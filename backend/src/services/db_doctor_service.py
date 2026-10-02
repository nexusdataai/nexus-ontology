"""
AWS Glue Call Database Doctor Service.

Provides diagnostic and repair capabilities for the Glue Call Database.
Detects and fixes inconsistencies such as missing partitions where S3 data exists
but catalog entries are missing.
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from loguru import logger

# Add scripts directory to path for imports
scripts_path = os.path.join(os.path.dirname(__file__), '../../scripts/call-scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from glue_catalog import GlueCatalog, BOTO3_AVAILABLE

if BOTO3_AVAILABLE:
    import boto3
    from botocore.exceptions import ClientError


def _localstack_boto_client(service: str, region: str):
    """Create boto3 client with LocalStack/K3s split endpoints when enabled."""
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 not available")
    try:
        from src.config.localstack_config import get_localstack_config, is_localstack_enabled
        if is_localstack_enabled():
            cfg = get_localstack_config()
            return boto3.client(
                service,
                endpoint_url=cfg.get_service_endpoint(service),
                region_name=region or cfg.region,
                aws_access_key_id=cfg.access_key,
                aws_secret_access_key=cfg.secret_key,
            )
    except Exception:
        pass
    return boto3.client(service, region_name=region)


class DiagnosticStage(str, Enum):
    """Stages of the diagnostic/repair process"""
    IDLE = "idle"
    CHECKING = "checking"
    REPORTING = "reporting"
    READY = "ready"
    REPAIRING = "repairing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class PartitionInfo:
    """Information about a partition"""
    year: int
    month: int
    day: int
    hour: int
    s3_location: str
    in_catalog: bool
    file_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "hour": self.hour,
            "s3_location": self.s3_location,
            "in_catalog": self.in_catalog,
            "file_count": self.file_count
        }


@dataclass
class SchemaInfo:
    """Information about table schema"""
    input_format: str
    serde_library: str
    columns: List[str]
    partition_keys: List[str]
    is_valid: bool
    issues: List[str]
    column_type_issues: List[str] = None
    partition_type_issues: List[str] = None
    table_location: str = ""
    expected_location: str = ""
    location_valid: bool = True
    partition_schema_mismatches: List[Dict] = None
    
    def __post_init__(self):
        if self.column_type_issues is None:
            self.column_type_issues = []
        if self.partition_type_issues is None:
            self.partition_type_issues = []
        if self.partition_schema_mismatches is None:
            self.partition_schema_mismatches = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_format": self.input_format,
            "serde_library": self.serde_library,
            "columns": self.columns,
            "partition_keys": self.partition_keys,
            "is_valid": self.is_valid,
            "issues": self.issues,
            "column_type_issues": self.column_type_issues,
            "partition_type_issues": self.partition_type_issues,
            "table_location": self.table_location,
            "expected_location": self.expected_location,
            "location_valid": self.location_valid,
            "partition_schema_mismatches": self.partition_schema_mismatches,
        }


@dataclass
class DiagnosticReport:
    """Results of database diagnostics"""
    stage: DiagnosticStage
    database_exists: bool
    table_exists: bool
    s3_bucket_accessible: bool
    total_s3_partitions: int
    total_catalog_partitions: int
    missing_partitions: List[PartitionInfo]
    orphaned_partitions: List[PartitionInfo]
    schema_info: Optional[SchemaInfo]
    issues_found: int
    recommendations: List[str]
    timestamp: str
    error: Optional[str] = None
    # Deep checks
    athena_query_success: bool = False
    athena_query_time_ms: float = 0
    athena_row_count: int = 0
    athena_error: Optional[str] = None
    data_samples_checked: int = 0
    data_integrity_issues: List[Dict] = None
    call_asset_checks: List[Dict] = None
    calls_with_all_assets: int = 0
    calls_with_missing_assets: int = 0
    tracker_summary: Optional[Dict[str, int]] = None

    def __post_init__(self):
        if self.data_integrity_issues is None:
            self.data_integrity_issues = []
        if self.call_asset_checks is None:
            self.call_asset_checks = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "database_exists": self.database_exists,
            "table_exists": self.table_exists,
            "s3_bucket_accessible": self.s3_bucket_accessible,
            "total_s3_partitions": self.total_s3_partitions,
            "total_catalog_partitions": self.total_catalog_partitions,
            "missing_partitions": [p.to_dict() for p in self.missing_partitions],
            "orphaned_partitions": [p.to_dict() for p in self.orphaned_partitions],
            "schema_info": self.schema_info.to_dict() if self.schema_info else None,
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "error": self.error,
            "athena_query_success": self.athena_query_success,
            "athena_query_time_ms": self.athena_query_time_ms,
            "athena_row_count": self.athena_row_count,
            "athena_error": self.athena_error,
            "data_samples_checked": self.data_samples_checked,
            "data_integrity_issues": self.data_integrity_issues,
            "call_asset_checks": self.call_asset_checks,
            "calls_with_all_assets": self.calls_with_all_assets,
            "calls_with_missing_assets": self.calls_with_missing_assets,
            "tracker_summary": self.tracker_summary,
        }


@dataclass
class RepairResult:
    """Results of repair operations"""
    stage: DiagnosticStage
    operations_performed: List[str]
    partitions_added: int
    partitions_failed: int
    table_rebuilt: bool
    success: bool
    errors: List[str]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "operations_performed": self.operations_performed,
            "partitions_added": self.partitions_added,
            "partitions_failed": self.partitions_failed,
            "table_rebuilt": self.table_rebuilt,
            "success": self.success,
            "errors": self.errors,
            "timestamp": self.timestamp
        }


class DbDoctorService:
    """
    Service for diagnosing and repairing Glue Call Database issues.
    
    Capabilities:
    - Scan S3 and compare with Glue catalog
    - Identify missing partitions
    - Validate table schema (format, columns, partitions)
    - Auto-repair partition inconsistencies
    - Auto-repair schema mismatches
    - Rebuild table if needed
    """
    
    # Expected table schema - must match JSON structure written by call_processor.py
    EXPECTED_INPUT_FORMAT = "org.apache.hadoop.mapred.TextInputFormat"
    EXPECTED_SERDE = "org.openx.data.jsonserde.JsonSerDe"
    EXPECTED_COLUMNS = [
        "task_id", "org_id", "created_at", "status", "direction",
        "origin_phone", "destination_phone", "queue_name", "queue_id",
        "agent_name", "agent_id", "duration_seconds", "recording_file",
        "transcript_file", "analysis_file", "sfdc_action_file"
    ]
    EXPECTED_COLUMN_TYPES = {
        "task_id": "string", "org_id": "string", "created_at": "bigint",
        "status": "string", "direction": "string", "origin_phone": "string",
        "destination_phone": "string", "queue_name": "string", "queue_id": "string",
        "agent_name": "string", "agent_id": "string", "duration_seconds": "int",
        "recording_file": "string", "transcript_file": "string",
        "analysis_file": "string", "sfdc_action_file": "string",
    }
    EXPECTED_PARTITIONS = ["year", "month", "day", "hour"]
    EXPECTED_PARTITION_TYPES = {"year": "string", "month": "string", "day": "string", "hour": "string"}
    EXPECTED_S3_PREFIX = "call-data/"
    
    # Common wrong formats that need repair
    PARQUET_INPUT_FORMAT = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    PARQUET_SERDE = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    
    def __init__(
        self,
        bucket: Optional[str] = None,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        data_prefix: Optional[str] = None,
        region: Optional[str] = None
    ):
        """Initialize the DB Doctor service"""
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for DB Doctor operations")
        
        self.catalog = GlueCatalog(
            bucket=bucket,
            database_name=database_name,
            table_name=table_name,
            data_prefix=data_prefix,
            region=region,
            verbose=False
        )
        self._s3_client = None
        self._current_stage = DiagnosticStage.IDLE
    
    @property
    def s3_client(self):
        """Lazy-load S3 client"""
        if self._s3_client is None:
            self._s3_client = _localstack_boto_client('s3', self.catalog.region)
        return self._s3_client
    
    def _validate_schema(self) -> SchemaInfo:
        """
        Validate the current table schema against expected schema.
        
        Checks:
        - Input format (TextInputFormat for JSON, not Parquet)
        - SerDe library (JsonSerDe)
        - Column names and TYPES
        - Partition key names and TYPES
        - S3 location prefix
        - Partition-to-table schema consistency
        """
        issues = []
        column_type_issues = []
        partition_type_issues = []
        partition_schema_mismatches = []
        table_location = ""
        expected_location = f"s3://{self.catalog.bucket}/{self.EXPECTED_S3_PREFIX}"
        location_valid = True
        
        try:
            table_response = self.catalog.glue_client.get_table(
                DatabaseName=self.catalog.database_name,
                Name=self.catalog.table_name
            )
            table = table_response['Table']
            sd = table.get('StorageDescriptor', {})
            
            # Extract current schema
            input_format = sd.get('InputFormat', '')
            serde_info = sd.get('SerdeInfo', {})
            serde_library = serde_info.get('SerializationLibrary', '')
            columns = [col['Name'] for col in sd.get('Columns', [])]
            column_types = {col['Name']: col['Type'] for col in sd.get('Columns', [])}
            partition_keys = [pk['Name'] for pk in table.get('PartitionKeys', [])]
            partition_key_types = {pk['Name']: pk['Type'] for pk in table.get('PartitionKeys', [])}
            table_location = sd.get('Location', '')
            
            # Check input format
            if input_format == self.PARQUET_INPUT_FORMAT:
                issues.append(f"Table uses Parquet format but data is JSON. Expected: {self.EXPECTED_INPUT_FORMAT}")
            elif input_format != self.EXPECTED_INPUT_FORMAT:
                issues.append(f"Unexpected input format: {input_format}. Expected: {self.EXPECTED_INPUT_FORMAT}")
            
            # Check SerDe
            if serde_library == self.PARQUET_SERDE:
                issues.append(f"Table uses Parquet SerDe but data is JSON. Expected: {self.EXPECTED_SERDE}")
            elif serde_library != self.EXPECTED_SERDE:
                issues.append(f"Unexpected SerDe: {serde_library}. Expected: {self.EXPECTED_SERDE}")
            
            # Check columns - wrong names
            wrong_columns = {
                'customer_phone': 'Should be origin_phone and destination_phone',
                'recording_url': 'Should be recording_file',
                'transcript_url': 'Should be transcript_file',
                'start_time': 'Should be created_at',
            }
            for wrong_col, suggestion in wrong_columns.items():
                if wrong_col in columns:
                    issues.append(f"Column '{wrong_col}' found. {suggestion}")
            
            # Check missing columns
            missing_columns = set(self.EXPECTED_COLUMNS) - set(columns)
            if missing_columns:
                issues.append(f"Missing columns: {', '.join(sorted(missing_columns))}")
            
            # Check column TYPES
            for col_name, expected_type in self.EXPECTED_COLUMN_TYPES.items():
                actual_type = column_types.get(col_name)
                if actual_type and actual_type != expected_type:
                    column_type_issues.append(f"{col_name}: found '{actual_type}', expected '{expected_type}'")
            if column_type_issues:
                issues.append(f"Column type mismatches: {len(column_type_issues)} columns have wrong types")
            
            # Check partition keys
            if partition_keys != self.EXPECTED_PARTITIONS:
                issues.append(f"Partition keys mismatch. Found: {partition_keys}. Expected: {self.EXPECTED_PARTITIONS}")
            
            # Check partition key TYPES
            for pk_name, expected_type in self.EXPECTED_PARTITION_TYPES.items():
                actual_type = partition_key_types.get(pk_name)
                if actual_type and actual_type != expected_type:
                    partition_type_issues.append(f"{pk_name}: found '{actual_type}', expected '{expected_type}'")
            if partition_type_issues:
                issues.append(f"Partition key type mismatches: {len(partition_type_issues)} keys have wrong types")
            
            # Check S3 location
            if table_location and not table_location.rstrip('/').endswith(self.EXPECTED_S3_PREFIX.rstrip('/')):
                location_valid = False
                issues.append(f"Table S3 location '{table_location}' should end with '{self.EXPECTED_S3_PREFIX}'")
            
            # Check partition-to-table schema consistency (sample first 3)
            try:
                resp = self.catalog.glue_client.get_partitions(
                    DatabaseName=self.catalog.database_name,
                    TableName=self.catalog.table_name,
                    MaxResults=3
                )
                for part in resp.get('Partitions', []):
                    part_vals = part.get('Values', [])
                    part_sd = part.get('StorageDescriptor', {})
                    part_cols = {c['Name']: c['Type'] for c in part_sd.get('Columns', [])}
                    mismatches = []
                    for col_name, table_type in column_types.items():
                        part_type = part_cols.get(col_name)
                        if part_type and part_type != table_type:
                            mismatches.append(f"{col_name}: partition has '{part_type}', table has '{table_type}'")
                    if mismatches:
                        partition_schema_mismatches.append({
                            "partition": f"year={part_vals[0]}/month={part_vals[1]}/day={part_vals[2]}/hour={part_vals[3]}" if len(part_vals) >= 4 else str(part_vals),
                            "issues": mismatches,
                        })
                if partition_schema_mismatches:
                    issues.append(f"Partition schema mismatches: {len(partition_schema_mismatches)} partition(s) have column types that differ from the table")
            except Exception as e:
                logger.warning(f"Could not check partition schema consistency: {e}")
            
            is_valid = len(issues) == 0
            
            return SchemaInfo(
                input_format=input_format,
                serde_library=serde_library,
                columns=columns,
                partition_keys=partition_keys,
                is_valid=is_valid,
                issues=issues,
                column_type_issues=column_type_issues,
                partition_type_issues=partition_type_issues,
                table_location=table_location,
                expected_location=expected_location,
                location_valid=location_valid,
                partition_schema_mismatches=partition_schema_mismatches,
            )
            
        except ClientError as e:
            logger.error(f"Failed to validate schema: {e}")
            return SchemaInfo(
                input_format="",
                serde_library="",
                columns=[],
                partition_keys=[],
                is_valid=False,
                issues=[f"Failed to get table info: {str(e)}"]
            )
    
    def _parse_partition_from_s3_key(self, key: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Parse partition values from S3 key path.
        
        Expected format: call-data/year=2025/month=01/day=14/hour=08/...
        
        Returns:
            Tuple of (year, month, day, hour) or None if not parseable
        """
        parts = key.split('/')
        try:
            partition_dict = {}
            for part in parts:
                if '=' in part:
                    key_name, value = part.split('=', 1)
                    if key_name in ['year', 'month', 'day', 'hour']:
                        partition_dict[key_name] = int(value)
            
            if len(partition_dict) == 4:
                return (
                    partition_dict['year'],
                    partition_dict['month'],
                    partition_dict['day'],
                    partition_dict['hour']
                )
        except (ValueError, KeyError):
            pass
        
        return None
    
    def _scan_s3_partitions(self) -> List[PartitionInfo]:
        """
        Scan S3 bucket to discover all partitions.
        
        Returns:
            List of PartitionInfo objects
        """
        logger.info(f"Scanning S3 bucket: s3://{self.catalog.bucket}/{self.catalog.data_prefix}")
        
        partitions_map: Dict[Tuple[int, int, int, int], PartitionInfo] = {}
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.catalog.bucket,
                Prefix=self.catalog.data_prefix
            )
            
            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    partition_tuple = self._parse_partition_from_s3_key(key)
                    
                    if partition_tuple:
                        year, month, day, hour = partition_tuple
                        
                        if partition_tuple not in partitions_map:
                            s3_location = f"s3://{self.catalog.bucket}/{self.catalog.get_partition_path(year, month, day, hour)}"
                            partitions_map[partition_tuple] = PartitionInfo(
                                year=year,
                                month=month,
                                day=day,
                                hour=hour,
                                s3_location=s3_location,
                                in_catalog=False,
                                file_count=0
                            )
                        
                        partitions_map[partition_tuple].file_count += 1
            
            partitions = list(partitions_map.values())
            logger.info(f"Found {len(partitions)} partitions in S3")
            return partitions
            
        except ClientError as e:
            logger.error(f"Failed to scan S3: {e}")
            raise
    
    def _get_catalog_partitions(self) -> List[PartitionInfo]:
        """
        Get all partitions from Glue catalog.
        
        Returns:
            List of PartitionInfo objects
        """
        logger.info(f"Fetching partitions from Glue catalog")
        
        try:
            catalog_partitions = self.catalog.list_partitions(max_results=1000)
            
            partitions = []
            for p in catalog_partitions:
                s3_location = f"s3://{self.catalog.bucket}/{self.catalog.get_partition_path(p['year'], p['month'], p['day'], p['hour'])}"
                partitions.append(PartitionInfo(
                    year=p['year'],
                    month=p['month'],
                    day=p['day'],
                    hour=p['hour'],
                    s3_location=s3_location,
                    in_catalog=True,
                    file_count=0
                ))
            
            logger.info(f"Found {len(partitions)} partitions in catalog")
            return partitions
            
        except ClientError as e:
            logger.error(f"Failed to fetch catalog partitions: {e}")
            raise
    
    # ------------------------------------------------------------------
    # Deep checks: Athena query, data integrity, call asset verification
    # ------------------------------------------------------------------
    
    def _run_athena_query_test(self) -> Dict[str, Any]:
        """Test Athena query execution against the table."""
        import time as _time
        try:
            athena = _localstack_boto_client('athena', self.catalog.region)
            bucket = self.catalog.bucket
            db = self.catalog.database_name
            table = self.catalog.table_name
            output = f"s3://{bucket}/athena-results/"
            
            start = _time.time()
            resp = athena.start_query_execution(
                QueryString=f'SELECT count(*) as cnt FROM "{db}"."{table}"',
                QueryExecutionContext={"Database": db},
                ResultConfiguration={"OutputLocation": output},
            )
            qid = resp["QueryExecutionId"]
            
            # Poll (10s timeout)
            for _ in range(20):
                _time.sleep(0.5)
                status = athena.get_query_execution(QueryExecutionId=qid)
                state = status["QueryExecution"]["Status"]["State"]
                if state == "SUCCEEDED":
                    elapsed = (_time.time() - start) * 1000
                    results = athena.get_query_results(QueryExecutionId=qid)
                    rows = results["ResultSet"]["Rows"]
                    count = int(rows[1]["Data"][0]["VarCharValue"]) if len(rows) > 1 else 0
                    return {"success": True, "time_ms": round(elapsed, 1), "row_count": count, "error": None}
                if state in ("FAILED", "CANCELLED"):
                    reason = status["QueryExecution"]["Status"].get("StateChangeReason", "")
                    return {"success": False, "time_ms": 0, "row_count": 0, "error": f"{state}: {reason}"}
            
            return {"success": False, "time_ms": 0, "row_count": 0, "error": "Query timeout (10s)"}
        except Exception as e:
            return {"success": False, "time_ms": 0, "row_count": 0, "error": str(e)}

    def execute_query(
        self,
        query: str,
        max_rows: int = 1000,
        timeout_seconds: int = 30,
        max_query_length: int = 8192,
    ) -> Dict[str, Any]:
        """
        Execute a user-provided SELECT query against the configured Glue table via Athena.
        Validates that the query is SELECT-only and references only the configured database and table.
        Returns columns, rows (capped at max_rows), row_count, execution_time_ms, truncated.
        """
        import re
        import time as _time

        q = query.strip() if query else ""
        if len(q) > max_query_length:
            return {"error": f"Query exceeds max length ({max_query_length} bytes)"}
        if not q.upper().startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed"}
        db = self.catalog.database_name
        table = self.catalog.table_name
        from_pattern = re.compile(
            r"\bFROM\s+[\"']?" + re.escape(db) + r"[\"']?\s*\.\s*[\"']?" + re.escape(table) + r"[\"']?",
            re.IGNORECASE,
        )
        if not from_pattern.search(q):
            return {"error": f"Query must reference only the configured table: {db}.{table}"}

        try:
            athena = _localstack_boto_client("athena", self.catalog.region)
            output = f"s3://{self.catalog.bucket}/athena-results/"
            start = _time.time()
            resp = athena.start_query_execution(
                QueryString=q,
                QueryExecutionContext={"Database": db},
                ResultConfiguration={"OutputLocation": output},
            )
            qid = resp["QueryExecutionId"]
            poll_interval = 0.5
            max_polls = int(timeout_seconds / poll_interval)
            for _ in range(max_polls):
                _time.sleep(poll_interval)
                status = athena.get_query_execution(QueryExecutionId=qid)
                state = status["QueryExecution"]["Status"]["State"]
                if state == "SUCCEEDED":
                    elapsed_ms = (_time.time() - start) * 1000
                    results = athena.get_query_results(QueryExecutionId=qid)
                    rows_raw = results["ResultSet"]["Rows"]
                    if not rows_raw:
                        return {
                            "columns": [],
                            "rows": [],
                            "row_count": 0,
                            "execution_time_ms": round(elapsed_ms, 1),
                            "truncated": False,
                        }
                    columns = [c.get("VarCharValue", "") for c in rows_raw[0]["Data"]]
                    data_rows = []
                    for row in rows_raw[1:]:
                        data_rows.append([cell.get("VarCharValue", "") for cell in row["Data"]])
                    truncated = len(data_rows) > max_rows
                    if truncated:
                        data_rows = data_rows[:max_rows]
                    return {
                        "columns": columns,
                        "rows": data_rows,
                        "row_count": len(data_rows),
                        "execution_time_ms": round(elapsed_ms, 1),
                        "truncated": truncated,
                    }
                if state in ("FAILED", "CANCELLED"):
                    reason = status["QueryExecution"]["Status"].get("StateChangeReason", "")
                    return {"error": f"{state}: {reason}"}
            return {"error": f"Query timeout ({timeout_seconds}s)"}
        except Exception as e:
            logger.exception("execute_query failed")
            return {"error": str(e)}

    def _check_data_integrity(self, max_samples: int = 5) -> Tuple[int, List[Dict]]:
        """Sample metadata JSON files from S3 and validate field integrity."""
        import json as _json
        issues = []
        checked = 0
        required_fields = {"task_id", "status"}
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            sample_keys = []
            for page in paginator.paginate(Bucket=self.catalog.bucket, Prefix=self.catalog.data_prefix, MaxKeys=200):
                for obj in page.get('Contents', []):
                    if obj['Key'].endswith('.json'):
                        sample_keys.append(obj['Key'])
                        if len(sample_keys) >= max_samples:
                            break
                if len(sample_keys) >= max_samples:
                    break
            
            for key in sample_keys:
                checked += 1
                file_issues = []
                try:
                    resp = self.s3_client.get_object(Bucket=self.catalog.bucket, Key=key)
                    data = _json.loads(resp['Body'].read().decode('utf-8'))
                    
                    # Check required fields
                    missing = required_fields - set(data.keys())
                    if missing:
                        file_issues.append(f"Missing required fields: {', '.join(missing)}")
                    
                    # Check created_at is numeric (bigint), not string
                    created_at = data.get('created_at')
                    if created_at is not None:
                        if isinstance(created_at, str):
                            file_issues.append(f"created_at is string '{created_at[:20]}...', expected numeric (bigint)")
                    
                except _json.JSONDecodeError:
                    file_issues.append("File is not valid JSON")
                except Exception as e:
                    file_issues.append(f"Could not read file: {str(e)[:80]}")
                
                if file_issues:
                    issues.append({"file": f"s3://{self.catalog.bucket}/{key}", "issues": file_issues})
        except Exception as e:
            logger.warning(f"Data integrity check failed: {e}")
        
        return checked, issues
    
    def _check_call_assets(self, max_calls: int = 5) -> Tuple[List[Dict], int, int]:
        """Query Athena for sample calls and verify each call's asset files exist in S3."""
        import time as _time
        import json as _json
        
        checks = []
        all_ok = 0
        some_missing = 0
        
        try:
            athena = _localstack_boto_client('athena', self.catalog.region)
            db = self.catalog.database_name
            table = self.catalog.table_name
            output = f"s3://{self.catalog.bucket}/athena-results/"
            
            query = f"""
                SELECT task_id, status, direction, origin_phone, destination_phone,
                       queue_name, duration_seconds, created_at,
                       recording_file, transcript_file, analysis_file, sfdc_action_file
                FROM "{db}"."{table}"
                ORDER BY year DESC, month DESC, day DESC, hour DESC
                LIMIT {max_calls}
            """
            
            resp = athena.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": db},
                ResultConfiguration={"OutputLocation": output},
            )
            qid = resp["QueryExecutionId"]
            
            # Poll
            for _ in range(20):
                _time.sleep(0.5)
                status = athena.get_query_execution(QueryExecutionId=qid)
                if status["QueryExecution"]["Status"]["State"] == "SUCCEEDED":
                    break
                if status["QueryExecution"]["Status"]["State"] in ("FAILED", "CANCELLED"):
                    return checks, 0, 0
            
            results = athena.get_query_results(QueryExecutionId=qid)
            rows = results["ResultSet"]["Rows"]
            if len(rows) < 2:
                return checks, 0, 0
            
            cols = [c["VarCharValue"] for c in rows[0]["Data"]]
            
            for row in rows[1:]:
                record = {}
                for i, col in enumerate(cols):
                    record[col] = row["Data"][i].get("VarCharValue") if i < len(row["Data"]) else None
                
                task_id = record.get("task_id", "?")
                
                # Overview check
                overview_fields = ["task_id", "status", "direction", "origin_phone", "destination_phone", "queue_name", "duration_seconds", "created_at"]
                present = sum(1 for f in overview_fields if record.get(f))
                overview = {"status": "pass" if present >= 6 else "warn", "fields_present": present, "fields_total": len(overview_fields)}
                
                # Check each asset file
                def check_s3_file(s3_path):
                    if not s3_path:
                        return {"status": "missing", "exists": False}
                    try:
                        path = s3_path[5:] if s3_path.startswith("s3://") else s3_path
                        bucket, key = path.split("/", 1)
                        head = self.s3_client.head_object(Bucket=bucket, Key=key)
                        return {
                            "status": "pass",
                            "exists": True,
                            "size_bytes": head.get("ContentLength", 0),
                            "content_type": head.get("ContentType", ""),
                        }
                    except ClientError:
                        return {"status": "fail", "exists": False}
                    except Exception:
                        return {"status": "fail", "exists": False}
                
                recording = check_s3_file(record.get("recording_file"))
                transcript = check_s3_file(record.get("transcript_file"))
                analysis = check_s3_file(record.get("analysis_file"))
                sfdc = check_s3_file(record.get("sfdc_action_file"))
                
                # If analysis file exists, validate it has expected keys
                if analysis.get("exists") and record.get("analysis_file"):
                    try:
                        path = record["analysis_file"]
                        if path.startswith("s3://"):
                            path = path[5:]
                        b, k = path.split("/", 1)
                        obj = self.s3_client.get_object(Bucket=b, Key=k)
                        data = _json.loads(obj['Body'].read().decode('utf-8'))
                        analysis["has_grading"] = "grading" in data
                        analysis["has_compliance"] = "compliance" in data
                        analysis["has_deal_potential"] = "deal_potential" in data
                    except Exception:
                        pass
                
                diarization = {"status": "missing", "exists": False}
                if transcript.get("exists") and record.get("transcript_file"):
                    try:
                        path = record["transcript_file"]
                        if path.startswith("s3://"):
                            path = path[5:]
                        b, k = path.split("/", 1)
                        obj = self.s3_client.get_object(Bucket=b, Key=k)
                        data = _json.loads(obj['Body'].read().decode('utf-8'))
                        segments = data.get("transcript") if isinstance(data.get("transcript"), list) else []
                        has_speaker = any(
                            seg.get("speaker") or seg.get("role") for seg in segments if isinstance(seg, dict)
                        )
                        diarization = {"status": "pass" if has_speaker else "warn", "exists": bool(has_speaker)}
                    except Exception:
                        pass
                
                has_all = all(a.get("exists", False) or a.get("status") == "missing" for a in [recording, transcript, analysis, sfdc])
                has_missing = any(a.get("status") == "fail" for a in [recording, transcript, analysis, sfdc])
                
                if has_missing:
                    some_missing += 1
                else:
                    all_ok += 1
                
                checks.append({
                    "task_id": task_id,
                    "overview": overview,
                    "recording": recording,
                    "transcript": transcript,
                    "diarization": diarization,
                    "analysis": analysis,
                    "sfdc_action": sfdc,
                })
        
        except Exception as e:
            logger.warning(f"Call asset check failed: {e}")
        
        return checks, all_ok, some_missing
    
    def diagnose(self) -> DiagnosticReport:
        """
        Run full diagnostics on the Call Database.
        
        Returns:
            DiagnosticReport with findings and recommendations
        """
        self._current_stage = DiagnosticStage.CHECKING
        timestamp = datetime.now().isoformat()
        
        try:
            # Check if database exists
            db_exists = self.catalog.database_exists()
            
            # Check if table exists
            table_exists = self.catalog.table_exists() if db_exists else False
            
            # Check S3 bucket accessibility
            try:
                self.s3_client.head_bucket(Bucket=self.catalog.bucket)
                s3_accessible = True
            except ClientError:
                s3_accessible = False
            
            # If basic infrastructure is missing, return early
            if not db_exists or not table_exists or not s3_accessible:
                self._current_stage = DiagnosticStage.REPORTING
                recommendations = []
                if not s3_accessible:
                    recommendations.append("S3 bucket is not accessible - check permissions and bucket existence")
                if not db_exists:
                    recommendations.append("Database does not exist - run setup_glue.py --create to initialize")
                if not table_exists and db_exists:
                    recommendations.append("Table does not exist - run setup_glue.py --create to initialize")
                
                return DiagnosticReport(
                    stage=self._current_stage,
                    database_exists=db_exists,
                    table_exists=table_exists,
                    s3_bucket_accessible=s3_accessible,
                    total_s3_partitions=0,
                    total_catalog_partitions=0,
                    missing_partitions=[],
                    orphaned_partitions=[],
                    schema_info=None,
                    issues_found=sum([not db_exists, not table_exists, not s3_accessible]),
                    recommendations=recommendations,
                    timestamp=timestamp
                )
            
            # Validate table schema
            schema_info = self._validate_schema()
            logger.info(f"Schema validation: valid={schema_info.is_valid}, issues={len(schema_info.issues)}")
            
            # Scan S3 for partitions
            s3_partitions = self._scan_s3_partitions()
            
            # Get catalog partitions
            catalog_partitions = self._get_catalog_partitions()
            
            # Create lookup sets
            s3_partition_keys = {
                (p.year, p.month, p.day, p.hour) for p in s3_partitions
            }
            catalog_partition_keys = {
                (p.year, p.month, p.day, p.hour) for p in catalog_partitions
            }
            
            # Find missing partitions (in S3 but not in catalog)
            missing_keys = s3_partition_keys - catalog_partition_keys
            missing_partitions = [
                p for p in s3_partitions
                if (p.year, p.month, p.day, p.hour) in missing_keys
            ]
            
            # Find orphaned partitions (in catalog but not in S3)
            orphaned_keys = catalog_partition_keys - s3_partition_keys
            orphaned_partitions = [
                p for p in catalog_partitions
                if (p.year, p.month, p.day, p.hour) in orphaned_keys
            ]
            
            # Generate recommendations
            recommendations = []
            
            # Schema issues (highest priority - must fix before partitions work)
            if not schema_info.is_valid:
                recommendations.append(
                    f"CRITICAL: Schema mismatch detected ({len(schema_info.issues)} issues) - run 'Rebuild Table' to fix"
                )
                for issue in schema_info.issues[:3]:  # Show first 3 issues
                    recommendations.append(f"  - {issue}")
                if len(schema_info.issues) > 3:
                    recommendations.append(f"  - ... and {len(schema_info.issues) - 3} more issues")
            
            if missing_partitions:
                recommendations.append(
                    f"Found {len(missing_partitions)} missing partitions - run repair to add them to catalog"
                )
            if orphaned_partitions:
                recommendations.append(
                    f"Found {len(orphaned_partitions)} orphaned partitions in catalog with no S3 data"
                )
            if schema_info.is_valid and not missing_partitions and not orphaned_partitions:
                recommendations.append("Database is healthy - no issues detected")
            
            # ── Deep checks ──
            
            # Athena query test
            logger.info("Running Athena query test...")
            athena_result = self._run_athena_query_test()
            if not athena_result["success"]:
                recommendations.append(f"Athena query FAILED: {athena_result['error']}")
            
            # Data integrity sampling
            logger.info("Running data integrity check...")
            data_checked, data_issues = self._check_data_integrity(max_samples=5)
            if data_issues:
                recommendations.append(f"Data integrity: {len(data_issues)} of {data_checked} sampled files have issues")
            
            # Call asset verification
            logger.info("Running call asset verification...")
            call_checks, calls_ok, calls_missing = self._check_call_assets(max_calls=5)
            if calls_missing > 0:
                recommendations.append(f"Call assets: {calls_missing} of {len(call_checks)} sampled calls have missing asset files")
            
            # Set stage based on what was found
            if not schema_info.is_valid or missing_partitions:
                self._current_stage = DiagnosticStage.READY
            else:
                self._current_stage = DiagnosticStage.COMPLETE
            
            # Count total issues including schema
            total_issues = len(missing_partitions) + len(orphaned_partitions)
            if not schema_info.is_valid:
                total_issues += len(schema_info.issues)
            if not athena_result["success"]:
                total_issues += 1
            total_issues += len(data_issues)
            total_issues += calls_missing

            # WXCC task-tracker probe was removed alongside the call-processing
            # decommissioning (the wxcc-task-tracking DDB table is no longer
            # provisioned). tracker_summary intentionally stays None.
            tracker_summary = None

            return DiagnosticReport(
                stage=self._current_stage,
                database_exists=db_exists,
                table_exists=table_exists,
                s3_bucket_accessible=s3_accessible,
                total_s3_partitions=len(s3_partitions),
                total_catalog_partitions=len(catalog_partitions),
                missing_partitions=missing_partitions,
                orphaned_partitions=orphaned_partitions,
                schema_info=schema_info,
                issues_found=total_issues,
                recommendations=recommendations,
                timestamp=timestamp,
                athena_query_success=athena_result["success"],
                athena_query_time_ms=athena_result["time_ms"],
                athena_row_count=athena_result["row_count"],
                athena_error=athena_result["error"],
                data_samples_checked=data_checked,
                data_integrity_issues=data_issues,
                call_asset_checks=call_checks,
                calls_with_all_assets=calls_ok,
                calls_with_missing_assets=calls_missing,
                tracker_summary=tracker_summary,
            )
            
        except Exception as e:
            self._current_stage = DiagnosticStage.ERROR
            logger.error(f"Diagnostic failed: {e}")
            return DiagnosticReport(
                stage=self._current_stage,
                database_exists=False,
                table_exists=False,
                s3_bucket_accessible=False,
                total_s3_partitions=0,
                total_catalog_partitions=0,
                missing_partitions=[],
                orphaned_partitions=[],
                schema_info=None,
                issues_found=0,
                recommendations=[],
                timestamp=timestamp,
                error=str(e)
            )
    
    def repair_partitions(self, missing_partitions: List[PartitionInfo]) -> RepairResult:
        """
        Repair missing partitions by adding them to the catalog.
        
        Args:
            missing_partitions: List of partitions to add
            
        Returns:
            RepairResult with operation details
        """
        self._current_stage = DiagnosticStage.REPAIRING
        timestamp = datetime.now().isoformat()
        
        operations_performed = ["add_missing_partitions"]
        partitions_added = 0
        partitions_failed = 0
        errors = []
        
        try:
            logger.info(f"Repairing {len(missing_partitions)} missing partitions...")
            
            for partition in missing_partitions:
                try:
                    result = self.catalog.add_partition(
                        year=partition.year,
                        month=partition.month,
                        day=partition.day,
                        hour=partition.hour
                    )
                    
                    if result['status'] in ['created', 'exists']:
                        partitions_added += 1
                        logger.info(f"Added partition: year={partition.year}/month={partition.month}/day={partition.day}/hour={partition.hour}")
                    else:
                        partitions_failed += 1
                        errors.append(f"Unexpected status for partition {partition.year}/{partition.month}/{partition.day}/{partition.hour}: {result['status']}")
                        
                except Exception as e:
                    partitions_failed += 1
                    error_msg = f"Failed to add partition {partition.year}/{partition.month}/{partition.day}/{partition.hour}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            self._current_stage = DiagnosticStage.COMPLETE
            success = partitions_failed == 0
            
            return RepairResult(
                stage=self._current_stage,
                operations_performed=operations_performed,
                partitions_added=partitions_added,
                partitions_failed=partitions_failed,
                table_rebuilt=False,
                success=success,
                errors=errors,
                timestamp=timestamp
            )
            
        except Exception as e:
            self._current_stage = DiagnosticStage.ERROR
            logger.error(f"Repair failed: {e}")
            return RepairResult(
                stage=self._current_stage,
                operations_performed=operations_performed,
                partitions_added=partitions_added,
                partitions_failed=partitions_failed,
                table_rebuilt=False,
                success=False,
                errors=[str(e)],
                timestamp=timestamp
            )
    
    def remove_orphaned_partitions(self, orphaned_partitions: List[PartitionInfo]) -> RepairResult:
        """
        Remove orphaned partitions from the catalog (partitions with no S3 data).
        
        This is an advanced/optional operation. Orphaned partitions don't cause errors,
        but removing them keeps the catalog clean.
        
        Args:
            orphaned_partitions: List of orphaned partitions to remove
            
        Returns:
            RepairResult with operation details
        """
        self._current_stage = DiagnosticStage.REPAIRING
        timestamp = datetime.now().isoformat()
        
        operations_performed = ["remove_orphaned_partitions"]
        partitions_removed = 0
        partitions_failed = 0
        errors = []
        
        try:
            logger.info(f"Removing {len(orphaned_partitions)} orphaned partitions from catalog...")
            
            for partition in orphaned_partitions:
                try:
                    partition_values = [
                        str(partition.year),
                        str(partition.month),
                        str(partition.day),
                        str(partition.hour)
                    ]
                    
                    self.catalog.glue_client.delete_partition(
                        DatabaseName=self.catalog.database_name,
                        TableName=self.catalog.table_name,
                        PartitionValues=partition_values
                    )
                    
                    partitions_removed += 1
                    logger.info(f"Removed orphaned partition: year={partition.year}/month={partition.month}/day={partition.day}/hour={partition.hour}")
                    
                except Exception as e:
                    partitions_failed += 1
                    error_msg = f"Failed to remove partition {partition.year}/{partition.month}/{partition.day}/{partition.hour}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            self._current_stage = DiagnosticStage.COMPLETE
            success = partitions_failed == 0
            
            logger.info(f"Orphan removal complete: {partitions_removed} partitions removed, {partitions_failed} failed")
            
            return RepairResult(
                stage=self._current_stage,
                operations_performed=operations_performed,
                partitions_added=partitions_removed,  # Reuse field for count
                partitions_failed=partitions_failed,
                table_rebuilt=False,
                success=success,
                errors=errors,
                timestamp=timestamp
            )
            
        except Exception as e:
            self._current_stage = DiagnosticStage.ERROR
            logger.error(f"Orphan removal failed: {e}")
            return RepairResult(
                stage=self._current_stage,
                operations_performed=operations_performed,
                partitions_added=0,
                partitions_failed=0,
                table_rebuilt=False,
                success=False,
                errors=[str(e)],
                timestamp=timestamp
            )
    
    def rebuild_table(self) -> RepairResult:
        """
        Rebuild the table by dropping and recreating it, then reindexing all S3 data.
        
        Returns:
            RepairResult with operation details
        """
        self._current_stage = DiagnosticStage.REPAIRING
        timestamp = datetime.now().isoformat()
        
        operations_performed = ["drop_table", "create_table", "rescan_s3", "add_all_partitions"]
        errors = []
        
        try:
            logger.info("Rebuilding table...")
            
            # Drop existing table
            if self.catalog.table_exists():
                self.catalog.delete_table()
                logger.info("Dropped existing table")
            
            # Create fresh table
            self.catalog.create_calls_table()
            logger.info("Created fresh table")
            
            # Scan S3 and add all partitions
            s3_partitions = self._scan_s3_partitions()
            logger.info(f"Found {len(s3_partitions)} partitions in S3, adding to catalog...")
            
            partitions_added = 0
            partitions_failed = 0
            
            for partition in s3_partitions:
                try:
                    self.catalog.add_partition(
                        year=partition.year,
                        month=partition.month,
                        day=partition.day,
                        hour=partition.hour
                    )
                    partitions_added += 1
                except Exception as e:
                    partitions_failed += 1
                    errors.append(f"Failed to add partition {partition.year}/{partition.month}/{partition.day}/{partition.hour}: {str(e)}")
            
            self._current_stage = DiagnosticStage.COMPLETE
            success = partitions_failed == 0
            
            logger.info(f"Table rebuild complete: {partitions_added} partitions added, {partitions_failed} failed")
            
            return RepairResult(
                stage=self._current_stage,
                operations_performed=operations_performed,
                partitions_added=partitions_added,
                partitions_failed=partitions_failed,
                table_rebuilt=True,
                success=success,
                errors=errors,
                timestamp=timestamp
            )
            
        except Exception as e:
            self._current_stage = DiagnosticStage.ERROR
            logger.error(f"Table rebuild failed: {e}")
            return RepairResult(
                stage=self._current_stage,
                operations_performed=operations_performed,
                partitions_added=0,
                partitions_failed=0,
                table_rebuilt=False,
                success=False,
                errors=[str(e)],
                timestamp=timestamp
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current operation status.
        
        Returns:
            Status dictionary
        """
        return {
            "stage": self._current_stage.value,
            "database": self.catalog.database_name,
            "table": self.catalog.table_name,
            "bucket": self.catalog.bucket,
            "timestamp": datetime.now().isoformat()
        }
