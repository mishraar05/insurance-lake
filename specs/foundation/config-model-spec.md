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

## 3. Entities (8)

Implemented in the SDK today: **source, target, load, transform, dq_rule**. Planned (FND-001 design, not yet built): **recon_rule, masking_rule, dependency**.

### source  (cfg_source)
Describes a feed's origin. PK `source_id`.
Fields: source_id, source_name, source_type (FILE|TABLE|STREAM|API|CDC), source_system (PolicyCenter, ClaimCenter, ...), connection_string, file_format (CSV|JSON|PARQUET|AVRO|XML|DELTA|FIXEDWIDTH), schema_location, credential_scope, credential_key, business_domain (POLICY|CLAIM|BILLING|PARTY|PAYMENT|LOSS), pii_flag, data_classification (PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED), sla_hours, active_flag, + audit (created_by/ts, updated_by/ts).

### target  (cfg_target)
Describes a destination table. PK `target_id`.
Fields: target_id, target_name, catalog_name, schema_name, table_name, layer (BRONZE|SILVER|GOLD), table_type (MANAGED|EXTERNAL), format (DELTA), partition_columns[], liquid_clustering_columns[], primary_key[], acord_entity (Party|Policy|Coverage|Claim|Payment|Loss), retention_days, enable_cdf, active_flag, + audit.

### load  (cfg_load)
Source -> bronze loading rule. PK `load_id`; FK source_id -> cfg_source, target_id -> cfg_target.
Fields: load_id, load_name, source_id, target_id, load_type (BATCH_FULL|BATCH_INCREMENTAL|STREAM_APPEND|STREAM_CDC|STREAM_UPSERT), load_pattern (APPEND|OVERWRITE|MERGE|SCD2|CDC), engine (DECLARATIVE|AUTOLOADER|COPY_INTO|STRUCTURED_STREAMING), watermark_column, watermark_type (TIMESTAMP|SEQUENCE|FILENAME), checkpoint_location, trigger_interval, merge_keys, autoloader_options{}, schedule_cron, depends_on, active_flag, + audit.

### transform  (cfg_transform)
Bronze->silver->gold transformation rule. PK `transform_id`; FK source_target_id / destination_target_id -> cfg_target.
Fields: transform_id, transform_name, source_target_id, destination_target_id, transform_type (SQL|PYTHON|ACORD_MAPPING|LOOKUP|AGGREGATION|PIVOT), transform_sql, transform_python, acord_mapping_template, scd_type (SCD1|SCD2), scd_key_columns, scd_timestamp_column, engine (DECLARATIVE|STRUCTURED_STREAMING|BATCH), dependencies, active_flag, + audit.

### dq_rule  (cfg_dq_rule)
Data-quality rule bound to a target. PK `dq_rule_id`; FK target_id -> cfg_target.
Fields: dq_rule_id, rule_name, target_id, rule_type (NOT_NULL|UNIQUE|RANGE|REGEX|CUSTOM_SQL|REFERENTIAL_INTEGRITY|FRESHNESS), column_name, rule_expression, threshold_percent (0-1), on_failure (WARN|FAIL|QUARANTINE), active_flag, + audit.

### recon_rule  (cfg_recon_rule) - PLANNED
Reconciliation check. PK `recon_rule_id`.
Fields: recon_rule_id, rule_name, load_id, target_id, recon_type (ROW_COUNT|CONTROL_TOTAL|CROSS_LAYER|SOURCE_OF_RECORD), source_ref, target_ref, measure_column (for control totals), tolerance_percent, on_break (WARN|FAIL), active_flag, + audit.

### masking_rule  (cfg_masking_rule) - PLANNED
PII handling. PK `masking_rule_id`; FK target_id.
Fields: masking_rule_id, rule_name, target_id, column_name, classification (CONFIDENTIAL|RESTRICTED), technique (UC_COLUMN_MASK|ROW_FILTER|TOKENIZE|HASH), mask_function, reversible_flag, active_flag, + audit.

### dependency  (cfg_dependency) - PLANNED
Normalized DAG edges. PK `dependency_id`.
Fields: dependency_id, object_type (LOAD|TRANSFORM), object_id, depends_on_id, dependency_type, active_flag, + audit.

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

### SOLID Principles Application (REQUIRED for all components)

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

### Design Patterns (use where applicable)

**Recommended patterns for this component:**

