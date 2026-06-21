---
id: dataio.load_strategy.scd2-strategy
title: SCD2 Strategy Spec
owner: EY
status: draft
target_path: src/load_strategy/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/load_strategy/scd2-strategy-spec.md
acceptance:
  - "pytest tests/unit/test_scd2_strategy.py"
regeneration: scaffold-then-edit
---

# SCD2 Strategy Spec

## 1. Purpose

Implement the **LoadStrategy protocol** for **Slowly Changing Dimension Type 2 (SCD2)**, enabling the framework to maintain full historical records with effective date ranges.

**SCD2 characteristics:**
* **Full history tracking** — every change creates a new row with date range
* **Effective dates** — `effective_start_date`, `effective_end_date`, `is_current` flag
* **No deletes** — expired records marked with `is_current = false`
* **Use cases** — customer dimensions, product catalogs, policy master data

**SCD2 logic:**
1. **New records** — insert with `is_current = true`, `effective_end_date = 9999-12-31`
2. **Changed records** — expire old row (`is_current = false`, set `effective_end_date`), insert new row
3. **Unchanged records** — no action

**Key capabilities:**
* Delta MERGE for upsert semantics
* Automatic effective date management
* Primary key matching for change detection
* Support for declarative and imperative modes

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements LoadStrategy protocol from engine-contracts-spec
* Uses Delta MERGE for ACID guarantees
* Returns write metrics (rows inserted, rows updated)
* ABC balance hooks for row count validation

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (LoadStrategy protocol, Delta MERGE)
* **ROADMAP.md Phase 0** — SCD2 strategy is Wave 1 core capability
* **metadata-models-spec.md** — LoadStrategy enum
* **engine-contracts-spec.md** — LoadStrategy protocol definition
* **Backlog tasks:** DATAIO-012, LOADSTRAT-003

### 2.2 Design Constraints
* **Protocol compliance** — implement LoadStrategy protocol (write, supports_execution_mode, generate_ddl)
* **Primary keys required** — SCD2 requires primary keys for change detection
* **Date columns** — add `effective_start_date`, `effective_end_date`, `is_current` to target table
* **Delta MERGE** — use Delta's MERGE for upsert semantics
* **Performance** — optimize for large dimension tables (millions of rows)

---

## 3. Procedure

### 3.1 SCD2Strategy Implementation

**Purpose:** Maintain full history with effective dates

