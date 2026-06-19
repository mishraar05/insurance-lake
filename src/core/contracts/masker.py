from __future__ import annotations
from typing import Protocol, runtime_checkable, TYPE_CHECKING, List
from core.metadata import MaskingRuleConfig
if TYPE_CHECKING:
    from pyspark.sql import DataFrame


@runtime_checkable
class Masker(Protocol):
    """Applies masking techniques to columns of a DataFrame per masking rules."""
    def mask(self, df: "DataFrame", rules: List[MaskingRuleConfig]) -> "DataFrame": ...
