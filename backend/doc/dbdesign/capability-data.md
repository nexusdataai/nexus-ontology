# DynamoDB Database Structure for Business Capability Catalogue

## Overview

The Business Capability Catalogue uses **AWS DynamoDB** with a **Single Table Design** pattern to store all capability-related data in one table called `BusinessCapabilitySystem`. This design provides exceptional performance, scalability, and cost-effectiveness by grouping related data together and using composite keys for efficient queries.

Each **Business Capability** represents a business functionality (like "Alert Management", "Customer Onboarding", "Fraud Detection") delivered through composed software components including UI Dashboards, API Servers, MCP Servers, Databases, and other technical building blocks.

---

## Why Single Table Design?

**Business Benefits:**
- ✅ **Faster Queries** - All related data retrieved in one query (capability + components + dependencies + metrics)
- ✅ **Lower Costs** - Fewer queries = lower AWS costs
- ✅ **Better Performance** - Related data stored together on same partition
- ✅ **Scalability** - Unlimited scale with predictable performance
- ✅ **Flexibility** - Easy to add new component types without schema changes
- ✅ **Operational Efficiency** - Single source of truth for capability architecture

**Traditional vs Single Table:**
```
Traditional (Multiple Tables):
- Capabilities Table
- Components Table  
- Dependencies Table
- Metrics Table
- Configuration Table
- Jobs Table
→ 6 queries to understand complete capability architecture ❌

Single Table Design:
- BusinessCapabilitySystem Table
→ 1-2 queries to get complete capability view ✅
```

---

## Table Structure

### Primary Keys

#### Partition Key (PK)
Groups all data for a specific capability together.

**Pattern:** `CAPABILITY#{capabilityId}`

**Example:** `CAPABILITY#CAP-ALERT-MGT-001`

**Why:** All data for capability CAP-ALERT-MGT-001 (components, dependencies, metrics, etc.) is stored on the same partition, enabling fast retrieval of complete capability information in a single query.

#### Sort Key (SK)
Uniquely identifies the type and instance of data within a capability.

**Patterns:**
- `METADATA` - Capability metadata (one per capability)
- `COMPONENT#{order:02d}#{componentId}` - Software components (ordered by layer/criticality)
- `DEPENDENCY#{sourceComponentId}#{targetComponentId}` - Component relationships
- `JOB#{timestamp}#{jobId}` - Implementation/deployment jobs
- `METRIC#{componentId}#{metricType}#{timestamp}` - Performance metrics
- `RULE#{priority:03d}#{ruleId}` - Configuration and business rules

**Examples:**
```
METADATA
COMPONENT#01#ui-dashboard-alert-001
COMPONENT#02#api-server-alert-001
COMPONENT#03#mcp-server-alert-001
COMPONENT#04#database-alert-001
DEPENDENCY#api-server-alert-001#database-alert-001
JOB#2025-11-22T10:00:00Z#JOB-DEPLOY-456
METRIC#api-server-alert-001#latency#2025-11-22T10:30:00Z
RULE#001#rule-alert-severity-mapping
```

### Global Secondary Index (GSI1)

Enables queries across multiple capabilities or specific subsets of data.

#### GSI1 Partition Key (GSI1PK)
Groups related entities for cross-capability queries.

**Patterns:**
- `CAPABILITIES` - All capability metadata (for listing all capabilities)
- `CAPABILITY#{capabilityId}#COMPONENTS` - All components for a capability
- `COMPONENT#{componentType}` - All components of a specific type
- `DOMAIN#{businessDomain}` - All capabilities in a business domain
- `JOB#{jobId}` - All metrics/logs for a specific job
- `HEALTH#{status}` - Capabilities by health status

#### GSI1 Sort Key (GSI1SK)
Orders the data within the GSI1PK group.

**Patterns:**
- ISO 8601 timestamps for time-based ordering
- `{priority:02d}#{name}` for prioritized lists
- `{healthScore:03d}#{capabilityId}` for health-based sorting

---

## Entity Types

### 1. Capability Metadata

**Purpose:** Core information about a business capability

**Access Pattern:** Get specific capability by ID, list all capabilities