```python
# dataio/load_strategy/scd2_strategy.py
from typing import Optional, Dict, Any
import time
from datetime import date, datetime
from pyspark.sql import DataFrame, functions as F

from core.contracts import LoadStrategy
from core.metadata import LoadStrategy as LoadStrategyEnum
from dataio.load_strategy import register_load_strategy

@register_load_strategy(LoadStrategyEnum.SCD2)
class SCD2Strategy(LoadStrategy):
    """
    Slowly Changing Dimension Type 2 (SCD2) load strategy.
    
    Maintains full history by:
    - Inserting new records with is_current = true
    - Expiring changed records (is_current = false, set effective_end_date)
    - Inserting new versions of changed records
    
    Adds three columns to target table:
    - effective_start_date: When this version became effective
    - effective_end_date: When this version expired (9999-12-31 for current)
    - is_current: Boolean flag for current version
    
    Use cases:
    - Customer dimensions
    - Product catalogs
    - Policy master data
    - Any dimension requiring history tracking
    """
    
    # SCD2 date constants
    MAX_DATE = date(9999, 12, 31)
    
    def write(
        self,
        df: DataFrame,
        target_table_fqn: str,
        primary_keys: list[str],
        partition_columns: Optional[list[str]] = None,
        execution_mode: str = "imperative"
    ) -> Dict[str, Any]:
        """
        Apply SCD2 logic to merge source DataFrame into target table.
        
        Args:
            df: Source DataFrame to merge
            target_table_fqn: Fully qualified target table name (catalog.schema.table)
            primary_keys: Primary key columns (REQUIRED for SCD2)
            partition_columns: Optional partition columns
            execution_mode: "declarative" (Lakeflow SDP) or "imperative" (PySpark)
            
        Returns:
            dict with write metrics:
                {
                    "rows_written": int,  # Total rows written (inserts)
                    "rows_updated": int,  # Rows expired (updated is_current = false)
                    "rows_inserted": int,  # New rows inserted
                    "duration_seconds": float
                }
                
        Raises:
            ValueError: If primary_keys empty, execution_mode not supported, or table not found
        """
        if not primary_keys:
            raise ValueError("SCD2 strategy requires primary_keys for change detection")
        
        if not self.supports_execution_mode(execution_mode):
            raise ValueError(f"Execution mode not supported: {execution_mode}")
        
        start_time = time.time()
        
        # Add SCD2 columns to source DataFrame
        source_with_scd2 = self._prepare_source_df(df)
        
        # Count source rows for metrics
        source_count = source_with_scd2.count()
        
        # Write based on execution mode
        if execution_mode == "imperative":
            metrics = self._write_imperative(
                source_with_scd2,
                target_table_fqn,
                primary_keys,
                partition_columns
            )
        else:
            # Declarative mode (Lakeflow SDP)
            # Note: SCD2 in Lakeflow SDP uses APPLY CHANGES INTO
            # This is a placeholder for imperative fallback
            metrics = self._write_imperative(
                source_with_scd2,
                target_table_fqn,
                primary_keys,
                partition_columns
            )
        
        duration = time.time() - start_time
        metrics["duration_seconds"] = duration
        
        return metrics
    
    def _prepare_source_df(self, df: DataFrame) -> DataFrame:
        """
        Add SCD2 columns to source DataFrame.
        
        Args:
            df: Source DataFrame
            
        Returns:
            DataFrame with SCD2 columns added
        """
        current_date = F.current_date()
        
        return df \
            .withColumn("effective_start_date", current_date) \
            .withColumn("effective_end_date", F.lit(self.MAX_DATE)) \
            .withColumn("is_current", F.lit(True))
    
    def _write_imperative(
        self,
        source_df: DataFrame,
        target_table_fqn: str,
        primary_keys: list[str],
        partition_columns: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply SCD2 using Delta MERGE.
        
        SCD2 MERGE logic:
        1. MATCHED + changed → UPDATE old row (set is_current = false, effective_end_date)
        2. MATCHED + changed → INSERT new row (with new data)
        3. NOT MATCHED → INSERT new row
        
        Args:
            source_df: Source DataFrame with SCD2 columns
            target_table_fqn: Fully qualified table name
            primary_keys: Primary key columns
            partition_columns: Optional partition columns
            
        Returns:
            dict with metrics (rows_written, rows_updated, rows_inserted)
        """
        from delta.tables import DeltaTable
        
        spark = source_df.sparkSession
        
        # Check if target table exists
        try:
            target_delta = DeltaTable.forName(spark, target_table_fqn)
        except Exception:
            # Table doesn't exist, create it with first load
            return self._initial_load(source_df, target_table_fqn, partition_columns)
        
        # Build join condition for primary keys
        join_condition = " AND ".join([
            f"target.{pk} = source.{pk}" for pk in primary_keys
        ])
        
        # Build change detection condition (all non-PK columns differ)
        # Get all columns except primary keys and SCD2 columns
        non_pk_columns = [
            col for col in source_df.columns
            if col not in primary_keys
            and col not in ["effective_start_date", "effective_end_date", "is_current"]
        ]
        
        # Compare each non-PK column for changes
        change_conditions = [
            f"target.{col} != source.{col}" for col in non_pk_columns
        ]
        change_condition = " OR ".join(change_conditions) if change_conditions else "false"
        
        # SCD2 MERGE statement
        merge_result = target_delta.alias("target") \
            .merge(
                source_df.alias("source"),
                f"({join_condition}) AND target.is_current = true"
            ) \
            .whenMatchedUpdate(
                condition=change_condition,
                set={
                    "is_current": "false",
                    "effective_end_date": "current_date()"
                }
            ) \
            .whenNotMatchedInsert(
                values={
                    **{col: f"source.{col}" for col in source_df.columns}
                }
            ) \
            .execute()
        
        # Insert new versions of changed records
        # This is a second pass to insert the new version after expiring the old one
        changed_records = source_df.alias("source") \
            .join(
                spark.table(target_table_fqn).alias("target"),
                [source_df[pk] == F.col(f"target.{pk}") for pk in primary_keys],
                "inner"
            ) \
            .where(F.col("target.is_current") == False) \
            .where(F.col("target.effective_end_date") == F.current_date()) \
            .select([F.col(f"source.{col}") for col in source_df.columns])
        
        if changed_records.count() > 0:
            changed_records.write.format("delta").mode("append").saveAsTable(target_table_fqn)
        
        # Extract metrics from merge result
        rows_updated = merge_result.get("num_updated_rows", 0)
        rows_inserted = merge_result.get("num_inserted_rows", 0)
        changed_count = changed_records.count()
        
        return {
            "rows_written": rows_inserted + changed_count,
            "rows_updated": rows_updated,
            "rows_inserted": rows_inserted + changed_count
        }
    
    def _initial_load(
        self,
        df: DataFrame,
        target_table_fqn: str,
        partition_columns: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Initial load when target table doesn't exist.
        
        Args:
            df: Source DataFrame with SCD2 columns
            target_table_fqn: Fully qualified table name
            partition_columns: Optional partition columns
            
        Returns:
            dict with metrics
        """
        row_count = df.count()
        
        writer = df.write.format("delta").mode("append")
        
        if partition_columns:
            writer = writer.partitionBy(*partition_columns)
        
        writer.saveAsTable(target_table_fqn)
        
        return {
            "rows_written": row_count,
            "rows_updated": 0,
            "rows_inserted": row_count
        }
    
    def supports_execution_mode(self, execution_mode: str) -> bool:
        """
        Check if this strategy supports the given execution mode.
        
        Args:
            execution_mode: "declarative" or "imperative"
            
        Returns:
            True if mode is supported
        """
        # SCD2 works for both modes
        # Declarative uses APPLY CHANGES INTO (Lakeflow SDP)
        # Imperative uses Delta MERGE (PySpark)
        return execution_mode in ("declarative", "imperative")
    
    def generate_ddl(
        self,
        target_table_fqn: str,
        df: DataFrame,
        partition_columns: Optional[list[str]] = None
    ) -> str:
        """
        Generate CREATE TABLE DDL for SCD2 target table.
        
        Adds SCD2 columns:
        - effective_start_date DATE
        - effective_end_date DATE
        - is_current BOOLEAN
        
        Args:
            target_table_fqn: Fully qualified table name
            df: Sample DataFrame to infer schema
            partition_columns: Optional partition columns
            
        Returns:
            SQL CREATE TABLE statement
        """
        # Get schema from DataFrame (without SCD2 columns)
        base_schema = [
            f"{field.name} {field.dataType.simpleString().upper()}"
            for field in df.schema.fields
        ]
        
        # Add SCD2 columns
        scd2_columns = [
            "effective_start_date DATE NOT NULL",
            "effective_end_date DATE NOT NULL",
            "is_current BOOLEAN NOT NULL"
        ]
        
        all_columns = base_schema + scd2_columns
        columns_ddl = ",\n  ".join(all_columns)
        
        # Build CREATE TABLE statement
        ddl = f"CREATE TABLE IF NOT EXISTS {target_table_fqn} (\n  {columns_ddl}\n) USING DELTA"
        
        # Add partitioning if specified
        if partition_columns:
            ddl += f"\nPARTITIONED BY ({', '.join(partition_columns)})"
        
        return ddl
```

