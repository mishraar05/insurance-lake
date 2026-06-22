# src/core/metadata/source.py
"""Source configuration model."""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    FILE = "FILE"
    TABLE = "TABLE"
    STREAM = "STREAM"
    API = "API"
    CDC = "CDC"


class SourceConfig(BaseModel):
    source_id: str
    source_name: str
    source_type: SourceType
    source_system: str
    connection_string: Optional[str] = None
    file_format: Optional[str] = None
    schema_location: Optional[str] = None
    credential_scope: Optional[str] = None
    credential_key: Optional[str] = None
    business_domain: str
    pii_flag: bool
    data_classification: str
    sla_hours: int
    active_flag: bool = True
