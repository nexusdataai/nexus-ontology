"""
Property-based tests for Data Plane Pydantic models.

Feature: ai-data-plane
Properties 9, 10

Tests DataPlaneResponse camelCase serialization and serialization round-trip
using hypothesis strategies to generate random valid model instances.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import datetime
from hypothesis import given, settings, HealthCheck, strategies as st
from hypothesis.strategies import composite
from src.models.data_plane_models import (
    DataPlaneResponse,
    DataPlaneStatus,
    DataPlaneType,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_nonempty_text = st.text(
    min_size=1,
    max_size=20,
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        blacklist_characters="\x00",
    ),
).filter(lambda s: s.strip() != "")

_data_plane_type_st = st.sampled_from(list(DataPlaneType))
_data_plane_status_st = st.sampled_from(list(DataPlaneStatus))

_iso_timestamp_st = st.datetimes(
    min_value=datetime.datetime(2000, 1, 1),
    max_value=datetime.datetime(2099, 12, 31),
).map(lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

_connection_config_value_st = st.one_of(
    _nonempty_text,
    st.integers(min_value=0, max_value=65535),
    st.booleans(),
)

_connection_config_st = st.dictionaries(
    keys=_nonempty_text,
    values=_connection_config_value_st,
    min_size=1,
    max_size=3,
)


@composite
def data_plane_response_st(draw):
    """Generate a random valid DataPlaneResponse instance."""
    return DataPlaneResponse(
        id=str(draw(st.uuids())),
        name=draw(_nonempty_text),
        type=draw(_data_plane_type_st),
        status=draw(_data_plane_status_st),
        connection_config=draw(_connection_config_st),
        created_at=draw(_iso_timestamp_st),
        updated_at=draw(_iso_timestamp_st),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_no_underscores(keys):
    """Check that none of the top-level keys contain underscores."""
    return all("_" not in k for k in keys)


# ---------------------------------------------------------------------------
# Property 9: DataPlaneResponse camelCase serialization
# ---------------------------------------------------------------------------


class TestDataPlaneResponseCamelCase:
    """
    Property 9: DataPlaneResponse camelCase serialization

    For any valid DataPlaneResponse object, serializing it to JSON should
    produce keys in camelCase format (connectionConfig, createdAt, updatedAt)
    rather than snake_case.
    """

    @given(instance=data_plane_response_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.data_too_large])
    def test_response_serializes_to_camel_case(self, instance):
        """
        Feature: ai-data-plane, Property 9: DataPlaneResponse camelCase serialization
        **Validates: Requirements 5.6, 2.8**
        """
        data = instance.model_dump(by_alias=True)
        assert _has_no_underscores(data.keys()), (
            f"Non-camelCase keys found: {[k for k in data.keys() if '_' in k]}"
        )
        # Verify the specific aliased keys are present
        assert "connectionConfig" in data
        assert "createdAt" in data
        assert "updatedAt" in data
        # Verify snake_case variants are absent
        assert "connection_config" not in data
        assert "created_at" not in data
        assert "updated_at" not in data


# ---------------------------------------------------------------------------
# Property 10: DataPlaneResponse serialization round-trip
# ---------------------------------------------------------------------------


class TestDataPlaneResponseRoundTrip:
    """
    Property 10: DataPlaneResponse serialization round-trip

    For any valid DataPlaneResponse object, serializing to JSON
    (via .model_dump(by_alias=True)) and then deserializing back
    (via DataPlaneResponse(**json_data)) should produce an equivalent object.
    """

    @given(instance=data_plane_response_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.data_too_large])
    def test_response_round_trip(self, instance):
        """
        Feature: ai-data-plane, Property 10: DataPlaneResponse serialization round-trip
        **Validates: Requirements 5.7**
        """
        data = instance.model_dump(by_alias=True)
        restored = DataPlaneResponse(**data)

        assert restored.id == instance.id
        assert restored.name == instance.name
        assert restored.type == instance.type
        assert restored.status == instance.status
        assert restored.connection_config == instance.connection_config
        assert restored.created_at == instance.created_at
        assert restored.updated_at == instance.updated_at
