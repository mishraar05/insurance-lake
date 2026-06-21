---
id: ingestion.engine
title: Ingestion Engine - Batch Orchestrator
owner: EY
status: active
target_path: src/framework/ingestion/
owning_skill: insurelake-spec-codegen
backlog: [ING-001]
provides:
  - IngestionEngine
  - run_batch_append
  - validate_config
  - create_quarantine_table
  - IngestionError
  - MaxRetriesExceededError
  - ConfigurationError
  - NullRunHandle
depends_on:
  - foundation.abc-sdk
  - foundation.config-model
  - foundation.contracts
  - dataio.readers.file-readers
  - dataio.load_strategy.append-strategy
generation_context:
  - specs/ingestion/ingestion-engine-spec.md
  - specs/foundation/abc-sdk-spec.md
  - specs/foundation/config-model-spec.md
  - specs/foundation/contracts-spec.md
  - specs/dataio/file-readers-spec.md
  - specs/dataio/append-strategy-spec.md
  - specs/CAPABILITY_REGISTRY.md
acceptance:
  - "pytest tests/unit/test_ingestion_engine.py --cov=src/framework/ingestion --cov-report=term-missing --cov-fail-under=80"
  - "pytest tests/integration/test_ingestion_batch_append.py"
  - "pytest tests/integration/test_ingestion_multi_source.py"
  - "mypy src/framework/ingestion/ --strict"
  - "ruff check src/framework/ingestion/"
regeneration: scaffold-then-edit
---

# ING-001 - Ingestion Engine Specification

**Status:** Active · 2026-06-20 · Skill: `insurelake-spec-codegen`  
**Execution Mode:** Batch Processing (PySpark)  
**Target DBR:** 15.4 LTS or later

---

## 1. Purpose & Scope

### Purpose
Orchestrate metadata-driven data ingestion from file-based sources into Unity Catalog Delta tables, with full ABC (Audit/Balance/Control) instrumentation, retry logic, and quarantine handling.

### In Scope
* **Execution modes:** Batch processing (PySpark on Databricks compute)
* **Load patterns:** Append-only (Phase 1), extensible for SCD1, SCD2, Full Refresh (Phase 2+)
* **Source types:** File-based only (CSV, JSON, Parquet, Delta)
* **Source cardinality:** Single-source AND multi-source ingestion (union pattern)
* **Write strategies:** Append flow (direct write to Delta tables)
* **ABC instrumentation:** All runs log audit, balance, and cost metrics
* **Error handling:** Configurable retry with exponential/linear backoff, batch-level quarantine
* **Configuration:** Fully metadata-driven (no hard-coded paths, catalogs, or behavior)

### Out of Scope
* Streaming mode (continuous processing) - deferred to Phase 2
* SCD2/AUTO CDC patterns - deferred to Phase 2 (requires MERGE logic)
* Non-declarative mode alternatives - N/A (Phase 1 is batch PySpark)
* JDBC/API/Kafka readers - deferred to Phase 2
* Record-level quarantine - deferred to Phase 2 (Phase 1: batch-level only)
* Data quality checks - framework is extensible for DQ, but implementation deferred to Phase 2
* Transformations - handled by Harmonization Framework

---

## 2. Requirements

### Functional Requirements

**FR-1: Metadata-Driven Execution**
* Engine reads all configuration from `LoadConfig`, `SourceConfig`, `TargetConfig` (no hard-coded values)
* Supports catalog/schema/table names as config parameters
* Supports multi-customer isolation via config namespacing

**FR-2: Single-Source & Multi-Source Ingestion**
* Single-source: Read from one `SourceConfig`, write to one `TargetConfig`
* Multi-source: Read from multiple `SourceConfig` entries (union pattern), write to one `TargetConfig`
* ABC logging must aggregate metrics across all sources in multi-source runs

**FR-3: Append-Only Pattern**
* Load pattern: `APPEND`
* Write mode: Direct append to Delta table (no MERGE, no deduplication)
* Idempotency: Handled by upstream (duplicate prevention outside engine scope)

**FR-4: ABC Instrumentation**
* Every run creates a `run_id` via `ABC.start_run()`
* Log audit metrics: `rows_read`, `rows_written`, `rows_rejected`, `start_time`, `end_time`, `duration_sec`, `status`
* Log balance check: Compare `rows_read` vs `rows_written` (for append-only)
* Log cost metrics: `dbu_consumed`, `duration_min`, `estimated_cost_usd` (Phase 2 implementation)
* Close run with `ABC.end_run()` and final status

**FR-5: Retry Logic**
* Configurable retry attempts (default: 3)
* Configurable backoff strategy: `exponential` OR `linear`
* Retry on transient errors (network, throttling, temporary unavailability)
* Fail immediately on fatal errors (schema mismatch, permission denied, invalid config)

**FR-6: Quarantine / Dead Letter Queue**
* Batch-level quarantine: If entire batch fails validation/write, move to quarantine table
* Quarantine table schema: Original source columns + metadata columns (`quarantine_id`, `run_id`, `quarantine_reason`, `quarantine_timestamp`)
* Quarantine table naming: `{target_catalog}.{target_schema}.{target_table}_quarantine`
* Configurable: Quarantine can be enabled/disabled via `LoadConfig.enable_quarantine`

**FR-7: Configuration Validation**
* Validate all config before execution (fail fast)
* Check: Catalogs/schemas exist, source paths are accessible, target tables exist or can be created
* Check: Required fields present (`source_id`, `target_id`, `load_pattern`)
* Check: Referential integrity (source/target references are valid)
* Check: File format compatibility (config format matches actual file type)

### Non-Functional Requirements

**NFR-1: Performance**
* Batch append ingestion: <5 min for 10M records × 20 columns (avg 1KB/row) on i4i.xlarge × 3 workers
* Multi-source union: Linear scaling (2x sources ≈ 2x time)
* Minimize shuffles (use Liquid Clustering on target tables)

**NFR-2: Reliability**
* Retry logic must succeed on transient failures (95th percentile: 2 attempts)
* ABC logging must never fail the run (defensive exception handling with try/except on ALL calls)
* Quarantine logic must never lose data (write-ahead, atomic commits)

**NFR-3: Observability**
* Every run emits ABC audit, balance, and cost records
* Failures log to `abc_control` with full stack trace
* Retry attempts logged to `abc_control` with attempt number

**NFR-4: Extensibility**
* Support new load patterns by adding strategy classes (no engine changes)
* Support new reader types by implementing `Reader` protocol (no engine changes)
* Support DQ checks via optional `Check` protocol hook (reserved, not implemented in Phase 1)

**NFR-5: Testability**
* Unit test coverage >80% (pytest + pytest-cov)
* Integration tests for: single-source append, multi-source append, retry, quarantine
* Type safety: mypy strict mode, no `Any` in public signatures

---

## 3. Interface - Exact Skeleton

**CRITICAL:** The generator MUST emit this interface exactly as specified. Deviations will cause downstream integration failures.

