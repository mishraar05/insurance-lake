---
id: foundation.abc-sdk
title: ABC SDK (Audit, Balance, Control)
owner: EY
status: active
target_path: src/core/sdk/
owning_skill: framework-dev.build-abc-sdk
backlog: [FND-010, FND-011, FND-013, FND-014]
provides:
  - ABC
  - RunHandle
  - start_run
  - end_run
  - log_audit
  - log_balance
  - log_dq
  - log_exception
  - log_cost
depends_on: []
generation_context:
  - specs/foundation/abc-sdk-spec.md
acceptance:
  - "pytest tests/unit/test_abc_sdk.py"
  - "pytest tests/integration/test_abc_integration.py"
regeneration: scaffold-then-edit
---

# ABC SDK Specification (Audit, Balance, Control)

**Spec ID:** FND-010, FND-011, FND-013, FND-014  
**Title:** ABC SDK - Modernization of Audit/Balance/Control Framework  
**Owner:** EY  
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

## 3. Interface - exact skeleton

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
        pass
    
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
        pass
    
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
        pass
    
    def log_audit(self, run_id: str, metrics: Dict):
        """Log audit metrics (rows read/written/rejected, timings)."""
        pass
    
    def log_balance(self, run_id: str, checks: List[Dict]):
        """Log balance checks (count + financial reconciliation)."""
        pass
    
    def log_dq(self, run_id: str, results: List[Dict]):
        """Log DQ rule outcomes."""
        pass
    
    def log_exception(self, run_id: str, error: Exception):
        """Log structured exception."""
        pass
    
    def log_cost(self, run_id: str, consumption: Dict):
        """Log cost and consumption metrics."""
        pass
