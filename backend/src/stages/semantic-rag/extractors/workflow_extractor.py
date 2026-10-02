"""
Workflow Rules Extractor

Parses workflow definitions (YAML/JSON files describing approval flows,
SLAs, triggers, and process sequences) into OntoDocument objects.

Expected workflow file format (YAML or JSON):
  workflows:
    - name: Credit Approval Flow
      trigger: credit_limit_change > 10%
      steps:
        - action: submit_for_approval
          approver_role: Finance Manager
          sla_hours: 24
        - action: sync_to_erp
          system: Oracle
      constraints:
        - blocked_during: financial_close
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


class WorkflowExtractor:
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
            self._info("No workflow definitions found — skipping")

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

        self._info(f"Found {len(files)} workflow files in {path}")
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

        workflows = data.get("workflows", [])
        if not workflows and isinstance(data, dict):
            workflows = [data]

        docs = []
        for i, wf in enumerate(workflows):
            if not isinstance(wf, dict):
                continue

            name = wf.get("name", f"Workflow_{filename}_{i}")
            trigger = wf.get("trigger", "")
            steps = wf.get("steps", [])
            constraints = wf.get("constraints", [])

            steps_text = "\n".join(
                f"  {j+1}. {s.get('action', 'unknown')}"
                + (f" (approver: {s['approver_role']})" if 'approver_role' in s else "")
                + (f" (SLA: {s['sla_hours']}h)" if 'sla_hours' in s else "")
                for j, s in enumerate(steps) if isinstance(s, dict)
            )
            constraints_text = "\n".join(
                f"  - {c}" if isinstance(c, str) else f"  - {json.dumps(c)}"
                for c in constraints
            )

            content = f"Workflow: {name}\nTrigger: {trigger}\n"
            if steps_text:
                content += f"Steps:\n{steps_text}\n"
            if constraints_text:
                content += f"Constraints:\n{constraints_text}\n"

            use_case = wf.get("use_case", "")
            scor_process = wf.get("scor_process", "")
            related_entities = wf.get("related_entities", [])
            related_policies = wf.get("related_policies", [])

            if use_case:
                content += f"Use Case: {use_case}\n"
            if scor_process:
                content += f"SCOR Process: {scor_process}\n"
            if related_entities:
                content += "Related Entities: " + ", ".join(str(e) for e in related_entities) + "\n"
            if related_policies:
                content += "Related Policies: " + ", ".join(str(p) for p in related_policies) + "\n"

            relationships = []
            for s in steps:
                if isinstance(s, dict) and s.get("system"):
                    relationships.append(OntoRelationship(
                        relation_type="syncs_to",
                        target_id=s["system"],
                        description=f"Step '{s.get('action', '')}' interacts with {s['system']}",
                    ))

            fdw_server = "sfdc_itxp2dev"
            for dep in wf.get("dependencies", []):
                if isinstance(dep, dict):
                    entity = dep.get("entity", "")
                    rel_desc = dep.get("relationship", "")
                    dep_system = dep.get("system", "")
                    if entity:
                        if dep_system and dep_system.lower() in ("oracle", "erp"):
                            tid = OntoDocument.generate_id("Oracle", entity, entity_type="Schema")
                        elif dep_system and dep_system.lower() == "internal":
                            tid = OntoDocument.generate_id("Internal", entity, entity_type="Policy")
                        else:
                            tid = OntoDocument.generate_id(fdw_server, entity, entity_type="Schema")
                        relationships.append(OntoRelationship(
                            relation_type="depends_on",
                            target_id=tid,
                            description=rel_desc,
                        ))

            doc_id = OntoDocument.generate_id("Internal", name, entity_type="Workflow")
            meta = {
                "source_file": filename, "trigger": trigger,
                "step_count": len(steps),
            }
            if use_case:
                meta["use_case"] = use_case
            if scor_process:
                meta["scor_process"] = scor_process
            if related_entities:
                meta["related_entities"] = related_entities
            if related_policies:
                meta["related_policies"] = related_policies

            docs.append(OntoDocument(
                id=doc_id,
                system="Internal",
                entity_type="Workflow",
                object_name=name,
                category="workflow",
                content=content,
                source="workflow_def",
                structured_metadata=meta,
                relationships=relationships,
            ))

        self._info(f"  Parsed {len(docs)} workflows from {filename}")
        return docs
