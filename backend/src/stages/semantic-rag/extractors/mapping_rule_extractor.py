"""
Mapping Rule Extractor

Reads active mapping rules from MappingRuleService and enriches
unified schema OntoDocuments with source mapping metadata.

For each active mapping rule, the matching schema entity doc gets:
  - structured_metadata: mapping_rule_id, source_type, source_schema, source_table, field_maps
  - fdw_mapping_status upgraded to "mapped_via_rule"
  - content appended with mapping source info
  - a syncs_to relationship to the source table
"""

import asyncio
import os
import sys
from typing import Dict, List

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stage_dir = os.path.dirname(_current_dir)
if _stage_dir not in sys.path:
    sys.path.insert(0, _stage_dir)

from onto_model import OntoDocument, OntoRelationship


class MappingRuleExtractor:

    def __init__(self, logger=None):
        self._log = logger

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def enrich_with_mapping_rules(self, schema_docs: List[OntoDocument]) -> Dict[str, int]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(self._enrich_sync, schema_docs)
                    return future.result()
            return loop.run_until_complete(self._enrich_async(schema_docs))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._enrich_async(schema_docs))
            finally:
                loop.close()

    def _enrich_sync(self, schema_docs: List[OntoDocument]) -> Dict[str, int]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._enrich_async(schema_docs))
        finally:
            loop.close()

    async def _enrich_async(self, schema_docs: List[OntoDocument]) -> Dict[str, int]:
        try:
            from src.services.mapping_rule_service import MappingRuleService
            service = MappingRuleService()
            rules = await service.list_all()
            active_rules = [r for r in rules if r.status.value == "active"]
            self._info(f"Found {len(active_rules)} active mapping rules out of {len(rules)} total")
        except Exception as e:
            self._info(f"MappingRuleService unavailable ({e}) — skipping mapping rule enrichment")
            return {"enriched": 0, "rules_found": 0, "error": str(e)}

        if not active_rules:
            self._info("No active mapping rules found")
            return {"enriched": 0, "rules_found": 0}

        doc_by_name = {}
        for doc in schema_docs:
            name = doc.object_name
            if name:
                doc_by_name[name.lower()] = doc

        enriched = 0
        for rule in active_rules:
            entity_name = rule.virtual_entity
            doc = doc_by_name.get(entity_name.lower())
            if not doc:
                continue

            meta = doc.structured_metadata
            meta["mapping_rule_id"] = rule.id
            meta["mapping_rule_name"] = rule.name
            meta["mapping_source_type"] = rule.source_type.value
            meta["mapping_source_schema"] = rule.source_schema
            meta["mapping_source_table"] = rule.source_table
            meta["mapping_source_system"] = rule.source_system
            meta["mapping_field_maps"] = [
                {"source": fm.source_field, "target": fm.target_field}
                for fm in rule.field_maps
            ]

            current_status = meta.get("fdw_mapping_status", "virtual")
            if current_status in ("virtual", "unmapped"):
                meta["fdw_mapping_status"] = "mapped_via_rule"

            fm_lines = []
            for fm in rule.field_maps[:15]:
                if fm.source_field and fm.target_field:
                    fm_lines.append(f"  {fm.source_field} -> {fm.target_field}")
                elif fm.target_field:
                    fm_lines.append(f"  ? -> {fm.target_field}")
            fm_text = "\n".join(fm_lines) if fm_lines else "  (no field mappings)"
            if len(rule.field_maps) > 15:
                fm_text += f"\n  ... and {len(rule.field_maps) - 15} more"

            doc.content += (
                f"\nMapping Rule: Mapped to {rule.source_schema}.{rule.source_table} "
                f"via rule '{rule.name}' ({rule.source_type.value}). "
                f"{len(rule.field_maps)} field mappings:\n{fm_text}"
            )

            target_id = OntoDocument.generate_id(
                rule.source_system or "Simulator",
                rule.source_table,
                entity_type="Schema",
            )
            doc.relationships.append(OntoRelationship(
                relation_type="syncs_to",
                target_id=target_id,
                description=f"Mapped via rule '{rule.name}' to {rule.source_schema}.{rule.source_table}",
            ))

            enriched += 1

        self._info(f"Mapping rule enrichment: {enriched} entities enriched from {len(active_rules)} rules")
        return {"enriched": enriched, "rules_found": len(active_rules)}