---

### 3.2 SCD2 MERGE Logic Explained

**Three scenarios:**

1. **New record (NOT MATCHED):**
   ```
   Source: policy_id=POL001, status=Active
   Target: (no match)
   → INSERT with is_current=true, effective_end_date=9999-12-31
   ```

2. **Changed record (MATCHED + different):**
   ```
   Source: policy_id=POL001, status=Cancelled
   Target: policy_id=POL001, status=Active, is_current=true
   → Step 1: UPDATE target set is_current=false, effective_end_date=current_date
   → Step 2: INSERT source with is_current=true, effective_end_date=9999-12-31
   ```

3. **Unchanged record (MATCHED + same):**
   ```
   Source: policy_id=POL001, status=Active
   Target: policy_id=POL001, status=Active, is_current=true
   → No action (already current)
   ```

---

### 3.3 Usage Patterns

**Imperative mode (PySpark):**
```python
from dataio.load_strategy import get_load_strategy
from core.metadata import LoadStrategy as LoadStrategyEnum

# Read source data
source_df = spark.read.format("csv").load("/Volumes/main/raw/customers/")

# Get SCD2 strategy
strategy = get_load_strategy(LoadStrategyEnum.SCD2)

# Apply SCD2
metrics = strategy.write(
    df=source_df,
    target_table_fqn="main.silver.customer_dim",
    primary_keys=["customer_id"],
    partition_columns=["region"],
    execution_mode="imperative"
)

print(f"Inserted {metrics['rows_inserted']} rows, expired {metrics['rows_updated']} rows")
```

