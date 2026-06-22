# src/core/metadata/target.py
"""Target configuration model."""
from pydantic import BaseModel
from typing import Optional, List


class TargetConfig(BaseModel):
    target_id: str
    target_name: str
    catalog_name: str
    schema_name: str
    table_name: str
    layer: str  # BRONZE|SILVER|GOLD
    table_type: str  # MANAGED|EXTERNAL
    format: str  # DELTA
    partition_columns: List[str]
    liquid_clustering_columns: List[str]
    primary_key: List[str]
    acord_entity: Optional[str] = None
    retention_days: int
    enable_cdf: bool
    dimensional: bool = False  # gold star/snowflake (drives schema-evolution SCD handling)
    active_flag: bool = True
