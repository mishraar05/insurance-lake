---
id: foundation.source-target-config
title: Source & Target Configuration Entities
owner: EY InsureLake Team
status: active
target_path: src/core/metadata/
depends_on:
  - foundation.config-types-enums
  - foundation.config-storage
provides:
  - SourceConfig (Pydantic model)
  - TargetConfig (Pydantic model)
  - Source/Target validators
  - PARAM row serialization for Source/Target
acceptance:
  - "SourceConfig validates file/table/stream/API/CDC sources"
  - "TargetConfig validates Delta managed/external, streaming tables, MVs"
  - "All validators enforce business rules (e.g., API sources require credentials)"
  - "Serialization is lossless (round-trip integrity)"
generation_context:
  - specs/foundation/config-model/source-target-spec.md
  - specs/foundation/config-model/config-types-enums-spec.md
  - specs/foundation/config-model/config-storage-spec.md
regeneration: scaffold-then-edit
---

# Source & Target Configuration Specification

**Status:** Active · 2026-06-23 · Dependencies: config-types-enums-spec.md, config-storage-spec.md

**Architecture Summary:**  
Defines **SourceConfig** and **TargetConfig** entities that represent data sources (file, table, stream, API, CDC) and data targets (Delta managed/external, streaming tables, materialized views) in the metadata-driven framework. Both entities serialize to PARAM rows and integrate with ConfigLoader for persistence and validation.

---

## 1. Purpose & Scope

### Purpose
Define the data structures and validation rules for source and target configurations in the InsureLake framework. These entities drive:
* **Data ingestion** — Where to read data from (files, tables, streams, APIs, CDC feeds)
* **Data persistence** — Where to write data to (Unity Catalog tables, volumes, streaming tables)
* **Governance** — PII flags, data classification, retention policies
* **Schema evolution** — Source system types (stable, regulated, volatile)

### In Scope
* **SourceConfig entity** — Pydantic model with fields, validators, serialization
* **TargetConfig entity** — Pydantic model with fields, validators, serialization, target types
* **Business rule validators** — API sources require credentials, streaming tables require engine=DECLARATIVE, etc.
* **PARAM row serialization** — to_param_rows() / from_param_rows() patterns
* **Integration with ConfigLoader** — Persistence via ABC_JOB_PARAM_TBL / ABC_SRC_CTRL_TBL

### Out of Scope
* **LoadConfig entity** — See load-config-spec.md
* **TransformConfig / DQRuleConfig** — See transform-dq-spec.md
* **Runtime execution logic** — Ingestion engines consume these configs but are defined elsewhere
* **ConfigLoader implementation** — See config-storage-spec.md

---

## 2. Requirements

### Functional Requirements

**FR-1: Multi-Source Support**  
SourceConfig must support:
* FILE sources (CSV, Parquet, JSON, Avro, Delta, ORC) on cloud storage (S3, ADLS, GCS)
* TABLE sources (Unity Catalog tables, external Delta tables)
* STREAM sources (Kafka, Kinesis, Event Hubs)
* API sources (REST APIs, SOAP services, custom connectors)
* CDC sources (Debezium, Oracle GoldenGate, SQL Server CDC)

**FR-2: Multi-Target Support**  
TargetConfig must support:
* Delta managed tables (Unity Catalog default)
* Delta external tables (external location, MANAGED or EXTERNAL)
* Streaming tables (Lakeflow SDP Declarative streaming tables)
* Materialized views (UC materialized views)
* Parquet files (direct Parquet writes for non-Delta targets)
* Other formats (CSV, JSON for legacy interop)

**FR-3: Governance Fields**  
Both SourceConfig and TargetConfig must include:
* PII flag (boolean) — Marks configs containing personally identifiable information
* Data classification (CONFIDENTIAL, RESTRICTED, PUBLIC, INTERNAL)
* Retention policies (retention_days for data lifecycle management)
* Business domain tags (POLICY, CLAIMS, BILLING, CUSTOMER)

**FR-4: Schema Evolution Controls**  
SourceConfig must support schema evolution policies:
* Source system type (stable, regulated, volatile) — Drives mergeSchema/additive rules
* Governance tier (standard, high) — Affects validation strictness
* Type change policy (none, widening, strict) — Controls type evolution rules

**FR-5: Validation-on-Save**  
All fields must be validated via Pydantic validators before persistence:
* Identifiers (source_id, target_id) — Alphanumeric + underscores, 3-100 chars
* Unity Catalog names (catalog, schema, table) — UC-compliant naming rules
* File paths (S3, ADLS, GCS) — Valid URI format
* Enum values (source_type, layer, table_type) — Must match enum definitions
* Business rules (e.g., API sources require connection_string and credentials)

**FR-6: FK Relationships**  
TargetConfig may be referenced by LoadConfig, TransformConfig, DQRuleConfig via target_id (logical FK).

**FR-7: SCD2 Versioning**  
All config changes must preserve immutable history via SCD2 (inherited from config-storage-spec.md).

### Non-Functional Requirements

**NFR-1: Performance**  
Source/Target configs must load in <50ms (part of overall <100ms config load budget).