**Declarative mode (Lakeflow SDP):**
```sql
-- In Lakeflow SDP pipeline
CREATE OR REFRESH STREAMING TABLE silver.customer_dim;

APPLY CHANGES INTO silver.customer_dim
FROM STREAM(bronze.customer_raw)
KEYS (customer_id)
SEQUENCE BY update_timestamp
STORED AS SCD TYPE 2;
```

---

### 3.4 DDL Generation

**Generate CREATE TABLE DDL with SCD2 columns:**
```python
strategy = get_load_strategy(LoadStrategyEnum.SCD2)

# Generate DDL from sample DataFrame
ddl = strategy.generate_ddl(
    target_table_fqn="main.silver.customer_dim",
    df=source_df,
    partition_columns=["region"]
)

print(ddl)
# Output:
# CREATE TABLE IF NOT EXISTS main.silver.customer_dim (
#   customer_id STRING,
#   customer_name STRING,
#   email STRING,
#   region STRING,
#   effective_start_date DATE NOT NULL,
#   effective_end_date DATE NOT NULL,
#   is_current BOOLEAN NOT NULL
# ) USING DELTA
# PARTITIONED BY (region)

# Execute DDL
spark.sql(ddl)
```

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/load_strategy/scd2_strategy.py`** — SCD2Strategy implementation
* **`dataio/load_strategy/__init__.py`** — Factory registration (extends pattern)
* **Unit tests** — test SCD2 logic (new, changed, unchanged), DDL generation
* **Integration tests** — test end-to-end SCD2 to Delta table

### 4.2 Downstream Consumption
* **HarmonizationEngine** — uses get_load_strategy(LoadStrategy.SCD2) for Silver dimension tables
* **Config-driven pipelines** — YAML configs specify load_strategy: scd2

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
* **Primary keys missing** — raise ValueError("SCD2 requires primary_keys")
* **Table not found (initial load)** — create table with first batch
* **MERGE failure** — re-raise with context (table name, primary keys)
* **Schema mismatch** — Delta handles schema evolution if enabled

### 5.2 Edge Cases
* **Empty source DataFrame** — no MERGE, return 0 rows written
* **All records unchanged** — MERGE matches but no updates/inserts
* **Multiple changes same day** — latest change wins (use timestamp for ordering if available)
* **Primary key change** — treated as delete old + insert new (two records)
* **Null primary keys** — Delta MERGE will skip (log warning)

### 5.3 Performance Considerations
* **MERGE overhead** — SCD2 is slower than append (requires full table scan for matching)
* **Partitioning** — partition by date or region to reduce scan size
* **Z-ordering** — Z-order by primary keys for faster lookups
* **Optimize** — run OPTIMIZE periodically to compact small files
* **Change detection** — comparing all non-PK columns can be expensive for wide tables

---

## 6. ABC Hooks

### 6.1 Audit
* **MERGE operations** — audit before and after:
  ```python
  abc_sdk.audit(event="scd2_merge_start", table_fqn=target_table_fqn, source_count=source_count)
  # ... MERGE ...
  abc_sdk.audit(event="scd2_merge_success", table_fqn=target_table_fqn, metrics=metrics)
  ```

### 6.2 Balance
* **Row count validation** — compare source and net change:
  ```python
  abc_sdk.balance(
      check_type="scd2_net_change",
      source="source_df",
      target=target_table_fqn,
      source_count=source_df.count(),
      inserted=metrics["rows_inserted"],
      updated=metrics["rows_updated"]
  )
  ```

### 6.3 Cost Tracking
* **DBU consumption** — track MERGE operations:
  ```python
  abc_sdk.cost_track(
      operation="scd2_merge",
      table_fqn=target_table_fqn,
      rows_processed=source_count,
      duration_seconds=metrics["duration_seconds"]
  )
  ```

### 6.4 Logging
* **Structured logging** — log MERGE operations:
  ```python
  logger.info(f"Applying SCD2 to {target_table_fqn}", extra={
      "trace_id": trace_id,
      "primary_keys": primary_keys,
      "source_count": source_count
  })
  ```

---

## 7. Examples

### 7.1 Basic SCD2
```python
from pyspark.sql import SparkSession
from dataio.load_strategy import get_load_strategy
from core.metadata import LoadStrategy as LoadStrategyEnum