**Keys:**
- **PK:** `CAPABILITY#{capabilityId}`
- **SK:** `METADATA`
- **GSI1PK:** `CAPABILITIES`
- **GSI1SK:** `{businessDomain}#{priority:02d}#{name}`

**Data Structure:**
```json
{
  "PK": "CAPABILITY#CAP-ALERT-MGT-001",
  "SK": "METADATA",
  "EntityType": "Capability",
  "GSI1PK": "CAPABILITIES",
  "GSI1SK": "operations#01#alert-management",
  "CreatedAt": "2025-11-22T09:00:00.000000Z",
  "UpdatedAt": "2025-11-22T14:30:00.000000Z",
  "Data": {
    "capabilityId": "CAP-ALERT-MGT-001",
    "name": "Alert Management",
    "description": "End-to-end alert lifecycle management including creation, routing, escalation, and resolution",
    "businessDomain": "operations",
    "status": "active",
    "priority": "critical",
    "owner": "operations-team",
    "createdBy": "john.smith",
    "version": "2.1.0",
    "tags": ["alerting", "monitoring", "incident-management"],
    "businessMetrics": {
      "sla": "99.99%",
      "rto": "5 minutes",
      "rpo": "1 minute",
      "criticalityLevel": "tier-1"
    },
    "architecture": {
      "pattern": "microservices",
      "deploymentModel": "multi-region",
      "scalabilityType": "horizontal",
      "redundancy": "active-active"
    },
    "compliance": {
      "standards": ["ISO-27001", "SOC2", "GDPR"],
      "lastAudit": "2025-10-15T00:00:00Z",
      "certificationStatus": "certified"
    },
    "aggregates": {
      "totalComponents": 8,
      "activeComponents": 8,
      "healthScore": 98.5,
      "totalDependencies": 15,
      "totalJobs": 145,
      "successfulJobs": 142,
      "failedJobs": 3,
      "averageDeploymentTime": "12.5m",
      "totalIncidents": 5,
      "totalRules": 25,
      "activeRules": 23,
      "lastDeployment": "2025-11-20T18:00:00Z",
      "monthlyOperationalCost": 15000,
      "userCount": 500
    },
    "lifecycle": {
      "phase": "production",
      "plannedRetirement": null,
      "lastMajorUpdate": "2025-10-01T00:00:00Z",
      "nextReview": "2025-12-01T00:00:00Z"
    }
  }
}
```

**Business Logic:**
- `status` tracks capability lifecycle (planning, development, active, deprecated, retiring)
- `priority` determines business criticality (low, medium, high, critical)
- `healthScore` calculated from component health and incident history
- `businessDomain` groups capabilities by organizational structure
- `aggregates` provides real-time operational insights

---

### 2. Software Components

**Purpose:** Define individual software components that deliver the capability

**Access Pattern:** List all components for capability, find components by type

**Keys:**
- **PK:** `CAPABILITY#{capabilityId}`
- **SK:** `COMPONENT#{order:02d}#{componentId}`
- **GSI1PK:** `COMPONENT#{componentType}`
- **GSI1SK:** `{capabilityId}#{componentId}`