1. **Repository Pattern**
   - Why: Decouple config storage (Delta) from business logic (engines)
   - Benefit: Swap storage backend without touching engines
   - Example:
     ```python
     class ConfigRepository(ABC):
         @abstractmethod
         def get_source(self, source_id: str) -> SourceConfig: ...
     
     class UCConfigRepository(ConfigRepository):
         def get_source(self, source_id: str) -> SourceConfig:
             df = spark.read.table("cfg_source").filter(f"source_id = '{source_id}'")
             return SourceConfig(**df.first().asDict())
     ```

2. **Builder Pattern**
   - Why: Complex config objects with many optional fields
   - Benefit: Fluent API for config creation
   - Example:
     ```python
     source = SourceConfigBuilder() \
         .with_name("PolicyCenter_Policy") \
         .with_type("FILE") \
         .with_format("CSV") \
         .with_classification("CONFIDENTIAL") \
         .build()
     ```

3. **Factory Pattern**
   - Why: Create config objects from different sources (UC tables, YAML, API)
   - Benefit: Centralized config instantiation logic
   - Example:
     ```python
     class ConfigFactory:
         @staticmethod
         def from_table(load_id: str) -> LoadConfig:
             # Read from UC table
         
         @staticmethod
         def from_yaml(path: str) -> LoadConfig:
             # Read from YAML file
     ```

4. **Value Object Pattern**
   - Why: Config entities are immutable, identity-based
   - Benefit: Thread-safe, hashable, equality by value
   - Example:
     ```python
     @dataclass(frozen=True)  # Immutable
     class SourceConfig:
         source_id: str
         source_name: str
         source_type: str
         # No setters; create new instance to "change"
     ```

**Extensibility considerations:**
- **Multi-customer:** Add `customer_id` column to all entities; filter queries by customer context
- **New config types:** Add new entity table + new Pydantic class (e.g., `AlertRuleConfig`)
- **Config versioning:** ABC audit framework tracks all changes; engines can query "config as-of timestamp"
- **Schema evolution:** Delta table schema changes (ADD COLUMN) backward-compatible via Pydantic defaults

## 6. Implementation logic & guidance

**Logic / algorithm:**
1. **Config DDL:** Create 8 Delta tables in `insurelake_config.config` schema (see section 3)
2. **Pydantic models:** Define typed classes (`SourceConfig`, `TargetConfig`, etc.) matching table schemas
3. **ConfigLoader:** Utility class reads from UC tables, returns typed config objects
4. **Validation layer:** Pydantic validators enforce business rules (see validation rules below)

**Path:** UC tables at `insurelake_config.config.cfg_{source,target,load,transform,dq_rule,recon_rule,masking_rule,dependency}`

**Constraints (hard):**
- All tables are Delta format
- All changes audited via ABC framework (who, when, before/after)
- No direct table modifications (use config loader API)
- **Follow SOLID principles (see section 5):**
  - SRP: One entity per concern (source, target, load, transform, dq_rule)
  - OCP: Extend via new entities, not schema changes
  - LSP: Config types substitutable (any source_type works where source expected)
  - ISP: Segregated entities (engines read only what they need)
  - DIP: Engines depend on ConfigLoader abstraction, not raw Delta tables

## 7. Validation, edge cases & versioning policy

**Key validation rules (enforced by the loader):**
- FILE sources require file_format and connection_string.
- PII sources (pii_flag) require CONFIDENTIAL or RESTRICTED classification.
- partition_columns and liquid_clustering_columns are mutually exclusive.
- STREAM loads require checkpoint_location.
- DECLARATIVE engine requires APPEND or SCD2 pattern.
- MERGE / SCD2 / CDC patterns require merge_keys.
- transform source_target_id != destination_target_id (no self-transform).
- SCD2 + DECLARATIVE requires key columns and a timestamp.
- dq threshold_percent in [0,1]; on_failure in {WARN, FAIL, QUARANTINE}.
- non-CUSTOM_SQL dq rules require column_name.
- All FKs validated on load (ForeignKeyError); dependency graphs checked for cycles (CircularDependencyError).

**Versioning & change audit (FND-005):**
Every insert/update/delete to a config table writes a change record (who, when, before/after) to ABC. Config is versioned so a run can be reproduced against the config as-of a point in time.

