
# How sematic rag should behave 

For Oracle ERP + Salesforce RAG, each test should verify:

1. Correct object identification
2. Correct field-level mapping
3. Correct policy retrieval
4. Correct workflow dependency retrieval
5. Correct cross-system linkage awareness
6. Correct risk/approval thresholds
7. Correct environment restrictions
8. Correct version awareness

---

# 🧪 10 Black-Box Test Scenarios

Each test below contains:

* User Question
* Expected RAG Retrieval (What must be surfaced)
* What Failure Looks Like

---

# ✅ Test 1 — Field Ownership & Source of Truth

### Question:

> Which system is the source of truth for customer credit limit?

### Expected Retrieval:

* Salesforce Account.Credit_Limit__c field
* Policy document stating Salesforce owns credit limit
* Integration mapping showing sync to Oracle AR
* Dependency rule: "Oracle AR balance cannot override credit limit"

### Failure:

* Says Oracle is source of truth
* Doesn’t mention integration mapping
* Misses policy constraints

---

# ✅ Test 2 — Approval Threshold Logic

### Question:

> What happens if I increase a customer's credit limit by more than 15%?

### Expected Retrieval:

* Business rule: >10% requires approval
* Workflow: Credit Limit Approval Flow
* Required approver role
* SLA for approval
* ERP sync condition after approval

### Failure:

* Only retrieves field definition
* Misses approval threshold
* Misses workflow dependency

---

# ✅ Test 3 — Cross-System Dependency Awareness

### Question:

> If I deactivate a customer in Salesforce, what is impacted in Oracle ERP?

### Expected Retrieval:

* Salesforce Account.Status field
* Integration mapping to Oracle AR customer status
* Policy: "Deactivation requires AR balance check"
* Dependency: Cannot deactivate if open invoices exist

### Failure:

* Only retrieves Salesforce field
* Doesn’t mention AR or invoice dependency

---

# ✅ Test 4 — Financial Close Restriction

### Question:

> Can customer credit limits be modified during financial close?

### Expected Retrieval:

* Close window policy document
* ERP restriction rule
* Environment flag: close_period_active
* Compliance rule: SOX constraint

### Failure:

* Says “Yes” without policy context
* Does not retrieve close window restriction

---

# ✅ Test 5 — Field Validation Constraint

### Question:

> What validations apply to the credit limit field?

### Expected Retrieval:

* Field type (currency)
* Max allowed value
* Required justification field
* Approval rule threshold
* Dependency: Risk tier must be evaluated

### Failure:

* Only retrieves field type
* Misses validation and policy constraints

---

# ✅ Test 6 — Workflow Trigger Discovery

### Question:

> What workflows are triggered when a new enterprise customer is created?

### Expected Retrieval:

* Salesforce Account creation workflow
* Risk assessment process
* Oracle ERP customer provisioning
* Credit review process
* Required data enrichment step

### Failure:

* Only retrieves object schema
* Misses workflow chain

---

# ✅ Test 7 — Risk Tier Dependency

### Question:

> How is customer risk tier determined and where is it used?

### Expected Retrieval:

* Field: Risk_Tier__c (Salesforce)
* Risk scoring process documentation
* Policy linking risk tier to credit approval threshold
* ERP AR collection priority rule

### Failure:

* Only retrieves field location
* Misses downstream usage in approval logic

---

# ✅ Test 8 — Schema Drift Awareness

### Question:

> What changed in customer schema in the last release?

### Expected Retrieval:

* Versioned schema metadata
* Newly added fields
* Deprecated fields
* Policy updates referencing new fields

### Failure:

* Returns outdated schema
* No version awareness

---

# ✅ Test 9 — Permission Constraint Awareness

### Question:

> Who is authorized to override customer credit block?

### Expected Retrieval:

* Role definition (Finance Manager)
* Policy override rule
* Audit logging requirement
* Required justification documentation

### Failure:

* Does not retrieve RBAC mapping
* Misses override logging requirement

---

# ✅ Test 10 — Multi-System Transaction Awareness

### Question:

> What steps are required to fully onboard a new B2B customer across systems?

### Expected Retrieval:

* Salesforce account creation schema
* Required fields list
* Oracle ERP customer creation process
* Credit assessment workflow
* Integration dependency mapping
* Sequence constraints
* Failure rollback rule

### Failure:

* Only retrieves Salesforce object
* Misses Oracle provisioning
* Misses process order

---

# 📊 How to Score Black-Box Tests

