# InsureLake Capability Registry

**Purpose:** Central registry of all capabilities (functions, classes, protocols, features) provided by InsureLake framework components  
**Status:** Living Document  
**Last Updated:** 2026-06-20  
**Owner:** EY

---

## 1. Overview

This registry catalogs every **capability** (function, class, protocol, interface, or feature) provided by the InsureLake framework. Each capability is tagged to its providing spec, enabling:

* **Dependency resolution** - Understand what capabilities a component needs
* **Impact analysis** - Find what depends on a capability before changing it
* **Discovery** - Locate where a capability is implemented
* **Build planning** - Resolve transitive dependencies for selective builds

---

## 2. Registry Structure

Each capability entry includes:

| Field | Description |
|-------|-------------|
| **Capability Name** | Unique identifier (function, class, or protocol name) |
| **Type** | `class`, `function`, `protocol`, `dataclass`, `constant`, `feature` |
| **Provided By** | Spec ID that provides this capability |
| **Module Path** | Python import path (e.g., `src.core.sdk.abc`) |
| **Status** | `active`, `draft`, `deprecated` |
| **Depends On** | Other capabilities this one requires |
| **Used By** | Specs that depend on this capability |

---

## 3. Foundation Capabilities

### 3.1 ABC SDK (`foundation.abc-sdk`)

**Module:** `src/core/sdk/`  
**Status:** Active  
**Spec:** `specs/foundation/abc-sdk-spec.md`

| Capability | Type | Description | Dependencies |
|------------|------|-------------|--------------|
| `ABC` | class | Main SDK class for Audit/Balance/Control logging | `SparkSession` |
| `RunHandle` | dataclass | Container for `run_id` and `trace_id` | None |
| `start_run` | function | Initiate a new run, return RunHandle | `ABC` |
| `end_run` | function | Close a run with final status | `ABC`, `RunHandle` |
| `log_audit` | function | Log audit metrics (rows, timings, identity) | `ABC`, `RunHandle` |
| `log_balance` | function | Log balance/reconciliation checks | `ABC`, `RunHandle` |
| `log_dq` | function | Log data quality rule outcomes | `ABC`, `RunHandle` |
| `log_exception` | function | Log structured exceptions | `ABC`, `RunHandle` |
| `log_cost` | function | Log cost and consumption metrics | `ABC`, `RunHandle` |

**ABC Tables:**
* `abc_audit` - Run audit trail
* `abc_balance` - Balance and reconciliation checks
* `abc_control` - DQ results and exceptions
* `abc_cost` - Cost and consumption tracking

---

### 3.2 Config Model (`core.metadata`)

**Module:** `src/core/metadata/`  
**Status:** Active  
**Depends On:** `foundation.abc-sdk`

| Capability | Type | Description | Dependencies |
|------------|------|-------------|--------------|
| `SourceConfig` | dataclass | Source connection and format configuration | None |
| `TargetConfig` | dataclass | Target table and write configuration | None |
| `LoadConfig` | dataclass | Load strategy and execution parameters | `SourceConfig`, `TargetConfig` |
| `DQRuleConfig` | dataclass | Data quality rule configuration | None |
| `TransformConfig` | dataclass | Transformation rule configuration | None |
| `ConfigLoader` | class | Load configurations from metadata tables | All config models |

**Metadata Tables:**
* `src_source` - Source definitions
* `tgt_target` - Target definitions
* `load_config` - Load configurations
* `dq_rules` - Data quality rules
* `transform_rules` - Transformation rules

---

### 3.3 Core Contracts (`core.contracts`)

**Module:** `src/core/contracts/`  
**Status:** Active  
**Depends On:** `core.metadata`

| Capability | Type | Description | Dependencies |
|------------|------|-------------|--------------|
| `Reader` | protocol | Read data from sources to DataFrame | `SourceConfig`, `LoadConfig` |
| `LoadStrategy` | protocol | Write DataFrame to targets | `TargetConfig`, `LoadConfig` |
| `Engine` | protocol | Orchestrate framework runs | `RunContext`, `RunResult` |
| `Check` | protocol | Evaluate DQ rules against DataFrame | `DQRuleConfig`, `CheckResult` |
| `Masker` | protocol | Apply masking to DataFrame columns | `MaskingRuleConfig` |
| `RunContext` | dataclass | Execution context for engines | None |
| `RunResult` | dataclass | Execution outcome container | None |
| `CheckResult` | dataclass | DQ check result container | None |

