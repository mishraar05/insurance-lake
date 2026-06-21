---
id: core.metadata.metadata-models
title: Metadata Models Spec
owner: EY
status: draft
target_path: src/core/metadata/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/core/metadata/metadata-models-spec.md
acceptance:
  - "pytest tests/unit/test_metadata_models.py"
regeneration: scaffold-then-edit
---

# Metadata Models Spec

## 1. Purpose

Define the **core metadata models** as Python dataclasses that serve as the **single source of truth (SSOT)** for all InsureLake framework components. These models represent:

* **Feed** — source data configuration (what to ingest, from where, how)
* **Pipeline** — overall pipeline definition (orchestration, execution mode, layers)
* **TransformRule** — transformation logic (silver/gold curation)
* **DQCheck** — data quality validation rules
* **MaskRule** — PII/PHI masking rules
* **ReconRule** — reconciliation/balance checks

These dataclasses will:
1. **Drive code generation** — `metadata-to-ddl-spec.md` generates Delta DDL + JSON-schema from these classes
2. **Enforce type safety** — all framework components import and type-check against these models
3. **Enable serialization** — config files (YAML/JSON) deserialize into these objects using Pydantic
4. **Support validation** — each model uses Pydantic validators for business rule checks

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Supports both declarative (Lakeflow SDP) and non-declarative (PySpark + MERGE) execution modes
* Aligns with Medallion architecture (Bronze → Silver → Gold)
* Captures ACORD canonical model entities in Silver layer
* Integrates ABC framework metadata (audit, balance, cost tracking)

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §3** — framework scope (Ingestion, Harmonization, DQ, Recon, Masking)
* **PROJECT_CONTEXT.md §4** — architecture decisions (Medallion, UC, dual execution modes, ACORD model)
* **ROADMAP.md Phase 0** — metadata models are Wave 0 foundation
* **Backlog tasks:** FND-001, META-001

### 2.2 Design Constraints
* **Python 3.10+ only** — leverage modern typing features (e.g., `|` union syntax, `TypeAlias`)
* **Pydantic v2** — use for validation, serialization, and automatic type conversion
* **UC-native** — all table references must be fully qualified `{catalog}.{schema}.{table}`
* **JSON-serializable** — all fields must round-trip through JSON (no complex objects, use strings for enums)
* **Self-validating** — Pydantic validators enforce business rules automatically

---

## 3. Procedure

### 3.1 Core Entity Models

Define six core dataclasses in `core/metadata/models.py` using Pydantic BaseModel:

#### 3.1.1 Feed Model
Represents a source data feed (ingestion target).

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class SourceFormat(str, Enum):
    """Supported source formats for ingestion."""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    DELTA = "delta"
    AVRO = "avro"
    JDBC = "jdbc"  # Generic JDBC; db_type specified separately

class LoadStrategy(str, Enum):
    """Data load strategy."""
    APPEND = "append"          # Append-only (no updates/deletes)
    SCD1 = "scd1"              # Type 1 (overwrite/upsert, no history)
    SCD2 = "scd2"              # Type 2 (maintain history with effective dates)
    FULL_REFRESH = "full_refresh"  # Truncate and reload

