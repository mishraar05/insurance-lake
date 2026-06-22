# src/core/contracts/reader.py
from __future__ import annotations
from typing import Protocol, runtime_checkable, TYPE_CHECKING
from core.metadata import SourceConfig, LoadConfig
if TYPE_CHECKING:
    from pyspark.sql import DataFrame


@runtime_checkable
class Reader(Protocol):
    def read(self, source: SourceConfig, load: LoadConfig) -> "DataFrame": ...
