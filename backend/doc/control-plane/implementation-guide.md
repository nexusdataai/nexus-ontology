# AI Data Plane & Control Plane — Implementation Guide

This document describes the complete implementation of the AI Data Plane and AI Control Plane as deployed in the Nexus Telco CallSense platform. It maps the reference architecture (see `architecture.md` and `Total-system-architecture.md`) to actual code, APIs, infrastructure, and testing procedures.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND (nexus-ui)                                              │
│  /copilot → CopilotPage.tsx → POST /api/v1/control-plane/agent     │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  AI CONTROL PLANE (nexus-backend)                                 │
│                                                                     │
│  ┌─ Intent Analyzer ──────────────────────────────────────────────┐ │
│  │  Classifies: read_only | low_risk_write | high_risk_write      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌─ ReAct Agent Loop (max 10 steps) ─────────────────────────────┐ │
│  │  LLM (gpt-4o-mini) + 6 tools + policy enforcement             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌─ Enterprise RAG Layer ─────────────────────────────────────────┐ │
│  │  pgvector (1662 embeddings) + text-embedding-3-small           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌─ Policy & Guardrail Core ─────────────────────────────────────┐ │
│  │  Risk gates, step budget, field restrictions, loop detection   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌─ Audit Logger ─────────────────────────────────────────────────┐ │
│  │  DynamoDB: every tool call, violation, session logged          │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  AI DATA PLANE (nexus-backend + BSSMagic)                         │
│                                                                     │
│  ┌─ FDW Path ────────────────────────────────────────────────────┐  │
│  │  PostgreSQL 17 + Multicorn FDW → Salesforce (1661 tables)     │  │
│  │  Schema: sfdc_itxp2dev                                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌─ CRM Path ────────────────────────────────────────────────────┐  │
│  │  BSSMagic TMF API → Salesforce writes (Lead creation, SOQL)   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. AI Data Plane

The Data Plane provides virtualized read/write access to enterprise source systems (Salesforce) without data replication.

### 2.1 Infrastructure

| Component | Technology | Location |
|-----------|-----------|----------|
| Database | PostgreSQL 17 (Debian) | EKS pod `call-processing-prod-bssmagic-0` |
| FDW Extension | Multicorn (Python FDW) | Pre-installed in BSSMagic image |
| Vector Extension | pgvector 0.8.1 | Installed at runtime |
| Foreign Server | `sfdc_itxp2dev` | Points to Salesforce sandbox |
| Foreign Tables | 1,661 tables | Maps to Salesforce objects |
| CRM Runtime | BSSMagic TMF API (port 8000) | Same pod as PostgreSQL |

### 2.2 Source Files

| File | Class/Module | Purpose |
|------|-------------|---------|
| `src/config/fdw_config.py` | `FDWConfig` | Environment-based configuration |
| `src/services/fdw_connection_manager.py` | `PostgreSQLConnectionManager` | SQLAlchemy connection pool with async wrapper |
| `src/services/fdw_discovery_service.py` | `FDWDiscoveryService` | Introspects foreign servers, tables, columns |
| `src/services/fdw_query_service.py` | `FDWQueryService` | Parameterized query builder with whitelist validation |
| `src/services/bssmagic_crm_service.py` | `BSSMagicCRMService` | Salesforce CRM operations via TMF API |
| `src/services/data_plane_service.py` | `DataPlaneService` | CRUD for data plane configurations (DynamoDB) |
| `src/models/fdw_models.py` | Various | Pydantic models for all FDW payloads |
| `src/apis/fdw_api.py` | FastAPI router | REST endpoints for FDW operations |
| `src/fdw_lifecycle.py` | — | Startup/shutdown lifecycle management |

### 2.3 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FDW_PG_HOST` | Yes (to enable) | — | PostgreSQL host. When set, FDW is enabled |
| `FDW_PG_PORT` | No | `5432` | PostgreSQL port |
| `FDW_PG_DATABASE` | Yes | — | Database name |
| `FDW_PG_USER` | Yes | — | Database user |
| `FDW_PG_PASSWORD` | Yes | — | Database password |
| `FDW_PG_SCHEMA` | No | `public` | Default schema |
| `FDW_PG_SSL_MODE` | No | `prefer` | SSL mode |
| `FDW_PG_POOL_MIN` | No | `2` | Minimum pool connections |
| `FDW_PG_POOL_MAX` | No | `10` | Maximum pool connections |
| `FDW_PG_QUERY_TIMEOUT` | No | `30` | Query timeout in seconds |

