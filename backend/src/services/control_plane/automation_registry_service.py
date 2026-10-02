"""
Automation Registry service (Workspace / Control Plane, Phase 3.2)

DDB-backed store for automation playbook YAML definitions
(``AUTOMATION#{use_case_id}`` rows). Playbooks used to live only on disk
under ``enterprise-knowledge/automation/<solution>/*.yaml``; the spec
requires them in DynamoDB so backup/restore is uniform and the frontend
can browse them without a filesystem hop.

Row shape:
- ``useCaseId``: slug (also the row's PK suffix)
- ``solution``: parent directory name (e.g. ``order-to-cash``)
- ``sourceFile``: original filename
- ``yamlText``: raw YAML content (durable, portable)
- ``updatedAt``, ``createdAt``

The indexer (``AutomationIndexer``) can then materialize DDB rows into a
temp directory for its existing file-based extractors, keeping the code
path minimally invasive.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutomationRegistryService:
    _instance: Optional["AutomationRegistryService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "AutomationRegistryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------- reads -------

    async def list(self, solution: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_automations(solution)
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"AutomationRegistry list failed: {e}")
            return []

    async def get(self, use_case_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._repo.get_automation(use_case_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"AutomationRegistry get({use_case_id}) failed: {e}")
            return None

    # ------- writes -------

    async def upsert(
        self,
        use_case_id: str,
        solution: str,
        yaml_text: str,
        *,
        source_file: str = "",
    ) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {
            "useCaseId": use_case_id,
            "solution": solution,
            "sourceFile": source_file or f"{use_case_id}.yaml",
            "yamlText": yaml_text,
            "sizeBytes": len(yaml_text.encode("utf-8")),
            "updatedAt": _now_iso(),
        }
        try:
            return self._repo.put_automation(use_case_id, attrs)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"AutomationRegistry upsert({use_case_id}) failed: {e}")
            raise

    async def delete(self, use_case_id: str) -> int:
        try:
            return self._repo.delete_automation(use_case_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"AutomationRegistry delete({use_case_id}) failed: {e}")
            return 0

    # ------- bootstrap -------

    async def bootstrap_from_disk(self, root: Path, force: bool = False) -> int:
        """Seed AUTOMATION# rows from ``root/<solution>/*.yaml``.

        If ``force`` is false (default), skip when any AUTOMATION# rows
        already exist. Returns the number of rows written.
        """
        if not root.is_dir():
            return 0
        try:
            existing = self._repo.list_automations()
        except FoundryWorkspaceRepositoryError:
            existing = []
        if existing and not force:
            return 0

        written = 0
        for solution_dir in sorted(root.iterdir()):
            if not solution_dir.is_dir():
                continue
            solution = solution_dir.name
            for yml in sorted(solution_dir.glob("*.yaml")):
                use_case_id = yml.stem
                try:
                    yaml_text = yml.read_text(encoding="utf-8")
                    await self.upsert(
                        use_case_id,
                        solution=solution,
                        yaml_text=yaml_text,
                        source_file=yml.name,
                    )
                    written += 1
                except Exception as e:
                    logger.warning(f"AutomationRegistry bootstrap {yml}: {e}")
        if written:
            logger.info(f"AutomationRegistry bootstrapped {written} playbooks from {root}")
        return written

    async def materialize_to_tempdir(self) -> Optional[Path]:
        """Write every AUTOMATION# row to disk mirroring the historical
        directory shape (``<tmp>/<solution>/<use_case_id>.yaml``) so the
        existing ``AutomationIndexer`` file walker can consume DDB rows
        without a wider refactor. Returns the tempdir path, or ``None``
        if DDB is empty."""
        try:
            rows = self._repo.list_automations()
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"AutomationRegistry materialize list failed: {e}")
            return None
        if not rows:
            return None
        tempdir = Path(tempfile.mkdtemp(prefix="automation-ddb-"))
        for row in rows:
            solution = str(row.get("solution") or "misc")
            uc_id = str(row.get("useCaseId") or row.get("PK", "").split("#", 1)[-1])
            yaml_text = str(row.get("yamlText") or "")
            if not uc_id or not yaml_text:
                continue
            (tempdir / solution).mkdir(parents=True, exist_ok=True)
            (tempdir / solution / f"{uc_id}.yaml").write_text(yaml_text, encoding="utf-8")
        return tempdir


def get_automation_registry() -> AutomationRegistryService:
    return AutomationRegistryService.get_instance()


def is_ddb_automation_registry_enabled() -> bool:
    return (os.getenv("USE_DDB_AUTOMATION_REGISTRY", "true").strip().lower() != "false")
