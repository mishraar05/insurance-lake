# Engine Contracts Spec

---

## Front Matter

```yaml
id: engine-contracts-spec
version: 1.0
status: approved
approved_date: 2026-06-18
tier: core
component: contracts
backlog_ids:
  - FND-004  # Define framework contracts/interfaces
  - ARCH-001 # Architecture patterns and protocols
dependencies:
  - metadata-models-spec
runtime: Python 3.10+
purpose: Define protocol interfaces (Reader, LoadStrategy, Engine, Check, Masker) that all framework implementations must follow
inputs:
  - metadata-models-spec.md (imports Feed, Pipeline, DQCheck, etc.)
  - PROJECT_CONTEXT.md §4 (architecture decisions)
outputs:
  - Python Protocol/ABC definitions for all framework contracts
  - Type-safe interfaces for dependency injection
  - Documentation of contract requirements
tools_required:
  - Python typing.Protocol or abc.ABC
  - Python typing module
```

---

## 1. Purpose

Define **protocol interfaces** (contracts) that all InsureLake framework components must implement. These protocols enable:

1. **Type safety** — components type-check against protocols at compile time
2. **Polymorphism** — engines/readers/strategies are interchangeable via dependency injection
3. **Testability** — easy to mock implementations for unit tests
4. **Extensibility** — new implementations just implement the protocol

**Five core protocols:**
* **Reader** — reads source data (files, JDBC, streams)
* **LoadStrategy** — writes data with specific semantics (append, SCD1, SCD2)
* **Engine** — orchestrates end-to-end pipelines (ingestion, harmonization, DQ, recon, masking)
* **Check** — executes data quality validations
* **Masker** — applies PII/PHI masking techniques

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Protocols work for both declarative (Lakeflow SDP) and imperative (PySpark + MERGE) execution modes
* Methods accept metadata models (Feed, Pipeline, etc.) as typed parameters
* ABC hooks (audit, balance, cost) are called by protocol implementations

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture decisions (dual execution modes, ABC framework)
* **ROADMAP.md Phase 0** — contracts are Wave 0 foundation
* **metadata-models-spec.md** — imports Feed, Pipeline, TransformRule, DQCheck, MaskRule, ReconRule types
* **Backlog tasks:** FND-004, ARCH-001

### 2.2 Design Constraints
* **Protocol vs. ABC** — use `typing.Protocol` for structural subtyping (duck typing); use `abc.ABC` for explicit inheritance when shared implementation is needed
* **Spark DataFrames** — protocols return `pyspark.sql.DataFrame` (standard Databricks pattern)
* **No side effects in constructors** — protocols define interfaces, not implementations
* **Immutable results** — return new DataFrames, don't mutate inputs

---

## 3. Procedure

### 3.1 Reader Protocol

**Purpose:** Abstracts source data reading (files, JDBC, streams).

**Contract:**
```python
from typing import Protocol
from pyspark.sql import DataFrame, SparkSession
from core.metadata import Feed

class Reader(Protocol):
    """
    Protocol for source data readers.
    
    Implementations:
    - FileReader (CSV, JSON, Parquet, Delta)
    - StreamingReader (Auto Loader, Kafka)
    - JDBCReader (SQL Server, Postgres, Oracle)
    """
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read source data as a Spark DataFrame.
        
        Args:
            spark: Active SparkSession
            feed: Feed configuration (source_location, source_format, file_format_options)
            
        Returns:
            DataFrame with source data
            
        Raises:
            FileNotFoundError: If source_location doesn't exist
            ConnectionError: If JDBC connection fails
            ValueError: If source_format is unsupported
        """
        ...
    
    def supports_format(self, source_format: str) -> bool:
        """
        Check if this reader supports the given source format.
        
        Args:
            source_format: Format string (e.g., "csv", "jdbc")
            
        Returns:
            True if format is supported, False otherwise
        """
        ...
```

**Usage Pattern:**
```python
from dataio.readers import get_reader

# Get reader for feed format
reader = get_reader(feed.source_format)
df = reader.read(spark, feed)
```

---

### 3.2 LoadStrategy Protocol

**Purpose:** Abstracts data writing semantics (append, SCD1, SCD2).

