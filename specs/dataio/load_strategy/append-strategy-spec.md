---
id: dataio.load_strategy.append-strategy
title: Append Strategy Spec
owner: EY
status: draft
target_path: src/load_strategy/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/load_strategy/append-strategy-spec.md
acceptance:
  - "pytest tests/unit/test_append_strategy.py"
regeneration: scaffold-then-edit
---

# Append Strategy Spec

## 1. Purpose

Implement the **LoadStrategy protocol** for append-only data loading, enabling the framework to write new rows to Delta tables without modifying existing data.

**Append strategy characteristics:**
* **No deduplication** — all rows are appended, including duplicates
* **No updates/deletes** — existing rows never modified
* **Simple semantics** — fast writes, no MERGE required
* **Use cases** — fact tables, event logs, audit trails, immutable data

**Key capabilities:**
* Write to Delta tables (create if not exists)
* Support partitioning for query performance
* Dual execution modes (imperative PySpark, declarative Lakeflow SDP)
* Metrics tracking (rows written, duration)

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements LoadStrategy protocol from engine-contracts-spec
* Returns write metrics dict
* Supports both imperative and declarative execution modes
* ABC balance hooks for row count validation

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (LoadStrategy protocol, dual execution modes)
* **ROADMAP.md Phase 0** — append strategy is Wave 1 foundation
* **metadata-models-spec.md** — LoadStrategy enum
* **engine-contracts-spec.md** — LoadStrategy protocol definition
* **Backlog tasks:** DATAIO-010, LOADSTRAT-001

### 2.2 Design Constraints
* **Protocol compliance** — implement LoadStrategy protocol (write, supports_execution_mode, generate_ddl)
* **Delta Lake format** — all writes use Delta for ACID guarantees
* **Idempotent DDL** — CREATE TABLE IF NOT EXISTS
* **Mode** — always use append mode (never overwrite)
* **Performance** — leverage Delta's optimized append path

---

## 3. Procedure

### 3.1 AppendStrategy Implementation

**Purpose:** Append new rows to target table without modifications