**Edge cases:**
- **Circular dependencies:** Dependency graph validation rejects cycles
- **Missing FKs:** Load fails with clear error (source_id not found in cfg_source)
- **Schema drift:** Delta tables support ADD COLUMN (backward-compatible via Pydantic defaults)

## 8. Error handling

**Validation errors:**
- `ConfigValidationError`: Business rule violation (e.g., PII without classification)
- `ForeignKeyError`: FK constraint violated (e.g., load.source_id not in cfg_source)
- `CircularDependencyError`: Dependency cycle detected

**Handling:**
- Config loader validates on read; raises typed exceptions
- Engines catch exceptions, log structured error, fail fast
- ABC audit logs all validation failures

## 9. Testing & acceptance

### Acceptance Criteria
- [ ] All 8 entity tables created in `insurelake_config.config` schema
- [ ] Pydantic models defined for all entities
- [ ] ConfigLoader reads from UC tables and returns typed objects
- [ ] Validation rules enforced (FK checks, business rules)
- [ ] ABC audit integration working (who, when, before/after)
- [ ] **SOLID compliance verified:**
  - [ ] SRP: Each entity has single concern (manual review)
  - [ ] OCP: New config types added as new entities, not schema changes (manual review)
  - [ ] LSP: Config types substitutable (test polymorphism)
  - [ ] ISP: Engines read segregated entities (no fat config table)
  - [ ] DIP: Engines depend on ConfigLoader abstraction (test mock injection)

### Testing SOLID compliance

**SRP (Single Responsibility) Tests:**
```python
def test_entity_separation():
    # Each entity has ONE concern
    source = config_loader.get_source("SRC001")
    assert "load_pattern" not in source  # Load pattern is in cfg_load, not cfg_source
    assert "dq_rule_type" not in source  # DQ rules are in cfg_dq_rule, not cfg_source
```

**OCP (Open/Closed) Tests:**
```python
def test_new_source_type_extension():
    # Adding new source_type doesn't break existing code
    new_source = SourceConfig(
        source_id="SRC999",
        source_name="NewAPI",
        source_type="GRAPHQL",  # New type!
        # ... other fields
    )
    # Existing engines still work (OCP)
    engine = IngestionEngine(config_loader)
    engine.run(load_id="LOAD001")  # No changes needed
```

**LSP (Liskov Substitution) Tests:**
```python
def test_source_type_substitutability():
    # Any source_type can be used where source expected
    sources = [
        config_loader.get_source("FILE_SOURCE"),
        config_loader.get_source("TABLE_SOURCE"),
        config_loader.get_source("API_SOURCE"),
    ]
    for source in sources:
        # Same interface, different types
        assert hasattr(source, "source_name")
        assert hasattr(source, "source_type")
        # All work with engine (substitutable)
        reader = ReaderFactory.create(source)
        df = reader.read()
```

**ISP (Interface Segregation) Tests:**
```python
def test_engine_reads_only_needed_config():
    # Ingestion engine reads source + load, NOT transform or dq
    class MockConfigLoader:
        def get_source(self, source_id): return SourceConfig(...)
        def get_load(self, load_id): return LoadConfig(...)
        # No get_transform, get_dq_rule methods
    
    engine = IngestionEngine(MockConfigLoader())
    engine.run(load_id="LOAD001")  # Works without transform/dq config
```

**DIP (Dependency Inversion) Tests:**
```python
def test_engine_depends_on_abstraction():
    # Engine accepts ConfigLoader abstraction, not concrete UC implementation
    class MockConfigLoader(ConfigLoader):
        def get_source(self, source_id):
            return SourceConfig(source_id=source_id, source_name="Mock", ...)
    
    mock_loader = MockConfigLoader()
    engine = IngestionEngine(config_loader=mock_loader)  # DIP - abstraction
    result = engine.run(load_id="LOAD001")
    assert result.status == "SUCCESS"
```

## 10. Examples

**Conformant config loading:**
```python
# Repository pattern + DIP
loader = UCConfigRepository(spark)
load_cfg = loader.get_load("LOAD001")
source_cfg = loader.get_source(load_cfg.source_id)
target_cfg = loader.get_target(load_cfg.target_id)

# Engine depends on abstraction (ConfigRepository), not UC tables
engine = IngestionEngine(config_repository=loader)
result = engine.run(load_id="LOAD001")
```

