# src/core/metadata/dq_rule.py
"""DQ rule configuration model."""
from pydantic import BaseModel
from typing import Optional


class DQRuleConfig(BaseModel):
    dq_rule_id: str
    rule_name: str
    target_id: str
    rule_type: str
    column_name: str
    rule_expression: Optional[str] = None
    threshold_percent: float
    on_failure: str  # WARN|FAIL|QUARANTINE
    active_flag: bool = True
