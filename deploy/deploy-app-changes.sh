#!/usr/bin/env bash
#
# deploy-app-changes.sh — Nexus Ontology wrapper for kube-operator deploy
#
# Equivalent to (from nexus-deployer/kube-operator):
#   ./deploy-app-changes.sh ontology --env local --all
#
# Builds API + UI, bumps VERSION files, optionally commits, and rolls out to the
# target cluster (local K3s uses ontology-local namespace).
#
# First-time local deploy: this script bootstraps the NexusCapability CR when
# workloads are missing (same pattern as ai-engine-local).
#
# Usage:
#   ./deploy/deploy-app-changes.sh
#   ./deploy/deploy-app-changes.sh --env local
#   ./deploy/deploy-app-changes.sh --api --env local
#   ./deploy/deploy-app-changes.sh --bump minor -m "feat: ontology UI update"
#   ./deploy/deploy-app-changes.sh --dry-run
#   ./deploy/deploy-app-changes.sh --skip-build --no-commit
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NEXUS_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"
DEPLOYER_DIR="${NEXUS_ROOT}/nexus-deployer/kube-operator"
DEPLOYER_SCRIPT="${DEPLOYER_DIR}/deploy-app-changes.sh"

DEPLOY_ENV="${DEPLOY_ENV:-local}"
BUMP_TYPE="patch"
COMMIT_MSG=""
DO_PUSH=true
FORCE_ALL=true
DRY_RUN=false
SKIP_BUILD=false
SKIP_ROLLOUT=false
NO_CACHE=false
EXTRA_ARGS=()

usage() {
    sed -n '2,22p' "$0"
    echo ""
    echo "Options:"
    echo "  --env ENV           local | dev | stage | prod  (default: local)"
    echo "  --bump TYPE         patch | minor | major       (default: patch)"
    echo "  -m, --message MSG   Git commit message (api/ui repos)"
    echo "  --no-push           Commit locally but do not push"
    echo "  --no-commit         Skip git commits"
    echo "  --api|--backend     Deploy API only"
    echo "  --ui|--frontend     Deploy UI only"
    echo "  --no-all            Only deploy components with git changes"
    echo "  --skip-build        Rollout using tags from versions.env"
    echo "  --skip-rollout      Build + commit only"
    echo "  --no-cache          docker build --no-cache"
    echo "  --dry-run           Show plan only"
    echo "  -h, --help          Show this help"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --env)           DEPLOY_ENV="$2"; shift 2 ;;
        --bump)          BUMP_TYPE="$2"; shift 2 ;;
        -m|--message)    COMMIT_MSG="$2"; shift 2 ;;
        --no-push)       DO_PUSH=false; shift ;;
        --no-commit)     EXTRA_ARGS+=(--no-commit); shift ;;
        --api|--backend) EXTRA_ARGS+=(--api); FORCE_ALL=false; shift ;;
        --ui|--frontend) EXTRA_ARGS+=(--ui); FORCE_ALL=false; shift ;;
        --no-all)        FORCE_ALL=false; shift ;;
        --all|--both)    FORCE_ALL=true; shift ;;
        --skip-build)    SKIP_BUILD=true; shift ;;
        --skip-rollout)  SKIP_ROLLOUT=true; shift ;;
        --no-cache)      NO_CACHE=true; shift ;;
        --dry-run)       DRY_RUN=true; shift ;;
        -h|--help)       usage; exit 0 ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ ! -x "${DEPLOYER_SCRIPT}" ]; then
    echo "Deploy script not found: ${DEPLOYER_SCRIPT}" >&2
    exit 1
fi

_kubeconfig="${DEPLOYER_DIR}/../aws-login/.kube/config"
if [ -f "${_kubeconfig}" ]; then
    export KUBECONFIG="${KUBECONFIG:-${_kubeconfig}}"
fi
export ONTOLOGY_DIR="${REPO_ROOT}"

_cmd=(
    "${DEPLOYER_SCRIPT}"
    ontology
    --env "${DEPLOY_ENV}"
    --bump "${BUMP_TYPE}"
)

[ "$FORCE_ALL" = true ] && _cmd+=(--all)
[ "$DO_PUSH" = true ] && _cmd+=(--push)
[ "$SKIP_BUILD" = true ] && _cmd+=(--skip-build)
[ "$SKIP_ROLLOUT" = true ] && _cmd+=(--skip-rollout)
[ "$NO_CACHE" = true ] && _cmd+=(--no-cache)
[ "$DRY_RUN" = true ] && _cmd+=(--dry-run)
[ -n "$COMMIT_MSG" ] && _cmd+=(-m "$COMMIT_MSG")
[ "${#EXTRA_ARGS[@]}" -gt 0 ] && _cmd+=("${EXTRA_ARGS[@]}")

echo "→ ${_cmd[*]}"
exec "${_cmd[@]}"
