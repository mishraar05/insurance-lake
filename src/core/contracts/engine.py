# src/core/contracts/engine.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Optional, Dict, Any


@dataclass
class RunContext:
    component: str
    entity: str
    run_type: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class RunResult:
    status: str                       # SUCCESS | FAILED
    metrics: Dict[str, Any] = field(default_factory=dict)
    run_id: Optional[str] = None


@runtime_checkable
class Engine(Protocol):
    def run(self, context: RunContext) -> RunResult: ...