```

---

## 4. Inputs / Outputs

**Inputs:**
- Component name, entity name, run type
- Metrics dicts (rows, timings, costs)
- Balance check specifications
- DQ rule results
- Exception objects

**Outputs:**
- ABC Delta tables in Unity Catalog (`insurelake_abc.abc` schema)
- RunHandle objects for tracking
- Warning logs if ABC writes fail (non-blocking)

---

## 5. Design

### Architecture Overview

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

### SOLID Principles Application

**Single Responsibility Principle (SRP):**
- **ABC class**: Coordinates logging operations, delegates to specialized writers
- **Table writers**: Each writer handles ONE table (AuditWriter, BalanceWriter, ControlWriter, CostWriter)
- **RunHandle**: Single purpose - carry run_id and trace_id
- Example separation:
  ```python
  class ABC:
      def __init__(self):
          self._audit_writer = AuditWriter()
          self._balance_writer = BalanceWriter()
          self._control_writer = ControlWriter()
          self._cost_writer = CostWriter()
      
      def log_audit(self, run_id, metrics):
          self._audit_writer.write(run_id, metrics)  # Delegates to specialist
  ```

**Open/Closed Principle (OCP):**
- **Closed for modification**: ABC interface (7 methods) is stable
- **Open for extension**: New log types via new methods, not modifying existing
- Example:
  ```python
  # Future: Add lineage logging WITHOUT changing existing methods
  def log_lineage(self, run_id, upstream_ids, downstream_ids):
      self._lineage_writer.write(run_id, upstream_ids, downstream_ids)
  # Existing log_audit(), log_balance() unchanged
  ```

**Liskov Substitution Principle (LSP):**
- **Writer polymorphism**: All table writers implement same `TableWriter` interface
- Any writer substitutes for `TableWriter` base
- Example:
  ```python
  class TableWriter(ABC):
      def write(self, run_id: str, data: Dict) -> None:
          pass
  
  class AuditWriter(TableWriter):
      def write(self, run_id, data):
          # Write to abc_audit table
          pass
  
  class BalanceWriter(TableWriter):
      def write(self, run_id, data):
          # Write to abc_balance table
          pass
  
  # All writers interchangeable
  def batch_write(writers: List[TableWriter], run_id, data):
      for writer in writers:
          writer.write(run_id, data)  # LSP - any writer works
  ```

**Interface Segregation Principle (ISP):**
- **Segregated logging methods**: `log_audit`, `log_balance`, `log_dq`, `log_cost` (not one `log_everything`)
- Clients call only what they need:
  - Ingestion engine calls `start_run`, `log_audit`, `log_balance`, `end_run`
  - DQ engine calls `start_run`, `log_dq`, `end_run`
  - Cost tracker calls `log_cost` only
- Counter-example (DON'T DO):
  ```python
  # BAD: Fat interface forcing all clients to know all methods
  class ABC:
      def log_all(self, audit, balance, dq, cost, exception):
          # Forces every caller to provide ALL metrics, even if unused
          pass
  ```

**Dependency Inversion Principle (DIP):**
- **ABC depends on abstractions**: `SparkSession` interface (not concrete impl)
- **Table writers depend on abstraction**: `TableWriter` protocol, not Delta specifics
- High-level ABC orchestration doesn't depend on low-level Delta writes
- Example:
  ```python
  # High-level ABC depends on abstraction
  class ABC:
      def __init__(self, writer_factory: TableWriterFactory):
          self._writers = writer_factory.create_writers()  # DIP
      
      def log_audit(self, run_id, metrics):
          writer = self._writers["audit"]  # Abstraction
          writer.write(run_id, metrics)
  
  # Low-level implementation
  class DeltaTableWriterFactory(TableWriterFactory):
      def create_writers(self):
          return {
              "audit": DeltaAuditWriter(),
              "balance": DeltaBalanceWriter()
          }
  # ABC doesn't know it's Delta - could be Iceberg, Hudi, Postgres
  ```

### Data Model

#### ABC Tables (insurelake_abc.abc schema)

**Table: abc_audit**
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

**Table: abc_balance**
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

**Table: abc_control**
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

**Table: abc_cost**
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

## 6. Implementation logic & guidance

This section provides **exact code implementations** for all ABC SDK methods. Code generators MUST implement these patterns exactly.

### 6.1 Initialization Pattern

```python
class ABC:
    def __init__(
        self,
        catalog: str = "insurelake_abc",
        schema: str = "abc",
        spark: Optional[SparkSession] = None
    ):
        """Initialize ABC SDK."""
        import logging
        from pyspark.sql import SparkSession
        
        self.catalog = catalog
        self.schema = schema
        self.spark = spark or SparkSession.builder.getOrCreate()
        self.logger = logging.getLogger(__name__)
        
        # Test connectivity (non-blocking)
        try:
            self.spark.sql(f"USE CATALOG {self.catalog}")
            self.spark.sql(f"USE SCHEMA {self.schema}")
        except Exception as e:
            self.logger.warning(f"ABC connectivity check failed: {e}")
```

### 6.2 start_run() Implementation

```python
def start_run(
    self,
    component: str,
    entity: str,
    run_type: str,
    trace_id: Optional[str] = None
) -> RunHandle:
    """Start a new run and return RunHandle."""
    import uuid
    from datetime import datetime
    
    # Step 1: Generate run_id (always new UUID)
    run_id = str(uuid.uuid4())
    
    # Step 2: Generate or accept trace_id
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    
    # Step 3: Get current identity
    try:
        identity = self.spark.conf.get("spark.databricks.user.email", "unknown")
    except Exception:
        identity = "unknown"
    
    # Step 4: Insert RUNNING status into abc_audit (idempotent)
    audit_record = {
        "run_id": run_id,
        "trace_id": trace_id,
        "component": component,
        "entity": entity,
        "run_type": run_type,
        "status": "RUNNING",
        "start_ts": datetime.utcnow(),
        "identity": identity,
        "created_ts": datetime.utcnow()
    }
    
    try:
        df = self.spark.createDataFrame([audit_record])
        df.write.format("delta").mode("append").saveAsTable(
            f"{self.catalog}.{self.schema}.abc_audit"
        )
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC write failed for run {run_id}: {e}")
        self._write_local_fallback("abc_audit", audit_record)
    
    # Step 5: Return handle
    return RunHandle(run_id=run_id, trace_id=trace_id)