**Contract:**
```python
from typing import Protocol, Optional
from pyspark.sql import DataFrame
from core.metadata import Feed, TransformRule, LoadStrategy as LoadStrategyEnum

class LoadStrategy(Protocol):
    """
    Protocol for data loading strategies.
    
    Implementations:
    - AppendStrategy (append-only)
    - SCD1Strategy (upsert/overwrite, no history)
    - SCD2Strategy (maintain history with effective dates)
    - FullRefreshStrategy (truncate and reload)
    """
    
    def write(
        self,
        df: DataFrame,
        target_table_fqn: str,
        primary_keys: list[str],
        partition_columns: Optional[list[str]] = None,
        execution_mode: str = "imperative"
    ) -> dict[str, any]:
        """
        Write DataFrame to target table using strategy-specific semantics.
        
        Args:
            df: Source DataFrame to write
            target_table_fqn: Fully qualified target table name (catalog.schema.table)
            primary_keys: List of primary key columns (for SCD1/SCD2)
            partition_columns: Optional partition columns
            execution_mode: "declarative" (Lakeflow SDP) or "imperative" (PySpark MERGE)
            
        Returns:
            dict with write metrics:
                {
                    "rows_written": int,
                    "rows_updated": int,  # For SCD1/SCD2
                    "rows_inserted": int,  # For SCD1/SCD2
                    "duration_seconds": float
                }
                
        Raises:
            ValueError: If primary_keys are required but missing
            TableNotFoundError: If target table doesn't exist (for SCD1/SCD2)
        """
        ...
    
    def supports_execution_mode(self, execution_mode: str) -> bool:
        """
        Check if this strategy supports the given execution mode.
        
        Args:
            execution_mode: "declarative" or "imperative"
            
        Returns:
            True if mode is supported, False otherwise
        """
        ...
    
    def generate_ddl(self, target_table_fqn: str, df: DataFrame, partition_columns: Optional[list[str]] = None) -> str:
        """
        Generate CREATE TABLE DDL for the target table (if it doesn't exist).
        
        Args:
            target_table_fqn: Fully qualified table name
            df: Sample DataFrame to infer schema
            partition_columns: Optional partition columns
            
        Returns:
            SQL CREATE TABLE statement
        """
        ...
```

**Usage Pattern:**
```python
from dataio.load_strategy import get_load_strategy

# Get strategy for feed
strategy = get_load_strategy(feed.load_strategy)
metrics = strategy.write(
    df=source_df,
    target_table_fqn=feed.target_table_fqn,
    primary_keys=feed.primary_keys,
    partition_columns=feed.partition_columns,
    execution_mode=pipeline.execution_mode.value
)
```

---

### 3.3 Engine Protocol

**Purpose:** Abstracts end-to-end pipeline execution.

**Contract:**
```python
from typing import Protocol
from pyspark.sql import SparkSession
from core.metadata import Pipeline

class Engine(Protocol):
    """
    Protocol for pipeline execution engines.
    
    Implementations:
    - IngestionEngine (Feed → Bronze)
    - HarmonizationEngine (Bronze → Silver/Gold)
    - DQEngine (validate tables)
    - ReconEngine (balance checks)
    - MaskingEngine (apply PII/PHI masking)
    """
    
    def execute(self, spark: SparkSession, pipeline: Pipeline) -> dict[str, any]:
        """
        Execute the entire pipeline end-to-end.
        
        Args:
            spark: Active SparkSession
            pipeline: Pipeline configuration (feeds, transforms, checks, execution_mode)
            
        Returns:
            dict with execution metrics:
                {
                    "status": "success" | "failed" | "partial",
                    "duration_seconds": float,
                    "feeds_processed": int,  # For ingestion
                    "transforms_executed": int,  # For harmonization
                    "checks_passed": int,  # For DQ
                    "checks_failed": int,  # For DQ
                    "rows_processed": int,
                    "error": Optional[str]  # If status == "failed"
                }
                
        Raises:
            PipelineExecutionError: If pipeline fails critically
        """
        ...
    
    def validate_pipeline(self, pipeline: Pipeline) -> list[str]:
        """
        Validate pipeline configuration before execution.
        
        Args:
            pipeline: Pipeline configuration to validate
            
        Returns:
            List of validation error messages (empty list = valid)
        """
        ...
    
    def supports_execution_mode(self, execution_mode: str) -> bool:
        """
        Check if this engine supports the given execution mode.
        
        Args:
            execution_mode: "declarative" or "imperative"
            
        Returns:
            True if mode is supported, False otherwise
        """
        ...
```

