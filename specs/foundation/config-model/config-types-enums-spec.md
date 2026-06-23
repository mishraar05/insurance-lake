---
id: core.metadata.types
title: Config Model - Types, Enums & Exceptions
owner: EY
status: active
target_path: src/core/metadata/config_types.py
owning_skill: framework-dev.build-config-model
backlog: [FND-001-TYPES]
provides:
  - SourceType, Layer, TableType, Format (11 enums total)
  - ConfigValidationError, FKViolationError, ParamParseError
  - Shared validation patterns (identifier validation, regex patterns)
depends_on: []
generation_context:
  - specs/foundation/config-model/config-types-enums-spec.md
  - docs/ABC-MAPPING.md
acceptance:
  - "pytest tests/unit/test_config_types.py"
  - "All 11 enums validate valid and invalid values"
  - "Custom exceptions carry structured context"
regeneration: full-regen-safe
confidence_score: 0.95
---

# FND-001-TYPES - Config Model Types & Enums Specification

Status: active · 2026-06-23 · Skill: `framework-dev.build-config-model`

**Purpose:** Define shared enumerations, custom exceptions, and validation patterns used across all config entities. This is the foundational layer with zero dependencies—all other config specs import from this.

---

## 1. Purpose & Scope

**In scope:**
* 11 enumeration types representing valid categorical values (source types, layers, engines, etc.)
* 3 custom exception classes for structured error handling
* Shared validation patterns (identifier regex, naming conventions)
* Confidence scoring guidelines for validation quality

**Out of scope:**
* Config entity models (SourceConfig, TargetConfig, etc.) → see `source-target-spec.md`, `load-config-spec.md`
* Storage/persistence logic → see `config-storage-spec.md`
* Complex validators (cross-field, FK checks) → see `config-validators-spec.md`

---

## 2. Guardrails (Natural Language Rules)

### Core Principles
1. **Enum immutability:** Once an enum value is in production use, it MUST NOT be removed or renamed—only additions are safe
2. **No dynamic enums:** Enum values are compile-time constants, not database-driven lookups
3. **Case sensitivity:** All enum values use UPPER_SNAKE_CASE (e.g., `AUTOLOADER`, not `AutoLoader`)
4. **No numeric enums:** Use semantic string values, not magic numbers
5. **Exception context:** All custom exceptions MUST carry structured context (field names, values, FK references)

### Business Rules
* **SourceType validation:**
  - `FILE` sources MUST specify `file_format` (CSV/JSON/PARQUET)
  - `TABLE` sources MUST specify fully qualified table name (catalog.schema.table)
  - `API` sources MUST specify `connection_string` and `credential_scope`
  - `STREAM` sources MUST provide checkpoint location
  - `CDC` sources MUST specify `watermark_column` for change tracking

* **Layer validation:**
  - `BRONZE` = raw/landing data (minimal transformation)
  - `SILVER` = cleansed/standardized data (business logic applied)
  - `GOLD` = aggregated/dimensional data (analytics-ready)
  - Layer transitions MUST be sequential: BRONZE → SILVER → GOLD (no skipping)

* **Engine compatibility:**
  - `AUTOLOADER` only valid for `FILE` sources with cloud storage paths
  - `DECLARATIVE` requires checkpoint location and materialized view targets
  - `STRUCTURED_STREAMING` requires watermark column for event-time processing
  - `SPARK_SQL` for batch-only transformations (no streaming)

* **Format constraints:**
  - `DELTA` is the ONLY format supporting time travel, CDF, and ACID transactions
  - `PARQUET` is read-only (no updates/deletes)
  - `CSV`/`JSON` are landing zone only (never target format for SILVER/GOLD)

### What NOT to Do
❌ **Do NOT:**
* Add enum values for customer-specific sources (use `source_system` field instead)
* Use enum values as user-facing display text (maintain separate display name mappings)
* Store enum values with mixed case in PARAM_VAL (always uppercase)
* Create "OTHER" or "UNKNOWN" catch-all enum values (fail validation instead)
* Reuse enum names across different enums (e.g., `Type` in multiple contexts—be specific)

### Confidence Scoring
Each enum value has an implicit confidence score based on production usage:
* **0.95+** (High confidence): Core values in production (FILE, TABLE, DELTA, BRONZE/SILVER/GOLD)
* **0.80-0.94** (Medium confidence): Emerging patterns (CDC, STREAM, ACORD_MAPPING)
* **0.60-0.79** (Low confidence): Experimental/future values (API sources, custom transforms)
* **<0.60** (Deprecated): Planned for removal in next major version

