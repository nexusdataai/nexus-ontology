"""
O2C Glue Catalog

Manages AWS Glue catalog tables and partitions for Order-to-Cash analytics:
- o2c_orders: per-order match status, anomaly score, risk rank
- o2c_alerts: triggered alerts per job run
- o2c_kpis: KPI snapshots per job run
"""

import os
from loguru import logger

o2c_glue_logger = logger.bind(component="o2c-glue")

DATABASE_NAME_DEFAULT = "nexus-ai-dev-analytics"

TABLE_SCHEMAS = {
    "o2c_orders": [
        {"Name": "opportunity_id", "Type": "string"},
        {"Name": "account_id", "Type": "string"},
        {"Name": "account_name", "Type": "string"},
        {"Name": "account_tier", "Type": "string"},
        {"Name": "order_amount", "Type": "double"},
        {"Name": "close_date", "Type": "string"},
        {"Name": "delivery_id", "Type": "string"},
        {"Name": "match_status", "Type": "string"},
        {"Name": "delivered_qty", "Type": "int"},
        {"Name": "invoiced_amount", "Type": "double"},
        {"Name": "anomaly_score", "Type": "int"},
        {"Name": "composite_risk", "Type": "double"},
        {"Name": "risk_rank", "Type": "int"},
        {"Name": "job_id", "Type": "string"},
        {"Name": "processed_at", "Type": "string"},
    ],
    "o2c_alerts": [
        {"Name": "job_id", "Type": "string"},
        {"Name": "processed_at", "Type": "string"},
        {"Name": "total_alerts", "Type": "int"},
        {"Name": "alerts", "Type": "string"},
    ],
    "o2c_kpis": [
        {"Name": "job_id", "Type": "string"},
        {"Name": "processed_at", "Type": "string"},
        {"Name": "dso", "Type": "double"},
        {"Name": "match_rate", "Type": "double"},
        {"Name": "leakage_rate", "Type": "double"},
        {"Name": "total_open_ar", "Type": "double"},
        {"Name": "total_orders_processed", "Type": "int"},
        {"Name": "total_alerts", "Type": "int"},
        {"Name": "at_risk_amount", "Type": "double"},
        {"Name": "cash_projection", "Type": "string"},
    ],
}

PARTITION_KEYS = [
    {"Name": "year", "Type": "string"},
    {"Name": "month", "Type": "string"},
    {"Name": "day", "Type": "string"},
]


class O2CGlueCatalog:

    def __init__(self, region_name: str = "us-east-1", database_name: str = ""):
        self._region = region_name
        self._database = database_name or os.getenv("GLUE_DATABASE", DATABASE_NAME_DEFAULT)
        self._client = None

    def _glue(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("glue", region_name=self._region)
        return self._client

    def ensure_tables(self, s3_bucket: str):
        glue = self._glue()

        try:
            glue.get_database(Name=self._database)
        except Exception:
            try:
                glue.create_database(DatabaseInput={"Name": self._database, "Description": "O2C Analytics"})
                o2c_glue_logger.info(f"Created Glue database: {self._database}")
            except Exception as e:
                o2c_glue_logger.warning(f"Database creation failed: {e}")

        for table_name, columns in TABLE_SCHEMAS.items():
            prefix = table_name.replace("o2c_", "o2c-")
            try:
                glue.get_table(DatabaseName=self._database, Name=table_name)
                o2c_glue_logger.debug(f"Table {table_name} already exists")
            except Exception:
                try:
                    glue.create_table(
                        DatabaseName=self._database,
                        TableInput={
                            "Name": table_name,
                            "Description": f"Order-to-Cash {table_name.replace('o2c_', '')}",
                            "StorageDescriptor": {
                                "Columns": columns,
                                "Location": f"s3://{s3_bucket}/{prefix}/",
                                "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                                "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                                "SerdeInfo": {
                                    "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                                },
                            },
                            "PartitionKeys": PARTITION_KEYS,
                            "TableType": "EXTERNAL_TABLE",
                        },
                    )
                    o2c_glue_logger.info(f"Created Glue table: {self._database}.{table_name}")
                except Exception as e:
                    o2c_glue_logger.warning(f"Table {table_name} creation failed: {e}")

    def add_partition(self, table_name: str, s3_bucket: str, s3_prefix: str,
                      year: str, month: str, day: str):
        glue = self._glue()
        columns = TABLE_SCHEMAS.get(table_name, [])
        try:
            glue.create_partition(
                DatabaseName=self._database,
                TableName=table_name,
                PartitionInput={
                    "Values": [year, month, day],
                    "StorageDescriptor": {
                        "Columns": columns,
                        "Location": f"s3://{s3_bucket}/{s3_prefix}",
                        "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                        "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                        "SerdeInfo": {"SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe"},
                    },
                },
            )
            o2c_glue_logger.info(f"Added partition {year}/{month}/{day} to {table_name}")
        except Exception as e:
            if "AlreadyExistsException" in str(type(e).__name__) or "already exists" in str(e).lower():
                o2c_glue_logger.debug(f"Partition {year}/{month}/{day} already exists for {table_name}")
            else:
                o2c_glue_logger.warning(f"Partition add failed for {table_name}: {e}")
