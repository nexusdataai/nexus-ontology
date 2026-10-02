#!/usr/bin/env python3
"""
O2C Diagnostics Runner

Run this script on the deployed environment where the backend is accessible.
Usage:
    python scripts/run_o2c_diagnostics.py [--url http://localhost:8000]
"""

import argparse
import json
import sys
import requests

COLORS = {
    "pass": "\033[92m",  # green
    "ok": "\033[92m",
    "warn": "\033[93m",  # yellow
    "inactive": "\033[93m",
    "fail": "\033[91m",  # red
    "error": "\033[91m",
    "no_data": "\033[91m",
    "missing": "\033[91m",
    "reset": "\033[0m",
}


def color(status: str, text: str) -> str:
    c = COLORS.get(status, "")
    return f"{c}{text}{COLORS['reset']}" if c else text


def main():
    parser = argparse.ArgumentParser(description="Run O2C Solution Diagnostics")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    print(f"\n{'='*60}")
    print(f"  O2C Solution Diagnostics")
    print(f"  Backend: {base}")
    print(f"{'='*60}\n")

    # Step 1: Health check
    print("1. Checking backend health...")
    try:
        r = requests.get(f"{base}/api/v1/health/", timeout=10)
        health = r.json()
        print(f"   Health: {color('pass', health.get('status', 'unknown'))}\n")
    except Exception as e:
        print(f"   {color('fail', f'Backend not reachable: {e}')}")
        sys.exit(1)

    # Step 2: Run diagnostics
    print("2. Running O2C diagnostics (this may take 10-30s)...")
    try:
        r = requests.post(f"{base}/api/v1/diagnostics/o2c", json={}, timeout=60)
        if r.status_code != 200:
            print(f"   {color('fail', f'HTTP {r.status_code}: {r.text[:200]}')}")
            sys.exit(1)
        report = r.json()
    except Exception as e:
        print(f"   {color('fail', f'Diagnostics failed: {e}')}")
        sys.exit(1)

    overall = report.get("overall_status", "unknown")
    print(f"   Overall: {color(overall, overall.upper())}\n")

    # Step 3: Data Adequacy
    da = report["sections"]["data_adequacy"]
    print(f"{'─'*60}")
    print(f"  DATA ADEQUACY  [{color(da['status'], da['status'].upper())}]")
    print(f"  {da['summary']['with_data']} of {da['summary']['total_entities']} entities have data")
    print(f"{'─'*60}")
    for e in da["entities"]:
        status_str = color(e["status"], e["status"].upper().ljust(8))
        print(f"  {e['name']:<25} {e['system']:<12} rows={str(e['rows']):>5}  fields={str(e['fields']):>3}  {status_str}")
        if e.get("error"):
            print(f"    └─ {color('warn', e['error'])}")
    print()

    # Step 4: Mapping Correctness
    mc = report["sections"]["mapping_correctness"]
    print(f"{'─'*60}")
    print(f"  MAPPING CORRECTNESS  [{color(mc['status'], mc['status'].upper())}]")
    print(f"  {mc['summary']['active']} of {mc['summary']['total_rules']} rules active")
    print(f"{'─'*60}")
    for r in mc["rules"]:
        status_str = color(r["status"], r["status"].upper().ljust(8))
        src = f"{r['source_schema']}.{r['source_table']}" if r["source_table"] else "—"
        print(f"  {r['entity']:<25} {src:<35} mapped={r['mapped_fields']:>2}  {status_str}")
        if r.get("issue"):
            print(f"    └─ {color('warn', r['issue'])}")
        if r.get("rule_name"):
            print(f"    └─ rule: {r['rule_name']} (status: {r.get('rule_status', '?')})")
    print()

    # Step 5: Data after Mapping
    dm = report["sections"]["data_after_mapping"]
    print(f"{'─'*60}")
    print(f"  DATA AFTER MAPPING  [{color(dm['status'], dm['status'].upper())}]")
    print(f"{'─'*60}")
    for q in dm["queries"]:
        status_str = color(q["status"], q["status"].upper().ljust(8))
        print(f"  {q['entity']:<25} rows={q['rows_returned']:>5}  {status_str}")
        if q["field_keys"]:
            print(f"    └─ fields: {', '.join(q['field_keys'][:10])}")
        if q.get("error"):
            print(f"    └─ {color('warn', q['error'])}")
    print()

    # Step 6: Data Quality
    dq = report["sections"]["data_quality"]
    print(f"{'─'*60}")
    print(f"  DATA QUALITY  [{color(dq['status'], dq['status'].upper())}]")
    s = dq["summary"]
    print(f"  {s['passed']} passed, {s['warnings']} warnings, {s['failures']} failures")
    print(f"{'─'*60}")
    issues_only = [c for c in dq["checks"] if c["status"] != "ok"]
    if issues_only:
        for c in issues_only:
            status_str = color(c["status"], c["status"].upper().ljust(8))
            present = "yes" if c["field_present"] else color("fail", "NO")
            print(f"  {c['entity']:<20} {c['field']:<20} nulls={c['null_count']:>3} ({c['null_pct']:>5.1f}%)  present={present}  {status_str}")
    else:
        print(f"  {color('pass', 'All checks passed')}")
    print()

    # Step 7: Results Analysis
    ra = report["sections"]["results_analysis"]
    print(f"{'─'*60}")
    print(f"  RESULTS ANALYSIS  [{color(ra['status'], ra['status'].upper())}]")
    print(f"{'─'*60}")
    for e in ra["entities"]:
        status_str = color(e["status"], e["status"].upper().ljust(8))
        print(f"  {e['name']:<25} rows={e['rows']:>5}  {status_str}")
        if e.get("kpis"):
            for k, v in e["kpis"].items():
                print(f"    └─ {k}: {v}")
        if e.get("summary"):
            sm = e["summary"]
            print(f"    └─ matched={sm['matched']}, mismatched={sm['mismatched']}, "
                  f"rate={sm['match_rate_pct']}%, value=${sm['total_value']:,.0f}, high_risk={sm['high_risk']}")
        if e.get("alert_count") is not None:
            print(f"    └─ alerts: {e['alert_count']}")
    print()

    # Summary
    print(f"{'='*60}")
    print(f"  OVERALL: {color(overall, overall.upper())}")
    print(f"{'='*60}\n")

    # Save raw JSON
    with open("/tmp/o2c_diagnostics.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Raw report saved to /tmp/o2c_diagnostics.json\n")


if __name__ == "__main__":
    main()
