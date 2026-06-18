"""
Data Quality rule configuration model.

Represents a data quality rule for validation and control.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class DQRuleConfig:
    """Configuration for a data quality rule."""
    
    # Identity
    dq_rule_id: str
    rule_name: str
    
    # Target
    target_id: str
    
    # Rule specification
    rule_type: str  # NOT_NULL, UNIQUE, RANGE, REGEX, CUSTOM_SQL, REFERENTIAL_INTEGRITY, FRESHNESS
    column_name: Optional[str] = None  # Column to check (required for most rules)
    rule_expression: Optional[str] = None  # SQL expression or regex pattern
    
    # Threshold
    threshold_percent: float = 1.0  # Allowed failure rate (0-1)
    
    # Action
    on_failure: str = "WARN"  # WARN, FAIL, QUARANTINE
    
    # Lifecycle
    active_flag: bool = True
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_ts: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate required combinations after initialization."""
        # Most rule types require column_name (except CUSTOM_SQL)
        if self.rule_type != "CUSTOM_SQL" and not self.column_name:
            raise ValueError(
                f"DQ Rule '{self.dq_rule_id}': rule_type '{self.rule_type}' requires column_name"
            )
        
        # Validate threshold_percent is between 0 and 1
        if not (0 <= self.threshold_percent <= 1):
            raise ValueError(
                f"DQ Rule '{self.dq_rule_id}': threshold_percent must be between 0 and 1, "
                f"got {self.threshold_percent}"
            )
        
        # Validate on_failure action
        valid_actions = ["WARN", "FAIL", "QUARANTINE"]
        if self.on_failure not in valid_actions:
            raise ValueError(
                f"DQ Rule '{self.dq_rule_id}': invalid on_failure '{self.on_failure}'. "
                f"Valid values: {valid_actions}"
            )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database writes."""
        return {
            "dq_rule_id": self.dq_rule_id,
            "rule_name": self.rule_name,
            "target_id": self.target_id,
            "rule_type": self.rule_type,
            "column_name": self.column_name,
            "rule_expression": self.rule_expression,
            "threshold_percent": self.threshold_percent,
            "on_failure": self.on_failure,
            "active_flag": self.active_flag,
            "created_by": self.created_by,
            "created_ts": self.created_ts,
            "updated_by": self.updated_by,
            "updated_ts": self.updated_ts,
        }
    
    @classmethod
    def from_row(cls, row) -> "DQRuleConfig":
        """Create from Spark Row or dict."""
        if hasattr(row, "asDict"):
            row = row.asDict()
        
        return cls(
            dq_rule_id=row["dq_rule_id"],
            rule_name=row["rule_name"],
            target_id=row["target_id"],
            rule_type=row["rule_type"],
            column_name=row.get("column_name"),
            rule_expression=row.get("rule_expression"),
            threshold_percent=row.get("threshold_percent", 1.0),
            on_failure=row.get("on_failure", "WARN"),
            active_flag=row.get("active_flag", True),
            created_by=row.get("created_by"),
            created_ts=row.get("created_ts"),
            updated_by=row.get("updated_by"),
            updated_ts=row.get("updated_ts"),
        )
