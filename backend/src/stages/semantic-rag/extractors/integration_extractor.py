"""
Integration Mapping Extractor

Parses system-to-system integration mapping files (JSON/YAML) that describe
field-level sync relationships between enterprise systems.

Expected format:
  integrations:
    - name: Salesforce_to_Oracle_AR_Sync
      source_system: Salesforce
      target_system: Oracle
      mappings:
        - source_field: Account.Credit_Limit__c
          target_field: AR_Customer.credit_limit
          sync_direction: unidirectional
          sync_frequency: real_time
"""

import os
import sys
import glob
import json
from typing import List

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stage_dir = os.path.dirname(_current_dir)
if _stage_dir not in sys.path:
    sys.path.insert(0, _stage_dir)

from onto_model import OntoDocument, OntoRelationship


class IntegrationExtractor:
    def __init__(self, logger=None, local_path: str = ""):
        self._log = logger
        self._local_path = local_path

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def extract(self) -> List[OntoDocument]:
        docs: List[OntoDocument] = []

        if self._local_path and os.path.exists(self._local_path):
            docs.extend(self._extract_local(self._local_path))

        if not docs:
            self._info("No integration mapping files found — skipping")

        return docs

    def _extract_local(self, path: str) -> List[OntoDocument]:
        if os.path.isfile(path):
            files = [path]
        else:
            files = (
                glob.glob(os.path.join(path, "**/*.yaml"), recursive=True)
                + glob.glob(os.path.join(path, "**/*.yml"), recursive=True)
                + glob.glob(os.path.join(path, "**/*.json"), recursive=True)
            )

        self._info(f"Found {len(files)} integration mapping files in {path}")
        docs = []

        for filepath in files:
            try:
                docs.extend(self._parse_file(filepath))
            except Exception as e:
                self._info(f"  Failed to parse {filepath}: {e}")

        return docs

    def _parse_file(self, filepath: str) -> List[OntoDocument]:
        ext = os.path.splitext(filepath)[1].lower()
        filename = os.path.basename(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            raw = f.read()

        if ext in ('.yaml', '.yml'):
            try:
                import yaml
                data = yaml.safe_load(raw)
            except ImportError:
                self._info(f"  PyYAML not available — skipping {filename}")
                return []
        elif ext == '.json':
            data = json.loads(raw)
        else:
            return []

        if not isinstance(data, dict):
            return []

        integrations = data.get("integrations", [])
        if not integrations:
            integrations = [data]

        docs = []
        for i, integ in enumerate(integrations):
            if not isinstance(integ, dict):
                continue

            name = integ.get("name", f"Integration_{filename}_{i}")
            source_sys = integ.get("source_system", "Unknown")
            target_sys = integ.get("target_system", "Unknown")
            mappings = integ.get("mappings", [])

            mapping_lines = []
            relationships = []
            for m in mappings:
                if not isinstance(m, dict):
                    continue

                m_name = m.get("name", "")
                fields = m.get("fields", [])
                src_obj = m.get("source_object", "")
                tgt_obj = m.get("target_object", "")

                if fields:
                    for fld in fields:
                        if not isinstance(fld, dict):
                            continue
                        src_f = fld.get("source", "?")
                        tgt_f = fld.get("target", "?")
                        direction = fld.get("direction", "source_to_target")
                        mapping_lines.append(f"  - {src_f} -> {tgt_f} ({direction})")
                else:
                    src_f = m.get("source_field", "?")
                    tgt_f = m.get("target_field", "?")
                    direction = m.get("sync_direction", "unidirectional")
                    freq = m.get("sync_frequency", "batch")
                    mapping_lines.append(f"  - {src_f} -> {tgt_f} ({direction}, {freq})")

                if src_obj:
                    fdw_server = "sfdc_itxp2dev"
                    relationships.append(OntoRelationship(
                        relation_type="syncs_to",
                        target_id=OntoDocument.generate_id(fdw_server, src_obj, entity_type="Schema"),
                        description=f"Source object {src_obj} in {source_sys}",
                    ))
                if tgt_obj:
                    relationships.append(OntoRelationship(
                        relation_type="syncs_to",
                        target_id=OntoDocument.generate_id("Oracle", tgt_obj, entity_type="Schema"),
                        description=f"Target object {tgt_obj} in {target_sys}",
                    ))

            fdw_server = "sfdc_itxp2dev"
            for dep in integ.get("dependencies", []):
                if isinstance(dep, dict):
                    entity = dep.get("entity", "")
                    rel_desc = dep.get("relationship", "")
                    dep_system = dep.get("system", "")
                    if entity:
                        if dep_system and dep_system.lower() in ("oracle", "erp"):
                            tid = OntoDocument.generate_id("Oracle", entity, entity_type="Schema")
                        elif dep_system and dep_system.lower() == "internal":
                            tid = OntoDocument.generate_id("Internal", entity, entity_type="Workflow")
                        else:
                            tid = OntoDocument.generate_id(fdw_server, entity, entity_type="Schema")
                        relationships.append(OntoRelationship(
                            relation_type="depends_on",
                            target_id=tid,
                            description=rel_desc,
                        ))

            content = (
                f"Integration: {name}\n"
                f"Source: {source_sys}\n"
                f"Target: {target_sys}\n"
                f"Field Mappings:\n" + "\n".join(mapping_lines)
            )

            related_entities = integ.get("related_entities", [])
            triggered_by = integ.get("triggered_by_workflows", [])
            used_by_apps = integ.get("used_by_apps", [])

            if related_entities:
                content += "\nRelated Entities: " + ", ".join(str(e) for e in related_entities)
            if triggered_by:
                content += "\nTriggered By Workflows: " + ", ".join(str(w) for w in triggered_by)
            if used_by_apps:
                content += "\nUsed By Applications: " + ", ".join(str(a) for a in used_by_apps)

            meta = {
                "source_file": filename,
                "source_system": source_sys,
                "target_system": target_sys,
                "mapping_count": len(mappings),
            }
            if related_entities:
                meta["related_entities"] = related_entities
            if triggered_by:
                meta["triggered_by_workflows"] = triggered_by
            if used_by_apps:
                meta["used_by_apps"] = used_by_apps

            doc_id = OntoDocument.generate_id(source_sys, name, entity_type="Integration")
            docs.append(OntoDocument(
                id=doc_id,
                system=source_sys,
                entity_type="Integration",
                object_name=name,
                category="integration",
                content=content,
                source="integration_map",
                structured_metadata=meta,
                relationships=relationships,
            ))

        self._info(f"  Parsed {len(docs)} integration mappings from {filename}")
        return docs