Each question should be evaluated on:

| Dimension                     | Score |
| ----------------------------- | ----- |
| Correct Object Identified     | 1     |
| Correct Fields Retrieved      | 1     |
| Policy Retrieved              | 1     |
| Workflow Dependency Retrieved | 1     |
| Cross-System Impact Retrieved | 1     |
| Version Correct               | 1     |

Max per test: 6
Production readiness target: ≥ 5 average

---

# 🔎 Advanced Black-Box Test (Edge Case)

### Question:

> Increase ACME's credit limit to 2 million.

RAG must retrieve:

* Current credit limit
* Risk tier
* Approval threshold
* Max allowed limit
* ERP impact
* Financial close restriction

If it only retrieves field name and value — your RAG is shallow.

---

# 🚨 Red Flags in Testing

Your RAG is not enterprise-grade if:

* It retrieves only schema but not policy
* It ignores workflow documentation
* It doesn’t surface cross-system dependencies
* It misses versioned updates
* It retrieves irrelevant objects frequently
* It retrieves too much noise

---

# 🏁 What Good Enterprise Semantic RAG Looks Like

When a question is asked, the retrieval bundle should look like:

## Retrieval bundle
```
Primary Object: Salesforce.Account
Relevant Fields: Credit_Limit__c, Risk_Tier__c
Policies: Credit Increase Approval Rule v3.2
Workflow: Credit Approval Flow
ERP Dependency: AR_Customer_Sync
Close Window Restriction: Enabled
```

If retrieval lacks one of these dimensions — planning will be unsafe.

---

# 🧠 Final Insight

Semantic RAG in enterprise is not about answering questions.

It is about enabling safe orchestration decisions.

If retrieval does not surface:

* Constraints
* Dependencies
* Ownership
* Approval requirements

Then your ReAct agent becomes dangerous.


I’ll show you:

1. What to extract
2. How to normalize it
3. How to chunk it
4. How to embed it
5. How to store it
6. How to enable safe retrieval
7. A concrete example

---

# 🎯 Goal

Turn this:

* Salesforce metadata
* Oracle ERP configuration
* Policy documents
* Workflow definitions
* Integration mappings

Into structured semantic retrieval units that support safe planning.

---

# 1️⃣ Step 1 — Define Canonical Knowledge Model

Before indexing anything, define a unified metadata schema.

This is critical.

We do NOT dump raw JSON.

We normalize into a canonical document model:

```json
{
  "id": "SF_ACCOUNT_CREDIT_LIMIT_V3",
  "system": "Salesforce",
  "entity_type": "Field",
  "object_name": "Account",
  "field_name": "Credit_Limit__c",
  "version": "3.2",
  "environment": "prod",
  "category": "Schema | Policy | Workflow | Integration",
  "risk_level": "Medium",
  "content": "... natural language enriched description ...",
  "structured_metadata": {
      "data_type": "Currency",
      "max_value": 1000000,
      "approval_threshold_percent": 10,
      "sync_target": "AR_Customer"
  }
}
```

This is what gets embedded.

---

# 2️⃣ Step 2 — Extract Metadata From Systems

### A. Salesforce

Use:

* Metadata API
* Tooling API

Extract:

* Object definitions
* Field metadata
* Validation rules
* Workflow rules
* Apex triggers
* Flow definitions

---

### B. Oracle ERP

Extract:

* Table schema
* Business rule configuration
* Approval hierarchies
* GL rules
* AR/AP dependencies
* Customizations

---

### C. Enterprise Policy Docs

Parse:

* PDF policies
* Confluence docs
* Compliance documentation
* SOPs

Use document parser → structured text.

---

# 3️⃣ Step 3 — Semantic Enrichment

Raw metadata is not enough.

We enrich it.

Example:

Raw:

```
Field: Credit_Limit__c
Type: Currency(18,2)
Validation Rule: value <= 1000000
```

Enriched document:

```
The Credit Limit field on the Salesforce Account object 
defines the maximum allowable credit exposure for a customer.

Business Rules:
- Maximum allowed value is 1,000,000 USD.
- Increases above 10% require Finance Manager approval.
- Field syncs to Oracle AR_Customer.credit_limit.
- Cannot be modified during financial close window.
- Requires Risk_Tier__c evaluation before update.

Dependent Workflows:
- Credit Approval Flow
- AR Sync Process
```

Now the embedding captures meaning and dependencies.

This is critical.

---