**Design Pattern:** Protocol-based (structural typing, `@runtime_checkable`)

---

### 3.4 Schema Codegen (`scripts.codegen`)

**Module:** `scripts/codegen/`  
**Status:** Active  
**Depends On:** `core.metadata`

| Capability | Type | Description | Dependencies |
|------------|------|-------------|--------------|
| `sql_type` | function | Convert Python type to SQL type | None |
| `model_to_ddl` | function | Generate CREATE TABLE DDL from config model | `TargetConfig` |
| `model_to_jsonschema` | function | Generate JSON Schema from config model | `TargetConfig` |
| `generate` | function | Main generation orchestrator | All above |
| `main` | function | CLI entry point | `generate` |

**Outputs:** 
* SQL DDL files
* JSON Schema files

---

### 3.5 Spec Validator (`foundation.spec-validator`)

**Module:** `scripts/speccheck/`  
**Status:** Active  
**Depends On:** None

| Capability | Type | Description | Dependencies |
|------------|------|-------------|--------------|
| `Finding` | dataclass | Validation finding container | None |
| `parse_front_matter` | function | Extract YAML front-matter from spec | None |
| `check_spec` | function | Validate single spec file | `Finding` |
| `check_corpus` | function | Validate all specs in directory | `check_spec` |
| `validate` | function | Main validation orchestrator | All above |
| `main` | function | CLI entry point | `validate` |

**Validation Rules:**
* Front-matter completeness
* SOLID principles documentation
* Acceptance criteria
* Dependency resolution

---

## 4. Agentic Capabilities

### 4.1 Capability Registry & Resolver (`agentic.capability-registry`)

**Module:** `src/agents/registry/`  
**Status:** Active  
**Depends On:** None

| Capability | Type | Description | Dependencies |
|------------|------|-------------|--------------|
| `Capability` | dataclass | Capability metadata (framework, feature, spec_id) | None |
| `load_registry` | function | Scan specs and build capability registry | None |
| `menu` | function | Build framework → features menu | `Capability` |
| `resolve_selection` | function | Resolve selected specs + dependencies | `load_registry` |
| `build_plan` | function | Generate topologically-ordered build plan | `resolve_selection` |

**Input:** Spec front-matter (YAML)  
**Output:** Menu structure, build plans

---

## 5. Data I/O Capabilities

### 5.1 Readers (`dataio.readers.*`)

**Module:** `src/readers/`  
**Status:** Draft (pending Phase 1)  
**Depends On:** `core.contracts` (implements `Reader` protocol)

| Spec | Capabilities | Source Types |
|------|-------------|--------------|
| `dataio.readers.file-readers` | `CSVReader`, `JSONReader`, `ParquetReader`, `DeltaReader` | CSV, JSON, Parquet, Delta |
| `dataio.readers.jdbc-readers` | `JDBCReader`, `PostgresReader`, `MySQLReader`, `SQLServerReader` | JDBC sources |
| `dataio.readers.streaming-readers` | `KafkaReader`, `EventHubReader`, `KinesisReader` | Event streams |
| `dataio.readers.excel-readers` | `ExcelReader` | Excel workbooks |
| `dataio.readers.sap-readers` | `SAPReader`, `SAPIDocReader` | SAP systems |
| `dataio.readers.odbc-readers` | `ODBCReader` | ODBC sources |

**Common Interface:** All implement `Reader.read(source: SourceConfig, load: LoadConfig) -> DataFrame`

---

### 5.2 Load Strategies (`dataio.load_strategy.*`)

**Module:** `src/load_strategy/`  
**Status:** Draft (pending Phase 1)  
**Depends On:** `core.contracts` (implements `LoadStrategy` protocol)

| Spec | Capabilities | Strategy |
|------|-------------|----------|
| `dataio.load_strategy.append-strategy` | `AppendStrategy` | Append-only writes |
| `dataio.load_strategy.full-refresh-strategy` | `FullRefreshStrategy` | Truncate and load |
| `dataio.load_strategy.scd1-strategy` | `SCD1Strategy` | Update in place (Type 1) |
| `dataio.load_strategy.scd2-strategy` | `SCD2Strategy` | Versioned history (Type 2) |