**Confidence decay:** If an enum value is not used in any active config for 6 months, its confidence drops below 0.60 and triggers deprecation review.

---

## 3. Enumerations (11 Total)

### 3.1 SourceType
**Purpose:** Categorize data ingestion sources

**Valid values:**
* `FILE` - File-based sources (S3, ADLS, GCS)
  - Requires: `file_format`, `schema_location`
  - Confidence: 0.95 (primary ingestion pattern)
  
* `TABLE` - Unity Catalog or external tables
  - Requires: Fully qualified table name
  - Confidence: 0.95 (common for bronze → silver)
  
* `STREAM` - Real-time event streams (Kafka, Kinesis)
  - Requires: `watermark_column`, checkpoint location
  - Confidence: 0.82 (growing adoption)
  
* `API` - REST/SOAP API endpoints
  - Requires: `connection_string`, `credential_scope`
  - Confidence: 0.68 (limited use cases)
  
* `CDC` - Change Data Capture feeds (Debezium, AWS DMS)
  - Requires: `watermark_column`, merge keys
  - Confidence: 0.75 (insurance industry adoption)

**Validation rules:**
* Source type determines required config fields (enforced by cross-field validators)
* Cannot change source type after initial config creation (immutable)

---

### 3.2 Layer
**Purpose:** Medallion architecture layers

**Valid values:**
* `BRONZE` - Raw/landing zone (minimal transformation)
  - Confidence: 0.98
* `SILVER` - Cleansed/standardized (business rules applied)
  - Confidence: 0.98
* `GOLD` - Aggregated/dimensional (analytics-ready)
  - Confidence: 0.98

**Business rules:**
* Data must flow sequentially through layers (no BRONZE → GOLD direct)
* Each layer has specific retention policies (BRONZE: 30d, SILVER: 365d, GOLD: indefinite)
* Layer determines schema evolution policy (BRONZE: permissive, GOLD: strict)

---

### 3.3 TableType
**Purpose:** Unity Catalog table types

**Valid values:**
* `MANAGED` - Databricks-managed storage (default)
  - Confidence: 0.95
* `EXTERNAL` - External storage location
  - Confidence: 0.88

**Usage guidance:**
* Use `MANAGED` unless regulatory/compliance requires external storage
* External tables require pre-provisioned storage locations

---

### 3.4 Format
**Purpose:** Table storage formats

**Valid values:**
* `DELTA` - Delta Lake format (ACID, time travel, CDF)
  - Confidence: 0.98 (required for all SILVER/GOLD)
* `PARQUET` - Columnar format (read-only)
  - Confidence: 0.75 (legacy bronze tables)
* `CSV` - Comma-separated values (landing only)
  - Confidence: 0.70 (source files, not targets)
* `JSON` - JSON format (landing only)
  - Confidence: 0.72 (API responses, logs)

**Constraints:**
* Only `DELTA` supports UPDATE, DELETE, MERGE operations
* `CSV`/`JSON` are valid source formats but invalid target formats for SILVER/GOLD

---

### 3.5 LoadType
**Purpose:** Batch vs streaming ingestion

**Valid values:**
* `BATCH` - Scheduled batch processing
  - Confidence: 0.92
* `STREAMING` - Continuous streaming ingestion
  - Requires: `watermark_column`, trigger interval
  - Confidence: 0.85
* `INCREMENTAL` - Incremental batch (watermark-based)
  - Requires: `watermark_column`
  - Confidence: 0.90

**Selection guidance:**
* Use `BATCH` for daily/hourly file drops
* Use `STREAMING` for real-time event processing (<1min latency)
* Use `INCREMENTAL` for large tables with timestamp/ID watermarks

---

### 3.6 LoadPattern
**Purpose:** Data loading strategies

**Valid values:**
* `APPEND` - Append-only (no deduplication)
  - Confidence: 0.94
* `MERGE` - Upsert based on merge keys
  - Requires: `merge_keys`
  - Confidence: 0.92
* `UPSERT` - Insert or update based on primary key
  - Requires: `merge_keys`
  - Confidence: 0.88
* `OVERWRITE` - Full table replacement
  - Confidence: 0.70 (use sparingly)
* `SCD2` - Slowly Changing Dimension Type 2 (history tracking)
  - Requires: `merge_keys`, SCD2 timestamp columns
  - Confidence: 0.85

**Pattern selection rules:**
* Use `APPEND` for immutable event logs
* Use `MERGE`/`UPSERT` for transactional data (policies, claims)
* Use `SCD2` for dimensional data requiring history (customers, agents)
* Avoid `OVERWRITE` unless intentional full refresh

