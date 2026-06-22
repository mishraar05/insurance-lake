# src/core/sdk/run_handle.py
"""RunHandle dataclass for ABC SDK."""
from dataclasses import dataclass


@dataclass
class RunHandle:
    """Handle returned by start_run()"""
    run_id: str
    trace_id: str
