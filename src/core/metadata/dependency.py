from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DependencyConfig:
    """Normalized DAG edge (control-table cfg_dependency)."""
    dependency_id: str
    object_type: str           # LOAD | TRANSFORM
    object_id: str
    depends_on_id: str
    dependency_type: Optional[str] = None
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