```python
# dataio/load_strategy/append_strategy.py
from typing import Optional, Dict, Any
import time
from pyspark.sql import DataFrame

from core.contracts import LoadStrategy
from core.metadata import LoadStrategy as LoadStrategyEnum
from dataio.load_strategy import register_load_strategy

@register_load_strategy(LoadStrategyEnum.APPEND)
class AppendStrategy(LoadStrategy):
    """
    Append-only load strategy.
    
    Writes all rows to target table without modifications.
    No deduplication, no updates, no deletes.
    
    Use cases:
    - Fact tables (transactions, events)
    - Audit logs
    - Immutable data
    - Bronze layer ingestion
    """
    
    def write(
        self,
        df: DataFrame,
        target_table_fqn: str,
        primary_keys: list[str],
        partition_columns: Optional[list[str]] = None,
        execution_mode: str = "imperative"
    ) -> Dict[str, Any]:
        """
        Append DataFrame rows to target table.
        
        Args:
            df: Source DataFrame to write
            target_table_fqn: Fully qualified target table name (catalog.schema.table)
            primary_keys: Primary key columns (not used for append, but required by protocol)
            partition_columns: Optional partition columns
            execution_mode: "declarative" (Lakeflow SDP) or "imperative" (PySpark)
            
        Returns:
            dict with write metrics:
                {
                    "rows_written": int,
                    "rows_updated": 0,  # Always 0 for append
                    "rows_inserted": int,  # Same as rows_written
                    "duration_seconds": float
                }
                
        Raises:
            ValueError: If execution_mode not supported
        """
        if not self.supports_execution_mode(execution_mode):
            raise ValueError(f"Execution mode not supported: {execution_mode}")
        
        start_time = time.time()
        
        # Count rows (materialize DataFrame)
        row_count = df.count()
        
        # Write based on execution mode
        if execution_mode == "imperative":
            self._write_imperative(df, target_table_fqn, partition_columns)
        else:
            # Declarative mode (Lakeflow SDP)
            # Note: In Lakeflow SDP, writes are defined via SQL, not Python
            # This is a placeholder for imperative fallback
            self._write_imperative(df, target_table_fqn, partition_columns)
        
        duration = time.time() - start_time
        
        return {
            "rows_written": row_count,
            "rows_updated": 0,  # Append doesn't update
            "rows_inserted": row_count,
            "duration_seconds": duration
        }
    
    def _write_imperative(
        self,
        df: DataFrame,
        target_table_fqn: str,
        partition_columns: Optional[list[str]] = None
    ) -> None:
        """
        Write DataFrame using imperative PySpark API.
        
        Args:
            df: Source DataFrame
            target_table_fqn: Fully qualified table name
            partition_columns: Optional partition columns
        """
        writer = df.write.format("delta").mode("append")
        
        # Apply partitioning if specified
        if partition_columns:
            writer = writer.partitionBy(*partition_columns)
        
        # Write to table
        writer.saveAsTable(target_table_fqn)
    
    def supports_execution_mode(self, execution_mode: str) -> bool:
        """
        Check if this strategy supports the given execution mode.
        
        Args:
            execution_mode: "declarative" or "imperative"
            
        Returns:
            True if mode is supported, False otherwise
        """
        # Append works for both modes
        return execution_mode in ("declarative", "imperative")
    
    def generate_ddl(
        self,
        target_table_fqn: str,
        df: DataFrame,
        partition_columns: Optional[list[str]] = None
    ) -> str:
        """
        Generate CREATE TABLE DDL for the target table.
        
        Args:
            target_table_fqn: Fully qualified table name
            df: Sample DataFrame to infer schema
            partition_columns: Optional partition columns
            
        Returns:
            SQL CREATE TABLE statement
        """
        # Get schema from DataFrame
        schema_ddl = self._generate_schema_ddl(df.schema)
        
        # Build CREATE TABLE statement
        ddl = f"CREATE TABLE IF NOT EXISTS {target_table_fqn} ({schema_ddl}) USING DELTA"
        
        # Add partitioning if specified
        if partition_columns:
            ddl += f" PARTITIONED BY ({', '.join(partition_columns)})"
        
        return ddl
    
    def _generate_schema_ddl(self, schema) -> str:
        """
        Convert PySpark schema to SQL DDL column definitions.
        
        Args:
            schema: PySpark StructType
            
        Returns:
            SQL column definitions (e.g., "col1 STRING, col2 INT")
        """
        columns = []
        for field in schema.fields:
            col_def = f"{field.name} {field.dataType.simpleString().upper()}"
            if not field.nullable:
                col_def += " NOT NULL"
            columns.append(col_def)
        
        return ", ".join(columns)
```

---

### 3.2 Usage Patterns

**Imperative mode (PySpark):**
```python
from dataio.load_strategy import get_load_strategy
from core.metadata import LoadStrategy as LoadStrategyEnum

# Read source data
source_df = spark.read.format("csv").load("/Volumes/main/raw/policies/")

# Get append strategy
strategy = get_load_strategy(LoadStrategyEnum.APPEND)

# Write to Bronze table
metrics = strategy.write(
    df=source_df,
    target_table_fqn="main.bronze.policy_raw",
    primary_keys=["policy_id"],  # Not used for append, but required by protocol
    partition_columns=["effective_date"],
    execution_mode="imperative"
)

print(f"Appended {metrics['rows_written']} rows in {metrics['duration_seconds']:.2f}s")
```

**Declarative mode (Lakeflow SDP):**
```sql
-- In Lakeflow SDP pipeline
CREATE OR REFRESH STREAMING TABLE bronze.policy_raw
PARTITIONED BY (effective_date)
AS SELECT * FROM STREAM(main.raw.policies_stream)
```

---

### 3.3 DDL Generation

