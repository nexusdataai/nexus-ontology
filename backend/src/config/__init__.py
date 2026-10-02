# Config package for Nexus Backend (Call Processing Capability)

from .config_provider import (
    ConfigProvider,
    get_config,
    reset_config,
    init_config,
    detect_environment,
    is_aws_environment,
    CAPABILITY_NAME,
    VALID_ENVIRONMENTS,
)

from .localstack_config import (
    LocalStackConfig,
    get_localstack_config,
    reset_localstack_config,
    is_localstack_enabled,
    is_running_on_ecs,
    is_aws_environment as is_real_aws,
    get_runtime_environment,
)

__all__ = [
    # ConfigProvider
    'ConfigProvider',
    'get_config',
    'reset_config',
    'init_config',
    'detect_environment',
    'is_aws_environment',
    'CAPABILITY_NAME',
    'VALID_ENVIRONMENTS',
    # LocalStack
    'LocalStackConfig',
    'get_localstack_config',
    'reset_localstack_config',
    'is_localstack_enabled',
    'is_running_on_ecs',
    'is_real_aws',
    'get_runtime_environment',
]