**Usage Pattern:**
```python
from framework.ingestion import IngestionEngine

# Instantiate engine
engine = IngestionEngine(
    reader_registry=reader_registry,
    load_strategy_registry=load_strategy_registry,
    abc_sdk=abc_sdk
)

# Validate pipeline
errors = engine.validate_pipeline(pipeline)
if errors:
    raise ValueError(f"Invalid pipeline: {errors}")

# Execute
metrics = engine.execute(spark, pipeline)
print(f"Processed {metrics['feeds_processed']} feeds in {metrics['duration_seconds']}s")
```

---

### 3.4 Check Protocol

**Purpose:** Abstracts data quality check execution.

**Contract:**
```python
from typing import Protocol
from pyspark.sql import DataFrame, SparkSession
from core.metadata import DQCheck

class Check(Protocol):
    """
    Protocol for data quality checks.
    
    Implementations:
    - NotNullCheck
    - UniqueCheck
    - RangeCheck
    - PatternCheck
    - ReferentialCheck
    - CustomSQLCheck
    """
    
    def execute(self, spark: SparkSession, check: DQCheck) -> dict[str, any]:
        """
        Execute data quality check on target table.
        
        Args:
            spark: Active SparkSession
            check: DQCheck configuration (table_fqn, check_type, check_expression, severity)
            
        Returns:
            dict with check results:
                {
                    "check_id": str,
                    "status": "passed" | "failed",
                    "total_rows": int,
                    "failed_rows": int,
                    "failure_rate": float,  # 0.0 to 1.0
                    "severity": str,  # "warn", "block", "quarantine"
                    "action_taken": str,  # "continued", "blocked", "quarantined"
                    "quarantine_table": Optional[str],  # If action == "quarantined"
                    "error": Optional[str]  # If execution failed
                }
                
        Raises:
            TableNotFoundError: If check.table_fqn doesn't exist
            ValidationError: If check configuration is invalid
        """
        ...
    
    def supports_check_type(self, check_type: str) -> bool:
        """
        Check if this implementation supports the given check type.
        
        Args:
            check_type: Check type string (e.g., "not_null", "pattern")
            
        Returns:
            True if check type is supported, False otherwise
        """
        ...
```

**Usage Pattern:**
```python
from dataio.checks import get_check

# Get check implementation
check_impl = get_check(dq_check.check_type)
result = check_impl.execute(spark, dq_check)

if result["status"] == "failed" and result["severity"] == "block":
    raise DataQualityError(f"Check {dq_check.check_id} failed: {result}")
```

---

### 3.5 Masker Protocol

**Purpose:** Abstracts PII/PHI masking techniques.

**Contract:**
```python
from typing import Protocol
from pyspark.sql import DataFrame, SparkSession
from core.metadata import MaskRule

class Masker(Protocol):
    """
    Protocol for PII/PHI masking techniques.
    
    Implementations:
    - RedactMasker (full redaction)
    - HashMasker (one-way hash)
    - TokenizeMasker (reversible tokenization)
    - UCDynamicMasker (Unity Catalog dynamic masking)
    - PartialMasker (partial masking)
    """
    
    def mask(self, spark: SparkSession, mask_rule: MaskRule) -> dict[str, any]:
        """
        Apply masking to target table column.
        
        Args:
            spark: Active SparkSession
            mask_rule: MaskRule configuration (table_fqn, column_name, technique)
            
        Returns:
            dict with masking results:
                {
                    "mask_id": str,
                    "status": "success" | "failed",
                    "rows_masked": int,
                    "technique": str,
                    "duration_seconds": float,
                    "error": Optional[str]
                }
                
        Raises:
            TableNotFoundError: If mask_rule.table_fqn doesn't exist
            ColumnNotFoundError: If mask_rule.column_name doesn't exist
            ValueError: If technique configuration is invalid
        """
        ...
    
    def supports_technique(self, technique: str) -> bool:
        """
        Check if this masker supports the given technique.
        
        Args:
            technique: Technique string (e.g., "redact", "hash")
            
        Returns:
            True if technique is supported, False otherwise
        """
        ...
    
    def is_reversible(self) -> bool:
        """
        Check if this masking technique is reversible (e.g., tokenization).
        
        Returns:
            True if technique supports unmasking, False otherwise
        """
        ...
```

