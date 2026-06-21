---
id: dataio.load_strategy.full-refresh-strategy
title: Full Refresh Strategy Spec
owner: EY
status: draft
target_path: src/load_strategy/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/load_strategy/full-refresh-strategy-spec.md
acceptance:
  - "pytest tests/unit/test_full_refresh_strategy.py"
regeneration: scaffold-then-edit
---

# Full Refresh Strategy Spec

## 1. Purpose

Implement the **LoadStrategy protocol** for **Full Refresh**, enabling the framework to completely replace table contents with new data (truncate and reload).

**Full Refresh characteristics:**
* **Complete replacement** — delete all existing rows, write new data
* **Simple semantics** — truncate (or overwrite) + append
* **ACID guarantees** — Delta ensures atomic replace
* **Use cases** — small reference tables, daily snapshots, complete rebuilds

**Full Refresh logic:**
1. **Truncate** — delete all existing rows (or overwrite mode)
2. **Load** — write new data
3. **Atomic** — Delta ensures no intermediate state visible

**Key capabilities:**
* Overwrite mode for complete replacement
* Support for partitioned overwrite (replace specific partitions)
* ACID guarantees via Delta Lake
* Support for declarative and imperative modes

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements LoadStrategy protocol from engine-contracts-spec
* Uses Delta overwrite mode for atomic replace
* Returns write metrics (rows written)
* ABC balance hooks for row count validation

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (LoadStrategy protocol, Delta Lake)
* **ROADMAP.md Phase 0** — full refresh strategy is Wave 1 foundation
* **metadata-models-spec.md** — LoadStrategy enum
* **engine-contracts-spec.md** — LoadStrategy protocol definition
* **Backlog tasks:** DATAIO-013, LOADSTRAT-004

### 2.2 Design Constraints
* **Protocol compliance** — implement LoadStrategy protocol (write, supports_execution_mode, generate_ddl)
* **Primary keys optional** — full refresh doesn't need primary keys (complete replace)
* **Delta overwrite** — use Delta's overwrite mode for atomic replace
* **Partitioned overwrite** — support replacing specific partitions

---

## 3. Procedure

### 3.1 FullRefreshStrategy Implementation

**Purpose:** Replace all table data atomically

```python
# dataio/load_strategy/full_refresh_strategy.py
from typing import Optional, Dict, Any
import time
from pyspark.sql import DataFrame

from core.contracts import LoadStrategy
from core.metadata import LoadStrategy as LoadStrategyEnum
from dataio.load_strategy import register_load_strategy

@register_load_strategy(LoadStrategyEnum.FULL_REFRESH)
class FullRefreshStrategy(LoadStrategy):
    """
    Full Refresh load strategy.
    
    Completely replaces table contents with new data.
    Uses Delta overwrite mode for atomic replacement.
    
    Use cases:
    - Small reference tables (< 1M rows)
    - Daily snapshots
    - Complete rebuilds
    - Tables where history not needed
    
    Performance considerations:
    - Rewrites entire table (expensive for large tables)
    - Use SCD1/SCD2 for incremental updates
    - Use append for event logs
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
        Overwrite target table with source DataFrame.
        
        Args:
            df: Source DataFrame to write
            target_table_fqn: Fully qualified target table name (catalog.schema.table)
            primary_keys: Primary key columns (not used for full refresh, but required by protocol)
            partition_columns: Optional partition columns
            execution_mode: "declarative" (Lakeflow SDP) or "imperative" (PySpark)
            
        Returns:
            dict with write metrics:
                {
                    "rows_written": int,
                    "rows_updated": 0,  # Always 0 (not an update)
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
            # Note: Full refresh in Lakeflow SDP uses COMPLETE mode
            # This is a placeholder for imperative fallback
            self._write_imperative(df, target_table_fqn, partition_columns)
        
        duration = time.time() - start_time
        
        return {
            "rows_written": row_count,
            "rows_updated": 0,  # Full refresh doesn't update
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
        Write DataFrame using imperative PySpark API with overwrite mode.
        
        Args:
            df: Source DataFrame
            target_table_fqn: Fully qualified table name
            partition_columns: Optional partition columns
        """
        writer = df.write.format("delta").mode("overwrite")
        
        # Dynamic partition overwrite if partitions specified
        if partition_columns:
            # Enable dynamic partition overwrite
            # This only overwrites partitions present in the source DataFrame
            writer = writer.option("partitionOverwriteMode", "dynamic") \
                .partitionBy(*partition_columns)
        
        # Write to table
        writer.saveAsTable(target_table_fqn)
    
    def supports_execution_mode(self, execution_mode: str) -> bool:
        """
        Check if this strategy supports the given execution mode.
        
        Args:
            execution_mode: "declarative" or "imperative"
            
        Returns:
            True if mode is supported
        """
        # Full refresh works for both modes
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

# Read source data (complete snapshot)
source_df = spark.read.format("csv").load("/Volumes/main/raw/product_catalog/")

# Get full refresh strategy
strategy = get_load_strategy(LoadStrategyEnum.FULL_REFRESH)

# Overwrite table completely
metrics = strategy.write(
    df=source_df,
    target_table_fqn="main.silver.product_catalog",
    primary_keys=[],  # Not used for full refresh
    partition_columns=["category"],
    execution_mode="imperative"
)

print(f"Replaced table with {metrics['rows_written']} rows")
```

