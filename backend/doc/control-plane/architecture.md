 # Broad Level System
 
                         ┌─────────────────────────┐
                         │       User Interface     │
                         │  (Chat / API / Copilot)  │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │ Identity & RBAC Layer   │
                         │ (SSO, OAuth, SCIM)      │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │ Intent + Risk Analyzer  │
                         │ (LLM or small model)    │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │ Enterprise RAG Layer    │
                         │ (Metadata + Policies)   │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │ ReAct Planning Engine   │
                         │ (LLM Agent Loop)        │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │ Policy & Guardrail Core │
                         │ (OPA / Custom Engine)   │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │ Tool Abstraction Layer  │
                         │ (Controlled APIs)       │
                         └────────────┬────────────┘
                                      ↓
         ┌──────────────────────┬────────────────────────┐
         ↓                      ↓                        ↓
┌────────────────┐     ┌────────────────┐        ┌────────────────┐
│ Salesforce API │     │ Oracle ERP API │        │ Other Systems  │
└────────────────┘     └────────────────┘        └────────────────┘

# Overall Flow

┌──────────────────────┐
│     User Interface    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Intent + Risk Class. │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Enterprise RAG Layer │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  ReAct LLM Planner   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Tool Control Layer   │
│ (Guardrails + Policy)│
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ System Adapters      │
│ SF | Oracle | SAP    │
└──────────────────────┘

