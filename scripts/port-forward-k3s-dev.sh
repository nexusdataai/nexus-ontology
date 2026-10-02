#!/bin/bash
#
# port-forward-k3s-dev.sh — Forward K3s local stack services to localhost for host dev.
#
# All shared infra (MinIO, MiniStack, Scylla, Redis, Mimir, Postgres) lives in
# nexus-local. Capability namespaces only run app pods.
#
# Usage:
#   ./scripts/port-forward-k3s-dev.sh
#   ./scripts/port-forward-k3s-dev.sh --kube-context local-cluster
#   ./scripts/stop-port-forward-k3s-dev.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOYER_ROOT="$(cd "${REPO_ROOT}/../nexus-deployer" && pwd)"
PID_FILE="${REPO_ROOT}/.k3s-port-forward.pids"

KUBE_CONTEXT="${KUBE_CONTEXT:-local-cluster}"
KUBECONFIG="${KUBECONFIG:-${DEPLOYER_ROOT}/aws-login/.kube/config}"
INFRA_NS="${INFRA_NS:-nexus-local}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --kube-context) KUBE_CONTEXT="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--kube-context NAME]"
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

export KUBECONFIG

kctl() {
    kubectl --context "${KUBE_CONTEXT}" "$@"
}

if [[ -f "${PID_FILE}" ]]; then
    echo "Port-forwards may already be running (PID file: ${PID_FILE})"
    echo "Run: ${SCRIPT_DIR}/stop-port-forward-k3s-dev.sh"
    exit 1
fi

: > "${PID_FILE}"

_start_pf() {
    local name="$1"
    local ns="$2"
    local svc="$3"
    local local_port="$4"
    local remote_port="$5"
    kctl port-forward -n "${ns}" "svc/${svc}" "${local_port}:${remote_port}" >/dev/null 2>&1 &
    echo "$!" >> "${PID_FILE}"
    echo "  ${name}: 127.0.0.1:${local_port} -> ${ns}/${svc}:${remote_port}"
}

echo "Starting K3s port-forwards (context: ${KUBE_CONTEXT})"
echo ""

_start_pf "Scylla (DynamoDB)" "${INFRA_NS}" "scylla-svc" 8001 8000
_start_pf "MiniStack (Athena/Glue/SSM)" "${INFRA_NS}" "ministack-svc" 4566 4566
_start_pf "MinIO (S3)" "${INFRA_NS}" "minio-svc" 9000 9000
_start_pf "Redis" "${INFRA_NS}" "redis-svc" 6379 6379

if kctl get svc pgvector-svc -n "${INFRA_NS}" >/dev/null 2>&1; then
    _start_pf "Postgres (pgvector)" "${INFRA_NS}" "pgvector-svc" 5432 5432
else
    echo "  Postgres: skipped (pgvector-svc not in ${INFRA_NS} — run local-k3s/deploy-local-aws-stack.sh)"
fi

if kctl get svc mimir-svc -n "${INFRA_NS}" >/dev/null 2>&1; then
    _start_pf "Mimir" "${INFRA_NS}" "mimir-svc" 9090 8080
else
    echo "  Mimir: skipped (mimir-svc not in ${INFRA_NS} — run local-k3s/deploy-local-aws-stack.sh)"
fi

sleep 1
echo ""
echo "Port-forwards running. Stop with: ${SCRIPT_DIR}/stop-port-forward-k3s-dev.sh"
echo ""
echo "Endpoints: DDB :8001 | MiniStack :4566 | S3 :9000 | Redis :6379 | PG :5432 | Mimir :9090"
echo ""
echo "Next:"
echo "  cp backend/.env.local.k3s.example backend/.env.local"
echo "  cd backend && python mcp_http_gateway.py"
echo "  cd frontend && npm run dev"
