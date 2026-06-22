# src/core/contracts/load_strategy.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, TYPE_CHECKING, Optional, Dict, Any
from core.metadata import TargetConfig, LoadConfig
if TYPE_CHECKING:
    from pyspark.sql import DataFrame


@dataclass
class WriteResult:
    num_output_rows: int              # rows the commit actually wrote (engines read this for balance)
    operation: str = "WRITE"          # WRITE | MERGE | OVERWRITE
    metrics: Dict[str, Any] = field(default_factory=dict)   # raw Delta operationMetrics


@runtime_checkable
class LoadStrategy(Protocol):
    def apply(self, df: "DataFrame", target: TargetConfig, load: LoadConfig,
              options: Optional[Dict[str, str]] = None) -> WriteResult: ...   # options from schema-evolution
