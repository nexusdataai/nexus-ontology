"""
Foundry Workspace Repository

Single-table DynamoDB access layer for the Foundry workspace - the central
hub for business / configuration / semantic entities in Nexus AI.

Item layout (single-table style, mirrors transformation-system):

| Entity                    | PK                          | SK                                  | GSI1PK                  | GSI1SK                    |
|---------------------------|-----------------------------|-------------------------------------|-------------------------|---------------------------|
| Solution metadata         | SOLUTION#{solutionId}       | META                                | SOLUTION                | {name|lower}              |
| Solution -> View link     | SOLUTION#{solutionId}       | VIEW#{order:06d}#{viewId}           | VIEW#{viewId}           | SOLUTION#{solutionId}     |
| View metadata             | VIEW#{viewId}               | META                                | VIEW                    | {name|lower}              |
| View -> Dashboard tab     | VIEW#{viewId}               | TAB#{order:06d}#{tabId}             | DASHBOARD#{dashboardId} | VIEW#{viewId}             |
| Dashboard metadata        | DASHBOARD#{uid}             | META                                | DASHBOARD               | {updatedAt}               |
| Tool metadata             | TOOL#{toolId}               | META                                | TOOL                    | {updatedAt}               |
| Tool version snapshot     | TOOL#{toolId}               | VERSION#{n:06d}                     | TOOL_VERSION            | {toolId}#{n:06d}          |
| Tool tag link             | TOOL#{toolId}               | TAG#{tag}                           | TAG#{tag}               | TOOL#{toolId}             |
| Data Plane                | DATAPLANE#{id}              | META                                | DATAPLANE               | {type}#{name|lower}       |
| Connector                 | CONNECTOR#{id}              | META                                | CONNECTOR               | {updatedAt}               |
| Connector API             | CONNECTOR#{connectorId}     | API#{apiId}                         | CONNECTORAPI#{apiId}    | CONNECTOR#{connectorId}   |
| Connector Setting         | CONNECTORSETTING#{provider} | META                                | CONNECTORSETTING        | {provider}                |
| Mapping Rule (canonical)  | MAPPINGRULE#{id}            | META                                | MAPPINGRULE             | {sourceDp}#{targetVdl}    |
| Mapping Rule (by source)  | DATAPLANE#{sourceDpId}      | MAPPING#{ruleId}                    | -                       | -                         |
| Mapping Rule (by target)  | VDLENTITY#{vdlName}         | MAPPING#{ruleId}                    | -                       | -                         |
| VDL Entity                | VDLENTITY#{name}            | META                                | VDLENTITY               | {name|lower}              |
| Policy doc                | POLICY#{slug}               | META                                | POLICY                  | {slug|lower}              |
| Workflow definition       | WORKFLOWDEF#{slug}          | META                                | WORKFLOWDEF             | {slug|lower}              |
| Integration definition    | INTEGRATIONDEF#{slug}       | META                                | INTEGRATIONDEF          | {slug|lower}              |
| Simulator identity        | SIM#{service}               | META                                | SIM                     | {service|lower}           |
| Simulator table metadata  | SIM#{service}               | TABLE#{schema}.{table}              | -                       | -                         |
| Data Source definition    | DATASOURCE#{id}             | META                                | DATASOURCE              | {type}#{name|lower}       |
| VDL API spec              | VDLAPI#{apiId}              | META                                | VDLAPI                  | {verb}#{entity|lower}     |
| VDL API impl binding      | VDLAPI#{apiId}              | IMPL#{implId}                       | -                       | -                         |
| Connector API (flat reg)  | CONNAPI#{apiId}             | META                                | CONNAPI                 | {target}#{apiId|lower}    |
| Connector API audit event | CONNAPI#{apiId}             | AUDIT#{iso_ts}#{eventId}            | -                       | -                         |
| Automation playbook       | AUTOMATION#{useCaseId}      | META                                | AUTOMATION              | {solution}#{useCaseId}    |
| Solution YAML (NLP idx)   | SOLUTIONYAML#{solutionId}   | META                                | SOLUTIONYAML            | {solutionId|lower}        |
| Tools Registry entry      | TOOLREG#{toolId}            | META                                | TOOLREG                 | {group}#{toolId|lower}    |
| Tools Registry impl       | TOOLREG#{toolId}            | IMPL#{lang}#{version}               | -                       | -                         |
| Knowledge Pipeline meta   | KP#{pipelineId}             | META                                | KP                      | {pipelineId|lower}        |
| Knowledge Pipeline run    | KP#{pipelineId}             | RUN#{iso_ts}                        | -                       | -                         |

Mapping-rule writes are transactional (3 rows: canonical META + 2 denormalized
link rows) so list-by-source and list-by-target queries are PK-direct without
needing a second GSI.

VDL Entity, Policy, Workflow Definition, and Integration Definition rows form
the Supply Chain Foundry knowledge content — they carry the original source
file text under ``contentText`` plus structured metadata, and are the
authoritative source consumed by the Knowledge Processor pipeline (replacing
the legacy ``enterprise-knowledge/`` file reads). One-time bootstrap from those
files is provided by ``bootstrap_foundry_from_files.py``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from loguru import logger


class FoundryWorkspaceRepositoryError(Exception):
    """Exception raised for foundry workspace repository errors."""
    pass


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------

def solution_pk(solution_id: str) -> str:
    return f"SOLUTION#{solution_id}"


def view_pk(view_id: str) -> str:
    return f"VIEW#{view_id}"


def dashboard_pk(dashboard_id: str) -> str:
    return f"DASHBOARD#{dashboard_id}"


def journey_pk(journey_id: str) -> str:
    return f"JOURNEY#{journey_id}"


def tool_pk(tool_id: str) -> str:
    return f"TOOL#{tool_id}"


def tool_version_sk(version: int) -> str:
    return f"VERSION#{version:06d}"


def tool_tag_sk(tag: str) -> str:
    return f"TAG#{tag}"


def view_link_sk(order: int, view_id: str) -> str:
    return f"VIEW#{order:06d}#{view_id}"


def tab_link_sk(order: int, tab_id: str) -> str:
    return f"TAB#{order:06d}#{tab_id}"


# --- New PK builders for consolidated entities (Data Planes, Connectors,
# --- Connector APIs, Connector Settings, Mapping Rules, VDL Entities)

def data_plane_pk(data_plane_id: str) -> str:
    return f"DATAPLANE#{data_plane_id}"


def connector_pk(connector_id: str) -> str:
    return f"CONNECTOR#{connector_id}"


def connector_api_sk(api_id: str) -> str:
    return f"API#{api_id}"


def connector_setting_pk(provider: str) -> str:
    return f"CONNECTORSETTING#{provider}"


def mapping_rule_pk(rule_id: str) -> str:
    return f"MAPPINGRULE#{rule_id}"


def mapping_link_sk(rule_id: str) -> str:
    """SK used on denormalized link rows under DATAPLANE#... and VDLENTITY#... PKs."""
    return f"MAPPING#{rule_id}"