**NFR-2: Type Safety**  
All fields must have type hints. Pydantic enforces runtime type checking.

**NFR-3: Extensibility**  
New source types (e.g., GraphQL, gRPC) and target types (e.g., Iceberg, Hudi) can be added via enum extension without breaking existing configs.

**NFR-4: Testability**  
All validators must be unit-testable in isolation (no external dependencies).

**NFR-5: Documentation**  
All fields and validators must have Google-style docstrings.

---

## 2.1 Business Rules Matrix

### Source Type Business Rules

| Source Type | Required Fields | Validation Rules |
|-------------|----------------|------------------|
| FILE | file_format, schema_location | schema_location must be valid cloud URI (s3://, abfss://, gs://) |
| TABLE | source_system | Must reference valid UC table or external table |
| STREAM | connection_string | Must be valid Kafka/Kinesis/EventHubs connection string |
| API | connection_string, credential_scope | Credentials required for authentication |
| CDC | connection_string, file_format | file_format specifies CDC format (Debezium JSON, etc.) |

### Target Type Business Rules

| Target Type | Required Fields | Validation Rules | Compatible Engines |
|-------------|----------------|------------------|-------------------|
| DELTA_MANAGED | catalog_name, schema_name, table_name | UC-compliant names | DECLARATIVE, AUTOLOADER, STRUCTURED_STREAMING |
| DELTA_EXTERNAL | catalog_name, schema_name, table_name, location | External location must exist | DECLARATIVE, AUTOLOADER, STRUCTURED_STREAMING |
| STREAMING_TABLE | catalog_name, schema_name, table_name | engine must be DECLARATIVE | DECLARATIVE only |
| MATERIALIZED_VIEW | catalog_name, schema_name, table_name | Must have source table reference | DECLARATIVE only |
| PARQUET | location | Direct file write, no UC catalog | STRUCTURED_STREAMING only |
| CSV | location | Direct file write | STRUCTURED_STREAMING only |

### Layer + Table Type Combinations

| Layer | Allowed Table Types | Rationale |
|-------|-------------------|-----------| 
| BRONZE | DELTA_MANAGED, DELTA_EXTERNAL, STREAMING_TABLE | Raw ingestion layer |
| SILVER | DELTA_MANAGED, STREAMING_TABLE, MATERIALIZED_VIEW | Cleaned, validated data |
| GOLD | DELTA_MANAGED, MATERIALIZED_VIEW | Aggregated, business-ready data |

### Data Classification Requirements

| Classification | Min Retention Days | PII Flag | Encryption Required |
|----------------|-------------------|----------|---------------------|
| PUBLIC | 30 | False | No |
| INTERNAL | 90 | False | Recommended |
| RESTRICTED | 365 | Optional | Yes |
| CONFIDENTIAL | 2555 (7 years) | True | Yes |

---

## 3. Interface Definition

### 3.1 SourceConfig Entity

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from enum import Enum

class SourceConfig(BaseModel):
    """
    Configuration for a data source in the InsureLake framework.
    
    Represents sources from files, tables, streams, APIs, or CDC feeds.
    Validates business rules and serializes to PARAM rows for persistence.
    """
    
    # Identity
    source_id: str = Field(
        ..., 
        min_length=3, 
        max_length=100,
        description="Unique identifier for this source (alphanumeric + underscores)"
    )
    source_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name for this source"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source: FILE, TABLE, STREAM, API, CDC"
    )
    
    # Source Location
    schema_location: Optional[str] = Field(
        None,
        description="Cloud storage path (s3://, abfss://, gs://) or UC table name"
    )
    connection_string: Optional[str] = Field(
        None,
        description="Connection string for STREAM, API, or CDC sources"
    )
    credential_scope: Optional[str] = Field(
        None,
        description="Databricks secret scope for credentials"
    )
    
    # Format & Schema
    file_format: Optional[FileFormat] = Field(
        None,
        description="File format: CSV, PARQUET, JSON, AVRO, DELTA, ORC"
    )
    source_system: Optional[str] = Field(
        None,
        description="Source system identifier (e.g., 'SAP_ECC', 'SALESFORCE')"
    )
    
    # Schema Evolution
    schema_evolution_mode: SchemaEvolutionMode = Field(
        SchemaEvolutionMode.ADDITIVE,
        description="Schema evolution policy: NONE, ADDITIVE, WIDENING, FULL"
    )
    source_system_type: SourceSystemType = Field(
        SourceSystemType.STABLE,
        description="Source system type: STABLE, REGULATED, VOLATILE"
    )
    
    # Governance
    contains_pii: bool = Field(
        False,
        description="Whether this source contains personally identifiable information"
    )
    data_classification: DataClassification = Field(
        DataClassification.INTERNAL,
        description="Data classification: PUBLIC, INTERNAL, RESTRICTED, CONFIDENTIAL"
    )
    business_domain: Optional[BusinessDomain] = Field(
        None,
        description="Business domain: POLICY, CLAIMS, BILLING, CUSTOMER"
    )
    
    # Metadata
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Description of this source"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom metadata tags (key-value pairs)"
    )
    
    # SCD2 Fields (managed by ConfigLoader)
    effective_date: Optional[str] = Field(
        None,
        description="SCD2 effective date (ISO format)"
    )
    end_date: Optional[str] = Field(
        None,
        description="SCD2 end date (ISO format)"
    )
    is_current: bool = Field(
        True,
        description="SCD2 current record flag"
    )
    
    # Validators - See §6 for validation logic
    @field_validator('source_id')
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        """Validate source_id format. Implements Rule SV-1."""
        # Implementation: Apply Rule SV-1 from §6
        pass
    
    @field_validator('schema_location')
    @classmethod
    def validate_schema_location(cls, v: Optional[str], info) -> Optional[str]:
        """Validate schema_location for FILE sources. Implements Rule SV-2."""
        # Implementation: Apply Rule SV-2 from §6
        pass
    
    def model_post_init(self, __context: Any) -> None:
        """
        Post-init validation for cross-field business rules.
        
        Implements Rules: SV-2 (FILE), SV-3 (API), SV-4 (STREAM)
        See §6 for detailed validation logic.
        """
        # Implementation: Apply Rules SV-2, SV-3, SV-4 from §6
        pass
    
    # Serialization Methods
    def to_param_rows(self) -> list[Dict[str, Any]]:
        """
        Serialize SourceConfig to PARAM rows for ABC_SRC_CTRL_TBL.
        
        Format: 'source.{source_id}.{field_name}' → field_value
        
        Serialization rules:
        - Skip None values
        - Serialize enums to .value
        - Serialize dicts to JSON string
        - All values converted to string for param_value
        
        Returns:
            List of dicts with keys: param_name, param_value, param_type
        """
        # Implementation: See §4.3 Serialization Contract
        pass
    
    @classmethod
    def from_param_rows(cls, rows: list[Dict[str, Any]], source_id: str) -> 'SourceConfig':
        """
        Deserialize SourceConfig from PARAM rows.
        
        Args:
            rows: List of param rows from ABC_SRC_CTRL_TBL
            source_id: Source ID to filter rows
            
        Returns:
            SourceConfig instance
            
        Deserialization rules:
        - Filter rows by prefix 'source.{source_id}.'
        - Deserialize JSON strings back to dicts
        - Reconstruct enum instances from string values
        """
        # Implementation: See §4.3 Serialization Contract
        pass