# Total System Architecture

                         ┌────────────────────────────┐
                         │       User Interface         │
                         │  (Chat / API / Copilot)      │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │  Identity & RBAC Layer      │
                         │  (SSO, OAuth, SCIM)         │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │  Intent + Risk Analyzer     │
                         │  (Classifies: read-only,    │
                         │   low-risk write, high-risk │
                         │   write, cross-system)      │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
         ┌───────────────────────────────────────────────────────────────┐
         │              ReAct Planning Engine (LLM Agent Loop)           │
         │                                                               │
         │  PLAN → EXECUTE → OBSERVE → REPLAN → EXECUTE → OBSERVE       │
         │                                                               │
         │  1. Receives user intent + risk classification                │
         │  2. Queries Enterprise RAG for context ──────────────┐       │
         │  3. Reasons about next action                         │       │
         │  4. Selects tool from Tool Abstraction Layer          │       │
         │  5. Policy Engine validates before execution          │       │
         │  6. Observes result, replans if needed                │       │
         │  7. Loops until goal achieved or step limit reached   │       │
         │                                                       │       │
         │  ┌────────────────────────────────────────────────┐   │       │
         │  │  AI Applications (powered by this loop)        │   │       │
         │  │  - Fraud AI Assistant                          │   │       │
         │  │  - AML Investigator Copilot                    │   │       │
         │  │  - Risk Analytics Dashboard                    │   │       │
         │  │  - Enterprise System Orchestrator              │   │       │
         │  └────────────────────────────────────────────────┘   │       │
         │                                                       │       │
         │  ┌────────────────────────────────────────────────┐   │       │
         │  │  Policy & Guardrail Core                       │   │       │
         │  │  (OPA / Custom Engine)                         │   │       │
         │  │  - Approval thresholds  - Close windows        │   │       │
         │  │  - Field-level access   - Cross-system checks  │   │       │
         │  │  - Risk-based routing   - Dry-run mode         │   │       │
         │  │  - Max step limits      - Audit logging        │   │       │
         │  └────────────────────────────────────────────────┘   │       │
         │                                                       │       │
         │  ┌────────────────────────────────────────────────┐   │       │
         │  │  Tool Abstraction Layer (Controlled APIs)      │   │       │
         │  │  - get_account()      - propose_credit_change()│   │       │
         │  │  - get_ar_balance()   - submit_gl_adjustment() │   │       │
         │  │  - create_customer()  - trigger_workflow()     │   │       │
         │  │  LLM never calls raw APIs — only safe tools    │   │       │
         │  └────────────────────────────────────────────────┘   │       │
         └──────────────────────┬─────────────────────────────────┘──────┘
                                │                  ▲
                                │          (RAG feedback loop)
                                ▼                  │
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │                         AI-CONTROL-PLANE                                 │
  │            (Semantic Intelligence & Reasoning Layer)                      │
  │                                                                          │
  │  ┌───────────────────────────────────────────────────────────────┐       │
  │  │              Enterprise RAG Layer                             │       │
  │  │         (Semantic Retrieval for LLM Context)                  │       │
  │  │                                                               │       │
  │  │  Retrieves from Vector DB + Graph DB to provide:              │       │
  │  │  - Schema & field definitions                                 │       │
  │  │  - Business policies & approval rules                         │       │
  │  │  - Workflow dependencies & process rules                      │       │
  │  │  - API specs & integration mappings                           │       │
  │  │  - Cross-system dependency awareness                          │       │
  │  │                                                               │       │
  │  │  Answers: "Which object stores credit risk?"                  │       │
  │  │           "What triggers approval workflow?"                  │       │
  │  │           "What fields are required for customer creation?"   │       │
  │  │           "What is the ERP sync dependency?"                  │       │
  │  │                                                               │       │
  │  │  This is semantic retrieval, not relational querying.         │       │
  │  └──────────────────────┬────────────────────────────────────────┘       │
  │                         │                                                │
  │              ┌──────────┼──────────────────────┐                         │
  │              │          │                      │                         │
  │      ┌──────────────┐ ┌──────────────┐  ┌──────────────┐                │
  │      │  Graph Query │ │ Vector Search│  │  ML Scoring  │                │
  │      │  + Reasoner  │ │ (Similarity) │  │  Engine      │                │
  │      └──────┬───────┘ └──────┬───────┘  └──────┬───────┘                │
  │             │                │                  │                        │
  │  ┌───────────────────────────────────────────────────────────────┐       │
  │  │                 Intelligence Layer                            │       │
  │  │                                                               │       │
  │  │  ┌──────────────────┐     ┌────────────────────────────┐     │       │
  │  │  │   Graph DB       │     │       Vector DB            │     │       │
  │  │  │ (Ontology + RDF) │     │ (Embeddings Store)         │     │       │
  │  │  │                  │     │                            │     │       │
  │  │  │ Structural       │     │ Semantic Knowledge:        │     │       │
  │  │  │ Knowledge:       │     │  - Schema embeddings       │     │       │
  │  │  │  - Accounts      │     │  - Policy embeddings       │     │       │
  │  │  │  - Transactions  │     │  - Workflow embeddings     │     │       │
  │  │  │  - Customers     │     │  - API spec embeddings     │     │       │
  │  │  │  - Risk Rules    │     │  - Process rule embeddings │     │       │
  │  │  │  - Relationships │     │  - Fraud case embeddings   │     │       │
  │  │  │  - Ontology      │     │  - Customer embeddings     │     │       │
  │  │  │                  │     │                            │     │       │
  │  │  └────────┬─────────┘     └──────────┬─────────────────┘     │       │
  │  └───────────┼────────────────────────────┼───────────────────────┘       │
  │              │                            │                              │
  └──────────────┼────────────────────────────┼──────────────────────────────┘
                 │                            │
  ┌──────────────────┼────────────────────────────────┼───────────────────┐
  │                  │                                │                   │
  │                  │     AI-DATA-PLANE              │                   │
  │                  │     (Data Ingestion & Transformation)              │
  │                  │                                │                   │
  │     ┌────────────┴──────────┬─────────────────────┴────────────┐     │
  │     │                       │                                  │     │
  │     │  CDC Path             │  ETL Path              FDW Path  │     │
  │     │                       │                                  │     │
  │     ▼                       ▼                                  ▼     │
  │ ┌──────────────┐     ┌───────────────────┐      ┌───────────────────┐│
  │ │ RDF Stream   │     │ RDF Batch         │      │ FDW Wrapper       ││
  │ │ Processor    │     │ Transformer       │      │ (Virtual Access)  ││
  │ │ (CDC→Ontology│     │ (R2RML / Batch)   │      │                   ││
  │ │  Mapper)     │     │                   │      │ Postgres FDW /    ││
  │ └──────┬───────┘     └────────┬──────────┘      │ Trino / Presto    ││
  │        │                      │                  └────────┬──────────┘│
  │        ▼                      ▼                           │          │
  │ ┌──────────────┐     ┌───────────────────┐                │          │
  │ │ Kafka        │     │ ETL Engine        │                │          │
  │ │              │     │ (Spark / Airflow  │                │          │
  │ └──────┬───────┘     │  / Custom)        │                │          │
  │        │             └────────┬──────────┘                │          │
  │        ▼                      │                           │          │
  │ ┌──────────────┐              │                           │          │
  │ │ CDC Engine   │              │                           │          │
  │ │ (Debezium)   │              │                           │          │
  │ └──────┬───────┘              │                           │          │
  │        │                      │                           │          │
  │        ▼                      ▼                           ▼          │
  │ ┌─────────────────────────────────────────────────────────────────┐  │
  │ │                     Enterprise Source Systems                    │  │
  │ │                                                                 │  │
  │ │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ ┌──────────┐│  │
  │ │  │ Core Banking │  │  ERP / GL    │  │  CRM     │ │  Legacy  ││  │
  │ │  │ (Temenos /   │  │ (SAP /       │  │(Salesforce│ │ Systems  ││  │
  │ │  │  Finacle)    │  │  Oracle)     │  │ / Custom)│ │ / Files  ││  │
  │ │  └──────────────┘  └──────────────┘  └──────────┘ └──────────┘│  │
  │ │                                                                 │  │
  │ │  CDC: Real-time event streams from transaction-heavy systems    │  │
  │ │  ETL: Batch extraction for historical, analytical & master data │  │
  │ │  FDW: Virtual access for low-volume / governance-restricted data│  │
  │ └─────────────────────────────────────────────────────────────────┘  │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘

# System adapters

                +----------------------+
                |  AI & Analytics      |
                +----------------------+
                           ↑
                +----------------------+
                |  TMF API + Reasoner  |
                +----------------------+
                           ↑
                +----------------------+
                |  Semantic Layer      |
                |  (Graph DB / RDF)    |
                +----------------------+
                   ↑                ↑
             ETL Path          CDC Path
                   ↑                ↑
        R2RML / Batch        Debezium / Kafka
                   ↑                ↑
           Finance Systems (ERP / GL / AP / AR)