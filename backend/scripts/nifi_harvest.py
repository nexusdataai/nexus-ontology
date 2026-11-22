#!/usr/bin/env python3
"""
Harvest Apache NiFi processor metadata from the vendored nifi/ tree.

Writes JSON seeds consumed by nexus-ontology (no JVM required).
Run from repo root:
  python nexus-ontology/backend/scripts/nifi_harvest.py \\
    --nifi-root /opt/mycode/nexus/nifi \\
    --out-dir nexus-ontology/backend/enterprise-knowledge/nifi
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PHASE1_LIVE = {
    "org.apache.nifi.processors.standard.ConvertRecord",
    "org.apache.nifi.processors.standard.EvaluateJsonPath",
    "org.apache.nifi.processors.standard.ReplaceText",
    "org.apache.nifi.processors.standard.SplitJson",
    "org.apache.nifi.processors.standard.MergeContent",
    "org.apache.nifi.processors.standard.RouteOnAttribute",
    "org.apache.nifi.processors.standard.QueryRecord",
    "org.apache.nifi.processors.attributes.UpdateAttribute",
    "org.apache.nifi.processors.jolt.JoltTransformJSON",
}

BUNDLE_ALLOWLIST = (
    "nifi-standard-bundle",
    "nifi-jolt-bundle",
    "nifi-update-attribute-bundle",
)

RE_TAGS = re.compile(r"@Tags\(\{([^}]+)\}\)")
RE_CAP = re.compile(r'@CapabilityDescription\("([^"]+)"')
RE_CLASS = re.compile(r"public class (\w+)")
RE_REL = re.compile(r"new Relationship\.Builder\(\)\.name\(\"([^\"]+)\"")
RE_PROP = re.compile(
    r"\.name\(\"([^\"]+)\"\)\s*\n\s*\.displayName\(\"([^\"]+)\"\)",
    re.MULTILINE,
)
RE_PROP_SIMPLE = re.compile(r"PropertyDescriptor\.Builder\(\)\s*\n\s*\.name\(\"([^\"]+)\"\)")


def _processor_id(java_class: str) -> str:
    short = java_class.rsplit(".", 1)[-1]
    return f"nifi.{short}"


def _parse_java_metadata(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tags_m = RE_TAGS.search(text)
    tags: List[str] = []
    if tags_m:
        raw = tags_m.group(1)
        tags = [t.strip().strip('"') for t in raw.split(",") if t.strip()]

    cap_m = RE_CAP.search(text)
    description = cap_m.group(1) if cap_m else ""

    cls_m = RE_CLASS.search(text)
    class_name = cls_m.group(1) if cls_m else path.stem

    relationships = list(dict.fromkeys(RE_REL.findall(text)))
    if not relationships:
        relationships = ["success", "failure"]

    properties: List[Dict[str, Any]] = []
    for name, display in RE_PROP.findall(text):
        properties.append({"name": name, "displayName": display, "required": False})
    for name in RE_PROP_SIMPLE.findall(text):
        if not any(p["name"] == name for p in properties):
            properties.append({"name": name, "displayName": name, "required": False})

    return {
        "tags": tags,
        "description": description,
        "className": class_name,
        "relationships": [{"name": r} for r in relationships],
        "properties": properties[:40],
    }


def _bundle_from_path(java_path: Path, nifi_root: Path) -> str:
    parts = java_path.relative_to(nifi_root).parts
    for p in parts:
        if p.endswith("-bundle"):
            if p.startswith("nifi-"):
                return "nexus-" + p[5:]
            return p
    return "unknown"


def _built_in_assets() -> List[Dict[str, Any]]:
    """Curated flow assets for Nexus Flow Studio (specs, docs, example graphs)."""
    live = [
        "nifi.UpdateAttribute",
        "nifi.JoltTransformJSON",
        "nifi.EvaluateJsonPath",
        "nifi.ReplaceText",
        "nifi.RouteOnAttribute",
        "nifi.QueryRecord",
        "nifi.ConvertRecord",
        "nifi.SplitJson",
        "nifi.MergeContent",
    ]
    assets: List[Dict[str, Any]] = [
        {
            "assetId": "jolt-shift-customer",
            "title": "Jolt shift: flatten customer",
            "kind": "jolt-spec",
            "processorIds": ["nifi.JoltTransformJSON"],
            "contentText": json.dumps(
                [{"operation": "shift", "spec": {"customer": {"name": "fullName", "id": "custId"}}}],
                indent=2,
            ),
        },
        {
            "assetId": "jolt-default-inject",
            "title": "Jolt default: add lineage fields",
            "kind": "jolt-spec",
            "processorIds": ["nifi.JoltTransformJSON"],
            "contentText": json.dumps(
                [
                    {
                        "operation": "default",
                        "spec": {"ingestedAt": "${now():toNumber()}", "source": "nexus-flow"},
                    }
                ],
                indent=2,
            ),
        },
        {
            "assetId": "update-attribute-doc",
            "title": "UpdateAttribute quick reference",
            "kind": "doc",
            "processorIds": ["nifi.UpdateAttribute"],
            "contentText": (
                "Add dynamic properties: name becomes FlowFile attribute. "
                "Values support ${attribute} expression subset. "
                "Delete Attributes Expression accepts a regex to remove keys."
            ),
        },
        {
            "assetId": "evaluate-jsonpath-doc",
            "title": "EvaluateJsonPath usage",
            "kind": "doc",
            "processorIds": ["nifi.EvaluateJsonPath"],
            "contentText": "Map JsonPath expressions to attributes, e.g. id = $.order.id",
        },
        {
            "assetId": "replace-text-doc",
            "title": "ReplaceText patterns",
            "kind": "doc",
            "processorIds": ["nifi.ReplaceText"],
            "contentText": "Search Value + Replacement Value; Regex Replace strategy for content transforms.",
        },
        {
            "assetId": "route-on-attribute-doc",
            "title": "RouteOnAttribute rules",
            "kind": "doc",
            "processorIds": ["nifi.RouteOnAttribute"],
            "contentText": "Each property is a relationship name; value is an expression evaluated against attributes.",
        },
        {
            "assetId": "query-record-doc",
            "title": "QueryRecord SQL subset",
            "kind": "doc",
            "processorIds": ["nifi.QueryRecord"],
            "contentText": "Filter JSON record arrays with SQL, e.g. SELECT * WHERE status = 'OPEN'.",
        },
        {
            "assetId": "convert-record-doc",
            "title": "ConvertRecord json/csv",
            "kind": "doc",
            "processorIds": ["nifi.ConvertRecord"],
            "contentText": "Set Record Reader / Record Writer to json or csv for lightweight format conversion.",
        },
        {
            "assetId": "split-json-doc",
            "title": "SplitJson array fan-out",
            "kind": "doc",
            "processorIds": ["nifi.SplitJson"],
            "contentText": "JsonPath Expression defaults to $; emits one FlowFile per array element.",
        },
        {
            "assetId": "merge-content-doc",
            "title": "MergeContent strategies",
            "kind": "doc",
            "processorIds": ["nifi.MergeContent"],
            "contentText": "Binary Concatenation or JSON Array merge for rebatching outbound payloads.",
        },
        {
            "assetId": "flow-etl-attribute-enrich",
            "title": "Example flow: JSON enrich + route",
            "kind": "example-flow",
            "processorIds": ["nifi.UpdateAttribute", "nifi.EvaluateJsonPath", "nifi.RouteOnAttribute"],
            "contentText": json.dumps(
                {
                    "nodes": [
                        {"id": "u", "type": "nifi.UpdateAttribute", "params": {"region": "US"}},
                        {"id": "j", "type": "nifi.EvaluateJsonPath", "params": {"orderId": "$.id"}},
                        {"id": "r", "type": "nifi.RouteOnAttribute", "params": {"premium": "${tier} == 'GOLD'"}},
                    ],
                    "edges": [
                        {"source": "u", "target": "j", "relationship": "success"},
                        {"source": "j", "target": "r", "relationship": "success"},
                    ],
                },
                indent=2,
            ),
        },
        {
            "assetId": "flow-jolt-load",
            "title": "Example flow: Jolt then ConvertRecord",
            "kind": "example-flow",
            "processorIds": ["nifi.JoltTransformJSON", "nifi.ConvertRecord"],
            "contentText": json.dumps(
                {
                    "nodes": [
                        {
                            "id": "jolt",
                            "type": "nifi.JoltTransformJSON",
                            "params": {
                                "Jolt Specification": '[{"operation":"shift","spec":{"payload":"data"}}]'
                            },
                        },
                        {
                            "id": "conv",
                            "type": "nifi.ConvertRecord",
                            "params": {"Record Reader": "json", "Record Writer": "csv"},
                        },
                    ],
                    "edges": [{"source": "jolt", "target": "conv", "relationship": "success"}],
                },
                indent=2,
            ),
        },
    ]
    for pid in live:
        short = pid.replace("nifi.", "")
        assets.append(
            {
                "assetId": f"processor-ref-{short.lower()}",
                "title": f"{short} (live Nexus processor)",
                "kind": "processor-ref",
                "processorIds": [pid],
                "contentText": f"Registered in Nexus Flow Studio as {pid} with Python runtime.",
            }
        )
    return assets


def harvest(nifi_root: Path) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    processors: List[Dict[str, Any]] = []
    seen_fqn: Set[str] = set()
    assets: List[Dict[str, Any]] = []

    for bundle in BUNDLE_ALLOWLIST:
        services = list(
            nifi_root.glob(
                f"nifi-extension-bundles/{bundle}/**/META-INF/services/org.apache.nifi.processor.Processor"
            )
        )
        for svc in services:
            bundle_name = _bundle_from_path(svc, nifi_root)
            for line in svc.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                fqn = line
                if fqn in seen_fqn:
                    continue
                seen_fqn.add(fqn)
                short = fqn.rsplit(".", 1)[-1]
                java_path = _find_java(nifi_root, bundle, short)
                meta = _parse_java_metadata(java_path) if java_path else {}
                proc_id = _processor_id(fqn)
                live = fqn in PHASE1_LIVE
                processors.append(
                    {
                        "processorId": proc_id,
                        "nifiClass": fqn,
                        "bundle": bundle_name,
                        "label": meta.get("className") or short,
                        "category": "nexus",
                        "description": meta.get("description") or f"Apache NiFi {short}",
                        "tags": meta.get("tags") or [],
                        "properties": meta.get("properties") or [],
                        "relationships": meta.get("relationships")
                        or [{"name": "success"}, {"name": "failure"}],
                        "runtime": "live" if live else "stub",
                        "codeRef": f"python://src.services.flow_processors.{_module_name(short)}.{short}Processor"
                        if live
                        else "",
                    }
                )

    assets.extend(_built_in_assets())

    return processors, assets


def _module_name(short: str) -> str:
    import re as _re

    s = _re.sub(r"(?<!^)(?=[A-Z])", "_", short).lower()
    return s


def _find_java(nifi_root: Path, bundle: str, class_name: str) -> Optional[Path]:
    pattern = f"nifi-extension-bundles/{bundle}/**/{class_name}.java"
    hits = list(nifi_root.glob(pattern))
    return hits[0] if hits else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nifi-root", type=Path, default=Path("/opt/mycode/nexus/nifi"))
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("nexus-ontology/backend/enterprise-knowledge/nifi"),
    )
    args = ap.parse_args()
    procs, assets = harvest(args.nifi_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "processors.json").write_text(json.dumps(procs, indent=2), encoding="utf-8")
    (args.out_dir / "assets.json").write_text(json.dumps(assets, indent=2), encoding="utf-8")
    print(f"Wrote {len(procs)} processors, {len(assets)} assets -> {args.out_dir}")


if __name__ == "__main__":
    main()