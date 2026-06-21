---
id: dataio.load_strategy.scd1-strategy
title: SCD1 Strategy Spec
owner: EY
status: draft
target_path: src/load_strategy/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/load_strategy/scd1-strategy-spec.md
acceptance:
  - "pytest tests/unit/test_scd1_strategy.py"
regeneration: scaffold-then-edit
---

# SCD1 Strategy Spec

## 1. Purpose

Implement the **LoadStrategy protocol** for **Slowly Changing Dimension Type 1 (SCD1)**, enabling the framework to upsert records without maintaining history.

**SCD1 characteristics:**
* **No history** — updates overwrite existing records
* **Upsert semantics** — INSERT new records, UPDATE existing records
* **Simple logic** — no date ranges, no versioning
* **Use cases** — reference tables, code tables, current-state dimensions

**SCD1 logic:**
1. **New records** — INSERT
2. **Existing records** — UPDATE with new values (overwrite)
3. **No history tracking** — old values lost

**Key capabilities:**
* Delta MERGE for upsert semantics
* Primary key matching
* Support for declarative and imperative modes
* Faster than SCD2 (no history tracking overhead)

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements LoadStrategy protocol from engine-contracts-spec
* Uses Delta MERGE for ACID guarantees
* Returns write metrics (rows inserted, rows updated)
* ABC balance hooks for row count validation

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (LoadStrategy protocol, Delta MERGE)
* **ROADMAP.md Phase 0** — SCD1 strategy is Wave 1 core capability
* **metadata-models-spec.md** — LoadStrategy enum
* **engine-contracts-spec.md** — LoadStrategy protocol definition
* **Backlog tasks:** DATAIO-011, LOADSTRAT-002

### 2.2 Design Constraints
* **Protocol compliance** — implement LoadStrategy protocol (write, supports_execution_mode, generate_ddl)
* **Primary keys required** — SCD1 requires primary keys for matching
* **Delta MERGE** — use Delta's MERGE for upsert semantics
* **Performance** — optimize for fast upserts (no history overhead)

---

## 3. Procedure

### 3.1 SCD1Strategy Implementation

**Purpose:** Upsert records without history

