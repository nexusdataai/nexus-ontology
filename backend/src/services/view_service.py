"""
View Service

Manages View metadata and tabbed dashboard composition. A View is stored as a
single META item in the foundry-workspace DynamoDB table; its ordered list of
tabs is embedded inline as a JSON string attribute (tabsJson). This avoids
TransactWriteItems entirely and matches the inline-payload pattern used for
Dashboards.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
    dashboard_pk,
    view_pk,
)

vs_logger = logger.bind(component="view-service")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_tabs(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = item.get("tabsJson")
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        vs_logger.warning(f"tabsJson parse failed: {e}")
    return []


def _renumber_tabs(tabs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for i, tab in enumerate(tabs):
        tab["order"] = i
    return tabs


def _project_tab(tab: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a tab dict into the canonical client-facing shape."""
    return {
        "tabId": tab.get("tabId") or str(uuid4()),
        "order": int(tab.get("order", 0) or 0),
        "label": tab.get("label", "Tab"),
        "icon": tab.get("icon"),
        "dashboardId": tab.get("dashboardId") or "",
        "simulatorRefs": list(tab.get("simulatorRefs") or []),
        "timeOverride": tab.get("timeOverride"),
    }


class ViewService:
    """View CRUD + tab management (single-item DynamoDB storage)."""

    def __init__(self, repository: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repository or FoundryWorkspaceRepository()
        vs_logger.info("ViewService initialized", table=self._repo.table_name)

    # -----------------------------------------------------------------------
    # CRUD
    # -----------------------------------------------------------------------

    async def create(self, payload: dict, user: str = "anonymous") -> dict:
        view_id = payload.get("viewId") or payload.get("view_id") or str(uuid4())
        now = _now()
        tabs = _renumber_tabs(
            [_project_tab(t) for t in (payload.get("tabs") or [])]
        )
        view = {
            "viewId": view_id,
            "name": payload.get("name", "New View"),
            "description": payload.get("description"),
            "tags": list(payload.get("tags") or []),
            "defaultTabId": payload.get("defaultTabId") or payload.get("default_tab_id"),
            "version": 1,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": user,
            "tabs": tabs,
        }
        self._save_view(view)
        vs_logger.info("View created", viewId=view_id, name=view["name"])
        return view

    async def update(self, view_id: str, payload: dict, user: str = "anonymous") -> dict:
        existing = await self.get(view_id)
        if not existing:
            raise ValueError(f"View not found: {view_id}")

        incoming_version = payload.get("version", 0)
        if incoming_version and incoming_version != int(existing.get("version", 0) or 0):
            raise ValueError(
                f"Version conflict: expected {existing.get('version')}, got {incoming_version}"
            )

        now = _now()
        existing.update({
            "name": payload.get("name", existing.get("name", "")),
            "description": payload.get("description", existing.get("description")),
            "tags": list(
                payload.get("tags")
                if payload.get("tags") is not None
                else (existing.get("tags") or [])
            ),
            "defaultTabId": payload.get("defaultTabId")
            or payload.get("default_tab_id")
            or existing.get("defaultTabId"),
            "version": int(existing.get("version", 0) or 0) + 1,
            "updatedAt": now,
        })
        self._save_view(existing)
        return existing

    async def delete(self, view_id: str) -> bool:
        try:
            self._repo.delete_pk(view_pk(view_id))
        except FoundryWorkspaceRepositoryError as e:
            vs_logger.warning(f"View delete failed for {view_id}: {e}")
            return False

        # Clean up references in any Solution viewsJson that include this view.
        try:
            self._cleanup_solution_backrefs(view_id)
        except Exception as e:
            vs_logger.warning(f"Failed to clean view backrefs for {view_id}: {e}")
        return True

    async def get(self, view_id: str) -> Optional[dict]:
        item = self._repo.get_meta(view_pk(view_id))
        if not item:
            return None
        return self._project_view(item)

    async def list_all(self, search: str = "", tags: Optional[List[str]] = None) -> List[dict]:
        rows = self._repo.query_gsi1("VIEW")
        items: List[dict] = []
        for row in rows:
            view = self._project_view(row)
            items.append({
                "viewId": view["viewId"],
                "name": view["name"],
                "description": view.get("description"),
                "tags": view.get("tags", []),
                "tabCount": len(view.get("tabs", [])),
                "createdAt": view.get("createdAt", ""),
                "updatedAt": view.get("updatedAt", ""),
                "createdBy": view.get("createdBy", ""),
            })

        if search:
            q = search.lower()
            items = [
                i for i in items
                if q in (i.get("name") or "").lower()
                or q in (i.get("description") or "").lower()
            ]
        if tags:
            tag_set = set(tags)
            items = [i for i in items if tag_set.intersection(set(i.get("tags") or []))]

        items.sort(key=lambda i: i.get("updatedAt", ""), reverse=True)
        return items

    # -----------------------------------------------------------------------
    # Tab management — all paths go through a single put_item via _save_view.
    # -----------------------------------------------------------------------

    async def add_tab(self, view_id: str, payload: dict) -> dict:
        view = await self.get(view_id)
        if not view:
            raise ValueError(f"View not found: {view_id}")
        dashboard_id = payload.get("dashboardId") or payload.get("dashboard_id")
        if not dashboard_id:
            raise ValueError("dashboardId is required")
        if not self._repo.get_meta(dashboard_pk(dashboard_id)):
            raise ValueError(f"Dashboard not found: {dashboard_id}")

        tabs = list(view.get("tabs") or [])
        tab_id = payload.get("tabId") or payload.get("tab_id") or str(uuid4())
        if any(t.get("tabId") == tab_id for t in tabs):
            raise ValueError(f"Tab id already exists: {tab_id}")

        new_tab = _project_tab({
            "tabId": tab_id,
            "label": payload.get("label", "Tab"),
            "icon": payload.get("icon"),
            "dashboardId": dashboard_id,
            "simulatorRefs": payload.get("simulatorRefs") or [],
            "timeOverride": payload.get("timeOverride") or payload.get("time_override"),
        })

        position = payload.get("position")
        if position is None or position < 0 or position > len(tabs):
            tabs.append(new_tab)
        else:
            tabs.insert(position, new_tab)

        view["tabs"] = _renumber_tabs(tabs)
        view["updatedAt"] = _now()
        self._save_view(view)
        return view

    async def update_tab(self, view_id: str, tab_id: str, payload: dict) -> dict:
        view = await self.get(view_id)
        if not view:
            raise ValueError(f"View not found: {view_id}")
        tabs = list(view.get("tabs") or [])
        if not any(t.get("tabId") == tab_id for t in tabs):
            raise ValueError(f"Tab not found: {tab_id}")

        new_dashboard_id = payload.get("dashboardId") or payload.get("dashboard_id")
        if new_dashboard_id and not self._repo.get_meta(dashboard_pk(new_dashboard_id)):
            raise ValueError(f"Dashboard not found: {new_dashboard_id}")

        next_tabs: List[Dict[str, Any]] = []
        for t in tabs:
            if t.get("tabId") == tab_id:
                next_tabs.append(_project_tab({
                    "tabId": tab_id,
                    "label": payload.get("label", t.get("label", "Tab")),
                    "icon": payload.get("icon", t.get("icon")),
                    "dashboardId": new_dashboard_id or t.get("dashboardId"),
                    "simulatorRefs": (
                        payload.get("simulatorRefs")
                        if payload.get("simulatorRefs") is not None
                        else t.get("simulatorRefs", [])
                    ),
                    "timeOverride": (
                        payload.get("timeOverride")
                        or payload.get("time_override")
                        or t.get("timeOverride")
                    ),
                }))
            else:
                next_tabs.append(_project_tab(t))

        view["tabs"] = _renumber_tabs(next_tabs)
        view["updatedAt"] = _now()
        self._save_view(view)
        return view

    async def remove_tab(self, view_id: str, tab_id: str) -> dict:
        view = await self.get(view_id)
        if not view:
            raise ValueError(f"View not found: {view_id}")
        tabs = [_project_tab(t) for t in view.get("tabs") or [] if t.get("tabId") != tab_id]
        view["tabs"] = _renumber_tabs(tabs)
        view["updatedAt"] = _now()
        self._save_view(view)
        return view

    async def reorder_tabs(self, view_id: str, tab_ids: List[str]) -> dict:
        view = await self.get(view_id)
        if not view:
            raise ValueError(f"View not found: {view_id}")
        tabs = list(view.get("tabs") or [])
        existing_ids = {t.get("tabId") for t in tabs if t.get("tabId")}
        if set(tab_ids) != existing_ids:
            raise ValueError("reorder_tabs must contain exactly the existing tab ids")
        by_id = {t.get("tabId"): t for t in tabs}
        next_tabs = [_project_tab(by_id[t]) for t in tab_ids]
        view["tabs"] = _renumber_tabs(next_tabs)
        view["updatedAt"] = _now()
        self._save_view(view)
        return view

    # -----------------------------------------------------------------------
    # Persistence helper
    # -----------------------------------------------------------------------

    def _save_view(self, view: Dict[str, Any]) -> None:
        view_id = view.get("viewId")
        if not view_id:
            raise ValueError("view.viewId is required to save")
        tabs = view.get("tabs") or []
        attrs = {
            "viewId": view_id,
            "name": view.get("name", ""),
            "description": view.get("description"),
            "tags": list(view.get("tags") or []),
            "defaultTabId": view.get("defaultTabId"),
            "version": int(view.get("version", 1) or 1),
            "createdAt": view.get("createdAt", ""),
            "updatedAt": view.get("updatedAt", ""),
            "createdBy": view.get("createdBy", ""),
            "tabsJson": json.dumps(tabs, default=str),
            "tabCount": len(tabs),
        }
        try:
            self._repo.put_meta(
                pk=view_pk(view_id),
                attrs=attrs,
                gsi1pk="VIEW",
                gsi1sk=(attrs["name"] or "").lower(),
            )
        except FoundryWorkspaceRepositoryError as e:
            vs_logger.error(f"Failed to save view {view_id}: {e}")
            raise

    def _project_view(self, item: Dict[str, Any]) -> Dict[str, Any]:
        tabs_raw = _parse_tabs(item)
        tabs = [_project_tab(t) for t in tabs_raw]
        return {
            "viewId": item.get("viewId") or str(item.get("PK", "")).split("#", 1)[-1],
            "name": item.get("name", ""),
            "description": item.get("description"),
            "tags": list(item.get("tags") or []),
            "defaultTabId": item.get("defaultTabId"),
            "version": int(item.get("version", 0) or 0),
            "createdAt": item.get("createdAt", ""),
            "updatedAt": item.get("updatedAt", ""),
            "createdBy": item.get("createdBy", ""),
            "tabs": tabs,
        }

    def _cleanup_solution_backrefs(self, view_id: str) -> None:
        """Remove this viewId from every Solution's embedded viewsJson list."""
        from src.services.solution_service import SolutionService

        # Lazy import to avoid a circular dependency at module load. Reuse this
        # repository so we share the same low-level client.
        sol_service = SolutionService(repository=self._repo)
        solutions = self._repo.query_gsi1("SOLUTION")
        for sol_meta in solutions:
            solution_id = sol_meta.get("solutionId")
            if not solution_id:
                continue
            try:
                sol_service.remove_view_inplace(solution_id, view_id)
            except Exception as e:
                vs_logger.warning(
                    f"Failed to remove view {view_id} from solution {solution_id}: {e}"
                )