---

### 3.7 Engine
**Purpose:** Ingestion/transformation execution engines

**Valid values:**
* `AUTOLOADER` - Databricks Auto Loader (cloud file ingestion)
  - Valid for: `FILE` sources only
  - Confidence: 0.95
* `DECLARATIVE` - Lakeflow Spark Declarative Pipelines (formerly DLT)
  - Requires: Checkpoint location
  - Confidence: 0.90
* `STRUCTURED_STREAMING` - Spark Structured Streaming
  - Requires: `watermark_column` for streaming sources
  - Confidence: 0.82
* `SPARK_SQL` - Batch SQL transformations
  - Confidence: 0.88

**Engine compatibility matrix:**
| Engine | FILE | TABLE | STREAM | API | CDC |
|--------|------|-------|--------|-----|-----|
| AUTOLOADER | ✓ | ✗ | ✗ | ✗ | ✗ |
| DECLARATIVE | ✓ | ✓ | ✓ | ✗ | ✓ |
| STRUCTURED_STREAMING | ✓ | ✓ | ✓ | ✗ | ✓ |
| SPARK_SQL | ✗ | ✓ | ✗ | ✗ | ✗ |

---

### 3.8 DQRuleType
**Purpose:** Data quality rule categories

**Valid values:**
* `NOT_NULL` - Column must not contain null values
  - Confidence: 0.98
* `UNIQUE` - Column values must be unique
  - Confidence: 0.95
* `RANGE` - Numeric/date values within specified range
  - Confidence: 0.90
* `PATTERN` - Regex pattern matching (e.g., email, phone)
  - Confidence: 0.88
* `CUSTOM` - Custom SQL/Python validation logic
  - Confidence: 0.75
* `FRESHNESS` - Data recency checks (max age threshold)
  - Confidence: 0.80

---

### 3.9 OnFailure
**Purpose:** Data quality failure actions

**Valid values:**
* `WARN` - Log warning, continue processing
  - Confidence: 0.85
* `FAIL` - Halt pipeline, raise exception
  - Confidence: 0.95
* `QUARANTINE` - Move failed records to quarantine table
  - Confidence: 0.88

**Decision guidance:**
* Use `FAIL` for critical business rules (PII validation, primary key integrity)
* Use `WARN` for statistical checks (expected ranges, historical trends)
* Use `QUARANTINE` for partial failure tolerance (process good records, isolate bad)

---

### 3.10 TransformType
**Purpose:** Transformation logic types

**Valid values:**
* `SQL` - SQL-based transformations
  - Confidence: 0.95
* `PYTHON` - Python UDF/Pandas transformations
  - Confidence: 0.88
* `ACORD_MAPPING` - ACORD XML to Delta mappings (insurance-specific)
  - Confidence: 0.72
* `CUSTOM` - Custom transformation logic
  - Confidence: 0.65

---

### 3.11 SCDType
**Purpose:** Slowly Changing Dimension handling

**Valid values:**
* `SCD1` - Overwrite (no history)
  - Confidence: 0.85
* `SCD2` - Add new row with effective dates (full history)
  - Confidence: 0.92
* `SCD3` - Add columns for previous value (limited history)
  - Confidence: 0.60 (rarely used)

---

## 4. Custom Exceptions

### 4.1 ConfigValidationError
**Purpose:** Base exception for all config validation failures

**Context carried:**
* Error message (human-readable)
* Config entity type (source/target/load/transform/dq)
* Validation rule that failed

**When raised:**
* Pydantic validation fails (field type mismatch, missing required field)
* Business rule violation (e.g., STREAMING load without watermark_column)
* Regex pattern mismatch (invalid identifier format)

**Confidence:** 0.98 (core error handling)

---

### 4.2 FKViolationError
**Purpose:** Foreign key reference not found

**Context carried:**
* FK field name (e.g., "source_id", "target_id")
* FK value attempted (e.g., "src_999")
* Referenced table/entity (e.g., "ABC_SRC_CTRL_TBL")

**When raised:**
* LoadConfig references non-existent source_id
* TransformConfig references non-existent target_id
* DQRuleConfig references non-existent target_id

**Example message:**
```
FK violation: source_id 'src_999' not found in ABC_SRC_CTRL_TBL
```

**Confidence:** 0.95 (critical for referential integrity)

---

### 4.3 ParamParseError
**Purpose:** PARAM row cannot be parsed into typed object

**Context carried:**
* JOB_SK (job surrogate key)
* PARAM_ZONE (source/target/load/transform/dq)
* PARAM_NM (parameter name)
* PARAM_VAL (raw value that failed parsing)
* Parse error details (JSON decode error, type coercion failure)

