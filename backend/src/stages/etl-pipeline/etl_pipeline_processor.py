"""
ETL Pipeline Processor — Core Logic for Data Extraction, Transformation, and Loading

Supports FDW sources (via mapping rules) and external simulator sources
(social listening, file uploads, google drive).

Transform step integrates DocumentExtractionService for file_uploads/google_drive
and NLP enrichment for social_listening.
"""

import os
import time
from typing import Any, Dict, List, Optional


SOURCE_TABLES: Dict[str, List[str]] = {
    'social_listening': ['Market_Signal', 'Brand_Sentiment', 'Competitor_Alert'],
    'file_uploads': ['Invoice_Upload', 'Lab_Report_Upload'],
    'google_drive': ['Contract_Document', 'Sustainability_Report'],
}

TABLE_DOC_TYPE_MAP: Dict[str, str] = {
    'Invoice_Upload': 'invoice',
    'Lab_Report_Upload': 'lab_report',
    'Contract_Document': 'contract',
    'Sustainability_Report': 'sustainability_report',
}

EXTRACTION_CONFIDENCE_THRESHOLD = 70.0


class ETLPipelineConfig:
    def __init__(self, mapping_rule_id: str = "", source_type: str = "generic",
                 source_query: str = "", batch_size: int = 1000,
                 mode: str = "full", schedule: str = ""):
        self.mapping_rule_id = mapping_rule_id
        self.source_type = source_type
        self.source_query = source_query
        self.batch_size = batch_size
        self.mode = mode
        self.schedule = schedule

    @classmethod
    def from_dict(cls, d: dict) -> "ETLPipelineConfig":
        return cls(
            mapping_rule_id=d.get("mapping_rule_id", d.get("mappingRuleId", "")),
            source_type=d.get("source_type", d.get("sourceType", "generic")),
            source_query=d.get("source_query", d.get("sourceQuery", "")),
            batch_size=d.get("batch_size", d.get("batchSize", 1000)),
            mode=d.get("mode", "full"),
            schedule=d.get("schedule", ""),
        )