```

### 3.2 TargetConfig Entity

```python
class TargetConfig(BaseModel):
    """
    Configuration for a data target in the InsureLake framework.
    
    Represents targets for Delta tables, streaming tables, materialized views,
    or direct file writes. Validates UC naming rules and business constraints.
    """
    
    # Identity
    target_id: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique identifier for this target (alphanumeric + underscores)"
    )
    target_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name for this target"
    )
    table_type: TableType = Field(
        ...,
        description="Target type: DELTA_MANAGED, DELTA_EXTERNAL, STREAMING_TABLE, etc."
    )
    
    # Unity Catalog Location
    catalog_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Unity Catalog catalog name (required for UC tables)"
    )
    schema_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Unity Catalog schema name (required for UC tables)"
    )
    table_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Unity Catalog table name (required for UC tables)"
    )
    
    # External Location (for DELTA_EXTERNAL, PARQUET, CSV)
    location: Optional[str] = Field(
        None,
        description="External storage location (s3://, abfss://, gs://) or /Volumes/ path"
    )
    
    # Lakehouse Architecture
    layer: Layer = Field(
        ...,
        description="Medallion layer: BRONZE, SILVER, GOLD"
    )
    
    # Write Behavior
    write_mode: WriteMode = Field(
        WriteMode.APPEND,
        description="Write mode: APPEND, OVERWRITE, MERGE, SCD2"
    )
    partition_columns: list[str] = Field(
        default_factory=list,
        description="Partition columns for table optimization"
    )
    cluster_columns: list[str] = Field(
        default_factory=list,
        description="Liquid clustering columns (Delta 3.0+)"
    )
    
    # Governance
    contains_pii: bool = Field(
        False,
        description="Whether this target contains PII"
    )
    data_classification: DataClassification = Field(
        DataClassification.INTERNAL,
        description="Data classification level"
    )
    retention_days: int = Field(
        90,
        ge=30,
        description="Data retention period in days"
    )
    business_domain: Optional[BusinessDomain] = Field(
        None,
        description="Business domain tag"
    )
    
    # Table Properties
    table_properties: Dict[str, str] = Field(
        default_factory=dict,
        description="Delta table properties (e.g., delta.enableChangeDataFeed)"
    )
    
    # Metadata
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Description of this target"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom metadata tags"
    )
    
    # SCD2 Fields
    effective_date: Optional[str] = Field(None, description="SCD2 effective date")
    end_date: Optional[str] = Field(None, description="SCD2 end date")
    is_current: bool = Field(True, description="SCD2 current flag")
    
    # Validators - See §6 for validation logic
    @field_validator('target_id')
    @classmethod
    def validate_target_id(cls, v: str) -> str:
        """Validate target_id format. Implements Rule TV-1."""
        # Implementation: Apply Rule TV-1 from §6
        pass
    
    @field_validator('catalog_name', 'schema_name', 'table_name')
    @classmethod
    def validate_uc_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate Unity Catalog naming rules. Implements Rule TV-3."""
        # Implementation: Apply Rule TV-3 from §6
        pass
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """Validate external location path. Implements Rule TV-2."""
        # Implementation: Apply Rule TV-2 from §6
        pass
    
    def model_post_init(self, __context: Any) -> None:
        """
        Post-init validation for cross-field business rules.
        
        Implements Rules: TV-1 (UC requirements), TV-2 (external location),
        TV-4 (layer compatibility), TV-5 (retention policy)
        See §6 for detailed validation logic.
        """
        # Implementation: Apply Rules TV-1, TV-2, TV-4, TV-5 from §6
        pass
    
    # Serialization Methods
    def to_param_rows(self) -> list[Dict[str, Any]]:
        """
        Serialize TargetConfig to PARAM rows for ABC_JOB_PARAM_TBL.
        
        Format: 'target.{target_id}.{field_name}' → field_value
        
        Returns:
            List of dicts with keys: param_name, param_value, param_type
        """
        # Implementation: See §4.3 Serialization Contract
        pass
    
    @classmethod
    def from_param_rows(cls, rows: list[Dict[str, Any]], target_id: str) -> 'TargetConfig':
        """
        Deserialize TargetConfig from PARAM rows.
        
        Args:
            rows: List of param rows from ABC_JOB_PARAM_TBL
            target_id: Target ID to filter rows
            
        Returns:
            TargetConfig instance
        """
        # Implementation: See §4.3 Serialization Contract
        pass
    
    @property
    def full_table_name(self) -> Optional[str]:
        """
        Return fully qualified UC table name.
        
        Returns:
            '{catalog_name}.{schema_name}.{table_name}' or None
        """
        if all([self.catalog_name, self.schema_name, self.table_name]):
            return f"{self.catalog_name}.{self.schema_name}.{self.table_name}"
        return None
```

---

## 4. Implementation Guidelines

### 4.1 Module Structure

```
src/core/metadata/
├── __init__.py
├── source_config.py      # SourceConfig class
├── target_config.py      # TargetConfig class
└── validators.py         # Shared validator utilities
```

### 4.2 Validator Implementation Pattern

All validators follow this pattern:

```python
@field_validator('field_name')
@classmethod
def validate_field(cls, v: <type>, info: ValidationInfo) -> <type>:
    """
    Validate field_name according to Rule X.
    
    Args:
        v: Field value
        info: Pydantic validation context (access other fields via info.data)
        
    Returns:
        Validated value
        
    Raises:
        ValueError: If validation fails with descriptive message
    """
    # Access other fields: other_value = info.data.get('other_field')
    # Validate according to rule in §6
    # Return validated value or raise ValueError
```

### 4.3 Serialization Contract

Both `to_param_rows()` and `from_param_rows()` must satisfy:

**Serialization Rules (to_param_rows):**
1. Skip None values
2. Convert enums to `.value` string
3. Convert dicts/lists to JSON string via `json.dumps()`
4. All param_value must be strings
5. Use prefix: `source.{id}.{field}` or `target.{id}.{field}`

**Deserialization Rules (from_param_rows):**
1. Filter rows by prefix
2. Parse JSON strings back to dicts/lists for appropriate fields
3. Enum reconstruction handled by Pydantic from string values
4. Return fully validated model instance

**Round-Trip Guarantee:**
```python
original = SourceConfig(...)
rows = original.to_param_rows()
reconstructed = SourceConfig.from_param_rows(rows, original.source_id)
assert original == reconstructed  # Must be True
```

### 4.4 Error Handling

```python
try:
    source = SourceConfig(**data)
except ValidationError as e:
    # Log validation errors with field names and messages
    logger.error(f"SourceConfig validation failed: {e.errors()}")
    # Re-raise with domain context
    raise ConfigValidationError(
        f"Invalid source config for {data.get('source_id')}",
        errors=e.errors()
    ) from e
```

### 4.5 Testing Strategy

**Unit Tests:**
* Test each validator in isolation
* Test all business rules from §6
* Test serialization round-trip for all field types

**Integration Tests:**
* Test ConfigLoader persistence
* Test SCD2 version history
* Test FK relationships with dependent configs

**Property-Based Tests:**
* Generate random valid configs (hypothesis)
* Verify round-trip invariants

---

## 5. Data Model

### 5.1 PARAM Row Schema

Both SourceConfig and TargetConfig serialize to PARAM rows in `ABC_JOB_PARAM_TBL`:

| Column | Type | Description |
|--------|------|-------------|
| param_name | STRING | Qualified parameter name (e.g., `source.claims_file.source_type`) |
| param_value | STRING | Serialized value (primitives as strings, collections as JSON) |
| param_type | STRING | Python type name (str, int, bool, list, dict) |
| effective_date | TIMESTAMP | SCD2 effective date |
| end_date | TIMESTAMP | SCD2 end date (NULL for current) |
| is_current | BOOLEAN | SCD2 current flag |

### 5.2 Naming Convention

**SourceConfig:**
```
source.{source_id}.{field_name}
```

Examples:
* `source.claims_file.source_type` → `"FILE"`
* `source.claims_file.schema_location` → `"s3://bucket/claims/"`
* `source.claims_file.contains_pii` → `"true"`

**TargetConfig:**
```
target.{target_id}.{field_name}
```

Examples:
* `target.bronze_claims.catalog_name` → `"insurance"`
* `target.bronze_claims.layer` → `"BRONZE"`
* `target.bronze_claims.partition_columns` → `'["claim_date", "region"]'` (JSON)

### 5.3 Example Serialized Rows

**SourceConfig PARAM Rows:**

| param_name | param_value | param_type |
|------------|-------------|------------|
| source.claims_file.source_id | claims_file | str |
| source.claims_file.source_type | FILE | str |
| source.claims_file.file_format | CSV | str |
| source.claims_file.schema_location | s3://insurance-lake/raw/claims/ | str |
| source.claims_file.contains_pii | True | bool |
| source.claims_file.data_classification | CONFIDENTIAL | str |

**TargetConfig PARAM Rows:**

| param_name | param_value | param_type |
|------------|-------------|------------|
| target.bronze_claims.target_id | bronze_claims | str |
| target.bronze_claims.table_type | DELTA_MANAGED | str |
| target.bronze_claims.catalog_name | insurance | str |
| target.bronze_claims.schema_name | bronze | str |
| target.bronze_claims.table_name | claims | str |
| target.bronze_claims.layer | BRONZE | str |
| target.bronze_claims.partition_columns | ["claim_date"] | str |

---

## 6. Logic & Validation Rules

### 6.1 Source Validation Logic

**Rule SV-1: Source ID Format**
```
VALIDATOR: validate_source_id
INPUT: source_id (str)
LOGIC:
  1. Remove all underscores from source_id
  2. Check if remaining characters are alphanumeric
  3. IF NOT alphanumeric: RAISE ValueError("source_id must be alphanumeric with underscores")
  4. RETURN source_id
```

**Rule SV-2: FILE Source Requirements**
```
VALIDATOR: validate_schema_location, model_post_init
INPUT: schema_location (Optional[str]), source_type (SourceType)
LOGIC:
  1. IF schema_location is None: RETURN None
  2. IF source_type == SourceType.FILE:
     a. Define valid_prefixes = ('s3://', 'abfss://', 'gs://', '/Volumes/')
     b. Check if schema_location starts with any valid prefix
     c. IF NOT: RAISE ValueError("FILE source schema_location must start with {valid_prefixes}")
  3. IF source_type == SourceType.FILE AND (file_format is None OR schema_location is None):
     RAISE ValueError("FILE sources require file_format and schema_location")
  4. RETURN schema_location
```

**Rule SV-3: API Source Requirements**
```
VALIDATOR: model_post_init
INPUT: source_type, connection_string, credential_scope
LOGIC:
  1. IF source_type == SourceType.API:
     a. IF connection_string is None OR credential_scope is None:
        RAISE ValueError("API sources require connection_string and credential_scope")
```

**Rule SV-4: STREAM Source Requirements**
```
VALIDATOR: model_post_init
INPUT: source_type, connection_string
LOGIC:
  1. IF source_type == SourceType.STREAM:
     a. IF connection_string is None:
        RAISE ValueError("STREAM sources require connection_string")
```

### 6.2 Target Validation Logic

**Rule TV-1: Target ID Format & UC Table Requirements**
```
VALIDATOR: validate_target_id, model_post_init
INPUT: target_id (str), table_type, catalog_name, schema_name, table_name
LOGIC:
  1. [Target ID Format]
     a. Remove all underscores from target_id
     b. Check if remaining characters are alphanumeric
     c. IF NOT alphanumeric: RAISE ValueError("target_id must be alphanumeric with underscores")
  
  2. [UC Table Requirements]
     a. Define uc_types = {DELTA_MANAGED, DELTA_EXTERNAL, STREAMING_TABLE, MATERIALIZED_VIEW}
     b. IF table_type IN uc_types:
        - IF NOT all([catalog_name, schema_name, table_name]):
          RAISE ValueError("{table_type} requires catalog_name, schema_name, and table_name")
```

**Rule TV-2: External Location Requirements**
```
VALIDATOR: validate_location, model_post_init
INPUT: location (Optional[str]), table_type
LOGIC:
  1. [Location Format]
     a. IF location is None: RETURN None
     b. Define valid_prefixes = ('s3://', 'abfss://', 'gs://', '/Volumes/')
     c. Check if location starts with any valid prefix
     d. IF NOT: RAISE ValueError("location must start with {valid_prefixes}")
  
  2. [Required for External Tables]
     a. IF table_type == TableType.DELTA_EXTERNAL AND location is None:
        RAISE ValueError("DELTA_EXTERNAL requires location")
  
  3. [Required for File Targets]
     a. IF table_type IN {TableType.PARQUET, TableType.CSV} AND location is None:
        RAISE ValueError("{table_type} requires location")
```

**Rule TV-3: UC Naming Rules**
```
VALIDATOR: validate_uc_name
INPUT: uc_name (Optional[str]) - applies to catalog_name, schema_name, table_name
LOGIC:
  1. IF uc_name is None: RETURN None
  2. Remove all underscores from uc_name
  3. Check if remaining characters are alphanumeric
  4. IF NOT alphanumeric: RAISE ValueError("UC names must be alphanumeric with underscores")
  5. IF first character is digit: RAISE ValueError("UC names cannot start with a digit")
  6. RETURN uc_name
```

**Rule TV-4: Layer + TableType Compatibility**
```
VALIDATOR: model_post_init
INPUT: layer (Layer), table_type (TableType)
LOGIC:
  1. Define layer_table_map:
     BRONZE → {DELTA_MANAGED, DELTA_EXTERNAL, STREAMING_TABLE}
     SILVER → {DELTA_MANAGED, STREAMING_TABLE, MATERIALIZED_VIEW}
     GOLD → {DELTA_MANAGED, MATERIALIZED_VIEW}
  
  2. Get allowed_types = layer_table_map[layer]
  3. IF table_type NOT IN allowed_types:
     RAISE ValueError("{table_type} not allowed in {layer} layer")
```

**Rule TV-5: Retention Policy Enforcement**
```
VALIDATOR: model_post_init
INPUT: data_classification, retention_days
LOGIC:
  1. Define min_retention map:
     PUBLIC → 30 days
     INTERNAL → 90 days
     RESTRICTED → 365 days
     CONFIDENTIAL → 2555 days (7 years)
  
  2. Get min_days = min_retention[data_classification]
  3. IF retention_days < min_days:
     RAISE ValueError("{data_classification} requires >= {min_days} retention days")
```

---

## 7. Testing & Acceptance

### 7.1 Unit Test Cases

**Test Suite: SourceConfig Validation**

```python
def test_source_id_alphanumeric_only():
    """SourceConfig.source_id must be alphanumeric + underscores."""
    with pytest.raises(ValueError, match="alphanumeric with underscores"):
        SourceConfig(source_id='invalid-id', ...)

def test_file_source_requires_format_and_location():
    """FILE sources must specify file_format and schema_location."""
    with pytest.raises(ValueError, match="FILE sources require"):
        SourceConfig(
            source_type=SourceType.FILE,
            file_format=None,
            schema_location='s3://bucket/path',
            ...
        )

def test_file_source_location_must_be_cloud_uri():
    """FILE schema_location must start with s3://, abfss://, gs://, or /Volumes/."""
    with pytest.raises(ValueError, match="valid cloud URI"):
        SourceConfig(
            source_type=SourceType.FILE,
            schema_location='/local/path',
            ...
        )

