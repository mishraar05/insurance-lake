"""
Transform configuration model.

Represents a data transformation from source target to destination target.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class TransformConfig:
    """Configuration for a data transformation operation."""
    
    # Identity
    transform_id: str
    transform_name: str
    
    # Source and destination
    source_target_id: str
    destination_target_id: str
    
    # Transform logic
    transform_type: str  # SQL, PYTHON, ACORD_MAPPING, LOOKUP, AGGREGATION, PIVOT
    transform_sql: Optional[str] = None  # SQL query for transformation
    transform_python: Optional[str] = None  # Python function path for transformation
    
    # ACORD mapping (for SILVER -> canonical)
    acord_mapping_template: Optional[str] = None
    
    # SCD handling
    scd_type: Optional[str] = None  # SCD1, SCD2
    scd_key_columns: Optional[str] = None  # Comma-separated business key
    scd_timestamp_column: Optional[str] = None
    
    # Engine
    engine: str = "DECLARATIVE"  # DECLARATIVE, STRUCTURED_STREAMING, BATCH
    
    # Dependencies
    dependencies: Optional[str] = None  # Comma-separated transform_ids this depends on
    
    # Lifecycle
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate required combinations after initialization."""
        # Source and destination must be different
        if self.source_target_id == self.destination_target_id:
            raise ValueError(
                f"Transform '{self.transform_id}': source_target_id and destination_target_id "
                f"must be different"
            )
        
        # SCD2 with DECLARATIVE engine requires APPLY CHANGES
        if self.scd_type == "SCD2" and self.engine == "DECLARATIVE":
            if not self.scd_key_columns or not self.scd_timestamp_column:
                raise ValueError(
                    f"Transform '{self.transform_id}': scd_type=SCD2 with engine=DECLARATIVE "
                    f"requires scd_key_columns and scd_timestamp_column"
                )
        
        # Either SQL or Python transform must be specified
        if self.transform_type in ["SQL", "PYTHON"]:
            if not self.transform_sql and not self.transform_python:
                raise ValueError(
                    f"Transform '{self.transform_id}': transform_type '{self.transform_type}' "
                    f"requires either transform_sql or transform_python"
                )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database writes."""
        return {
            "transform_id": self.transform_id,
            "transform_name": self.transform_name,
            "source_target_id": self.source_target_id,
            "destination_target_id": self.destination_target_id,
            "transform_type": self.transform_type,
            "transform_sql": self.transform_sql,
            "transform_python": self.transform_python,
            "acord_mapping_template": self.acord_mapping_template,
            "scd_type": self.scd_type,
            "scd_key_columns": self.scd_key_columns,
            "scd_timestamp_column": self.scd_timestamp_column,
            "engine": self.engine,
            "dependencies": self.dependencies,
            "active_flag": self.active_flag,
            "created_by": self.created_by,
            "created_ts": self.created_ts,
            "updated_by": self.updated_by,
            "updated_ts": self.updated_ts,
        }
    
    @classmethod
    def from_row(cls, row) -> "TransformConfig":
        """Create from Spark Row or dict."""
        if hasattr(row, "asDict"):
            row = row.asDict()
        
        return cls(
            transform_id=row["transform_id"],
            transform_name=row["transform_name"],
            source_target_id=row["source_target_id"],
            destination_target_id=row["destination_target_id"],
            transform_type=row["transform_type"],
            transform_sql=row.get("transform_sql"),
            transform_python=row.get("transform_python"),
            acord_mapping_template=row.get("acord_mapping_template"),
            scd_type=row.get("scd_type"),
            scd_key_columns=row.get("scd_key_columns"),
            scd_timestamp_column=row.get("scd_timestamp_column"),
            engine=row.get("engine", "DECLARATIVE"),
            dependencies=row.get("dependencies"),
            active_flag=row.get("active_flag", True),
            created_by=row.get("created_by"),
            created_ts=row.get("created_ts"),
            updated_by=row.get("updated_by"),
            updated_ts=row.get("updated_ts"),
        )
