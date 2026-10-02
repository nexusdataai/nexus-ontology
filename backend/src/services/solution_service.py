"""
Solution Service

Manages Solutions and their ordered list of associated Views ("Solution
Mapping"). A Solution is stored as a single META item in the foundry-workspace
DynamoDB table; its views are embedded inline as a JSON string attribute
(viewsJson). One PutItem per save, no TransactWriteItems.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
    solution_pk,
    view_pk,
)

ss_logger = logger.bind(component="solution-service")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_views(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = item.get("viewsJson")
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        ss_logger.warning(f"viewsJson parse failed: {e}")
    return []


def _project_view_link(link: Dict[str, Any], order: int) -> Dict[str, Any]:
    return {
        "viewId": link.get("viewId") or "",
        "order": order,
        "displayName": link.get("displayName") or link.get("display_name"),
    }


class SolutionService:
    """Solution CRUD + view association (single-item DynamoDB storage)."""

    def __init__(self, repository: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repository or FoundryWorkspaceRepository()
        ss_logger.info("SolutionService initialized", table=self._repo.table_name)

    # -----------------------------------------------------------------------
    # CRUD
    # -----------------------------------------------------------------------

    async def create(self, payload: dict, user: str = "anonymous") -> dict:
        solution_id = (
            payload.get("solutionId") or payload.get("solution_id") or str(uuid4())
        )
        now = _now()
        view_links_raw = payload.get("views") or []
        view_links = [
            _project_view_link(v, i) for i, v in enumerate(view_links_raw)
        ]
        solution = {
            "solutionId": solution_id,
            "name": payload.get("name", "New Solution"),
            "description": payload.get("description"),
            "appId": payload.get("appId") or payload.get("app_id"),
            "icon": payload.get("icon"),
            "version": 1,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": user,
            "views": view_links,
        }
        self._save_solution(solution)
        ss_logger.info("Solution created", solutionId=solution_id, name=solution["name"])
        return await self.get(solution_id) or solution

    async def update(self, solution_id: str, payload: dict, user: str = "anonymous") -> dict:
        existing = await self.get(solution_id)
        if not existing:
            raise ValueError(f"Solution not found: {solution_id}")

        incoming_version = payload.get("version", 0)
        if incoming_version and incoming_version != int(existing.get("version", 0) or 0):
            raise ValueError(
                f"Version conflict: expected {existing.get('version')}, got {incoming_version}"
            )

        existing.update({
            "name": payload.get("name", existing.get("name", "")),
            "description": payload.get("description", existing.get("description")),
            "appId": payload.get("appId")
            or payload.get("app_id")
            or existing.get("appId"),
            "icon": payload.get("icon", existing.get("icon")),
            "version": int(existing.get("version", 0) or 0) + 1,
            "updatedAt": _now(),
        })
        self._save_solution(existing)
        return await self.get(solution_id) or existing

    async def delete(self, solution_id: str) -> bool:
        try:
            self._repo.delete_pk(solution_pk(solution_id))
            return True
        except FoundryWorkspaceRepositoryError as e:
            ss_logger.warning(f"Solution delete failed for {solution_id}: {e}")
            return False

    async def get(self, solution_id: str) -> Optional[dict]:
        item = self._repo.get_meta(solution_pk(solution_id))
        if not item:
            return None
        return self._enrich(item)

    async def get_by_app_id(self, app_id: str) -> Optional[dict]:
        rows = self._repo.query_gsi1("SOLUTION")
        for row in rows:
            if row.get("appId") == app_id:
                return self._enrich(row)
        return None

    async def list_all(self, search: str = "") -> List[dict]:
        rows = self._repo.query_gsi1("SOLUTION")
        items: List[dict] = []
        for row in rows:
            views = _parse_views(row)
            items.append({
                "solutionId": row.get("solutionId"),
                "name": row.get("name", ""),
                "description": row.get("description"),
                "appId": row.get("appId"),
                "icon": row.get("icon"),
                "viewCount": len(views),
                "createdAt": row.get("createdAt", ""),
                "updatedAt": row.get("updatedAt", ""),
                "createdBy": row.get("createdBy", ""),
            })
        if search:
            q = search.lower()
            items = [
                i for i in items
                if q in (i.get("name") or "").lower()
                or q in (i.get("description") or "").lower()
            ]
        items.sort(key=lambda i: (i.get("name") or "").lower())
        return items

    # -----------------------------------------------------------------------
    # View associations
    # -----------------------------------------------------------------------

    async def add_view(
        self,
        solution_id: str,
        view_id: str,
        position: Optional[int] = None,
        display_name: Optional[str] = None,
    ) -> dict:
        solution = await self.get(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")
        if not self._repo.get_meta(view_pk(view_id)):
            raise ValueError(f"View not found: {view_id}")

        views = list(solution.get("views") or [])
        if any(v.get("viewId") == view_id for v in views):
            raise ValueError(f"View {view_id} already linked to solution {solution_id}")

        new_link = {"viewId": view_id, "displayName": display_name}
        if position is None or position < 0 or position > len(views):
            views.append(new_link)
        else:
            views.insert(position, new_link)

        solution["views"] = [_project_view_link(v, i) for i, v in enumerate(views)]
        solution["updatedAt"] = _now()
        self._save_solution(solution)
        return await self.get(solution_id) or solution

    async def remove_view(self, solution_id: str, view_id: str) -> dict:
        solution = await self.get(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")
        views = [v for v in (solution.get("views") or []) if v.get("viewId") != view_id]
        solution["views"] = [_project_view_link(v, i) for i, v in enumerate(views)]
        solution["updatedAt"] = _now()
        self._save_solution(solution)
        return await self.get(solution_id) or solution

    async def reorder_views(self, solution_id: str, view_ids: List[str]) -> dict:
        solution = await self.get(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")
        views = list(solution.get("views") or [])
        existing_ids = {v.get("viewId") for v in views if v.get("viewId")}
        if set(view_ids) != existing_ids:
            raise ValueError("reorder_views must contain exactly the existing view ids")
        by_id = {v.get("viewId"): v for v in views}
        ordered = [by_id[vid] for vid in view_ids]
        solution["views"] = [_project_view_link(v, i) for i, v in enumerate(ordered)]
        solution["updatedAt"] = _now()
        self._save_solution(solution)
        return await self.get(solution_id) or solution

    def remove_view_inplace(self, solution_id: str, view_id: str) -> bool:
        """Synchronous, idempotent removal of a viewId from a solution's views.
        Used by ViewService.delete to clean up backrefs after a view is gone.
        Returns True if a removal happened (the solution was rewritten)."""
        item = self._repo.get_meta(solution_pk(solution_id))
        if not item:
            return False
        views = _parse_views(item)
        kept = [v for v in views if v.get("viewId") != view_id]
        if len(kept) == len(views):
            return False
        solution = self._enrich(item)
        solution["views"] = [_project_view_link(v, i) for i, v in enumerate(kept)]
        solution["updatedAt"] = _now()
        self._save_solution(solution)
        return True

    # -----------------------------------------------------------------------
    # Persistence helpers
    # -----------------------------------------------------------------------

    def _save_solution(self, solution: Dict[str, Any]) -> None:
        solution_id = solution.get("solutionId")
        if not solution_id:
            raise ValueError("solution.solutionId is required to save")
        views = [_project_view_link(v, i) for i, v in enumerate(solution.get("views") or [])]
        attrs = {
            "solutionId": solution_id,
            "name": solution.get("name", ""),
            "description": solution.get("description"),
            "appId": solution.get("appId"),
            "icon": solution.get("icon"),
            "version": int(solution.get("version", 1) or 1),
            "createdAt": solution.get("createdAt", ""),
            "updatedAt": solution.get("updatedAt", ""),
            "createdBy": solution.get("createdBy", ""),
            "viewsJson": json.dumps(views, default=str),
            "viewCount": len(views),
        }
        try:
            self._repo.put_meta(
                pk=solution_pk(solution_id),
                attrs=attrs,
                gsi1pk="SOLUTION",
                gsi1sk=(attrs["name"] or "").lower(),
            )
        except FoundryWorkspaceRepositoryError as e:
            ss_logger.error(f"Failed to save solution {solution_id}: {e}")
            raise

    def _enrich(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a META item (with viewsJson) into a Solution dict; enrich
        each linked view with its current name (best-effort)."""
        views_raw = _parse_views(item)
        enriched: List[Dict[str, Any]] = []
        for i, link in enumerate(views_raw):
            view_id = link.get("viewId") or ""
            name = None
            if view_id:
                view_meta = self._repo.get_meta(view_pk(view_id))
                if view_meta:
                    name = view_meta.get("name")
            enriched.append({
                "viewId": view_id,
                "order": i,
                "name": name,
                "displayName": link.get("displayName"),
            })
        return {
            "solutionId": item.get("solutionId")
            or str(item.get("PK", "")).split("#", 1)[-1],
            "name": item.get("name", ""),
            "description": item.get("description"),
            "appId": item.get("appId"),
            "icon": item.get("icon"),
            "version": int(item.get("version", 0) or 0),
            "createdAt": item.get("createdAt", ""),
            "updatedAt": item.get("updatedAt", ""),
            "createdBy": item.get("createdBy", ""),
            "views": enriched,
        }
