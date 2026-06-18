# ABC SDK Specification (Audit, Balance, Control)

**Spec ID:** FND-010, FND-011, FND-013, FND-014  
**Title:** ABC SDK - Modernization of Audit/Balance/Control Framework  
**Author:** InsureLake Framework Team  
**Date:** 2026-06-18  
**Status:** In Progress  
**Depends On:** None (Foundation component)

---

## 1. Purpose

**What does the ABC SDK do?**

The ABC SDK is the **single, idempotent interface** for all framework components to record:
- **Audit**: What ran (who, when, what, where, results)
- **Balance**: Whether data balanced (count + financial reconciliation)
- **Control**: Data quality outcomes, validation decisions, exceptions

Every ingestion, transformation, DQ check, and reconciliation writes through the ABC SDK to maintain a complete audit trail, detect imbalances, and track control decisions.

**Key Features:**
- Idempotent writes (safe for streaming, batch, Lakeflow)
- Non-blocking (failures don't crash data pipelines)
- Trace ID propagation (end-to-end lineage)
- Cost tracking integration (FinOps)
- Typed exceptions with resilience

**Scope:**
- **In scope**: Python SDK wrapping existing ABC Delta tables, 7 core methods, unit tests >80%
- **Out of scope**: Redesigning ABC schema (SDK adapts to existing), ABC dashboards/reporting

---

## 2. Requirements

### Functional Requirements
1. **FR-1**: Provide 7 methods: `start_run`, `end_run`, `log_audit`, `log_balance`, `log_dq`, `log_exception`, `log_cost`
2. **FR-2**: All writes are **idempotent** (safe to re-run; upsert semantics)
3. **FR-3**: Generate unique `run_id` and `trace_id` on `start_run`
4. **FR-4**: Propagate `trace_id` across all calls for end-to-end lineage
5. **FR-5**: Capture structured metrics: rows, timings, identity, DQ outcomes, costs
6. **FR-6**: Map SDK calls to existing ABC table schemas (no schema changes)
7. **FR-7**: Support batch, streaming, and Lakeflow pipeline contexts

### Non-Functional Requirements
- **Performance**: <100ms per log call, non-blocking async writes preferred
- **Reliability**: ABC write failures must NOT fail data pipelines (resilience over strictness)
- **Testability**: >80% unit test coverage, mock Spark dependencies
- **Compatibility**: Existing ABC consumers (dashboards, reports) unaffected
- **Maintainability**: Clear error messages, typed exceptions, comprehensive logging

---

## 3. Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│  Framework Components (Ingestion, Harmonization, DQ, etc.)  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      ABC SDK                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Run Mgmt   │  │   Logging    │  │   Cost       │      │
│  │ start_run()  │  │ log_audit()  │  │ log_cost()   │      │
│  │ end_run()    │  │ log_balance()│  │              │      │
│  │              │  │ log_dq()     │  │              │      │
│  │              │  │log_exception()│  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ▼                                 │
│              ┌──────────────────────────┐                    │
│              │   ABC Table Writer       │                    │
│              │  (Idempotent, Resilient) │                    │
│              └──────────┬───────────────┘                    │
└─────────────────────────┼────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Unity Catalog: insurelake_abc.abc              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Audit   │  │ Balance  │  │ Control  │  │   Cost   │   │
│  │  Table   │  │  Table   │  │  Table   │  │  Table   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Components
- **ABC Class**: Main SDK entry point, manages Spark session and catalog/schema
- **RunHandle**: Dataclass holding `run_id` and `trace_id`
- **Table Writers**: Internal helpers for each ABC table (Audit, Balance, Control, Cost)
- **Exception Classes**: `ABCConnectionError`, `ABCWriteError`, `ABCValidationError`

---

## 4. Data Model

### ABC Tables (insurelake_abc.abc schema)

#### Table: abc_audit
```sql
CREATE TABLE insurelake_abc.abc.abc_audit (
  run_id STRING NOT NULL COMMENT 'Unique run identifier (UUID)',
  trace_id STRING COMMENT 'End-to-end trace ID for lineage',
  component STRING COMMENT 'Framework component (ingestion, harmonization, dq, etc.)',
  entity STRING COMMENT 'Entity processed (policy, claim, payment, etc.)',
  run_type STRING COMMENT 'BATCH_FULL, BATCH_INCREMENTAL, STREAM_APPEND, etc.',
  status STRING COMMENT 'RUNNING, SUCCESS, FAILED, TIMEOUT',
  start_ts TIMESTAMP COMMENT 'Run start timestamp',
  end_ts TIMESTAMP COMMENT 'Run end timestamp',
  duration_seconds DOUBLE COMMENT 'Elapsed time',
  rows_read LONG COMMENT 'Input row count',
  rows_written LONG COMMENT 'Output row count',
  rows_rejected LONG COMMENT 'Rejected row count',
  identity STRING COMMENT 'User/service principal',
  spark_job_id STRING COMMENT 'Spark job ID',
  metadata MAP<STRING, STRING> COMMENT 'Additional key-value metrics',
  created_ts TIMESTAMP COMMENT 'Record creation timestamp',
  CONSTRAINT pk_abc_audit PRIMARY KEY (run_id)
) USING DELTA
PARTITIONED BY (DATE(created_ts))
COMMENT 'Audit trail for all framework runs';
```

#### Table: abc_balance
```sql
CREATE TABLE insurelake_abc.abc.abc_balance (
  balance_id STRING NOT NULL COMMENT 'Unique balance check ID',
  run_id STRING NOT NULL COMMENT 'FK to abc_audit',
  check_name STRING COMMENT 'Name of balance check',
  check_type STRING COMMENT 'COUNT, FINANCIAL, HASH',
  source_ref STRING COMMENT 'Source table/file reference',
  source_value DOUBLE COMMENT 'Source count/amount',
  target_ref STRING COMMENT 'Target table reference',
  target_value DOUBLE COMMENT 'Target count/amount',
  variance DOUBLE COMMENT 'Difference (source - target)',
  variance_percent DOUBLE COMMENT 'Variance as percentage',
  threshold_percent DOUBLE COMMENT 'Acceptable tolerance',
  balanced BOOLEAN COMMENT 'Within tolerance?',
  created_ts TIMESTAMP,
  CONSTRAINT pk_abc_balance PRIMARY KEY (balance_id),
  CONSTRAINT fk_balance_audit FOREIGN KEY (run_id) REFERENCES insurelake_abc.abc.abc_audit(run_id)
) USING DELTA
PARTITIONED BY (DATE(created_ts))
COMMENT 'Balance and reconciliation checks';
```

#### Table: abc_control
```sql
CREATE TABLE insurelake_abc.abc.abc_control (
  control_id STRING NOT NULL COMMENT 'Unique control event ID',
  run_id STRING NOT NULL COMMENT 'FK to abc_audit',
  control_type STRING COMMENT 'DQ_RULE, EXCEPTION, VALIDATION',
  rule_id STRING COMMENT 'Rule identifier (dq_rule_id)',
  rule_name STRING COMMENT 'Human-readable rule name',
  target_table STRING COMMENT 'Table being validated',
  column_name STRING COMMENT 'Column checked (if applicable)',
  check_result STRING COMMENT 'PASS, FAIL, WARN',
  failed_count LONG COMMENT 'Number of failing records',
  action_taken STRING COMMENT 'WARN, FAIL, QUARANTINE',
  error_message STRING COMMENT 'Exception message',
  stack_trace STRING COMMENT 'Full stack trace',
  created_ts TIMESTAMP,
  CONSTRAINT pk_abc_control PRIMARY KEY (control_id),
  CONSTRAINT fk_control_audit FOREIGN KEY (run_id) REFERENCES insurelake_abc.abc.abc_audit(run_id)
) USING DELTA
PARTITIONED BY (DATE(created_ts))
COMMENT 'Data quality, validation, and exception tracking';
```

#### Table: abc_cost
```sql
CREATE TABLE insurelake_abc.abc.abc_cost (
  cost_id STRING NOT NULL COMMENT 'Unique cost entry ID',
  run_id STRING NOT NULL COMMENT 'FK to abc_audit',
  component STRING COMMENT 'Component consuming resources',
  entity STRING COMMENT 'Entity processed',
  dbu_seconds DOUBLE COMMENT 'DBU consumption (seconds)',
  dbu_count DOUBLE COMMENT 'Total DBUs',
  sql_warehouse_seconds DOUBLE COMMENT 'SQL warehouse compute seconds',
  genie_dbu DOUBLE COMMENT 'Genie Code DBU consumption',
  cost_usd DOUBLE COMMENT 'Estimated cost in USD',
  cluster_id STRING COMMENT 'Cluster ID',
  warehouse_id STRING COMMENT 'SQL Warehouse ID',
  created_ts TIMESTAMP,
  CONSTRAINT pk_abc_cost PRIMARY KEY (cost_id),
  CONSTRAINT fk_cost_audit FOREIGN KEY (run_id) REFERENCES insurelake_abc.abc.abc_audit(run_id)
) USING DELTA
PARTITIONED BY (DATE(created_ts))
COMMENT 'Cost and consumption tracking (FinOps)';
```

---

## 5. Implementation Details

### Code Structure
```
sdk/
├── __init__.py              # Export ABC class
├── abc.py                   # Main ABC SDK class
├── models/
│   ├── run_handle.py        # RunHandle dataclass
│   ├── audit_entry.py       # AuditEntry model
│   ├── balance_check.py     # BalanceCheck model
│   ├── control_event.py     # ControlEvent model
│   └── cost_entry.py        # CostEntry model
└── exceptions.py            # ABC exception classes
```

### Key Classes

#### Class: ABC
```python
from dataclasses import dataclass
from pyspark.sql import SparkSession
from typing import Optional, Dict, List
import uuid
from datetime import datetime

@dataclass
class RunHandle:
    """Handle returned by start_run()"""
    run_id: str
    trace_id: str

class ABC:
    """
    ABC SDK - Single interface for Audit/Balance/Control logging.
    
    Usage:
        abc = ABC(catalog="insurelake_abc", schema="abc")
        run = abc.start_run(component="ingestion", entity="policy", run_type="BATCH_INCREMENTAL")
        abc.log_audit(run.run_id, {"rows_read": 10000, "rows_written": 9980})
        abc.end_run(run.run_id, status="SUCCESS")
    """
    
    def __init__(
        self,
        catalog: str = "insurelake_abc",
        schema: str = "abc",
        spark: Optional[SparkSession] = None
    ):
        """Initialize ABC SDK."""
        self.catalog = catalog
        self.schema = schema
        self.spark = spark or SparkSession.getActiveSession()
        
        if not self.spark:
            raise ABCConnectionError("No active Spark session")
        
        # Test connectivity
        try:
            self.spark.sql(f"USE CATALOG {self.catalog}")
            self.spark.sql(f"USE SCHEMA {self.schema}")
        except Exception as e:
            raise ABCConnectionError(
                f"Cannot connect to {self.catalog}.{self.schema}: {str(e)}"
            )
    
    def start_run(
        self,
        component: str,
        entity: str,
        run_type: str,
        trace_id: Optional[str] = None
    ) -> RunHandle:
        """
        Start a new run and return RunHandle.
        
        Args:
            component: Framework component (ingestion, harmonization, dq, etc.)
            entity: Entity being processed (policy, claim, payment, etc.)
            run_type: BATCH_FULL, BATCH_INCREMENTAL, STREAM_APPEND, etc.
            trace_id: Optional trace ID (if propagating from upstream)
        
        Returns:
            RunHandle with run_id and trace_id
        """
        run_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        
        try:
            # Insert into abc_audit with status=RUNNING
            self.spark.sql(f"""
                INSERT INTO {self.catalog}.{self.schema}.abc_audit
                VALUES (
                    '{run_id}',
                    '{trace_id}',
                    '{component}',
                    '{entity}',
                    '{run_type}',
                    'RUNNING',
                    current_timestamp(),
                    NULL,
                    NULL,
                    NULL, NULL, NULL,
                    current_user(),
                    NULL,
                    NULL,
                    current_timestamp()
                )
            """)
        except Exception as e:
            # Log warning but don't fail
            print(f"WARNING: ABC write failed: {e}")
        
        return RunHandle(run_id=run_id, trace_id=trace_id)
    
    def end_run(
        self,
        run_id: str,
        status: str,
        metrics: Optional[Dict] = None
    ):
        """
        Close a run with final status.
        
        Args:
            run_id: Run ID from start_run()
            status: SUCCESS, FAILED, TIMEOUT
            metrics: Optional final metrics dict
        """
        # Implementation...
    
    def log_audit(self, run_id: str, metrics: Dict):
        """Log audit metrics (rows read/written/rejected, timings)."""
        # Implementation...
    
    def log_balance(self, run_id: str, checks: List[Dict]):
        """Log balance checks (count + financial reconciliation)."""
        # Implementation...
    
    def log_dq(self, run_id: str, results: List[Dict]):
        """Log DQ rule outcomes."""
        # Implementation...
    
    def log_exception(self, run_id: str, error: Exception):
        """Log structured exception."""
        # Implementation...
    
    def log_cost(self, run_id: str, consumption: Dict):
        """Log cost and consumption metrics."""
        # Implementation...
```

### Dependencies
- **PySpark**: For Spark session and SQL execution
- **dataclasses**: For models
- **uuid**: For run_id and trace_id generation
- **datetime**: For timestamps
- **typing**: For type hints

---

## 6. Validation Rules

1. **Rule 1**: `run_id` must be unique (UUID v4)
   - **On failure:** Raise `ABCValidationError`

2. **Rule 2**: `status` must be one of: RUNNING, SUCCESS, FAILED, TIMEOUT
   - **On failure:** Raise `ABCValidationError`

3. **Rule 3**: `component` and `entity` must not be NULL
   - **On failure:** Raise `ABCValidationError`

4. **Rule 4**: Balance checks must include `source_value` and `target_value`
   - **On failure:** Raise `ABCValidationError`

5. **Rule 5**: All table writes must be idempotent (upsert on PK)
   - **On failure:** Log warning, continue

6. **Rule 6**: ABC write failures must NOT crash data pipelines
   - **On failure:** Downgrade to warning + local log file

---

## 7. Error Handling

### Error Scenarios

| Error | Cause | Message | Recovery Action |
|-------|-------|---------|-----------------|
| ABCConnectionError | Catalog/schema not found | "Cannot connect to {catalog}.{schema}: {error}" | Check Unity Catalog permissions, verify catalog/schema exist |
| ABCWriteError | Insert/update fails | "Failed to write to {table}: {error}" | Log warning, write to local file, continue pipeline |
| ABCValidationError | Invalid input parameters | "Validation failed: {field} {reason}" | Raise exception in development; log warning in production |

### Resilience Strategy
- **Development/Test**: Raise exceptions immediately
- **Production**: Downgrade ABC errors to warnings, log locally, continue data pipeline
- **Local Fallback**: Write ABC entries to local JSON file if Delta writes fail

---

## 8. Testing

### Acceptance Criteria
- [x] ABC class initializes with valid Spark session
- [x] start_run() generates unique run_id and trace_id
- [x] All 7 methods write to correct ABC tables
- [x] Idempotent: repeated calls do not duplicate
- [x] Resilient: ABC write failures don't crash pipelines
- [x] >80% unit test coverage
- [x] Mock Spark dependencies (no external I/O)
- [x] Existing ABC consumers unaffected (FND-014)

### Test Scenarios

#### Scenario 1: Happy path
**Given:** Valid Spark session and ABC tables exist  
**When:** Call start_run(), log_audit(), end_run()  
**Then:** Entries written to abc_audit table, run marked SUCCESS

#### Scenario 2: ABC write failure
**Given:** ABC table write fails (permissions issue)  
**When:** Call log_audit()  
**Then:** Warning logged, local file written, pipeline continues

#### Scenario 3: Idempotent re-run
**Given:** Run already exists with same run_id  
**When:** Call end_run() again with same run_id  
**Then:** Update existing row, do not duplicate

#### Scenario 4: Trace ID propagation
**Given:** start_run() called with trace_id  
**When:** Pass trace_id to downstream components  
**Then:** All logs share same trace_id for lineage

---

## 9. Examples

### Example 1: Ingestion with full ABC logging

```python
from sdk import ABC, ConfigLoader

# Initialize
abc = ABC(catalog="insurelake_abc", schema="abc")
loader = ConfigLoader()

# Load config
load_config = loader.get_load("load_policy_batch")

# Start run
run = abc.start_run(
    component="ingestion",
    entity="policy",
    run_type=load_config.load_type
)

try:
    # Perform ingestion (simplified)
    source_count = 10000
    df = spark.read.format("csv").load(load_config.source.connection_string)
    df_clean = df.filter("policy_number IS NOT NULL")
    df_clean.write.mode("append").saveAsTable(load_config.target.fully_qualified_name)
    target_count = df_clean.count()
    rejected_count = source_count - target_count
    
    # Log audit metrics
    abc.log_audit(run.run_id, {
        "rows_read": source_count,
        "rows_written": target_count,
        "rows_rejected": rejected_count,
        "duration_seconds": 42.5
    })
    
    # Log balance check
    abc.log_balance(run.run_id, [{
        "check_name": "src_vs_bronze_count",
        "check_type": "COUNT",
        "source_ref": load_config.source.source_id,
        "source_value": source_count,
        "target_ref": load_config.target.fully_qualified_name,
        "target_value": target_count,
        "threshold_percent": 0.01  # 1% tolerance
    }])
    
    # Log cost
    abc.log_cost(run.run_id, {
        "dbu_seconds": 1234.5,
        "dbu_count": 2.0,
        "cluster_id": spark.conf.get("spark.databricks.clusterUsageTags.clusterId")
    })
    
    # End run successfully
    abc.end_run(run.run_id, status="SUCCESS")
    
except Exception as e:
    # Log exception
    abc.log_exception(run.run_id, e)
    abc.end_run(run.run_id, status="FAILED")
    raise
```

### Example 2: DQ check with ABC logging

```python
from sdk import ABC, ConfigLoader

abc = ABC()
loader = ConfigLoader()

# Start DQ run
run = abc.start_run(
    component="data_quality",
    entity="policy",
    run_type="DQ_BATCH"
)

# Load DQ rules
dq_rules = loader.get_dq_rules_by_target("tgt_bronze_policy")

# Run DQ checks
for rule in dq_rules:
    # Execute DQ check (simplified)
    if rule.rule_type == "NOT_NULL":
        failed_count = spark.sql(f"""
            SELECT COUNT(*) FROM insurelake.bronze.policy_raw
            WHERE {rule.column_name} IS NULL
        """).collect()[0][0]
        
        passed = (failed_count == 0)
        
        # Log DQ result
        abc.log_dq(run.run_id, [{
            "rule_id": rule.dq_rule_id,
            "rule_name": rule.rule_name,
            "target_table": "insurelake.bronze.policy_raw",
            "column_name": rule.column_name,
            "check_result": "PASS" if passed else "FAIL",
            "failed_count": failed_count,
            "action_taken": rule.on_failure
        }])

abc.end_run(run.run_id, status="SUCCESS")
```

---

## 10. References

- [FND-010_abc-sdk-interface-spec.md](FND-010_abc-sdk-interface-spec.md) - ABC SDK interface specification
- [FND-001_config-model-spec.md](FND-001_config-model-spec.md) - Config metadata model
- [FND-003-COMPLETE.md](../FND-003-COMPLETE.md) - Config Loader SDK (reference implementation)
- [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) - Project principles and roadmap
- Databricks system tables: `system.billing.usage` for cost data
- Unity Catalog audit logs

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-06-18 | Framework Team | Initial comprehensive spec based on interface spec |
