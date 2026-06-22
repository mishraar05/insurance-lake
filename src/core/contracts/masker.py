# src/core/contracts/masker.py
from __future__ import annotations
from typing import Protocol, runtime_checkable, TYPE_CHECKING, List
from core.metadata import MaskingRuleConfig
if TYPE_CHECKING:
    from pyspark.sql import DataFrame


@runtime_checkable
class Masker(Protocol):
    def mask(self, df: "DataFrame", rules: List[MaskingRuleConfig]) -> "DataFrame": ...
