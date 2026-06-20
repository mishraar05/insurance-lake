"""Config-entity metadata schema (control-table models)."""
from .source import SourceConfig
from .target import TargetConfig
from .load import LoadConfig
from .transform import TransformConfig
from .dq_rule import DQRuleConfig
from .masking_rule import MaskingRuleConfig
from .recon_rule import ReconRuleConfig
from .dependency import DependencyConfig

# Ordered registry used by codegen (model -> control table)
MODELS = [
    SourceConfig, TargetConfig, LoadConfig, TransformConfig,
    DQRuleConfig, MaskingRuleConfig, ReconRuleConfig, DependencyConfig,
]

__all__ = [m.__name__ for m in MODELS] + ["MODELS"]
