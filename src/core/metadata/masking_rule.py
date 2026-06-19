from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MaskingRuleConfig:
    """Masking rule for a target column (control-table cfg_masking_rule)."""
    masking_rule_id: str
    rule_name: str
    target_id: str
    column_name: str
    classification: str            # CONFIDENTIAL | RESTRICTED
    technique: str                 # UC_COLUMN_MASK | ROW_FILTER | TOKENIZE | HASH
    mask_function: Optional[str] = None
    reversible_flag: bool = False
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
