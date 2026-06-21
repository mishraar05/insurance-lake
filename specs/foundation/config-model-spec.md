---
id: foundation.config-model
title: Metadata / Config Model
owner: EY
status: active
target_path: src/core/metadata/
owning_skill: framework-dev.build-config-model
backlog: [FND-001]
provides:
  - SourceConfig
  - TargetConfig
  - LoadConfig
  - TransformConfig
  - DQRuleConfig
  - ConfigLoader
depends_on:
  - abc-sdk-spec
generation_context:
  - specs/foundation/config-model-spec.md
  - specs/foundation/abc-sdk-spec.md
acceptance:
  - "pytest tests/unit/test_config_model.py"
  - "pytest tests/integration/test_config_loader.py"
regeneration: scaffold-then-edit
---

# FND-001 - Metadata / Config Model Specification

Status: active · 2026-06-18 · Skill: `framework-dev.build-config-model`
Schema: `insurelake_config.config` (Unity Catalog). All tables are Delta, audited, and linked to the existing ABC framework (they do not duplicate ABC).

## 1. Purpose & scope
Define the configuration entities that drive the metadata-driven framework. The ingestion and harmonization engines and all cross-cutting services read only from these tables; behaviour is config, not code.

**In scope:** Eight config entities (source, target, load, transform, dq_rule, recon_rule, masking_rule, dependency) that capture all metadata for insurance lake ingestion, transformation, and quality checks.

**Out of scope:** Runtime state (logs, checkpoints, execution history) - those belong in ABC framework tables.

## 2. Requirements

**Functional:**
- FR-1: Define 8 config entities: source, target, load, transform, dq_rule, recon_rule, masking_rule, dependency
- FR-2: Support multi-layer (BRONZE|SILVER|GOLD) and multi-engine (DECLARATIVE|AUTOLOADER|STRUCTURED_STREAMING) patterns
- FR-3: Enforce referential integrity (FKs validated on load) and business rules (validation section)
- FR-4: Version all config changes (who, when, before/after) via ABC audit framework
- FR-5: Support multi-customer isolation via catalog/schema namespacing

**Non-functional:**
- NFR-1: All tables are Delta format in Unity Catalog
- NFR-2: Config queries must be fast (<100ms) - indexed on PKs/FKs
- NFR-3: Extensible - new config types added without modifying existing entities
- NFR-4: Immutable config versions - changes append, never update in place

## 3. Interface - exact skeleton

```python
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class SourceType(str, Enum):
    FILE = "FILE"
    TABLE = "TABLE"
    STREAM = "STREAM"
    API = "API"
    CDC = "CDC"

class SourceConfig(BaseModel):
    source_id: str
    source_name: str
    source_type: SourceType
    source_system: str
    connection_string: Optional[str]
    file_format: Optional[str]
    schema_location: Optional[str]
    credential_scope: Optional[str]
    credential_key: Optional[str]
    business_domain: str
    pii_flag: bool
    data_classification: str
    sla_hours: int
    active_flag: bool = True

class TargetConfig(BaseModel):
    target_id: str
    target_name: str
    catalog_name: str
    schema_name: str
    table_name: str
    layer: str  # BRONZE|SILVER|GOLD
    table_type: str  # MANAGED|EXTERNAL
    format: str  # DELTA
    partition_columns: List[str]
    liquid_clustering_columns: List[str]
    primary_key: List[str]
    acord_entity: Optional[str]
    retention_days: int
    enable_cdf: bool
    active_flag: bool = True

class LoadConfig(BaseModel):
    load_id: str
    load_name: str
    source_id: str
    target_id: str
    load_type: str
    load_pattern: str
    engine: str
    watermark_column: Optional[str]
    watermark_type: Optional[str]
    checkpoint_location: str
    trigger_interval: Optional[str]
    merge_keys: Optional[List[str]]
    autoloader_options: dict
    schedule_cron: Optional[str]
    depends_on: Optional[List[str]]
    active_flag: bool = True

class TransformConfig(BaseModel):
    transform_id: str
    transform_name: str
    source_target_id: str
    destination_target_id: str
    transform_type: str
    transform_sql: Optional[str]
    transform_python: Optional[str]
    acord_mapping_template: Optional[str]
    scd_type: Optional[str]
    scd_key_columns: Optional[List[str]]
    scd_timestamp_column: Optional[str]
    engine: str
    dependencies: Optional[List[str]]
    active_flag: bool = True

class DQRuleConfig(BaseModel):
    dq_rule_id: str
    rule_name: str
    target_id: str
    rule_type: str
    column_name: str
    rule_expression: Optional[str]
    threshold_percent: float
    on_failure: str  # WARN|FAIL|QUARANTINE
    active_flag: bool = True

class ConfigLoader:
    """Loads configuration from Unity Catalog tables."""
    
    def get_source(self, source_id: str) -> SourceConfig:
        """Retrieve source configuration by ID."""
        pass
    
    def get_target(self, target_id: str) -> TargetConfig:
        """Retrieve target configuration by ID."""
        pass
    
    def get_load(self, load_id: str) -> LoadConfig:
        """Retrieve load configuration by ID."""
        pass
    
    def get_transform(self, transform_id: str) -> TransformConfig:
        """Retrieve transform configuration by ID."""
        pass
    
    def get_dq_rule(self, dq_rule_id: str) -> DQRuleConfig:
        """Retrieve DQ rule configuration by ID."""
        pass
    
    def save_source(self, config: SourceConfig) -> None:
        """Save source configuration."""
        pass
    
    def save_target(self, config: TargetConfig) -> None:
        """Save target configuration."""
        pass
    
    def save_load(self, config: LoadConfig) -> None:
        """Save load configuration."""
        pass
```

