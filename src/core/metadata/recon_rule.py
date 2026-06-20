from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ReconRuleConfig:
    """Reconciliation rule (control-table cfg_recon_rule)."""
    recon_rule_id: str
    rule_name: str
    recon_type: str            # ROW_COUNT | CONTROL_TOTAL | CROSS_LAYER | SOURCE_OF_RECORD
    load_id: Optional[str] = None
    target_id: Optional[str] = None
    source_ref: Optional[str] = None
    target_ref: Optional[str] = None
    measure_column: Optional[str] = None
    tolerance_percent: float = 0.0
    on_break: str = "WARN"     # WARN | FAIL
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