```python
# dataio/load_strategy/scd1_strategy.py
from typing import Optional, Dict, Any
import time
from pyspark.sql import DataFrame

from core.contracts import LoadStrategy
from core.metadata import LoadStrategy as LoadStrategyEnum
from dataio.load_strategy import register_load_strategy

@register_load_strategy(LoadStrategyEnum.SCD1)
class SCD1Strategy(LoadStrategy):
    """
    Slowly Changing Dimension Type 1 (SCD1) load strategy.
    
    Simple upsert: INSERT new records, UPDATE existing records.
    No history tracking - old values are overwritten.
    
    Use cases:
    - Reference tables (country codes, product types)
    - Current-state dimensions
    - Lookup tables
    - Master data without history requirements
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
        Apply SCD1 upsert to target table.
        
        Args:
            df: Source DataFrame to merge
            target_table_fqn: Fully qualified target table name (catalog.schema.table)
            primary_keys: Primary key columns (REQUIRED for SCD1)
            partition_columns: Optional partition columns
            execution_mode: "declarative" (Lakeflow SDP) or "imperative" (PySpark)
            
        Returns:
            dict with write metrics:
                {
                    "rows_written": int,  # Total rows written
                    "rows_updated": int,  # Rows updated
                    "rows_inserted": int,  # Rows inserted
                    "duration_seconds": float
                }
                
        Raises:
            ValueError: If primary_keys empty, execution_mode not supported
        """
        if not primary_keys:
            raise ValueError("SCD1 strategy requires primary_keys for matching")
        
        if not self.supports_execution_mode(execution_mode):
            raise ValueError(f"Execution mode not supported: {execution_mode}")
        
        start_time = time.time()
        
        # Count source rows for metrics
        source_count = df.count()
        
        # Write based on execution mode
        if execution_mode == "imperative":
            metrics = self._write_imperative(
                df,
                target_table_fqn,
                primary_keys,
                partition_columns
            )
        else:
            # Declarative mode (Lakeflow SDP)
            # Note: SCD1 in Lakeflow SDP uses APPLY CHANGES INTO
            # This is a placeholder for imperative fallback
            metrics = self._write_imperative(
                df,
                target_table_fqn,
                primary_keys,
                partition_columns
            )
        
        duration = time.time() - start_time
        metrics["duration_seconds"] = duration
        
        return metrics
    
    def _write_imperative(
        self,
        source_df: DataFrame,
        target_table_fqn: str,
        primary_keys: list[str],
        partition_columns: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply SCD1 using Delta MERGE.
        
        SCD1 MERGE logic:
        1. MATCHED → UPDATE with new values
        2. NOT MATCHED → INSERT new row
        
        Args:
            source_df: Source DataFrame
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
        
        # Build update set clause (all columns)
        update_set = {
            col: f"source.{col}" for col in source_df.columns
        }
        
        # Build insert values clause (all columns)
        insert_values = {
            col: f"source.{col}" for col in source_df.columns
        }
        
        # SCD1 MERGE statement
        merge_result = target_delta.alias("target") \
            .merge(
                source_df.alias("source"),
                join_condition
            ) \
            .whenMatchedUpdate(set=update_set) \
            .whenNotMatchedInsert(values=insert_values) \
            .execute()
        
        # Extract metrics from merge result
        rows_updated = merge_result.get("num_updated_rows", 0)
        rows_inserted = merge_result.get("num_inserted_rows", 0)
        rows_written = rows_updated + rows_inserted
        
        return {
            "rows_written": rows_written,
            "rows_updated": rows_updated,
            "rows_inserted": rows_inserted
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
            df: Source DataFrame
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
        """Check if this strategy supports the given execution mode."""
        return execution_mode in ("declarative", "imperative")
    
    def generate_ddl(
        self,
        target_table_fqn: str,
        df: DataFrame,
        partition_columns: Optional[list[str]] = None
    ) -> str:
        """
        Generate CREATE TABLE DDL for SCD1 target table.
        
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
        """Convert PySpark schema to SQL DDL column definitions."""
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
source_df = spark.read.format("csv").load("/Volumes/main/raw/product_types/")

# Get SCD1 strategy
strategy = get_load_strategy(LoadStrategyEnum.SCD1)

# Apply SCD1 upsert
metrics = strategy.write(
    df=source_df,
    target_table_fqn="main.silver.product_type_dim",
    primary_keys=["product_type_code"],
    partition_columns=None,
    execution_mode="imperative"
)

print(f"Inserted {metrics['rows_inserted']} rows, updated {metrics['rows_updated']} rows")
```

**Declarative mode (Lakeflow SDP):**
```sql
-- In Lakeflow SDP pipeline
CREATE OR REFRESH STREAMING TABLE silver.product_type_dim;

APPLY CHANGES INTO silver.product_type_dim
FROM STREAM(bronze.product_type_raw)
KEYS (product_type_code)
SEQUENCE BY update_timestamp
STORED AS SCD TYPE 1;
```

---

## 4. Examples

### 4.1 Basic SCD1 Upsert
```python
from pyspark.sql import SparkSession
from dataio.load_strategy import get_load_strategy
from core.metadata import LoadStrategy as LoadStrategyEnum

spark = SparkSession.builder.appName("SCD1Example").getOrCreate()

# Initial load
initial_data = [
    ("TYPE001", "Auto", "Automobile insurance"),
    ("TYPE002", "Home", "Homeowners insurance")
]
columns = ["product_type_code", "product_type_name", "description"]
initial_df = spark.createDataFrame(initial_data, columns)

strategy = get_load_strategy(LoadStrategyEnum.SCD1)
metrics = strategy.write(
    df=initial_df,
    target_table_fqn="main.silver.product_type_dim",
    primary_keys=["product_type_code"],
    execution_mode="imperative"
)

print(f"✅ Initial load: {metrics['rows_inserted']} rows")

# Query current data
spark.sql("SELECT * FROM main.silver.product_type_dim").show()
# +------------------+------------------+-------------------------+
# |product_type_code |product_type_name |description              |
# +------------------+------------------+-------------------------+
# |TYPE001           |Auto              |Automobile insurance     |
# |TYPE002           |Home              |Homeowners insurance     |
# +------------------+------------------+-------------------------+

# Update: TYPE001 description changed
update_data = [
    ("TYPE001", "Auto", "Vehicle insurance coverage"),  # Changed description
    ("TYPE002", "Home", "Homeowners insurance"),  # Unchanged
    ("TYPE003", "Life", "Life insurance")  # New record
]
update_df = spark.createDataFrame(update_data, columns)

metrics = strategy.write(
    df=update_df,
    target_table_fqn="main.silver.product_type_dim",
    primary_keys=["product_type_code"],
    execution_mode="imperative"
)

print(f"✅ Updated {metrics['rows_updated']} rows, inserted {metrics['rows_inserted']} rows")

# Query updated data
spark.sql("SELECT * FROM main.silver.product_type_dim ORDER BY product_type_code").show()
# +------------------+------------------+-------------------------+
# |product_type_code |product_type_name |description              |
# +------------------+------------------+-------------------------+
# |TYPE001           |Auto              |Vehicle insurance coverage|  # Updated
# |TYPE002           |Home              |Homeowners insurance     |
# |TYPE003           |Life              |Life insurance           |  # New
# +------------------+------------------+-------------------------+

# Note: Old description for TYPE001 is lost (no history)
```

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
* **Primary keys missing** — raise ValueError("SCD1 requires primary_keys")
* **Table not found (initial load)** — create table with first batch
* **MERGE failure** — re-raise with context
* **Schema mismatch** — Delta handles schema evolution if enabled