**Common Interface:** All implement `LoadStrategy.apply(df: DataFrame, target: TargetConfig, load: LoadConfig) -> None`

---

## 6. Framework Engine Capabilities

### 6.1 Ingestion Framework (`ingestion.*`)

**Module:** `src/framework/ingestion/`  
**Status:** Draft (pending Phase 1)  
**Depends On:** `core.contracts`, `core.metadata`, `foundation.abc-sdk`, `dataio.readers.*`, `dataio.load_strategy.*`

| Capability | Type | Description |
|------------|------|-------------|
| `IngestionEngine` | class | Orchestrates ingestion runs (implements `Engine` protocol) |
| `run_batch_full` | function | Full table ingestion |
| `run_batch_incremental` | function | Incremental batch ingestion |
| `run_stream_append` | function | Streaming append ingestion |
| `run_scd2_batch` | function | SCD2 batch ingestion |

**ABC Instrumentation:** All runs log to ABC (audit, balance, cost)

---

### 6.2 Harmonization Framework (`harmonization.*`)

**Module:** `src/framework/harmonization/`  
**Status:** Draft (pending Phase 1)  
**Depends On:** Same as Ingestion + transformation capabilities

| Capability | Type | Description |
|------------|------|-------------| 
| `HarmonizationEngine` | class | Orchestrates harmonization runs |
| `apply_transformations` | function | Apply transformation rules |
| `map_to_acord` | function | Map to ACORD canonical model |
| `cleanse` | function | Data cleansing and standardization |

---

### 6.3 Data Quality Framework (`quality.*`)

**Module:** `src/framework/quality/`  
**Status:** Draft (pending Phase 2)  
**Depends On:** `core.contracts` (implements `Check` protocol)

| Capability | Type | Description |
|------------|------|-------------|
| `DQEngine` | class | Orchestrates DQ checks |
| `NotNullCheck` | class | Not null validation |
| `RangeCheck` | class | Value range validation |
| `RegexCheck` | class | Pattern matching validation |
| `ReferentialCheck` | class | Foreign key validation |
| `CustomCheck` | class | Custom SQL-based checks |

---

## 7. Capability Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                        │
│  Ingestion Engine, Harmonization Engine, DQ Engine, etc.        │
└────────────────────────┬────────────────────────────────────────┘
                         │ depends on
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CONTRACTS LAYER                             │
│  Reader, LoadStrategy, Engine, Check, Masker protocols          │
└────────────────────────┬────────────────────────────────────────┘
                         │ depends on
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION LAYER                           │
│  SourceConfig, TargetConfig, LoadConfig, ConfigLoader           │
└────────────────────────┬────────────────────────────────────────┘
                         │ depends on
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FOUNDATION LAYER                            │
│  ABC SDK (Audit, Balance, Control)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Cross-Reference: Ingestion Framework Needs

Based on the capability analysis, the **Ingestion Framework** requires these capabilities:

### Foundation (Must Have)
* `ABC`, `RunHandle`, `start_run`, `end_run`, `log_audit`, `log_balance`, `log_cost` - ABC SDK
* `SourceConfig`, `TargetConfig`, `LoadConfig`, `ConfigLoader` - Config Model
* `Reader`, `LoadStrategy`, `Engine`, `RunContext`, `RunResult` - Core Contracts

### Data I/O (Must Have)
* At least one `Reader` implementation (e.g., `CSVReader`, `JDBCReader`)
* At least one `LoadStrategy` implementation (e.g., `AppendStrategy`, `SCD2Strategy`)

### Quality (Optional)
* `Check`, `CheckResult` - For inline DQ validation
* `DQRuleConfig` - For DQ rule configuration

### Masking (Optional)
* `Masker` protocol - For inline data masking during ingestion

---

## 9. Capability Status Tracking

### ✅ Active (Ready to Use)
* `foundation.abc-sdk` - All 9 capabilities
* `core.metadata` - All 6 capabilities
* `core.contracts` - All 8 capabilities
* `scripts.codegen` - All 5 capabilities
* `foundation.spec-validator` - All 6 capabilities
* `agentic.capability-registry` - All 5 capabilities