**Current production values:**
```
FDW_PG_HOST=call-processing-prod-bssmagic-svc
FDW_PG_PORT=5432
FDW_PG_DATABASE=bssmagic
FDW_PG_USER=postgres
FDW_PG_PASSWORD=admin
FDW_PG_SCHEMA=public
```

### 2.4 FDW REST API Endpoints

Base path: `/api/fdw`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/fdw/servers` | List all foreign servers |
| GET | `/api/fdw/tables?server=name` | List foreign tables (optional server filter) |
| GET | `/api/fdw/tables/{schema}/{table}/columns` | Get column metadata |
| POST | `/api/fdw/query` | Execute parameterized query |
| GET | `/api/fdw/tmf/standards` | List TMF spec standards |
| GET | `/api/fdw/tmf/types` | Get TMF type definitions |

**Query request example:**
```json
{
  "table": "Lead",
  "schemaName": "sfdc_itxp2dev",
  "columns": ["Id", "Name", "Company", "Email"],
  "filters": [
    {"column": "Company", "operator": "like", "value": "%Networks%"}
  ],
  "orderBy": [{"column": "Name", "direction": "asc"}],
  "limit": 10
}
```

**Supported filter operators:** `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `like`, `in`

### 2.5 BSSMagic CRM Operations

| Operation | Endpoint | Risk |
|-----------|----------|------|
| Create Lead | `POST /tmf-api/salesLead` | Write |
| Query Leads | `POST /query` (SOQL) | Read |
| Query Products | `POST /query` (SOQL) | Read |
| Query Pricing | `POST /query` (SOQL) | Read |
| Upload File | `POST /tmf-api/contentVersion` | Write |
| Link File | `POST /tmf-api/contentDocumentLink` | Write |
| RecordType Lookup | `POST /query` (SOQL) | Read |

### 2.6 Testing the Data Plane

**From a backend pod:**
```bash
# List foreign servers
curl -s http://localhost:8000/api/fdw/servers | python3 -m json.tool

# List foreign tables (first 5)
curl -s http://localhost:8000/api/fdw/tables | python3 -c "import sys,json; [print(t['tableName']) for t in json.load(sys.stdin)[:5]]"

# Get columns for Lead table
curl -s http://localhost:8000/api/fdw/tables/sfdc_itxp2dev/Lead/columns | python3 -m json.tool

# Query Leads
curl -s -X POST http://localhost:8000/api/fdw/query \
  -H 'Content-Type: application/json' \
  -d '{"table":"Lead","schemaName":"sfdc_itxp2dev","columns":["Name","Company"],"limit":5}'

# Health check
curl -s http://localhost:8000/api/v1/health/fdw
```

**Via kubectl:**
```bash
POD=$(kubectl get pods -n call-processing-prod -l app=call-processing-prod-backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -n call-processing-prod -- curl -s http://localhost:8000/api/fdw/servers
```

---

## 3. AI Control Plane

The Control Plane provides semantic intelligence, agent-based reasoning, and policy-enforced tool execution on top of the Data Plane.

### 3.1 Source Files