**Declarative mode (Lakeflow SDP):**
```sql
-- In Lakeflow SDP pipeline
CREATE OR REFRESH STREAMING TABLE silver.product_catalog
AS SELECT * FROM STREAM(bronze.product_catalog_raw)
-- Note: COMPLETE output mode (not available for STREAMING TABLE)
-- Use materialized view instead:

CREATE OR REFRESH MATERIALIZED VIEW silver.product_catalog
AS SELECT * FROM bronze.product_catalog_raw
```

---

### 3.3 Dynamic Partition Overwrite

**Purpose:** Replace only partitions present in source data

```python
# Source data has only 2024-01 partition
source_df = spark.read.format("csv") \
    .load("/Volumes/main/raw/sales/2024-01/")

# Only overwrites 2024-01 partition
# Other partitions (2023-12, 2023-11, etc.) remain intact
strategy = get_load_strategy(LoadStrategyEnum.FULL_REFRESH)
strategy.write(
    df=source_df,
    target_table_fqn="main.silver.sales",
    primary_keys=[],
    partition_columns=["month"],  # Enables dynamic partition overwrite
    execution_mode="imperative"
)
```

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/load_strategy/full_refresh_strategy.py`** — FullRefreshStrategy implementation
* **`dataio/load_strategy/__init__.py`** — Factory registration (extends pattern)
* **Unit tests** — test overwrite, dynamic partition overwrite, metrics
* **Integration tests** — test end-to-end full refresh to Delta table

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_load_strategy(LoadStrategy.FULL_REFRESH) for reference tables
* **Config-driven pipelines** — YAML configs specify load_strategy: full_refresh

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
* **Write failure** — re-raise with context (table name, row count)

### 5.2 Edge Cases
* **Empty DataFrame** — overwrite with 0 rows (table becomes empty)
* **Partitioned overwrite** — only partitions in source are replaced
* **Non-partitioned overwrite** — entire table replaced
* **Concurrent writes** — Delta handles optimistic concurrency control

### 5.3 Performance Considerations
* **Expensive for large tables** — rewrites entire table (or partitions)
* **Use append for incremental** — full refresh only for complete snapshots
* **Use SCD1/SCD2 for updates** — full refresh not suitable for incremental changes
* **Optimize after overwrite** — Delta automatically compacts files

---

## 6. ABC Hooks

### 6.1 Audit
* **Overwrite operations** — audit before and after:
  ```python
  abc_sdk.audit(event="full_refresh_start", table_fqn=target_table_fqn, rows=row_count)
  # ... write ...
  abc_sdk.audit(event="full_refresh_success", table_fqn=target_table_fqn, metrics=metrics)
  ```

### 6.2 Balance
* **Row count validation** — compare source and target after write:
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
* **DBU consumption** — track overwrite operations:
  ```python
  abc_sdk.cost_track(
      operation="full_refresh",
      table_fqn=target_table_fqn,
      rows_processed=metrics["rows_written"],
      duration_seconds=metrics["duration_seconds"]
  )
  ```

### 6.4 Logging
* **Structured logging** — log overwrite operations:
  ```python
  logger.info(f"Full refresh of {target_table_fqn}", extra={
      "trace_id": trace_id,
      "row_count": row_count,
      "partition_columns": partition_columns
  })
  ```

---

## 7. Examples

### 7.1 Basic Full Refresh
```python
from pyspark.sql import SparkSession
from dataio.load_strategy import get_load_strategy
from core.metadata import LoadStrategy as LoadStrategyEnum

