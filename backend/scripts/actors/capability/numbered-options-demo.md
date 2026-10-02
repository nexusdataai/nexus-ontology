# Numbered Options Enhancement

## Overview
The capability-manager.py CLI has been enhanced to display selection options as numbered choices instead of requiring users to type full text values.

## What Changed

### Before:
```
Business Domain (operations/customer/product/finance/hr/technology/sales/marketing/supply-chain/analytics/security/compliance): 
```
Users had to type the exact domain name.

### After:
```
📦 Select Business Domain:
  [1] operations
  [2] customer
  [3] product
  [4] finance
  [5] hr
  [6] technology
  [7] sales
  [8] marketing
  [9] supply-chain
  [10] analytics
  [11] security
  [12] compliance

Select domain (1-12): 
```
Users simply type a number.

## Enhanced Functions

### 1. Create Capability (`create_capability`)
- **Business Domain**: Numbered options 1-12
- **Priority**: Numbered options 1-4 (low, medium, high, critical)

### 2. Update Capability (`update_capability`)
- **Status**: Numbered options 1-5 (planning, development, active, deprecated, retiring)
- **Priority**: Numbered options 1-4

### 3. Create Component (`create_component`)
- **Component Type**: Numbered options for all component types

### 4. Create Job (`create_job`)
- **Job Type**: Numbered options for all job types
- **Priority**: Numbered options 1-4

## Benefits
✅ **Faster Input**: Type a number instead of full text
✅ **No Typos**: Eliminates spelling errors
✅ **Clear Options**: See all available choices at once
✅ **Better UX**: Colored output with confirmation
✅ **Fallback**: Invalid selections default to safe values

## Usage Example
```bash
# When creating a capability:
📦 Select Business Domain:
  [1] operations
  [2] customer
  [3] product
  ...

Select domain (1-12): 3
✓ Selected: product

⚡ Select Priority:
  [1] low
  [2] medium
  [3] high
  [4] critical

Select priority (1-4): 3
✓ Selected: high
```

## Error Handling
- Invalid numbers show warning and use default
- Out-of-range selections use safe defaults
- Non-numeric input handled gracefully
