"""
Athena Query Service

Reusable Athena query executor for querying Glue catalog tables.
Generalized Athena query service for
any Glue table (including AI automation result objects).
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from loguru import logger

athena_logger = logger.bind(component="athena-query")


class AthenaQueryService:

    def __init__(self, region: str = "", database: str = "", output_bucket: str = ""):
        self._region = region or os.getenv("AWS_REGION", "us-east-1")
        self._database = database
        self._output_bucket = output_bucket
        self._output_location = ""

        if not self._database:
            try:
                from src.config.config_provider import get_config
                config = get_config()
                self._database = getattr(config, "glue_database", "") or os.getenv("GLUE_DATABASE", "call-processing-dev-analytics")
                self._output_bucket = self._output_bucket or getattr(config, "s3_recordings_bucket", "")
            except Exception:
                self._database = os.getenv("GLUE_DATABASE", "call-processing-dev-analytics")

        if self._output_bucket:
            self._output_location = f"s3://{self._output_bucket}/athena-results/"

    def _client(self):
        from src.utils.aws_client_utils import AWSClientManager
        return AWSClientManager(region_name=self._region).create_client("athena")

    async def execute_query(self, sql: str, database: str = None) -> List[Dict[str, Any]]:
        db = database or self._database
        if not db:
            raise ValueError("No Athena database configured")
        if not self._output_location:
            raise ValueError("No S3 output location configured for Athena")

        athena_logger.info(f"Executing Athena query on {db}: {sql[:100]}...")

        client = self._client()
        response = client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": db},
            ResultConfiguration={"OutputLocation": self._output_location},
        )
        execution_id = response["QueryExecutionId"]

        for _ in range(60):
            await asyncio.sleep(1)
            status_resp = client.get_query_execution(QueryExecutionId=execution_id)
            state = status_resp["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                break
            if state in ("FAILED", "CANCELLED"):
                reason = status_resp["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
                raise RuntimeError(f"Athena query {state}: {reason}")
        else:
            raise RuntimeError("Athena query timed out after 60s")

        result_resp = client.get_query_results(QueryExecutionId=execution_id, MaxResults=1000)
        rows = result_resp.get("ResultSet", {}).get("Rows", [])
        if not rows:
            return []

        columns = [col["VarCharValue"] for col in rows[0]["Data"]]
        results = []
        for row in rows[1:]:
            values = [cell.get("VarCharValue", "") for cell in row["Data"]]
            results.append(dict(zip(columns, values)))

        athena_logger.info(f"Athena query returned {len(results)} rows")
        return results

    async def query_table(self, table: str, columns: Optional[List[str]] = None,
                          filters: Optional[Dict[str, Any]] = None, limit: int = 100,
                          order_by: Optional[str] = None, database: str = None) -> Dict[str, Any]:
        col_str = ", ".join(columns) if columns else "*"
        sql = f'SELECT {col_str} FROM "{table}"'

        where_parts = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, str):
                    where_parts.append(f"{field} = '{value}'")
                elif isinstance(value, (int, float)):
                    where_parts.append(f"{field} = {value}")
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        if order_by:
            sql += f" ORDER BY {order_by}"

        sql += f" LIMIT {limit}"

        rows = await self.execute_query(sql, database)

        from src.models.fdw_models import QueryMetadata, QueryResponse
        metadata = QueryMetadata(duration_ms=0, table_queried=table, row_count=len(rows))
        return QueryResponse(rows=rows, metadata=metadata)

    async def get_latest_partition(self, table: str, database: str = None) -> Dict[str, str]:
        sql = f'SELECT year, month, day FROM "{table}" ORDER BY year DESC, month DESC, day DESC LIMIT 1'
        rows = await self.execute_query(sql, database)
        if rows:
            return rows[0]
        return {}

    async def aggregate_query(self, table: str, column: str, aggregation: str = "count",
                              group_by: Optional[str] = None, limit: int = 100,
                              database: str = None) -> List[Dict[str, Any]]:
        agg_func = aggregation.upper()
        if agg_func not in ("COUNT", "SUM", "AVG", "MIN", "MAX"):
            agg_func = "COUNT"

        if group_by:
            sql = f'SELECT {group_by}, {agg_func}({column}) as value FROM "{table}" GROUP BY {group_by} ORDER BY value DESC LIMIT {limit}'
        else:
            sql = f'SELECT {agg_func}({column}) as value FROM "{table}"'

        return await self.execute_query(sql, database)
