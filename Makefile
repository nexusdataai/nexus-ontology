# Nexus Ontology — developer entrypoints.

OPERATOR_DIR := ../nexus-deployer/kube-operator
ONTOLOGY_DIR := $(CURDIR)
NAMESPACE ?= ontology-dev
ENV ?= dev
KUBE_CONTEXT ?= local-cluster

.PHONY: deploy-dev package push rollout apply-k8s smoke port-forward-k3s stop-port-forward-k3s verify-k3s-dev ensure-k3s-dev init-k3s-local-aws dev-backend dev-backend-setup dev-frontend dev-frontend-setup init-postgres-extensions

package:
	$(OPERATOR_DIR)/package-images.sh --only-ontology-images --ontology-dir $(ONTOLOGY_DIR)

push:
	$(OPERATOR_DIR)/create-ecr-images.sh --only-ontology-images

apply-k8s:
	kubectl apply -k deploy/k8s/ -n ontology-dev --server-side || \
	kubectl apply -k deploy/k8s/

rollout:
	$(OPERATOR_DIR)/app-rollout.sh --capability ontology --env $(ENV) --namespace $(NAMESPACE) ontology-all

deploy-dev: package push apply-k8s rollout

smoke:
	kubectl exec -n $(NAMESPACE) deploy/nexus-ontology -- curl -sf http://127.0.0.1:8000/health
	kubectl exec -n $(NAMESPACE) deploy/nexus-ontology-ui -- wget -qO- --timeout=5 http://127.0.0.1:8080/ >/dev/null

port-forward-k3s:
	./scripts/port-forward-k3s-dev.sh --kube-context $(KUBE_CONTEXT)

stop-port-forward-k3s:
	./scripts/stop-port-forward-k3s-dev.sh

verify-k3s-dev:
	./scripts/verify-k3s-dev-services.sh

ensure-k3s-dev:
	./scripts/ensure-k3s-dev-port-forwards.sh --kube-context $(KUBE_CONTEXT)

init-postgres-extensions:
	./scripts/init-postgres-extensions.sh --kube-context $(KUBE_CONTEXT)

init-k3s-local-aws: ensure-k3s-dev
	unset AWS_PROFILE AWS_DEFAULT_PROFILE; \
	AWS_ACCESS_KEY_ID=minioadmin AWS_SECRET_ACCESS_KEY=minioadmin \
	python3 $(OPERATOR_DIR)/scripts/local_init_aws.py \
	  --capabilities ontology \
	  --environment local \
	  --scylla-endpoint http://127.0.0.1:8001 \
	  --minio-endpoint http://127.0.0.1:9000 \
	  --ministack-endpoint http://127.0.0.1:4566

dev-backend-setup:
	@test -f backend/.env.local || cp backend/.env.local.k3s.example backend/.env.local
	cd backend && python -m venv .venv 2>/dev/null || true
	cd backend && . .venv/bin/activate && pip install -q -r requirements.txt

dev-backend: dev-backend-setup ensure-k3s-dev
	@./scripts/init-postgres-extensions.sh --kube-context $(KUBE_CONTEXT) || true
	cd backend && unset AWS_PROFILE AWS_DEFAULT_PROFILE; . .venv/bin/activate && python mcp_http_gateway.py

dev-frontend-setup:
	@test -f frontend/.env.local || cp frontend/.env.local.k3s.example frontend/.env.local
	@test -f frontend/public/config.json || cp frontend/public/config.local.json frontend/public/config.json
	cd frontend && npm ci

dev-frontend: dev-frontend-setup
	@curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 || { echo "ERROR: Backend not running on :8000. Start it first: make dev-backend"; exit 1; }
	cd frontend && npm run dev