**Usage Pattern:**
```python
from dataio.maskers import get_masker

# Get masker implementation
masker = get_masker(mask_rule.technique)
result = masker.mask(spark, mask_rule)

print(f"Masked {result['rows_masked']} rows using {result['technique']}")
```

---

### 3.6 Factory Registry Pattern

**Purpose:** Enable protocol-based dependency injection.

**Implementation:**
```python
# dataio/readers/__init__.py
from typing import Dict, Type
from core.contracts import Reader
from core.metadata import SourceFormat

_READER_REGISTRY: Dict[SourceFormat, Type[Reader]] = {}

def register_reader(source_format: SourceFormat):
    """Decorator to register a Reader implementation."""
    def decorator(cls: Type[Reader]) -> Type[Reader]:
        _READER_REGISTRY[source_format] = cls
        return cls
    return decorator

def get_reader(source_format: SourceFormat) -> Reader:
    """Get Reader implementation for source format."""
    if source_format not in _READER_REGISTRY:
        raise ValueError(f"No reader registered for format: {source_format}")
    return _READER_REGISTRY[source_format]()

# Example usage in file_readers.py
@register_reader(SourceFormat.CSV)
class CSVReader:
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        return spark.read.format("csv") \
            .options(**feed.file_format_options) \
            .load(feed.source_location)
    
    def supports_format(self, source_format: str) -> bool:
        return source_format == "csv"
```

**Similar registries:**
* `dataio/load_strategy/__init__.py` — `get_load_strategy(load_strategy: LoadStrategy)`
* `dataio/checks/__init__.py` — `get_check(check_type: CheckType)`
* `dataio/maskers/__init__.py` — `get_masker(technique: MaskingTechnique)`

---

## 4. Outputs

### 4.1 Deliverables
* **`core/contracts/protocols.py`** — All protocol definitions (Reader, LoadStrategy, Engine, Check, Masker)
* **`core/contracts/__init__.py`** — Exports for easy import (`from core.contracts import Reader, Engine, ...`)
* **`core/contracts/exceptions.py`** — Custom exceptions (PipelineExecutionError, DataQualityError, etc.)
* **Factory registries** — in each implementation package (`dataio/readers/__init__.py`, etc.)

### 4.2 Downstream Consumption
* **Wave 1 specs** — all dataio implementations (file-readers, jdbc-readers, append-strategy, scd2-strategy, dq-checks, masking-techniques) implement these protocols
* **Wave 2 specs** — all framework engines (ingestion-engine, harmonization-engine, dq-engine, recon-engine, masking-engine) implement Engine protocol
* **Unit tests** — mock protocols for isolated testing

---

## 5. Guardrails

### 5.1 Error Handling
* **Protocol violations** — static type checkers (mypy) catch missing methods at compile time
* **Runtime errors** — implementations raise specific exceptions (TableNotFoundError, ValidationError, PipelineExecutionError)
* **Graceful degradation** — engines return partial success status when some operations fail

### 5.2 Edge Cases
* **Unsupported formats/modes** — `supports_*()` methods return False; caller should check before calling
* **Missing dependencies** — raise ImportError with clear message (e.g., "JDBC driver not installed")
* **Concurrent writes** — LoadStrategy implementations should use Delta MERGE with optimistic concurrency control

### 5.3 Performance Considerations
* **Protocol overhead** — negligible; Python protocols are compile-time checks only
* **DataFrame materialization** — protocols should avoid `.collect()` or `.count()` unless necessary for metrics
* **Lazy evaluation** — return DataFrames for chaining; caller decides when to materialize

---

## 6. ABC Hooks