**Data Structure:**
```json
{
  "PK": "CAPABILITY#CAP-ALERT-MGT-001",
  "SK": "COMPONENT#01#ui-dashboard-alert-001",
  "EntityType": "SoftwareComponent",
  "GSI1PK": "COMPONENT#ui-dashboard",
  "GSI1SK": "CAP-ALERT-MGT-001#ui-dashboard-alert-001",
  "CreatedAt": "2025-11-22T09:00:00.000000Z",
  "UpdatedAt": "2025-11-22T14:00:00.000000Z",
  "Data": {
    "componentId": "ui-dashboard-alert-001",
    "capabilityId": "CAP-ALERT-MGT-001",
    "name": "Alert Management Dashboard",
    "description": "React-based dashboard for alert visualization and management",
    "componentType": "ui-dashboard",
    "order": 1,
    "layer": "presentation",
    "status": "active",
    "version": "2.3.1",
    "technology": {
      "stack": "react",
      "framework": "next.js",
      "language": "typescript",
      "runtime": "node-18",
      "dependencies": ["react@18.2.0", "next@13.4.0", "mui@5.14.0"]
    },
    "deployment": {
      "type": "container",
      "platform": "kubernetes",
      "image": "alert-dashboard:2.3.1",
      "replicas": 3,
      "resources": {
        "cpu": "500m",
        "memory": "1Gi"
      },
      "endpoints": [
        {
          "type": "https",
          "url": "https://alerts.company.com",
          "port": 443,
          "healthCheck": "/health"
        }
      ]
    },
    "configuration": {
      "environment": "production",
      "configMap": "alert-dashboard-config",
      "secrets": ["alert-api-key", "auth-secret"],
      "featureFlags": {
        "darkMode": true,
        "advancedFilters": true,
        "bulkActions": false
      }
    },
    "health": {
      "status": "healthy",
      "lastCheck": "2025-11-22T14:28:00Z",
      "availability": 99.98,
      "responseTime": 125,
      "errorRate": 0.02,
      "activeAlerts": 0
    },
    "sla": {
      "availability": 99.9,
      "responseTime": 200,
      "errorRate": 0.1
    },
    "ownership": {
      "team": "frontend-team",
      "leadEngineer": "sarah.johnson",
      "oncallRotation": "frontend-oncall",
      "slackChannel": "#alert-dashboard"
    },
    "repository": {
      "type": "github",
      "url": "https://github.com/company/alert-dashboard",
      "branch": "main",
      "cicdPipeline": "jenkins/alert-dashboard"
    }
  }
}
```

**Component Types:**
- `ui-dashboard` - User interface components
- `api-server` - REST/GraphQL API servers
- `mcp-server` - Model Context Protocol servers
- `database` - Data storage components
- `message-queue` - Async messaging components
- `cache` - Caching layers
- `scheduler` - Job scheduling components
- `worker` - Background processing workers

**Business Logic:**
- `order` determines component criticality/dependency order
- `layer` identifies architectural layer (presentation, business, data)
- `health.status` aggregates from monitoring systems
- `deployment` contains all operational details
- Components can be versioned independently

---

### 3. Component Dependencies

**Purpose:** Track relationships and dependencies between components

**Access Pattern:** Get dependency graph for capability, find dependent components

**Keys:**
- **PK:** `CAPABILITY#{capabilityId}`
- **SK:** `DEPENDENCY#{sourceComponentId}#{targetComponentId}`
- **GSI1PK:** `CAPABILITY#{capabilityId}#DEPENDENCIES`
- **GSI1SK:** `{criticality:02d}#{sourceComponentId}#{targetComponentId}`

**Data Structure:**
```json
{
  "PK": "CAPABILITY#CAP-ALERT-MGT-001",
  "SK": "DEPENDENCY#api-server-alert-001#database-alert-001",
  "EntityType": "ComponentDependency",
  "GSI1PK": "CAPABILITY#CAP-ALERT-MGT-001#DEPENDENCIES",
  "GSI1SK": "01#api-server-alert-001#database-alert-001",
  "CreatedAt": "2025-11-22T09:00:00.000000Z",
  "UpdatedAt": "2025-11-22T09:00:00.000000Z",
  "Data": {
    "sourceComponentId": "api-server-alert-001",
    "sourceComponentName": "Alert API Server",
    "targetComponentId": "database-alert-001",
    "targetComponentName": "Alert Database",
    "dependencyType": "runtime",
    "criticality": "critical",
    "interface": {
      "type": "database",
      "protocol": "postgresql",
      "connectionString": "vault:alert-db-connection",
      "poolSize": 20
    },
    "requirements": {
      "minVersion": "14.0",
      "features": ["json", "partitioning", "full-text-search"],
      "performance": {
        "maxLatency": "10ms",
        "minThroughput": "1000 qps"
      }
    },
    "fallback": {
      "strategy": "circuit-breaker",
      "timeout": "30s",
      "retries": 3,
      "backupComponent": null
    },
    "contract": {
      "schemaVersion": "1.2.0",
      "validationEnabled": true,
      "breakingChanges": false
    },
    "monitoring": {
      "sliEnabled": true,
      "alertThreshold": {
        "errorRate": 1,
        "latency": 100
      }
    }
  }
}
```

