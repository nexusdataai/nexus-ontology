"""
Generic processor for the Four-Views journey families.

Implements three concerns shared across all 8 solutions:

  * predictive(prefix)   -> writes <PREFIX>_Forecast_Result, <PREFIX>_Scenario_Result
                            (Athena rows) + appends a `<prefix>_kpi_forecast`
                            metric series to Mimir.
  * action_loop(prefix)  -> writes <PREFIX>_Action_Log, <PREFIX>_Outcome_Tracker,
                            <PREFIX>_Audit_Event (Athena rows) + appends a
                            `<prefix>_kpi` daily snapshot to Mimir.
  * historian(prefix)    -> appends solution-specific time-series to Mimir
                            (e.g. df_demand_actual, io_stock_qty,
                            pq_line_state, scr_vendor_risk, c360_health,
                            esg_pathway_co2, esg_sentiment).

The writer is the new ResultSink so every entity goes to its plan-specified
storage tier. Models are deterministic synthetic heuristics (linear/
seasonal); they are good enough for demo dashboards and they keep the
pipeline self-contained (no real ML dependency).
"""

from __future__ import annotations

import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from src.services.mimir_client import Sample
from src.services.result_sink import ResultSink
from src.services.solution_entity_catalogue import SOLUTION_PREFIXES, _common_kpi_metrics

fv_logger = logger.bind(component="four-views-processor")


# Mapping from app_id -> prefix
APP_TO_PREFIX = SOLUTION_PREFIXES


def _ts_ms(offset_days: int = 0) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=offset_days)).timestamp() * 1000)