```python
# src/framework/ingestion/engine.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from pyspark.sql import DataFrame, SparkSession
from core.contracts import Engine, RunContext, RunResult
from core.metadata import LoadConfig, SourceConfig, TargetConfig
from core.sdk.abc import ABC, RunHandle

# Custom exceptions
class IngestionError(Exception):
    """Base exception for ingestion errors."""
    pass

class MaxRetriesExceededError(IngestionError):
    """Raised when maximum retry attempts are exceeded."""
    pass

class ConfigurationError(IngestionError):
    """Raised for invalid configuration."""
    pass

@dataclass
class NullRunHandle:
    """
    Placeholder RunHandle when ABC.start_run() fails.
    
    Allows engine to continue execution without ABC logging.
    All ABC operations will be no-ops with this handle.
    """
    run_id: str = "UNKNOWN"
    trace_id: str = "UNKNOWN"

@dataclass
class IngestionConfig:
    """Ingestion-specific configuration."""
    load: LoadConfig
    sources: List[SourceConfig]  # Multi-source support
    target: TargetConfig
    retry_config: Optional["RetryConfig"] = None
    enable_quarantine: bool = True

    validate_source_format: bool = True  # Set False to skip format validation for faster startup
@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    backoff_strategy: str = "exponential"  # "exponential" or "linear"
    initial_delay_sec: int = 1
    max_delay_sec: int = 60
    backoff_multiplier: float = 2.0  # For exponential backoff only

class IngestionEngine:
    """
    Orchestrates metadata-driven data ingestion from file sources to Unity Catalog Delta tables.
    
    Implements the Engine protocol from foundation.contracts.
    Supports single-source and multi-source ingestion with ABC instrumentation.
    """
    
    def __init__(
        self,
        spark: SparkSession,
        abc: ABC,
        reader: "Reader",  # From dataio.readers
        strategy: "LoadStrategy"  # From dataio.load_strategy
    ):
        """
        Initialize the Ingestion Engine.
        
        Args:
            spark: Active SparkSession
            abc: ABC SDK instance for audit/balance/control logging
            reader: Reader implementation (e.g., FileReader)
            strategy: LoadStrategy implementation (e.g., AppendStrategy)
        """
        self.spark = spark
        self.abc = abc
        self.reader = reader
        self.strategy = strategy
    
    def run(self, context: RunContext) -> RunResult:
        """
        Execute ingestion run. Implements Engine protocol.
        
        Args:
            context: RunContext with component, entity, run_type, params
            
        Returns:
            RunResult with status, metrics, run_id
        """
        pass
    
    def run_batch_append(
        self,
        config: IngestionConfig,
        run_handle: RunHandle
    ) -> RunResult:
        """
        Execute batch append ingestion (single or multi-source).
        
        Process:
        1. Validate configuration
        2. Read sources (union if multi-source)
        3. Apply LoadStrategy (append write)
        4. Log ABC metrics
        5. Return RunResult
        
        Args:
            config: IngestionConfig with load/source/target details
            run_handle: ABC RunHandle for audit logging
            
        Returns:
            RunResult with status and metrics
        """
        pass
    
    def validate_config(self, config: IngestionConfig) -> None:
        """
        Validate configuration before execution. Fail fast on invalid config.
        
        Checks:
        - Required fields present (source_id, target_id, load_pattern)
        - Catalogs and schemas exist
        - Source paths accessible and format-compatible
        - Target table exists or can be created
        - Referential integrity (source/target references valid)
        
        Args:
            config: IngestionConfig to validate
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass
    
    def create_quarantine_table(self, config: IngestionConfig) -> None:
        """
        Create quarantine table if it doesn't exist.
        
        Table name: {target_catalog}.{target_schema}.{target_table}_quarantine
        Schema: Original source columns + metadata columns
        
        Args:
            config: IngestionConfig with target details
        """
        pass
    
    def _read_sources(
        self,
        config: IngestionConfig,
        run_handle: RunHandle
    ) -> DataFrame:
        """
        Read data from sources (single or multi-source union).
        
        For multi-source:
        - Read each source independently
        - Union all DataFrames
        - Log aggregate metrics to ABC
        
        Args:
            config: IngestionConfig with sources list
            run_handle: ABC RunHandle for audit logging
            
        Returns:
            DataFrame with unioned data
        """
        pass
    
    def _retry_with_backoff(
        self,
        func: Callable[..., Any],
        config: IngestionConfig,
        run_handle: RunHandle,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute function with retry and backoff logic.
        
        Retry on transient errors:
        - Network errors (connection timeout, DNS)
        - Throttling errors (429, rate limit)
        - Temporary unavailability (503, service unavailable)
        
        Fail immediately on fatal errors:
        - Schema mismatch (mismatched columns)
        - Permission denied (401, 403)
        - Invalid configuration (400, bad request)
        
        Args:
            func: Function to execute with retry
            config: IngestionConfig with retry settings
            run_handle: ABC RunHandle for retry logging
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result from func
            
        Raises:
            MaxRetriesExceededError: If all retry attempts fail
            Exception: If fatal error occurs
        """
        pass
    
    def _quarantine_batch(
        self,
        df: DataFrame,
        config: IngestionConfig,
        run_handle: RunHandle,
        error_reason: str
    ) -> None:
        """
        Write failed batch to quarantine table.
        
        Args:
            df: DataFrame to quarantine
            config: IngestionConfig with quarantine settings
            run_handle: ABC RunHandle for quarantine logging
            error_reason: Reason for quarantine
        """
        pass
    
    def _log_abc_safe(
        self,
        log_func: Callable[..., None],
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Safely execute ABC logging (defensive exception handling).
        
        ABC failures must never propagate to main logic.
        
        Args:
            log_func: ABC logging function to call
            *args, **kwargs: Arguments to pass to log_func
        """
        pass
```

---

## 4. Inputs / Outputs

### Inputs

**Configuration (from Unity Catalog metadata tables):**
* `LoadConfig`: Load strategy, pattern, engine, schedule, checkpoint location
* `SourceConfig`: Source paths, format, connection details, credentials
* `TargetConfig`: Target catalog/schema/table, partition columns, clustering, retention
* `RetryConfig`: Retry attempts, backoff strategy, delays

**Data Sources:**
* File-based sources (CSV, JSON, Parquet, Delta)
* Single source OR multiple sources (union pattern)
* Paths: Unity Catalog Volumes (`/Volumes/catalog/schema/volume/path`), cloud storage (S3, ADLS, GCS)

### Outputs

**Data Outputs:**
* Unity Catalog Delta tables (append mode)
* Quarantine tables (batch-level rejected records)

**ABC Outputs (logged to Unity Catalog):**
* `abc_audit`: Run audit trail (run_id, feed_id, component, rows, timings, status)
* `abc_balance`: Balance checks (rows_read vs rows_written)
* `abc_control`: Control metadata (retry attempts, config snapshots)
* `abc_cost`: Cost metrics (dbu_consumed, duration_min, estimated_cost_usd) - Phase 2

**Return Value:**
* `RunResult`: Status (SUCCESS/FAILED), metrics (rows_read, rows_written, duration_sec), run_id

---

## 5. Design

### Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                       Ingestion Engine                             │
│  (Orchestrator - implements Engine protocol)                      │
└───────────────┬───────────────────────────────────────────────────┘
                │
                │ depends on
                │
    ┌───────────┴───────────┬──────────────────┬──────────────────┐
    │                       │                  │                  │
    ▼                       ▼                  ▼                  ▼