**Generate CREATE TABLE DDL:**
```python
strategy = get_load_strategy(LoadStrategyEnum.APPEND)

# Generate DDL from sample DataFrame
ddl = strategy.generate_ddl(
    target_table_fqn="main.bronze.policy_raw",
    df=source_df,
    partition_columns=["effective_date"]
)

print(ddl)
# Output:
# CREATE TABLE IF NOT EXISTS main.bronze.policy_raw (
#   policy_id STRING,
#   policy_number STRING,
#   effective_date DATE,
#   premium DOUBLE
# ) USING DELTA
# PARTITIONED BY (effective_date)

# Execute DDL
spark.sql(ddl)
```

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/load_strategy/append_strategy.py`** — AppendStrategy implementation
* **`dataio/load_strategy/__init__.py`** — Factory registration (extends pattern from engine-contracts-spec)
* **Unit tests** — test append write, DDL generation, metrics
* **Integration tests** — test end-to-end append to Delta table

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_load_strategy(LoadStrategy.APPEND) to write Bronze tables
* **Config-driven pipelines** — YAML configs specify load_strategy: append

---

## 5. Guardrails

### SOLID Principles Application

**Single Responsibility Principle (SRP):**
- Each component/class has ONE reason to change
- Separate concerns: reading, transformation, writing, validation

**Open/Closed Principle (OCP):**
- Open for extension via new implementations
- Closed for modification of existing interfaces

**Liskov Substitution Principle (LSP):**
- Subclasses/implementations are substitutable for their base protocol
- All implementations honor the same contract

**Interface Segregation Principle (ISP):**
- Clients depend only on methods they use
- Separate protocols for different concerns (Reader, LoadStrategy, Engine, Check, Masker)

**Dependency Inversion Principle (DIP):**
- Depend on abstractions (protocols), not concrete implementations
- High-level modules don't depend on low-level details



### 5.1 Error Handling
* **Table not found** — CREATE TABLE IF NOT EXISTS ensures table exists
* **Schema mismatch** — Delta Lake handles schema evolution (addColumns, overwriteSchema)
* **Partition column missing** — PySpark raises AnalysisException with clear message
* **Write failure** — re-raise with context (table name, row count)

### 5.2 Edge Cases
* **Empty DataFrame** — append succeeds with 0 rows written
* **Duplicate rows** — all rows appended, including duplicates (no deduplication)
* **Schema evolution** — Delta merges schemas if mergeSchema=true (not default)
* **Concurrent writes** — Delta handles optimistic concurrency control

### 5.3 Performance Considerations
* **Append-only path** — Delta's append is fast, no MERGE overhead
* **Partitioning** — reduces query time via partition pruning
* **Small files** — frequent small appends create many files; run OPTIMIZE periodically
* **Statistics** — Delta automatically collects statistics for query optimization

---

## 6. ABC Hooks

### 6.1 Audit
* **Write operations** — audit before and after write:
  ```python
  abc_sdk.audit(event="append_start", table_fqn=target_table_fqn, rows=row_count)
  # ... write ...
  abc_sdk.audit(event="append_success", table_fqn=target_table_fqn, metrics=metrics)
  ```

### 6.2 Balance
* **Row count validation** — compare source and target counts:
  ```python
  abc_sdk.balance(
      check_type="row_count",
      source="source_df",
      target=target_table_fqn,
      source_count=source_df.count(),
      target_count=spark.table(target_table_fqn).count()
  )
  ```

### 6.3 Cost Tracking
* **DBU consumption** — track write operations:
  ```python
  abc_sdk.cost_track(
      operation="append",
      table_fqn=target_table_fqn,
      rows_processed=metrics["rows_written"],
      duration_seconds=metrics["duration_seconds"]
  )
  ```

### 6.4 Logging
* **Structured logging** — log write operations:
  ```python
  logger.info(f"Appending to {target_table_fqn}", extra={
      "trace_id": trace_id,
      "row_count": row_count,
      "partition_columns": partition_columns
  })
  ```

---

## 7. Examples

### 7.1 Basic Append
```python
from pyspark.sql import SparkSession
from dataio.load_strategy import get_load_strategy
from core.metadata import LoadStrategy as LoadStrategyEnum

