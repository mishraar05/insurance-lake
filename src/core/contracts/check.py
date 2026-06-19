from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, TYPE_CHECKING
from core.metadata import DQRuleConfig
if TYPE_CHECKING:
    from pyspark.sql import DataFrame


@dataclass
class CheckResult:
    rule_id: str
    passed: bool
    failed_count: int
    action: str  # WARN | FAIL | QUARANTINE


@runtime_checkable
class Check(Protocol):
    """Evaluates a DQ rule against a DataFrame."""
    def evaluate(self, df: "DataFrame", rule: DQRuleConfig) -> CheckResult: ...