class Feed(BaseModel):
    """
    Represents a source data feed configuration.
    
    Attributes:
        feed_id: Unique identifier (e.g., "policy_feed_001")
        name: Human-readable name (e.g., "Policy Master Feed")
        source_system: Source system name (e.g., "SAP", "Salesforce")
        source_format: File format or connection type
        source_location: Path (UC volume, S3, ADLS) or JDBC connection string
        jdbc_db_type: Optional DB type for JDBC sources (e.g., "sqlserver", "postgres")
        load_strategy: How to load data (append, SCD1, SCD2, full refresh)
        target_catalog: UC catalog for Bronze table
        target_schema: UC schema for Bronze table
        target_table: Table name in Bronze layer
        primary_keys: List of columns forming the primary key (for SCD)
        partition_columns: Optional partitioning columns (e.g., ["date", "region"])
        file_format_options: Optional dict for format-specific options (e.g., {"header": "true", "delimiter": ","})
        enabled: Whether feed is active
    """
    feed_id: str
    name: str
    source_system: str
    source_format: SourceFormat
    source_location: str
    jdbc_db_type: Optional[str] = None  # For JDBC sources: "sqlserver", "postgres", "oracle", etc.
    load_strategy: LoadStrategy
    target_catalog: str
    target_schema: str
    target_table: str
    primary_keys: list[str] = Field(default_factory=list)
    partition_columns: list[str] = Field(default_factory=list)
    file_format_options: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    
    @property
    def target_table_fqn(self) -> str:
        """Fully qualified table name."""
        return f"{self.target_catalog}.{self.target_schema}.{self.target_table}"
    
    @field_validator('feed_id', 'name')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @field_validator('primary_keys')
    @classmethod
    def validate_primary_keys_for_scd(cls, v: list[str], info) -> list[str]:
        # Access load_strategy from validation context
        if 'load_strategy' in info.data:
            load_strategy = info.data['load_strategy']
            if load_strategy in (LoadStrategy.SCD1, LoadStrategy.SCD2) and not v:
                raise ValueError(f"primary_keys required for {load_strategy.value} load strategy")
        return v
    
    @field_validator('target_catalog', 'target_schema', 'target_table')
    @classmethod
    def validate_uc_components(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Unity Catalog components (catalog, schema, table) are required")
        return v

    class Config:
        frozen = True  # Immutable
```

#### 3.1.2 Pipeline Model
Represents an end-to-end pipeline (may orchestrate multiple feeds/transforms).

```python
class ExecutionMode(str, Enum):
    """Pipeline execution mode."""
    DECLARATIVE = "declarative"  # Lakeflow Spark Declarative Pipeline
    IMPERATIVE = "imperative"    # PySpark notebook + MERGE logic

class Layer(str, Enum):
    """Medallion layer."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"

class PipelineType(str, Enum):
    """Pipeline type (enforces validation rules)."""
    INGESTION = "ingestion"
    HARMONIZATION = "harmonization"
    QUALITY = "quality"
    RECONCILIATION = "reconciliation"
    MASKING = "masking"

class Pipeline(BaseModel):
    """
    Represents a pipeline definition.
    
    Attributes:
        pipeline_id: Unique identifier (e.g., "ingest_policy_pipeline")
        name: Human-readable name
        description: Pipeline purpose and scope
        pipeline_type: Type of pipeline (determines validation rules)
        execution_mode: Declarative (SDP) or imperative (job + notebook)
        source_layer: Input layer (e.g., Bronze for harmonization)
        target_layer: Output layer (e.g., Silver for harmonization)
        feeds: List of feed IDs this pipeline processes (for ingestion pipelines)
        transforms: List of transform rule IDs (for harmonization pipelines)
        dq_checks: List of DQ check IDs (for quality pipelines)
        recon_rules: List of recon rule IDs (for reconciliation)
        schedule: Optional cron schedule (e.g., "0 0 * * *" for daily at midnight)
        enabled: Whether pipeline is active
    """
    pipeline_id: str
    name: str
    description: str
    pipeline_type: PipelineType
    execution_mode: ExecutionMode
    source_layer: Optional[Layer] = None  # None for ingestion (no source layer)
    target_layer: Layer = Layer.BRONZE
    feeds: list[str] = Field(default_factory=list)
    transforms: list[str] = Field(default_factory=list)
    dq_checks: list[str] = Field(default_factory=list)
    recon_rules: list[str] = Field(default_factory=list)
    schedule: Optional[str] = None
    enabled: bool = True
    
    @field_validator('pipeline_id', 'name')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @field_validator('feeds')
    @classmethod
    def validate_ingestion_has_feeds(cls, v: list[str], info) -> list[str]:
        if 'pipeline_type' in info.data:
            pipeline_type = info.data['pipeline_type']
            if pipeline_type == PipelineType.INGESTION and not v:
                raise ValueError("Ingestion pipelines must specify at least one feed")
        return v
    
    @field_validator('transforms')
    @classmethod
    def validate_harmonization_has_transforms(cls, v: list[str], info) -> list[str]:
        if 'pipeline_type' in info.data:
            pipeline_type = info.data['pipeline_type']
            if pipeline_type == PipelineType.HARMONIZATION and not v:
                raise ValueError("Harmonization pipelines must specify at least one transform")
        return v

    class Config:
        frozen = True
```

#### 3.1.3 TransformRule Model
Represents a transformation (Silver/Gold curation).

```python
class TransformType(str, Enum):
    """Type of transformation."""
    SQL = "sql"              # SQL query-based
    SPARK = "spark"          # PySpark code-based
    UDF = "udf"              # User-defined function (ACORD standardization)

class TransformRule(BaseModel):
    """
    Represents a transformation rule for harmonization/curation.
    
    Attributes:
        transform_id: Unique identifier
        name: Human-readable name
        description: What this transform does
        transform_type: SQL, Spark, or UDF
        source_tables: List of fully qualified source table names
        target_table_fqn: Fully qualified target table name
        transform_logic: SQL query string OR Python code string OR UDF name
        load_strategy: How to write results (append, SCD1, SCD2)
        primary_keys: Primary key columns (for SCD)
        enabled: Whether rule is active
    """
    transform_id: str
    name: str
    description: str
    transform_type: TransformType
    source_tables: list[str]
    target_table_fqn: str
    transform_logic: str
    load_strategy: LoadStrategy = LoadStrategy.APPEND
    primary_keys: list[str] = Field(default_factory=list)
    enabled: bool = True
    
    @field_validator('transform_id', 'name', 'target_table_fqn', 'transform_logic')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @field_validator('source_tables')
    @classmethod
    def validate_source_tables(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("source_tables cannot be empty")
        return v

    class Config:
        frozen = True
```

#### 3.1.4 DQCheck Model
Represents a data quality check.

```python
class CheckType(str, Enum):
    """Type of data quality check."""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"              # Numeric range check
    PATTERN = "pattern"          # Regex pattern match
    REFERENTIAL = "referential"  # Foreign key check
    CUSTOM_SQL = "custom_sql"    # Custom SQL expression

class CheckSeverity(str, Enum):
    """Severity level for check failures."""
    WARN = "warn"        # Log warning, continue processing
    BLOCK = "block"      # Stop pipeline execution
    QUARANTINE = "quarantine"  # Move bad records to quarantine table

class DQCheck(BaseModel):
    """
    Represents a data quality check rule.
    
    Attributes:
        check_id: Unique identifier
        name: Human-readable name
        description: What this check validates
        check_type: Type of validation
        table_fqn: Fully qualified table name to check
        column_name: Optional column name (for column-level checks)
        check_expression: SQL expression or pattern (depends on check_type)
        severity: Action to take on failure (warn, block, quarantine)
        threshold: Optional failure threshold (0.0 to 1.0, percentage of rows that can fail)
        enabled: Whether check is active
    """
    check_id: str
    name: str
    description: str
    check_type: CheckType
    table_fqn: str
    column_name: Optional[str] = None
    check_expression: Optional[str] = None
    severity: CheckSeverity = CheckSeverity.WARN
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enabled: bool = True
    
    @field_validator('check_id', 'name', 'table_fqn')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @field_validator('check_expression')
    @classmethod
    def validate_expression_for_type(cls, v: Optional[str], info) -> Optional[str]:
        if 'check_type' in info.data:
            check_type = info.data['check_type']
            if check_type in (CheckType.RANGE, CheckType.PATTERN, CheckType.CUSTOM_SQL) and not v:
                raise ValueError(f"check_expression required for {check_type.value}")
        return v

    class Config:
        frozen = True
```

#### 3.1.5 MaskRule Model
Represents a masking/PII handling rule.

```python
class MaskingTechnique(str, Enum):
    """Masking technique."""
    REDACT = "redact"              # Full redaction (e.g., "***")
    HASH = "hash"                  # One-way hash (SHA-256)
    TOKENIZE = "tokenize"          # Reversible tokenization
    UC_DYNAMIC = "uc_dynamic"      # Unity Catalog dynamic masking
    PARTIAL_MASK = "partial_mask"  # Partial masking (e.g., "555-**-1234")

class MaskRule(BaseModel):
    """
    Represents a PII/PHI masking rule.
    
    Attributes:
        mask_id: Unique identifier
        name: Human-readable name
        description: What PII/PHI this masks
        table_fqn: Fully qualified table name
        column_name: Column to mask
        technique: Masking technique
        uc_masking_policy: Optional UC masking policy name (for UC_DYNAMIC)
        masking_pattern: Optional pattern for PARTIAL_MASK (e.g., "XXX-XX-####")
        enabled: Whether rule is active
    """
    mask_id: str
    name: str
    description: str
    table_fqn: str
    column_name: str
    technique: MaskingTechnique
    uc_masking_policy: Optional[str] = None
    masking_pattern: Optional[str] = None
    enabled: bool = True
    
    @field_validator('mask_id', 'name', 'table_fqn', 'column_name')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @field_validator('uc_masking_policy')
    @classmethod
    def validate_uc_policy_for_dynamic(cls, v: Optional[str], info) -> Optional[str]:
        if 'technique' in info.data:
            technique = info.data['technique']
            if technique == MaskingTechnique.UC_DYNAMIC and not v:
                raise ValueError("uc_masking_policy required for UC_DYNAMIC technique")
        return v
    
    @field_validator('masking_pattern')
    @classmethod
    def validate_pattern_for_partial(cls, v: Optional[str], info) -> Optional[str]:
        if 'technique' in info.data:
            technique = info.data['technique']
            if technique == MaskingTechnique.PARTIAL_MASK and not v:
                raise ValueError("masking_pattern required for PARTIAL_MASK technique")
        return v

    class Config:
        frozen = True
```

#### 3.1.6 ReconRule Model
Represents a reconciliation/balance check.

```python
class ReconType(str, Enum):
    """Type of reconciliation check."""
    ROW_COUNT = "row_count"          # Compare record counts
    SUM = "sum"                      # Compare sum of a column
    CHECKSUM = "checksum"            # Compare hash of dataset
    CUSTOM = "custom"                # Custom SQL comparison

class ReconRule(BaseModel):
    """
    Represents a reconciliation rule (feeds ABC Balance framework).
    
    Attributes:
        recon_id: Unique identifier
        name: Human-readable name
        description: What is being reconciled
        recon_type: Type of reconciliation
        source_table_fqn: Source (upstream) table
        target_table_fqn: Target (downstream) table
        column_name: Optional column for SUM reconciliation
        tolerance: Optional tolerance as percentage (0.01 = 1% difference allowed)
        custom_sql: Optional custom SQL for CUSTOM recon_type
        enabled: Whether rule is active
    """
    recon_id: str
    name: str
    description: str
    recon_type: ReconType
    source_table_fqn: str
    target_table_fqn: str
    column_name: Optional[str] = None
    tolerance: Optional[float] = Field(default=None, ge=0.0, le=1.0)  # Percentage (0.0 to 1.0)
    custom_sql: Optional[str] = None
    enabled: bool = True
    
    @field_validator('recon_id', 'name', 'source_table_fqn', 'target_table_fqn')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @field_validator('column_name')
    @classmethod
    def validate_column_for_sum(cls, v: Optional[str], info) -> Optional[str]:
        if 'recon_type' in info.data:
            recon_type = info.data['recon_type']
            if recon_type == ReconType.SUM and not v:
                raise ValueError("column_name required for SUM reconciliation")
        return v
    
    @field_validator('custom_sql')
    @classmethod
    def validate_sql_for_custom(cls, v: Optional[str], info) -> Optional[str]:
        if 'recon_type' in info.data:
            recon_type = info.data['recon_type']
            if recon_type == ReconType.CUSTOM and not v:
                raise ValueError("custom_sql required for CUSTOM reconciliation")
        return v

    class Config:
        frozen = True
```

### 3.2 ACORD Canonical Model Entities (Silver Layer)

**Decision:** Define Python dataclasses for ACORD entities to maintain type safety and enable validation.

ACORD entities will be defined in a separate file `core/domain/acord_models.py` and documented fully in `specs/core/domain/ACORD_CANONICAL_SCHEMA.md`. The minimum viable schema includes:

```python
# core/domain/acord_models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum

class PartyType(str, Enum):
    """Type of party."""
    PERSON = "person"
    ORGANIZATION = "organization"

class Party(BaseModel):
    """ACORD Party entity (person or organization)."""
    party_id: str
    party_type: PartyType
    name: str
    date_of_birth: Optional[date] = None  # For PERSON
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "USA"
    created_date: date
    updated_date: date
    
    class Config:
        frozen = True

class PolicyStatus(str, Enum):
    """Policy status."""
    ACTIVE = "active"
    PENDING = "pending"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Policy(BaseModel):
    """ACORD Policy entity."""
    policy_id: str
    policy_number: str
    party_id: str  # FK to Party
    status: PolicyStatus
    effective_date: date
    expiration_date: date
    premium_amount: float
    currency: str = "USD"
    product_type: str  # e.g., "auto", "home", "commercial"
    created_date: date
    updated_date: date
    
    class Config:
        frozen = True

# Coverage, Claim, Payment, Loss entities follow similar pattern
# See specs/core/domain/ACORD_CANONICAL_SCHEMA.md for full definitions
```

**Note:** Full ACORD schema (20-30 fields per entity) will be documented in `ACORD_CANONICAL_SCHEMA.md` spec created next.

### 3.3 Serialization & Deserialization

Pydantic handles JSON serialization/deserialization automatically:

```python
# Serialize to JSON
feed_json = policy_feed.model_dump_json()

# Deserialize from JSON
feed_obj = Feed.model_validate_json(feed_json)

# Serialize to dict
feed_dict = policy_feed.model_dump()

# Deserialize from dict
feed_obj = Feed.model_validate(feed_dict)

# Load from YAML (via pyyaml)
import yaml
with open("feed_config.yaml") as f:
    feed_data = yaml.safe_load(f)
    feed = Feed.model_validate(feed_data)
```

---

## 4. Outputs

### 4.1 Deliverables
* **`core/metadata/models.py`** — Python module with all Pydantic model definitions
* **`core/domain/acord_models.py`** — ACORD entity models (Party, Policy, Coverage, Claim, Payment, Loss)
* **`core/metadata/__init__.py`** — Exports for easy import (`from core.metadata import Feed, Pipeline, ...`)
* **`specs/core/domain/ACORD_CANONICAL_SCHEMA.md`** — Full ACORD schema documentation
* **Unit tests** — `tests/core/metadata/test_models.py` with validation tests

### 4.2 Downstream Consumption
* **engine-contracts-spec.md** — imports these types for protocol method signatures
* **metadata-to-ddl-spec.md** — introspects these Pydantic models to generate DDL
* **config-loader** — deserializes YAML/JSON configs into these objects using Pydantic
* **All engines** — instantiate these models to drive pipeline execution

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
* **Invalid enum values** — Pydantic raises `ValidationError` with clear message
* **Validation failures** — Pydantic validators run automatically; raise `ValidationError` with all errors aggregated
* **Missing required fields** — Pydantic raises `ValidationError` at instantiation

### 5.2 Edge Cases
* **Empty lists** — `Field(default_factory=list)` ensures mutable defaults are safe
* **Optional fields** — use `Optional[T]` with `= None` default
* **Immutable objects** — `Config.frozen = True` prevents field modification after creation

### 5.3 Performance Considerations
* **Pydantic is fast** — v2 uses Rust core; no performance concern for typical config objects
* **JSON serialization** — `model_dump_json()` is optimized; faster than manual serialization

---

## 6. ABC Hooks

### 6.1 Audit
* **Metadata changes** — when a Feed/Pipeline/Rule is created/updated/deleted, call:
  ```python
  abc_sdk.audit(
      event="metadata_update",
      entity_type="Feed",
      entity_id=feed.feed_id,
      user=current_user,
      changes={"old": old_feed.model_dump(), "new": new_feed.model_dump()}
  )
  ```

### 6.2 Balance
* **Not directly applicable** — metadata models themselves don't have balance checks; the pipelines they define will have balance checks

### 6.3 Cost Tracking
* **Metadata storage** — track Delta table writes for metadata tables:
  ```python
  abc_sdk.cost_track(
      operation="metadata_write",
      table=f"{catalog}.{schema}.feed_metadata",
      record_count=1
  )
  ```

### 6.4 Logging
* **Structured logging** — log Pydantic validation errors with trace ID:
  ```python
  import logging
  from pydantic import ValidationError
  
  logger = logging.getLogger(__name__)
  
  try:
      feed = Feed.model_validate(feed_data)
  except ValidationError as e:
      logger.error(f"Feed validation failed", extra={
          "trace_id": trace_id,
          "feed_id": feed_data.get("feed_id"),
          "errors": e.errors()
      })
  ```

---

## 7. Examples

### 7.1 Feed Example
```python
from core.metadata import Feed, SourceFormat, LoadStrategy

# Define a CSV feed with SCD2 strategy
policy_feed = Feed(
    feed_id="policy_master_feed",
    name="Policy Master Data Feed",
    source_system="PolicyAdmin",
    source_format=SourceFormat.CSV,
    source_location="/Volumes/main/raw/policy/",
    load_strategy=LoadStrategy.SCD2,
    target_catalog="main",
    target_schema="bronze",
    target_table="policy_raw",
    primary_keys=["policy_id"],
    partition_columns=["ingest_date"],
    file_format_options={"header": "true", "delimiter": ","},
    enabled=True
)

# Automatic validation (raises ValidationError if invalid)
print(f"Feed FQN: {policy_feed.target_table_fqn}")

# Serialize to JSON
json_str = policy_feed.model_dump_json(indent=2)
print(json_str)

# Deserialize from JSON
loaded_feed = Feed.model_validate_json(json_str)
assert loaded_feed == policy_feed
```

### 7.2 Pipeline Example
```python
from core.metadata import Pipeline, ExecutionMode, Layer, PipelineType

# Define a harmonization pipeline
harmonize_policy = Pipeline(
    pipeline_id="harmonize_policy_pipeline",
    name="Policy Harmonization to Silver",
    description="Transform Bronze policy data to ACORD-aligned Silver",
    pipeline_type=PipelineType.HARMONIZATION,
    execution_mode=ExecutionMode.DECLARATIVE,
    source_layer=Layer.BRONZE,
    target_layer=Layer.SILVER,
    feeds=[],  # Not an ingestion pipeline
    transforms=["policy_bronze_to_silver"],
    dq_checks=["policy_not_null_checks"],
    recon_rules=["policy_row_count_recon"],
    schedule="0 2 * * *",  # Daily at 2 AM
    enabled=True
)

# Pydantic automatically validates that harmonization pipelines have transforms
```

### 7.3 DQCheck Example
```python
from core.metadata import DQCheck, CheckType, CheckSeverity

# Not-null check on policy_number
policy_not_null = DQCheck(
    check_id="policy_number_not_null",
    name="Policy Number Not Null",
    description="Ensure policy_number is never null",
    check_type=CheckType.NOT_NULL,
    table_fqn="main.silver.policy",
    column_name="policy_number",
    severity=CheckSeverity.BLOCK,
    threshold=0.0,  # Fail if any nulls
    enabled=True
)

# Validation happens automatically
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **Valid instantiation** — create each model with valid data, assert no ValidationError
2. **Validation failures** — test each model with invalid data, assert ValidationError raised with correct messages
3. **FQN property** — test `Feed.target_table_fqn` returns correct format
4. **Enum validation** — attempt invalid enum values, assert ValidationError
5. **JSON round-trip** — serialize to JSON, deserialize back, assert equality
6. **Default values** — test empty lists and optional fields have correct defaults
7. **Immutability** — attempt to modify frozen field, assert error
8. **Pipeline type enforcement** — test that INGESTION must have feeds, HARMONIZATION must have transforms

### 8.2 Integration Tests
* **Config loader integration** — load a YAML config file, deserialize to Feed/Pipeline objects using Pydantic
* **DDL generation** — pass models to codegen script, assert valid SQL is produced

### 8.3 Synthetic Data Tests
* **Feed catalog** — 10 sample feeds covering all source formats and load strategies
* **Pipeline examples** — 5 pipelines (ingestion, harmonization, quality, recon, masking)
* **Rule examples** — 20+ rules covering all check types, mask techniques, recon types

---

## 9. References

### 9.1 Internal Documents
* `PROJECT_CONTEXT.md` §3 — framework scope
* `PROJECT_CONTEXT.md` §4 — architecture (Medallion, ACORD, UC)
* `ROADMAP.md` Phase 0 — Wave 0 foundation specs
* `AI_Ready_Backlog_Tasks.xlsx` — FND-001, META-001
* `specs/core/domain/ACORD_CANONICAL_SCHEMA.md` — Full ACORD entity definitions (to be created)

### 9.2 External Standards
* **ACORD** — https://www.acord.org/ (P&C insurance data standards)
* **Pydantic** — https://docs.pydantic.dev/latest/ (v2 validation and serialization)
* **Python typing** — https://docs.python.org/3/library/typing.html

### 9.3 Databricks Documentation
* Unity Catalog table naming — https://docs.databricks.com/aws/en/data-governance/unity-catalog/
* Delta Lake — https://docs.databricks.com/aws/en/delta/

---

## 10. Decisions Made

All clarifications resolved per validation framework recommendations:

1. **ACORD entities** — Define Python dataclasses in `core/domain/acord_models.py` for type safety
2. **ACORD schema** — Minimum viable 20-30 fields per entity; document in `ACORD_CANONICAL_SCHEMA.md`
3. **JDBC source format** — Generic `JDBC` with optional `jdbc_db_type` field
4. **Deserialization** — Use Pydantic v2 for robust validation and auto-conversion
5. **Pipeline validation** — Added `PipelineType` enum; enforce feeds for INGESTION, transforms for HARMONIZATION
6. **Masking techniques** — 5 techniques sufficient for v1; extensible via enum
7. **ReconRule tolerance** — Percentage (0.0 to 1.0); use Pydantic `Field(ge=0.0, le=1.0)` validation

---

**End of Metadata Models Spec (Approved)**
