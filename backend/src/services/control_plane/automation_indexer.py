"""
Automation Indexer.

Walks ``enterprise-knowledge/automation/<solution>/<use_case_id>.yaml``,
validates against ``models/automation_models.py`` schemas, embeds each
record (UseCase / Stage / Step / ToolBinding / ConnectorAPI) into
control_plane_embeddings with a distinct content_type, and registers
parent->child edges in the metadata-based relationship index used by
GraphStore (or AGE if available).

Cross-references are validated against the live ToolRegistry and the
connector_apis registry; bad references are logged but do not stop the
ingest.

Idempotent: keys on (content_type, record_id), upserts on every run.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger
from pydantic import ValidationError

from src.models.automation_models import (
    ConnectorAPIDoc, IndexedUseCaseSummary, StageDoc, StepDoc,
    ToolBindingDoc, ToolDoc, UseCaseDoc,
)

ai_logger = logger.bind(component="automation-indexer")


CONTENT_TYPES = {
    "use_case":       "onto_use_case",
    "stage":          "onto_stage",
    "step":           "onto_step",
    "tool_binding":   "onto_tool_binding",
    "connector_api":  "onto_connector_api",
    "tool":           "onto_tool",
}


def _default_yaml_root() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "enterprise-knowledge" / "automation"


def _default_tools_yaml_root() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "enterprise-knowledge" / "tools"


def _extract_header_comment(raw_yaml: str) -> Optional[str]:
    """Harvest the leading Cursor-style header comment band from a YAML
    source (plan section 29). Returns the joined comment block (without
    the leading ``#`` markers) or None if the file does not begin with a
    comment band.

    Convention: a header comment is any contiguous run of ``#``-prefixed
    lines starting at the very first line of the file. The strict
    ``# ====`` decoration is recommended but not required at this layer
    (the linter enforces the decoration; the indexer just captures
    whatever the author put there).
    """
    if not raw_yaml:
        return None
    lines: List[str] = []
    for line in raw_yaml.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            lines.append(stripped[1:].strip())
            continue
        if not stripped:
            # Allow blank lines inside the header band (sometimes used
            # for visual separation between sub-blocks).
            if lines:
                lines.append("")
                continue
            # Leading blank lines before any comment - keep scanning.
            continue
        break
    text = "\n".join(lines).strip()
    return text or None


class AutomationIndexer:

    def __init__(
        self,
        embedding_service: Any,
        vector_store: Any,
        tool_registry: Any = None,
        connector_apis_module: Any = None,
        yaml_root: Optional[Path] = None,
        tools_yaml_root: Optional[Path] = None,
    ) -> None:
        self._embeddings = embedding_service
        self._vector = vector_store
        self._tool_registry = tool_registry
        self._connector_apis = connector_apis_module
        self._yaml_root = yaml_root or _default_yaml_root()
        self._tools_yaml_root = tools_yaml_root or _default_tools_yaml_root()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def index_all(self) -> Dict[str, Any]:
        stats = {
            "files_seen": 0,
            "validated": 0,
            "validation_errors": 0,
            "indexed_use_cases": 0,
            "indexed_stages": 0,
            "indexed_steps": 0,
            "indexed_tool_bindings": 0,
            "indexed_connector_apis": 0,
            "indexed_tools": 0,
            "tool_orphans_yaml_only": [],
            "tool_orphans_registry_only": [],
            "missing_tools": [],
            "missing_connector_apis": [],
            "errors": [],
            # Phase 3 - track header-comment + tool_kind coverage so the
            # diagnostics panel can show authoring health. Not blocking
            # during the rollout grace period.
            "missing_headers": [],
            "missing_tool_kinds": [],
        }

        # Phase 2: index tool catalogue first so use cases that reference
        # tools by name can cross-validate against on-disk metadata too.
        await self._index_tools(stats)

        # Phase 3 (data-organization spec): DDB is authoritative.
        # Bootstrap AUTOMATION# rows from disk when empty, then read from
        # DDB via a materialized temp directory so the existing file walker
        # stays the single ingest code path.
        active_root = self._yaml_root
        ddb_tempdir = None
        try:
            from src.services.control_plane.automation_registry_service import (
                get_automation_registry,
                is_ddb_automation_registry_enabled,
            )
            if is_ddb_automation_registry_enabled():
                reg = get_automation_registry()
                await reg.bootstrap_from_disk(self._yaml_root)
                materialized = await reg.materialize_to_tempdir()
                if materialized is not None:
                    ddb_tempdir = materialized
                    active_root = materialized
                    stats["source"] = "dynamodb"
                else:
                    stats["source"] = "filesystem"
            else:
                stats["source"] = "filesystem"
        except Exception as e:
            ai_logger.warning("Automation DDB path failed, falling back to disk: {}", e)
            stats["source"] = "filesystem"

        if not active_root.exists():
            ai_logger.warning("Automation root {} does not exist", active_root)
            return stats

        files = sorted(active_root.rglob("*.yaml"))
        ai_logger.info("Automation indexer: {} YAML files under {} (source={})",
                       len(files), active_root, stats.get("source"))
        stats["files_seen"] = len(files)

        for fpath in files:
            try:
                doc = self._load_one(fpath)
            except ValidationError as ve:
                stats["validation_errors"] += 1
                ai_logger.warning("Validation failed for {}: {}", fpath, ve)
                stats["errors"].append({"file": str(fpath), "error": str(ve)})
                continue
            except Exception as e:
                stats["validation_errors"] += 1
                ai_logger.warning("Could not read {}: {}", fpath, e)
                stats["errors"].append({"file": str(fpath), "error": str(e)})
                continue

            stats["validated"] += 1
            await self._index_one(doc, stats)

        ai_logger.info(
            "Automation indexing complete: use_cases={} stages={} steps={} bindings={} apis={} (missing tools={}, missing apis={})",
            stats["indexed_use_cases"], stats["indexed_stages"], stats["indexed_steps"],
            stats["indexed_tool_bindings"], stats["indexed_connector_apis"],
            len(stats["missing_tools"]), len(stats["missing_connector_apis"]),
        )

        # Clean up any DDB-materialized temp directory. Best-effort.
        if ddb_tempdir is not None:
            try:
                import shutil
                shutil.rmtree(ddb_tempdir, ignore_errors=True)
            except Exception:
                pass
        return stats

    async def dry_run(self) -> Dict[str, Any]:
        """
        Validate every YAML and cross-reference its tool / connector_api
        references against the live registries WITHOUT writing to the vector
        store or graph.  Used by ``POST /api/v1/diagnostics/automation/dry-run``
        to power the Automation tab in the Diagnostics page.

        Phase 3 additions per plan section 36:
          - ``has_header``: each automation YAML's header band presence
          - ``taxonomy_warnings``: stage / kind alignment issues per
            ``JourneyDoc.validate_strict`` (act stages must contain a
            mutate/notify step; resolve/diagnose must contain only
            read/analyze/decide; steps must not carry ``connector_api``).
          - ``runtime_orphans``: YAML tool catalog entries that have no
            backing runtime (neither code-defined nor DDB-loaded).
        """
        from src.models.automation_models import JourneyDoc

        result: Dict[str, Any] = {
            "yaml_root": str(self._yaml_root),
            "files_seen": 0,
            "validated": 0,
            "validation_errors": 0,
            "use_cases": [],
            "errors": [],
            "totals": {
                "use_cases": 0,
                "stages": 0,
                "steps": 0,
                "tool_bindings": 0,
                "connector_apis": 0,
                "high_risk_steps": 0,
                "missing_tools": 0,
                "missing_connector_apis": 0,
                # Phase 3 additions
                "missing_headers": 0,
                "stage_kind_mismatches": 0,
                "step_connector_api_violations": 0,
            },
        }

        if not self._yaml_root.exists():
            return result

        try:
            known_tools = (
                {t.name for t in self._tool_registry.list_tools()}
                if self._tool_registry is not None else set()
            )
        except Exception:
            known_tools = set()
        try:
            known_apis = (
                {s.api_id for s in self._connector_apis.list_all()}
                if self._connector_apis is not None else set()
            )
        except Exception:
            known_apis = set()

        # Phase 3 - cache per-tool kind so JourneyDoc.validate_strict can
        # enforce stage / kind alignment. Heuristic from
        # ``Tool.effective_tool_kind`` keeps backwards-compat with legacy
        # registrations that pre-date the explicit field.
        tool_kinds: Dict[str, str] = {}
        if self._tool_registry is not None:
            try:
                for t in self._tool_registry.list_tools():
                    try:
                        tool_kinds[t.name] = t.effective_tool_kind()
                    except Exception:
                        tool_kinds[t.name] = "analyze"
            except Exception:
                pass

        files = sorted(self._yaml_root.rglob("*.yaml"))
        result["files_seen"] = len(files)

        for fpath in files:
            rel = str(fpath.relative_to(self._yaml_root))
            try:
                raw = fpath.read_text(encoding="utf-8")
                has_header = bool(_extract_header_comment(raw))
                doc = self._load_one(fpath)
            except ValidationError as ve:
                result["validation_errors"] += 1
                result["errors"].append({"file": rel, "error": str(ve)})
                continue
            except Exception as e:
                result["validation_errors"] += 1
                result["errors"].append({"file": rel, "error": str(e)})
                continue

            result["validated"] += 1

            inline_apis = {api.api_id for api in doc.connector_apis}
            tool_refs = doc.all_tool_names()
            api_refs = doc.all_connector_api_ids()

            missing_tools = [t for t in tool_refs if known_tools and t not in known_tools]
            missing_apis = [
                a for a in api_refs
                if known_apis and a not in known_apis and a not in inline_apis
            ]

            stage_count = len(doc.stages)
            step_count = sum(len(s.steps) for s in doc.stages)
            high_risk = 0
            api_risk = {api.api_id: api.risk_level for api in doc.connector_apis}
            for stage in doc.stages:
                for step in stage.steps:
                    if step.requires_approval:
                        high_risk += 1
                        continue
                    for b in step.effective_bindings():
                        rl = api_risk.get(b.connector_api or "")
                        if rl == "high_risk_write":
                            high_risk += 1
                            break

            binding_count = sum(
                len(step.effective_bindings())
                for stage in doc.stages for step in stage.steps
            )

            # Phase 3 - run JourneyDoc.validate_strict for stage/kind +
            # step-connector-api warnings. Cast UseCaseDoc fields into
            # JourneyDoc so the alignment rules apply uniformly.
            taxonomy_warnings: List[Dict[str, str]] = []
            try:
                jd = JourneyDoc(**doc.model_dump())
                report = jd.validate_strict(
                    known_tools=known_tools,
                    known_connector_apis=known_apis,
                    tool_kinds=tool_kinds,
                )
                for issue in report.errors + report.warnings:
                    taxonomy_warnings.append({
                        "severity": issue.severity, "code": issue.code,
                        "path": issue.path, "message": issue.message,
                    })
            except Exception as e:
                taxonomy_warnings.append({
                    "severity": "error", "code": "validate_strict_failed",
                    "path": "", "message": str(e),
                })

            stage_kind_mismatches = sum(
                1 for w in taxonomy_warnings
                if w["code"] in {"act_stage_no_mutator", "resolve_stage_has_mutator"}
            )
            step_connector_violations = sum(
                1 for w in taxonomy_warnings
                if w["code"] in {"step_connector_api_forbidden", "binding_connector_api_forbidden"}
            )

            if missing_tools or missing_apis or result["errors"]:
                status = "fail" if (missing_tools or missing_apis) else "warn"
            elif not has_header or stage_kind_mismatches:
                status = "warn"
            else:
                status = "pass"

            result["use_cases"].append({
                "use_case_id": doc.use_case_id,
                "title": doc.title,
                "solution_id": doc.solution_id,
                "status": status,
                "yaml_file": rel,
                "stage_count": stage_count,
                "step_count": step_count,
                "binding_count": binding_count,
                "tool_refs": tool_refs,
                "connector_api_refs": api_refs,
                "missing_tools": missing_tools,
                "missing_connector_apis": missing_apis,
                "high_risk_steps": high_risk,
                "tags": list(doc.tags),
                "kpi_impact": list(doc.kpi_impact),
                # Phase 3 additions
                "has_header_comment": has_header,
                "taxonomy_warnings": taxonomy_warnings,
                "stage_kind_mismatches": stage_kind_mismatches,
                "step_connector_api_violations": step_connector_violations,
            })

            t = result["totals"]
            t["use_cases"] += 1
            t["stages"] += stage_count
            t["steps"] += step_count
            t["tool_bindings"] += binding_count
            t["connector_apis"] += len(doc.connector_apis)
            t["high_risk_steps"] += high_risk
            t["missing_tools"] += len(missing_tools)
            t["missing_connector_apis"] += len(missing_apis)
            if not has_header:
                t["missing_headers"] += 1
            t["stage_kind_mismatches"] += stage_kind_mismatches
            t["step_connector_api_violations"] += step_connector_violations

        result["use_cases"].sort(key=lambda u: u["use_case_id"])

        if result["validation_errors"] > 0 or result["totals"]["missing_tools"] > 0 or result["totals"]["missing_connector_apis"] > 0:
            result["overall"] = "degraded" if result["totals"]["missing_tools"] or result["totals"]["missing_connector_apis"] else "unhealthy"
            if result["validation_errors"] > 0:
                result["overall"] = "unhealthy"
        elif (
            result["totals"]["missing_headers"] > 0
            or result["totals"]["stage_kind_mismatches"] > 0
            or result["totals"]["step_connector_api_violations"] > 0
        ):
            # Authoring quality issues: degrade rather than fail so the
            # rollout grace period (lint --phase3-grace) keeps green.
            result["overall"] = "degraded"
        else:
            result["overall"] = "healthy"

        result["registry"] = {
            "known_tools": sorted(known_tools),
            "known_connector_apis": sorted(known_apis),
        }

        return result

    async def taxonomy_report(self) -> Dict[str, Any]:
        """Phase 3 - cross-cutting taxonomy view used by the Diagnostics
        Automation taxonomy panel.

        Aggregates header / stage-kind / step-connector violations across
        every automation YAML and the YAML tool catalogue's runtime
        orphans (tools whose YAML lives in enterprise-knowledge/tools/
        but have no live runtime in code or DDB).
        """
        dry = await self.dry_run()
        catalogue = await self.tool_catalogue_report()

        per_solution: Dict[str, Dict[str, int]] = {}
        for uc in dry.get("use_cases", []):
            sol = uc.get("solution_id", "unknown")
            slot = per_solution.setdefault(sol, {
                "total": 0, "missing_header": 0,
                "stage_kind_mismatches": 0,
                "step_connector_api_violations": 0,
                "missing_tools": 0, "missing_connector_apis": 0,
            })
            slot["total"] += 1
            if not uc.get("has_header_comment"):
                slot["missing_header"] += 1
            slot["stage_kind_mismatches"] += int(uc.get("stage_kind_mismatches") or 0)
            slot["step_connector_api_violations"] += int(uc.get("step_connector_api_violations") or 0)
            slot["missing_tools"] += len(uc.get("missing_tools") or [])
            slot["missing_connector_apis"] += len(uc.get("missing_connector_apis") or [])

        return {
            "totals": {
                **dry.get("totals", {}),
                "yaml_tools": catalogue.get("totals", {}).get("yaml_tools", 0),
                "yaml_only_orphans": catalogue.get("totals", {}).get("yaml_only_orphans", 0),
                "registry_only_orphans": catalogue.get("totals", {}).get("registry_only_orphans", 0),
            },
            "per_solution": per_solution,
            "missing_headers": [
                uc["use_case_id"] for uc in dry.get("use_cases", [])
                if not uc.get("has_header_comment")
            ],
            "stage_kind_mismatches": [
                {"use_case_id": uc["use_case_id"], "warnings": [
                    w for w in (uc.get("taxonomy_warnings") or [])
                    if w["code"] in {"act_stage_no_mutator", "resolve_stage_has_mutator"}
                ]}
                for uc in dry.get("use_cases", [])
                if uc.get("stage_kind_mismatches")
            ],
            "step_connector_api_violations": [
                {"use_case_id": uc["use_case_id"], "warnings": [
                    w for w in (uc.get("taxonomy_warnings") or [])
                    if w["code"] in {"step_connector_api_forbidden", "binding_connector_api_forbidden"}
                ]}
                for uc in dry.get("use_cases", [])
                if uc.get("step_connector_api_violations")
            ],
            "yaml_tools_without_runtime": catalogue.get("yaml_only_orphans", []),
            "tools_missing_header": catalogue.get("missing_headers", []),
            "tools_missing_kind": catalogue.get("missing_tool_kinds", []),
            "overall": dry.get("overall", "unknown"),
        }

    async def tool_catalogue_report(self) -> Dict[str, Any]:
        """Walk ``enterprise-knowledge/tools/**/*.yaml`` and report
        catalogue health.

        Returns the shape consumed by the Diagnostics > Automation >
        Tool Catalogue panel: totals (yaml/registered/orphans/groups),
        metadata-quality counters, risk distribution, the orphan lists,
        and a per-tool row with metadata-quality flags.
        """
        report: Dict[str, Any] = {
            "totals": {
                "yaml_tools": 0,
                "registered_tools": 0,
                "yaml_only_orphans": 0,
                "registry_only_orphans": 0,
                "groups": {},
            },
            "metadata_quality": {
                "with_consumes_entities": 0,
                "with_produces_entities": 0,
                "with_connector_api": 0,
                "with_example_invocation": 0,
                "with_tags": 0,
                # Phase 3 - tool_kind + header_comment coverage.
                "with_tool_kind": 0,
                "with_header_comment": 0,
            },
            # Phase 3 - per-tool flags for the panel to highlight.
            "missing_headers": [],
            "missing_tool_kinds": [],
            "risk_distribution": {"read_only": 0, "low_risk_write": 0, "high_risk_write": 0},
            "yaml_only_orphans": [],
            "registry_only_orphans": [],
            "tools": [],
            "errors": [],
            "tools_yaml_root": str(self._tools_yaml_root),
            "overall": "healthy",
        }

        try:
            registry_tools = (
                {t.name: t for t in self._tool_registry.list_tools()}
                if self._tool_registry is not None else {}
            )
        except Exception as e:
            registry_tools = {}
            report["errors"].append({"phase": "registry_scan", "error": str(e)})

        report["totals"]["registered_tools"] = len(registry_tools)

        yaml_ids: set = set()
        if self._tools_yaml_root.exists():
            for fpath in sorted(self._tools_yaml_root.rglob("*.yaml")):
                try:
                    with fpath.open("r", encoding="utf-8") as f:
                        raw = f.read()
                    data = yaml.safe_load(raw) or {}
                    if not data.get("header_comment"):
                        harvested = _extract_header_comment(raw)
                        if harvested:
                            data["header_comment"] = harvested
                    doc = ToolDoc(**data)
                except ValidationError as ve:
                    report["errors"].append({"file": str(fpath), "error": str(ve)})
                    continue
                except Exception as e:
                    report["errors"].append({"file": str(fpath), "error": str(e)})
                    continue

                yaml_ids.add(doc.tool_id)
                report["totals"]["yaml_tools"] += 1
                report["totals"]["groups"][doc.group] = report["totals"]["groups"].get(doc.group, 0) + 1

                if doc.risk_level in report["risk_distribution"]:
                    report["risk_distribution"][doc.risk_level] += 1

                if doc.consumes_entities:
                    report["metadata_quality"]["with_consumes_entities"] += 1
                if doc.produces_entities:
                    report["metadata_quality"]["with_produces_entities"] += 1
                if doc.connector_api:
                    report["metadata_quality"]["with_connector_api"] += 1
                if doc.example_invocation:
                    report["metadata_quality"]["with_example_invocation"] += 1
                if doc.tags:
                    report["metadata_quality"]["with_tags"] += 1
                if doc.tool_kind:
                    report["metadata_quality"]["with_tool_kind"] += 1
                else:
                    report["missing_tool_kinds"].append(doc.tool_id)
                if doc.header_comment:
                    report["metadata_quality"]["with_header_comment"] += 1
                else:
                    report["missing_headers"].append(doc.tool_id)

                report["tools"].append({
                    "tool_id": doc.tool_id,
                    "display_name": doc.display_name,
                    "group": doc.group,
                    "risk_level": doc.risk_level,
                    "requires_approval": doc.requires_approval,
                    "connector_api": doc.connector_api,
                    "consumes_count": len(doc.consumes_entities),
                    "produces_count": len(doc.produces_entities),
                    "tags": list(doc.tags),
                    "registered": doc.tool_id in registry_tools,
                    "yaml_present": True,
                    "example_invocation": bool(doc.example_invocation),
                    "tool_kind": doc.effective_tool_kind(),
                    "tool_kind_explicit": doc.tool_kind is not None,
                    "has_header_comment": bool(doc.header_comment),
                })

        # Orphan diff: YAML-only (yaml present but no live registration)
        # and registry-only (registered but no YAML to surface in KG).
        yaml_only = sorted([tid for tid in yaml_ids if tid not in registry_tools])
        registry_only = sorted([tid for tid in registry_tools if tid not in yaml_ids])
        report["yaml_only_orphans"] = yaml_only
        report["registry_only_orphans"] = registry_only
        report["totals"]["yaml_only_orphans"] = len(yaml_only)
        report["totals"]["registry_only_orphans"] = len(registry_only)

        # Surface registry-only tools as additional rows so the panel
        # shows them alongside YAML tools (yaml_present=False).
        for name, t in registry_tools.items():
            if name in yaml_ids:
                continue
            try:
                rl = t.risk_level.value if hasattr(t.risk_level, "value") else str(t.risk_level)
            except Exception:
                rl = "read_only"
            try:
                kind = t.effective_tool_kind() if hasattr(t, "effective_tool_kind") else None
            except Exception:
                kind = None
            report["tools"].append({
                "tool_id": name,
                "display_name": name.replace("_", " ").title(),
                "group": "registry",
                "risk_level": rl,
                "requires_approval": bool(getattr(t, "requires_approval", False)),
                "connector_api": getattr(t, "connector_api", None),
                "consumes_count": 0,
                "produces_count": 0,
                "tags": list(getattr(t, "tags", []) or []),
                "registered": True,
                "yaml_present": False,
                "example_invocation": False,
                "tool_kind": kind,
                "tool_kind_explicit": getattr(t, "tool_kind", None) is not None,
                "has_header_comment": False,
            })

        report["tools"].sort(key=lambda r: (r["group"], r["tool_id"]))

        if yaml_only or report["errors"]:
            report["overall"] = "unhealthy" if yaml_only else "degraded"
        elif registry_only:
            report["overall"] = "degraded"

        return report

    async def list_use_cases(self) -> List[IndexedUseCaseSummary]:
        """Return summaries of every use case currently on disk (without re-embedding)."""
        if not self._yaml_root.exists():
            return []
        out: List[IndexedUseCaseSummary] = []
        for fpath in sorted(self._yaml_root.rglob("*.yaml")):
            try:
                doc = self._load_one(fpath)
            except Exception:
                continue
            stage_count = len(doc.stages)
            step_count = sum(len(s.steps) for s in doc.stages)
            out.append(IndexedUseCaseSummary(
                use_case_id=doc.use_case_id,
                title=doc.title,
                solution_id=doc.solution_id,
                status=doc.status,
                stage_count=stage_count,
                step_count=step_count,
                tool_count=len(doc.all_tool_names()),
                connector_api_count=len(doc.all_connector_api_ids()),
            ))
        return out

    async def get_use_case(self, use_case_id: str) -> Optional[UseCaseDoc]:
        for fpath in sorted(self._yaml_root.rglob("*.yaml")):
            try:
                doc = self._load_one(fpath)
            except Exception:
                continue
            if doc.use_case_id == use_case_id:
                return doc
        return None

    # ------------------------------------------------------------------
    # YAML -> validated doc
    # ------------------------------------------------------------------

    def _load_one(self, fpath: Path) -> UseCaseDoc:
        with fpath.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return UseCaseDoc(**data)

    # ------------------------------------------------------------------
    # Embedding + upsert
    # ------------------------------------------------------------------

    async def _index_one(self, doc: UseCaseDoc, stats: Dict[str, Any]) -> None:
        # Cross-reference checks (advisory)
        if self._tool_registry is not None:
            try:
                known = {t.name for t in self._tool_registry.list_tools()}
            except Exception:
                known = set()
            for tname in doc.all_tool_names():
                if known and tname not in known:
                    stats["missing_tools"].append({"use_case": doc.use_case_id, "tool": tname})

        if self._connector_apis is not None:
            try:
                known_apis = {s.api_id for s in self._connector_apis.list_all()}
            except Exception:
                known_apis = set()
            inline_apis = {api.api_id for api in doc.connector_apis}
            for aid in doc.all_connector_api_ids():
                if known_apis and aid not in known_apis and aid not in inline_apis:
                    stats["missing_connector_apis"].append({"use_case": doc.use_case_id, "api_id": aid})

        # Build the docs list to upsert in one batch.
        docs: List[Dict[str, Any]] = []
        texts: List[str] = []

        # 1. Use case
        uc_text = (
            f"Automation Use Case '{doc.title}' for solution '{doc.solution_id}'.\n"
            f"id: {doc.use_case_id}\n"
            f"description: {doc.description or ''}\n"
            f"tags: {', '.join(doc.tags)}\n"
            f"kpi_impact: {', '.join(doc.kpi_impact)}\n"
            f"consumes: {', '.join(doc.consumes_entities)}\n"
            f"produces: {', '.join(doc.produces_entities)}\n"
            f"stages: " + ", ".join(s.name for s in doc.stages)
        )
        texts.append(uc_text)
        docs.append({
            "content_type": CONTENT_TYPES["use_case"],
            "source_id": doc.use_case_id,
            "content": uc_text,
            "metadata": {
                "use_case_id": doc.use_case_id,
                "title": doc.title,
                "solution_id": doc.solution_id,
                "status": doc.status,
                "tags": list(doc.tags),
                "stage_ids": [s.stage_id for s in doc.stages],
                "tool_names": doc.all_tool_names(),
                "connector_api_ids": doc.all_connector_api_ids(),
                "consumes_entities": list(doc.consumes_entities),
                "produces_entities": list(doc.produces_entities),
                "relations": [
                    {"target": f"sol::{doc.solution_id}", "type": "APPLIES_TO_SOLUTION"},
                    *[{"target": f"stage::{doc.use_case_id}::{s.stage_id}", "type": "HAS_STAGE"} for s in doc.stages],
                    *[{"target": f"entity::{e}", "type": "CONSUMES_ENTITY"} for e in doc.consumes_entities],
                    *[{"target": f"entity::{e}", "type": "PRODUCES_ENTITY"} for e in doc.produces_entities],
                ],
            },
        })

        # 2. Stages
        for stage in doc.stages:
            stage_sid = f"stage::{doc.use_case_id}::{stage.stage_id}"
            stage_text = (
                f"Stage '{stage.name}' (order {stage.order}) of use case '{doc.title}'.\n"
                f"description: {stage.description or ''}\n"
                f"steps: " + ", ".join(s.name for s in stage.steps)
            )
            texts.append(stage_text)
            docs.append({
                "content_type": CONTENT_TYPES["stage"],
                "source_id": stage_sid,
                "content": stage_text,
                "metadata": {
                    "stage_id": stage.stage_id,
                    "use_case_id": doc.use_case_id,
                    "solution_id": doc.solution_id,
                    "order": stage.order,
                    "name": stage.name,
                    "step_ids": [s.step_id for s in stage.steps],
                    "relations": [
                        {"target": doc.use_case_id, "type": "STAGE_OF"},
                        *[{"target": f"step::{doc.use_case_id}::{stage.stage_id}::{s.step_id}", "type": "HAS_STEP"}
                          for s in stage.steps],
                    ],
                },
            })

            # 3. Steps and 4. ToolBindings
            for step in stage.steps:
                step_sid = f"step::{doc.use_case_id}::{stage.stage_id}::{step.step_id}"
                bindings = step.effective_bindings()
                step_text = (
                    f"Step '{step.name}' (stage '{stage.name}') of use case '{doc.title}'.\n"
                    f"description: {step.description or ''}\n"
                    f"requires_approval: {step.requires_approval}\n"
                    f"tools: " + ", ".join(b.tool for b in bindings)
                )
                texts.append(step_text)
                docs.append({
                    "content_type": CONTENT_TYPES["step"],
                    "source_id": step_sid,
                    "content": step_text,
                    "metadata": {
                        "step_id": step.step_id,
                        "stage_id": stage.stage_id,
                        "use_case_id": doc.use_case_id,
                        "solution_id": doc.solution_id,
                        "order": step.order,
                        "requires_approval": step.requires_approval,
                        "tools": [b.tool for b in bindings],
                        "connector_api_ids": [b.connector_api for b in bindings if b.connector_api],
                        "relations": [
                            {"target": stage_sid, "type": "STEP_OF_STAGE"},
                            *[{"target": f"binding::{step_sid}::{b.tool}", "type": "USES_TOOL"} for b in bindings],
                        ],
                    },
                })

                for b in bindings:
                    binding_sid = f"binding::{step_sid}::{b.tool}"
                    binding_text = (
                        f"Tool binding: step '{step.name}' invokes tool '{b.tool}'.\n"
                        f"description: {b.description or ''}\n"
                        f"params: {json.dumps(b.params, default=str)}\n"
                        f"connector_api: {b.connector_api or ''}"
                    )
                    texts.append(binding_text)
                    docs.append({
                        "content_type": CONTENT_TYPES["tool_binding"],
                        "source_id": binding_sid,
                        "content": binding_text,
                        "metadata": {
                            "binding_id": b.binding_id or binding_sid,
                            "step_id": step.step_id,
                            "tool": b.tool,
                            "params": b.params,
                            "connector_api": b.connector_api,
                            "use_case_id": doc.use_case_id,
                            "relations": [
                                {"target": step_sid, "type": "BINDING_OF_STEP"},
                                *([{"target": b.connector_api, "type": "CALLS_API"}] if b.connector_api else []),
                            ],
                        },
                    })
                    stats["indexed_tool_bindings"] += 1

                stats["indexed_steps"] += 1

            stats["indexed_stages"] += 1

        # 5. Inline-declared connector APIs
        for api in doc.connector_apis:
            api_text = (
                f"Connector API '{api.api_id}' on '{api.target_system}'.\n"
                f"operation: {api.operation}\n"
                f"description: {api.description or ''}\n"
                f"risk: {api.risk_level}\n"
                f"request_schema: {json.dumps(api.request_schema, default=str)}\n"
                f"response_schema: {json.dumps(api.response_schema, default=str)}"
            )
            texts.append(api_text)
            docs.append({
                "content_type": CONTENT_TYPES["connector_api"],
                "source_id": api.api_id,
                "content": api_text,
                "metadata": {
                    "api_id": api.api_id,
                    "target_system": api.target_system,
                    "operation": api.operation,
                    "risk_level": api.risk_level,
                    "simulator_writeback": api.simulator_writeback,
                    "use_case_id": doc.use_case_id,
                },
            })
            stats["indexed_connector_apis"] += 1

        # Globally registered connector APIs the use case references but
        # didn't inline - upsert them so retrieval includes them too.
        if self._connector_apis is not None:
            inline_ids = {api.api_id for api in doc.connector_apis}
            for aid in doc.all_connector_api_ids():
                if aid in inline_ids:
                    continue
                spec = self._connector_apis.get(aid)
                if spec is None:
                    continue
                api_text = (
                    f"Connector API '{spec.api_id}' on '{spec.target_system}'.\n"
                    f"operation: {spec.operation}\n"
                    f"description: {spec.description}\n"
                    f"risk: {spec.risk_level}"
                )
                texts.append(api_text)
                docs.append({
                    "content_type": CONTENT_TYPES["connector_api"],
                    "source_id": spec.api_id,
                    "content": api_text,
                    "metadata": {
                        "api_id": spec.api_id,
                        "target_system": spec.target_system,
                        "operation": spec.operation,
                        "risk_level": spec.risk_level,
                        "simulator_writeback": spec.simulator_writeback,
                        "tags": list(spec.tags),
                    },
                })
                stats["indexed_connector_apis"] += 1

        # Embed all texts in a single batch and upsert.
        try:
            embeddings = self._embeddings.embed_batch(texts)
        except Exception as e:
            ai_logger.warning("Embedding batch failed for {}: {}", doc.use_case_id, e)
            return
        for d, emb in zip(docs, embeddings):
            d["embedding"] = emb
        try:
            await self._vector.upsert_batch(docs)
        except Exception as e:
            ai_logger.warning("Vector upsert failed for {}: {}", doc.use_case_id, e)
            stats["errors"].append({"use_case": doc.use_case_id, "error": str(e)})
            return

        stats["indexed_use_cases"] += 1

    # ------------------------------------------------------------------
    # Phase 2 - Tool catalogue indexing
    # ------------------------------------------------------------------

    async def _index_tools(self, stats: Dict[str, Any]) -> None:
        """Walk enterprise-knowledge/tools/**/*.yaml, embed each as
        ``onto_tool``, cross-check against the live ToolRegistry, and
        emit (:TOOL) graph metadata for the AGE/metadata graph store.
        """
        if not self._tools_yaml_root.exists():
            ai_logger.info("Tool catalogue dir {} does not exist; skipping", self._tools_yaml_root)
            return

        files = sorted(self._tools_yaml_root.rglob("*.yaml"))
        if not files:
            return

        try:
            registry_tool_names = (
                {t.name for t in self._tool_registry.list_tools()}
                if self._tool_registry is not None else set()
            )
        except Exception:
            registry_tool_names = set()

        yaml_tool_ids: List[str] = []
        docs: List[Dict[str, Any]] = []
        texts: List[str] = []

        for fpath in files:
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    raw = f.read()
                data = yaml.safe_load(raw) or {}
                # Phase 3 - if the YAML didn't declare ``header_comment``
                # explicitly, harvest the leading ``# ====`` band from the
                # raw source so it survives indexing + DDB seed.
                if not data.get("header_comment"):
                    harvested = _extract_header_comment(raw)
                    if harvested:
                        data["header_comment"] = harvested
                doc = ToolDoc(**data)
            except ValidationError as ve:
                stats["validation_errors"] += 1
                stats["errors"].append({"file": str(fpath), "error": str(ve)})
                continue
            except Exception as e:
                stats["validation_errors"] += 1
                stats["errors"].append({"file": str(fpath), "error": str(e)})
                continue

            yaml_tool_ids.append(doc.tool_id)

            if registry_tool_names and doc.tool_id not in registry_tool_names:
                stats["tool_orphans_yaml_only"].append(doc.tool_id)
            if not doc.header_comment:
                stats["missing_headers"].append(doc.tool_id)
            if not doc.tool_kind:
                stats["missing_tool_kinds"].append(doc.tool_id)

            kind = doc.effective_tool_kind()
            search_text = (
                f"Tool '{doc.display_name}' ({doc.tool_id}) in group '{doc.group}'.\n"
                f"kind: {kind}\n"
                f"description: {doc.description}\n"
                f"risk_level: {doc.risk_level}\n"
                f"requires_approval: {doc.requires_approval}\n"
                f"connector_api: {doc.connector_api or ''}\n"
                f"consumes: {', '.join(doc.consumes_entities)}\n"
                f"produces: {', '.join(doc.produces_entities)}\n"
                f"tags: {', '.join(doc.tags)}"
            )
            texts.append(search_text)
            relations: List[Dict[str, str]] = [
                {"target": f"group::{doc.group}", "type": "IN_GROUP"},
            ]
            if doc.connector_api:
                relations.append({"target": doc.connector_api, "type": "CALLS_API"})
            for ent in doc.consumes_entities:
                relations.append({"target": f"entity::{ent}", "type": "READS"})
            for ent in doc.produces_entities:
                relations.append({"target": f"entity::{ent}", "type": "WRITES"})

            docs.append({
                "content_type": CONTENT_TYPES["tool"],
                "source_id": doc.tool_id,
                "content": search_text,
                "metadata": {
                    "tool_id": doc.tool_id,
                    "display_name": doc.display_name,
                    "group": doc.group,
                    "description": doc.description,
                    "risk_level": doc.risk_level,
                    "requires_approval": doc.requires_approval,
                    "cacheable": doc.cacheable,
                    "connector_api": doc.connector_api,
                    "consumes_entities": list(doc.consumes_entities),
                    "produces_entities": list(doc.produces_entities),
                    "tags": list(doc.tags),
                    "parameters": doc.parameters,
                    "tool_kind": kind,
                    "has_header_comment": bool(doc.header_comment),
                    "relations": relations,
                },
            })

        for name in sorted(registry_tool_names):
            if name not in yaml_tool_ids:
                stats["tool_orphans_registry_only"].append(name)

        if not docs:
            return

        try:
            embeddings = self._embeddings.embed_batch(texts)
        except Exception as e:
            ai_logger.warning("Embedding batch failed for tool catalogue: {}", e)
            return
        for d, emb in zip(docs, embeddings):
            d["embedding"] = emb
        try:
            await self._vector.upsert_batch(docs)
            stats["indexed_tools"] = len(docs)
            ai_logger.info(
                "Tool catalogue indexed: {} tools (yaml-only orphans={}, registry-only orphans={})",
                len(docs), len(stats["tool_orphans_yaml_only"]), len(stats["tool_orphans_registry_only"]),
            )
        except Exception as e:
            ai_logger.warning("Vector upsert failed for tool catalogue: {}", e)
            stats["errors"].append({"phase": "tool_catalogue", "error": str(e)})