### 🚧 Draft (Spec Complete, Implementation Pending)
* `dataio.readers.*` - 6 reader specs (18+ capabilities)
* `dataio.load_strategy.*` - 4 strategy specs (4 capabilities)
* `ingestion.*` - Engine spec (5+ capabilities)
* `harmonization.*` - Engine spec (4+ capabilities)
* `quality.*` - DQ checks (6+ capabilities)

### 📝 Planned (Spec Not Complete)
* `masking.*` - Masking engine and techniques
* `observability.*` - Logging, monitoring, alerting
* `orchestration.*` - CI/CD, workflow orchestration
* `finops.*` - Cost tracking, estimation dashboard

---

## 10. Usage Guidelines

### For Framework Developers

**Adding a New Capability:**
1. Add capability to spec front-matter `provides:` list
2. Update this registry with capability details
3. Document dependencies in `depends_on:` 
4. Implement capability following SOLID principles
5. Add unit tests (>80% coverage)
6. Update acceptance criteria

**Deprecating a Capability:**
1. Mark status as `deprecated` in this registry
2. Document migration path in spec
3. Update all dependent specs
4. Maintain backward compatibility for 2 releases
5. Remove after deprecation period

### For Agentic Build System

**Resolving Dependencies:**
1. User selects feature (e.g., "Ingestion - Batch")
2. `resolve_selection()` reads spec's `depends_on:`
3. Recursively resolve transitive dependencies
4. `build_plan()` topologically sorts specs
5. Generate code in dependency order (foundation first)

**Example Resolution:**
```
User selects: ingestion.batch
→ depends on: core.contracts
  → depends on: core.metadata
    → depends on: foundation.abc-sdk
      → depends on: (none)
      
Build order: [abc-sdk, config-model, contracts, ingestion.batch]
```

---

## 10.5 Architectural Decisions - Ingestion Framework

**Decision Date:** 2026-06-20  
**Status:** Approved  
**Context:** Design decisions for the initial Ingestion Framework build

### 1. Execution Modes

**Decision:**
* Create **sub-specs** for execution modes to manage complexity
* **Phase 1:** Declarative mode only (Lakeflow Spark Declarative Pipelines) with batch processing
* **Phase 2:** Non-declarative mode (PySpark + MERGE on Lakeflow Jobs)

**Rationale:**
* Keeps individual specs focused and maintainable
* Declarative mode with Lakeflow SDP is the strategic direction (AUTO CDC, simplified operations)
* Non-declarative mode needed for backward compatibility and edge cases

**Implementation:**
* Main spec: `ingestion.engine` (orchestration layer)
* Sub-spec: `ingestion.engine.declarative` (Lakeflow SDP implementation)
* Sub-spec: `ingestion.engine.batch` (PySpark + MERGE implementation)

---

### 2. Load Patterns - Initial Scope

**Decision:**
* **Phase 1:** Append-only pattern
* Code must be **extensible** for future patterns (SCD1, SCD2, Full Refresh)

**Rationale:**
* Append is simplest pattern (no MERGE logic, no deduplication)
* Proves the end-to-end framework architecture
* Provides immediate value for event logs, audit trails, fact tables

**Extension Strategy:**
* Strategy pattern with `LoadStrategy` protocol
* Each pattern is a separate strategy class implementing the protocol
* Engine selects strategy based on config (`load_pattern` field)

---

### 3. Reader Support - Initial Scope

**Decision:**
* **Phase 1:** File-based readers only (CSV, JSON, Parquet, Delta)
* Support **both** multi-source AND single-source ingestion

**Rationale:**
* File-based ingestion is most common in data lake scenarios
* Covers majority of initial use cases (landing zone → bronze)
* Multi-source support enables union/concatenation patterns

**Multi-Source Implementation:**
* Config accepts `sources: List[SourceConfig]` (not just single source)
* Engine iterates sources, reads each, unions DataFrames
* ABC logging aggregates metrics across all sources

---

### 4. Load Strategy - AUTO CDC vs Append

**Decision:**
* **Phase 1:** Support **both** append flow AND AUTO CDC
* Append: Direct write to Delta table (`df.write.mode("append")`)
* AUTO CDC: Lakeflow SDP `dlt.apply_changes()` (for SCD Type 2)