### 6.1 Audit
* **Protocol method calls** — implementations call ABC audit at entry/exit:
  ```python
  def execute(self, spark: SparkSession, pipeline: Pipeline) -> dict[str, any]:
      abc_sdk.audit(event="pipeline_start", pipeline_id=pipeline.pipeline_id)
      try:
          result = self._do_execute(spark, pipeline)
          abc_sdk.audit(event="pipeline_success", pipeline_id=pipeline.pipeline_id, metrics=result)
          return result
      except Exception as e:
          abc_sdk.audit(event="pipeline_failed", pipeline_id=pipeline.pipeline_id, error=str(e))
          raise
  ```

### 6.2 Balance
* **Reconciliation checks** — Engine implementations call ABC balance after writes:
  ```python
  abc_sdk.balance(
      check_type="row_count",
      source_table=feed.source_location,
      target_table=feed.target_table_fqn,
      source_count=source_df.count(),
      target_count=target_df.count()
  )
  ```

### 6.3 Cost Tracking
* **DBU consumption** — Engine implementations call ABC cost tracking:
  ```python
  abc_sdk.cost_track(
      operation="ingestion",
      pipeline_id=pipeline.pipeline_id,
      rows_processed=metrics["rows_processed"],
      duration_seconds=metrics["duration_seconds"]
  )
  ```

### 6.4 Logging
* **Structured logging** — all protocol implementations log with trace ID:
  ```python
  logger.info(f"Executing check {check.check_id}", extra={
      "trace_id": trace_id,
      "check_type": check.check_type.value,
      "table_fqn": check.table_fqn
  })
  ```

---

## 7. Examples

### 7.1 Implementing a Reader
```python
from core.contracts import Reader
from core.metadata import Feed, SourceFormat
from pyspark.sql import DataFrame, SparkSession

class ParquetReader:
    """Reader for Parquet files."""
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """Read Parquet files from source_location."""
        if feed.source_format != SourceFormat.PARQUET:
            raise ValueError(f"ParquetReader only supports PARQUET format, got {feed.source_format}")
        
        return spark.read.format("parquet") \
            .options(**feed.file_format_options) \
            .load(feed.source_location)
    
    def supports_format(self, source_format: str) -> bool:
        """Check if format is supported."""
        return source_format == "parquet"

# Register with factory
from dataio.readers import register_reader
register_reader(SourceFormat.PARQUET)(ParquetReader)
```

### 7.2 Implementing a LoadStrategy
```python
from core.contracts import LoadStrategy
from pyspark.sql import DataFrame
from typing import Optional
import time

class AppendStrategy:
    """Append-only load strategy."""
    
    def write(
        self,
        df: DataFrame,
        target_table_fqn: str,
        primary_keys: list[str],
        partition_columns: Optional[list[str]] = None,
        execution_mode: str = "imperative"
    ) -> dict[str, any]:
        """Write DataFrame using append mode."""
        start_time = time.time()
        
        writer = df.write.format("delta").mode("append")
        
        if partition_columns:
            writer = writer.partitionBy(*partition_columns)
        
        writer.saveAsTable(target_table_fqn)
        
        duration = time.time() - start_time
        rows_written = df.count()
        
        return {
            "rows_written": rows_written,
            "rows_updated": 0,
            "rows_inserted": rows_written,
            "duration_seconds": duration
        }
    
    def supports_execution_mode(self, execution_mode: str) -> bool:
        """Append works for both modes."""
        return execution_mode in ("declarative", "imperative")
    
    def generate_ddl(self, target_table_fqn: str, df: DataFrame, partition_columns: Optional[list[str]] = None) -> str:
        """Generate CREATE TABLE DDL."""
        schema = df.schema.simpleString()
        ddl = f"CREATE TABLE IF NOT EXISTS {target_table_fqn} ({schema}) USING DELTA"
        if partition_columns:
            ddl += f" PARTITIONED BY ({', '.join(partition_columns)})"
        return ddl
```