# 4️⃣ Step 4 — Intelligent Chunking Strategy

Never chunk randomly by tokens.

Chunk by semantic unit:

### Good Chunk Types:

* One object + its fields
* One policy rule
* One workflow definition
* One integration mapping

Each chunk should answer:

* What is this?
* What are its constraints?
* What are its dependencies?
* What system owns it?

---

# 5️⃣ Step 5 — Embedding Strategy

For each chunk:

```
embedding = embed(content)
```

Store:

```
vector
+ metadata filters
```

Example metadata columns:

| Column      | Purpose                   |
| ----------- | ------------------------- |
| system      | Salesforce / Oracle       |
| entity_type | Field / Policy / Workflow |
| object_name | Account                   |
| version     | 3.2                       |
| environment | prod/sandbox              |
| risk_level  | high/medium/low           |
| category    | schema/policy/integration |

This enables hybrid filtering.

---

# 6️⃣ Step 6 — Storage Example (Postgres + pgvector)

Example table:

```sql
CREATE TABLE enterprise_rag_index (
    id TEXT PRIMARY KEY,
    system TEXT,
    entity_type TEXT,
    object_name TEXT,
    field_name TEXT,
    category TEXT,
    version TEXT,
    environment TEXT,
    risk_level TEXT,
    content TEXT,
    embedding VECTOR(1536)
);
```

Index:

```sql
CREATE INDEX ON enterprise_rag_index
USING ivfflat (embedding vector_cosine_ops);
```

---

# 7️⃣ Step 7 — Retrieval Mechanism

When user asks:

> Increase credit limit for ACME

Pipeline:

### 1️⃣ Intent Detection

Detect: credit limit change

### 2️⃣ Query Expansion

Expand query:

```
credit limit approval rules validation threshold workflow dependency Oracle sync
```

### 3️⃣ Hybrid Query

```sql
SELECT *
FROM enterprise_rag_index
WHERE system IN ('Salesforce', 'Oracle')
AND category IN ('Schema', 'Policy', 'Workflow', 'Integration')
ORDER BY embedding <-> query_embedding
LIMIT 10;
```

### 4️⃣ Rerank Results

Optional: cross-encoder reranker

---

# 8️⃣ Example End-to-End

Let’s walk a full example.

---

## Input:

> What happens if I increase credit limit by 20%?

---

## Retrieved Chunks:

1️⃣ Salesforce Account.Credit_Limit__c field definition
2️⃣ Policy: >10% requires approval
3️⃣ Workflow: Credit Approval Flow
4️⃣ Integration: Sync to Oracle AR
5️⃣ Close window restriction

---

## Final RAG Context Given to LLM:

```
Field: Credit_Limit__c (Salesforce Account)
- Max value: 1,000,000
- Approval threshold: >10%

Policy:
- Increases above 10% require Finance Manager approval.

Workflow:
- Credit Approval Flow triggered on update.

Integration:
- Syncs to Oracle AR_Customer.credit_limit.

Restriction:
- Modifications blocked during financial close window.
```

Now the agent can safely plan.

---

# 9️⃣ Versioning Mechanism

When Salesforce metadata changes:

1. Detect change (webhook / scheduled sync)
2. Rebuild enriched chunk
3. Increment version
4. Soft-delete old version
5. Re-embed

Never overwrite blindly.

---

# 🔟 Automation Pipeline

Production indexing pipeline looks like:

```
Salesforce Metadata Pull
        ↓
Normalization
        ↓
Semantic Enrichment
        ↓
Chunking
        ↓
Embedding
        ↓
Vector DB Insert
        ↓
Index Refresh
```

Run:

* On deployment
* Nightly
* On metadata change

---

# 1️⃣1️⃣ Common Mistakes

❌ Embedding raw JSON
❌ Chunking by token size
❌ No metadata filters
❌ No versioning
❌ Mixing production + sandbox
❌ Indexing transactional data

---

# 1️⃣2️⃣ Advanced Enhancement (Very Powerful)

Add structured relationships:

```
Account.Credit_Limit__c
   → triggers → Credit Approval Flow
   → syncs_to → AR_Customer.credit_limit
   → constrained_by → Close_Window_Policy
```

Store relationships in graph DB.

Then combine:

* Vector search for semantic match
* Graph traversal for dependency expansion

This gives enterprise-grade reasoning.

---

# 🔐 Production Rule

Semantic RAG must retrieve:

* Object
* Field
* Policy
* Workflow
* Integration dependency