**Rationale:**
* Append is simpler, lower-latency, no CDC overhead
* AUTO CDC needed for SCD2 patterns (already scoped for Phase 1)
* Both patterns commonly used together (append for facts, AUTO CDC for dimensions)

**Implementation:**
* Separate strategy classes: `AppendStrategy`, `AutoCDCStrategy`
* AUTO CDC requires Lakeflow SDP (declarative mode only)
* Append works in both declarative and non-declarative modes

---

### 5. ABC Tables - Schema Design

**Decision:**
* **Create ABC tables** from scratch (nothing exists in current catalog)
* Tables accept **human-configurable** catalog and schema names (not hard-coded)

**Schema:**

**`abc_audit`** - Run audit trail
```sql
CREATE TABLE {catalog}.{schema}.abc_audit (
  run_id STRING NOT NULL,
  feed_id STRING NOT NULL,
  component STRING NOT NULL,
  run_type STRING NOT NULL,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP,
  duration_sec DECIMAL(10,2),
  rows_read BIGINT,
  rows_written BIGINT,
  rows_rejected BIGINT,
  status STRING NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) USING DELTA;
```

**`abc_balance`** - Reconciliation checks
```sql
CREATE TABLE {catalog}.{schema}.abc_balance (
  balance_id STRING NOT NULL,
  run_id STRING NOT NULL,
  feed_id STRING NOT NULL,
  check_type STRING NOT NULL,
  source_count BIGINT,
  target_count BIGINT,
  delta BIGINT,
  reconciliation_status STRING NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) USING DELTA;
```

**`abc_control`** - Framework control metadata
```sql
CREATE TABLE {catalog}.{schema}.abc_control (
  control_id STRING NOT NULL,
  run_id STRING NOT NULL,
  control_type STRING NOT NULL,
  control_key STRING NOT NULL,
  control_value STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) USING DELTA;
```

**`abc_cost`** - Cost and consumption tracking
```sql
CREATE TABLE {catalog}.{schema}.abc_cost (
  cost_id STRING NOT NULL,
  run_id STRING NOT NULL,
  resource_type STRING NOT NULL,
  resource_id STRING,
  dbu_consumed DECIMAL(18,6),
  duration_min DECIMAL(10,2),
  estimated_cost_usd DECIMAL(18,4),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) USING DELTA;
```

**Catalog/Schema Configuration:**
* Default: `{catalog}.{schema}` provided via config (e.g., `insurelake_abc.control`)
* Configurable at framework initialization
* No hard-coded values in code

---

### 6. Error Handling & Retry Strategy

**Decision (Provisional - Requires Brainstorming):**
* **Retries:** Configurable, default = 3 attempts
* **Backoff:** Support both exponential AND linear strategies (configurable)
* **Scope:** Retry everything for now (refine later based on error types)

**Rationale:**
* Transient failures are common (network, throttling, temporary unavailability)
* Exponential backoff prevents overwhelming downstream systems
* Linear backoff useful for rate-limited APIs

**Implementation (Provisional):**
```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_strategy: str = "exponential"  # or "linear"
    initial_delay_sec: int = 1
    max_delay_sec: int = 60
    backoff_multiplier: float = 2.0  # for exponential
```

**Open Questions:**
* Which errors are retryable vs fatal?
* Should retry be at component level (reader, writer) or orchestration level?
* How to handle partial failures in multi-source ingestion?

**Action:** Schedule brainstorming session to finalize retry logic

---

### 7. Quarantine / Dead Letter Queue

**Decision:**
* **Yes** - Separate quarantine table for rejected records
* Support **both** record-level AND batch-level quarantine
* **Phase 1:** Implement batch-level (simpler)

**Batch-Level Quarantine (Phase 1):**
* If entire batch fails validation/write, move to quarantine table
* Quarantine table schema matches source + adds metadata columns

**Record-Level Quarantine (Phase 2):**
* Filter rejected records during processing
* Write rejected records to quarantine table
* Continue processing valid records