def _isoformat(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


class FourViewsProcessor:
    """
    Carries solution context (app_id / prefix) and routes step calls to
    one of the three concerns.

    Construct one per stage instance; ResultSink is created lazily so a
    single processor can be reused across steps.
    """

    def __init__(
        self,
        app_id: str,
        log_callback: Optional[Callable] = None,
        job_id: str = "",
        journey_id: str = "",
        s3_client: Any = None,
        config: Any = None,
    ) -> None:
        self.app_id = app_id
        self.prefix = APP_TO_PREFIX.get(app_id, app_id.upper())
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config
        self._sink: Optional[ResultSink] = None
        self._mimir_lookback_days = 60

    def _log(self, level: str, msg: str, step_id: str = None) -> None:
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            fv_logger.log(level.upper(), msg)

    def _sink_obj(self) -> ResultSink:
        if self._sink is None:
            self._sink = ResultSink(
                job_id=self.job_id,
                journey_id=self.journey_id,
                s3_client=self._s3,
                config=self._config,
            )
        return self._sink

    # ------------------------------------------------------------------
    # Predictive: forecasts + scenarios
    # ------------------------------------------------------------------

    async def step_predictive(self) -> Dict[str, Any]:
        self._log("INFO", f"Generating forecasts + scenarios for {self.prefix}", "predictive")
        sink = self._sink_obj()

        kpis = _common_kpi_metrics(self.prefix)
        forecast_rows: List[Dict[str, Any]] = []
        scenario_rows: List[Dict[str, Any]] = []
        mimir_samples: List[Sample] = []

        rng = random.Random(hash((self.prefix, self.job_id)) & 0xFFFFFFFF)
        now = datetime.now(timezone.utc)

        for kpi in kpis:
            base = rng.uniform(20, 100)
            for h in range(1, 14):
                ts = now + timedelta(weeks=h)
                point = base * (1 + rng.uniform(-0.06, 0.06)) + h * rng.uniform(-0.5, 0.5)
                lower = point * 0.85
                upper = point * 1.15
                forecast_rows.append({
                    "forecast_id": str(uuid.uuid4()),
                    "entity_id": kpi,
                    "kpi_name": kpi,
                    "horizon_period": ts.strftime("%Y-W%U"),
                    "point_value": round(point, 3),
                    "lower_80": round(lower, 3),
                    "upper_80": round(upper, 3),
                    "model": "linear_seasonal_v1",
                    "created_at": _isoformat(now),
                })
                mimir_samples.append(Sample(
                    metric=f"{self.prefix.lower()}_kpi_forecast",
                    labels={"kpi": kpi, "scenario": "baseline"},
                    value=round(point, 3),
                    timestamp_ms=int(ts.timestamp() * 1000),
                ))

            for lever, mult in [("aggressive", 1.10), ("conservative", 0.92)]:
                scenario_rows.append({
                    "scenario_id": str(uuid.uuid4()),
                    "name": f"{kpi}-{lever}",
                    "lever": lever,
                    "kpi_name": kpi,
                    "baseline_value": round(base, 3),
                    "scenario_value": round(base * mult, 3),
                    "delta_pct": round((mult - 1) * 100, 2),
                    "computed_at": _isoformat(now),
                })

        await sink.write_rows(
            f"{self.prefix}_Forecast_Result", forecast_rows,
            virtual_entity=f"{self.prefix}_Forecast_Result",
        )
        await sink.write_rows(
            f"{self.prefix}_Scenario_Result", scenario_rows,
            virtual_entity=f"{self.prefix}_Scenario_Result",
        )
        await sink.write_metric_batch(
            mimir_samples,
            virtual_entity=f"{self.prefix}_KPI_Trend",
            label_map={"kpi": "kpi", "scenario": "scenario"},
        )

        return {
            "status": "completed",
            "forecast_rows": len(forecast_rows),
            "scenario_rows": len(scenario_rows),
            "mimir_samples": len(mimir_samples),
        }

    # ------------------------------------------------------------------
    # Action loop: action log + outcome + audit + KPI snapshot
    # ------------------------------------------------------------------

    async def step_action_loop(self) -> Dict[str, Any]:
        self._log("INFO", f"Running action loop + outcome capture for {self.prefix}", "action_loop")
        sink = self._sink_obj()
        rng = random.Random(hash((self.prefix, self.job_id, "action")) & 0xFFFFFFFF)
        now = datetime.now(timezone.utc)

        action_types = self._action_types_for_prefix()
        actions: List[Dict[str, Any]] = []
        outcomes: List[Dict[str, Any]] = []
        audit: List[Dict[str, Any]] = []

        for i in range(rng.randint(8, 16)):
            action_id = f"ACT-{self.prefix}-{int(now.timestamp())}-{i:03d}"
            atype = rng.choice(action_types)
            actions.append({
                "action_id": action_id,
                "action_type": atype,
                "target_entity": atype.split(":")[0],
                "target_id": f"{self.prefix}-T-{rng.randint(1, 999):03d}",
                "status": rng.choice(["executed", "executed", "executed", "pending", "failed"]),
                "notes": f"Auto-triggered by {self.prefix} action loop",
                "taken_by": "system",
                "taken_at": _isoformat(now - timedelta(minutes=rng.randint(1, 600))),
                "job_id": self.job_id,
            })
            # Always emit at least one outcome per action so Outcome_Tracker
            # is never empty after a single action_loop run. The Outcomes view
            # bar/line panels need a non-empty dataset to render.
            kpi = rng.choice(_common_kpi_metrics(self.prefix) or [f"{self.prefix.lower()}_metric"])
            before = rng.uniform(20, 100)
            after = before * rng.uniform(0.85, 1.10)
            outcomes.append({
                "outcome_id": str(uuid.uuid4()),
                "action_id": action_id,
                "kpi_name": kpi,
                "kpi_before": round(before, 3),
                "kpi_after": round(after, 3),
                "delta_value": round(after - before, 3),
                "currency": "USD",
                "measured_at": _isoformat(now),
            })
            audit.append({
                "event_id": str(uuid.uuid4()),
                "actor": "system",
                "verb": "execute",
                "target": action_id,
                "payload": atype,
                "event_ts": _isoformat(now),
            })

        # Cohort summary rollups (region x metric) consumed by Diagnose dashboards
        cohorts: List[Dict[str, Any]] = []
        regions = ["North", "South", "East", "West", "Central"]
        kpi_names = _common_kpi_metrics(self.prefix) or [f"{self.prefix.lower()}_metric"]
        for region in regions:
            for kpi in kpi_names:
                cohorts.append({
                    "cohort_id": f"COH-{self.prefix}-{region}-{kpi}",
                    "dimension": "region",
                    "dimension_value": region,
                    "metric_name": kpi,
                    "metric_value": round(rng.uniform(20, 95), 3),
                    "rolled_up_at": _isoformat(now),
                })

        # Active alert rows for the Monitor dashboard alert-list panel
        alerts: List[Dict[str, Any]] = []
        for i in range(rng.randint(3, 8)):
            severity = rng.choice(["high", "medium", "medium", "low"])
            alerts.append({
                "alert_id": f"ALERT-{self.prefix}-{int(now.timestamp())}-{i:03d}",
                "severity": severity,
                "title": rng.choice(action_types).replace(":", " ").title(),
                "message": f"Auto-generated {self.prefix} alert {i+1}",
                "entity_id": f"{self.prefix}-T-{rng.randint(1, 999):03d}",
                "created_at": _isoformat(now - timedelta(minutes=rng.randint(1, 360))),
            })

        # Anomaly score rows so the Monitor "Top Risk Items" table populates.
        anomaly_rows: List[Dict[str, Any]] = []
        anomaly_samples_for_mimir: List[Sample] = []
        for i in range(20):
            entity_id = f"{self.prefix}-E-{rng.randint(1, 999):03d}"
            entity_type = rng.choice(["customer", "vendor", "material", "plant", "line", "order"])
            score = round(rng.uniform(40, 95), 2)
            anomaly_rows.append({
                "entity_id": entity_id,
                "entity_type": entity_type,
                "value": score,
                "timestamp": int(now.timestamp() * 1000),
            })
            anomaly_samples_for_mimir.append(Sample(
                metric=f"{self.prefix.lower()}_anomaly",
                labels={"entity_id": entity_id, "entity_type": entity_type},
                value=score,
                timestamp_ms=int(now.timestamp() * 1000),
            ))

        await sink.write_rows(f"{self.prefix}_Action_Log", actions,
                              virtual_entity=f"{self.prefix}_Action_Log")
        await sink.write_rows(f"{self.prefix}_Cohort_Summary", cohorts,
                              virtual_entity=f"{self.prefix}_Cohort_Summary")
        await sink.write_rows(f"{self.prefix}_Alert", alerts,
                              virtual_entity=f"{self.prefix}_Alert")
        await sink.write_metric_batch(
            anomaly_samples_for_mimir,
            virtual_entity=f"{self.prefix}_Anomaly_Score",
            label_map={"entity_id": "entity_id", "entity_type": "entity_type"},
        )
        await sink.write_rows(f"{self.prefix}_Outcome_Tracker", outcomes,
                              virtual_entity=f"{self.prefix}_Outcome_Tracker")
        await sink.write_rows(f"{self.prefix}_Audit_Event", audit,
                              virtual_entity=f"{self.prefix}_Audit_Event")

        # Append today's KPI snapshot AND a 30-day backfill (when the
        # KPI_Trend table is short) so the Monitor view's line chart shows a
        # real trend instead of a single data point. The backfill is gated by
        # the existing row count on the simulator-side mirror so this is
        # idempotent across restarts.
        kpi_metric = f"{self.prefix.lower()}_kpi"
        kpi_list = _common_kpi_metrics(self.prefix) or [f"{self.prefix.lower()}_metric"]
        samples: List[Sample] = []
        for kpi in kpi_list:
            samples.append(Sample(
                metric=kpi_metric,
                labels={"kpi": kpi},
                value=round(rng.uniform(15, 95), 3),
                timestamp_ms=int(now.timestamp() * 1000),
            ))

        existing_kpi_rows = await self._sim_count("external_sources", f"{self.prefix}_KPI_Trend")
        if existing_kpi_rows < 30:
            for kpi in kpi_list:
                base = rng.uniform(20, 95)
                for d in range(30, 0, -1):
                    base = max(0.0, min(100.0, base + rng.uniform(-1.5, 1.5)))
                    samples.append(Sample(
                        metric=kpi_metric,
                        labels={"kpi": kpi},
                        value=round(base, 2),
                        timestamp_ms=int((now - timedelta(days=d)).timestamp() * 1000),
                    ))

        await sink.write_metric_batch(
            samples, virtual_entity=f"{self.prefix}_KPI_Trend",
            label_map={"kpi": "kpi"},
        )

        # 14-day Anomaly_Score backfill so the Diagnose "Anomaly Trend" line
        # panel has history, not just today's snapshot.
        existing_anomaly_rows = await self._sim_count("external_sources", f"{self.prefix}_Anomaly_Score")
        if existing_anomaly_rows < 100:
            history_samples: List[Sample] = []
            for i in range(20):
                entity_id = f"{self.prefix}-E-{rng.randint(1, 999):03d}"
                entity_type = rng.choice(["customer", "vendor", "material", "plant", "line", "order"])
                base = rng.uniform(40, 90)
                for d in range(14, 0, -1):
                    base = max(0.0, min(100.0, base + rng.uniform(-3, 3)))
                    history_samples.append(Sample(
                        metric=f"{self.prefix.lower()}_anomaly",
                        labels={"entity_id": entity_id, "entity_type": entity_type},
                        value=round(base, 2),
                        timestamp_ms=int((now - timedelta(days=d)).timestamp() * 1000),
                    ))
            if history_samples:
                await sink.write_metric_batch(
                    history_samples,
                    virtual_entity=f"{self.prefix}_Anomaly_Score",
                    label_map={"entity_id": "entity_id", "entity_type": "entity_type"},
                )

        return {
            "status": "completed",
            "actions": len(actions),
            "outcomes": len(outcomes),
            "audit_events": len(audit),
            "kpi_samples": len(samples),
        }

    async def _sim_count(self, schema: str, table: str) -> int:
        """How many rows the external simulator currently has for this table."""
        try:
            from src.apis.fdw_api import _simulators
        except Exception:
            return 0
        sim = _simulators.get("external") if _simulators else None
        if sim is None or not hasattr(sim, "_get_table_data"):
            return 0
        try:
            rows = await sim._get_table_data(schema, table)
            return len(rows or [])
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Historian: solution-specific Mimir series
    # ------------------------------------------------------------------

    async def step_historian(self) -> Dict[str, Any]:
        self._log("INFO", f"Running historian for {self.prefix}", "historian")
        sink = self._sink_obj()
        rng = random.Random(hash((self.prefix, "hist")) & 0xFFFFFFFF)

        samples: List[Sample] = []
        days = self._mimir_lookback_days

        if self.prefix == "DF":
            for region in ["North", "South", "East", "West", "Central"]:
                for category in ["Carbonated", "Juice", "Water", "Energy", "Tea"]:
                    base = rng.uniform(800, 5000)
                    for d in range(days, 0, -1):
                        samples.append(Sample(
                            metric="df_demand_actual",
                            labels={"region": region, "category": category},
                            value=round(base * rng.uniform(0.7, 1.3), 1),
                            timestamp_ms=_ts_ms(d),
                        ))
            await sink.write_metric_batch(samples, virtual_entity="DF_Demand_Actual_Daily",
                                          label_map={"region": "region", "category": "category"})

        elif self.prefix == "IO":
            for plant_idx in range(10):
                plant_id = f"PLT-{plant_idx+1:03d}"
                for category in ["Carbonated", "Juice", "Water"]:
                    base = rng.uniform(20_000, 180_000)
                    for d in range(days, 0, -1):
                        samples.append(Sample(
                            metric="io_stock_qty",
                            labels={"plant_id": plant_id, "category": category},
                            value=round(base * rng.uniform(0.85, 1.15), 1),
                            timestamp_ms=_ts_ms(d),
                        ))
            await sink.write_metric_batch(samples, virtual_entity="IO_Stock_Snapshot_Daily",
                                          label_map={"plant_id": "plant_id", "category": "category"})

        elif self.prefix == "PQ":
            # Indicator gauge per line for the last 24h, sampled hourly
            for line_idx in range(25):
                line_id = f"PL-{line_idx+1:03d}"
                plant_id = f"PLT-{(line_idx % 10) + 1:03d}"
                for h in range(24, 0, -1):
                    state = rng.choices([1, 0, -1], weights=[7, 2, 1])[0]
                    samples.append(Sample(
                        metric="pq_line_state",
                        labels={"line_id": line_id, "plant_id": plant_id},
                        value=state,
                        timestamp_ms=int((datetime.now(timezone.utc) - timedelta(hours=h)).timestamp() * 1000),
                    ))
            await sink.write_metric_batch(samples, virtual_entity="PQ_Line_State",
                                          label_map={"line_id": "line_id", "plant_id": "plant_id"})

        elif self.prefix == "SCR":
            for v_idx in range(80):
                vendor_id = f"VND-{v_idx+1:03d}"
                region = rng.choice(["APAC", "EMEA", "LATAM", "NA"])
                base = rng.uniform(20, 80)
                for d in range(days, 0, -1):
                    base = max(0, min(100, base + rng.uniform(-2, 2)))
                    samples.append(Sample(
                        metric="scr_vendor_risk",
                        labels={"vendor_id": vendor_id, "region": region},
                        value=round(base, 2),
                        timestamp_ms=_ts_ms(d),
                    ))
            await sink.write_metric_batch(samples, virtual_entity="SCR_Risk_History",
                                          label_map={"vendor_id": "vendor_id", "region": "region"})

        elif self.prefix == "C360":
            for a_idx in range(200):
                acc = f"ACC-{a_idx+1:05d}"
                tier = rng.choice(["Platinum", "Gold", "Silver", "Bronze"])
                base = rng.uniform(40, 95)
                for d in range(days, 0, -1):
                    base = max(0, min(100, base + rng.uniform(-1.5, 1.5)))
                    samples.append(Sample(
                        metric="c360_health",
                        labels={"account_id": acc, "tier": tier},
                        value=round(base, 2),
                        timestamp_ms=_ts_ms(d),
                    ))
            await sink.write_metric_batch(samples, virtual_entity="C360_Account_Health",
                                          label_map={"account_id": "account_id", "tier": "tier"})

        elif self.prefix == "ESG":
            for plant_idx in range(10):
                plant_id = f"PLT-{plant_idx+1:03d}"
                base_pathway = rng.uniform(80, 130)
                for d in range(days, 0, -1):
                    base_pathway *= rng.uniform(0.997, 1.001)
                    samples.append(Sample(
                        metric="esg_pathway_co2",
                        labels={"plant_id": plant_id},
                        value=round(base_pathway, 2),
                        timestamp_ms=_ts_ms(d),
                    ))
            await sink.write_metric_batch(samples, virtual_entity="ESG_Pathway_Forecast",
                                          label_map={"plant_id": "plant_id"})

            sentiment_samples = []
            for brand in ["StarFizz", "TropicBurst", "AquaPure", "PowerVolt", "ZenBrew"]:
                base = rng.uniform(-0.2, 0.6)
                for d in range(days, 0, -1):
                    base += rng.uniform(-0.05, 0.05)
                    sentiment_samples.append(Sample(
                        metric="esg_sentiment",
                        labels={"brand": brand},
                        value=round(max(-1.0, min(1.0, base)), 3),
                        timestamp_ms=_ts_ms(d),
                    ))
            await sink.write_metric_batch(
                sentiment_samples, virtual_entity="ESG_Sentiment_Score",
                label_map={"brand": "brand"},
            )

        elif self.prefix == "O2C":
            # KPI trend backfill (so the Predict view has historical context)
            kpis = _common_kpi_metrics("O2C")
            for kpi in kpis:
                base = rng.uniform(30, 90)
                for d in range(days, 0, -1):
                    base += rng.uniform(-1.0, 1.0)
                    samples.append(Sample(
                        metric="o2c_kpi",
                        labels={"kpi": kpi},
                        value=round(base, 2),
                        timestamp_ms=_ts_ms(d),
                    ))
            await sink.write_metric_batch(samples, virtual_entity="O2C_KPI_Trend",
                                          label_map={"kpi": "kpi"})

        elif self.prefix == "PA":
            for vendor_idx in range(80):
                vendor_id = f"VND-{vendor_idx+1:03d}"
                base = rng.uniform(0, 80)
                for d in range(days, 0, -1):
                    base = max(0, min(100, base + rng.uniform(-1.5, 1.5)))
                    samples.append(Sample(
                        metric="pa_vendor_risk",
                        labels={"vendor_id": vendor_id},
                        value=round(base, 2),
                        timestamp_ms=_ts_ms(d),
                    ))
            await sink.write_metric_batch(samples, virtual_entity="PA_Vendor_Risk_Forecast",
                                          label_map={"vendor_id": "vendor_id"})

        return {"status": "completed", "mimir_samples": len(samples)}

    def _action_types_for_prefix(self) -> List[str]:
        return {
            "O2C": ["dunning:level1", "dunning:level2", "credit_hold", "dispute:price", "escalation:exec"],
            "DF": ["override:approve", "override:reject", "model:retrain", "promo:adjust"],
            "IO": ["transfer:plant", "writeoff:expired", "expedite", "reorder:trigger"],
            "PA": ["negotiate:price", "approve:auto", "block:vendor", "switch:vendor"],
            "PQ": ["capa:open", "capa:close", "maintenance:schedule", "shift:change"],
            "SCR": ["alt_vendor:activate", "expedite:air", "hedge:forward", "stock:position"],
            "C360": ["retain:offer", "upsell:bundle", "save:call", "campaign:launch"],
            "ESG": ["initiative:fund", "audit:schedule", "report:publish", "offset:purchase"],
        }.get(self.prefix, ["generic:action"])