def test_api_source_requires_credentials():
    """API sources must have connection_string and credential_scope."""
    with pytest.raises(ValueError, match="API sources require"):
        SourceConfig(
            source_type=SourceType.API,
            connection_string=None,
            credential_scope=None,
            ...
        )

def test_stream_source_requires_connection_string():
    """STREAM sources must have connection_string."""
    with pytest.raises(ValueError, match="STREAM sources require"):
        SourceConfig(
            source_type=SourceType.STREAM,
            connection_string=None,
            ...
        )
```

**Test Suite: TargetConfig Validation**

```python
def test_target_id_alphanumeric_only():
    """TargetConfig.target_id must be alphanumeric + underscores."""
    with pytest.raises(ValueError, match="alphanumeric"):
        TargetConfig(target_id='invalid-id', ...)

def test_uc_table_requires_catalog_schema_table():
    """UC table types must have catalog_name, schema_name, table_name."""
    with pytest.raises(ValueError, match="requires catalog_name"):
        TargetConfig(
            table_type=TableType.DELTA_MANAGED,
            catalog_name=None,
            ...
        )

def test_uc_names_cannot_start_with_digit():
    """UC names cannot start with a digit."""
    with pytest.raises(ValueError, match="cannot start with a digit"):
        TargetConfig(
            catalog_name='9insurance',
            ...
        )