spark = SparkSession.builder.appName("AppendExample").getOrCreate()

# Create sample data
data = [
    ("POL001", "12345", "2024-01-01", 1000.0),
    ("POL002", "12346", "2024-01-02", 1500.0)
]
columns = ["policy_id", "policy_number", "effective_date", "premium"]
df = spark.createDataFrame(data, columns)

# Append to table
strategy = get_load_strategy(LoadStrategyEnum.APPEND)
metrics = strategy.write(
    df=df,
    target_table_fqn="main.bronze.policy_raw",
    primary_keys=["policy_id"],
    partition_columns=["effective_date"],
    execution_mode="imperative"
)

print(f"✅ Appended {metrics['rows_written']} rows")
```

### 7.2 Append with DDL Generation
```python
# Generate DDL if table doesn't exist
ddl = strategy.generate_ddl(
    target_table_fqn="main.bronze.claim_raw",
    df=claim_df,
    partition_columns=["claim_date"]
)

spark.sql(ddl)  # Create table

# Append data
metrics = strategy.write(
    df=claim_df,
    target_table_fqn="main.bronze.claim_raw",
    primary_keys=["claim_id"],
    partition_columns=["claim_date"],
    execution_mode="imperative"
)
```

### 7.3 Streaming Append
```python
# Read streaming data
streaming_df = spark.readStream.format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.schemaLocation", "/tmp/schema") \
    .load("/Volumes/main/raw/claims/")

# Append strategy doesn't directly handle streaming writes
# Use streaming writeStream API instead
query = streaming_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .toTable("main.bronze.claim_raw")

query.awaitTermination()
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **Basic append** — test write() with simple DataFrame
2. **Partition columns** — test partitionBy() applied correctly
3. **Empty DataFrame** — test 0 rows written
4. **DDL generation** — test generate_ddl() produces valid SQL
5. **Execution modes** — test supports_execution_mode() for declarative/imperative
6. **Metrics** — test returned metrics dict (rows_written, duration)

### 8.2 Integration Tests
* **End-to-end append** — write to Delta table, verify rows exist
* **Partitioning** — verify partitions created correctly
* **Schema evolution** — append with new column, verify Delta merges schema

### 8.3 Regression Tests
* **Duplicate appends** — verify all rows appended (no deduplication)
* **Concurrent writes** — verify optimistic concurrency control works

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — LoadStrategy protocol definition
* `metadata-models-spec.md` — LoadStrategy enum
* `PROJECT_CONTEXT.md` §4 — architecture decisions

### 9.2 External Standards
* **PySpark DataFrameWriter** — https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrameWriter.html
* **Delta Lake** — https://docs.delta.io/latest/delta-batch.html

### 9.3 Databricks Documentation
* **Delta Lake append** — https://docs.databricks.com/aws/en/delta/merge.html
* **Partitioning** — https://docs.databricks.com/aws/en/tables/partitions.html

---

## 10. Decisions Made

All design decisions:

1. **Mode** — always use append mode (never overwrite)
2. **Primary keys** — accepted by protocol but not used (no MERGE for append)
3. **Execution modes** — support both declarative and imperative (imperative implemented first)
4. **DDL generation** — CREATE TABLE IF NOT EXISTS for idempotency
5. **Schema DDL** — convert PySpark StructType to SQL column definitions
6. **Metrics** — return rows_written, rows_inserted (equal), rows_updated (0)
7. **Partitioning** — apply partitionBy() if partition_columns specified
8. **Row count** — materialize DataFrame via .count() for metrics (accept performance cost)

---

**End of Append Strategy Spec (Approved)**