| File | Class/Module | Purpose |
|------|-------------|---------|
| `src/services/control_plane/embedding_service.py` | `EmbeddingService` | OpenAI text-embedding-3-small (1536 dims) |
| `src/services/control_plane/vector_store.py` | `VectorStore` | pgvector CRUD + cosine similarity search |
| `src/services/control_plane/schema_indexer.py` | `SchemaIndexer` | FDW Discovery → embeddings → pgvector |
| `src/services/control_plane/llm_client.py` | `LLMClient` | OpenAI gpt-4o-mini chat completions |
| `src/services/control_plane/rag_service.py` | `RAGService` | Vector retrieval + context builder + LLM |
| `src/services/control_plane/tool_registry.py` | `ToolRegistry` | Central registry with OpenAI function-calling format |
| `src/services/control_plane/tools/fdw_tools.py` | — | discover_tables, discover_columns, query_table |
| `src/services/control_plane/tools/rag_tools.py` | — | search_schema_knowledge |
| `src/services/control_plane/tools/crm_tools.py` | — | create_salesforce_lead, soql_query |
| `src/services/control_plane/agent_executor.py` | `AgentExecutor` | ReAct loop: PLAN → EXECUTE → OBSERVE |
| `src/services/control_plane/policy_engine.py` | `PolicyEngine` | Pre-execution validation + guardrails |
| `src/services/control_plane/audit_logger.py` | `AuditLogger` | DynamoDB audit trail |
| `src/services/control_plane/intent_analyzer.py` | `analyze_intent()` | LLM + heuristic intent classification |
| `src/apis/control_plane_api.py` | FastAPI router | REST endpoints for all control plane operations |

### 3.2 Intelligence Store (pgvector)

**Database:** BSSMagic PostgreSQL (same instance as FDW)

**Extension:** pgvector 0.8.1

**Table:** `control_plane_embeddings`
```sql
CREATE TABLE control_plane_embeddings (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,       -- fdw_table, fdw_server, tmf_spec
    source_id VARCHAR(255) NOT NULL,         -- e.g. sfdc_itxp2dev.Lead
    content TEXT NOT NULL,                    -- Natural language description
    metadata JSONB DEFAULT '{}',             -- Structured column/table metadata
    embedding vector(1536),                  -- OpenAI text-embedding-3-small
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_type, source_id)
);
```

**Indexes:**
- `idx_cpe_content_type` — B-tree on content_type
- `idx_cpe_embedding` — IVFFlat on embedding (cosine distance)

**Current contents:**
| content_type | count | Description |
|-------------|-------|-------------|
| fdw_server | 1 | sfdc_itxp2dev (Multicorn wrapper) |
| fdw_table | 1,661 | All Salesforce objects with column metadata |
| tmf_spec | 0 | (available for future indexing) |
| **Total** | **1,662** | |

### 3.3 Registered Tools

| Tool Name | Risk Level | Approval | Description |
|-----------|-----------|----------|-------------|
| `search_schema_knowledge` | read_only | No | Semantic search over 1662 schema embeddings |
| `discover_tables` | read_only | No | List/filter foreign tables by name pattern |
| `discover_columns` | read_only | No | Get column metadata for a specific table |
| `query_table` | read_only | No | Parameterized SELECT via FDW (max 100 rows) |
| `soql_query` | read_only | No | Direct SOQL via BSSMagic /query endpoint |
| `create_salesforce_lead` | high_risk_write | **Yes** | Create Lead in Salesforce via BSSMagic TMF API |

### 3.4 Policy Rules

| Rule | Enforcement | Configuration |
|------|------------|---------------|
| Risk gating | Tools filtered by intent risk level | `read_only` → only read tools; `high_risk_write` → all tools |
| Step budget | Max steps per agent run | Default: 10, configurable per request |
| Write limit | Max write actions per session | Default: 3 |
| Approval gate | High-risk writes require explicit approval | `create_salesforce_lead` requires approval |
| Field restriction | Blocks access to sensitive columns | `OwnerId`, `CreatedById`, `SystemModstamp`, `IsDeleted` |
| Loop detection | Blocks repeated identical tool calls | Threshold: 2 identical calls in last 5 |

### 3.5 Intent Classification

| Intent | Trigger | Tools Available |
|--------|---------|-----------------|
| `read_only` | Querying, searching, listing, inspecting | All read tools (5) |
| `low_risk_write` | Creating notes, updating descriptions | Read + low-risk write tools |
| `high_risk_write` | Financial changes, record creation/deletion | All tools (6) |
| `cross_system` | Operations spanning multiple systems | All tools (6) |

**Classification method:** LLM-based (gpt-4o-mini, temperature=0.0) with keyword heuristic fallback.

### 3.6 Control Plane REST API Endpoints

