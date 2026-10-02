"""
Solutions YAML service (Workspace, Phase 5)

Backs the AI Solutions YAML registry (``SOLUTIONYAML#`` rows in
foundry-workspace). Distinct from the existing ``SOLUTION#`` PK - that
one is the runtime view-mapping record; ``SOLUTIONYAML#`` is the
structured product catalog with rich NLP-searchable content.

Row shape:
- ``solutionId``    : slug (matches AppDef.id in the frontend)
- ``title``         : display name
- ``description``   : multi-paragraph
- ``verticals[]``, ``personas[]``, ``categories[]``
- ``automations[]`` : list of use_case_id refs (Automation Registry)
- ``analytics[]``   : list of view_id refs (Analytics)
- ``nlq_examples[]``
- ``sourceYaml``    : raw YAML text for portability
- ``updatedAt``
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_seed_dir() -> Path:
    override = os.getenv("SOLUTIONS_YAML_SEED_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "enterprise-knowledge" / "solutions"


class SolutionsYamlService:
    _instance: Optional["SolutionsYamlService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "SolutionsYamlService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------- reads -------

    async def list(self) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_solution_yamls()
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"SolutionsYaml list failed: {e}")
            return []

    async def get(self, solution_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._repo.get_solution_yaml(solution_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"SolutionsYaml get({solution_id}) failed: {e}")
            return None

    # ------- writes -------

    async def upsert(self, solution_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs["solutionId"] = solution_id
        attrs.setdefault("updatedAt", _now_iso())
        try:
            return self._repo.put_solution_yaml(solution_id, attrs)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"SolutionsYaml upsert({solution_id}) failed: {e}")
            raise

    async def delete(self, solution_id: str) -> int:
        try:
            return self._repo.delete_solution_yaml(solution_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"SolutionsYaml delete({solution_id}) failed: {e}")
            return 0

    # ------- bootstrap -------

    async def bootstrap_from_files(self, seed_dir: Optional[Path] = None, force: bool = False) -> int:
        directory = seed_dir or _default_seed_dir()
        if not directory.is_dir():
            return 0
        try:
            existing = self._repo.list_solution_yamls()
        except FoundryWorkspaceRepositoryError:
            existing = []
        if existing and not force:
            return 0

        written = 0
        for yml in sorted(directory.glob("*.yaml")):
            try:
                text = yml.read_text(encoding="utf-8")
                doc = yaml.safe_load(text) or {}
                solution_id = str(doc.get("solutionId") or doc.get("id") or yml.stem)
                attrs = {
                    **doc,
                    "solutionId": solution_id,
                    "sourceYaml": text,
                    "sourceFile": yml.name,
                    "sizeBytes": len(text.encode("utf-8")),
                }
                await self.upsert(solution_id, attrs)
                written += 1
            except Exception as e:
                logger.warning(f"SolutionsYaml bootstrap parse {yml}: {e}")
        if written:
            logger.info(f"SolutionsYaml bootstrapped {written} solutions from {directory}")
        return written


def get_solutions_yaml_service() -> SolutionsYamlService:
    return SolutionsYamlService.get_instance()
