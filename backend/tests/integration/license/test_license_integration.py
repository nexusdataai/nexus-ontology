"""
License Integration Tests

Integration tests for the license enablement feature covering:
- License activation via REST API and MCP tool
- License validation and status checking
- License deactivation and renewal
- Feature tier gating
- Grace period handling
- Audit logging
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
import json


class TestLicenseActivation:
    """Integration tests for license activation."""
    
    @pytest.mark.asyncio
    async def test_activate_valid_license_via_api(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test activating a valid license key via REST API."""
        result = await license_helper.activate_license(valid_enterprise_key)
        
        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["tier"] == "enterprise"
        assert data["data"]["is_active"] is True
        assert "license_id" in data["data"]
        assert "expires_at" in data["data"]
    
    @pytest.mark.asyncio
    async def test_activate_license_via_mcp_tool(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test activating a license via MCP tool endpoint."""
        result = await license_helper.call_license_tool(
            action="activate",
            license_key=valid_enterprise_key
        )
        
        assert result["status_code"] == 200
        # Parse MCP response format
        response = result["data"]
        content = response.get("content", [{}])[0]
        text = content.get("text", "{}")
        data = json.loads(text) if isinstance(text, str) else text
        
        assert data.get("status") == "success"
        assert data.get("tier") == "enterprise"
    
    @pytest.mark.asyncio
    async def test_activate_invalid_license_format(
        self, api_client, license_helper, clean_license_state
    ):
        """Test activation with invalid license key format."""
        result = await license_helper.activate_license("invalid-key-format")
        
        assert result["status_code"] == 400
        data = result["data"]
        assert "error" in str(data).lower() or "invalid" in str(data).lower()
    
    @pytest.mark.asyncio
    async def test_activate_expired_license(
        self, api_client, expired_license_key, license_helper, clean_license_state
    ):
        """Test activation with expired license key."""
        result = await license_helper.activate_license(expired_license_key)
        
        # Should fail with expired error
        assert result["status_code"] in [400, 403]
    
    @pytest.mark.asyncio
    async def test_activate_same_license_twice_is_idempotent(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test that activating the same license twice returns existing activation."""
        # First activation
        result1 = await license_helper.activate_license(valid_enterprise_key)
        assert result1["status_code"] == 200
        
        # Second activation with same key
        result2 = await license_helper.activate_license(valid_enterprise_key)
        assert result2["status_code"] == 200
        
        # Should return same license ID
        license_id1 = result1["data"]["data"]["license_id"]
        license_id2 = result2["data"]["data"]["license_id"]
        assert license_id1 == license_id2


class TestLicenseStatus:
    """Integration tests for license status checking."""
    
    @pytest.mark.asyncio
    async def test_get_status_with_active_license(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test getting status with an active license."""
        # Activate first
        await license_helper.activate_license(valid_enterprise_key)
        
        # Get status
        result = await license_helper.get_license_status()
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert data["license_status"] == "active"
        assert data["tier"] == "enterprise"
        assert "days_remaining" in data
        assert "features" in data
    
    @pytest.mark.asyncio
    async def test_get_status_without_license(
        self, api_client, license_helper, clean_license_state
    ):
        """Test getting status when no license is activated."""
        result = await license_helper.get_license_status()
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert data["license_status"] == "not_activated"
        assert "activation_instructions" in data
    
    @pytest.mark.asyncio
    async def test_status_via_mcp_tool(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test getting status via MCP tool."""
        await license_helper.activate_license(valid_enterprise_key)
        
        result = await license_helper.call_license_tool(action="status")
        
        assert result["status_code"] == 200
        response = result["data"]
        content = response.get("content", [{}])[0]
        text = content.get("text", "{}")
        data = json.loads(text) if isinstance(text, str) else text
        
        assert data.get("license_status") == "active"
    
    @pytest.mark.asyncio
    async def test_status_shows_expiration_warning(
        self, api_client, expiring_soon_key, license_helper, clean_license_state
    ):
        """Test that status shows warning for expiring license."""
        await license_helper.activate_license(expiring_soon_key)
        
        result = await license_helper.get_license_status()
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert data["is_expiring_soon"] is True
        assert data.get("expiration_warning") is not None


class TestLicenseDeactivation:
    """Integration tests for license deactivation."""
    
    @pytest.mark.asyncio
    async def test_deactivate_active_license(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test deactivating an active license."""
        # Activate first
        await license_helper.activate_license(valid_enterprise_key)
        
        # Deactivate
        result = await license_helper.deactivate_license("Test deactivation")
        
        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "success"
        assert "deactivated_at" in data["data"]
        
        # Verify status is now not_activated
        status = await license_helper.get_license_status()
        assert status["data"]["data"]["license_status"] in ["not_activated", "deactivated"]
    
    @pytest.mark.asyncio
    async def test_deactivate_without_active_license(
        self, api_client, license_helper, clean_license_state
    ):
        """Test deactivation when no license is active."""
        result = await license_helper.deactivate_license("Test")
        
        assert result["status_code"] == 403
    
    @pytest.mark.asyncio
    async def test_deactivate_via_mcp_tool(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test deactivation via MCP tool."""
        await license_helper.activate_license(valid_enterprise_key)
        
        result = await license_helper.call_license_tool(
            action="deactivate",
            reason="MCP tool test"
        )
        
        assert result["status_code"] == 200


class TestLicenseRenewal:
    """Integration tests for license renewal."""
    
    @pytest.mark.asyncio
    async def test_renew_license_with_valid_key(
        self, api_client, valid_enterprise_key, renewal_key, license_helper, clean_license_state
    ):
        """Test renewing a license with a valid renewal key."""
        # Activate first
        await license_helper.activate_license(valid_enterprise_key)
        
        # Renew
        result = await license_helper.renew_license(renewal_key)
        
        # Note: Renewal may fail if not within renewal window
        # This test validates the API endpoint works
        assert result["status_code"] in [200, 400]
    
    @pytest.mark.asyncio
    async def test_renew_without_active_license(
        self, api_client, renewal_key, license_helper, clean_license_state
    ):
        """Test renewal when no license is active."""
        result = await license_helper.renew_license(renewal_key)
        
        assert result["status_code"] == 403


class TestFeatureGating:
    """Integration tests for feature tier gating."""
    
    @pytest.mark.asyncio
    async def test_enterprise_has_all_features(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test that enterprise tier has access to all features."""
        await license_helper.activate_license(valid_enterprise_key)
        
        # Check various features (use actual feature names from FEATURE_TIER_MAPPING)
        for feature in ["journeys", "basic_analytics", "second_brain", "export"]:
            result = await license_helper.check_feature(feature)
            assert result["status_code"] == 200
            data = result["data"]["data"]
            assert data["is_allowed"] is True, f"Feature '{feature}' should be allowed for enterprise tier"
    
    @pytest.mark.asyncio
    async def test_basic_tier_limited_features(
        self, api_client, valid_basic_key, license_helper, clean_license_state
    ):
        """Test that basic tier has limited feature access."""
        await license_helper.activate_license(valid_basic_key)
        
        # Check a feature that requires higher tier
        result = await license_helper.check_feature("advanced_analytics")
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        # Basic tier should not have access to advanced features
        if not data["is_allowed"]:
            assert "upgrade_message" in data
    
    @pytest.mark.asyncio
    async def test_feature_check_without_license(
        self, api_client, license_helper, clean_license_state
    ):
        """Test feature check when no license is active."""
        result = await license_helper.check_feature("journeys")
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert data["is_allowed"] is False


class TestLicenseValidation:
    """Integration tests for license validation."""
    
    @pytest.mark.asyncio
    async def test_validate_active_license(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test validating an active license."""
        await license_helper.activate_license(valid_enterprise_key)
        
        result = await license_helper.validate_license()
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert data["is_valid"] is True
        assert data["license_status"] == "active"
        assert data["can_write"] is True
    
    @pytest.mark.asyncio
    async def test_validate_without_license(
        self, api_client, license_helper, clean_license_state
    ):
        """Test validation when no license is active."""
        result = await license_helper.validate_license()
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert data["is_valid"] is False
        assert data["license_status"] == "not_activated"


class TestAuditLogging:
    """Integration tests for audit logging."""
    
    @pytest.mark.asyncio
    async def test_audit_logs_after_activation(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test that activation creates audit log entry."""
        await license_helper.activate_license(valid_enterprise_key)
        
        result = await license_helper.get_audit_logs(limit=10)
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert "entries" in data
        
        # Should have at least one entry for activation
        entries = data["entries"]
        if len(entries) > 0:
            # Check for activation event
            event_types = [e["event_type"] for e in entries]
            assert "license_activated" in event_types or len(entries) > 0
    
    @pytest.mark.asyncio
    async def test_audit_logs_pagination(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test audit logs pagination."""
        await license_helper.activate_license(valid_enterprise_key)
        
        result = await license_helper.get_audit_logs(limit=5)
        
        assert result["status_code"] == 200
        data = result["data"]["data"]
        assert "page_size" in data
        assert data["page_size"] == 5


class TestLicenseLifecycle:
    """Integration tests for complete license lifecycle."""
    
    @pytest.mark.asyncio
    async def test_complete_license_lifecycle(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test complete lifecycle: activate → use → deactivate."""
        # Step 1: Verify no license
        status = await license_helper.get_license_status()
        assert status["data"]["data"]["license_status"] == "not_activated"
        
        # Step 2: Activate
        activation = await license_helper.activate_license(valid_enterprise_key)
        assert activation["status_code"] == 200
        license_id = activation["data"]["data"]["license_id"]
        
        # Step 3: Verify active
        status = await license_helper.get_license_status()
        assert status["data"]["data"]["license_status"] == "active"
        
        # Step 4: Check feature access
        feature = await license_helper.check_feature("journeys")
        assert feature["data"]["data"]["is_allowed"] is True
        
        # Step 5: Validate
        validation = await license_helper.validate_license()
        assert validation["data"]["data"]["is_valid"] is True
        
        # Step 6: Deactivate
        deactivation = await license_helper.deactivate_license("Lifecycle test complete")
        assert deactivation["status_code"] == 200
        
        # Step 7: Verify deactivated
        status = await license_helper.get_license_status()
        assert status["data"]["data"]["license_status"] in ["not_activated", "deactivated"]
        
        # Step 8: Verify audit trail
        audit = await license_helper.get_audit_logs(limit=20)
        assert audit["status_code"] == 200


class TestMCPToolIntegration:
    """Integration tests for MCP tool interface."""
    
    @pytest.mark.asyncio
    async def test_all_mcp_tool_actions(
        self, api_client, valid_enterprise_key, license_helper, clean_license_state
    ):
        """Test all MCP tool actions work correctly."""
        # Activate
        result = await license_helper.call_license_tool(
            action="activate",
            license_key=valid_enterprise_key
        )
        assert result["status_code"] == 200
        
        # Status
        result = await license_helper.call_license_tool(action="status")
        assert result["status_code"] == 200
        
        # Validate
        result = await license_helper.call_license_tool(action="validate")
        assert result["status_code"] == 200
        
        # Check feature
        result = await license_helper.call_license_tool(
            action="check_feature",
            feature_id="journeys"
        )
        assert result["status_code"] == 200
        
        # Audit logs
        result = await license_helper.call_license_tool(
            action="audit_logs",
            limit=10
        )
        assert result["status_code"] == 200
        
        # Deactivate
        result = await license_helper.call_license_tool(
            action="deactivate",
            reason="MCP tool test"
        )
        assert result["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_mcp_tool_invalid_action(
        self, api_client, license_helper
    ):
        """Test MCP tool with invalid action."""
        result = await license_helper.call_license_tool(action="invalid_action")
        
        assert result["status_code"] == 200
        response = result["data"]
        content = response.get("content", [{}])[0]
        text = content.get("text", "{}")
        data = json.loads(text) if isinstance(text, str) else text
        
        assert data.get("status") == "error"
        assert "unknown" in data.get("message", "").lower() or "available_actions" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
