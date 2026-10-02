# Product Pricing Implementation

## Executive Summary

The CallSense platform retrieves real-time product pricing from Salesforce CPQ (CloudSense) through a 4-step query chain that mirrors the Langflow Product Pricing Agent. For each processed sales call, the system:

1. **Identifies products** discussed on the call using AI-powered transcript analysis
2. **Matches products** to Salesforce CPQ Price Items using a progressive relaxation ladder (R0-R4)
3. **Retrieves pricing** through the CloudSense 3-object chain (Price Item → Pricing Element → Price Item Pricing Rule Association)
4. **Calculates deal value** by aggregating recurring and one-off charges, multiplied by quantity

The pricing is sourced from live Salesforce data via the BSSMagic FDW (Foreign Data Wrapper) runtime, which translates SOQL queries into Axway API calls. Pricing values displayed in the application are **never AI-estimated** — they are actual Salesforce CPQ prices. When pricing cannot be fetched, the system shows "Deal value could not be determined" rather than fabricating values.

### Key Parameters

| Parameter | Source | Default |
|-----------|--------|---------|
| Product Name | AI extraction from call transcript | Required |
| Contract Term | AI extraction from transcript | 24 months |
| Quantity / Connections | AI extraction from transcript | 1 |
| Currency | PRA query filter | SGD |
| Adjustment Type | PRA query filter | Initial Price |

### Deal Value Formula

```
Per-Product Deal Value:
  Recurring = SUM(cspmb__recurring_adjustment__c) from matching PRAs
  One-off   = SUM(cspmb__one_off_adjustment__c) from matching PRAs

Total Deal Value:
  Total Recurring = SUM(per_product_recurring × quantity) across all products
  Total One-off   = SUM(per_product_one_off × quantity) across all products
```

---

## Detailed Technical Implementation

### Step 1: Product Extraction from Transcript (Step 5.5)

**Prompt**: `DEFAULT_PRODUCT_DETAILS_PROMPT` in `prompt_model.py`

The AI analyzes the call transcript and extracts a structured JSON with:

```json
{
  "products": [
    {
      "product_name": "Business Internet Light Dedicated 300 Mbps",
      "product_type": "Internet Service",
      "bandwidth": "300 Mbps",
      "contract_length": "24 months",
      "contract_term_months": 24,
      "quantity": 1,
      "customer_interest": "high|medium|low",
      "features": ["Static IP", "SLA"]
    }
  ]
}
```

**Fields used downstream**:
- `product_name` → product matching (Step 6.5)
- `product_type`, `bandwidth` → SOQL query refinement
- `contract_term_months` → contract-term-aware product variant selection (Step 6.6)
- `quantity` → deal value multiplier

**Edge cases**:
- If contract term not discussed: defaults to 24 months
- If quantity not discussed: defaults to 1
- If no products discussed: empty array, pricing step is skipped entirely

---

### Step 2: Product Matching (Step 6.5)

**Implementation**: `ProductMatcher.match_products()` in `bssmagic_crm_service.py`

Uses an R0→R4 progressive relaxation ladder to find matching `cspmb__Price_Item__c` records:

| Level | Strategy | Criteria |
|-------|----------|----------|
| R0 | Strict | Product Definition Name + Bandwidth + Unlimited flags |
| R1 | Relax bandwidth | Product Definition Name + Unlimited flags (drop bandwidth) |
| R2 | Relax unlimited | Product Definition Name only |
| R3 | Name search | LIKE query on Price Item Name |
| R4 | Broadest | Category-based fallback |

**Query invariants** (always applied):
- `cspmb__Is_Active__c = true`
- `cspmb__Role__c = 'Variant'`
- `LIMIT 2` (at most 2 matches per level)

**Contract term selection**: When multiple products match (e.g., "-1", "-12", "-24", "-36" variants), the system prefers the variant whose name contains `-{contract_term_months}`. For example, if the customer discussed a 24-month contract, the product ending in "-24" is selected. If no contract-term match exists, the first match is used.

**Edge cases**:
- No match at any level: product is skipped, no pricing for it
- Product Definition Name not recognized: R3/R4 use broader LIKE queries
- Multiple products discussed: each is matched independently

---

### Step 3: Pricing Element Retrieval (Step 6.6a-b)