def test_delta_external_requires_location():
    """DELTA_EXTERNAL must have location."""
    with pytest.raises(ValueError, match="DELTA_EXTERNAL requires location"):
        TargetConfig(
            table_type=TableType.DELTA_EXTERNAL,
            location=None,
            ...
        )

def test_layer_table_type_compatibility():
    """Layer + TableType combinations must be allowed."""
    with pytest.raises(ValueError, match="not allowed in GOLD layer"):
        TargetConfig(
            layer=Layer.GOLD,
            table_type=TableType.STREAMING_TABLE,
            ...
        )

def test_retention_days_meets_classification_minimum():
    """Retention days must meet minimum for data_classification."""
    with pytest.raises(ValueError, match="CONFIDENTIAL requires >= 2555"):
        TargetConfig(
            data_classification=DataClassification.CONFIDENTIAL,
            retention_days=365,
            ...
        )
```

**Test Suite: Serialization**

```python
def test_source_config_serialization_round_trip():
    """SourceConfig serialization must be lossless."""
    original = SourceConfig(
        source_id='test_source',
        source_name='Test Source',
        source_type=SourceType.FILE,
        file_format=FileFormat.CSV,
        schema_location='s3://bucket/path',
        contains_pii=True,
        tags={'owner': 'analytics'}
    )
    
    rows = original.to_param_rows()
    reconstructed = SourceConfig.from_param_rows(rows, 'test_source')
    
    assert original == reconstructed