spark = SparkSession.builder.appName("FullRefreshExample").getOrCreate()

# Create sample data (product catalog)
data = [
    ("PROD001", "Product A", "Category 1", 100.0),
    ("PROD002", "Product B", "Category 2", 150.0)
]
columns = ["product_id", "product_name", "category", "price"]
df = spark.createDataFrame(data, columns)

# Full refresh
strategy = get_load_strategy(LoadStrategyEnum.FULL_REFRESH)
metrics = strategy.write(
    df=df,
    target_table_fqn="main.silver.product_catalog",
    primary_keys=[],  # Not used
    partition_columns=None,
    execution_mode="imperative"
)

print(f"✅ Full refresh: {metrics['rows_written']} rows")
```

### 7.2 Dynamic Partition Overwrite
```python
# Initial load with 2 partitions
jan_data = [("TXN001", "2024-01-15", 100.0)]
feb_data = [("TXN002", "2024-02-20", 200.0)]
all_data = jan_data + feb_data
columns = ["txn_id", "txn_date", "amount"]
initial_df = spark.createDataFrame(all_data, columns)

# Initial load
strategy.write(
    df=initial_df,
    target_table_fqn="main.silver.transactions",
    primary_keys=[],
    partition_columns=["txn_date"],
    execution_mode="imperative"
)

# Check table
spark.sql("SELECT * FROM main.silver.transactions ORDER BY txn_date").show()
# +-------+----------+------+
# |txn_id |txn_date  |amount|
# +-------+----------+------+
# |TXN001 |2024-01-15|100.0 |
# |TXN002 |2024-02-20|200.0 |
# +-------+----------+------+

# Overwrite only January partition
jan_update = [("TXN003", "2024-01-25", 300.0)]
jan_df = spark.createDataFrame(jan_update, columns)

strategy.write(
    df=jan_df,
    target_table_fqn="main.silver.transactions",
    primary_keys=[],
    partition_columns=["txn_date"],  # Dynamic partition overwrite
    execution_mode="imperative"
)

# February partition unchanged, January replaced
spark.sql("SELECT * FROM main.silver.transactions ORDER BY txn_date").show()
# +-------+----------+------+
# |txn_id |txn_date  |amount|
# +-------+----------+------+
# |TXN003 |2024-01-25|300.0 |  # January replaced
# |TXN002 |2024-02-20|200.0 |  # February unchanged
# +-------+----------+------+
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **Basic overwrite** — test write() replaces all data
2. **Empty DataFrame** — test 0 rows written (table becomes empty)
3. **DDL generation** — test generate_ddl() produces valid SQL
4. **Execution modes** — test supports_execution_mode()
5. **Metrics** — test returned metrics (rows_written)
6. **Dynamic partition overwrite** — test partitioned overwrite

### 8.2 Integration Tests
* **End-to-end full refresh** — overwrite table, verify data replaced
* **Partitioned overwrite** — replace specific partitions, verify others intact

### 8.3 Regression Tests
* **Concurrent writes** — verify optimistic concurrency control works

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — LoadStrategy protocol
* `metadata-models-spec.md` — LoadStrategy enum
* `PROJECT_CONTEXT.md` §4 — architecture decisions

### 9.2 External Standards
* **Delta Lake overwrite** — https://docs.delta.io/latest/delta-batch.html#overwrite

### 9.3 Databricks Documentation
* **Delta overwrite** — https://docs.databricks.com/aws/en/delta/merge.html#overwrite-mode
* **Dynamic partition overwrite** — https://docs.databricks.com/aws/en/delta/partitions.html#dynamic-partition-overwrite

---

## 10. Decisions Made

All design decisions:

1. **Mode** — always use overwrite mode (complete replace)
2. **Primary keys** — accepted by protocol but not used (complete replace doesn't need PKs)
3. **Execution modes** — support both declarative and imperative
4. **DDL generation** — CREATE TABLE IF NOT EXISTS for idempotency
5. **Dynamic partition overwrite** — enable via partitionOverwriteMode=dynamic
6. **Metrics** — return rows_written, rows_inserted (equal), rows_updated (0)
7. **Partitioning** — apply partitionBy() if partition_columns specified
8. **Row count** — materialize DataFrame via .count() for metrics

---

**End of Full Refresh Strategy Spec (Approved)**