**Builder pattern for config creation:**
```python
source = SourceConfigBuilder() \
    .with_id("SRC001") \
    .with_name("PolicyCenter_Policy") \
    .with_type("FILE") \
    .with_format("CSV") \
    .with_classification("CONFIDENTIAL") \
    .with_pii_flag(True) \
    .build()
```

### SOLID Example: Good vs. Bad

**❌ BAD (Violates SOLID):**
```python
# Violates ISP - fat config table
CREATE TABLE cfg_everything (
    source_id STRING,
    source_name STRING,
    source_type STRING,
    target_id STRING,
    target_name STRING,
    layer STRING,
    load_pattern STRING,
    engine STRING,
    dq_rule_type STRING,
    dq_threshold FLOAT,
    transform_sql STRING,
    masking_technique STRING
    -- 50+ columns mixing all concerns!
);

# Problem 1: Every engine reads massive table with unused columns
class IngestionEngine:
    def run(self, config_id):
        # Must read ALL columns even though only need source + target + load
        cfg = spark.read.table("cfg_everything").filter(f"id = '{config_id}'").first()
        # Violates ISP - forced to see transform_sql, dq_rule_type, masking_technique

# Problem 2: Violates SRP - one table, many reasons to change
# Adding a new DQ rule type touches the same table as adding a new source type

# Problem 3: Violates DIP - engine tightly coupled to cfg_everything schema
class IngestionEngine:
    def run(self, config_id):
        cfg = spark.read.table("cfg_everything")  # Hard-coded table name!
        # Can't swap config storage (e.g., REST API, YAML files)
```

**✅ GOOD (Follows SOLID):**
```python
# Follows ISP - segregated entities
CREATE TABLE cfg_source (...);  # Source concerns only
CREATE TABLE cfg_target (...);  # Target concerns only
CREATE TABLE cfg_load (...);    # Load concerns only
CREATE TABLE cfg_dq_rule (...); # DQ concerns only

# Follows SRP - each entity has ONE reason to change
# Adding new DQ rule type: only cfg_dq_rule changes
# Adding new source type: only cfg_source changes

# Follows DIP - engine depends on abstraction (ConfigRepository)
class ConfigRepository(ABC):
    @abstractmethod
    def get_source(self, source_id: str) -> SourceConfig: ...
    @abstractmethod
    def get_load(self, load_id: str) -> LoadConfig: ...

class UCConfigRepository(ConfigRepository):
    def get_source(self, source_id: str) -> SourceConfig:
        df = spark.read.table("insurelake_config.config.cfg_source")
        return SourceConfig(**df.filter(f"source_id = '{source_id}'").first().asDict())

# Engine depends on abstraction
class IngestionEngine:
    def __init__(self, config_repo: ConfigRepository):  # DIP - abstraction
        self._repo = config_repo
    
    def run(self, load_id: str):
        load_cfg = self._repo.get_load(load_id)
        source_cfg = self._repo.get_source(load_cfg.source_id)
        # Engine doesn't know config comes from UC tables

# Usage - can inject different implementations
prod_engine = IngestionEngine(config_repo=UCConfigRepository(spark))
test_engine = IngestionEngine(config_repo=MockConfigRepository())
```

**Key Differences:**
* **BAD:** Fat config table, all concerns mixed, tight coupling to UC tables
* **GOOD:** Segregated entities, single responsibility, abstraction via repository

**Benefits of GOOD approach:**
1. **Testability:** Inject mock config repository for unit tests
2. **Flexibility:** Swap config storage (UC → REST API) without changing engines
3. **Maintainability:** Changes to DQ rules don't affect source/target/load schemas
4. **Performance:** Engines read only needed tables (source + load for ingestion, not transform/dq)

## 11. Regeneration contract
`regeneration: scaffold-then-edit`. DDL scripts are generated from this spec, but config data (INSERT statements) is hand-maintained. UC tables are ONE-TIME created; schema evolution via ALTER TABLE ADD COLUMN.

## 12. References
- `foundation/contracts-spec.md` — Config entities consumed via `SourceConfig`, `TargetConfig`, etc.
- `foundation/abc-sdk-spec.md` — All config changes audited via ABC framework
- `../../skills/_shared/standards.md` — Repository pattern, validation, error handling

---

**SOLID Compliance:** ✅ Updated 2026-06-18 - Comprehensive SOLID principles documented for config model design.