spark = SparkSession.builder.appName("SCD2Example").getOrCreate()

# Create sample data (customer dimension)
data = [
    ("CUST001", "John Doe", "john@example.com", "US"),
    ("CUST002", "Jane Smith", "jane@example.com", "CA")
]
columns = ["customer_id", "customer_name", "email", "region"]
source_df = spark.createDataFrame(data, columns)

# Apply SCD2
strategy = get_load_strategy(LoadStrategyEnum.SCD2)
metrics = strategy.write(
    df=source_df,
    target_table_fqn="main.silver.customer_dim",
    primary_keys=["customer_id"],
    partition_columns=["region"],
    execution_mode="imperative"
)

print(f"✅ SCD2 applied: {metrics['rows_inserted']} inserted, {metrics['rows_updated']} expired")
```

### 7.2 SCD2 with Change Detection
```python
# Initial load
initial_data = [
    ("POL001", "Active", 1000.0),
    ("POL002", "Active", 1500.0)
]
initial_df = spark.createDataFrame(initial_data, ["policy_id", "status", "premium"])

strategy.write(initial_df, "main.silver.policy_dim", ["policy_id"], execution_mode="imperative")

# Query current records
current = spark.sql("SELECT * FROM main.silver.policy_dim WHERE is_current = true")
current.show()
# +----------+--------+---------+---------------------+-------------------+----------+
# |policy_id |status  |premium  |effective_start_date |effective_end_date |is_current|
# +----------+--------+---------+---------------------+-------------------+----------+
# |POL001    |Active  |1000.0   |2024-01-15           |9999-12-31         |true      |
# |POL002    |Active  |1500.0   |2024-01-15           |9999-12-31         |true      |
# +----------+--------+---------+---------------------+-------------------+----------+

# Update: POL001 status changed to Cancelled
update_data = [
    ("POL001", "Cancelled", 1000.0),
    ("POL002", "Active", 1500.0)  # Unchanged
]
update_df = spark.createDataFrame(update_data, ["policy_id", "status", "premium"])

