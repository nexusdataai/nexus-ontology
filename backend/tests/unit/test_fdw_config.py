"""
Unit tests for FDW configuration module.

Tests FDWConfig dataclass, from_environment() loading, validation,
connection_url property, and module-level helpers.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
"""

import os
import pytest

from src.config.fdw_config import (
    FDWConfig,
    FDWConfigurationError,
    get_fdw_config,
    is_fdw_enabled,
    reset_fdw_config,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

FDW_ENV_VARS = [
    'FDW_PG_HOST', 'FDW_PG_PORT', 'FDW_PG_DATABASE', 'FDW_PG_USER',
    'FDW_PG_PASSWORD', 'FDW_PG_SCHEMA', 'FDW_PG_SSL_MODE',
    'FDW_PG_POOL_MIN', 'FDW_PG_POOL_MAX', 'FDW_PG_QUERY_TIMEOUT',
]


def _clear_fdw_env():
    """Remove all FDW-related environment variables."""
    for var in FDW_ENV_VARS:
        os.environ.pop(var, None)


def _set_valid_fdw_env(**overrides):
    """Set a complete valid FDW environment."""
    defaults = {
        'FDW_PG_HOST': 'db.example.com',
        'FDW_PG_DATABASE': 'fdw_db',
        'FDW_PG_USER': 'fdw_user',
        'FDW_PG_PASSWORD': 'secret123',
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        os.environ[k] = v


@pytest.fixture(autouse=True)
def clean_env():
    """Reset env and global config before/after each test."""
    _clear_fdw_env()
    reset_fdw_config()
    yield
    _clear_fdw_env()
    reset_fdw_config()


# ── Disabled state ───────────────────────────────────────────────────────────

class TestFDWDisabled:
    """Tests when FDW_PG_HOST is not set."""

    def test_disabled_when_host_not_set(self):
        """Validates: Requirement 1.2"""
        config = FDWConfig.from_environment()
        assert config.enabled is False

    def test_disabled_config_has_defaults(self):
        config = FDWConfig.from_environment()
        assert config.port == 5432
        assert config.schema == 'public'
        assert config.ssl_mode == 'prefer'
        assert config.pool_min == 2
        assert config.pool_max == 10
        assert config.query_timeout == 30

    def test_disabled_when_host_is_empty_string(self):
        os.environ['FDW_PG_HOST'] = '   '
        config = FDWConfig.from_environment()
        assert config.enabled is False


# ── Enabled state ────────────────────────────────────────────────────────────

class TestFDWEnabled:
    """Tests when FDW_PG_HOST is set with valid params."""

    def test_enabled_with_required_params(self):
        """Validates: Requirement 1.1"""
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        assert config.enabled is True
        assert config.host == 'db.example.com'
        assert config.database == 'fdw_db'
        assert config.user == 'fdw_user'
        assert config.password == 'secret123'

    def test_default_port(self):
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        assert config.port == 5432

    def test_custom_port(self):
        _set_valid_fdw_env(FDW_PG_PORT='5433')
        config = FDWConfig.from_environment()
        assert config.port == 5433

    def test_invalid_port_falls_back_to_default(self):
        _set_valid_fdw_env(FDW_PG_PORT='not_a_number')
        config = FDWConfig.from_environment()
        assert config.port == 5432

    def test_default_schema(self):
        """Validates: Requirement 1.3"""
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        assert config.schema == 'public'

    def test_custom_schema(self):
        _set_valid_fdw_env(FDW_PG_SCHEMA='fdw_schema')
        config = FDWConfig.from_environment()
        assert config.schema == 'fdw_schema'

    def test_default_ssl_mode(self):
        """Validates: Requirement 1.4"""
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        assert config.ssl_mode == 'prefer'

    def test_custom_ssl_mode(self):
        _set_valid_fdw_env(FDW_PG_SSL_MODE='require')
        config = FDWConfig.from_environment()
        assert config.ssl_mode == 'require'

    def test_pool_defaults(self):
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        assert config.pool_min == 2
        assert config.pool_max == 10

    def test_custom_pool_sizes(self):
        _set_valid_fdw_env(FDW_PG_POOL_MIN='5', FDW_PG_POOL_MAX='20')
        config = FDWConfig.from_environment()
        assert config.pool_min == 5
        assert config.pool_max == 20

    def test_invalid_pool_sizes_fall_back(self):
        _set_valid_fdw_env(FDW_PG_POOL_MIN='bad', FDW_PG_POOL_MAX='bad')
        config = FDWConfig.from_environment()
        assert config.pool_min == 2
        assert config.pool_max == 10

    def test_default_query_timeout(self):
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        assert config.query_timeout == 30

    def test_custom_query_timeout(self):
        _set_valid_fdw_env(FDW_PG_QUERY_TIMEOUT='60')
        config = FDWConfig.from_environment()
        assert config.query_timeout == 60


# ── Validation ───────────────────────────────────────────────────────────────

class TestFDWValidation:
    """Tests for missing required params when FDW_PG_HOST is set."""

    def test_missing_all_required_params(self):
        """Validates: Requirements 1.5, 1.6"""
        os.environ['FDW_PG_HOST'] = 'db.example.com'
        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()
        assert 'FDW_PG_DATABASE' in exc_info.value.missing_params
        assert 'FDW_PG_USER' in exc_info.value.missing_params
        assert 'FDW_PG_PASSWORD' in exc_info.value.missing_params

    def test_missing_database_only(self):
        os.environ['FDW_PG_HOST'] = 'db.example.com'
        os.environ['FDW_PG_USER'] = 'user'
        os.environ['FDW_PG_PASSWORD'] = 'pass'
        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()
        assert exc_info.value.missing_params == ['FDW_PG_DATABASE']

    def test_missing_user_only(self):
        os.environ['FDW_PG_HOST'] = 'db.example.com'
        os.environ['FDW_PG_DATABASE'] = 'mydb'
        os.environ['FDW_PG_PASSWORD'] = 'pass'
        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()
        assert exc_info.value.missing_params == ['FDW_PG_USER']

    def test_missing_password_only(self):
        os.environ['FDW_PG_HOST'] = 'db.example.com'
        os.environ['FDW_PG_DATABASE'] = 'mydb'
        os.environ['FDW_PG_USER'] = 'user'
        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()
        assert exc_info.value.missing_params == ['FDW_PG_PASSWORD']

    def test_missing_database_and_user(self):
        os.environ['FDW_PG_HOST'] = 'db.example.com'
        os.environ['FDW_PG_PASSWORD'] = 'pass'
        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()
        assert set(exc_info.value.missing_params) == {'FDW_PG_DATABASE', 'FDW_PG_USER'}

    def test_error_message_lists_missing_params(self):
        os.environ['FDW_PG_HOST'] = 'db.example.com'
        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()
        msg = str(exc_info.value)
        assert 'FDW_PG_DATABASE' in msg
        assert 'FDW_PG_USER' in msg
        assert 'FDW_PG_PASSWORD' in msg


# ── connection_url property ──────────────────────────────────────────────────

class TestConnectionURL:
    """Tests for the connection_url property."""

    def test_connection_url_format(self):
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        expected = 'postgresql+psycopg2://fdw_user:secret123@db.example.com:5432/fdw_db'
        assert config.connection_url == expected

    def test_connection_url_with_custom_port(self):
        _set_valid_fdw_env(FDW_PG_PORT='5433')
        config = FDWConfig.from_environment()
        assert ':5433/' in config.connection_url


# ── Module-level helpers ─────────────────────────────────────────────────────

class TestModuleHelpers:
    """Tests for get_fdw_config(), is_fdw_enabled(), reset_fdw_config()."""

    def test_get_fdw_config_returns_singleton(self):
        config1 = get_fdw_config()
        config2 = get_fdw_config()
        assert config1 is config2

    def test_reset_clears_singleton(self):
        config1 = get_fdw_config()
        reset_fdw_config()
        config2 = get_fdw_config()
        assert config1 is not config2

    def test_is_fdw_enabled_false_when_disabled(self):
        assert is_fdw_enabled() is False

    def test_is_fdw_enabled_true_when_enabled(self):
        _set_valid_fdw_env()
        reset_fdw_config()
        assert is_fdw_enabled() is True


# ── __repr__ ─────────────────────────────────────────────────────────────────

class TestRepr:
    """Tests for __repr__ (password exclusion)."""

    def test_repr_disabled(self):
        config = FDWConfig.from_environment()
        assert repr(config) == 'FDWConfig(enabled=False)'

    def test_repr_enabled_excludes_password(self):
        _set_valid_fdw_env()
        config = FDWConfig.from_environment()
        r = repr(config)
        assert 'secret123' not in r
        assert 'db.example.com' in r
        assert 'fdw_db' in r