┌─────────┐         ┌─────────────┐    ┌──────────┐      ┌──────────┐
│  Reader │         │LoadStrategy │    │ABC SDK   │      │ConfigMgr │
│Protocol │         │  Protocol   │    │          │      │          │
└─────────┘         └─────────────┘    └──────────┘      └──────────┘
    │                       │                  │                  │
    │                       │                  │                  │
    ▼                       ▼                  ▼                  ▼
┌─────────┐         ┌─────────────┐    ┌──────────┐      ┌──────────┐
│FileReader│        │AppendStrat  │    │ABC Tables│      │UC Metadata│
│CSVReader │        │             │    │(Delta)   │      │(Delta)   │
│JSONReader│        │             │    │          │      │          │
└─────────┘         └─────────────┘    └──────────┘      └──────────┘
```

### Execution Flow - Batch Append (Single Source)

```
1. Client calls engine.run(RunContext)
   ↓
2. Engine parses RunContext.params → IngestionConfig
   ↓
3. Engine calls validate_config(config)
   ↓
4. ABC.start_run() → RunHandle
   ↓
5. Engine calls _read_sources(config, run_handle)
   ↓
6. Reader.read(source, load) → DataFrame
   ↓
7. ABC.log_audit(run_handle, rows_read=df.count())
   ↓
8. Engine calls strategy.apply(df, target, load)
   ↓
9. Strategy writes to Delta table (append mode)
   ↓
10. Count newly written rows: rows_written = df.count()
    ↓
11. ABC.log_balance(run_handle, rows_read, rows_written)
    ↓
12. ABC.log_cost(run_handle, duration) [Phase 2: add DBU calculation]
    ↓
13. ABC.end_run(run_handle, status="SUCCESS")
    ↓
14. Engine returns RunResult(status="SUCCESS", metrics={...})
```

### Execution Flow - Multi-Source Append

```
1-4. [Same as single-source]
   ↓
5. Engine calls _read_sources(config, run_handle)
   ↓
6. FOR EACH source IN config.sources:
   │   Reader.read(source, load) → DataFrame_i
   │   ABC.log_audit(run_handle, rows_read=df_i.count(), source_id=source.source_id)
   ↓
7. Union all DataFrames → df_union
   ↓
8. ABC.log_audit(run_handle, total_rows_read=df_union.count())
   ↓
9-14. [Same as single-source, using df_union]
```

### Execution Flow - Retry with Backoff

```
1. Engine calls _retry_with_backoff(func, config, run_handle)
   ↓
2. FOR attempt IN range(1, max_attempts + 1):
   │   TRY:
   │       result = func(*args, **kwargs)
   │       _log_abc_safe(abc.log_control, run_handle, control_type="RETRY_SUCCESS", attempt=attempt)
   │       RETURN result
   │   EXCEPT TransientError AS e:
   │       _log_abc_safe(abc.log_control, run_handle, control_type="RETRY_ATTEMPT", attempt=attempt, error=str(e))
   │       IF attempt < max_attempts:
   │           delay = calculate_delay(attempt, config.retry_config)
   │           time.sleep(delay)
   │           CONTINUE
   │       ELSE:
   │           RAISE MaxRetriesExceededError
   │   EXCEPT FatalError AS e:
   │       _log_abc_safe(abc.log_exception, run_handle, exception=e)
   │       RAISE e
   ↓
3. RAISE MaxRetriesExceededError
```

### Quarantine Flow (Batch-Level)

```
1. Engine attempts strategy.apply(df, target, load)
   ↓
