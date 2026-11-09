"""
Data Source Mode Service.

Single source of truth for the per-source "simulator vs real" routing
decision. Replaces five out-of-sync switches that existed before:

  - SSM ``{source}/enabled`` boolean (inverted naming, real-first default)
  - ``fdw_api?source=`` HTTP query param (HTTP-only)
  - ``VirtualQueryService`` "if simulator loaded" heuristic
  - Data Plane UI pill (useState only, no persistence)
  - Settings panel writing the legacy boolean

Reads ``data_source_mode/{source}`` from SSM; auto-migrates the legacy
``{source}/enabled`` boolean on first read (``true`` -> ``simulator``,
``false`` -> ``real``). Default mode is ``simulator`` for every source -
real mode requires an explicit admin opt-in via
``PUT /api/v1/data-source-mode/{source}``.

Used by:
  - ``fdw_tools`` (``query_table`` / ``discover_*``)
  - ``VirtualQueryService.query_virtual_entity``
  - ``fdw_api`` (default when ``?source=`` is omitted)
  - ``virtual_query_tools.get_entity_schema``
  - ReAct tool diagnostics canary runner

The service is process-local with an in-memory cache; ``set_mode``
invalidates the cache and fires a callback so any subscribers (e.g. the
simulator services) can hot-reload state.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional

from loguru import logger

dsm_logger = logger.bind(component="data-source-mode")


Mode = Literal["simulator", "real"]
ModeChangeCallback = Callable[[str, str], Optional[Awaitable[None]]]


class DataSourceModeService:
    """SSM-backed per-source mode resolver.

    Sources are 1:1 with the cards on the Data Plane page so the
    ``simulator | real`` summary count matches what the user sees.
    Today three of them (``file_uploads`` / ``google_drive`` /
    ``social_listening``) all route to the single ``external``
    simulator service; if real mode is wired for one of them later
    the others are unaffected because the resolver tracks each
    independently.
    """

    SOURCES: List[str] = [
        "sfdc",
        "oracle",
        "sap",
        "file_uploads",
        "google_drive",
        "social_listening",
        "tpm",
        "sourcing",
    ]
    DEFAULT_MODE: Mode = "simulator"

    # Map a foreign-table schema (as it appears in mapping rules) onto a
    # mode source. ``external_sources`` is shared across the three
    # external sub-sources today; we point it at ``file_uploads`` as the
    # canonical key (the simulator is unified, so any of the three would
    # resolve to the same backing store - this just picks one for tag
    # purposes when the canary records the executed mode).
    SCHEMA_TO_SOURCE: Dict[str, str] = {
        "sfdc_schema":     "sfdc",
        "sfdc_itxp2dev":   "sfdc",  # legacy
        "salesforce":      "sfdc",
        "oracle_erp":      "oracle",
        "sap_s4hana":      "sap",
        "external_sources": "file_uploads",
        "tpm_cpq":         "tpm",
        "sourcing_cpq":    "sourcing",
    }

    # Legacy SSM `{cat}/enabled` boolean keys. Read once on init, then
    # written forward into the canonical ``data_source_mode/{source}``
    # key. ``enabled=true`` means simulator mode is on.
    LEGACY_ENABLED_CATEGORY: Dict[str, str] = {
        "sfdc":     "sfdc",
        "oracle":   "oracle-erp",
        "sap":      "sap",
        # external sub-sources had no legacy `enabled` key - default simulator.
    }

    # Legacy aggregate ``data_source_mode/external`` key fans out into
    # the three sub-source keys when present (forward-migration only;
    # the aggregate key is left in SSM as a stable artefact).
    LEGACY_AGGREGATE_SOURCES: Dict[str, str] = {
        "file_uploads":     "external",
        "google_drive":     "external",
        "social_listening": "external",
    }

    def __init__(
        self,
        ssm_loader: Any = None,
        capability_name: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> None:
        self._ssm = ssm_loader
        self._capability = capability_name or os.getenv("CAPABILITY_NAME", "call-processing")
        self._environment = environment or os.getenv("ENVIRONMENT", "dev")
        self._cache: Dict[str, Mode] = {}
        self._initialized = False
        self._listeners: List[ModeChangeCallback] = []

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Read each source's mode from SSM (with legacy migration) and
        seed the in-memory cache. Idempotent."""
        if self._initialized:
            return
        loop = asyncio.get_event_loop()
        for source in self.SOURCES:
            try:
                mode = await loop.run_in_executor(None, self._read_mode_for_source, source)
                self._cache[source] = mode
            except Exception as e:
                dsm_logger.warning(
                    "Mode read failed for {}: {}; defaulting to {}",
                    source, e, self.DEFAULT_MODE,
                )
                self._cache[source] = self.DEFAULT_MODE
        self._initialized = True
        dsm_logger.info("Data source modes initialized: {}", self._cache)

    def add_listener(self, cb: ModeChangeCallback) -> None:
        """Register a callback fired when ``set_mode`` mutates a source.

        The callback receives ``(source, new_mode)``. Async callbacks are
        awaited; sync callbacks are invoked directly. Any exception is
        logged and swallowed.
        """
        self._listeners.append(cb)

    # ------------------------------------------------------------------
    # Public resolver
    # ------------------------------------------------------------------

    def effective_mode(self, source: Optional[str]) -> Mode:
        """Return ``simulator`` or ``real`` for the given source.

        Unknown sources fall back to ``simulator`` (safe default).
        """
        if not source:
            return self.DEFAULT_MODE
        normalized = source.lower()
        return self._cache.get(normalized, self.DEFAULT_MODE)

    def all_modes(self) -> Dict[str, Mode]:
        return {s: self._cache.get(s, self.DEFAULT_MODE) for s in self.SOURCES}

    def schema_to_source(self, schema_name: Optional[str]) -> Optional[str]:
        if not schema_name:
            return None
        return self.SCHEMA_TO_SOURCE.get(schema_name.lower())

    async def set_mode(self, source: str, mode: str) -> Mode:
        """Persist a new mode for ``source`` to SSM, update the cache,
        and notify listeners. Returns the resolved mode (post-validation).
        """
        if source not in self.SOURCES:
            raise ValueError(f"unknown source '{source}'; allowed: {self.SOURCES}")
        if mode not in ("simulator", "real"):
            raise ValueError(f"mode must be 'simulator' or 'real', got '{mode}'")

        previous = self._cache.get(source, self.DEFAULT_MODE)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._write_mode_for_source, source, mode)
        except Exception as e:
            dsm_logger.warning("SSM write failed for {} -> {}: {}", source, mode, e)
        self._cache[source] = mode  # type: ignore[assignment]

        if previous != mode:
            for cb in list(self._listeners):
                try:
                    rv = cb(source, mode)
                    if asyncio.iscoroutine(rv):
                        await rv
                except Exception as e:
                    dsm_logger.warning("mode listener for {} ({}) raised: {}", source, mode, e)

        return mode  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # SSM I/O
    # ------------------------------------------------------------------

    def _ssm_path(self, source: str) -> str:
        return f"/{self._capability}/{self._environment}/data_source_mode/{source}"

    def _legacy_ssm_path(self, source: str) -> Optional[str]:
        cat = self.LEGACY_ENABLED_CATEGORY.get(source)
        if not cat:
            return None
        return f"/{self._capability}/{self._environment}/{cat}/enabled"

    def _read_mode_for_source(self, source: str) -> Mode:
        """Read order:
            1. Canonical ``data_source_mode/{source}``
            2. Legacy aggregate ``data_source_mode/{aggregate}`` (e.g. ``external``
               for any of the three external sub-sources)
            3. Legacy ``{cat}/enabled`` boolean (translated + persisted forward)
            4. Default ``simulator``
        """
        if self._ssm is None:
            return self.DEFAULT_MODE

        path = self._ssm_path(source)
        try:
            raw = self._ssm.get_parameter(path)
        except Exception as e:
            dsm_logger.debug("SSM read miss for {}: {}", path, e)
            raw = None

        if isinstance(raw, str) and raw.strip().lower() in ("simulator", "real"):
            return raw.strip().lower()  # type: ignore[return-value]

        # Forward-migrate from a legacy aggregate key (e.g. external -> file_uploads).
        aggregate = self.LEGACY_AGGREGATE_SOURCES.get(source)
        if aggregate:
            try:
                agg_val = self._ssm.get_parameter(self._ssm_path(aggregate))
            except Exception:
                agg_val = None
            if isinstance(agg_val, str) and agg_val.strip().lower() in ("simulator", "real"):
                migrated: Mode = agg_val.strip().lower()  # type: ignore[assignment]
                try:
                    self._ssm.put_parameter(
                        path,
                        migrated,
                        description=(
                            f"Mode for {source} data source "
                            f"(auto-migrated from legacy aggregate data_source_mode/{aggregate})"
                        ),
                    )
                    dsm_logger.info(
                        "Migrated legacy aggregate {} -> {} = {}",
                        aggregate, source, migrated,
                    )
                except Exception as e:
                    dsm_logger.warning("Migration write failed for {}: {}", path, e)
                return migrated

        # Legacy fallback - migrate forward when a legacy boolean exists.
        legacy_path = self._legacy_ssm_path(source)
        if legacy_path:
            try:
                legacy_val = self._ssm.get_parameter(legacy_path)
            except Exception:
                legacy_val = None
            if isinstance(legacy_val, str):
                migrated_b: Mode = "simulator" if legacy_val.strip().lower() == "true" else "real"
                try:
                    self._ssm.put_parameter(
                        path,
                        migrated_b,
                        description=f"Mode for {source} data source (auto-migrated from legacy {legacy_path})",
                    )
                    dsm_logger.info(
                        "Migrated legacy {} -> {} = {}", legacy_path, path, migrated_b,
                    )
                except Exception as e:
                    dsm_logger.warning("Migration write failed for {}: {}", path, e)
                return migrated_b

        return self.DEFAULT_MODE

    def _write_mode_for_source(self, source: str, mode: str) -> None:
        if self._ssm is None:
            return
        path = self._ssm_path(source)
        ok = self._ssm.put_parameter(
            path, mode, description=f"Mode for {source} data source",
        )
        if not ok:
            raise RuntimeError(f"put_parameter failed for {path}")