## 4. Inputs / Outputs
- **Inputs:** Config YAML files, admin UI forms, API payloads, migration scripts
- **Outputs:** Delta tables in Unity Catalog; Python/Pydantic config classes (`SourceConfig`, `TargetConfig`, etc.) for SDK consumption

## 5. Design

### Data Model Architecture
- **Normalized star schema:** Core entities (source, target) + associative entities (load, transform, dq_rule)
- **Delta tables in UC:** All config lives in `insurelake_config.config` schema
- **Versioned via ABC:** Every change writes audit record (who, when, before/after)
- **Multi-customer:** Catalog/schema isolation + customer_id dimension (optional)

### SDK Layer
- **Pydantic models:** One class per entity (`SourceConfig`, `TargetConfig`, etc.)
- **Loader utilities:** `ConfigLoader` reads from UC tables, returns typed config objects
- **Validation:** Pydantic validators enforce business rules (section 6)

### SOLID Principles Application

**Single Responsibility Principle (SRP):**
- Each config entity has ONE concern:
  - `source` describes origins (FILE, TABLE, API)
  - `target` describes destinations (layer, partitioning, clustering)
  - `load` describes source->target mapping (engine, pattern, schedule)
  - `dq_rule` describes quality checks (rule type, threshold, action)
- Example: `source` knows nothing about load patterns or quality rules — those are separate entities

**Open/Closed Principle (OCP):**
- **Closed for modification:** Existing entities stable (no new columns break existing code)
- **Open for extension:** New config types → new entities (e.g., `masking_rule`, `recon_rule`)
- Example:
  ```python
  # Adding PII masking: NEW entity (masking_rule), not new columns on source/target
  # Existing code unchanged; new engines read masking_rule
  ```
- New source types extend via `source_type` enum, not schema changes

**Liskov Substitution Principle (LSP):**
- **Config polymorphism:** Any `source_type` (FILE|TABLE|API) substitutes where `source` expected
- Engines read `SourceConfig` abstraction, don't branch on concrete types
- Example:
  ```python
  def load_data(source: SourceConfig):  # Works with ANY source_type
      if source.source_type == "FILE":
          reader = FileReader(source)
      elif source.source_type == "API":
          reader = APIReader(source)
      # Same interface for all readers
  ```

**Interface Segregation Principle (ISP):**
- **Segregated entities:** source, target, load, transform, dq_rule, masking_rule (separate tables)
- Clients read only what they need:
  - Ingestion engine reads `source` + `load` (not transform/dq)
  - Harmonization engine reads `transform` (not source/load)
  - DQ engine reads `dq_rule` (not source/target/load)