**Dependency Types:**
- `runtime` - Required for component to function
- `buildtime` - Required during build/compile
- `data` - Data flow dependency
- `optional` - Enhanced functionality but not required
- `fallback` - Backup/failover relationship

**Business Logic:**
- `criticality` determines impact of dependency failure
- `fallback.strategy` defines resilience patterns
- Dependencies form directed graph for analysis
- Contract validation ensures compatibility

---

### 4. Implementation Jobs

**Purpose:** Track deployment, update, and maintenance job executions

**Access Pattern:** Get job history for capability, monitor active deployments

**Keys:**
- **PK:** `CAPABILITY#{capabilityId}`
- **SK:** `JOB#{timestamp}#{jobId}`
- **GSI1PK:** `JOB#{jobId}`
- **GSI1SK:** `{timestamp}`

**Data Structure:**
```json
{
  "PK": "CAPABILITY#CAP-ALERT-MGT-001",
  "SK": "JOB#2025-11-22T10:00:00.000000Z#JOB-DEPLOY-456",
  "EntityType": "ImplementationJob",
  "GSI1PK": "JOB#JOB-DEPLOY-456",
  "GSI1SK": "2025-11-22T10:00:00.000000Z",
  "CreatedAt": "2025-11-22T10:00:00.000000Z",
  "UpdatedAt": "2025-11-22T10:15:00.000000Z",
  "Data": {
    "jobId": "JOB-DEPLOY-456",
    "capabilityId": "CAP-ALERT-MGT-001",
    "jobType": "deployment",
    "status": "completed",
    "priority": "high",
    "triggeredBy": "ci-pipeline",
    "approvedBy": "john.smith",
    "startTime": "2025-11-22T10:00:00.000000Z",
    "endTime": "2025-11-22T10:15:00.000000Z",
    "duration": 900,
    "targetComponents": [
      {
        "componentId": "api-server-alert-001",
        "fromVersion": "1.5.2",
        "toVersion": "1.6.0",
        "status": "completed"
      },
      {
        "componentId": "ui-dashboard-alert-001",
        "fromVersion": "2.3.0",
        "toVersion": "2.3.1",
        "status": "completed"
      }
    ],
    "strategy": {
      "type": "rolling",
      "canary": {
        "enabled": true,
        "percentage": 10,
        "duration": "5m"
      },
      "rollback": {
        "automatic": true,
        "threshold": {
          "errorRate": 5,
          "latency": 500
        }
      }
    },
    "validation": {
      "preDeployment": {
        "healthChecks": "passed",
        "smokeTests": "passed",
        "securityScan": "passed"
      },
      "postDeployment": {
        "functionalTests": "passed",
        "performanceTests": "passed",
        "integrationTests": "passed"
      }
    },
    "metrics": {
      "affectedUsers": 0,
      "downtime": 0,
      "rollbacksTriggered": 0,
      "deploymentsCompleted": 2,
      "totalArtifactsDeployed": 2
    },
    "artifacts": {
      "deploymentPlan": "s3://deployments/CAP-ALERT-MGT-001/JOB-456/plan.yaml",
      "logs": "s3://deployments/CAP-ALERT-MGT-001/JOB-456/logs/",
      "reports": "s3://deployments/CAP-ALERT-MGT-001/JOB-456/reports/"
    }
  }
}
```

**Job Types:**
- `deployment` - New version deployment
- `rollback` - Revert to previous version
- `configuration` - Config changes only
- `scaling` - Resource scaling operations
- `maintenance` - Routine maintenance tasks
- `emergency` - Emergency fixes

**Business Logic:**
- Jobs track complete deployment lifecycle
- Validation gates ensure safe deployments
- Metrics capture business impact
- Artifacts stored in S3 for audit trail

---

### 5. Performance Metrics

**Purpose:** Runtime metrics and health data for operational monitoring

**Access Pattern:** Get current metrics, query historical performance

**Keys:**
- **PK:** `CAPABILITY#{capabilityId}`
- **SK:** `METRIC#{componentId}#{metricType}#{timestamp}`
- **GSI1PK:** `METRICS#{componentId}`
- **GSI1SK:** `{timestamp}`

