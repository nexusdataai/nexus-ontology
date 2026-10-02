# Test Script Coverage Matrix

## Overview

This document provides a clear mapping of what each test script in the `run-jobs` folder actually tests.

## Test Scripts and Their Coverage

| Script Name | Primary Purpose | Operations Tested | Type |
|------------|-----------------|-------------------|------|
| **`test_run_job_action.sh`** | Tests job execution functionality | • `run_job` action<br>• Different trigger types<br>• Invalid parameter handling<br>• Journey/stage validation | **Execution Testing** |
| **`test_journey_inspection_operations.sh`**<br>*(formerly test_enhanced_run_jobs.sh)* | Tests journey analysis and reporting | • `list_rules` - List journey rules<br>• `dashboard` - Get analytics<br>• `get_journey_summary` - Summary data<br>• `get_comprehensive` - Full details<br>• Error handling | **Inspection/Reporting** |
| **`test_journeys_job_operations.sh`** | Tests job management operations | • `update_job_status` - Update status<br>• `get_job_metrics` - Get metrics<br>• `get_job_timeline` - Get timeline<br>• `batch_cancel_jobs` - Bulk cancel | **Job Management** |

## Coverage Categories

### 1. 🚀 **Job Execution**
- **Script:** `test_run_job_action.sh`
- **Purpose:** Actually running transformation jobs
- **Key Actions:** `run_job`

### 2. 📊 **Journey Inspection/Reporting**
- **Script:** `test_journey_inspection_operations.sh`
- **Purpose:** Analyzing and viewing journey data
- **Key Actions:** `dashboard`, `get_journey_summary`, `list_rules`, `get_comprehensive`

### 3. 🔧 **Job Management**
- **Script:** `test_journeys_job_operations.sh`
- **Purpose:** Managing existing jobs (status, metrics, cancellation)
- **Key Actions:** `update_job_status`, `get_job_metrics`, `get_job_timeline`, `batch_cancel_jobs`

## Why All Three Scripts Are Needed

Each script serves a distinct purpose:

1. **`test_run_job_action.sh`** - Tests the **execution** of new jobs
2. **`test_journey_inspection_operations.sh`** - Tests **viewing/analyzing** journey information
3. **`test_journeys_job_operations.sh`** - Tests **managing** existing jobs

They are complementary, not redundant:
- You need to **run** jobs (script 1)
- You need to **inspect** journeys (script 2)  
- You need to **manage** running/completed jobs (script 3)

## Complete Test Flow

For comprehensive testing, run scripts in this order:

```bash
# 1. First, test journey inspection to understand what journeys exist
./test_journey_inspection_operations.sh

# 2. Then, test running new jobs on those journeys
./test_run_job_action.sh JRN-XXX

# 3. Finally, test managing those running jobs
./test_journeys_job_operations.sh
```

## Quick Reference

| Need to test... | Use this script |
|----------------|-----------------|
| Running a new transformation job | `test_run_job_action.sh` |
| Viewing journey dashboard/summary | `test_journey_inspection_operations.sh` |
| Updating job status | `test_journeys_job_operations.sh` |
| Getting job metrics | `test_journeys_job_operations.sh` |
| Listing journey rules | `test_journey_inspection_operations.sh` |
| Canceling multiple jobs | `test_journeys_job_operations.sh` |
| Testing different job triggers | `test_run_job_action.sh` |
| Getting comprehensive journey data | `test_journey_inspection_operations.sh` |

## Note on Naming

The script `test_enhanced_run_jobs.sh` was renamed to `test_journey_inspection_operations.sh` to better reflect its actual functionality. Despite its original name suggesting it tests "running jobs", it actually tests journey inspection and reporting operations.