def test_target_config_serialization_round_trip():
    """TargetConfig serialization must be lossless."""
    original = TargetConfig(
        target_id='test_target',
        target_name='Test Target',
        table_type=TableType.DELTA_MANAGED,
        catalog_name='insurance',
        schema_name='bronze',
        table_name='test',
        layer=Layer.BRONZE,
        partition_columns=['date', 'region'],
        tags={'env': 'dev'}
    )
    
    rows = original.to_param_rows()
    reconstructed = TargetConfig.from_param_rows(rows, 'test_target')
    
    assert original == reconstructed
```

### 7.2 Integration Test Cases

```python
def test_source_config_persists_via_config_loader(spark):
    """SourceConfig integrates with ConfigLoader for persistence."""
    loader = ConfigLoader(spark, catalog='insurance', schema='config')
    
    source = SourceConfig(
        source_id='claims_file',
        source_name='Claims CSV Files',
        source_type=SourceType.FILE,
        file_format=FileFormat.CSV,
        schema_location='s3://insurance-lake/raw/claims/',
        contains_pii=True
    )
    
    loader.save_source_config(source)
    loaded = loader.load_source_config('claims_file')
    
    assert loaded == source

def test_target_config_persists_via_config_loader(spark):
    """TargetConfig integrates with ConfigLoader for persistence."""
    loader = ConfigLoader(spark, catalog='insurance', schema='config')
    
    target = TargetConfig(
        target_id='bronze_claims',
        target_name='Bronze Claims Table',
        table_type=TableType.DELTA_MANAGED,
        catalog_name='insurance',
        schema_name='bronze',
        table_name='claims',
        layer=Layer.BRONZE,
        partition_columns=['claim_date']
    )
    
    loader.save_target_config(target)
    loaded = loader.load_target_config('bronze_claims')
    
    assert loaded == target
