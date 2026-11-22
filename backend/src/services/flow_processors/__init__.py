"""Python implementations of phase-1 NiFi processors."""

# Import modules so @register_processor runs
from src.services.flow_processors import (  # noqa: F401
    convert_record,
    evaluate_json_path,
    jolt_transform_json,
    merge_content,
    query_record,
    replace_text,
    route_on_attribute,
    split_json,
    update_attribute,
)