metrics = strategy.write(update_df, "main.silver.policy_dim", ["policy_id"], execution_mode="imperative")

print(f"Changed records: {metrics['rows_updated']}, New versions: {metrics['rows_inserted']}")

# Query all versions (including history)
all_versions = spark.sql("SELECT * FROM main.silver.policy_dim ORDER BY policy_id, effective_start_date")
all_versions.show()
# +----------+---------+---------+---------------------+-------------------+----------+
# |policy_id |status   |premium  |effective_start_date |effective_end_date |is_current|
# +----------+---------+---------+---------------------+-------------------+----------+
# |POL001    |Active   |1000.0   |2024-01-15           |2024-01-16         |false     |
# |POL001    |Cancelled|1000.0   |2024-01-16           |9999-12-31         |true      |
# |POL002    |Active   |1500.0   |2024-01-15           |9999-12-31         |true      |
# +----------+---------+---------+---------------------+-------------------+----------+
```

### 7.3 Querying Historical Data
```python
# Get current snapshot
current = spark.sql("""
    SELECT * FROM main.silver.customer_dim
    WHERE is_current = true
""")

# Get snapshot as of specific date
snapshot_2024_01_10 = spark.sql("""
    SELECT * FROM main.silver.customer_dim
    WHERE effective_start_date <= '2024-01-10'
      AND effective_end_date > '2024-01-10'
""")

# Get all versions for a customer
customer_history = spark.sql("""
    SELECT * FROM main.silver.customer_dim
    WHERE customer_id = 'CUST001'
    ORDER BY effective_start_date
""")
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **New records** — test INSERT for NOT MATCHED
2. **Changed records** — test UPDATE + INSERT for MATCHED with changes
3. **Unchanged records** — test no action for MATCHED without changes
4. **Primary keys** — test ValueError if primary_keys empty
5. **SCD2 columns** — test effective_start_date, effective_end_date, is_current added
6. **DDL generation** — test generate_ddl() includes SCD2 columns
7. **Initial load** — test first load creates table

### 8.2 Integration Tests
* **End-to-end SCD2** — initial load + updates, verify history tracked
* **Change detection** — update records, verify old versions expired
* **Multiple updates** — update same record twice, verify 3 versions
* **Partitioning** — verify partitions created correctly

### 8.3 Regression Tests
* **Concurrent MERGE** — verify optimistic concurrency control works
* **Schema evolution** — add column to source, verify Delta merges schema

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — LoadStrategy protocol definition
* `metadata-models-spec.md` — LoadStrategy enum
* `PROJECT_CONTEXT.md` §4 — architecture decisions

### 9.2 External Standards
* **SCD Type 2** — Kimball dimensional modeling pattern
* **Delta MERGE** — https://docs.delta.io/latest/delta-update.html#merge

### 9.3 Databricks Documentation
* **Delta MERGE** — https://docs.databricks.com/aws/en/delta/merge.html
* **APPLY CHANGES INTO** — https://docs.databricks.com/aws/en/delta-live-tables/cdc.html

---

## 10. Decisions Made

All design decisions:

1. **SCD2 columns** — effective_start_date, effective_end_date, is_current (standard pattern)
2. **Max date** — 9999-12-31 for current records (standard convention)
3. **Change detection** — compare all non-PK columns (comprehensive but expensive)
4. **Two-step MERGE** — expire old version, then insert new version (required for SCD2)
5. **Initial load** — if table doesn't exist, create with first batch
6. **Execution modes** — support both declarative (APPLY CHANGES INTO) and imperative (Delta MERGE)
7. **Primary keys required** — raise ValueError if missing (SCD2 depends on PKs)
8. **DDL generation** — CREATE TABLE IF NOT EXISTS with SCD2 columns

---

**End of SCD2 Strategy Spec (Approved)**