def vdl_entity_pk(name: str) -> str:
    return f"VDLENTITY#{name}"


# --- PK builders for Supply Chain Foundry knowledge content (policies,
# --- workflows, integrations). Slugs are derived from source filenames (with
# --- extension stripped) so that round-trips between files and DDB are
# --- deterministic and human-debuggable.

def policy_pk(slug: str) -> str:
    return f"POLICY#{slug}"


def workflow_def_pk(slug: str) -> str:
    return f"WORKFLOWDEF#{slug}"


def integration_def_pk(slug: str) -> str:
    return f"INTEGRATIONDEF#{slug}"


# --- PK builders introduced by the data-organization spec alignment
# --- (Phase 0). SIM/DATASOURCE/VDLAPI/CONNAPI/AUTOMATION/SOLUTIONYAML/
# --- TOOLREG/KP namespaces mirror the plane taxonomy in
# --- ``nexus-backend/src/services/planes.py``.

def simulator_pk(service: str) -> str:
    return f"SIM#{service}"


def simulator_table_sk(schema: str, table: str) -> str:
    return f"TABLE#{schema}.{table}"


def data_source_pk(data_source_id: str) -> str:
    return f"DATASOURCE#{data_source_id}"


def vdl_api_pk(api_id: str) -> str:
    return f"VDLAPI#{api_id}"


def vdl_api_impl_sk(impl_id: str) -> str:
    return f"IMPL#{impl_id}"


def conn_api_pk(api_id: str) -> str:
    """Flat Connector API Registry PK (Phase 2). Distinct from the legacy
    nested ``CONNECTOR#{connectorId}/API#{apiId}`` layout, which we keep
    around as a compatibility fallback."""
    return f"CONNAPI#{api_id}"


def conn_api_audit_sk(iso_ts: str, event_id: str) -> str:
    return f"AUDIT#{iso_ts}#{event_id}"


def automation_pk(use_case_id: str) -> str:
    return f"AUTOMATION#{use_case_id}"


def solution_yaml_pk(solution_id: str) -> str:
    return f"SOLUTIONYAML#{solution_id}"


def tool_reg_pk(tool_id: str) -> str:
    return f"TOOLREG#{tool_id}"


def tool_reg_impl_sk(lang: str, version: str) -> str:
    return f"IMPL#{lang}#{version}"


def kp_pk(pipeline_id: str) -> str:
    return f"KP#{pipeline_id}"


