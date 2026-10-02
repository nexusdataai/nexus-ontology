#!/bin/bash
#
# init-postgres-extensions.sh — Enable pgvector tables (+ AGE if image supports it)
#
# Normally handled by the Helm postgres-init-extensions Job in nexus-local.
# Use this script only when postgres.initExtensions: false in Helm values,
# or to re-run init after manual schema changes.
#
# Usage:
#   ./scripts/init-postgres-extensions.sh
#   ./scripts/init-postgres-extensions.sh --kube-context local-cluster
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOYER_ROOT="$(cd "${REPO_ROOT}/../nexus-deployer" && pwd)"

KUBE_CONTEXT="${KUBE_CONTEXT:-local-cluster}"
KUBECONFIG="${KUBECONFIG:-${DEPLOYER_ROOT}/aws-login/.kube/config}"
INFRA_NS="${INFRA_NS:-nexus-local}"
PG_POD="${PG_POD:-pgvector-0}"
DB_NAME="${DB_NAME:-ontology_cp}"
DB_USER="${DB_USER:-nexus}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --kube-context) KUBE_CONTEXT="$2"; shift 2 ;;
        --namespace) INFRA_NS="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--kube-context NAME] [--namespace NS]"
            echo "Default namespace: nexus-local (shared stack)"
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

export KUBECONFIG

kctl() {
    kubectl --context "${KUBE_CONTEXT}" "$@"
}

if ! kctl get pod -n "${INFRA_NS}" "${PG_POD}" >/dev/null 2>&1; then
    echo "Pod ${INFRA_NS}/${PG_POD} not found. Deploy shared stack first:" >&2
    echo "  cd nexus-deployer/local-k3s && ./deploy-local-aws-stack.sh --kube-context ${KUBE_CONTEXT}" >&2
    exit 1
fi

echo "Initializing postgres extensions in ${INFRA_NS}/${PG_POD} (db=${DB_NAME})"

kctl exec -i -n "${INFRA_NS}" "${PG_POD}" -- psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<'EOSQL'
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS control_plane_embeddings (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_type, source_id)
);
CREATE INDEX IF NOT EXISTS idx_cpe_content_type ON control_plane_embeddings(content_type);

CREATE TABLE IF NOT EXISTS mapping_rules (
    id VARCHAR(255) PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
EOSQL

AGE_COUNT=$(kctl exec -n "${INFRA_NS}" "${PG_POD}" -- psql -U "${DB_USER}" -d "${DB_NAME}" -t -A -c \
    "SELECT count(*) FROM pg_available_extensions WHERE name = 'age';" 2>/dev/null | tr -d '[:space:]' || echo "0")

if [[ "${AGE_COUNT}" -gt 0 ]]; then
    echo "Apache AGE available — creating extension and enterprise_onto graph"
    kctl exec -i -n "${INFRA_NS}" "${PG_POD}" -- psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<'EOSQL' || true
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, public;
SELECT create_graph('enterprise_onto');
EOSQL
else
    echo "Apache AGE not in postgres image — graph RAG uses metadata fallback (see README)"
fi

echo "Postgres extension init complete"
