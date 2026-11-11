#!/usr/bin/env bash
#
# Build the branded Nexus test reports for one component and (optionally)
# publish them to the test-reports site.
#
# The pages come from tests/report_generators/nexus_report_kit.py, which reads
# the raw result files a test run writes (unit.json, integration.json,
# bdd.json, ...). The output uses the same layout as the live site:
#
#   index.html                          portal: every component
#   <slug>/index.html                   component dashboard
#   <slug>/<kind>/<run>/report.html     one detailed report
#
# Usage:
#   publish_branded_reports.sh --reports tests/reports --component "Backend" --slug backend            # build only
#   publish_branded_reports.sh --reports tests/reports --component "Backend" --slug backend --publish  # build and upload
#
# Options:
#   --reports DIR     folder holding the result JSON files (required)
#   --component NAME  name shown on the pages, e.g. "Backend" (required)
#   --slug SLUG       folder on the site: ai-engine | backend | deployer | simulator (required)
#   --out DIR         where to build (default: ./dist/test-reports)
#   --publish         upload to S3 and refresh CloudFront (needs a working AWS sign-in)
#
# Publishing changes only this component's folder and the portal front page.
# Other components' folders are left as they are; their summaries are pulled
# first so the portal shows every component.

set -euo pipefail

BUCKET="${NEXUS_REPORTS_BUCKET:-ai-engine-test-reports}"
PREFIX="${NEXUS_REPORTS_PREFIX:-test-reports}"
CLOUDFRONT_DIST="${NEXUS_REPORTS_DISTRIBUTION:-E269STPYK4FJVQ}"
CLOUDFRONT_DOMAIN="${NEXUS_REPORTS_DOMAIN:-d37vwg02pj6oqg.cloudfront.net}"

REPORTS="" COMPONENT="" SLUG="" OUT="dist/test-reports" PUBLISH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reports) REPORTS="$2"; shift 2 ;;
    --component) COMPONENT="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --publish) PUBLISH=1; shift ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$REPORTS" || -z "$COMPONENT" || -z "$SLUG" ]]; then
  echo "Needs --reports, --component and --slug. See --help." >&2
  exit 2
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT="${NEXUS_REPORT_KIT:-$HERE/../report_generators/nexus_report_kit.py}"
PYTHON="${PYTHON:-python3}"
[[ -x ".venv/bin/python" ]] && PYTHON=".venv/bin/python"

mkdir -p "$OUT"

if [[ "$PUBLISH" == "1" ]]; then
  # Bring down the other components' summaries so the portal lists them all.
  for other in ai-engine backend deployer simulator; do
    [[ "$other" == "$SLUG" ]] && continue
    mkdir -p "$OUT/$other"
    aws s3 cp "s3://$BUCKET/$PREFIX/$other/summary.json" "$OUT/$other/summary.json" --only-show-errors 2>/dev/null || rm -f "$OUT/$other/summary.json"
    rmdir "$OUT/$other" 2>/dev/null || true
  done
fi

"$PYTHON" "$KIT" site --reports "$REPORTS" --out "$OUT/$SLUG" --component "$COMPONENT" --slug "$SLUG"
"$PYTHON" "$KIT" portal --out "$OUT"
echo "Built: $OUT/index.html"

if [[ "$PUBLISH" != "1" ]]; then
  echo "Not published. Add --publish to upload."
  exit 0
fi

aws s3 sync "$OUT/$SLUG" "s3://$BUCKET/$PREFIX/$SLUG" --only-show-errors \
  --cache-control "public, max-age=300" --exclude "*.json"
aws s3 cp "$OUT/$SLUG/summary.json" "s3://$BUCKET/$PREFIX/$SLUG/summary.json" --only-show-errors \
  --content-type "application/json" --cache-control "no-cache"
aws s3 cp "$OUT/index.html" "s3://$BUCKET/$PREFIX/index.html" --only-show-errors \
  --content-type "text/html; charset=utf-8" --cache-control "no-cache"
aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DIST" \
  --paths "/index.html" "/$SLUG/index.html" "/$SLUG/summary.json" >/dev/null
echo "Published: https://$CLOUDFRONT_DOMAIN/index.html"