Base path: `/api/v1/control-plane`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/control-plane/search` | Semantic vector search over embeddings | Session cookie |
| POST | `/api/v1/control-plane/ask` | RAG Q&A (single LLM call with context) | Session cookie |
| POST | `/api/v1/control-plane/agent` | ReAct agent with multi-step tool use | Session cookie |
| POST | `/api/v1/control-plane/index` | Trigger schema re-indexing | Session cookie |
| GET | `/api/v1/control-plane/stats` | Embedding counts and status | Session cookie |
| GET | `/api/v1/control-plane/tools` | List registered tools with risk levels | Session cookie |

**Agent request example:**
```json
{
  "question": "Show me the first 5 Leads with their name and company",
  "max_steps": 10
}
```

**Agent response example:**
```json
{
  "answer": "Here are the first 5 Leads...",
  "intent": "read_only",
  "session_id": "bf9872fb-60d7-4f40-b...",
  "steps": [
    {"step": 1, "tool": "discover_tables", "duration_ms": 83.8},
    {"step": 2, "tool": "discover_columns", "duration_ms": 9.6},
    {"step": 3, "tool": "query_table", "duration_ms": 1447.1},
    {"step": 4, "action": "final_answer"}
  ],
  "total_steps": 4,
  "total_tokens": 9130,
  "policy_violations": []
}
```

### 3.7 Testing the Control Plane

**Stats (verify indexing):**
```bash
curl -s http://localhost:8000/api/v1/control-plane/stats
# Expected: {"total_embeddings":1662,"fdw_servers":1,"fdw_tables":1661,...,"embedding_available":true}
```

**Re-index schemas:**
```bash
curl -s -X POST http://localhost:8000/api/v1/control-plane/index
# Expected: {"status":"ok","indexed":{"servers":1,"tables":1661,"errors":0}}
```

**List tools:**
```bash
curl -s http://localhost:8000/api/v1/control-plane/tools
# Expected: 6 tools with risk levels
```

**Semantic search:**
```bash
curl -s -X POST http://localhost:8000/api/v1/control-plane/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "customer account credit limit", "limit": 5}'
```

**RAG Q&A:**
```bash
curl -s -X POST http://localhost:8000/api/v1/control-plane/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "What tables store product pricing information?"}'
```

**Agent (full ReAct loop):**
```bash
curl -s -X POST http://localhost:8000/api/v1/control-plane/agent \
  -H 'Content-Type: application/json' \
  -d '{"question": "Show me the first 3 Leads with their name and company"}'
