"""
InsureLake SDK - Configuration Loader and Metadata Framework.

Main package for loading and validating InsureLake P&C framework configuration.

Usage:
    from insurelake_sdk import ConfigLoader
    
    loader = ConfigLoader(catalog="insurelake_config", schema="config")
    load_config = loader.get_load("load_policy_batch")
    source = loader.get_source(load_config.source_id)
    dq_rules = loader.get_dq_rules_by_target(load_config.target_id)
"""

from .config_loader import ConfigLoader
from .models import (
    SourceConfig,
    TargetConfig,
    LoadConfig,
    TransformConfig,
    DQRuleConfig,
)
from .exceptions import (
    InsureLakeSDKError,
    ConfigNotFoundError,
    ConfigValidationError,
    ForeignKeyError,
    CircularDependencyError,
    InvalidConfigError,
    CatalogConnectionError,
)

__version__ = "0.1.0"

__all__ = [
    "ConfigLoader",
    "SourceConfig",
    "TargetConfig",
    "LoadConfig",
    "TransformConfig",
    "DQRuleConfig",
    "InsureLakeSDKError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "ForeignKeyError",
    "CircularDependencyError",
    "InvalidConfigError",
    "CatalogConnectionError",
]
