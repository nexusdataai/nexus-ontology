"""
Unified Schema Extractor

Schema-first extraction that consumes the in-memory VDL catalog
(authoritatively stored in the ``foundry-workspace`` DynamoDB table as
``VDLENTITY#`` rows) via :class:`VdlCatalogService` and produces
OntoDocuments for every entity — regardless of whether a live FDW
foreign table exists.

The canonical catalog is source-agnostic. The per-domain ``system``
attribute is derived from DOMAIN_TO_SYSTEM (the same mapping used by
the audit endpoint's SYSTEM_SCHEMA_MAP and the seeder's DOMAIN_TO_SIM)
so that downstream views can still summarize by source system.

Each entity's ``aliases`` list (e.g. Customer → [Account, AR_Customer])
is preserved in ``structured_metadata["aliases"]`` so the FDW mapping
resolver can match against legacy source-coupled names when the
canonical name itself has no live foreign table.
"""

import os
import sys
from typing import Any, Dict, List, Optional

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stage_dir = os.path.dirname(_current_dir)
if _stage_dir not in sys.path:
    sys.path.insert(0, _stage_dir)

from onto_model import OntoDocument, OntoRelationship


# Mirrors seed_canonical_mapping_rules.DOMAIN_TO_SIM and the audit
# endpoint's SYSTEM_SCHEMA_MAP. Canonical entities have no per-domain
# ``system`` field by design; this mapping records the *primary* source
# system that backs each domain in the platform today so that summaries
# by system (e.g. the Mapping Audit Report) stay meaningful.
DOMAIN_TO_SYSTEM: Dict[str, str] = {
    "Customer & Sales":           "Salesforce",
    "Finance - General Ledger":   "Oracle",
    "Finance - Receivables":      "Oracle",
    "Finance - Payables":         "Oracle",
    "Procurement":                "Oracle",
    "Inventory":                  "SAP",
    "Product Master":             "SAP",
    "Production & Quality":       "SAP",
    "Logistics":                  "SAP",
    "Commercial CPQ":             "TPM_Simulator",
    "Strategic Sourcing":         "Sourcing_Simulator",
    "Document Management":        "Google_Drive",
    "External Signals":           "Social_Listening",
    "File Capture":               "File_Uploads",
    "Order-to-Cash Results":      "AI_Automation",
}

# Marker recorded on legacy file-loader entries by VdlCatalogService.
_LEGACY_STATUS = "legacy"