**When raised:**
* JSON-encoded PARAM_VAL is malformed
* PARAM_VAL datatype doesn't match expected type (e.g., string for integer field)
* Missing required PARAM rows for entity reconstruction

**Example message:**
```
ParamParseError: Cannot parse PARAM_ZONE='load', PARAM_NM='merge_keys', PARAM_VAL='[invalid json' 
  → JSON decode error: Expecting ',' delimiter (line 1)
```

**Confidence:** 0.92 (critical for EAV storage integrity)

---

## 5. Shared Validation Patterns

### 5.1 Identifier Validation
**Rule:** Alphanumeric + underscores, 3-100 characters, must start with letter

**Regex pattern:**
```
^[a-zA-Z][a-zA-Z0-9_]{2,99}$
```

**Applies to:**
* source_id, source_name
* target_id, target_name
* load_id, load_name
* transform_id, dq_rule_id

**Rationale:** Ensures safe use as Spark column names, SQL identifiers, file paths

---

### 5.2 Fully Qualified Name Validation
**Rule:** Three-part name (catalog.schema.table), each part is valid identifier

**Regex pattern:**
```
^[a-zA-Z][a-zA-Z0-9_]{2,99}\.[a-zA-Z][a-zA-Z0-9_]{2,99}\.[a-zA-Z][a-zA-Z0-9_]{2,99}$
```

**Applies to:**
* Table references (source tables, target tables)
* Checkpoint locations (Unity Catalog volume paths)

---

### 5.3 Cron Expression Validation
**Rule:** Valid Quartz cron expression (5-7 fields)

**Applies to:**
* LoadConfig.schedule_cron
* Job scheduling metadata

**Validation approach:**
* Use `croniter` library for parsing
* Reject invalid expressions at config save time (fail-fast)

---

## 6. Testing & Acceptance

### Unit Tests
**UT-ENUM-1:** Validate all enum values
* Test: Instantiate each enum with valid and invalid values
* Expected: Valid values accepted, invalid values raise ValueError

**UT-ENUM-2:** Enum string serialization
* Test: Serialize enums to string, deserialize back
* Expected: Round-trip preserves value (AUTOLOADER → "AUTOLOADER" → AUTOLOADER)

**UT-EXC-1:** Exception context preservation
* Test: Raise FKViolationError with context, catch and inspect
* Expected: Context attributes accessible (fk_name, fk_value)

**UT-VAL-1:** Identifier regex validation
* Test: Valid identifiers ("source_001", "my_config_v2")
* Expected: Pass validation

**UT-VAL-2:** Invalid identifier rejection
* Test: Invalid identifiers ("123_start", "name-with-dash", "a")
* Expected: Validation error raised

### Acceptance Criteria
* **AC-1:** All 11 enums defined with at least 2 values each
* **AC-2:** All 3 custom exceptions carry structured context
* **AC-3:** Identifier regex rejects 100% of invalid formats (no false positives)
* **AC-4:** Zero circular dependencies (this spec imports nothing)

---

## 7. Confidence Score Summary

| Component | Confidence | Basis |
|-----------|-----------|-------|
| SourceType enum | 0.92 | Proven in production (FILE, TABLE core patterns) |
| Layer enum | 0.98 | Medallion architecture standard |
| LoadPattern enum | 0.88 | SCD2, MERGE patterns well-tested |
| Engine enum | 0.90 | AUTOLOADER, DECLARATIVE dominant |
| DQRuleType enum | 0.85 | NOT_NULL, UNIQUE core rules; CUSTOM evolving |
| FKViolationError | 0.95 | Critical for data integrity |
| ParamParseError | 0.92 | Essential for EAV storage |
| Identifier validation | 0.97 | Regex battle-tested |

**Overall spec confidence:** 0.95 (foundational, zero dependencies, well-tested patterns)

---

## 8. References

### Dependencies
* **None** (this is the base layer)

### Imported by
* `config-storage-spec.md` (ConfigLoader uses enums)
* `source-target-spec.md` (SourceConfig, TargetConfig use enums)
* `load-config-spec.md` (LoadConfig uses enums)
* `transform-dq-spec.md` (TransformConfig, DQRuleConfig use enums)
* `config-validators-spec.md` (Validators check enum membership)

### External References
* [Python Enum Documentation](https://docs.python.org/3/library/enum.html)
* [Pydantic Custom Validators](https://docs.pydantic.dev/latest/concepts/validators/)

---

**END OF SPEC**