```

### 7.3 Acceptance Criteria

✅ **AC-1: Multi-Source Support**  
SourceConfig validates FILE, TABLE, STREAM, API, and CDC sources with appropriate field requirements.

✅ **AC-2: Multi-Target Support**  
TargetConfig validates Delta managed/external, streaming tables, materialized views, Parquet, and CSV targets.

✅ **AC-3: Business Rule Enforcement**  
All validators enforce business rules (API sources require credentials, streaming tables work only in DECLARATIVE engine, etc.).

✅ **AC-4: UC Naming Compliance**  
UC identifiers (catalog, schema, table) follow Unity Catalog naming rules (alphanumeric + underscores, no leading digit).

✅ **AC-5: Layer + TableType Compatibility**  
Layer + TableType combinations are validated per business rules matrix.

✅ **AC-6: Retention Policy Enforcement**  
Data classification drives minimum retention days (PUBLIC: 30, INTERNAL: 90, RESTRICTED: 365, CONFIDENTIAL: 2555).

✅ **AC-7: Lossless Serialization**  
`to_param_rows()` and `from_param_rows()` provide lossless round-trip serialization.

✅ **AC-8: SCD2 Integration**  
Both entities include SCD2 fields (effective_date, end_date, is_current) for version history.

✅ **AC-9: Type Safety**  
All fields have type hints; Pydantic enforces runtime type checking.

✅ **AC-10: Performance**  
Config load time <50ms for typical configs (<100ms budget overall).

---

## 8. Examples

### 8.1 Example: FILE Source + DELTA_MANAGED Target

```python
from src.core.metadata import SourceConfig, TargetConfig
from src.core.metadata.enums import SourceType, FileFormat, TableType, Layer, DataClassification

# Define FILE source for claims CSV files
source = SourceConfig(
    source_id='claims_csv',
    source_name='Claims CSV Files',
    source_type=SourceType.FILE,
    file_format=FileFormat.CSV,
    schema_location='s3://insurance-lake/raw/claims/',
    source_system='POLICY_ADMIN_SYSTEM',
    contains_pii=True,
    data_classification=DataClassification.CONFIDENTIAL,
    description='Daily claims export from policy admin system'
)

