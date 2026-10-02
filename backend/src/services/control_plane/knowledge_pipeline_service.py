"""
Knowledge Pipeline registry (Control plane, Phase 3.4)

Small facade over ``KP#`` rows in foundry-workspace. Purpose:
- ``KP#{pipeline_id}`` / ``META``  - pipeline registry entry (id, name,
  description, stage_ids, etc.). Currently a single entry for the
  Knowledge Processor / semantic_rag pipeline; the shape leaves room for
  future pipelines (solutions indexer, tools reindex).
- ``KP#{pipeline_id}`` / ``RUN#{iso_ts}`` - lightweight run summary
  (duration_ms, top-level counts, error tail). Full logs continue to
  live in S3 journey-logs.

Bootstrap seeds a single ``semantic_rag`` pipeline entry at startup so
``/api/v1/knowledge-pipelines`` returns something even before the first
Knowledge Processor run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_KNOWN_PIPELINES = [
    {
        "pipelineId": "semantic_rag",
        "name": "Knowledge Processor",
        "description": (
            "Extracts schemas/policies/workflows/integrations from foundry-workspace "
            "and materializes pgvector Knowledge Index + Apache AGE Knowledge Graph."
        ),
        "stageIds": ["semantic_rag"],
        "outputs": ["control_plane_embeddings", "enterprise_onto"],
    },
]


class KnowledgePipelineService:
    _instance: Optional["KnowledgePipelineService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "KnowledgePipelineService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------- reads --------

    async def list(self) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_kps()
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"KnowledgePipeline list failed: {e}")
            return []

    async def get(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._repo.get_kp(pipeline_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"KnowledgePipeline get({pipeline_id}) failed: {e}")
            return None

    async def list_runs(self, pipeline_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_kp_runs(pipeline_id, limit=limit)
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"KnowledgePipeline list_runs({pipeline_id}) failed: {e}")
            return []

    # -------- writes --------

    async def upsert(self, pipeline_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs["pipelineId"] = pipeline_id
        attrs.setdefault("updatedAt", _now_iso())
        try:
            return self._repo.put_kp(pipeline_id, attrs)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"KnowledgePipeline upsert({pipeline_id}) failed: {e}")
            raise

    async def record_run(
        self,
        pipeline_id: str,
        summary: Dict[str, Any],
        *,
        iso_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = iso_ts or _now_iso()
        try:
            return self._repo.put_kp_run(pipeline_id, ts, summary)
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"KnowledgePipeline record_run({pipeline_id}) failed: {e}")
            return {}

    # -------- bootstrap --------

    async def bootstrap_defaults(self) -> int:
        try:
            existing = {r.get("pipelineId") for r in self._repo.list_kps()}
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"KnowledgePipeline bootstrap list failed: {e}")
            return 0
        written = 0
        for entry in _KNOWN_PIPELINES:
            if entry["pipelineId"] in existing:
                continue
            try:
                self._repo.put_kp(entry["pipelineId"], entry)
                written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"KnowledgePipeline bootstrap upsert failed: {e}")
        if written:
            logger.info(f"KnowledgePipeline bootstrapped {written} default pipelines")
        return written


def get_knowledge_pipeline_service() -> KnowledgePipelineService:
    return KnowledgePipelineService.get_instance()
