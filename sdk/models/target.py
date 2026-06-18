"""
Target configuration model.

Represents a destination Unity Catalog table in the lakehouse.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class TargetConfig:
    """Configuration for a destination Unity Catalog table."""
    
    # Identity
    target_id: str
    target_name: str
    
    # Unity Catalog location
    catalog_name: str
    schema_name: str
    table_name: str
    
    # Table characteristics
    layer: str  # BRONZE, SILVER, GOLD
    table_type: str  # MANAGED, EXTERNAL
    format: str = "DELTA"  # DELTA, PARQUET, ICEBERG
    
    # Optimization
    partition_columns: Optional[List[str]] = None
    liquid_clustering_columns: Optional[List[str]] = None
    primary_key: Optional[List[str]] = None
    
    # Business context
    acord_entity: Optional[str] = None  # Party, Policy, Coverage, Claim, Payment, Loss
    retention_days: Optional[int] = None
    
    # Features
    enable_cdf: bool = True
    
    # Lifecycle
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate required combinations after initialization."""
        # Partition and liquid clustering are mutually exclusive
        if self.partition_columns and self.liquid_clustering_columns:
            raise ValueError(
                f"Target '{self.target_id}': partition_columns and liquid_clustering_columns "
                f"are mutually exclusive. Choose one optimization strategy."
            )
        
        # Validate ACORD entity mapping for SILVER layer
        valid_acord_entities = ["Party", "Policy", "Coverage", "Claim", "Payment", "Loss"]
        if self.layer == "SILVER" and self.acord_entity:
            if self.acord_entity not in valid_acord_entities:
                raise ValueError(
                    f"Target '{self.target_id}': invalid acord_entity '{self.acord_entity}'. "
                    f"Valid values: {valid_acord_entities}"
                )
    
    @property
    def fully_qualified_name(self) -> str:
        """Get fully qualified table name."""
        return f"{self.catalog_name}.{self.schema_name}.{self.table_name}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database writes."""
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "catalog_name": self.catalog_name,
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "layer": self.layer,
            "table_type": self.table_type,
            "format": self.format,
            "partition_columns": self.partition_columns,
            "liquid_clustering_columns": self.liquid_clustering_columns,
            "primary_key": self.primary_key,
            "acord_entity": self.acord_entity,
            "retention_days": self.retention_days,
            "enable_cdf": self.enable_cdf,
            "active_flag": self.active_flag,
            "created_by": self.created_by,
            "created_ts": self.created_ts,
            "updated_by": self.updated_by,
            "updated_ts": self.updated_ts,
        }
    
    @classmethod
    def from_row(cls, row) -> "TargetConfig":
        """Create from Spark Row or dict."""
        if hasattr(row, "asDict"):
            row = row.asDict()
        
        return cls(
            target_id=row["target_id"],
            target_name=row["target_name"],
            catalog_name=row["catalog_name"],
            schema_name=row["schema_name"],
            table_name=row["table_name"],
            layer=row["layer"],
            table_type=row["table_type"],
            format=row.get("format", "DELTA"),
            partition_columns=row.get("partition_columns"),
            liquid_clustering_columns=row.get("liquid_clustering_columns"),
            primary_key=row.get("primary_key"),
            acord_entity=row.get("acord_entity"),
            retention_days=row.get("retention_days"),
            enable_cdf=row.get("enable_cdf", True),
            active_flag=row.get("active_flag", True),
            created_by=row.get("created_by"),
            created_ts=row.get("created_ts"),
            updated_by=row.get("updated_by"),
            updated_ts=row.get("updated_ts"),
        )