2. IF write fails AND df exists in scope:
   │   _log_abc_safe(abc.log_control, run_handle, control_type="QUARANTINE_TRIGGER", reason=str(error))
   │   ↓
   │   IF config.enable_quarantine:
   │       ↓
   │       3. Add metadata columns to df:
   │          df_quarantine = df.withColumn("quarantine_id", uuid())
   │                            .withColumn("run_id", run_handle.run_id)
   │                            .withColumn("quarantine_reason", lit(str(error)))
   │                            .withColumn("quarantine_timestamp", current_timestamp())
   │       ↓
   │       4. Write to quarantine table:
   │          quarantine_table = f"{target.catalog}.{target.schema}.{target.table}_quarantine"
   │          df_quarantine.write.mode("append").saveAsTable(quarantine_table)
   │       ↓
   │       5. _log_abc_safe(abc.log_audit, run_handle, rows_rejected=df_quarantine.count())
   │   ↓
   │   RAISE original error (quarantine doesn't suppress failures)
```

### SOLID Principles Application

**Single Responsibility Principle (SRP):**
* `IngestionEngine`: Orchestration ONLY (no reading, writing, ABC logging logic)
* `Reader`: Reading ONLY (no writing, validation, or ABC)
* `LoadStrategy`: Writing ONLY (no reading, orchestration, or ABC)
* `ABC`: Audit/Balance/Control logging ONLY (no orchestration or data processing)

**Open/Closed Principle (OCP):**
* Engine is CLOSED for modification (stable orchestration logic)
* Engine is OPEN for extension via dependency injection (swap readers, strategies)
* New load patterns: Add `LoadStrategy` implementation, pass to engine constructor
* New source types: Add `Reader` implementation, pass to engine constructor

**Liskov Substitution Principle (LSP):**
* Any `Reader` can replace any other `Reader` (protocol compliance)
* Any `LoadStrategy` can replace any other `LoadStrategy` (protocol compliance)
* Engine doesn't know which concrete implementations it's using (structural typing)

**Interface Segregation Principle (ISP):**
* Protocols are minimal: `Reader` has ONE method (`read`), `LoadStrategy` has ONE method (`apply`)
* Engine doesn't depend on ABC methods it doesn't use (only `start_run`, `end_run`, `log_audit`, `log_balance`, `log_cost`)

**Dependency Inversion Principle (DIP):**
* Engine depends on abstractions (`Reader`, `LoadStrategy` protocols), not concrete implementations
* Concrete implementations injected at runtime (constructor injection)
* Testability: Mock `Reader`, `LoadStrategy`, `ABC` in unit tests

---

## 6. Logic / algorithm

**Logic / algorithm:** The Ingestion Engine orchestrates metadata-driven data ingestion through a sequence of deterministic steps: configuration validation, ABC run initiation, source reading (single or multi-source union), load strategy application, ABC metric logging, retry with exponential/linear backoff, and quarantine handling on failures. All steps follow the exact logic specified below.

**CRITICAL:** This section defines the EXACT logic the generator must implement. No improvisation allowed.

### Procedure

The Ingestion Engine executes ingestion in the following high-level sequence:

1. **Initialization**: Constructor accepts Spark, ABC, Reader, and LoadStrategy via dependency injection
2. **Run invocation**: `run()` method receives `RunContext` with configuration parameters
3. **Configuration validation**: `validate_config()` checks all prerequisites (catalogs exist, paths accessible, required fields present)
4. **ABC run start**: `ABC.start_run()` initiates audit logging and returns `RunHandle`
5. **Source reading**: `_read_sources()` reads single or multiple sources (union pattern)
6. **Load strategy application**: `strategy.apply()` writes data to target table (append)
7. **Balance check**: Compare `rows_read` vs `rows_written` (incremental count)
8. **Cost logging**: Log duration and placeholder DBU (Phase 2: implement actual calculation)
9. **ABC run end**: `ABC.end_run()` closes audit trail
10. **Result return**: `RunResult` with status and metrics

All steps include retry logic for transient errors and defensive ABC logging (errors don't propagate via `_log_abc_safe`).

### Decision rules

**Retry decision (transient vs fatal errors):**
* **Retry**: Network errors, throttling (429), temporary unavailability (503)
* **Fail immediately**: Schema mismatch, permission denied (401/403), invalid configuration

**Quarantine decision:**
* **Trigger**: If `config.enable_quarantine == True` AND write fails AND `df` exists in scope
* **Action**: Write failed batch to quarantine table with metadata, then re-raise original error
* **Skip**: If quarantine disabled OR df not in scope, fail without quarantine

**Multi-source union decision:**
* **Single source**: `len(config.sources) == 1` → read directly, no union
* **Multi-source**: `len(config.sources) > 1` → read each source, union with `allowMissingColumns=True`

**Load pattern routing:**
* `load_pattern == "APPEND"` → Direct append write (no MERGE)
* Other patterns deferred to Phase 2

### Key code fragments

**Retry with exponential backoff:**
```python
for attempt in range(1, retry_config.max_attempts + 1):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if is_fatal_error(e):
            raise  # No retry
        if attempt < retry_config.max_attempts:
            delay = initial_delay * (backoff_multiplier ** (attempt - 1))
            time.sleep(min(delay, max_delay))
        else:
            raise MaxRetriesExceededError(f"Failed after {attempt} attempts: {str(e)}")
```

**Multi-source union:**
```python
if len(config.sources) == 1:
    return self.reader.read(config.sources[0], config.load)
else:
    dfs = [self.reader.read(src, config.load) for src in config.sources]
    df_union = dfs[0]
    for df_i in dfs[1:]:
        df_union = df_union.unionByName(df_i, allowMissingColumns=True)
    return df_union
```

**Defensive ABC logging:**
```python
def _log_abc_safe(self, log_func: Callable[..., None], *args: Any, **kwargs: Any) -> None:
    try:
        log_func(*args, **kwargs)
    except Exception as e:
        # ABC failures don't propagate - log to stderr for debugging
        print(f"WARNING: ABC logging failed: {str(e)}", file=sys.stderr)
```

### Edge cases

**Empty source:**
* If source has zero records, proceed normally (ABC logs `rows_read=0`, `rows_written=0`)
* Balance check: `delta=0` (pass)

**Multi-source with schema mismatch:**
* Use `unionByName(..., allowMissingColumns=True)` to handle missing columns
* Missing columns filled with `null`

**Target table doesn't exist:**
* `strategy.apply()` creates table on first write (Delta auto-create)
* Quarantine table created lazily on first quarantine event

**All retry attempts exhausted:**
* Raise `MaxRetriesExceededError` with message: "Max retries exceeded (N attempts). Last error: {error}"
* ABC logs all retry attempts to `abc_control` (via `_log_abc_safe`)

**Quarantine table creation fails:**
* Log quarantine failure to `abc_control` but don't suppress original error
* Original write error propagates to caller

**ABC tables don't exist:**
* ABC SDK handles table creation automatically (defensive)
* If ABC table creation fails, log warning but don't fail ingestion run

**DataFrame not in scope during exception:**
* Check `'df' in locals()` before attempting quarantine
* Skip quarantine if df undefined

---

### Detailed Implementation

### 6.1 Engine Initialization

```python
def __init__(
    self,
    spark: SparkSession,
    abc: ABC,
    reader: "Reader",
    strategy: "LoadStrategy"
):
    """
    LOGIC:
    1. Validate inputs (not None)
    2. Check reader/strategy have required methods (hasattr check, not isinstance)
    3. Store as instance variables
    """
    if spark is None:
        raise ConfigurationError("SparkSession cannot be None")
    if abc is None:
        raise ConfigurationError("ABC instance cannot be None")
    
    # Protocol validation via duck typing (hasattr, not isinstance)
    if not hasattr(reader, 'read'):
        raise TypeError(f"reader must implement Reader protocol (have 'read' method), got {type(reader)}")
    if not hasattr(strategy, 'apply'):
        raise TypeError(f"strategy must implement LoadStrategy protocol (have 'apply' method), got {type(strategy)}")
    
    self.spark = spark
    self.abc = abc
    self.reader = reader
    self.strategy = strategy
```

### 6.2 Run Method (Engine Protocol)

```python
def run(self, context: RunContext) -> RunResult:
    """
    LOGIC:
    1. Parse context.params → IngestionConfig
    2. Validate configuration
    3. Start ABC run
    4. Execute run logic in try/except/finally with defensive ABC logging
    5. Return RunResult
    """
    # Parse config
    if "config" not in context.params:
        raise ConfigurationError("RunContext.params must contain 'config' key")
    
    config_dict = context.params["config"]
    config = IngestionConfig(**config_dict)
    
    # Validate config
    self.validate_config(config)
    
    # Start ABC run (with defensive logging)
    run_handle = None
    try:
        run_handle = self.abc.start_run(
            component=context.component,
            entity=context.entity,
            run_type=context.run_type
        )
    except Exception as e:
        # If ABC start fails, create NullRunHandle and continue
        print(f"WARNING: ABC start_run failed: {str(e)}\", file=sys.stderr)
        run_handle = NullRunHandle()  # Safe fallback - allows engine to continue
    
    try:
        # Route to appropriate run method
        if context.run_type == "batch_append":
            result = self.run_batch_append(config, run_handle)
        else:
            raise ConfigurationError(f"Unknown run_type: {context.run_type}")
        
        # End run with success (defensive)
        if not isinstance(run_handle, NullRunHandle):
            self._log_abc_safe(self.abc.end_run, run_handle, status="SUCCESS")
        
        return result
    
    except Exception as e:
        # Log exception and end run with failure (defensive)
        if not isinstance(run_handle, NullRunHandle):
            self._log_abc_safe(self.abc.log_exception, run_handle, exception=e)
            self._log_abc_safe(self.abc.end_run, run_handle, status="FAILED")
        raise
```

### 6.3 Validate Config

```python
def validate_config(self, config: IngestionConfig) -> None:
    """
    LOGIC:
    1. Check required fields
    2. Check catalog/schema existence
    3. Check source path accessibility AND format compatibility
    4. Check target table (OK if doesn't exist)
    5. Check retry config
    6. Raise ConfigurationError with clear message if any check fails
    """
    # Required fields
    if not config.load.load_id:
        raise ConfigurationError("LoadConfig.load_id is required")
    if not config.target.target_id:
        raise ConfigurationError("TargetConfig.target_id is required")
    if not config.sources:
        raise ConfigurationError("IngestionConfig.sources cannot be empty")
    if config.load.load_pattern not in ["APPEND"]:
        raise ConfigurationError(f"LoadConfig.load_pattern must be 'APPEND' in Phase 1, got '{config.load.load_pattern}'")
    
    # Check source paths exist AND format matches
    for source in config.sources:
        if source.source_type == "FILE":
            try:
                # Check if path is accessible
                test_df = self.spark.read.format("binaryFile").load(source.connection_string).limit(1)
                if test_df.isEmpty():
                    print(f"WARNING: Source path is empty: {source.connection_string}")
                
                # Verify format compatibility (optional - can be disabled for performance)
                if config.validate_source_format:
                    format_str = source.file_format.lower()
                    try:
                        test_read = self.spark.read.format(format_str).load(source.connection_string).limit(1)
                        test_read.count()  # Force execution
                    except Exception as format_error:
                        raise ConfigurationError(
                            f"Source format mismatch: Config specifies '{format_str}' but file at '{source.connection_string}' "
                            f"cannot be read with that format. Error: {str(format_error)}"
                        )
            except ConfigurationError:
                raise  # Re-raise format errors
            except Exception as e:
                raise ConfigurationError(f"Source path not accessible: {source.connection_string}. Error: {str(e)}")
    
    # Check target catalog exists
    catalogs = self.spark.sql(f"SHOW CATALOGS LIKE '{config.target.catalog_name}'").collect()
    if not catalogs:
        raise ConfigurationError(f"Target catalog does not exist: {config.target.catalog_name}")
    
    # Check target schema exists
    schemas = self.spark.sql(
        f"SHOW SCHEMAS IN {config.target.catalog_name} LIKE '{config.target.schema_name}'"
    ).collect()
    if not schemas:
        raise ConfigurationError(
            f"Target schema does not exist: {config.target.catalog_name}.{config.target.schema_name}"
        )
    
    # Check target table (OK if doesn't exist, will be created)
    target_full_name = f"{config.target.catalog_name}.{config.target.schema_name}.{config.target.table_name}"
    try:
        self.spark.sql(f"DESCRIBE TABLE {target_full_name}")
    except Exception:
        # Table doesn't exist - this is OK
        pass
    
    # Retry config validation
    if config.retry_config:
        if config.retry_config.max_attempts <= 0:
            raise ConfigurationError("RetryConfig.max_attempts must be > 0")
        if config.retry_config.backoff_strategy not in ["exponential", "linear"]:
            raise ConfigurationError(
                f"RetryConfig.backoff_strategy must be 'exponential' or 'linear', "
                f"got '{config.retry_config.backoff_strategy}'"
            )
        if config.retry_config.initial_delay_sec <= 0:
            raise ConfigurationError("RetryConfig.initial_delay_sec must be > 0")
        if config.retry_config.max_delay_sec < config.retry_config.initial_delay_sec:
            raise ConfigurationError("RetryConfig.max_delay_sec must be >= initial_delay_sec")
```

### 6.4 Run Batch Append

```python
def run_batch_append(
    self,
    config: IngestionConfig,
    run_handle: RunHandle
) -> RunResult:
    """
    LOGIC:
    1. Log run start (defensive)
    2. Read sources with retry
    3. Count source rows
    4. Apply load strategy with retry
    5. Count newly written rows (same as source count for append)
    6. Log balance check (compare rows_read vs rows_written)
    7. Log cost (Phase 2: add DBU calculation)
    8. Return RunResult
    9. Handle quarantine on failure (if df exists)
    """
    import time
    from datetime import datetime
    
    start_time = datetime.now()
    df = None  # Initialize to track scope
    
    # Log run start (defensive)
    self._log_abc_safe(
        self.abc.log_audit,
        run_handle,
        status="STARTED",
        feed_id=config.load.load_id,
        component="IngestionEngine",
        run_type="batch_append"
    )
    
    try:
        # Read sources with retry
        df = self._retry_with_backoff(
            self._read_sources,
            config,
            run_handle,
            config,
            run_handle
        )
        
        # Cache DataFrame to avoid redundant scans during count and write
        # Note: Only beneficial if DataFrame is used multiple times (e.g., count + write + quarantine)
        df.cache()
        
        # Count source rows
        rows_read = df.count()
        self._log_abc_safe(self.abc.log_audit, run_handle, rows_read=rows_read)
        
        # Apply load strategy with retry
        self._retry_with_backoff(
            self.strategy.apply,
            config,
            run_handle,
            df,
            config.target,
            config.load
        )
        
        # Unpersist DataFrame after write to free memory
        df.unpersist()
        
        # For append, rows_written == rows_read (no deduplication)
        rows_written = rows_read
        self._log_abc_safe(self.abc.log_audit, run_handle, rows_written=rows_written)
        
        # Log balance check
        delta = rows_written - rows_read  # Should be 0 for append
        self._log_abc_safe(
            self.abc.log_balance,
            run_handle,
            check_type="APPEND_BALANCE",
            source_count=rows_read,
            target_count=rows_written,
            delta=delta,
            reconciliation_status="PASS" if delta == 0 else "FAIL"
        )
        
        # Log cost (Phase 2: implement actual DBU calculation)
        end_time = datetime.now()
        duration_min = (end_time - start_time).total_seconds() / 60.0
        self._log_abc_safe(
            self.abc.log_cost,
            run_handle,
            resource_type="BATCH_INGESTION",
            dbu_consumed=0.0,  # TODO Phase 2: Calculate actual DBU consumption
            duration_min=duration_min,
            estimated_cost_usd=0.0  # TODO Phase 2: Calculate based on DBU rate
        )
        
        # Return result
        return RunResult(
            status="SUCCESS",
            metrics={
                "rows_read": rows_read,
                "rows_written": rows_written,
                "duration_sec": (end_time - start_time).total_seconds()
            },
            run_id=run_handle.run_id if run_handle else None
        )
    
    except Exception as e:
        # Handle quarantine if enabled AND df exists in scope
        if config.enable_quarantine and 'df' in locals() and df is not None:
            try:
                self._quarantine_batch(df, config, run_handle, str(e))
            except Exception as quarantine_error:
                # Log quarantine failure but don't suppress original error
                self._log_abc_safe(
                    self.abc.log_control,
                    run_handle,
                    control_type="QUARANTINE_FAILED",
                    error=str(quarantine_error)
                )
        
        # Re-raise original error
        raise
```

### 6.5 Read Sources (Single & Multi-Source)

```python
def _read_sources(
    self,
    config: IngestionConfig,
    run_handle: RunHandle
) -> DataFrame:
    """
    LOGIC:
    1. Single source: read directly
    2. Multi-source: read each, log per-source, union with allowMissingColumns
    3. Log total metrics (defensive)
    4. Return DataFrame
    """
    if len(config.sources) == 1:
        # Single source
        df = self.reader.read(config.sources[0], config.load)
        return df
    else:
        # Multi-source union
        dfs = []
        for source in config.sources:
            df_i = self.reader.read(source, config.load)
            
            # Log per-source metrics (defensive)
            
            # PERFORMANCE NOTE: Per-source counting triggers a full scan of df_i.
            # Trade-off: Detailed observability (per-source metrics) vs. performance (skip counts).
            # For large multi-source loads, consider making per-source logging optional.
            source_count = df_i.count()
            self._log_abc_safe(
                self.abc.log_audit,
                run_handle,
                rows_read=source_count,
                source_id=source.source_id,
                component="IngestionEngine._read_sources"
            )
            
            dfs.append(df_i)
        
        # Union all DataFrames
        df_union = dfs[0]
        for df_i in dfs[1:]:
            df_union = df_union.unionByName(df_i, allowMissingColumns=True)
        
        # Log total metrics (defensive)
        total_count = df_union.count()
        self._log_abc_safe(
            self.abc.log_audit,
            run_handle,
            total_rows_read=total_count,
            total_sources=len(config.sources),
            component="IngestionEngine._read_sources"
        )
        
        return df_union
```

### 6.6 Retry with Backoff

```python
def _retry_with_backoff(
    self,
    func: Callable[..., Any],
    config: IngestionConfig,
    run_handle: RunHandle,
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    LOGIC:
    1. Get retry config
    2. Define error classification functions
    3. Loop through retry attempts
    4. Execute function, classify errors, retry or fail accordingly
    5. Log all attempts (defensive)
    """
    import time
    import sys
    
    # Get retry config
    retry_config = config.retry_config if config.retry_config else RetryConfig()
    
    def is_transient_error(e: Exception) -> bool:
        """Check if error is transient (retryable)."""
        error_msg = str(e).lower()
        error_type = type(e).__name__
        
        # Network errors
        if error_type in ["ConnectionError", "TimeoutError"]:
            return True
        if "connection" in error_msg or "timeout" in error_msg:
            return True
        
        # Throttling
        if "429" in error_msg or "rate limit" in error_msg or "throttl" in error_msg:
            return True
        
        # Temporary unavailability
        if "503" in error_msg or "temporarily unavailable" in error_msg or "service unavailable" in error_msg:
            return True
        
        return False
    
    def is_fatal_error(e: Exception) -> bool:
        """Check if error is fatal (not retryable)."""
        error_msg = str(e).lower()
        error_type = type(e).__name__
        
        # Schema mismatch
        if "AnalysisException" in error_type and ("mismatch" in error_msg or "cannot resolve" in error_msg):
            return True
        
        # Permission denied
        if error_type in ["PermissionError", "PermissionDenied"]:
            return True
        if "401" in error_msg or "403" in error_msg or "permission denied" in error_msg:
            return True
        
        # Invalid config
        if error_type in ["ValueError", "ConfigurationError", "IllegalArgumentException"]:
            return True
        
        return False
    
    def calculate_delay(attempt: int, retry_config: RetryConfig) -> float:
        """Calculate delay for next retry attempt."""
        if retry_config.backoff_strategy == "exponential":
            delay = retry_config.initial_delay_sec * (retry_config.backoff_multiplier ** (attempt - 1))
        else:  # linear
            delay = retry_config.initial_delay_sec * attempt
        
        # Cap at max_delay_sec
        return min(delay, retry_config.max_delay_sec)
    
    # Execute with retry
    last_error = None
    had_error = False
    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            
            # Log retry success (only if we recovered from a previous error)
            if had_error and attempt > 1:
                self._log_abc_safe(
                    self.abc.log_control,
                    run_handle,
                    control_type="RETRY_SUCCESS",
                    attempt=attempt
                )
            
            return result
        
        except Exception as e:
            last_error = e
            had_error = True
            
            # Check if error is fatal
            if is_fatal_error(e):
                self._log_abc_safe(
                    self.abc.log_exception,
                    run_handle,
                    exception=e,
                    error_type="FATAL"
                )
                raise
            
            # Check if error is transient OR unknown (default to retry for safety)
            if is_transient_error(e) or not is_fatal_error(e):
                self._log_abc_safe(
                    self.abc.log_control,
                    run_handle,
                    control_type="RETRY_ATTEMPT",
                    attempt=attempt,
                    error=str(e),
                    error_classification="TRANSIENT" if is_transient_error(e) else "UNKNOWN_RETRYABLE"
                )
                
                # Retry if attempts remaining
                if attempt < retry_config.max_attempts:
                    delay = calculate_delay(attempt, retry_config)
                    time.sleep(delay)
                    continue
                else:
                    # Max retries exceeded
                    raise MaxRetriesExceededError(
                        f"Max retries exceeded ({retry_config.max_attempts} attempts). Last error: {str(e)}"
                    )
    
    # Should never reach here, but for safety
    raise MaxRetriesExceededError(
        f"Max retries exceeded ({retry_config.max_attempts} attempts). Last error: {str(last_error)}"
    )
```

### 6.7 Quarantine Batch (Batch-Level)

```python
def _quarantine_batch(
    self,
    df: DataFrame,
    config: IngestionConfig,
    run_handle: RunHandle,
    error_reason: str
) -> None:
    """
    LOGIC:
    1. Add metadata columns to DataFrame
    2. Build quarantine table name
    3. Create quarantine table if not exists
    4. Write DataFrame to quarantine table
    5. Log ABC metrics (defensive)
    """
    from pyspark.sql.functions import lit, current_timestamp
    import uuid
    
    # Add metadata columns
    df_quarantine = df.withColumn("quarantine_id", lit(str(uuid.uuid4()))) \
                      .withColumn("run_id", lit(run_handle.run_id if run_handle else "UNKNOWN")) \
                      .withColumn("quarantine_reason", lit(error_reason)) \
                      .withColumn("quarantine_timestamp", current_timestamp())
    
    # Build quarantine table name
    quarantine_table = f"{config.target.catalog_name}.{config.target.schema_name}.{config.target.table_name}_quarantine"
    
    # Create quarantine table if not exists
    self.create_quarantine_table(config)
    
    # Write to quarantine table
    df_quarantine.write.mode("append").saveAsTable(quarantine_table)
    
    # Log ABC metrics (defensive)
    quarantine_count = df_quarantine.count()
    self._log_abc_safe(
        self.abc.log_audit,
        run_handle,
        rows_rejected=quarantine_count
    )
    self._log_abc_safe(
        self.abc.log_control,
        run_handle,
        control_type="QUARANTINE_BATCH",
        reason=error_reason,
        quarantine_table=quarantine_table,
        rows_quarantined=quarantine_count
    )
```

### 6.8 Create Quarantine Table

```python
def create_quarantine_table(self, config: IngestionConfig) -> None:
    """
    LOGIC:
    1. Build quarantine table name
    2. Check if table exists (RETURN if yes)
    3. Get target table schema (if exists)
    4. Add metadata columns to schema
    5. Create quarantine table
    """
    from pyspark.sql.functions import to_date
    
    # Build quarantine table name
    quarantine_table = f"{config.target.catalog_name}.{config.target.schema_name}.{config.target.table_name}_quarantine"
    
    # Check if table exists
    try:
        self.spark.sql(f"DESCRIBE TABLE {quarantine_table}")
        return  # Table exists, nothing to do
    except Exception:
        pass  # Table doesn't exist, create it
    
    # Get target table schema (if exists)
    target_table = f"{config.target.catalog_name}.{config.target.schema_name}.{config.target.table_name}"
    try:
        target_df = self.spark.table(target_table).limit(0)
        
        # Add metadata columns
        from pyspark.sql.types import StringType, TimestampType
        from pyspark.sql.functions import lit, current_timestamp
        
        quarantine_df = target_df.withColumn("quarantine_id", lit("").cast(StringType())) \
                                  .withColumn("run_id", lit("").cast(StringType())) \
                                  .withColumn("quarantine_reason", lit("").cast(StringType())) \
                                  .withColumn("quarantine_timestamp", current_timestamp())
        
        # Create table with schema - partition by date of quarantine_timestamp
        quarantine_df.write.format("delta") \
                     .option("delta.enableChangeDataFeed", "true") \
                     .option("delta.autoOptimize.optimizeWrite", "true") \
                     .option("delta.autoOptimize.autoCompact", "true") \
                     .partitionBy(to_date("quarantine_timestamp")) \
                     .saveAsTable(quarantine_table)
    
    except Exception:
        # Target table doesn't exist yet - create empty quarantine with metadata only
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {quarantine_table} (
          quarantine_id STRING NOT NULL,
          run_id STRING NOT NULL,
          quarantine_reason STRING NOT NULL,
          quarantine_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        USING DELTA
        PARTITIONED BY (DATE(quarantine_timestamp))
        TBLPROPERTIES (
          'delta.enableChangeDataFeed' = 'true',
          'delta.autoOptimize.optimizeWrite' = 'true',
          'delta.autoOptimize.autoCompact' = 'true'
        )
        """
        self.spark.sql(ddl)
```

### 6.9 Defensive ABC Logging

```python
def _log_abc_safe(
    self,
    log_func: Callable[..., None],
    *args: Any,
    **kwargs: Any
) -> None:
    """
    LOGIC:
    1. Try to execute ABC logging function
    2. Catch all exceptions
    3. Log to stderr (don't propagate)
    """
    import sys
    
    try:
        log_func(*args, **kwargs)
    except Exception as e:
        # ABC failures don't propagate - log to stderr for debugging
        print(f"WARNING: ABC logging failed for {log_func.__name__}: {str(e)}", file=sys.stderr)
```

---

## 7. Guardrails & Constraints

**CRITICAL:** These guardrails MUST be enforced by the generator to prevent hallucinations and ensure deterministic code generation.

### 7.1 Configuration Guardrails

**NO HARD-CODED VALUES:**
* ❌ NEVER: `catalog = "insurelake_bronze"`
* ✅ ALWAYS: `catalog = config.target.catalog_name`

**NO DEFAULT PATHS:**
* ❌ NEVER: `path = "/mnt/data/default"`
* ✅ ALWAYS: `path = source.connection_string`

**NO ASSUMED FORMATS:**
* ❌ NEVER: `format = "parquet"`  (without checking config)
* ✅ ALWAYS: `format = source.file_format`

### 7.2 ABC Logging Guardrails

**DEFENSIVE EXCEPTION HANDLING:**
* ALL ABC logging calls must use `_log_abc_safe()` helper
* ABC failures must NEVER propagate to main logic

```python
# ✅ CORRECT
self._log_abc_safe(self.abc.log_audit, run_handle, rows_read=count)

# ❌ WRONG (direct call - ABC failure kills run)
self.abc.log_audit(run_handle, rows_read=count)
```

### 7.3 Retry Logic Guardrails

**TRANSIENT vs FATAL:**
* ONLY retry transient errors (network, throttling, temporary unavailability)
* NEVER retry fatal errors (schema mismatch, permission denied, invalid config)
* DEFAULT to retry for unknown errors (fail-safe approach)

**MAX ATTEMPTS:**
* ALWAYS respect `retry_config.max_attempts`
* NEVER infinite loops

### 7.4 Schema Guardrails

**NO SCHEMA ASSUMPTIONS:**
* ❌ NEVER: `df.select("id", "name", "timestamp")`  (assumed columns)
* ✅ ALWAYS: Infer schema from source or config

**SCHEMA EVOLUTION:**
* Enable schema evolution on Delta tables: `mergeSchema=true`
* Allow missing columns in multi-source unions: `unionByName(..., allowMissingColumns=True)`

### 7.5 Databricks Syntax Guardrails

**USE LATEST SYNTAX:**
* Delta Lake: `OPTIMIZE`, `VACUUM`, `LIQUID CLUSTERING` (latest syntax)
* Unity Catalog: Fully qualified names (`catalog.schema.table`), NOT legacy `database.table`

**VERIFY AGAINST DOCS:**
* Cross-reference all Spark/Delta/Databricks APIs with official documentation
* Include doc links in comments for non-obvious APIs

### 7.6 Dependency Guardrails

**PROTOCOL COMPLIANCE:**
* ONLY call methods defined in protocol interfaces
* Use duck typing (hasattr checks) NOT isinstance for protocol validation

```python
# ✅ CORRECT (protocol check via duck typing)
if not hasattr(reader, 'read'):
    raise TypeError("reader must implement Reader protocol")

# ❌ WRONG (isinstance doesn't work with protocols without @runtime_checkable)
if not isinstance(reader, Reader):
    raise TypeError("reader must implement Reader protocol")
```

**DEPENDENCY INJECTION:**
* NEVER instantiate readers/strategies inside engine
* ALWAYS accept via constructor (DIP compliance)

### 7.7 Testing Guardrails

**MOCKING:**
* ALL unit tests must mock external dependencies (Spark, ABC, Reader, Strategy)
* Integration tests run against real Spark (local mode or cluster)

**COVERAGE:**
* Minimum 80% line coverage (enforced by pytest-cov)
* 100% coverage for critical paths (config validation, retry logic, quarantine)

---

## 8. Error Handling

### Error Categories

**Configuration Errors (Fail Fast):**
* Invalid config (missing required fields)
* Catalog/schema doesn't exist
* Source path not accessible or format mismatch
* Invalid retry config

**Transient Errors (Retry):**
* Network errors (connection timeout, DNS)
* Throttling (rate limit, 429)
* Temporary unavailability (503, service unavailable)

**Fatal Errors (Fail Immediately):**
* Schema mismatch (column type mismatch)
* Permission denied (401, 403)
* Invalid credentials

**ABC Errors (Log & Continue):**
* ABC table write failure
* ABC schema mismatch
* ABC permission denied

### Error Responses

**Configuration Errors:**
```python
raise ConfigurationError("Target catalog does not exist: {catalog}. Please verify configuration.")
```

**Transient Errors (after max retries):**
```python
raise MaxRetriesExceededError("Max retries exceeded (3 attempts). Last error: {error}. Check network connectivity and retry.")
```

**Fatal Errors:**
```python
raise PermissionError("Permission denied for catalog {catalog}. Request USAGE and SELECT privileges.")
```

---

## 9. Performance Considerations

### Optimization Strategies

**Liquid Clustering:**
* Target tables should use Liquid Clustering on partition columns
* Defined in `TargetConfig.liquid_clustering_columns`
* Engine doesn't manage clustering (Delta handles automatically)

**Partition Pruning:**
* Use partition columns in WHERE clauses for reads
* Defined in `TargetConfig.partition_columns`

**Broadcast Joins:**
* For small lookup tables (< 10MB)
* Use `spark.sql.autoBroadcastJoinThreshold` config

**Caching:**
* Cache DataFrames only if read multiple times (e.g., multi-target writes)
* Unpersist after use to free memory

**Parallelism:**
* Use `spark.sql.shuffle.partitions` for large datasets (default: 200)
* Use `df.repartition(N)` before writes for balanced parallelism

### Performance Targets

**Batch Append (Single Source):**
* 10M records × 20 columns (avg 1KB/row): < 5 minutes on i4i.xlarge × 3 workers
* 100M records × 20 columns: < 30 minutes on same cluster

**Multi-Source Union (3 sources):**
* 10M records per source: < 10 minutes on i4i.xlarge × 3 workers

---

## 10. Testing Strategy

### Unit Tests

**Coverage:**
* `test_validate_config`: All validation checks (required fields, catalog existence, format compatibility)
* `test_read_sources_single`: Single source read
* `test_read_sources_multi`: Multi-source union
* `test_retry_transient_success`: Retry succeeds on transient error
* `test_retry_fatal_fail`: Retry fails immediately on fatal error
* `test_quarantine_batch`: Batch-level quarantine on write failure
* `test_log_abc_safe`: Defensive ABC logging (exception doesn't propagate)
* `test_null_run_handle`: Engine continues with NullRunHandle when ABC fails

**Mocking:**
* Mock `SparkSession`, `ABC`, `Reader`, `LoadStrategy`
* Use `pytest-mock` for dependency injection

### Integration Tests

**Coverage:**
* `test_batch_append_single_source`: End-to-end single source append
* `test_batch_append_multi_source`: End-to-end multi-source union + append
* `test_retry_network_error`: Retry on network failure (simulated)
* `test_quarantine_write_failure`: Quarantine on write failure (simulated)

**Environment:**
* Local Spark (pyspark standalone)
* Mock Unity Catalog (local Delta tables)
* Mock ABC tables (local Delta tables)

### Counter-Examples (What NOT to Do)

**❌ DON'T: Hard-code configuration values**
```python
# BAD: Hard-coded catalog name
catalog = "insurelake_bronze"
```
✅ DO: Use configuration
```python
# GOOD: Read from config
catalog = config.target.catalog_name
```

**❌ DON'T: Retry fatal errors**
```python
# BAD: Retry on schema mismatch
for attempt in range(3):
    try:
        write_to_table(df)
    except AnalysisException:
        time.sleep(1)  # Schema errors won't fix themselves!
```
✅ DO: Fail fast on fatal errors
```python
# GOOD: Detect fatal errors and fail immediately
if is_fatal_error(e):
    raise
```

**❌ DON'T: Use isinstance for protocol checks**
```python
# BAD: isinstance doesn't work with structural protocols
if not isinstance(reader, Reader):
    raise TypeError("reader must implement Reader protocol")
```
✅ DO: Use duck typing (hasattr)
```python
# GOOD: Check for protocol methods
if not hasattr(reader, 'read'):
    raise TypeError("reader must implement Reader protocol")
```

---

## 11. Observability

### ABC Instrumentation Points

**Run Start:**
* `abc.start_run()` → `run_id`, `trace_id`
* Log: `component="IngestionEngine"`, `entity="{feed_id}"`, `run_type="batch_append"`

**Read Phase:**
* Log per-source: `rows_read`, `source_id`, `source_path`
* Log aggregate (multi-source): `total_rows_read`, `total_sources`

**Write Phase:**
* Log post-write: `rows_written` (equals rows_read for append)

**Balance Check:**
* Log: `rows_read`, `rows_written`, `delta`, `reconciliation_status`

**Retry Attempts:**
* Log: `control_type="RETRY_ATTEMPT"`, `attempt`, `error`, `error_classification`
* Log: `control_type="RETRY_SUCCESS"`, `attempt`

**Quarantine:**
* Log: `control_type="QUARANTINE_BATCH"`, `reason`, `quarantine_table`, `rows_quarantined`

**Run End:**
* `abc.end_run()` → `status="SUCCESS|FAILED"`
* Log: `duration_sec`, `dbu_consumed` (Phase 2), `estimated_cost_usd` (Phase 2)

### Metrics to Monitor

**Success Rate:**
* `COUNT(status="SUCCESS") / COUNT(*) FROM abc_audit`

**Retry Rate:**
* `COUNT(control_type="RETRY_ATTEMPT") / COUNT(run_id) FROM abc_control`

**Quarantine Rate:**
* `SUM(rows_rejected) / SUM(rows_read) FROM abc_audit`

**Performance:**
* P50, P95, P99 of `duration_sec` by `feed_id`

---

## 12. References

### Databricks Documentation
* [Delta Lake](https://docs.databricks.com/delta/index.html)
* [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/index.html)
* [Liquid Clustering](https://docs.databricks.com/en/delta/clustering.html)
* [PySpark API Reference](https://spark.apache.org/docs/latest/api/python/)

### Internal Specs
* [abc-sdk-spec.md](../foundation/abc-sdk-spec.md) - ABC SDK specification
* [config-model-spec.md](../foundation/config-model-spec.md) - Config model specification
* [contracts-spec.md](../foundation/contracts-spec.md) - Core contracts specification
* [file-readers-spec.md](../dataio/file-readers-spec.md) - File readers specification
* [append-strategy-spec.md](../dataio/append-strategy-spec.md) - Append strategy specification
* [CAPABILITY_REGISTRY.md](../CAPABILITY_REGISTRY.md) - Capability registry and architectural decisions

### Project Documentation
* [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) - Project architecture and context
* [INGESTION_READINESS_REPORT.md](../INGESTION_READINESS_REPORT.md) - Readiness assessment

---

## 13. Acceptance Criteria

**Code Generation:**
* [ ] Generator emits exact interface from §3 (no deviations)
* [ ] All public methods have type hints (no `Any` in signatures except `Callable[..., Any]`)
* [ ] All guardrails from §7 enforced in generated code
* [ ] Custom exceptions defined (IngestionError, MaxRetriesExceededError, ConfigurationError)
* [ ] NullRunHandle class implemented for safe ABC failure handling

**Functional:**
* [ ] Single-source batch append: 10M records × 20 columns, <5 min on i4i.xlarge × 3
* [ ] Multi-source batch append: 3 sources × 10M records, <10 min on same cluster
* [ ] Retry succeeds on transient errors (95th percentile: 2 attempts)
* [ ] Retry defaults to retrying unknown errors (fail-safe behavior)
* [ ] Quarantine captures failed batches (100% data retention)
* [ ] Quarantine only triggered when DataFrame is in scope
* [ ] Balance check compares rows_read vs rows_written (not table count)

**Performance:**
* [ ] DataFrame cached before count to avoid redundant scans
* [ ] DataFrame unpersisted after write to free memory
* [ ] Format validation optional via validate_source_format flag
* [ ] Per-source counting documented with performance trade-offs


**Non-Functional:**
* [ ] Unit test coverage >80% (pytest-cov)
* [ ] Integration tests pass (batch append, multi-source, retry, quarantine)
* [ ] Type safety: mypy strict mode (zero errors)
* [ ] Linting: ruff check (zero errors)

**Observability:**
* [ ] Every run logs to ABC (audit, balance, cost) via _log_abc_safe
* [ ] Retry attempts logged to abc_control with error classification
* [ ] Quarantine events logged to abc_control
* [ ] ABC failures never propagate (defensive logging)
* [ ] NullRunHandle allows engine to continue when ABC unavailable

**Documentation:**
* [ ] All public methods documented (docstrings)
* [ ] README.md with usage examples
* [ ] Architecture diagrams (execution flow, component diagram)

---

**End of Specification**