def kp_run_sk(iso_ts: str) -> str:
    return f"RUN#{iso_ts}"


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class FoundryWorkspaceRepository:
    """DynamoDB repository for Solutions, Views, Dashboards (single-table)."""

    META_SK = "META"
    _transact_fallback_logged = False

    def __init__(self, table_name: Optional[str] = None):
        self._table_name = table_name or self._resolve_table_name()
        self._resource = self._build_resource()
        # Separate raw low-level client for transact_write_items: the resource's
        # client carries a high-level type translator that re-wraps already
        # wire-formatted AttributeValue dicts (turning {"S": "..."} into
        # {"M": {"S": ...}}), which makes transact ops fail validation.
        self._ll_client = self._build_low_level_client()
        self._table = self._resource.Table(self._table_name)
        logger.info(f"FoundryWorkspaceRepository initialized: table={self._table_name}")

    @staticmethod
    def _resolve_table_name() -> str:
        try:
            from src.config.config_provider import get_config
            return get_config().dynamodb_foundry_workspace_table
        except Exception:
            from src.config.resource_naming import dynamodb_table_name
            return dynamodb_table_name("foundry-workspace")

    @staticmethod
    def _build_resource():
        try:
            from src.config.localstack_config import get_localstack_config, is_localstack_enabled
            if is_localstack_enabled():
                cfg = get_localstack_config()
                return boto3.resource(
                    "dynamodb",
                    endpoint_url=cfg.get_service_endpoint("dynamodb"),
                    region_name=cfg.region,
                    aws_access_key_id=cfg.access_key,
                    aws_secret_access_key=cfg.secret_key,
                )
        except Exception:
            pass

        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL") or os.environ.get("AWS_ENDPOINT_URL_DYNAMODB")
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        if endpoint_url:
            return boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
        return boto3.resource("dynamodb", region_name=region)

    @staticmethod
    def _build_low_level_client():
        """Construct a fresh boto3 dynamodb client without the resource-level
        type translator. Used by transact_write_items where we pass raw
        AttributeValue wire-format items."""
        try:
            from src.config.localstack_config import get_localstack_config, is_localstack_enabled
            if is_localstack_enabled():
                cfg = get_localstack_config()
                return boto3.client(
                    "dynamodb",
                    endpoint_url=cfg.get_service_endpoint("dynamodb"),
                    region_name=cfg.region,
                    aws_access_key_id=cfg.access_key,
                    aws_secret_access_key=cfg.secret_key,
                )
        except Exception:
            pass

        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL") or os.environ.get("AWS_ENDPOINT_URL_DYNAMODB")
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        if endpoint_url:
            return boto3.client("dynamodb", endpoint_url=endpoint_url, region_name=region)
        return boto3.client("dynamodb", region_name=region)

    @classmethod
    def _transact_unsupported(cls, exc: ClientError) -> bool:
        code = exc.response.get("Error", {}).get("Code", "")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        if code == "UnknownOperationException":
            return "TransactWriteItems" in message
        if code == "ValidationException":
            return "TransactWriteItems" in message or "Unsupported operation" in message
        return False

    def _transact_write_items(self, ops: List[Dict[str, Any]]) -> None:
        """TransactWriteItems with sequential fallback for Scylla Alternator."""
        try:
            self._ll_client.transact_write_items(TransactItems=ops)
        except ClientError as e:
            if not self._transact_unsupported(e):
                raise
            if not FoundryWorkspaceRepository._transact_fallback_logged:
                logger.info(
                    "TransactWriteItems unsupported by DynamoDB endpoint — "
                    "using sequential writes (local Scylla Alternator)"
                )
                FoundryWorkspaceRepository._transact_fallback_logged = True
            self._transact_write_items_sequential(ops)

    def _transact_write_items_sequential(self, ops: List[Dict[str, Any]]) -> None:
        for op in ops:
            if "Put" in op:
                payload = op["Put"]
                self._ll_client.put_item(
                    TableName=payload["TableName"],
                    Item=payload["Item"],
                )
            elif "Delete" in op:
                payload = op["Delete"]
                self._ll_client.delete_item(
                    TableName=payload["TableName"],
                    Key=payload["Key"],
                )
            elif "Update" in op:
                payload = op["Update"]
                kwargs: Dict[str, Any] = {
                    "TableName": payload["TableName"],
                    "Key": payload["Key"],
                }
                for key in (
                    "UpdateExpression",
                    "ConditionExpression",
                    "ExpressionAttributeNames",
                    "ExpressionAttributeValues",
                ):
                    if key in payload:
                        kwargs[key] = payload[key]
                self._ll_client.update_item(**kwargs)
            else:
                raise FoundryWorkspaceRepositoryError(
                    f"Unsupported transact op keys: {list(op.keys())}"
                )

    @property
    def table(self):
        return self._table

    @property
    def table_name(self) -> str:
        return self._table_name

    # -----------------------------------------------------------------------
    # Generic helpers
    # -----------------------------------------------------------------------

    def get_meta(self, pk: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self._table.get_item(Key={"PK": pk, "SK": self.META_SK})
            return resp.get("Item")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                logger.warning(f"Foundry workspace table not found: {self._table_name}")
                return None
            logger.error(f"get_meta({pk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def put_meta(
        self,
        pk: str,
        attrs: Dict[str, Any],
        gsi1pk: Optional[str] = None,
        gsi1sk: Optional[str] = None,
        condition_not_exists: bool = False,
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {"PK": pk, "SK": self.META_SK, **attrs}
        if gsi1pk is not None:
            item["GSI1PK"] = gsi1pk
        if gsi1sk is not None:
            item["GSI1SK"] = gsi1sk

        kwargs: Dict[str, Any] = {"Item": item}
        if condition_not_exists:
            kwargs["ConditionExpression"] = "attribute_not_exists(PK)"
        try:
            self._table.put_item(**kwargs)
            return item
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ConditionalCheckFailedException":
                raise FoundryWorkspaceRepositoryError(f"Item already exists: {pk}")
            logger.error(f"put_meta({pk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def delete_pk(self, pk: str) -> int:
        """Delete all items under a given PK (META + child links). Returns deleted count."""
        try:
            deleted = 0
            last_key = None
            while True:
                kwargs: Dict[str, Any] = {
                    "KeyConditionExpression": Key("PK").eq(pk),
                    "ProjectionExpression": "PK, SK",
                }
                if last_key:
                    kwargs["ExclusiveStartKey"] = last_key
                resp = self._table.query(**kwargs)
                items = resp.get("Items", [])
                if items:
                    with self._table.batch_writer() as batch:
                        for item in items:
                            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                            deleted += 1
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
            return deleted
        except ClientError as e:
            logger.error(f"delete_pk({pk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def query_pk(self, pk: str, sk_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            cond = Key("PK").eq(pk)
            if sk_prefix:
                cond = cond & Key("SK").begins_with(sk_prefix)
            items: List[Dict[str, Any]] = []
            last_key = None
            while True:
                kwargs: Dict[str, Any] = {"KeyConditionExpression": cond}
                if last_key:
                    kwargs["ExclusiveStartKey"] = last_key
                resp = self._table.query(**kwargs)
                items.extend(resp.get("Items", []))
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
            return items
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return []
            logger.error(f"query_pk({pk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def query_gsi1(
        self,
        gsi1pk: str,
        gsi1sk_prefix: Optional[str] = None,
        scan_forward: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            cond = Key("GSI1PK").eq(gsi1pk)
            if gsi1sk_prefix:
                cond = cond & Key("GSI1SK").begins_with(gsi1sk_prefix)
            kwargs: Dict[str, Any] = {
                "IndexName": "GSI1",
                "KeyConditionExpression": cond,
                "ScanIndexForward": scan_forward,
            }
            if limit:
                kwargs["Limit"] = limit
            items: List[Dict[str, Any]] = []
            last_key = None
            while True:
                if last_key:
                    kwargs["ExclusiveStartKey"] = last_key
                resp = self._table.query(**kwargs)
                items.extend(resp.get("Items", []))
                last_key = resp.get("LastEvaluatedKey")
                if not last_key or (limit and len(items) >= limit):
                    break
            return items[:limit] if limit else items
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return []
            logger.error(f"query_gsi1({gsi1pk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def put_link(
        self,
        pk: str,
        sk: str,
        attrs: Dict[str, Any],
        gsi1pk: str,
        gsi1sk: str,
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": pk,
            "SK": sk,
            "GSI1PK": gsi1pk,
            "GSI1SK": gsi1sk,
            **attrs,
        }
        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"put_link({pk}, {sk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def delete_link(self, pk: str, sk: str) -> bool:
        try:
            self._table.delete_item(Key={"PK": pk, "SK": sk})
            return True
        except ClientError as e:
            logger.error(f"delete_link({pk}, {sk}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def transact_replace_links(
        self,
        pk: str,
        sk_prefix: str,
        existing_sks: List[str],
        new_items: List[Dict[str, Any]],
    ) -> None:
        """
        Atomically replace a set of link items under a PK.

        Used for reordering: deletes existing_sks and writes new_items in one
        TransactWriteItems call (max 100 ops total).
        """
        # DynamoDB forbids multiple operations targeting the same item key in a
        # single TransactWriteItems call. When an existing link is preserved at
        # the same SK (e.g. an existing tab keeps its order while a new tab is
        # appended), the Delete + Put would collide. The Put already overwrites
        # the existing item, so suppress the Delete for any SK that the Put set
        # also covers.
        new_sk_set = {item.get("SK") for item in new_items if item.get("SK")}

        ops: List[Dict[str, Any]] = []
        for sk in existing_sks:
            if sk in new_sk_set:
                continue
            ops.append({
                "Delete": {
                    "TableName": self._table_name,
                    "Key": {"PK": {"S": pk}, "SK": {"S": sk}},
                }
            })
        for item in new_items:
            put_item = {k: self._to_attr(v) for k, v in item.items() if v is not None}
            ops.append({
                "Put": {
                    "TableName": self._table_name,
                    "Item": put_item,
                }
            })
        if not ops:
            return
        if len(ops) > 100:
            raise FoundryWorkspaceRepositoryError(
                f"transact_replace_links exceeds 100 ops (got {len(ops)})"
            )
        try:
            self._transact_write_items(ops)
        except ClientError as e:
            # Surface the per-op CancellationReasons so a single ValidationError
            # in a transaction is debuggable. Boto3 hides them inside the
            # response dict and only exposes the generic message string.
            reasons = e.response.get("CancellationReasons") if hasattr(e, "response") else None
            try:
                ops_repr = json.dumps(ops, default=str)[:4000]
            except Exception:
                ops_repr = str(ops)[:4000]
            logger.error(
                f"transact_replace_links({pk}, {sk_prefix}) failed: {e} | "
                f"reasons={reasons} | ops={ops_repr}"
            )
            raise FoundryWorkspaceRepositoryError(str(e))

    @staticmethod
    def _to_attr(value: Any) -> Dict[str, Any]:
        """Minimal Python -> DynamoDB low-level attribute conversion for transact ops."""
        if value is None:
            return {"NULL": True}
        if isinstance(value, bool):
            return {"BOOL": value}
        if isinstance(value, (int, float)):
            return {"N": str(value)}
        if isinstance(value, str):
            return {"S": value}
        if isinstance(value, list):
            if not value:
                return {"L": []}
            return {"L": [FoundryWorkspaceRepository._to_attr(v) for v in value]}
        if isinstance(value, dict):
            return {"M": {k: FoundryWorkspaceRepository._to_attr(v) for k, v in value.items()}}
        # Pydantic v2 BaseModel — without this branch the fallback str() coerces
        # the model to its repr (e.g. "source_field='X' target_field='Y' ...")
        # and persists that as a DynamoDB string, silently corrupting nested data.
        if hasattr(value, "model_dump"):
            return FoundryWorkspaceRepository._to_attr(value.model_dump(by_alias=True))
        return {"S": str(value)}

    # =======================================================================
    # Data Plane CRUD (FDW / CDC / ETL connection configs)
    # =======================================================================

    def put_data_plane(self, data_plane_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        dp_type = str(attrs.get("type") or attrs.get("dataPlaneType") or "").lower()
        name = str(attrs.get("name") or "").lower()
        return self.put_meta(
            pk=data_plane_pk(data_plane_id),
            attrs=attrs,
            gsi1pk="DATAPLANE",
            gsi1sk=f"{dp_type}#{name}",
        )

    def get_data_plane(self, data_plane_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(data_plane_pk(data_plane_id))

    def list_data_planes(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("DATAPLANE")

    def delete_data_plane(self, data_plane_id: str) -> int:
        # Also delete any mapping link rows under this data plane PK.
        return self.delete_pk(data_plane_pk(data_plane_id))

    # =======================================================================
    # Connector + Connector API CRUD
    # =======================================================================

    def put_connector(self, connector_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        updated_at = str(attrs.get("updatedAt") or "")
        return self.put_meta(
            pk=connector_pk(connector_id),
            attrs=attrs,
            gsi1pk="CONNECTOR",
            gsi1sk=updated_at,
        )

    def get_connector(self, connector_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(connector_pk(connector_id))

    def list_connectors(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("CONNECTOR")

    def delete_connector(self, connector_id: str) -> int:
        # Cascade: also drops any API#... children under this connector PK.
        return self.delete_pk(connector_pk(connector_id))

    def put_connector_api(
        self,
        connector_id: str,
        api_id: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.put_link(
            pk=connector_pk(connector_id),
            sk=connector_api_sk(api_id),
            attrs=attrs,
            gsi1pk=f"CONNECTORAPI#{api_id}",
            gsi1sk=connector_pk(connector_id),
        )

    def get_connector_api(self, connector_id: str, api_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self._table.get_item(
                Key={"PK": connector_pk(connector_id), "SK": connector_api_sk(api_id)}
            )
            return resp.get("Item")
        except ClientError as e:
            logger.error(f"get_connector_api({connector_id}, {api_id}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def list_connector_apis(self, connector_id: str) -> List[Dict[str, Any]]:
        return self.query_pk(connector_pk(connector_id), sk_prefix="API#")

    def delete_connector_api(self, connector_id: str, api_id: str) -> bool:
        return self.delete_link(connector_pk(connector_id), connector_api_sk(api_id))

    # =======================================================================
    # Connector Settings (per-provider config, e.g. GDrive)
    # =======================================================================

    def put_connector_setting(self, provider: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=connector_setting_pk(provider),
            attrs=attrs,
            gsi1pk="CONNECTORSETTING",
            gsi1sk=provider,
        )

    def get_connector_setting(self, provider: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(connector_setting_pk(provider))

    def delete_connector_setting(self, provider: str) -> int:
        return self.delete_pk(connector_setting_pk(provider))

    # =======================================================================
    # VDL Entity CRUD (Virtual Data Layer — semantic-layer entity definitions)
    # =======================================================================

    def put_vdl_entity(self, name: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=vdl_entity_pk(name),
            attrs=attrs,
            gsi1pk="VDLENTITY",
            gsi1sk=name.lower(),
        )

    def get_vdl_entity(self, name: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(vdl_entity_pk(name))

    def list_vdl_entities(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("VDLENTITY")

    def delete_vdl_entity(self, name: str) -> int:
        # Cascade: also drops any MAPPING#... link rows under this VDL entity.
        return self.delete_pk(vdl_entity_pk(name))

    # =======================================================================
    # Mapping Rule CRUD (transactional 3-row writes: canonical + 2 links)
    # =======================================================================

    def put_mapping_rule(
        self,
        rule_id: str,
        source_dp_id: str,
        target_vdl_name: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Persist a mapping rule across 3 rows atomically:
          - MAPPINGRULE#{rule_id} / META (canonical, queryable via GSI1)
          - DATAPLANE#{source_dp_id} / MAPPING#{rule_id} (lookup by source)
          - VDLENTITY#{target_vdl_name} / MAPPING#{rule_id} (lookup by target)
        Full attrs are stored on all three rows (denormalized) so PK-direct
        list-by-source / list-by-target queries return full objects without a
        second hop.
        """
        full_attrs: Dict[str, Any] = {
            **attrs,
            "ruleId": rule_id,
            "sourceDataPlaneId": source_dp_id,
            "targetVdlEntity": target_vdl_name,
        }
        canonical_item = {
            "PK": mapping_rule_pk(rule_id),
            "SK": self.META_SK,
            "GSI1PK": "MAPPINGRULE",
            "GSI1SK": f"{source_dp_id}#{target_vdl_name}",
            **full_attrs,
        }
        source_link_item = {
            "PK": data_plane_pk(source_dp_id),
            "SK": mapping_link_sk(rule_id),
            **full_attrs,
        }
        target_link_item = {
            "PK": vdl_entity_pk(target_vdl_name),
            "SK": mapping_link_sk(rule_id),
            **full_attrs,
        }

        ops = [
            {"Put": {"TableName": self._table_name,
                     "Item": {k: self._to_attr(v) for k, v in canonical_item.items() if v is not None}}},
            {"Put": {"TableName": self._table_name,
                     "Item": {k: self._to_attr(v) for k, v in source_link_item.items() if v is not None}}},
            {"Put": {"TableName": self._table_name,
                     "Item": {k: self._to_attr(v) for k, v in target_link_item.items() if v is not None}}},
        ]
        try:
            self._transact_write_items(ops)
            return canonical_item
        except ClientError as e:
            reasons = e.response.get("CancellationReasons") if hasattr(e, "response") else None
            logger.error(f"put_mapping_rule({rule_id}) failed: {e} | reasons={reasons}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def get_mapping_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(mapping_rule_pk(rule_id))

    def list_mapping_rules(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("MAPPINGRULE")

    def list_mapping_rules_by_source(self, source_dp_id: str) -> List[Dict[str, Any]]:
        return self.query_pk(data_plane_pk(source_dp_id), sk_prefix="MAPPING#")

    def list_mapping_rules_by_target(self, target_vdl_name: str) -> List[Dict[str, Any]]:
        return self.query_pk(vdl_entity_pk(target_vdl_name), sk_prefix="MAPPING#")

    def delete_mapping_rule(self, rule_id: str) -> bool:
        """
        Atomically delete all 3 rows of a mapping rule. Requires reading the
        canonical row first to learn the source/target needed to locate the
        link rows.
        """
        canonical = self.get_meta(mapping_rule_pk(rule_id))
        if not canonical:
            return False
        source_dp_id = canonical.get("sourceDataPlaneId")
        target_vdl = canonical.get("targetVdlEntity")
        ops: List[Dict[str, Any]] = [
            {"Delete": {"TableName": self._table_name,
                        "Key": {"PK": {"S": mapping_rule_pk(rule_id)}, "SK": {"S": self.META_SK}}}}
        ]
        if source_dp_id:
            ops.append({"Delete": {"TableName": self._table_name,
                                   "Key": {"PK": {"S": data_plane_pk(source_dp_id)},
                                           "SK": {"S": mapping_link_sk(rule_id)}}}})
        if target_vdl:
            ops.append({"Delete": {"TableName": self._table_name,
                                   "Key": {"PK": {"S": vdl_entity_pk(target_vdl)},
                                           "SK": {"S": mapping_link_sk(rule_id)}}}})
        try:
            self._transact_write_items(ops)
            return True
        except ClientError as e:
            reasons = e.response.get("CancellationReasons") if hasattr(e, "response") else None
            logger.error(f"delete_mapping_rule({rule_id}) failed: {e} | reasons={reasons}")
            raise FoundryWorkspaceRepositoryError(str(e))

    # =======================================================================
    # Canonical Entity CRUD (Supply Chain Foundry — full payload, not just
    # the VDLENTITY name marker used by mapping rules)
    #
    # The pre-existing ``put_vdl_entity`` writes the same PK/SK/GSI pair but
    # carries only whatever ``attrs`` callers happen to pass. The methods
    # below wrap it with the canonical Foundry payload shape (aliases, domain,
    # semantic, risk_level, key_fields, relationships) so the bootstrap
    # script and the ``VdlCatalogService`` consume a stable dictionary.
    # =======================================================================

    def put_canonical_entity(self, name: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_vdl_entity(name=name, attrs=attrs)

    def get_canonical_entity(self, name: str) -> Optional[Dict[str, Any]]:
        return self.get_vdl_entity(name)

    def list_canonical_entities(self) -> List[Dict[str, Any]]:
        return self.list_vdl_entities()

    def delete_canonical_entity(self, name: str) -> int:
        return self.delete_vdl_entity(name)

    # =======================================================================
    # Policy / Workflow / Integration document CRUD
    #
    # Each row stores the original file content verbatim under ``contentText``
    # so the Knowledge Processor extractors can re-parse it without any
    # transformation loss. Structured fields (name, category, sourceFile,
    # contentType, sizeBytes, createdAt, updatedAt) ride alongside for listing
    # and filtering. Slugs are derived from filenames sans extension (e.g.
    # "credit-policy.md" -> slug "credit-policy") so PK/GSI lookups are
    # human-readable.
    # =======================================================================

    def put_policy(self, slug: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=policy_pk(slug),
            attrs=attrs,
            gsi1pk="POLICY",
            gsi1sk=slug.lower(),
        )

    def get_policy(self, slug: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(policy_pk(slug))

    def list_policies(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("POLICY")

    def delete_policy(self, slug: str) -> int:
        return self.delete_pk(policy_pk(slug))

    def put_workflow_def(self, slug: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=workflow_def_pk(slug),
            attrs=attrs,
            gsi1pk="WORKFLOWDEF",
            gsi1sk=slug.lower(),
        )

    def get_workflow_def(self, slug: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(workflow_def_pk(slug))

    def list_workflow_defs(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("WORKFLOWDEF")

    def delete_workflow_def(self, slug: str) -> int:
        return self.delete_pk(workflow_def_pk(slug))

    def put_integration_def(self, slug: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=integration_def_pk(slug),
            attrs=attrs,
            gsi1pk="INTEGRATIONDEF",
            gsi1sk=slug.lower(),
        )

    def get_integration_def(self, slug: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(integration_def_pk(slug))

    def list_integration_defs(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("INTEGRATIONDEF")

    def delete_integration_def(self, slug: str) -> int:
        return self.delete_pk(integration_def_pk(slug))

    # =======================================================================
    # Simulator Metadata (AI-OPs plane, Phase 1)
    #
    # Persists identity + per-table schema for each simulator so the spec's
    # requirement of "Simulator metadata in DynamoDB" is satisfied. Row data
    # itself continues to live in S3 + Redis.
    # =======================================================================

    def put_simulator_meta(self, service: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=simulator_pk(service),
            attrs=attrs,
            gsi1pk="SIM",
            gsi1sk=service.lower(),
        )

    def get_simulator_meta(self, service: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(simulator_pk(service))

    def list_simulators(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("SIM")

    def delete_simulator(self, service: str) -> int:
        return self.delete_pk(simulator_pk(service))

    def put_simulator_table(
        self,
        service: str,
        schema: str,
        table: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": simulator_pk(service),
            "SK": simulator_table_sk(schema, table),
            **attrs,
        }
        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"put_simulator_table({service},{schema}.{table}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def list_simulator_tables(self, service: str) -> List[Dict[str, Any]]:
        return self.query_pk(simulator_pk(service), sk_prefix="TABLE#")

    def delete_simulator_table(self, service: str, schema: str, table: str) -> bool:
        return self.delete_link(simulator_pk(service), simulator_table_sk(schema, table))

    # =======================================================================
    # Data Source Definitions (Data Plane, Phase 2)
    # =======================================================================

    def put_data_source(self, data_source_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        ds_type = str(attrs.get("type") or "").lower()
        name = str(attrs.get("name") or data_source_id).lower()
        return self.put_meta(
            pk=data_source_pk(data_source_id),
            attrs=attrs,
            gsi1pk="DATASOURCE",
            gsi1sk=f"{ds_type}#{name}",
        )

    def get_data_source(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(data_source_pk(data_source_id))

    def list_data_sources(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("DATASOURCE")

    def delete_data_source(self, data_source_id: str) -> int:
        return self.delete_pk(data_source_pk(data_source_id))

    # =======================================================================
    # Virtual Data API Registry (Data Plane, Phase 2)
    #
    # VDL APIs operate on virtual entities and are backed by one or more
    # Connector API implementations. Impl bindings can live inline on META
    # (default) or as separate ``IMPL#{implId}`` rows for large fan-outs.
    # =======================================================================

    def put_vdl_api(self, api_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        verb = str(attrs.get("verb") or "read").lower()
        entity = str(attrs.get("virtual_entity") or attrs.get("virtualEntity") or "").lower()
        return self.put_meta(
            pk=vdl_api_pk(api_id),
            attrs=attrs,
            gsi1pk="VDLAPI",
            gsi1sk=f"{verb}#{entity}",
        )

    def get_vdl_api(self, api_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(vdl_api_pk(api_id))

    def list_vdl_apis(
        self,
        virtual_entity: Optional[str] = None,
        verb: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = self.query_gsi1("VDLAPI")
        if verb:
            items = [i for i in items if str(i.get("verb", "")).lower() == verb.lower()]
        if virtual_entity:
            items = [
                i for i in items
                if str(i.get("virtual_entity", i.get("virtualEntity", ""))).lower() == virtual_entity.lower()
            ]
        return items

    def delete_vdl_api(self, api_id: str) -> int:
        return self.delete_pk(vdl_api_pk(api_id))

    def put_vdl_api_impl(
        self,
        api_id: str,
        impl_id: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": vdl_api_pk(api_id),
            "SK": vdl_api_impl_sk(impl_id),
            **attrs,
        }
        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"put_vdl_api_impl({api_id},{impl_id}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def list_vdl_api_impls(self, api_id: str) -> List[Dict[str, Any]]:
        return self.query_pk(vdl_api_pk(api_id), sk_prefix="IMPL#")

    # =======================================================================
    # Connector API Registry (Data Plane, Phase 2)
    #
    # Flat single-PK layout replaces the in-memory Python registry
    # ``_GLOBAL_CONNECTOR_APIS`` in ``src/services/control_plane/connector_apis.py``.
    # =======================================================================

    def put_conn_api(self, api_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        target = str(attrs.get("target_system") or attrs.get("targetSystem") or "").lower()
        return self.put_meta(
            pk=conn_api_pk(api_id),
            attrs=attrs,
            gsi1pk="CONNAPI",
            gsi1sk=f"{target}#{api_id.lower()}",
        )

    def get_conn_api(self, api_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(conn_api_pk(api_id))

    def list_conn_apis(self, target_system: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self.query_gsi1("CONNAPI")
        if target_system:
            wanted = target_system.lower()
            items = [
                i for i in items
                if str(i.get("target_system", i.get("targetSystem", ""))).lower() == wanted
            ]
        return items

    def delete_conn_api(self, api_id: str) -> int:
        # Cascade: also drops any AUDIT#... children under this API PK.
        return self.delete_pk(conn_api_pk(api_id))

    def put_conn_api_audit(
        self,
        api_id: str,
        iso_ts: str,
        event_id: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": conn_api_pk(api_id),
            "SK": conn_api_audit_sk(iso_ts, event_id),
            **attrs,
        }
        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"put_conn_api_audit({api_id}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def list_conn_api_audit(self, api_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = self._table.query(
                KeyConditionExpression=Key("PK").eq(conn_api_pk(api_id)) & Key("SK").begins_with("AUDIT#"),
                ScanIndexForward=False,
                Limit=limit,
            )
            return resp.get("Items", [])
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return []
            logger.error(f"list_conn_api_audit({api_id}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    # =======================================================================
    # Automation Registry (Workspace, Phase 3)
    #
    # Playbook YAMLs previously under ``enterprise-knowledge/automation/`` become
    # first-class DDB rows.
    # =======================================================================

    def put_automation(self, use_case_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        solution = str(attrs.get("solution") or "").lower()
        return self.put_meta(
            pk=automation_pk(use_case_id),
            attrs=attrs,
            gsi1pk="AUTOMATION",
            gsi1sk=f"{solution}#{use_case_id}",
        )

    def get_automation(self, use_case_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(automation_pk(use_case_id))

    def list_automations(self, solution: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self.query_gsi1("AUTOMATION")
        if solution:
            wanted = solution.lower()
            items = [i for i in items if str(i.get("solution", "")).lower() == wanted]
        return items

    def delete_automation(self, use_case_id: str) -> int:
        return self.delete_pk(automation_pk(use_case_id))

    # =======================================================================
    # Solution YAML Registry (Workspace, Phase 5)
    # =======================================================================

    def put_solution_yaml(self, solution_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=solution_yaml_pk(solution_id),
            attrs=attrs,
            gsi1pk="SOLUTIONYAML",
            gsi1sk=solution_id.lower(),
        )

    def get_solution_yaml(self, solution_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(solution_yaml_pk(solution_id))

    def list_solution_yamls(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("SOLUTIONYAML")

    def delete_solution_yaml(self, solution_id: str) -> int:
        return self.delete_pk(solution_yaml_pk(solution_id))

    # =======================================================================
    # Tools Registry (Reasoning, Phase 3.3)
    #
    # Catalog metadata for every ReAct tool. ``codeRef`` points either to
    # ``python://module.path.func`` for built-ins (source still in-repo) or
    # ``ddb://TOOL#{id}/VERSION#{n}/source_code`` for user-authored tools.
    # =======================================================================

    def put_tool_reg(self, tool_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        group = str(attrs.get("group") or "misc").lower()
        return self.put_meta(
            pk=tool_reg_pk(tool_id),
            attrs=attrs,
            gsi1pk="TOOLREG",
            gsi1sk=f"{group}#{tool_id.lower()}",
        )

    def get_tool_reg(self, tool_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(tool_reg_pk(tool_id))

    def list_tool_regs(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self.query_gsi1("TOOLREG")
        if group:
            wanted = group.lower()
            items = [i for i in items if str(i.get("group", "")).lower() == wanted]
        return items

    def delete_tool_reg(self, tool_id: str) -> int:
        return self.delete_pk(tool_reg_pk(tool_id))

    def put_tool_reg_impl(
        self,
        tool_id: str,
        lang: str,
        version: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": tool_reg_pk(tool_id),
            "SK": tool_reg_impl_sk(lang, version),
            **attrs,
        }
        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"put_tool_reg_impl({tool_id},{lang},{version}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def list_tool_reg_impls(self, tool_id: str) -> List[Dict[str, Any]]:
        return self.query_pk(tool_reg_pk(tool_id), sk_prefix="IMPL#")

    # =======================================================================
    # Knowledge Pipeline (Control, Phase 3.4)
    # =======================================================================

    def put_kp(self, pipeline_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return self.put_meta(
            pk=kp_pk(pipeline_id),
            attrs=attrs,
            gsi1pk="KP",
            gsi1sk=pipeline_id.lower(),
        )

    def get_kp(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        return self.get_meta(kp_pk(pipeline_id))

    def list_kps(self) -> List[Dict[str, Any]]:
        return self.query_gsi1("KP")

    def delete_kp(self, pipeline_id: str) -> int:
        return self.delete_pk(kp_pk(pipeline_id))

    def put_kp_run(
        self,
        pipeline_id: str,
        iso_ts: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": kp_pk(pipeline_id),
            "SK": kp_run_sk(iso_ts),
            **attrs,
        }
        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"put_kp_run({pipeline_id},{iso_ts}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))

    def list_kp_runs(self, pipeline_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = self._table.query(
                KeyConditionExpression=Key("PK").eq(kp_pk(pipeline_id)) & Key("SK").begins_with("RUN#"),
                ScanIndexForward=False,
                Limit=limit,
            )
            return resp.get("Items", [])
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return []
            logger.error(f"list_kp_runs({pipeline_id}) failed: {e}")
            raise FoundryWorkspaceRepositoryError(str(e))