class UnifiedSchemaExtractor:
    """Extracts OntoDocuments from the canonical VDL entity catalog.

    Backwards-compatible constructor: the ``schema_dir`` argument is
    preserved (and ignored) so older callers / tests don't break — the
    catalog is now sourced from ``VdlCatalogService`` and is no longer
    tied to a specific filesystem path.
    """

    SOURCE_LABEL = "foundry"

    def __init__(self, logger=None, schema_dir: str = ""):
        self._log = logger
        # Retained for backward compatibility with the previous file-based
        # API; not used for lookups any more.
        self._schema_dir = schema_dir

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def _warning(self, msg):
        if self._log and hasattr(self._log, "log_warning"):
            self._log.log_warning(msg)
        else:
            self._info(msg)

    def extract(self) -> List[OntoDocument]:
        try:
            from src.services.vdl_catalog_service import get_catalog
            catalog = get_catalog()
            entities = catalog.list_entities(refresh=True)
        except Exception as e:
            self._warning(
                f"VDL catalog unavailable ({e}); Knowledge Processor "
                "will produce zero schema documents."
            )
            return []

        if not entities:
            self._warning(
                "VDL catalog is empty. Run bootstrap_foundry_from_files.py "
                "to populate the foundry-workspace DynamoDB table."
            )
            return []

        docs: List[OntoDocument] = []
        for ent in entities:
            doc = self._extract_entity(ent)
            if doc is not None:
                docs.append(doc)

        self._info(
            f"Unified schema extraction complete: {len(docs)} total entities from foundry-workspace catalog"
        )
        return docs

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _extract_entity(self, ent: Dict[str, Any]) -> Optional[OntoDocument]:
        name = ent.get("name") or ""
        if not name:
            return None

        domain_name = ent.get("domain", "") or ""
        # `VdlCatalogService` leaves `system` blank for canonical entries
        # (it's resolved at request time from active mapping rules). For
        # OntoDocument purposes, fall back to the primary source per
        # DOMAIN_TO_SYSTEM. Legacy entries carry their original `system`.
        domain_system = ent.get("system") or DOMAIN_TO_SYSTEM.get(domain_name, "Canonical")

        aliases = [a for a in (ent.get("aliases") or []) if a]
        semantic = ent.get("semantic", "") or ""
        risk_level = ent.get("riskLevel", "medium")
        scor_process = ent.get("scorProcess", "") or ""
        gs1_standard = ent.get("gs1Standard", "") or ""
        is_virtual = bool(ent.get("isVirtual", False))
        is_legacy = (ent.get("fdwMappingStatus") == _LEGACY_STATUS)

        fields = ent.get("fields") or []
        relationships = ent.get("relationships") or []

        field_lines = []
        for kf in fields:
            line = f"  - {kf.get('name')} ({kf.get('dataType', 'unknown')})"
            if kf.get("semantic"):
                line += f": {kf['semantic']}"
            constraints = kf.get("constraints") or []
            if constraints:
                line += "\n    Constraints: " + "; ".join(constraints)
            field_lines.append(line)

        content_lines = [f"Entity: {name}", f"System: {domain_system}", f"Domain: {domain_name}"]
        if aliases:
            content_lines.append(f"Aliases: {', '.join(aliases)}")
        if semantic:
            content_lines.append(f"Description: {semantic}")
        if scor_process:
            content_lines.append(f"SCOR Process: {scor_process}")
        if gs1_standard:
            content_lines.append(f"GS1 Standard: {gs1_standard}")
        if field_lines:
            content_lines.append("Key Fields:")
            content_lines.extend(field_lines)
        content = "\n".join(content_lines) + "\n"

        ontorelations = self._build_relationships(relationships, domain_system)

        # ``virtual`` (legacy flag) is preserved; anything else defaults to
        # ``unmapped`` so the FDW resolver attempts a live match. The
        # catalog's own ``fdwMappingStatus`` ("canonical" / "legacy") is
        # recorded separately for traceability.
        fdw_mapping_status = "virtual" if is_virtual else "unmapped"

        # Physical hint for legacy entries that carry an explicit
        # source-coupled name (e.g. supply-chain-schema.yaml's
        # ``physical_source_table``).
        physical_source = ent.get("physicalSourceTable") or ""

        key_field_names = [kf.get("name") for kf in fields if kf.get("name")]
        key_field_details = [
            {
                "name": kf.get("name"),
                "data_type": kf.get("dataType", ""),
                "semantic": kf.get("semantic", ""),
                "risk_level": kf.get("riskLevel", ""),
            }
            for kf in fields if kf.get("name")
        ]

        return OntoDocument(
            id=OntoDocument.generate_id(domain_system, name, entity_type="Schema"),
            system=domain_system,
            entity_type="Schema",
            object_name=name,
            category="schema",
            content=content,
            source=self.SOURCE_LABEL,
            risk_level=risk_level,
            structured_metadata={
                "fdw_table": name,
                "aliases": aliases,
                "virtual": is_virtual,
                "domain": domain_name,
                "scor_process": scor_process,
                "gs1_standard": gs1_standard,
                "fdw_mapping_status": fdw_mapping_status,
                "catalog_status": ent.get("fdwMappingStatus", ""),
                "source_system": domain_system,
                "physical_source_table": physical_source,
                "canonical": not is_legacy,
                "key_fields": key_field_names,
                "key_field_details": key_field_details,
            },
            relationships=ontorelations,
        )

    def _build_relationships(
        self, relationships: List[Dict[str, Any]], default_system: str,
    ) -> List[OntoRelationship]:
        rels: List[OntoRelationship] = []
        for r in relationships:
            target_name = r.get("targetEntity") or r.get("target_entity") or ""
            target_cat = r.get("targetCategory") or r.get("target_category") or "schema"
            target_system = r.get("targetSystem") or r.get("target_system") or ""

            if target_cat == "schema":
                sys_name = target_system or default_system
                target_id = OntoDocument.generate_id(sys_name, target_name, entity_type="Schema")
            elif target_cat == "workflow":
                target_id = OntoDocument.generate_id("Internal", target_name, entity_type="Workflow")
            elif target_cat == "policy":
                target_id = OntoDocument.generate_id("Internal", target_name, entity_type="Policy")
            elif target_cat == "integration":
                sys_name = target_system or "Salesforce"
                target_id = OntoDocument.generate_id(sys_name, target_name, entity_type="Integration")
            else:
                target_id = OntoDocument.generate_id(default_system, target_name)

            rels.append(OntoRelationship(
                relation_type=r.get("type", "depends_on"),
                target_id=target_id,
                description=r.get("description", ""),
            ))
        return rels
