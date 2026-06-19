from __future__ import annotations
from typing import Protocol, runtime_checkable, TYPE_CHECKING
from core.metadata import TargetConfig, LoadConfig
if TYPE_CHECKING:
    from pyspark.sql import DataFrame


@runtime_checkable
class LoadStrategy(Protocol):
    """Persists a DataFrame to a target using a load pattern (append/scd2/merge/...)."""
    def apply(self, df: "DataFrame", target: TargetConfig, load: LoadConfig) -> None: ...
