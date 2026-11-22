# Flow processor parity matrix (117)

All processors in the Nexus catalog are registered with Python modules under `src/services/flow_processors/`.

| Level | Meaning |
|-------|---------|
| **full** | Dedicated module with behavior matching common NiFi use cases for preview runs |
| **partial** | Delegates to shared `handlers/builtin.py` with simplified Nexus semantics |
| **preview-only** | SQL/DB/JMS processors set `nexus.delegation` attributes; production uses journey stages |

Processors with dedicated implementations (20): UpdateAttribute, EvaluateJsonPath, JoltTransformJSON, ReplaceText, RouteOnAttribute, SplitJson, MergeContent, QueryRecord, ConvertRecord, AttributesToCSV, AttributesToJSON, CompressContent, ExtractText, SplitText, RouteText, CryptographicHashContent, CountText, ConvertCharacterSet, DeduplicateRecord, ValidateJson.

All other catalog processors use `dispatch()` handlers (partial or preview-only). Re-run `scripts/generate_flow_processor_ports.py` after harvest updates.