**Quarantine Table Schema:**
```sql
CREATE TABLE {catalog}.{schema}.{feed_id}_quarantine (
  quarantine_id STRING NOT NULL,
  run_id STRING NOT NULL,
  quarantine_reason STRING NOT NULL,
  quarantine_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  -- All original source columns (dynamic schema)
  ...
) USING DELTA
PARTITIONED BY (DATE(quarantine_timestamp));
```

**Rationale:**
* Batch-level is simpler (no record filtering logic, less compute overhead)
* Enables investigation and reprocessing of failed batches
* Record-level provides finer granularity but adds complexity

---

### 8. Databricks Syntax & Documentation

**Decision:**
* **Always** use latest syntax from current Databricks documentation
* Target latest LTS DBR when specifying runtime requirements
* Verify syntax against official docs before finalizing specs

**Sources:**
* [Databricks SQL Language Reference](https://docs.databricks.com/sql/language-manual/index.html)
* [Delta Lake Documentation](https://docs.databricks.com/delta/index.html)
* [Lakeflow Spark Declarative Pipelines](https://docs.databricks.com/en/delta-live-tables/index.html)
* [PySpark API Reference](https://spark.apache.org/docs/latest/api/python/)

**Validation Process:**
* Cross-reference all code fragments with official docs
* Include doc links in spec §12 (References)
* Test on latest DBR during implementation

---

### 9. Extensibility Requirements

**Decision:**
* Framework must be **extensible** for future capabilities without breaking changes
* Use **strategy pattern** for swappable components (readers, load strategies)
* Use **dependency injection** for testability and customization

**Extension Points:**
* **Readers:** New source types (JDBC, Kafka, S3 APIs) via `Reader` protocol
* **Load Strategies:** New patterns (SCD1, SCD2, Full Refresh) via `LoadStrategy` protocol
* **Validators:** Custom validation rules via `Check` protocol (future)
* **Transformations:** Custom transform logic via config-driven UDFs (future)

**Data Quality Hook (Future):**
* Engine must reserve space for optional DQ checks
* Interface defined now (via `Check` protocol), implementation deferred
* Example hook point: `if dq_enabled: run_checks(df, dq_rules)`

**Rationale:**
* Avoids refactoring when adding new patterns
* Supports multi-customer customization
* Aligns with SOLID principles (OCP, DIP)

---

### 10. Configuration Management

**Decision:**
* **All** framework behavior controlled via configuration (no hard-coded values)
* Configuration accepts **human input** (via UI, config files, or API)
* Config validation at load time (fail fast if invalid)

**Configurable Parameters:**
* ABC catalog/schema names
* Retry settings (attempts, backoff strategy, delays)
* Quarantine behavior (enabled/disabled, table location)
* Source paths, target tables, load patterns
* Reader-specific options (delimiter, header, schema)
* Parallelism settings (num partitions, shuffle partitions)

**Configuration Sources (in priority order):**
1. Runtime parameters (job arguments, notebook widgets)
2. Config tables (Unity Catalog metadata tables)
3. YAML files (for DAB deployments)
4. Environment variables (for sensitive values like secrets)

**Validation:**
* Validate at config load time (before execution)
* Fail with clear error messages (e.g., "ABC catalog 'xyz' does not exist")
* Provide default values where reasonable

---

## 11. Maintenance

### Update Triggers
* New spec created → Add capabilities to registry
* Spec front-matter changed → Update registry
* Capability deprecated → Mark in registry
* Dependency added → Update dependency graph
* **Architectural decision made → Update §10.5**

### Automation
* Registry sync: `python scripts/sync_registry.py`
* Validation: `python scripts/speccheck/validate_spec.py --check-registry`
* Graph generation: `python scripts/visualize_deps.py`

---

## 12. References

* [SPEC_REGISTRY.md](SPEC_REGISTRY.md) - Comprehensive spec inventory
* [capability-registry-spec.md](agentic/capability-registry-spec.md) - Capability registry system spec
* [contracts-spec.md](foundation/contracts-spec.md) - Core contracts specification
* [abc-sdk-spec.md](foundation/abc-sdk-spec.md) - ABC SDK specification
* [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) - Project architecture and decisions
* [INGESTION_READINESS_REPORT.md](INGESTION_READINESS_REPORT.md) - Spec validation and remediation plan

---

**Maintained by:** EY InsureLake Team  
**Questions?** See `docs/ROADMAP.md` or the capability-registry spec