```

**Via kubectl:**
```bash
POD=$(kubectl get pods -n call-processing-prod -l app=call-processing-prod-backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -n call-processing-prod -- curl -s -X POST http://localhost:8000/api/v1/control-plane/agent \
  -H 'Content-Type: application/json' \
  -d '{"question": "What columns does the Account table have?"}'
```

---

## 4. Frontend: AI Copilot

### 4.1 Source Files

| File | Description |
|------|-------------|
| `nexus-ui/src/pages/CopilotPage.tsx` | Full chat interface component |
| `nexus-ui/src/App.tsx` | Route: `/copilot` |
| `nexus-ui/src/components/Sidebar.tsx` | Navigation item: "AI Copilot" (Sparkles icon) |

### 4.2 Accessing the Copilot

1. Navigate to the application URL
2. Log in with valid credentials
3. Click the **Sparkles icon** ("AI Copilot") in the left sidebar
4. Or navigate directly to `/copilot`

### 4.3 UI Features

- **Chat interface** — Send natural language questions, receive agent-powered answers
- **Example questions** — Pre-populated quick-start buttons on empty state
- **Intent badge** — Color-coded per response: green (read_only), yellow (low_risk_write), red (high_risk_write), purple (cross_system)
- **Step trace** — Expandable panel showing every tool call, duration, and result preview
- **Token counter** — Shows total tokens consumed per query
- **Policy violations** — Red badge when guardrails block an action
- **Loading state** — Spinner while agent processes (timeout: 120s)

### 4.4 API Integration

The Copilot sends requests to:
```
POST /api/v1/control-plane/agent
Content-Type: application/json
Body: { "question": "...", "max_steps": 10 }
Timeout: 120000ms
```

Authentication is handled via session cookies (same as all other API calls).

---

## 5. Infrastructure & Deployment

### 5.1 EKS Pods

| Pod | Replicas | Contains |
|-----|----------|----------|
| `call-processing-prod-backend` | 3 | FastAPI gateway + Control Plane APIs |
| `call-processing-prod-frontend` | 3 | Nginx + React SPA (Copilot UI) |
| `call-processing-prod-bssmagic` | 1 (StatefulSet) | PostgreSQL 17 + pgvector + Multicorn FDW + BSSMagic runtime |

### 5.2 External Dependencies

| Service | Usage | Credentials |
|---------|-------|-------------|
| OpenAI API | Embeddings (text-embedding-3-small) + Chat (gpt-4o-mini) | AWS Secrets Manager: `call-processing/prod/openai` |
| AWS DynamoDB | Audit logs (`control-plane-audit`), Data plane configs | IAM role attached to EKS |
| Salesforce | Source system accessed via FDW + BSSMagic | Configured in BSSMagic pod |

### 5.3 Deploying Changes

```bash
cd /opt/mycode/trilogy/nexus-deployer/kube-operator
./deploy-app-changes.sh
```

This script:
1. Builds backend Docker image (`ai-job-engine`)
2. Builds frontend Docker image (`nexus-ui`)
3. Pushes both to ECR
4. Restarts backend and frontend pods
5. Waits for all pods to be ready

### 5.4 Re-indexing After Schema Changes

If Salesforce objects change, re-index the vector store:
```bash
curl -X POST https://<host>/api/v1/control-plane/index
```

This re-reads all foreign tables from the FDW discovery cache, generates new embeddings, and upserts them into pgvector. Takes approximately 40 seconds for 1661 tables.

**Note:** pgvector is installed at runtime in the BSSMagic pod. If the pod restarts, pgvector must be reinstalled:
```bash
kubectl exec call-processing-prod-bssmagic-0 -n call-processing-prod -c bssmagic-runtime -- \
  bash -c "apt-get update -qq && apt-get install -y -qq postgresql-17-pgvector"
kubectl exec call-processing-prod-bssmagic-0 -n call-processing-prod -c bssmagic-runtime -- \
  psql -U postgres -d bssmagic -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Then re-index via the API.

---

## 6. Architecture Mapping

How the implementation maps to the reference architecture in `architecture.md`:

| Architecture Layer | Implementation | Status |
|-------------------|---------------|--------|
| **User Interface** (Chat / API / Copilot) | `CopilotPage.tsx` at `/copilot` | Deployed |
| **Identity & RBAC Layer** | Cognito SSO + session cookies + role-based access | Deployed |
| **Intent + Risk Analyzer** | `intent_analyzer.py` (LLM + heuristic classification) | Deployed |
| **Enterprise RAG Layer** | `rag_service.py` + `vector_store.py` (pgvector, 1662 embeddings) | Deployed |
| **ReAct Planning Engine** | `agent_executor.py` (PLAN→EXECUTE→OBSERVE loop, max 10 steps) | Deployed |
| **Policy & Guardrail Core** | `policy_engine.py` (risk gates, step budget, field restrictions) | Deployed |
| **Tool Abstraction Layer** | `tool_registry.py` + 6 tools (FDW + RAG + CRM) | Deployed |
| **Audit Logging** | `audit_logger.py` (DynamoDB `control-plane-audit`) | Deployed |
| **AI-DATA-PLANE: FDW Path** | `fdw_discovery_service.py` + `fdw_query_service.py` (Multicorn FDW → Salesforce) | Deployed |
| **AI-DATA-PLANE: CRM Path** | `bssmagic_crm_service.py` (TMF API → Salesforce writes) | Deployed |
| **Intelligence Layer: Vector DB** | pgvector 0.8.1 in BSSMagic PostgreSQL | Deployed |
| **Intelligence Layer: Graph DB** | Not yet implemented (planned: Neo4j/Neptune for ontology) | Planned |
| **AI-DATA-PLANE: CDC Path** | Not yet implemented (planned: Debezium/Kafka) | Planned |
| **AI-DATA-PLANE: ETL Path** | Not yet implemented (planned: Spark/Airflow) | Planned |
