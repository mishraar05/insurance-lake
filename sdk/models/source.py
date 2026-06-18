"""
Source configuration model.

Represents an external data source feeding the lakehouse.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SourceConfig:
    """Configuration for an external data source."""
    
    # Identity
    source_id: str
    source_name: str
    
    # Source characteristics
    source_type: str  # FILE, TABLE, STREAM, API, CDC
    source_system: str  # PolicyCenter, ClaimCenter, etc.
    
    # Connection details
    connection_string: Optional[str] = None  # JDBC URL, API endpoint, or cloud storage path
    file_format: Optional[str] = None  # CSV, JSON, PARQUET, AVRO, XML, DELTA, FIXEDWIDTH
    schema_location: Optional[str] = None  # Path to Avro/JSON schema file or DDL
    
    # Security
    credential_scope: Optional[str] = None  # Databricks secret scope
    credential_key: Optional[str] = None  # Secret key name
    
    # Business context
    business_domain: str = None  # POLICY, CLAIM, BILLING, PARTY, PAYMENT, LOSS
    pii_flag: bool = False  # Contains PII/PHI?
    data_classification: str = None  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    
    # SLA
    sla_hours: Optional[int] = None  # Expected data arrival SLA in hours
    
    # Lifecycle
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate required combinations after initialization."""
        # Validate FILE sources have required fields
        if self.source_type == "FILE":
            if not self.file_format:
                raise ValueError(f"Source '{self.source_id}': source_type=FILE requires file_format")
            if not self.connection_string:
                raise ValueError(f"Source '{self.source_id}': source_type=FILE requires connection_string")
        
        # Validate PII sources have appropriate classification
        if self.pii_flag and self.data_classification not in ["CONFIDENTIAL", "RESTRICTED"]:
            raise ValueError(
                f"Source '{self.source_id}': pii_flag=true requires "
                f"data_classification='CONFIDENTIAL' or 'RESTRICTED', got '{self.data_classification}'"
            )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database writes."""
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "source_system": self.source_system,
            "connection_string": self.connection_string,
            "file_format": self.file_format,
            "schema_location": self.schema_location,
            "credential_scope": self.credential_scope,
            "credential_key": self.credential_key,
            "business_domain": self.business_domain,
            "pii_flag": self.pii_flag,
            "data_classification": self.data_classification,
            "sla_hours": self.sla_hours,
            "active_flag": self.active_flag,
            "created_by": self.created_by,
            "created_ts": self.created_ts,
            "updated_by": self.updated_by,
            "updated_ts": self.updated_ts,
        }
    
    @classmethod
    def from_row(cls, row) -> "SourceConfig":
        """Create from Spark Row or dict."""
        if hasattr(row, "asDict"):
            row = row.asDict()
        
        return cls(
            source_id=row["source_id"],
            source_name=row["source_name"],
            source_type=row["source_type"],
            source_system=row["source_system"],
            connection_string=row.get("connection_string"),
            file_format=row.get("file_format"),
            schema_location=row.get("schema_location"),
            credential_scope=row.get("credential_scope"),
            credential_key=row.get("credential_key"),
            business_domain=row["business_domain"],
            pii_flag=row["pii_flag"],
            data_classification=row["data_classification"],
            sla_hours=row.get("sla_hours"),
            active_flag=row.get("active_flag", True),
            created_by=row.get("created_by"),
            created_ts=row.get("created_ts"),
            updated_by=row.get("updated_by"),
            updated_ts=row.get("updated_ts"),
        )
