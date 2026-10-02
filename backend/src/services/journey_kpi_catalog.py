"""
Journey KPI Catalog.

Maps a journey's ``solution_id`` to the labels, icon name, and accent color
that the Journey Studio header should render for the **primary** KPI card
(the value itself comes from the universal ``metrics.itemsProcessed`` field
on each Job item).

The catalog is mirrored on the frontend in
``nexus-ui/src/config/journeyKpiCatalog.ts`` so the React JSX can render
lucide icons by string name without an extra round-trip; this module is the
backend source of truth and is what
``GET /api/v1/journeys/{id}`` exposes via the ``kpi_definition`` field.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


KPI_CATALOG: Dict[str, Dict[str, Any]] = {
    "order-to-cash": {
        "primary": {"label": "Orders Processed", "icon": "ShoppingCart", "color": "green"},
    },
    "demand-forecasting": {
        "primary": {"label": "Forecasts Generated", "icon": "TrendingUp", "color": "blue"},
    },
    "inventory-optimization": {
        "primary": {"label": "SKUs Optimized", "icon": "Boxes", "color": "purple"},
    },
    "procurement-analytics": {
        "primary": {"label": "POs Analyzed", "icon": "FileBarChart", "color": "amber"},
    },
    "production-quality": {
        "primary": {"label": "Production Runs Scored", "icon": "Factory", "color": "indigo"},
    },
    "supply-chain-risk": {
        "primary": {"label": "Vendors Risk-Scored", "icon": "AlertTriangle", "color": "red"},
    },
    "customer-360": {
        "primary": {"label": "Accounts Analyzed", "icon": "Users", "color": "cyan"},
    },
    "esg-sustainability": {
        "primary": {"label": "ESG Plants Analyzed", "icon": "Leaf", "color": "emerald"},
    },
    "call-processing": {
        "primary": {"label": "Calls Processed", "icon": "Phone", "color": "sky"},
    },
    "_default": {
        "primary": {"label": "Items Processed", "icon": "Activity", "color": "slate"},
    },
}


def get_definition(solution_id: Optional[str]) -> Dict[str, Any]:
    """Return the KPI definition for a given solution_id.

    Falls back to the ``_default`` row when ``solution_id`` is None or
    not present in the catalog.
    """
    if not solution_id:
        return KPI_CATALOG["_default"]
    return KPI_CATALOG.get(solution_id, KPI_CATALOG["_default"])