# Define DELTA_MANAGED target in Bronze layer
target = TargetConfig(
    target_id='bronze_claims',
    target_name='Bronze Claims Table',
    table_type=TableType.DELTA_MANAGED,
    catalog_name='insurance',
    schema_name='bronze',
    table_name='claims',
    layer=Layer.BRONZE,
    write_mode=WriteMode.APPEND,
    partition_columns=['claim_date', 'region'],
    contains_pii=True,
    data_classification=DataClassification.CONFIDENTIAL,
    retention_days=2555,  # 7 years for CONFIDENTIAL
    table_properties={
        'delta.enableChangeDataFeed': 'true',
        'delta.columnMapping.mode': 'name'
    },
    description='Raw claims data ingested from CSV files'
)

# Validate
print(f"Source: {source.source_name}")
print(f"Target: {target.full_table_name}")  # insurance.bronze.claims
```

### 8.2 Example: STREAM Source + STREAMING_TABLE Target

```python
# Define Kafka stream source
source = SourceConfig(
    source_id='iot_telemetry_stream',
    source_name='IoT Telemetry Kafka Stream',
    source_type=SourceType.STREAM,
    connection_string='kafka-broker.example.com:9092',
    credential_scope='kafka_secrets',
    source_system='IOT_GATEWAY',
    schema_evolution_mode=SchemaEvolutionMode.ADDITIVE,
    contains_pii=False,
    data_classification=DataClassification.INTERNAL,
    description='Real-time vehicle telemetry from IoT devices'
)

# Define streaming table target
target = TargetConfig(
    target_id='bronze_telemetry_stream',
    target_name='Bronze Telemetry Streaming Table',
    table_type=TableType.STREAMING_TABLE,
    catalog_name='insurance',
    schema_name='bronze',
    table_name='iot_telemetry',
    layer=Layer.BRONZE,
    contains_pii=False,
    data_classification=DataClassification.INTERNAL,
    retention_days=90,
    description='Real-time IoT telemetry streaming table'
)

# Note: STREAMING_TABLE requires engine=DECLARATIVE (validated at LoadConfig level)
```

### 8.3 Example: API Source + MATERIALIZED_VIEW Target

```python
# Define REST API source
source = SourceConfig(
    source_id='salesforce_api',
    source_name='Salesforce REST API',
    source_type=SourceType.API,
    connection_string='https://api.salesforce.com/v52.0',
    credential_scope='salesforce_secrets',
    source_system='SALESFORCE',
    contains_pii=True,
    data_classification=DataClassification.RESTRICTED,
    business_domain=BusinessDomain.CUSTOMER,
    description='Customer data from Salesforce CRM'
)

# Define materialized view target (Gold layer, aggregated)
target = TargetConfig(
    target_id='gold_customer_summary_mv',
    target_name='Gold Customer Summary MV',
    table_type=TableType.MATERIALIZED_VIEW,
    catalog_name='insurance',
    schema_name='gold',
    table_name='customer_summary',
    layer=Layer.GOLD,
    contains_pii=False,  # Aggregated, de-identified
    data_classification=DataClassification.INTERNAL,
    retention_days=365,
    business_domain=BusinessDomain.CUSTOMER,
    description='Aggregated customer metrics materialized view'
)
```

### 8.4 Example: Serialization to PARAM Rows

```python
# Create SourceConfig
source = SourceConfig(
    source_id='claims_file',
    source_name='Claims CSV',
    source_type=SourceType.FILE,
    file_format=FileFormat.CSV,
    schema_location='s3://bucket/claims/',
    contains_pii=True,
    tags={'env': 'prod', 'owner': 'analytics'}
)

# Serialize to PARAM rows
param_rows = source.to_param_rows()

# Example rows:
# [
#     {'param_name': 'source.claims_file.source_id', 'param_value': 'claims_file', 'param_type': 'str'},
#     {'param_name': 'source.claims_file.source_type', 'param_value': 'FILE', 'param_type': 'str'},
#     {'param_name': 'source.claims_file.file_format', 'param_value': 'CSV', 'param_type': 'str'},
#     {'param_name': 'source.claims_file.schema_location', 'param_value': 's3://bucket/claims/', 'param_type': 'str'},
#     {'param_name': 'source.claims_file.contains_pii', 'param_value': 'True', 'param_type': 'bool'},
#     {'param_name': 'source.claims_file.tags', 'param_value': '{"env": "prod", "owner": "analytics"}', 'param_type': 'dict'}
# ]

# Deserialize from PARAM rows
reconstructed = SourceConfig.from_param_rows(param_rows, 'claims_file')
assert reconstructed == source  # Lossless round-trip
```

---

## 9. References

* **Dependencies:**
  * `config-types-enums-spec.md` — Enum definitions (SourceType, TableType, Layer, etc.)
  * `config-storage-spec.md` — ConfigLoader, SCD2 persistence, PARAM row schema

* **Dependent Specs:**
  * `load-config-spec.md` — LoadConfig references SourceConfig + TargetConfig
  * `transform-dq-spec.md` — TransformConfig / DQRuleConfig reference TargetConfig

* **External References:**
  * [Pydantic V2 Docs](https://docs.pydantic.dev/latest/)
  * [Unity Catalog Naming Rules](https://docs.databricks.com/sql/language-manual/sql-ref-names.html)
  * [Delta Lake Table Properties](https://docs.delta.io/latest/table-properties.html)

---

**End of Specification**