**Data Structure:**
```json
{
  "PK": "CAPABILITY#CAP-ALERT-MGT-001",
  "SK": "METRIC#api-server-alert-001#performance#2025-11-22T14:30:00.000000Z",
  "EntityType": "PerformanceMetric",
  "GSI1PK": "METRICS#api-server-alert-001",
  "GSI1SK": "2025-11-22T14:30:00.000000Z",
  "CreatedAt": "2025-11-22T14:30:00.000000Z",
  "TTL": 1735689600,
  "Data": {
    "componentId": "api-server-alert-001",
    "componentName": "Alert API Server",
    "metricType": "performance",
    "timestamp": "2025-11-22T14:30:00.000000Z",
    "interval": "1m",
    "dimensions": {
      "environment": "production",
      "region": "us-east-1",
      "availability_zone": "us-east-1a"
    },
    "values": {
      "availability": {
        "value": 100.0,
        "unit": "percent",
        "status": "healthy"
      },
      "latency": {
        "p50": 45,
        "p95": 125,
        "p99": 200,
        "max": 450,
        "unit": "milliseconds",
        "status": "healthy"
      },
      "throughput": {
        "requests": 15420,
        "successful": 15400,
        "failed": 20,
        "unit": "per_minute",
        "status": "healthy"
      },
      "errors": {
        "rate": 0.13,
        "count": 20,
        "unit": "percent",
        "types": {
          "4xx": 15,
          "5xx": 5,
          "timeout": 0
        },
        "status": "healthy"
      },
      "saturation": {
        "cpu": 45.2,
        "memory": 62.1,
        "connections": 120,
        "unit": "percent",
        "status": "healthy"
      }
    },
    "alerts": {
      "active": [],
      "resolved": [
        {
          "alertId": "ALT-789",
          "condition": "latency.p99 > 500ms",
          "triggeredAt": "2025-11-22T14:25:00Z",
          "resolvedAt": "2025-11-22T14:28:00Z"
        }
      ]
    },
    "trends": {
      "availability": "stable",
      "latency": "improving",
      "throughput": "increasing",
      "errors": "stable"
    }
  }
}
```

**Metric Types:**
- `performance` - Latency, throughput, availability
- `resource` - CPU, memory, disk, network
- `business` - User activity, transactions
- `quality` - Error rates, data quality
- `security` - Auth failures, threat detection

**Business Logic:**
- Metrics collected at regular intervals (1m, 5m, 1h)
- TTL set for automatic cleanup (e.g., 90 days)
- Aggregations computed for dashboards
- Alerting thresholds trigger notifications
- Trends calculated for capacity planning

---

### 6. Configuration Rules

**Purpose:** Business rules, policies, and operational configurations

**Access Pattern:** Get active rules for capability, filter by rule type

**Keys:**
- **PK:** `CAPABILITY#{capabilityId}`
- **SK:** `RULE#{priority:03d}#{ruleId}`
- **GSI1PK:** `CAPABILITY#{capabilityId}#RULES`
- **GSI1SK:** `{ruleType}#{priority:03d}#{ruleId}`

**Data Structure:**
```json
{
  "PK": "CAPABILITY#CAP-ALERT-MGT-001",
  "SK": "RULE#001#rule-alert-severity-mapping",
  "EntityType": "ConfigurationRule",
  "GSI1PK": "CAPABILITY#CAP-ALERT-MGT-001#RULES",
  "GSI1SK": "business#001#rule-alert-severity-mapping",
  "CreatedAt": "2025-11-22T09:00:00.000000Z",
  "UpdatedAt": "2025-11-22T12:00:00.000000Z",
  "Data": {
    "ruleId": "rule-alert-severity-mapping",
    "name": "Alert Severity Mapping",
    "description": "Maps incoming alerts to severity levels based on criteria",
    "ruleType": "business",
    "scope": "capability",
    "priority": "high",
    "status": "active",
    "version": "1.2.0",
    "author": "operations-team",
    "approvedBy": "jane.doe",
    "effectiveFrom": "2025-11-22T00:00:00Z",
    "effectiveUntil": null,
    "conditions": [
      {
        "field": "source",
        "operator": "in",
        "values": ["production", "staging"],
        "weight": 2
      },
      {
        "field": "error_count",
        "operator": ">=",
        "value": 100,
        "weight": 3
      },
      {
        "field": "customer_impact",
        "operator": "equals",
        "value": "high",
        "weight": 5
      }
    ],
    "actions": [
      {
        "type": "set_severity",
        "parameters": {
          "calculation": "sum_weights",
          "mapping": {
            "0-3": "low",
            "4-6": "medium",
            "7-9": "high",
            "10+": "critical"
          }
        }
      },
      {
        "type": "notify",
        "parameters": {
          "channels": ["slack", "pagerduty"],
          "template": "alert-notification-v2"
        }
      }
    ],
    "metadata": {
      "tags": ["alerting", "severity", "business-logic"],
      "compliance": ["SOC2-CC7.2"],
      "testCoverage": 95,
      "lastReview": "2025-11-01T00:00:00Z"
    },
    "metrics": {
      "executionCount": 45230,
      "averageExecutionTime": 2.3,
      "successRate": 99.98,
      "lastExecuted": "2025-11-22T14:29:55Z"
    }
  }
}
```