- Counter-example (DON'T DO):
  ```python
  # BAD: Fat config table with all concerns
  cfg_everything: source_*, target_*, load_*, transform_*, dq_*
  # Problem: Every engine reads massive table with unused columns
  ```

**Dependency Inversion Principle (DIP):**
- **Engines depend on abstractions:** `SourceConfig`, `TargetConfig` (Pydantic models), not raw Delta tables
- Config loader abstracts storage format (UC tables today, could be REST API tomorrow)
- Example:
  ```python
  # High-level engine depends on abstraction
  class IngestionEngine:
      def __init__(self, config_loader: ConfigLoader):  # DIP - abstraction
          self._loader = config_loader
      
      def run(self, load_id: str):
          load_cfg = self._loader.get_load(load_id)  # Returns LoadConfig
          source_cfg = self._loader.get_source(load_cfg.source_id)  # SourceConfig
          # Engine doesn't know config comes from Delta tables
  
  # Concrete loader depends on same abstraction
  class UCConfigLoader(ConfigLoader):
      def get_load(self, load_id):
          df = spark.read.table("insurelake_config.config.cfg_load")
          # Returns LoadConfig (abstraction)
  ```

### Design Patterns
- **Repository pattern:** `ConfigLoader` abstracts config persistence (Delta tables, REST API, etc.)
- **Factory pattern:** Create reader/writer instances based on `source_type` / `load_pattern`
- **Strategy pattern:** DQ rule execution strategies (NOT_NULL, RANGE, CUSTOM_SQL)

## 6. Logic / algorithm

### Config Loading Flow
```python
# 1. Read config from UC tables
loader = UCConfigLoader(spark)
load_cfg = loader.get_load("load_001")

# 2. Resolve dependencies (FK traversal)
source_cfg = loader.get_source(load_cfg.source_id)
target_cfg = loader.get_target(load_cfg.target_id)

# 3. Build execution plan
if load_cfg.engine == "DECLARATIVE":
    pipeline = DeclarativePipeline(source_cfg, target_cfg, load_cfg)
elif load_cfg.engine == "AUTOLOADER":
    pipeline = AutoLoaderPipeline(source_cfg, target_cfg, load_cfg)

# 4. Execute
pipeline.run()
```

### Config Validation Rules
- **FK integrity:** All foreign keys must resolve (source_id in cfg_source, target_id in cfg_target)
- **Enum validation:** `source_type`, `load_pattern`, `engine` must be valid enum values
- **Business rules:**
  - STREAM_* load_types require `watermark_column`
  - SCD2 load_pattern requires `merge_keys`
  - DECLARATIVE engine requires `checkpoint_location`
- **Naming conventions:**
  - `source_name`: alphanumeric + underscores, no spaces
  - `table_name`: UC-compliant (catalog.schema.table)

### Config Versioning
Every change to config tables triggers ABC audit:
```python
# Before update
old_cfg = get_config("load_001")

# Update
update_config("load_001", {"schedule_cron": "0 8 * * *"})

# ABC audit captures change
abc_sdk.audit(
    event="config_update",
    entity_type="load",
    entity_id="load_001",
    before=old_cfg,
    after=new_cfg,
    changed_by=current_user()
)
```

### Multi-Customer Isolation
Two strategies:
1. **Catalog-level:** Each customer gets own catalog (`customer_a`, `customer_b`)
2. **Schema-level:** Shared catalog, customer-specific schema (`insurelake_config.customer_a`, `insurelake_config.customer_b`)

Recommended: **Schema-level** (simpler, lower overhead)

## 7. Validation, edge cases & versioning

### Edge Cases

**EC-1: Missing source file**
- Scenario: `source.file_format = CSV`, but file doesn't exist
- Handling: Fail fast at config load time (pre-execution validation)
- Validation: `FileSourceValidator.check_path_exists(source)`

**EC-2: Schema mismatch**
- Scenario: Source schema changed, target schema outdated
- Handling: Detect via schema evolution (Auto Loader), log warning, optionally fail
- Validation: `SchemaValidator.compare(source_schema, target_schema)`

**EC-3: Circular dependencies**
- Scenario: load_A depends on transform_B, transform_B depends on load_A
- Handling: Topological sort at runtime, fail if cycle detected
- Validation: `DependencyValidator.detect_cycles(dependency_graph)`

**EC-4: Orphaned config**
- Scenario: `load_id` references deleted `source_id`
- Handling: Soft delete (set `active_flag = false`), cascade to dependents
- Validation: `FKValidator.check_orphans()`

**EC-5: Invalid cron expression**
- Scenario: `schedule_cron = "invalid"`
- Handling: Validate at save time using cron parser
- Validation: `CronValidator.parse(schedule_cron)`

### Versioning Policy
- **Config schema versioning:** Backward-compatible changes only (add columns, never drop)
- **Config data versioning:** Immutable history (ABC audit), soft deletes
- **SDK versioning:** Semantic versioning (MAJOR.MINOR.PATCH)

### Migration Strategy
When adding new config entities or fields:
1. **Schema migration:** ALTER TABLE ADD COLUMN (nullable)
2. **Backfill:** Populate defaults for existing rows
3. **SDK update:** New Pydantic models, bump MINOR version
4. **Documentation:** Update this spec

## 8. Error handling

### Config Load Errors
```python
try:
    load_cfg = loader.get_load("load_001")
except ConfigNotFoundError as e:
    logger.error(f"Config not found: {e.load_id}")
    abc_sdk.audit(event="config_load_error", error=str(e))
    raise

except FKViolationError as e:
    logger.error(f"FK violation: {e.fk_name} -> {e.fk_value}")
    abc_sdk.audit(event="fk_violation", error=str(e))
    raise

except ValidationError as e:
    logger.error(f"Validation failed: {e.errors()}")
    abc_sdk.audit(event="validation_error", errors=e.errors())
    raise
```

### Config Update Errors
```python
try:
    update_config("load_001", changes)
except ImmutableFieldError as e:
    logger.error(f"Cannot modify immutable field: {e.field_name}")
    return {"status": "error", "message": "PK fields are immutable"}

except InvalidEnumError as e:
    logger.error(f"Invalid enum value: {e.field_name} = {e.value}")
    return {"status": "error", "message": f"Valid values: {e.valid_values}"}
```

## 9. Testing & acceptance

### Unit Tests
**UT-1: Config CRUD**
- Test: Create source, target, load; read back; update; delete
- Expected: All operations succeed, ABC audit records written

**UT-2: FK validation**
- Test: Create load with invalid source_id
- Expected: FKViolationError raised

**UT-3: Enum validation**
- Test: Create source with invalid source_type
- Expected: ValidationError raised

**UT-4: Business rules**
- Test: Create STREAM load without watermark_column
- Expected: ValidationError raised

### Integration Tests
**IT-1: End-to-end config flow**
- Setup: Create source + target + load configs
- Execute: Load data using config
- Validate: Data lands in target table

**IT-2: Config versioning**
- Setup: Create load config
- Action: Update schedule_cron
- Validate: ABC audit captures before/after

**IT-3: Dependency resolution**
- Setup: Create load_A depends on transform_B
- Execute: Run load_A
- Validate: transform_B runs first

### Acceptance Criteria
**AC-1:** All 8 config entities defined in Delta tables (5 implemented, 3 planned)
**AC-2:** Pydantic models for all entities, validated
**AC-3:** ConfigLoader reads from UC, returns typed objects
**AC-4:** FK integrity enforced (no orphans)
**AC-5:** All config changes audited via ABC
**AC-6:** 95%+ unit test coverage on config layer

## 10. Examples

### Example 1: Create Source Config
```python
source = SourceConfig(
    source_id="src_001",
    source_name="policies_salesforce",
    source_type="API",
    source_system="Salesforce",
    connection_string="https://api.salesforce.com/policies",
    file_format="JSON",
    business_domain="POLICY",
    pii_flag=True,
    data_classification="CONFIDENTIAL",
    sla_hours=4,
    active_flag=True
)
loader.save_source(source)
```

### Example 2: Create Target Config
```python
target = TargetConfig(
    target_id="tgt_001",
    target_name="policies_bronze",
    catalog_name="insurelake",
    schema_name="bronze",
    table_name="policies_raw",
    layer="BRONZE",
    table_type="MANAGED",
    format="DELTA",
    partition_columns=["ingest_date"],
    liquid_clustering_columns=["policy_number"],
    primary_key=["policy_id"],
    acord_entity="Policy",
    retention_days=365,
    enable_cdf=True,
    active_flag=True
)
loader.save_target(target)
```

### Example 3: Invalid FK Reference (Counter-Example)
```python
# BAD: Creating load with non-existent source_id
load = LoadConfig(
    load_id="load_001",
    load_name="ingest_policies",
    source_id="src_999",  # DOES NOT EXIST
    target_id="tgt_001",
    load_type="BATCH_INCREMENTAL",
    load_pattern="APPEND",
    engine="AUTOLOADER"
)

# Expected behavior:
try:
    loader.save_load(load)
except FKViolationError as e:
    print(f"FK violation: source_id 'src_999' not found")
    # Correct approach: Create source first, or use existing source_id
```

## 11. Regeneration contract

**Code generation scope:**
1. **Delta table DDL:** Generate CREATE TABLE statements for all 8 entities (§3)
2. **Pydantic models:** Generate Python classes (`SourceConfig`, `TargetConfig`, etc.)
3. **ConfigLoader:** Generate skeleton loader class with CRUD methods
4. **Validation logic:** Generate Pydantic validators for business rules (§7)

**Generation inputs:**
- This spec (markdown)
- Entity field definitions (§3)
- Validation rules (§7)

**Generation outputs:**
- `config_tables.sql` — DDL for all config tables
- `config_models.py` — Pydantic models
- `config_loader.py` — ConfigLoader class
- `config_validators.py` — Validation functions

**Regeneration rules:**
- **Safe to regenerate:** DDL, Pydantic models (schema-driven)
- **Not safe to regenerate:** Custom validation logic, business-specific transformations
- **Partial regeneration:** Update only DDL when adding new fields

## 12. References

### Dependencies
- **abc-sdk-spec.md** — Audit, Balance, Cost tracking hooks used for config versioning

### External References
- [Unity Catalog Best Practices](https://docs.databricks.com/en/data-governance/unity-catalog/best-practices.html)
- [Delta Lake Table Properties](https://docs.delta.io/latest/table-properties.html)
- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)

### Related Specs
- **metadata-models-spec.md** — Runtime state models (Feed, Job, AuditLog)
- **control-tables-ddl-spec.md** — SQL DDL for config tables
- **ingestion-engine-spec.md** — Consumes source + load configs
- **harmonization-engine-spec.md** — Consumes transform configs

---

**END OF SPEC**