class ETLPipelineProcessor:

    def __init__(self, config: dict = None, log_callback=None):
        self._log = log_callback
        self.config = ETLPipelineConfig.from_dict(config or {})
        self.extracted_data: List[Dict] = []
        self.transformed_data: List[Dict] = []
        self.mapping_rule = None
        self.field_map: Dict[str, str] = {}
        self._current_step_id: Optional[str] = None
        # Domain KPI dict surfaced to BaseStage.effective_kpis() and
        # persisted on the JobExecution row's Data.kpis by complete_job.
        # Populated incrementally by each step's natural return values
        # (extract -> rows_extracted, transform -> rows_transformed,
        # load -> rows_loaded, verify -> data_quality + null_fields).
        self._kpis: Dict[str, Any] = {}

    def _info(self, msg: str):
        if self._log:
            self._log.log_info(msg, self._current_step_id)

    def _warn(self, msg: str):
        if self._log:
            self._log.log_warning(msg, self._current_step_id)

    def _is_external_source(self) -> bool:
        return self.config.source_type in SOURCE_TABLES

    def _extract_from_gdrive_connector(self) -> List[Dict]:
        """Try extracting from real Google Drive via connector; returns empty if not configured."""
        try:
            from src.services.gdrive_connector_service import get_gdrive_connector_service
            import asyncio

            svc = get_gdrive_connector_service()
            settings = svc._get_settings()
            if not settings.oauth2_config or not settings.oauth2_config.client_id:
                return []

            self._info("Google Drive connector configured — extracting from real Drive API")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                files, _ = loop.run_until_complete(svc.list_files(page_size=self.config.batch_size))
            finally:
                loop.close()

            if not files:
                self._info("No files found in Google Drive folders")
                return []

            rows: List[Dict] = []
            for f in files:
                mime = f.get('mime_type', '')
                if 'contract' in f.get('name', '').lower() or 'agreement' in f.get('name', '').lower():
                    source_table = 'Contract_Document'
                elif 'sustainab' in f.get('name', '').lower() or 'esg' in f.get('name', '').lower():
                    source_table = 'Sustainability_Report'
                else:
                    source_table = 'Contract_Document'

                rows.append({
                    '_source_table': source_table,
                    '_gdrive_file_id': f.get('file_id', ''),
                    'Document_Path': f'/gdrive/{f.get("name", "")}',
                    'File_Name': f.get('name', ''),
                    'File_Size': f.get('size_bytes', 0),
                    'Mime_Type': mime,
                    'Modified_Time': f.get('modified_time', ''),
                })

            self._info(f"Google Drive extraction: {len(rows)} files discovered")
            return rows
        except Exception as e:
            self._warn(f"Google Drive connector extraction failed: {e}")
            return []

    def _extract_from_s3_uploads(self) -> List[Dict]:
        """Check S3 for new file uploads that haven't been processed yet."""
        s3_bucket = os.getenv("EXTERNAL_SIMULATOR_BUCKET", "")
        s3_prefix = os.getenv("EXTERNAL_SIMULATOR_PREFIX", "external-sources")
        if not s3_bucket:
            return []

        try:
            import boto3
            s3 = boto3.client("s3")
            rows: List[Dict] = []

            for folder, table in [("uploads/invoices", "Invoice_Upload"), ("uploads/lab_reports", "Lab_Report_Upload")]:
                prefix = f"{s3_prefix}/{folder}/" if s3_prefix else f"{folder}/"
                try:
                    resp = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix, MaxKeys=self.config.batch_size)
                    for obj in resp.get('Contents', []):
                        key = obj['Key']
                        filename = key.split('/')[-1]
                        if not filename:
                            continue
                        rows.append({
                            '_source_table': table,
                            '_s3_key': key,
                            'File_Path': f"/{folder}/{filename}",
                            'File_Name': filename,
                            'File_Size': obj.get('Size', 0),
                        })
                except Exception as e:
                    self._warn(f"S3 listing failed for {folder}: {e}")

            if rows:
                self._info(f"S3 upload scan: {len(rows)} files discovered")
            return rows
        except ImportError:
            return []
        except Exception as e:
            self._warn(f"S3 upload extraction failed: {e}")
            return []

    def _extract_from_external(self) -> List[Dict]:
        """Extract data from real connectors first, falling back to simulator."""
        if self.config.source_type == 'google_drive':
            gdrive_rows = self._extract_from_gdrive_connector()
            if gdrive_rows:
                return gdrive_rows

        if self.config.source_type == 'file_uploads':
            s3_rows = self._extract_from_s3_uploads()
            if s3_rows:
                return s3_rows

        tables = SOURCE_TABLES.get(self.config.source_type, [])
        if not tables:
            self._warn(f"No tables defined for source type: {self.config.source_type}")
            return []

        try:
            from src.apis.fdw_api import _simulators
            from src.models.fdw_models import QueryRequest
            import asyncio
            import inspect

            sim = _simulators.get("external")
            if not sim:
                self._warn("External simulator not registered")
                return []
            if hasattr(sim, "ensure_loaded"):
                try:
                    loop_probe = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop_probe)
                    try:
                        loop_probe.run_until_complete(sim.ensure_loaded())
                    finally:
                        loop_probe.close()
                except Exception as exc:
                    self._warn(f"External simulator health check failed: {exc}")

            all_rows: List[Dict] = []
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for table in tables:
                    self._info(f"Querying external_sources.{table} (limit={self.config.batch_size})")
                    try:
                        req = QueryRequest(
                            table=table,
                            schema_name="external_sources",
                            columns=[],
                            limit=self.config.batch_size,
                        )
                        result = sim.execute_query(req)
                        if inspect.isawaitable(result):
                            result = loop.run_until_complete(result)
                        rows = result.rows if hasattr(result, 'rows') else (result.get('rows', []) if isinstance(result, dict) else [])
                        self._info(f"  {table}: {len(rows)} rows extracted")
                        for row in rows:
                            row['_source_table'] = table
                        all_rows.extend(rows)
                    except Exception as e:
                        self._warn(f"  Failed to query {table}: {e}")
            finally:
                loop.close()

            return all_rows

        except Exception as e:
            self._warn(f"External extraction failed: {e}")
            return []

    def _extract_from_fdw(self) -> List[Dict]:
        """Extract data from FDW using a mapping rule."""
        if not self.config.mapping_rule_id:
            self._info("No mapping rule specified, skipping FDW extraction")
            return []

        try:
            from src.services.mapping_rule_service import MappingRuleService
            import asyncio

            service = MappingRuleService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(service.initialize())
                self.mapping_rule = loop.run_until_complete(service.get(self.config.mapping_rule_id))
            finally:
                loop.close()

            rule = self.mapping_rule
            self.field_map = {fm.source_field: fm.target_field for fm in rule.field_maps}
            self._info(f"Loaded mapping rule: {rule.name} with {len(rule.field_maps)} field maps")

            if rule.source_type.value == "FDW":
                self._info(f"Extracting from FDW: {rule.source_schema}.{rule.source_table}")
                try:
                    from src.services.fdw_connection_manager import PostgreSQLConnectionManager
                    from src.services.fdw_discovery_service import FDWDiscoveryService
                    from src.services.fdw_query_service import FDWQueryService
                    from src.config.fdw_config import FDWConfig
                    from src.models.fdw_models import QueryRequest

                    config = FDWConfig.from_environment()
                    conn_mgr = PostgreSQLConnectionManager(config)
                    loop2 = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop2)
                    try:
                        loop2.run_until_complete(conn_mgr.initialize())
                        discovery = FDWDiscoveryService(conn_mgr)
                        query_svc = FDWQueryService(conn_mgr, discovery)

                        source_cols = [fm.source_field for fm in rule.field_maps]
                        query_req = QueryRequest(
                            table=rule.source_table,
                            schema_name=rule.source_schema,
                            columns=source_cols,
                            limit=self.config.batch_size,
                        )
                        result = loop2.run_until_complete(query_svc.execute_query(query_req))
                        return result.rows
                    finally:
                        loop2.close()
                except Exception as e:
                    self._warn(f"FDW extraction failed: {e}")
                    return []
            else:
                self._info(f"Source type {rule.source_type.value} — using simulator fallback")
                return self._extract_from_simulator_via_rule()

        except Exception as e:
            self._warn(f"Mapping rule extraction failed: {e}")
            return []

    def _extract_from_simulator_via_rule(self) -> List[Dict]:
        """Fallback: query the simulator using the mapping rule's source table."""
        if not self.mapping_rule:
            return []
        try:
            from src.apis.fdw_api import _simulators
            from src.models.fdw_models import QueryRequest

            schema = self.mapping_rule.source_schema
            table = self.mapping_rule.source_table
            schema_to_sim = {
                "oracle_erp": "oracle",
                "sap_s4hana": "sap",
                "sfdc_itxp2dev": "simulator",
                "external_sources": "external",
            }
            sim_key = schema_to_sim.get(schema, "simulator")
            sim = _simulators.get(sim_key)
            if not sim or not getattr(sim, "loaded", False):
                self._warn(f"Simulator '{sim_key}' not loaded for {schema}.{table}")
                return []

            source_cols = [fm.source_field for fm in self.mapping_rule.field_maps]
            req = QueryRequest(table=table, schema_name=schema, columns=source_cols, limit=self.config.batch_size)
            result = sim.execute_query(req)
            rows = result.rows if hasattr(result, 'rows') else (result.get('rows', []) if isinstance(result, dict) else [])
            self._info(f"Simulator extraction: {len(rows)} rows from {schema}.{table}")
            return rows
        except Exception as e:
            self._warn(f"Simulator extraction failed: {e}")
            return []

    def step_extract(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        self._info(f"ETL Extract — source_type={self.config.source_type}, mapping_rule={self.config.mapping_rule_id or '(auto)'}")

        if self._is_external_source():
            self.extracted_data = self._extract_from_external()
        elif self.config.mapping_rule_id:
            self.extracted_data = self._extract_from_fdw()
        else:
            self._info("No source type or mapping rule — nothing to extract")
            self.extracted_data = []

        elapsed = round(time.time() - start, 2)
        self._info(f"Extraction complete: {len(self.extracted_data)} rows in {elapsed}s")
        self._kpis["rows_extracted"] = len(self.extracted_data)
        return {
            "status": "completed",
            "rows_extracted": len(self.extracted_data),
            "elapsed_seconds": elapsed,
        }

    def step_validate_schema(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.extracted_data:
            self._kpis.update({"valid_rows": 0, "invalid_rows": 0})
            return {"status": "completed", "message": "No data to validate", "valid_rows": 0, "invalid_rows": 0}

        if self.field_map:
            source_fields = set(self.field_map.keys())
            valid = sum(1 for row in self.extracted_data if source_fields.issubset(set(row.keys())))
            invalid = len(self.extracted_data) - valid
        else:
            valid = len(self.extracted_data)
            invalid = 0

        self._info(f"Schema validation: {valid} valid, {invalid} invalid out of {len(self.extracted_data)} rows")
        self._kpis.update({"valid_rows": valid, "invalid_rows": invalid})
        return {"status": "completed", "valid_rows": valid, "invalid_rows": invalid}

    def _transform_with_extraction(self, rows: List[Dict]) -> List[Dict]:
        """Run DocumentExtractionService on rows that lack extraction or have low confidence."""
        try:
            from src.services.document_extraction_service import DocumentExtractionService
        except ImportError:
            self._warn("DocumentExtractionService not available, skipping extraction transform")
            return rows

        extractor = DocumentExtractionService()
        s3_bucket = os.getenv("EXTERNAL_SIMULATOR_BUCKET", "")
        s3_prefix = os.getenv("EXTERNAL_SIMULATOR_PREFIX", "external-sources")
        result = []
        extracted_count = 0

        for row in rows:
            source_table = row.get('_source_table', '')
            doc_type = TABLE_DOC_TYPE_MAP.get(source_table)
            if not doc_type:
                result.append(row)
                continue

            confidence = row.get('Extraction_Confidence')
            if confidence is not None and float(confidence) >= EXTRACTION_CONFIDENCE_THRESHOLD:
                result.append(row)
                continue

            file_path = row.get('File_Path') or row.get('Document_Path') or ''
            if not file_path:
                result.append(row)
                continue

            content = b''
            s3_key = ''
            if s3_bucket and file_path:
                s3_key = f"{s3_prefix}{file_path}" if s3_prefix else file_path.lstrip('/')
                try:
                    import boto3
                    s3 = boto3.client("s3")
                    obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
                    content = obj["Body"].read()
                except Exception as e:
                    self._warn(f"S3 fetch failed for {s3_key}: {e}")

            if not content:
                result.append(row)
                continue

            filename = file_path.split('/')[-1] if '/' in file_path else file_path
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    fields = loop.run_until_complete(
                        extractor.extract_document(content, filename, doc_type, s3_bucket, s3_key)
                    )
                finally:
                    loop.close()

                fields.pop("_raw_text", None)
                fields.pop("_extraction_status", None)
                merged = {**row, **fields}
                result.append(merged)
                extracted_count += 1
                self._info(f"Extracted {filename}: confidence={fields.get('Extraction_Confidence', 0)}%")
            except Exception as e:
                self._warn(f"Extraction failed for {filename}: {e}")
                result.append(row)

        if extracted_count:
            self._info(f"Document extraction enriched {extracted_count}/{len(rows)} rows")
        return result

    def _transform_social_listening(self, rows: List[Dict]) -> List[Dict]:
        """Apply NLP enrichment to social listening rows."""
        try:
            from src.services.social_listening_enrichment_service import SocialListeningEnrichmentService
            enricher = SocialListeningEnrichmentService()
        except ImportError:
            self._warn("SocialListeningEnrichmentService not available, skipping NLP enrichment")
            return rows

        enriched = enricher.enrich_batch(rows)
        enriched_count = sum(1 for r in enriched if r.get('_enriched'))
        if enriched_count:
            self._info(f"NLP enrichment applied to {enriched_count}/{len(rows)} rows")
        return enriched

    def step_transform(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        if not self.extracted_data:
            return {"status": "completed", "message": "No data to transform", "rows_transformed": 0}

        if self.field_map and self.mapping_rule:
            transforms = {}
            for fm in self.mapping_rule.field_maps:
                if fm.transform:
                    transforms[fm.source_field] = fm.transform

            self.transformed_data = []
            for row in self.extracted_data:
                new_row = {}
                for src_field, tgt_field in self.field_map.items():
                    value = row.get(src_field)
                    transform = transforms.get(src_field)
                    if transform and value is not None:
                        if transform == "upper" and isinstance(value, str):
                            value = value.upper()
                        elif transform == "lower" and isinstance(value, str):
                            value = value.lower()
                        elif transform == "trim" and isinstance(value, str):
                            value = value.strip()
                        elif transform == "string":
                            value = str(value)
                    new_row[tgt_field] = value
                self.transformed_data.append(new_row)
        else:
            self.transformed_data = list(self.extracted_data)

        if self.config.source_type in ('file_uploads', 'google_drive'):
            self.transformed_data = self._transform_with_extraction(self.transformed_data)
        elif self.config.source_type == 'social_listening':
            self.transformed_data = self._transform_social_listening(self.transformed_data)

        elapsed = round(time.time() - start, 2)
        self._info(f"Transformed {len(self.transformed_data)} rows in {elapsed}s")
        self._kpis["rows_transformed"] = len(self.transformed_data)
        return {"status": "completed", "rows_transformed": len(self.transformed_data), "elapsed_seconds": elapsed}

    def _route_by_confidence(self, rows: List[Dict]) -> tuple:
        """Split rows into high-confidence (auto-load) and low-confidence (review queue)."""
        auto_load = []
        review_queue = []
        for row in rows:
            confidence = row.get('Extraction_Confidence')
            if confidence is not None:
                try:
                    conf_val = float(confidence)
                    if conf_val < EXTRACTION_CONFIDENCE_THRESHOLD:
                        row['_review_status'] = 'pending_review'
                        row['_review_reason'] = f'Low confidence: {conf_val}%'
                        review_queue.append(row)
                        continue
                except (ValueError, TypeError):
                    pass
            auto_load.append(row)
        return auto_load, review_queue

    def _persist_review_queue(self, review_rows: List[Dict]):
        """Persist low-confidence rows to the review queue in the external simulator."""
        if not review_rows:
            return
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if ext and getattr(ext, "loaded", False):
                key = ("external_sources", "ETL_Review_Queue")
                existing = ext._data.get(key, [])
                ext._data[key] = existing + review_rows
                self._info(f"Queued {len(review_rows)} low-confidence rows for human review")
            else:
                self._warn("Cannot persist review queue — external simulator not loaded")
        except Exception as e:
            self._warn(f"Review queue persistence failed: {e}")

    def step_load(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.transformed_data:
            return {"status": "completed", "message": "No data to load", "rows_loaded": 0}

        has_extraction = self.config.source_type in ('file_uploads', 'google_drive')
        auto_load_rows = self.transformed_data
        review_count = 0

        if has_extraction:
            auto_load_rows, review_rows = self._route_by_confidence(self.transformed_data)
            review_count = len(review_rows)
            if review_rows:
                self._persist_review_queue(review_rows)

        loaded = 0
        if self._is_external_source():
            try:
                from src.apis.fdw_api import _simulators
                ext = _simulators.get("external")
                if ext and getattr(ext, "loaded", False):
                    tables_data: Dict[str, List[Dict]] = {}
                    for row in auto_load_rows:
                        tbl = row.pop('_source_table', 'ETL_Output')
                        row.pop('_enriched', None)
                        row.pop('_review_status', None)
                        row.pop('_review_reason', None)
                        row.pop('_gdrive_file_id', None)
                        row.pop('_s3_key', None)
                        tables_data.setdefault(tbl, []).append(row)
                    for tbl, rows in tables_data.items():
                        key = ("external_sources", tbl)
                        existing = ext._data.get(key, [])
                        ext._data[key] = existing + rows
                        self._info(f"Loaded {len(rows)} rows to external_sources.{tbl}")
                        loaded += len(rows)
                else:
                    self._warn("External simulator not available for load")
            except Exception as e:
                self._warn(f"Load to external simulator failed: {e}")
        else:
            loaded = len(auto_load_rows)

        self._info(f"Load complete: {loaded} rows loaded, {review_count} sent to review queue")
        self._kpis["rows_loaded"] = loaded
        self._kpis["rows_queued_for_review"] = review_count
        return {
            "status": "completed",
            "rows_loaded": loaded,
            "rows_queued_for_review": review_count,
            "destination": "external_sources" if self._is_external_source() else "virtual_data_layer",
        }

    def step_verify(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        extracted = len(self.extracted_data)
        transformed = len(self.transformed_data)

        null_counts = {}
        for row in self.transformed_data:
            for k, v in row.items():
                if v is None:
                    null_counts[k] = null_counts.get(k, 0) + 1

        high_conf = sum(1 for r in self.transformed_data
                        if r.get('Extraction_Confidence') is not None
                        and float(r.get('Extraction_Confidence', 0)) >= EXTRACTION_CONFIDENCE_THRESHOLD)
        low_conf = sum(1 for r in self.transformed_data
                       if r.get('Extraction_Confidence') is not None
                       and float(r.get('Extraction_Confidence', 0)) < EXTRACTION_CONFIDENCE_THRESHOLD)

        quality = "pass" if extracted > 0 and extracted == transformed else ("warning" if extracted > 0 else "no_data")
        # ETL quality as a percentage so the schema's ``data_quality``
        # KPI (format=percent) has a numeric value to render rather
        # than the string label. Schema also surfaces the label via
        # ``data_quality_label`` for display.
        quality_pct = 100.0 if quality == "pass" else (50.0 if quality == "warning" else 0.0)
        # Total nulls across all fields (single int rather than a dict)
        # so it can be summed/averaged across jobs by the report
        # builder.
        null_fields_total = sum(null_counts.values()) if null_counts else 0
        self._info(f"Verification: {extracted} extracted, {transformed} transformed, quality={quality}")
        result = {
            "status": "completed",
            "rows_extracted": extracted,
            "rows_transformed": transformed,
            "rows_loaded": transformed - low_conf,
            "null_fields": null_counts,
            "data_quality": quality,
        }
        # Update the domain KPI dict so the journey-report builder can
        # surface these values. Schema sources from Data.kpis.*.
        self._kpis.update({
            "rows_extracted": extracted,
            "rows_transformed": transformed,
            "rows_loaded": transformed - low_conf,
            "null_fields": null_fields_total,
            "data_quality": quality_pct,
            "data_quality_label": quality,
        })
        if high_conf or low_conf:
            result["high_confidence_rows"] = high_conf
            result["low_confidence_rows"] = low_conf
            self._kpis["high_confidence_rows"] = high_conf
            self._kpis["low_confidence_rows"] = low_conf
        return result