**Rule Types:**
- `business` - Business logic and policies
- `security` - Security policies and controls
- `compliance` - Regulatory compliance rules
- `operational` - Operational thresholds and limits
- `routing` - Request routing and load balancing
- `transformation` - Data transformation rules

**Business Logic:**
- Rules executed by priority order
- Versioned for change tracking
- Conditions evaluated with weights/scoring
- Actions triggered based on evaluation
- Metrics track rule effectiveness

---

## Data Retrieval Patterns

### Pattern 1: Get Complete Capability Information

**Business Need:** View all details about a capability including components, dependencies, and health

**Query Strategy:**
1. Get capability metadata: Query `PK = CAPABILITY#{id}` AND `SK = METADATA`
2. Get all components: Query `PK = CAPABILITY#{id}` AND `SK begins_with COMPONENT#`
3. Get dependencies: Query `PK = CAPABILITY#{id}` AND `SK begins_with DEPENDENCY#`
4. Get active rules: Query `PK = CAPABILITY#{id}` AND `SK begins_with RULE#`

**Code Example:**
```python
# Get capability metadata
capability = table.get_item(
    Key={
        'PK': 'CAPABILITY#CAP-ALERT-MGT-001',
        'SK': 'METADATA'
    }
)

# Get all components (sorted by order)
components = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'CAPABILITY#CAP-ALERT-MGT-001',
        ':sk': 'COMPONENT#'
    }
)

# Get all dependencies
dependencies = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'CAPABILITY#CAP-ALERT-MGT-001',
        ':sk': 'DEPENDENCY#'
    }
)
```

**Why This Works:**
- All data for one capability is on same partition (fast!)
- Single partition query retrieves related data efficiently
- Components naturally ordered by criticality/layer

---

### Pattern 2: List All Capabilities

**Business Need:** Show dashboard of all business capabilities

**Query Strategy:**
- Use GSI1: Query `GSI1PK = CAPABILITIES`
- Returns all capability metadata sorted by domain and priority

**Code Example:**
```python
capabilities = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'CAPABILITIES'
    }
)
```

---

### Pattern 3: Find All Components by Type

**Business Need:** Locate all MCP servers across capabilities

**Query Strategy:**
- Use GSI1: Query `GSI1PK = COMPONENT#mcp-server`
- Returns all MCP server components with their capability context

**Code Example:**
```python
mcp_servers = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'COMPONENT#mcp-server'
    }
)
```

---

### Pattern 4: Get Capabilities by Business Domain

**Business Need:** View all capabilities in "operations" domain

**Query Strategy:**
- Use GSI1: Query `GSI1PK = DOMAIN#operations`
- Returns capabilities grouped by business domain

**Code Example:**
```python
operations_capabilities = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'DOMAIN#operations'
    }
)
```

---

### Pattern 5: Monitor Component Health

**Business Need:** Get current health metrics for all components

**Query Strategy:**
- Query recent metrics: `PK = CAPABILITY#{id}` AND `SK begins_with METRIC#`
- Filter by timestamp for current values

