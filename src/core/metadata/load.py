# src/core/metadata/load.py
"""Load configuration model."""
from pydantic import BaseModel
from typing import Optional, List


class LoadConfig(BaseModel):
    load_id: str
    load_name: str
    source_id: str
    target_id: str
    load_type: str
    load_pattern: str
    engine: str
    watermark_column: Optional[str] = None
    watermark_type: Optional[str] = None
    checkpoint_location: str
    trigger_interval: Optional[str] = None
    merge_keys: Optional[List[str]] = None
    autoloader_options: dict
    schedule_cron: Optional[str] = None
    depends_on: Optional[List[str]] = None
    # schema-evolution policy (consumed by ingestion.engine._build_resolution_context -> ResolutionContext)
    source_system_type: str = "stable"  # stable | regulated | volatile
    governance_tier: str = "standard"  # standard | high
    zero_downtime: bool = False
    paranoid: bool = False
    type_changes: str = "none"  # none | widening | strict
    renames_expected: bool = False
    active_flag: bool = True