**SOQL Query** (Step 6.6a):
```sql
SELECT Id, Name, cspmb__commercial_product__c,
       cspmb__description__c, cspmb__key__c,
       cspmb__pricing_element_type__c,
       cspmb__pricing_element_type__r.cspmb__description__c,
       cspmb__pricing_element_type__r.cspmb__key_definition__c,
       cspmb__pricing_element_type__r.cspmb__type__c
FROM cspmb__Pricing_Element__c
WHERE cspmb__commercial_product__c IN (<matched_product_ids>)
```

**Variant Filtering** (Step 6.6b — `_filter_pricing_elements`):

Each product can have multiple Pricing Elements representing different charge types and order scenarios. The filter:

1. **Segregates by charge type** using `cspmb__pricing_element_type__r.cspmb__type__c`:
   - "Recurring" → recurring charge PEs
   - "One Off" → one-off charge PEs
   - Other → fallback bucket

2. **Selects best variant per bucket** using `cspmb__key__c` and `cspmb__key_definition__c`:
   - Groups PEs by `key_definition`
   - Within each group, prefers PEs whose `cspmb__key__c` contains: "new", "new order", "default", "standard"
   - Falls back to first PE in group if no preferred key matches

3. **Result**: One PE per charge-type per key-definition per product (eliminates duplicates from Transfer Ownership, Reconnect, Nexus Telco Relocation variants)

**Edge cases**:
- No Pricing Elements found: pricing unavailable, step completes with empty results
- All PEs have keys like "Transfer Ownership" or "Reconnect" (no "new order"): first PE in each group is used
- Single PE per product: no filtering needed, passed through directly

---

### Step 4: Pricing Rule Association Query (Step 6.6c)

**SOQL Query**:
```sql
SELECT Id, cspmb__pricing_element__c,
       cspmb__one_off_adjustment__c, cspmb__recurring_adjustment__c,
       cspmb__one_off_adjustment_type__c, cspmb__recurring_adjustment_type__c,
       CurrencyIsoCode
FROM cspmb__Price_Item_Pricing_Rule_Association__c
WHERE cspmb__pricing_element__c IN (<filtered_pe_ids>)
  AND (cspmb__recurring_adjustment_type__c = 'Initial Price'
       OR cspmb__one_off_adjustment_type__c = 'Initial Price')
  AND CurrencyIsoCode = 'SGD'
```

**Filter criteria**:
- Only PRAs where at least one adjustment type is "Initial Price" (base/list price)
- Only SGD currency
- Excludes PRAs that are purely discount-type (e.g., "Absolute Discount" on both sides)

**Batching**: PEs are queried in batches of 5 to avoid SOQL query length limits.

**Fields retrieved**:

| Field | Purpose |
|-------|---------|
| `cspmb__one_off_adjustment__c` | One-off charge amount (SGD) |
| `cspmb__recurring_adjustment__c` | Monthly recurring charge amount (SGD) |
| `cspmb__one_off_adjustment_type__c` | Type: "Initial Price" or "Absolute Discount" |
| `cspmb__recurring_adjustment_type__c` | Type: "Initial Price" or "Absolute Discount" |
| `CurrencyIsoCode` | Currency code (filtered to SGD) |

**Edge cases**:
- PRA query returns no Initial Price records: product has no pricing
- Price fields are null for some records: null values are safely skipped in aggregation
- Batch query fails: warning logged, other batches continue

---

### Step 5: Price Aggregation (Step 6.6d)

For each product, all matching PRA records are aggregated:

```python
total_recurring_charge = SUM(cspmb__recurring_adjustment__c)  # where not null
total_one_off_charge   = SUM(cspmb__one_off_adjustment__c)    # where not null
```

**Important**: Both recurring and one-off values from ALL matching PRAs are summed, including PRAs where one type is "Initial Price" and the other is "Absolute Discount". The WHERE clause already filters to PRAs that have at least one "Initial Price" type.

---

### Step 6: Deal Value Calculation

**Location**: `_validate_compiled_actions()` and `_build_sfdc_actions_fallback()`

```
For each matched product:
  quantity = product_details.quantity (default 1)
  product_recurring = pricing_by_product[product_id].total_recurring_charge
  product_one_off   = pricing_by_product[product_id].total_one_off_charge

  total_recurring += product_recurring × quantity
  total_one_off   += product_one_off × quantity
```

The result is stored in `sfdc_action.json`:

```json
{
  "deal_value": {
    "total_recurring_charge": 230.0,
    "total_one_off_charge": 371.0,
    "currency": "SGD",
    "products_priced": 2
  },
  "products": [
    {
      "requested_product": "Business Broadband",
      "matched_product_id": "a4C2s000000VNE4EAO",
      "matched_product_name": "Business Wireless Broadband 4G (Dynamic IP) 100GB -24",
      "recurring_price": 100.0,
      "one_off_price": 160.5,
      "quantity": 1,
      "currency": "SGD"
    }
  ]
}
```

