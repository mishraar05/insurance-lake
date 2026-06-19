"""Typed interfaces (Protocols) the layers implement."""
from .reader import Reader
from .load_strategy import LoadStrategy
from .engine import Engine, RunContext, RunResult
from .check import Check, CheckResult
from .masker import Masker

__version__ = "0.1.0"

__all__ = [
    "Reader", "LoadStrategy", "Engine", "RunContext", "RunResult",
    "Check", "CheckResult", "Masker",
]