### 5.2 Edge Cases
* **Empty DataFrame** — no MERGE, return 0 rows written
* **All records unchanged** — MERGE matches and updates (even if values same)
* **Null primary keys** — Delta MERGE will skip
* **Primary key change** — treated as new record (old record orphaned)

### 5.3 Performance Considerations
* **MERGE overhead** — SCD1 is slower than append (requires matching)
* **Faster than SCD2** — no history tracking overhead
* **Partitioning** — partition by frequently-queried columns
* **Z-ordering** — Z-order by primary keys for faster lookups
* **Optimize** — run OPTIMIZE periodically

---

## 6. ABC Hooks

### 6.1 Audit
```python
abc_sdk.audit(event="scd1_merge_start", table_fqn=target_table_fqn, source_count=source_count)
# ... MERGE ...
abc_sdk.audit(event="scd1_merge_success", table_fqn=target_table_fqn, metrics=metrics)
```

### 6.2 Balance
```python
abc_sdk.balance(
    check_type="scd1_upsert",
    source="source_df",
    target=target_table_fqn,
    source_count=source_df.count(),
    inserted=metrics["rows_inserted"],
    updated=metrics["rows_updated"]
)
```

### 6.3 Cost Tracking
```python
abc_sdk.cost_track(
    operation="scd1_merge",
    table_fqn=target_table_fqn,
    rows_processed=source_count,
    duration_seconds=metrics["duration_seconds"]
)
```

---

## 7. Acceptance Criteria

### 7.1 Unit Tests (>80% coverage)
1. **Upsert** — test INSERT + UPDATE for matched/unmatched
2. **Primary keys** — test ValueError if primary_keys empty
3. **DDL generation** — test generate_ddl() produces valid SQL
4. **Execution modes** — test supports_execution_mode()
5. **Metrics** — test returned metrics (rows_inserted, rows_updated)
6. **Initial load** — test first load creates table

### 7.2 Integration Tests
* **End-to-end SCD1** — initial load + updates, verify no history
* **Concurrent MERGE** — verify optimistic concurrency control

---

## 8. References

### 8.1 Internal Documents
* `engine-contracts-spec.md` — LoadStrategy protocol
* `metadata-models-spec.md` — LoadStrategy enum
* `scd2-strategy-spec.md` — SCD2 pattern for comparison

### 8.2 External Standards
* **SCD Type 1** — Kimball dimensional modeling pattern
* **Delta MERGE** — https://docs.delta.io/latest/delta-update.html#merge

### 8.3 Databricks Documentation
* **Delta MERGE** — https://docs.databricks.com/aws/en/delta/merge.html
* **APPLY CHANGES INTO** — https://docs.databricks.com/aws/en/delta-live-tables/cdc.html

---

## 9. Decisions Made

1. **Primary keys required** — raise ValueError if missing
2. **No history tracking** — updates overwrite (simpler than SCD2)
3. **MERGE semantics** — MATCHED → UPDATE, NOT MATCHED → INSERT
4. **Initial load** — if table doesn't exist, create with first batch
5. **Execution modes** — support both declarative and imperative
6. **DDL generation** — CREATE TABLE IF NOT EXISTS (no SCD columns)

---

**End of SCD1 Strategy Spec (Approved)**