---

## Data Flow Diagram

```
Call Transcript
    │
    ▼
┌─────────────────────────┐
│ Step 5.5: AI Extraction │  → product_name, bandwidth, contract_term_months, quantity
│ (product-details.json)  │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Step 6.5: Product Match │  → cspmb__Price_Item__c IDs (R0-R4 ladder)
│ (SOQL via BSSMagic FDW) │     Contract term selects correct variant (-12, -24, -36)
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Step 6.6a: Pricing      │  → cspmb__Pricing_Element__c records
│ Elements (with type     │     with relationship fields for type metadata
│ relationship fields)    │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Step 6.6b: Variant      │  → Filtered PEs (recurring vs one-off, best variant)
│ Filter (Langflow Step 3)│     Eliminates Transfer Ownership, Reconnect, Relocation
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Step 6.6c: PRA Query    │  → cspmb__Price_Item_Pricing_Rule_Association__c
│ (Initial Price + SGD)   │     Actual dollar amounts: one_off_adjustment, recurring_adjustment
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Step 6.6d: Aggregation  │  → total_recurring_charge, total_one_off_charge per product
│ + Quantity Multiplier   │     × quantity for deal value totals
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ sfdc_action.json        │  → deal_value + per-product pricing
│ (stored in S3)          │     Displayed in Call Analysis Report + Deal Analysis Dashboard
└─────────────────────────┘
```

---

## Exception Scenarios

| Scenario | Behavior | User Impact |
|----------|----------|-------------|
| No products discussed in call | Pricing step skipped entirely | Deal value shows "could not be determined" |
| Product not found in Salesforce CPQ | R0→R4 ladder exhausted, product skipped | Product excluded from deal value |
| No Pricing Elements for matched product | Pricing unavailable for that product | Product shows $0 pricing |
| No PRAs with Initial Price type | No pricing records returned | Product shows $0 pricing |
| PRA query fails (network/timeout) | Warning logged, other batches continue | Partial pricing may be available |
| Currency not SGD | PRA filtered out | Only SGD pricing is captured |
| Contract term not discussed | Defaults to 24 months | Selects 24-month product variant |
| Quantity not discussed | Defaults to 1 | No multiplier applied |
| Both recurring and one-off are $0 | deal_value fields set to null | Report shows "Deal value could not be determined" |
| Multiple products, only some have pricing | Priced products contribute to total | Unpriced products show $0 individually |
| Axway API returns 400/500 | BSSMagic retries, then pricing step logs error | Pricing unavailable for that batch |

---

## API and Infrastructure

| Component | Role |
|-----------|------|
| **BSSMagic FDW Runtime** | PostgreSQL Foreign Data Wrapper that translates SOQL to Axway REST API calls |
| **Axway API Gateway** | `nexus-telco-api.invalid` — proxies to Salesforce |
| **Salesforce CPQ (CloudSense)** | Source of truth for products, pricing elements, and pricing rules |
| **S3** | Stores `sfdc_action.json` with deal_value and per-product pricing |
| **Call Analysis Dashboard** | Fetches `sfdc_action.json` via `/api/v1/calls/{id}/sfdc-action` and displays pricing in report modal |
| **Deal Analysis Dashboard** | Fetches SFDC deal values for all calls and aggregates into pipeline metrics |

---

## Alignment with Langflow Product Pricing Agent

The implementation mirrors the Langflow Product Pricing Agent's 5-step approach:

| Langflow Step | CallSense Step | Description |
|---------------|----------------|-------------|
| Step 1: Price Item lookup | Step 6.5 (Product Match) | Find `cspmb__Price_Item__c` by product code/name |
| Step 2: Pricing Elements | Step 6.6a | Query `cspmb__Pricing_Element__c` with relationship fields |
| Step 3: Segregate by type | Step 6.6b (`_filter_pricing_elements`) | Separate recurring vs one-off, select best variant by key |
| Step 4: PRA query | Step 6.6c | Query `cspmb__Price_Item_Pricing_Rule_Association__c` with Initial Price + SGD filter |
| Step 5: Consolidate | Step 6.6d | Sum recurring and one-off charges per product |

**Key difference**: CallSense adds contract-term-aware product selection and quantity multiplication, which Langflow does not perform.