```

### 6.3 end_run() Implementation

```python
def end_run(
    self,
    run_id: str,
    status: str,
    metrics: Optional[Dict] = None
):
    """Close a run with final status."""
    from datetime import datetime
    from pyspark.sql.functions import col, lit, when
    
    # Validate status
    valid_statuses = {"SUCCESS", "FAILED", "TIMEOUT"}
    if status not in valid_statuses:
        raise ABCValidationError(
            f"Invalid status '{status}'. Must be one of: {valid_statuses}"
        )
    
    # Calculate end_ts and duration
    end_ts = datetime.utcnow()
    
    try:
        # Read existing record to calculate duration
        audit_table = f"{self.catalog}.{self.schema}.abc_audit"
        existing = self.spark.table(audit_table).filter(col("run_id") == lit(run_id))
        
        if existing.count() == 0:
            self.logger.warning(f"No audit record found for run_id: {run_id}")
            return
        
        # Get start_ts
        start_ts = existing.select("start_ts").first()[0]
        duration_seconds = (end_ts - start_ts).total_seconds()
        
        # Update record (MERGE for idempotency)
        update_data = {
            "run_id": run_id,
            "status": status,
            "end_ts": end_ts,
            "duration_seconds": duration_seconds
        }
        
        # Merge metrics if provided
        if metrics:
            for key, value in metrics.items():
                update_data[key] = value
        
        # Write update (upsert pattern)
        df_update = self.spark.createDataFrame([update_data])
        df_update.createOrReplaceTempView("abc_audit_update")
        
        self.spark.sql(f"""
            MERGE INTO {audit_table} AS target
            USING abc_audit_update AS source
            ON target.run_id = source.run_id
            WHEN MATCHED THEN UPDATE SET *
        """)
        
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC end_run failed for {run_id}: {e}")
        self._write_local_fallback("abc_audit_update", {
            "run_id": run_id,
            "status": status,
            "end_ts": end_ts
        })
```

### 6.4 log_audit() Implementation

```python
def log_audit(self, run_id: str, metrics: Dict):
    """Log audit metrics (rows read/written/rejected, timings)."""
    from datetime import datetime
    
    # Validate inputs
    if not run_id:
        raise ABCValidationError("run_id cannot be None or empty")
    
    # Build audit record
    audit_record = {
        "run_id": run_id,
        "created_ts": datetime.utcnow()
    }
    audit_record.update(metrics)
    
    try:
        # Upsert into abc_audit (merge on run_id)
        df = self.spark.createDataFrame([audit_record])
        df.createOrReplaceTempView("abc_audit_metrics")
        
        audit_table = f"{self.catalog}.{self.schema}.abc_audit"
        self.spark.sql(f"""
            MERGE INTO {audit_table} AS target
            USING abc_audit_metrics AS source
            ON target.run_id = source.run_id
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """)
        
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC log_audit failed for {run_id}: {e}")
        self._write_local_fallback("abc_audit_metrics", audit_record)
```

### 6.5 log_balance() Implementation

```python
def log_balance(self, run_id: str, checks: List[Dict]):
    """Log balance checks (count + financial reconciliation)."""
    import uuid
    from datetime import datetime
    
    # Validate inputs
    if not run_id:
        raise ABCValidationError("run_id cannot be None or empty")
    
    if not checks:
        return  # Nothing to log
    
    # Add balance_id and timestamps to each check
    balance_records = []
    for check in checks:
        record = {
            "balance_id": str(uuid.uuid4()),
            "run_id": run_id,
            "created_ts": datetime.utcnow()
        }
        record.update(check)
        
        # Calculate variance if source_value and target_value provided
        if "source_value" in check and "target_value" in check:
            variance = check["source_value"] - check["target_value"]
            record["variance"] = variance
            
            # Calculate variance_percent
            if check["source_value"] != 0:
                variance_pct = (variance / check["source_value"]) * 100
                record["variance_percent"] = variance_pct
            
            # Determine if balanced (within threshold)
            threshold = check.get("threshold_percent", 0.01)  # Default 1%
            record["balanced"] = abs(variance_pct) <= threshold
        
        balance_records.append(record)
    
    try:
        # Insert into abc_balance
        df = self.spark.createDataFrame(balance_records)
        df.write.format("delta").mode("append").saveAsTable(
            f"{self.catalog}.{self.schema}.abc_balance"
        )
        
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC log_balance failed for {run_id}: {e}")
        for record in balance_records:
            self._write_local_fallback("abc_balance", record)