**Code Example:**
```python
# Get metrics from last hour
current_time = datetime.utcnow()
one_hour_ago = current_time - timedelta(hours=1)

metrics = table.query(
    KeyConditionExpression='PK = :pk AND SK BETWEEN :start AND :end',
    ExpressionAttributeValues={
        ':pk': 'CAPABILITY#CAP-ALERT-MGT-001',
        ':start': f'METRIC#',
        ':end': f'METRIC#{current_time.isoformat()}Z'
    }
)
```

---

### Pattern 6: Track Deployment History

**Business Need:** View all deployments for a capability

**Query Strategy:**
- Query jobs: `PK = CAPABILITY#{id}` AND `SK begins_with JOB#`
- Results naturally sorted by timestamp

**Code Example:**
```python
deployment_history = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'CAPABILITY#CAP-ALERT-MGT-001',
        ':sk': 'JOB#'
    },
    ScanIndexForward=False,  # Newest first
    Limit=20  # Last 20 deployments
)
```

---

## Hybrid Storage Architecture

Similar to the Transformation Journey system, the Business Capability Catalogue uses a **hybrid storage pattern** for large artifacts:

### Storage Decision Matrix

| Data Type | Primary Storage | Secondary Storage | Reason |
|-----------|----------------|-------------------|---------|
| **Capability Metadata** | DynamoDB | - | Fast queries, frequent updates, small size |
| **Component Definitions** | DynamoDB | - | Indexed access, relationship queries |
| **Dependencies** | DynamoDB | - | Graph queries, fast traversal |
| **Implementation Jobs** | DynamoDB | S3 (artifacts) | Status in DB, logs/reports in S3 |
| **Performance Metrics** | DynamoDB | S3 (historical) | Recent in DB, archives in S3 |
| **Configuration Rules** | DynamoDB | - | Fast evaluation, version control |

### S3 Storage Patterns

**Deployment Artifacts:**
```
s3://capability-deployments/
└── capabilities/
    └── {capability_id}/
        └── jobs/
            └── {job_id}/
                ├── deployment-plan.yaml
                ├── logs/
                │   ├── pre-deployment.log
                │   ├── deployment.log
                │   └── post-deployment.log
                └── reports/
                    ├── test-results.json
                    └── performance-baseline.json
```

**Historical Metrics:**
```
s3://capability-metrics/
└── capabilities/
    └── {capability_id}/
        └── components/
            └── {component_id}/
                └── {year}/{month}/{day}/
                    └── metrics-{hour}.json.gz
```

---

## Performance Considerations

### Partition Design

**Hot Partitions:** 
- Each capability gets its own partition (PK = CAPABILITY#{id})
- Active capabilities with many components stay on single partition
- DynamoDB automatically handles partition scaling

**Cold Partitions:**
- Deprecated capabilities accessed infrequently
- Historical metrics moved to S3 after TTL
- No performance impact on active capabilities

### Query Efficiency

**Single Partition Queries (Fastest):**
```python
# Get capability metadata: ~5ms
table.get_item(Key={'PK': 'CAPABILITY#ABC', 'SK': 'METADATA'})

# Get all components: ~10ms
table.query(KeyCondition='PK = :pk AND begins_with(SK, COMPONENT#)')
```

**GSI Queries (Fast):**
```python
# List all capabilities: ~20ms
table.query(IndexName='GSI1', KeyCondition='GSI1PK = CAPABILITIES')

# Find component type: ~15ms
table.query(IndexName='GSI1', KeyCondition='GSI1PK = COMPONENT#api-server')
```

### Data Size Optimization

**Item Size Estimates:**
- Capability metadata: ~5-10 KB ✅
- Component definition: ~3-5 KB ✅
- Dependency: ~1-2 KB ✅
- Job execution: ~5-10 KB ✅
- Performance metric: ~1-2 KB ✅
- Configuration rule: ~2-3 KB ✅

**TTL Strategy:**
- Metrics: 90 days (moved to S3)
- Jobs: Retained indefinitely
- Rules: Version history maintained

---

## Cost Optimization

### Read Cost Comparison

**Single Query to Get Capability:**
- Get metadata: 1 RCU
- Get 8 components: 2 RCUs
- Get 15 dependencies: 2 RCUs
- Get 10 active rules: 1 RCU
- **Total: ~6 RCUs**

**Traditional Multi-Table Design:**
- Get capability: 1 RCU
- Get 8 components: 8 RCUs
- Get 15 dependencies: 15 RCUs
- Get 10 rules: 10 RCUs
- **Total: 34 RCUs** ❌

**Savings: 82% fewer read costs!** ✅

### Storage Cost Optimization

**DynamoDB:**
- Active data only (metadata, configs, recent metrics)
- ~50KB per capability average
- Fast access for operational queries

**S3:**
- Historical metrics: $0.023/GB/month
- Deployment artifacts: $0.023/GB/month
- Lifecycle policies for archival

---

## Security and Access Control

### Encryption

**At Rest:** 
- DynamoDB: AWS KMS encryption
- S3: SSE-S3 or SSE-KMS

**In Transit:** TLS 1.2+

### IAM Policies

**Read-Only Access (Operators):**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Query",
    "s3:GetObject"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/BusinessCapabilitySystem",
    "arn:aws:s3:::capability-*/*"
  ]
}
```

**Component Management (DevOps):**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:Query",
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/BusinessCapabilitySystem",
    "arn:aws:s3:::capability-*/*"
  ]
}
```