### 7.3 Implementing a Check
```python
from core.contracts import Check
from core.metadata import DQCheck, CheckType, CheckSeverity
from pyspark.sql import SparkSession

class NotNullCheck:
    """Check for null values in a column."""
    
    def execute(self, spark: SparkSession, check: DQCheck) -> dict[str, any]:
        """Execute not-null check."""
        if check.check_type != CheckType.NOT_NULL:
            raise ValueError(f"NotNullCheck only supports NOT_NULL, got {check.check_type}")
        
        if not check.column_name:
            raise ValueError("column_name required for NOT_NULL check")
        
        # Read table and count nulls
        df = spark.table(check.table_fqn)
        total_rows = df.count()
        null_rows = df.filter(f"{check.column_name} IS NULL").count()
        
        failure_rate = null_rows / total_rows if total_rows > 0 else 0.0
        threshold = check.threshold or 0.0
        
        status = "passed" if failure_rate <= threshold else "failed"
        action_taken = "continued"
        
        if status == "failed":
            if check.severity == CheckSeverity.BLOCK:
                action_taken = "blocked"
            elif check.severity == CheckSeverity.QUARANTINE:
                action_taken = "quarantined"
                # Move bad rows to quarantine table
                quarantine_table = f"{check.table_fqn}_quarantine"
                df.filter(f"{check.column_name} IS NULL").write.mode("append").saveAsTable(quarantine_table)
            else:
                action_taken = "continued"  # WARN
        
        return {
            "check_id": check.check_id,
            "status": status,
            "total_rows": total_rows,
            "failed_rows": null_rows,
            "failure_rate": failure_rate,
            "severity": check.severity.value,
            "action_taken": action_taken,
            "quarantine_table": f"{check.table_fqn}_quarantine" if action_taken == "quarantined" else None,
            "error": None
        }
    
    def supports_check_type(self, check_type: str) -> bool:
        """Check if check type is supported."""
        return check_type == "not_null"
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **Protocol definition** — verify all protocols have correct method signatures (type checkers pass)
2. **Factory registration** — test `register_*` decorators and `get_*` functions
3. **Mock implementations** — create mock Reader/Engine/Check for testing
4. **Exception handling** — test that implementations raise correct exceptions
5. **Type checking** — run mypy on all protocol implementations (should pass)

### 8.2 Integration Tests
* **Reader → LoadStrategy** — read CSV, write to Delta using AppendStrategy
* **Engine orchestration** — IngestionEngine calls Reader + LoadStrategy, returns metrics
* **Check execution** — NotNullCheck reads table, quarantines bad rows

### 8.3 Synthetic Data Tests
* **Mock Reader** — returns synthetic DataFrame for testing
* **Mock Engine** — simulates pipeline execution with configurable success/failure

---

## 9. References

### 9.1 Internal Documents
* `metadata-models-spec.md` — Feed, Pipeline, DQCheck, MaskRule types
* `PROJECT_CONTEXT.md` §4 — architecture (dual execution modes, ABC)
* `ROADMAP.md` Phase 0 — contracts are Wave 0 foundation

### 9.2 External Standards
* **Python typing.Protocol** — https://docs.python.org/3/library/typing.html#typing.Protocol
* **Python abc.ABC** — https://docs.python.org/3/library/abc.html
* **PySpark DataFrame API** — https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/dataframe.html

### 9.3 Databricks Documentation
* **Delta Lake MERGE** — https://docs.databricks.com/aws/en/delta/merge.html
* **Auto Loader** — https://docs.databricks.com/aws/en/ingestion/auto-loader/
* **Unity Catalog** — https://docs.databricks.com/aws/en/data-governance/unity-catalog/

---

## 10. Decisions Made

All design decisions per validation framework:

1. **Protocol vs. ABC** — Use `typing.Protocol` for interfaces (structural subtyping); use `abc.ABC` only if shared implementation is needed
2. **Factory pattern** — Use decorator-based registration (`@register_reader`) for clean dependency injection
3. **Return types** — Protocols return dicts with metrics (not custom classes) for simplicity and JSON-serializability
4. **Error handling** — Raise specific exceptions (TableNotFoundError, ValidationError) for clear error messages
5. **Execution modes** — All protocols support both "declarative" and "imperative" via `supports_execution_mode()`
6. **ABC hooks** — Implementations call ABC SDK; not enforced by protocol (caller responsibility)
7. **DataFrame immutability** — Protocols return new DataFrames, never mutate inputs

---

**End of Engine Contracts Spec (Approved)**