```

### 6.6 log_dq() Implementation

```python
def log_dq(self, run_id: str, results: List[Dict]):
    """Log DQ rule outcomes."""
    import uuid
    from datetime import datetime
    
    # Validate inputs
    if not run_id:
        raise ABCValidationError("run_id cannot be None or empty")
    
    if not results:
        return  # Nothing to log
    
    # Add control_id and timestamps to each result
    control_records = []
    for result in results:
        record = {
            "control_id": str(uuid.uuid4()),
            "run_id": run_id,
            "control_type": "DQ_RULE",
            "created_ts": datetime.utcnow()
        }
        record.update(result)
        control_records.append(record)
    
    try:
        # Insert into abc_control
        df = self.spark.createDataFrame(control_records)
        df.write.format("delta").mode("append").saveAsTable(
            f"{self.catalog}.{self.schema}.abc_control"
        )
        
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC log_dq failed for {run_id}: {e}")
        for record in control_records:
            self._write_local_fallback("abc_control", record)
```

### 6.7 log_exception() Implementation

```python
def log_exception(self, run_id: str, error: Exception):
    """Log structured exception."""
    import uuid
    import traceback
    from datetime import datetime
    
    # Validate inputs
    if not run_id:
        raise ABCValidationError("run_id cannot be None or empty")
    
    # Serialize exception
    control_record = {
        "control_id": str(uuid.uuid4()),
        "run_id": run_id,
        "control_type": "EXCEPTION",
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        "created_ts": datetime.utcnow()
    }
    
    try:
        # Insert into abc_control
        df = self.spark.createDataFrame([control_record])
        df.write.format("delta").mode("append").saveAsTable(
            f"{self.catalog}.{self.schema}.abc_control"
        )
        
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC log_exception failed for {run_id}: {e}")
        self._write_local_fallback("abc_control", control_record)
```

### 6.8 log_cost() Implementation

```python
def log_cost(self, run_id: str, consumption: Dict):
    """Log cost and consumption metrics."""
    import uuid
    from datetime import datetime
    
    # Validate inputs
    if not run_id:
        raise ABCValidationError("run_id cannot be None or empty")
    
    # Build cost record
    cost_record = {
        "cost_id": str(uuid.uuid4()),
        "run_id": run_id,
        "created_ts": datetime.utcnow()
    }
    cost_record.update(consumption)
    
    try:
        # Insert into abc_cost
        df = self.spark.createDataFrame([cost_record])
        df.write.format("delta").mode("append").saveAsTable(
            f"{self.catalog}.{self.schema}.abc_cost"
        )
        
    except Exception as e:
        # Resilience: log warning, write local fallback, continue
        self.logger.warning(f"ABC log_cost failed for {run_id}: {e}")
        self._write_local_fallback("abc_cost", cost_record)
```

### 6.9 Local Fallback Implementation

```python
def _write_local_fallback(self, table: str, data: Dict):
    """Write ABC entry to local JSON file if Delta write fails."""
    import json
    from pathlib import Path
    from datetime import datetime
    
    # Create fallback directory
    fallback_dir = Path("/tmp/abc_fallback")
    fallback_dir.mkdir(parents=True, exist_ok=True)
    
    # Write to timestamped file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = fallback_dir / f"{table}_{timestamp}.json"
    
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=str)
        self.logger.info(f"ABC fallback written: {filename}")
    except Exception as e:
        self.logger.error(f"ABC fallback write failed: {e}")
```

### 6.10 Resilience Strategy

**Development/Test Mode:**
- Raise exceptions immediately for ABC failures
- No local fallback
- Fail fast for debugging

**Production Mode (default):**
- Downgrade ABC errors to warnings
- Write to local JSON fallback
- Continue data pipeline (ABC failures don't crash pipelines)
- Log detailed error messages

**Implementation:**
```python
# In __init__:
self.production_mode = os.getenv("ABC_PRODUCTION_MODE", "true").lower() == "true"

