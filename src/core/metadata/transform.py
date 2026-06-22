# src/core/metadata/transform.py
"""Transform configuration model."""
from pydantic import BaseModel
from typing import Optional, List


class TransformConfig(BaseModel):
    transform_id: str
    transform_name: str
    source_target_id: str
    destination_target_id: str
    transform_type: str
    transform_sql: Optional[str] = None
    transform_python: Optional[str] = None
    acord_mapping_template: Optional[str] = None
    scd_type: Optional[str] = None
    scd_key_columns: Optional[List[str]] = None
    scd_timestamp_column: Optional[str] = None
    engine: str
    dependencies: Optional[List[str]] = None
    active_flag: bool = True