---

## Monitoring and Observability

### CloudWatch Metrics

**DynamoDB Metrics:**
- ConsumedReadCapacityUnits
- ConsumedWriteCapacityUnits
- UserErrors
- SystemErrors
- ConditionalCheckFailedRequests

**Application Metrics:**
- Capability health scores
- Component availability
- Deployment success rates
- Rule execution performance
- Dependency failure rates

### Dashboards

**Capability Overview:**
```python
# Aggregated metrics from capability metadata
health_scores = []
for capability in capabilities:
    health_scores.append({
        'capability': capability['Data']['name'],
        'health': capability['Data']['aggregates']['healthScore'],
        'components': capability['Data']['aggregates']['totalComponents'],
        'incidents': capability['Data']['aggregates']['totalIncidents']
    })
```

---

## Best Practices

### 1. Use Composite Keys for Rich Queries

✅ **Good:**
```python
# Components ordered by criticality
SK = 'COMPONENT#01#database-alert-001'  # Critical
SK = 'COMPONENT#02#api-server-alert-001' # Important
SK = 'COMPONENT#03#ui-dashboard-alert-001' # Standard
```

### 2. Implement Proper TTL for Metrics

✅ **Good:**
```python
# Set TTL for metrics older than 90 days
item['TTL'] = int((datetime.utcnow() + timedelta(days=90)).timestamp())
```

### 3. Use Batch Operations for Related Writes

✅ **Good:**
```python
# Update capability and components atomically
with table.batch_writer() as batch:
    batch.put_item(Item=capability_metadata)
    for component in components:
        batch.put_item(Item=component)
```

### 4. Design for Query Patterns

✅ **Good:**
```python
# GSI1 enables finding all API servers
GSI1PK = 'COMPONENT#api-server'
GSI1SK = 'CAP-ALERT-MGT-001#api-server-alert-001'
```

### 5. Monitor Partition Heat

✅ **Good:**
```python
# Distribute metrics writes across time windows
timestamp = datetime.utcnow()
timestamp = timestamp.replace(second=0, microsecond=0)  # Round to minute
```

---

## Summary

The Business Capability Catalogue uses DynamoDB's **Single Table Design** to provide:

✅ **Performance** - All capability data in one partition
✅ **Scalability** - Unlimited capabilities and components
✅ **Cost Efficiency** - 82% fewer read operations
✅ **Flexibility** - Easy to add new component types
✅ **Operational Excellence** - Real-time health monitoring
✅ **Governance** - Complete audit trail

**Key Takeaways:**
1. One table (`BusinessCapabilitySystem`) stores all data
2. Partition key (`PK`) groups by capability
3. Sort key (`SK`) identifies entity type and relationships
4. GSI enables cross-capability discovery
5. Hybrid storage optimizes costs (DynamoDB + S3)
6. Design supports complete capability lifecycle

This design enables organizations to effectively catalog, manage, and operate their business capabilities with exceptional performance and minimal operational overhead.