# In each method:
try:
    # ABC write operation
    ...
except Exception as e:
    if self.production_mode:
        self.logger.warning(f"ABC write failed: {e}")
        self._write_local_fallback(table, record)
    else:
        raise ABCWriteError(f"ABC write failed: {e}") from e
```

---

## 7. Validation, edge cases & versioning

### Validation Rules

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

## 8. Error handling

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

## 9. Testing & acceptance

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

**Scenario 1: Happy path**  
**Given:** Valid Spark session and ABC tables exist  
**When:** Call start_run(), log_audit(), end_run()  
**Then:** Entries written to abc_audit table, run marked SUCCESS

**Scenario 2: ABC write failure**  
**Given:** ABC table write fails (permissions issue)  
**When:** Call log_audit()  
**Then:** Warning logged, local file written, pipeline continues

**Scenario 3: Idempotent re-run**  
**Given:** Run already exists with same run_id  
**When:** Call end_run() again with same run_id  
**Then:** Update existing row, do not duplicate

**Scenario 4: Trace ID propagation**  
**Given:** start_run() called with trace_id  
**When:** Pass trace_id to downstream components  
**Then:** All logs share same trace_id for lineage

---

## 10. Examples

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

### Example 3: Counter-Example - Blocking on ABC failure (DON'T DO)

```python
# BAD: Let ABC failures crash the data pipeline
abc = ABC()
run = abc.start_run("ingestion", "policy", "BATCH")

try:
    # Ingestion logic
    df.write.saveAsTable("insurelake.bronze.policy")
    
    # BAD: Raise if ABC write fails
    abc.log_audit(run.run_id, metrics)  # Crashes pipeline if ABC unavailable
except Exception as e:
    raise  # Pipeline fails even if ingestion succeeded

# CORRECT: ABC errors should warn, not fail
try:
    abc.log_audit(run.run_id, metrics)
except ABCWriteError as e:
    logger.warning(f"ABC logging failed: {e}")
    # Continue - data pipeline success is independent of ABC
```

---

## 12. Regeneration contract

**Code generation scope:**
1. **ABC class skeleton**: Generate class with 7 method signatures
2. **Table writers**: Generate DeltaAuditWriter, DeltaBalanceWriter, etc.
3. **Exception classes**: Generate ABCConnectionError, ABCWriteError, ABCValidationError
4. **Unit test scaffolding**: Generate test class with mock Spark fixtures

**Generation inputs:**
- This spec (markdown)
- ABC table DDL (§5 Data Model)
- Method signatures (§3 Interface)

**Generation outputs:**
- `abc.py` — ABC class
- `writers/` — Table writer classes
- `exceptions.py` — Exception classes
- `models/run_handle.py` — RunHandle dataclass
- `tests/test_abc.py` — Unit test skeleton

**Regeneration rules:**
- **Safe to regenerate**: Method signatures, exception classes, test scaffolding
- **Not safe to regenerate**: Business logic inside methods, custom validation
- **Partial regeneration**: Update only method signatures when adding new log types

---

## 13. References

### Dependencies
- None (foundation component)

### External References
- [FND-010_abc-sdk-interface-spec.md](FND-010_abc-sdk-interface-spec.md) - ABC SDK interface specification
- [FND-001_config-model-spec.md](FND-001_config-model-spec.md) - Config metadata model
- [FND-003-COMPLETE.md](../FND-003-COMPLETE.md) - Config Loader SDK (reference implementation)
- [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) - Project principles and roadmap
- Databricks system tables: `system.billing.usage` for cost data
- Unity Catalog audit logs

### Related Specs
- **config-model-spec.md** — Config entities that engines log through ABC
- **ingestion-engine-spec.md** — Primary consumer of ABC SDK
- **harmonization-engine-spec.md** — Secondary consumer of ABC SDK
- **dq-engine-spec.md** — Logs DQ results through ABC

---

**END OF SPEC**
