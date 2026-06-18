"""
Load configuration model.

Represents a data load operation from source to target.
"""

from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime


@dataclass
class LoadConfig:
    """Configuration for a data load operation."""
    
    # Identity
    load_id: str
    load_name: str
    
    # Source and target
    source_id: str
    target_id: str
    
    # Load characteristics
    load_type: str  # BATCH_FULL, BATCH_INCREMENTAL, STREAM_APPEND, STREAM_CDC, STREAM_UPSERT
    load_pattern: str  # APPEND, OVERWRITE, MERGE, SCD2, CDC
    engine: str  # DECLARATIVE, AUTOLOADER, COPY_INTO, STRUCTURED_STREAMING
    
    # Incremental load configuration
    watermark_column: Optional[str] = None
    watermark_type: Optional[str] = None  # TIMESTAMP, SEQUENCE, FILENAME
    
    # Streaming configuration
    checkpoint_location: Optional[str] = None
    trigger_interval: Optional[str] = None  # e.g., "5 minutes", "1 hour"
    
    # Merge configuration (for MERGE/SCD2/CDC patterns)
    merge_keys: Optional[str] = None  # Comma-separated list of key columns
    
    # Auto Loader configuration
    autoloader_options: Optional[Dict[str, str]] = None  # JSON with cloudFiles.* options
    
    # Schedule
    schedule_cron: Optional[str] = None
    depends_on: Optional[str] = None  # Comma-separated list of load_ids this depends on
    
    # Lifecycle
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate required combinations after initialization."""
        # Streaming loads require checkpoint location
        if self.load_type.startswith("STREAM_") and not self.checkpoint_location:
            raise ValueError(
                f"Load '{self.load_id}': load_type '{self.load_type}' requires checkpoint_location"
            )
        
        # Declarative engine requires specific patterns
        if self.engine == "DECLARATIVE" and self.load_pattern not in ["APPEND", "SCD2"]:
            raise ValueError(
                f"Load '{self.load_id}': engine=DECLARATIVE requires load_pattern "
                f"to be 'APPEND' or 'SCD2', got '{self.load_pattern}'"
            )
        
        # MERGE/SCD2/CDC patterns require merge keys
        if self.load_pattern in ["MERGE", "SCD2", "CDC"] and not self.merge_keys:
            raise ValueError(
                f"Load '{self.load_id}': load_pattern '{self.load_pattern}' requires merge_keys"
            )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database writes."""
        return {
            "load_id": self.load_id,
            "load_name": self.load_name,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "load_type": self.load_type,
            "load_pattern": self.load_pattern,
            "engine": self.engine,
            "watermark_column": self.watermark_column,
            "watermark_type": self.watermark_type,
            "checkpoint_location": self.checkpoint_location,
            "trigger_interval": self.trigger_interval,
            "merge_keys": self.merge_keys,
            "autoloader_options": self.autoloader_options,
            "schedule_cron": self.schedule_cron,
            "depends_on": self.depends_on,
            "active_flag": self.active_flag,
            "created_by": self.created_by,
            "created_ts": self.created_ts,
            "updated_by": self.updated_by,
            "updated_ts": self.updated_ts,
        }
    
    @classmethod
    def from_row(cls, row) -> "LoadConfig":
        """Create from Spark Row or dict."""
        if hasattr(row, "asDict"):
            row = row.asDict()
        
        return cls(
            load_id=row["load_id"],
            load_name=row["load_name"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            load_type=row["load_type"],
            load_pattern=row["load_pattern"],
            engine=row["engine"],
            watermark_column=row.get("watermark_column"),
            watermark_type=row.get("watermark_type"),
            checkpoint_location=row.get("checkpoint_location"),
            trigger_interval=row.get("trigger_interval"),
            merge_keys=row.get("merge_keys"),
            autoloader_options=row.get("autoloader_options"),
            schedule_cron=row.get("schedule_cron"),
            depends_on=row.get("depends_on"),
            active_flag=row.get("active_flag", True),
            created_by=row.get("created_by"),
            created_ts=row.get("created_ts"),
            updated_by=row.get("updated_by"),
            updated_ts=row.get("updated_ts"),
        )
