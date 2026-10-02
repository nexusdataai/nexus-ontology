# Nexus Ontology

Monorepo for the Nexus platform **ontology / control plane** — combined backend (FastAPI) and frontend (React SPA), deployed via `nexus-deployer/kube-operator`.

## Layout

```
nexus-ontology/
├── backend/          # FastAPI gateway (from nexus-backend)
├── frontend/         # React + Vite UI (from nexus-ui)
├── deploy/k8s/       # Kubernetes manifests
├── scripts/          # K3s local dev helpers (port-forward, postgres init)
├── VERSION           # Repo-level semver
└── Makefile          # Dev + deploy shortcuts
```

Ontology is a remote-only consumer of **nexus-simulator**. Set `SIMULATOR_BASE_URL` (in-cluster DNS) and `SIMULATOR_UI_URL` (browser deep-link; `http://localhost:8082` on local). There is no in-process simulator fallback.

## Local development (simple)

```bash
# Backend
cd backend && pip install -r requirements.txt
python mcp_http_gateway.py

# Frontend
cd frontend && npm ci && npm run dev
```

## K3s-backed local dev (recommended)

Run backend and frontend on the host with hot reload, connected to the K3s local stack (Scylla/MiniStack/MinIO/Redis + operator-managed Postgres/Mimir). No Docker image rebuild for app code changes.

### Prerequisites

1. K3s cluster and local AWS stack (from `nexus-deployer`):

```bash
cd ../nexus-deployer/aws-login && ./set-context.sh 6
cd ../nexus-deployer/kube-operator
./operator.sh deploy
cd ../local-k3s
./deploy-local-aws-stack.sh --kube-context local-cluster
./tests/verify-local-stack.sh --kube-context local-cluster
./tests/verify-local-boto3-apis.sh --kube-context local-cluster
```

2. Deploy ontology dev dependencies (postgres + Mimir only; no app pods):

```bash
# Required — use local K3s kubeconfig (not default ~/.kube EKS contexts)
source ../aws-login/.active-env
# Or: export KUBECONFIG=/path/to/nexus-deployer/aws-login/.kube/config

kubectl --context local-cluster apply -f examples/nexus-ontology-local-dev-deps.yaml
kubectl --context local-cluster wait -n ontology-local statefulset/pgvector --for=condition=ready --timeout=300s
```

If you see `the server has asked for the client to provide credentials`, kubectl is pointed at EKS instead of local K3s — run `source ../aws-login/.active-env` or `./set-context.sh 6` first.

3. Initialize postgres extensions (pgvector tables; AGE if image supports it):

```bash
cd ../../nexus-ontology
./scripts/init-postgres-extensions.sh
```

### Daily workflow

```bash
# Terminal 1 — port-forwards (auto-started by make dev-backend if missing)
make port-forward-k3s

# Terminal 2 — backend (ensures K3s port-forwards + verifies DDB/MiniStack/MinIO/Redis)
cp backend/.env.local.k3s.example backend/.env.local   # once
make dev-backend   # uses .venv + unsets AWS_PROFILE

# Or manually (do not use system python3 — needs venv + mcp package):
#   cd backend && unset AWS_PROFILE && source .venv/bin/activate && python mcp_http_gateway.py

# Terminal 3 — frontend
cp frontend/.env.local.k3s.example frontend/.env.local   # once
make dev-frontend
```

| Service | Host endpoint |
|---------|---------------|
| Backend API | http://localhost:8000 |
| Frontend UI | http://localhost:8080 |
| DynamoDB (Scylla) | http://127.0.0.1:8001 |
| Athena/Glue (MiniStack) | http://127.0.0.1:4566 |
| S3 (MinIO) | http://127.0.0.1:9000 |
| Redis | redis://127.0.0.1:6379 |
| Postgres | 127.0.0.1:5432 |
| Mimir | http://127.0.0.1:9090 |

Stop port-forwards: `./scripts/stop-port-forward-k3s-dev.sh`

**Important:** Do not reuse `backend/.env.local` for K3s dev — it may point at prod tables. Use `backend/.env.local.k3s.example` (`CAPABILITY_NAME=ontology`, `ENVIRONMENT=local`).

**Frontend + backend:** Start the backend first (`make dev-backend`), then the frontend (`make dev-frontend`). The frontend needs `http://localhost:8000` reachable. `make dev-frontend-setup` copies `public/config.local.json` → `public/config.json` and `.env.local.k3s.example` → `.env.local` if missing.

**Resource naming:** DynamoDB tables and most AWS resources follow `{capability}-{environment}-{purpose}`. Local K3s uses `ENVIRONMENT=local` (e.g. `ontology-local-foundry-workspace`); remote K8 uses `dev`/`prod` (e.g. `ontology-dev-foundry-workspace`). Set only `CAPABILITY_NAME` and `ENVIRONMENT` — do not hardcode table names unless overriding a single resource. The local init job (`make init-k3s-local-aws`) creates the same names Scylla-side.

### Apache AGE (optional, full graph RAG)

The default `pgvector/pgvector:pg16` image supports vector search; `GraphStore` falls back to metadata-based graph expansion without AGE. For full Cypher graph traversal, use a postgres image with Apache AGE (e.g. `nexus-sre-postgres`) in `nexus-ontology-local-dev-deps.yaml`, then re-run `./scripts/init-postgres-extensions.sh`.

## Deploy (kube-operator)

```bash
cd ../nexus-deployer/kube-operator
./bump-version.sh ontology-all patch --ontology-dir ../../nexus-ontology
./package-images.sh --only-ontology-images --ontology-dir ../../nexus-ontology
./create-ecr-images.sh --only-ontology-images
./app-rollout.sh --capability ontology --env dev --version <tag> ontology-all
```

Or from this repo:

```bash
make deploy-dev
```

## Images

| Component | ECR repository | K8s deployment |
|-----------|----------------|----------------|
| API | `nexus-ontology-api` | `nexus-ontology` |
| UI | `nexus-ontology-ui` | `nexus-ontology-ui` |

Namespace: `ontology-{env}` (e.g. `ontology-dev`, `ontology-prod`).
