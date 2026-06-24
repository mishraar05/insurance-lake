---
id: foundation.config-storage
title: Config Storage - EAV/PARAM Architecture & ConfigLoader
owner: EY InsureLake Team
status: active
target_path: src/core/metadata/config_loader_base.py
depends_on:
  - foundation.config-types-enums
provides:
  - ConfigLoaderBase (abstract base class)
  - EAV serialization patterns (to_param_rows / from_param_rows)
  - ABC table schema definitions
  - Safe query patterns (SQL injection prevention)
  - FK resolution patterns
  - SCD2 versioning patterns
acceptance:
  - "All config entities serialize to/from PARAM rows without data loss"
  - "ConfigLoader prevents SQL injection via spark.table().filter(col == lit())"
  - "FK violations detected at load time, not runtime"
  - "SCD2 versioning preserves immutable config history"
generation_context:
  - specs/foundation/config-model/config-storage-spec.md
  - specs/foundation/config-model/config-types-enums-spec.md
regeneration: scaffold-then-edit
---

# Config Storage Specification

**Status:** Active · 2026-06-23 · Dependency: config-types-enums-spec.md

**Architecture Summary:**  
All configuration (source, target, load, transform, DQ rules) persists as **Entity-Attribute-Value (EAV) rows** in Unity Catalog ABC framework tables (\`ABC_JOB_PARAM_TBL\`, \`ABC_SRC_CTRL_TBL\`). The **ConfigLoader** base class performs validation-on-read, returning typed Pydantic models. All config changes are versioned via **SCD2** (Slowly Changing Dimension Type 2), providing immutable audit history.

---

## 1. Purpose & Scope

### Purpose
Define the storage layer that persists configuration entities in a metadata-driven framework. This spec provides:
1. **EAV storage schema** — ABC table structures for PARAM-backed config
2. **ConfigLoader base class** — Abstract interface for loading/saving typed config objects
3. **Serialization patterns** — Convert Pydantic models ↔ PARAM rows
4. **Security patterns** — Prevent SQL injection via parameterized queries
5. **FK resolution** — Validate foreign key integrity at load time
6. **SCD2 versioning** — Track config history immutably

### In Scope
* ABC table schemas (\`ABC_JOB_PARAM_TBL\`, \`ABC_SRC_CTRL_TBL\`)
* ConfigLoader abstract base class
* PARAM row serialization (to_param_rows / from_param_rows)
* Safe query patterns using \`spark.table().filter(col == lit())\`
* FK validation patterns
* SCD2 versioning patterns (EFF_STRT_DTS, EFF_END_DTS, CURR_FLG)

### Out of Scope
* Concrete config entity classes (SourceConfig, TargetConfig, etc.) — see \`source-target-spec.md\`, \`load-config-spec.md\`, \`transform-dq-spec.md\`
* Business rule validators — see \`config-validators-spec.md\`
* Runtime execution state (logs, run history) — belongs in ABC RUN tables

---

## 2. Requirements

### Functional Requirements

**FR-1: EAV Storage**  
All config persists as EAV rows in \`ABC_JOB_PARAM_TBL\` with schema:  
\`(JOB_SK, PARAM_ZONE, PARAM_NM, PARAM_VAL, EFF_STRT_DTS, EFF_END_DTS, CURR_FLG, REC_VER_NO)\`

**FR-2: Source by Reference**  
Support source definitions stored separately in \`ABC_SRC_CTRL_TBL\` (SRC_SK as FK, no duplication).

**FR-3: Validation-on-Read**  
ConfigLoader reads PARAM rows, validates via Pydantic, returns typed objects. Invalid configs raise \`ConfigValidationError\` at load time, not execution time.

**FR-4: Multi-Engine Support**  
Storage layer supports DECLARATIVE (Lakeflow SDP), AUTOLOADER (Classic Auto Loader), and STRUCTURED_STREAMING engines.

**FR-5: FK Integrity**  
ConfigLoader validates foreign key references (e.g., load.source_id → source.source_id) on load. Missing FK raises \`FKViolationError\`.

**FR-6: SCD2 Versioning**  
All config changes append new rows with incremented REC_VER_NO. Old rows marked inactive via EFF_END_DTS and CURR_FLG = False. No in-place updates.

**FR-7: Multi-Catalog Isolation**  
ConfigLoader supports multi-customer/multi-environment isolation via catalog/schema namespacing (e.g., \`customer1_insurelake_config.bronze\`).

### Non-Functional Requirements

**NFR-1: Delta Format**  
All ABC tables are Delta format in Unity Catalog.

**NFR-2: Fast Reads**  
Config reads must be <100ms. Queries filter on \`JOB_SK + CURR_FLG = True\` for indexed lookups.

**NFR-3: JSON Encoding**  
Complex values (lists, dicts) are JSON-encoded in PARAM_VAL. Serialization must be lossless.

**NFR-4: Immutable History**  
SCD2 appends only — never updates/deletes existing rows.

**NFR-5: SQL Injection Prevention**  
All queries MUST use \`spark.table().filter(col == lit(value))\`. F-string SQL is **strictly forbidden**.

---

## 3. ABC Table Schemas

### 3.1 ABC_JOB_PARAM_TBL (EAV Configuration Storage)

**Purpose:** Stores all config entities as Entity-Attribute-Value rows.

**Schema:**
\`\`\`
Table: ABC_JOB_PARAM_TBL
Catalog: {customer}_insurelake_config
Schema: config
Format: Delta

Columns:
  JOB_SK: BIGINT (Primary Key part 1 - Job Surrogate Key)
  PARAM_ZONE: STRING (Primary Key part 2 - Config entity type: 'source'|'target'|'load'|'transform'|'dq')
  PARAM_NM: STRING (Primary Key part 3 - Field name within entity)
  PARAM_VAL: STRING (Field value - JSON-encoded for complex types)
  EFF_STRT_DTS: TIMESTAMP (Effective start date - SCD2)
  EFF_END_DTS: TIMESTAMP (Effective end date - SCD2, NULL if current)
  CURR_FLG: BOOLEAN (Current flag - SCD2, TRUE for active version)
  REC_VER_NO: INTEGER (Record version number - increments on each update)
  LOAD_DTS: TIMESTAMP (Audit - when row was loaded)
  LOAD_USER: STRING (Audit - who loaded the row)

Indexes:
  - Primary: (JOB_SK, PARAM_ZONE, PARAM_NM, REC_VER_NO)
  - Current: (JOB_SK, CURR_FLG) for fast active config retrieval

Partitioning: PARTITION BY (PARAM_ZONE) for query performance
\`\`\`

**PARAM_ZONE Values:**
* \`source\` — SourceConfig fields
* \`target\` — TargetConfig fields
* \`load\` — LoadConfig fields
* \`transform\` — TransformConfig fields
* \`dq\` — DQRuleConfig fields

**Example Rows (LoadConfig for JOB_SK=1001):**
\`\`\`
JOB_SK | PARAM_ZONE | PARAM_NM          | PARAM_VAL                | CURR_FLG | REC_VER_NO
-------|------------|-------------------|--------------------------|----------|------------
1001   | load       | load_id           | LOAD_CLAIMS_BRONZE       | TRUE     | 1
1001   | load       | load_name         | Claims Ingestion         | TRUE     | 1
1001   | load       | source_id         | SRC_CLAIMS_S3            | TRUE     | 1
1001   | load       | target_id         | TGT_CLAIMS_BRONZE        | TRUE     | 1
1001   | load       | engine            | DECLARATIVE              | TRUE     | 1
1001   | load       | load_pattern      | APPEND_ONLY              | TRUE     | 1
1001   | load       | merge_keys        | ["claim_id","policy_id"] | TRUE     | 1  (JSON)
1001   | load       | zero_downtime     | true                     | TRUE     | 1
\`\`\`

### 3.2 ABC_SRC_CTRL_TBL (Source Registry)

**Purpose:** Stores source definitions separately (source by reference pattern).

**Schema:**
\`\`\`
Table: ABC_SRC_CTRL_TBL
Catalog: {customer}_insurelake_config
Schema: config
Format: Delta

Columns:
  SRC_SK: BIGINT (Primary Key - Source Surrogate Key, auto-incremented)
  SRC_ID: STRING (Unique - Business key, e.g., 'SRC_CLAIMS_S3')
  SRC_NM: STRING (Display name)
  SRC_TYPE: STRING (SourceType enum: FILE|TABLE|STREAM|API|CDC)
  SRC_LOCATION: STRING (File path, table name, or API endpoint)
  SRC_FORMAT: STRING (FileFormat enum: CSV|PARQUET|JSON|AVRO|DELTA|ORC)
  SCHEMA_REGISTRY_ID: STRING (Optional - FK to schema registry)
  EFF_STRT_DTS: TIMESTAMP (SCD2)
  EFF_END_DTS: TIMESTAMP (SCD2)
  CURR_FLG: BOOLEAN (SCD2)
  REC_VER_NO: INTEGER (SCD2)
  LOAD_DTS: TIMESTAMP (Audit)
  LOAD_USER: STRING (Audit)

Indexes:
  - Primary: SRC_SK
  - Unique: (SRC_ID, REC_VER_NO)
  - Current: (SRC_ID, CURR_FLG)
\`\`\`

**Rationale:**  
Sources are reused across multiple loads. Storing them separately (normalized) avoids duplication and enables centralized source management.


---

## 4. ConfigLoader Base Class

### 4.1 Class Responsibilities

The \`ConfigLoaderBase\` abstract class provides:
1. **Load methods** — Retrieve typed config objects by ID
2. **Save methods** — Persist config objects as PARAM rows (append-only SCD2)
3. **FK resolution** — Validate foreign key integrity on load
4. **Safe queries** — Prevent SQL injection via parameterized filters
5. **Catalog/schema namespacing** — Support multi-customer isolation

### 4.2 Interface Definition (Natural Language)

**Class:** \`ConfigLoaderBase\`

**Constructor Parameters:**
* \`spark: SparkSession\` — PySpark session for table access
* \`catalog: str\` — Unity Catalog name (e.g., \`customer1_insurelake_config\`)
* \`schema: str\` — Schema name within catalog (e.g., \`config\`)

**Abstract Methods:**

All subclasses MUST implement these methods:

1. **get_source(source_id: str) → SourceConfig**
   * Retrieve active SourceConfig by source_id
   * Queries: \`ABC_SRC_CTRL_TBL\` filtered on \`SRC_ID = source_id AND CURR_FLG = True\`
   * Raises: \`ValueError\` if not found or multiple active found
   * Raises: \`ConfigValidationError\` if PARAM rows fail Pydantic validation

2. **get_target(target_id: str) → TargetConfig**
   * Retrieve active TargetConfig by target_id
   * Queries: \`ABC_JOB_PARAM_TBL\` filtered on \`JOB_SK = {derived_from_target_id} AND PARAM_ZONE = 'target' AND CURR_FLG = True\`
   * Raises: Same as get_source

3. **get_load(load_id: str) → LoadConfig**
   * Retrieve active LoadConfig by load_id
   * Queries: \`ABC_JOB_PARAM_TBL\` (PARAM_ZONE = 'load')
   * FK validation: Calls \`get_source(load.source_id)\` and \`get_target(load.target_id)\` to verify FKs exist
   * Raises: \`FKViolationError\` if source_id or target_id not found

4. **get_transform(transform_id: str) → TransformConfig**
   * Retrieve active TransformConfig by transform_id
   * FK validation: Verifies \`source_target_id\` and \`destination_target_id\` via \`get_target()\`

5. **get_dq_rule(dq_rule_id: str) → DQRuleConfig**
   * Retrieve active DQRuleConfig by dq_rule_id
   * FK validation: Verifies \`target_id\` via \`get_target()\`

6. **save_source(config: SourceConfig) → None**
   * Validate config via Pydantic \`model_validate()\`
   * Insert new row in \`ABC_SRC_CTRL_TBL\` with incremented REC_VER_NO
   * If prior version exists, mark it inactive (EFF_END_DTS = now, CURR_FLG = False)
   * Mode: Append-only Delta write

7. **save_target(config: TargetConfig) → None**
   * Convert config to PARAM rows via \`config.to_param_rows(job_sk)\`
   * Append to \`ABC_JOB_PARAM_TBL\` (PARAM_ZONE = 'target')

8. **save_load(config: LoadConfig) → None**
   * Similar to save_target, but PARAM_ZONE = 'load'

9. **save_transform(config: TransformConfig) → None**
   * PARAM_ZONE = 'transform'

10. **save_dq_rule(config: DQRuleConfig) → None**
    * PARAM_ZONE = 'dq'

### 4.3 Safe Query Pattern (SQL Injection Prevention)

**CRITICAL SECURITY REQUIREMENT:**

All config queries MUST use the following pattern:
\`\`\`python
df = (
    self.spark.table(f"{self.catalog}.{self.schema}.table_name")
    .filter(col("field_name") == lit(user_input_value))
    .filter(col("CURR_FLG") == lit(True))
)
\`\`\`

**Rationale:**
* \`spark.table()\` + \`.filter(col == lit())\` uses Spark's SQL parser, which parameterizes values automatically
* Prevents SQL injection even when \`user_input_value\` contains malicious SQL

**FORBIDDEN Pattern:**
\`\`\`python
# ❌ NEVER DO THIS - SQL injection vulnerability
query = f"SELECT * FROM {catalog}.{schema}.table WHERE field = '{user_input}' AND CURR_FLG = True"
df = spark.sql(query)
\`\`\`

**Why Forbidden:**
If \`user_input = "' OR '1'='1"\`, the query becomes:  
\`SELECT * FROM table WHERE field = '' OR '1'='1' AND CURR_FLG = True\`  
This bypasses the filter and returns all rows (SQL injection attack).

### 4.4 FK Resolution Pattern

**Purpose:** Validate foreign key integrity at config load time (fail fast).

**Pattern:**
\`\`\`python
def get_load(self, load_id: str) -> LoadConfig:
    # 1. Load PARAM rows
    param_rows = self._load_param_rows(load_id, 'load')
    
    # 2. Parse into LoadConfig
    load_cfg = LoadConfig.from_param_rows(param_rows)
    
    # 3. Validate FK integrity (fail fast)
    try:
        self.get_source(load_cfg.source_id)  # Verify source exists
    except ValueError as e:
        raise FKViolationError(
            fk_name="source_id",
            fk_value=load_cfg.source_id
        ) from e
    
    try:
        self.get_target(load_cfg.target_id)  # Verify target exists
    except ValueError as e:
        raise FKViolationError(
            fk_name="target_id",
            fk_value=load_cfg.target_id
        ) from e
    
    return load_cfg
\`\`\`

**Benefit:**
* Detects missing FK references at load time (before any data processing)
* Provides clear error messages for troubleshooting
* Prevents cryptic runtime failures (e.g., "table not found" errors during execution)

---

## 5. PARAM Row Serialization Patterns

### 5.1 Purpose

Convert Pydantic config models ↔ EAV PARAM rows losslessly. Each config class implements:
1. \`to_param_rows(job_sk: int) → List[Dict[str, Any]]\` — Serialize to PARAM rows
2. \`from_param_rows(rows: List[Dict[str, Any]]) → ConfigClass\` — Deserialize from PARAM rows

### 5.2 Serialization Rules

**Rule 1: Null Handling**  
Null/None fields are **skipped** (no PARAM row generated). This reduces storage and simplifies queries.

**Rule 2: Simple Types**  
Primitive types (str, int, float, bool) are converted to strings:  
\`PARAM_VAL = str(field_value)\`

**Rule 3: Complex Types (Lists, Dicts)**  
JSON-encode complex types:  
\`PARAM_VAL = json.dumps(field_value)\`

**Rule 4: Enum Types**  
Store enum value (not name):  
\`PARAM_VAL = str(enum_field.value)\`

**Rule 5: Boolean Types**  
Store as lowercase string:  
\`PARAM_VAL = str(field_value).lower()\` → \`"true"\` or \`"false"\`

### 5.3 to_param_rows() Pattern

**Template Method (Natural Language):**

\`\`\`
Method: to_param_rows(job_sk: int) → List[Dict[str, Any]]

For each field in the config model:
  1. Skip if field value is None
  2. Determine PARAM_VAL:
     - If list or dict: json.dumps(field_value)
     - If enum: str(field_value.value)
     - Else: str(field_value)
  3. Create PARAM row dict:
     {
       'JOB_SK': job_sk,
       'PARAM_ZONE': <entity_type>,  # 'source', 'target', 'load', 'transform', 'dq'
       'PARAM_NM': field_name,
       'PARAM_VAL': param_val,
       'EFF_STRT_DTS': current_timestamp(),
       'EFF_END_DTS': None,
       'CURR_FLG': True,
       'REC_VER_NO': 1,  # Incremented by save method
       'LOAD_DTS': current_timestamp(),
       'LOAD_USER': current_user()
     }
  4. Append to rows list

Return: List of PARAM row dicts
\`\`\`

**Example (LoadConfig → PARAM Rows):**

\`\`\`
Input LoadConfig:
  load_id = "LOAD_CLAIMS_BRONZE"
  load_name = "Claims Ingestion"
  source_id = "SRC_CLAIMS_S3"
  target_id = "TGT_CLAIMS_BRONZE"
  engine = Engine.DECLARATIVE
  load_pattern = LoadPattern.APPEND_ONLY
  merge_keys = ["claim_id", "policy_id"]
  zero_downtime = True
  checkpoint_location = None  (skipped)

Output PARAM Rows:
  [
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'load_id', 'PARAM_VAL': 'LOAD_CLAIMS_BRONZE', ...},
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'load_name', 'PARAM_VAL': 'Claims Ingestion', ...},
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'source_id', 'PARAM_VAL': 'SRC_CLAIMS_S3', ...},
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'target_id', 'PARAM_VAL': 'TGT_CLAIMS_BRONZE', ...},
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'engine', 'PARAM_VAL': 'DECLARATIVE', ...},
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'load_pattern', 'PARAM_VAL': 'APPEND_ONLY', ...},
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'merge_keys', 'PARAM_VAL': '["claim_id","policy_id"]', ...},  (JSON)
    {'JOB_SK': 1001, 'PARAM_ZONE': 'load', 'PARAM_NM': 'zero_downtime', 'PARAM_VAL': 'true', ...},
    # checkpoint_location skipped (None)
  ]
\`\`\`

### 5.4 from_param_rows() Pattern

**Template Method (Natural Language):**

\`\`\`
Classmethod: from_param_rows(rows: List[Dict[str, Any]]) → ConfigClass

1. Initialize empty dict: data = {}
2. For each PARAM row:
   a. Verify PARAM_ZONE matches expected entity type (raise ParamParseError if mismatch)
   b. Extract PARAM_NM (field name) and PARAM_VAL (field value string)
   c. Determine target type based on field name:
      - If field is in <list_fields>: data[field] = json.loads(PARAM_VAL) if PARAM_VAL else []
      - If field is in <dict_fields>: data[field] = json.loads(PARAM_VAL) if PARAM_VAL else {}
      - If field is in <bool_fields>: data[field] = PARAM_VAL.lower() in ['true', '1', 'yes']
      - If field is in <enum_fields>: data[field] = EnumClass(PARAM_VAL)  # Pydantic auto-converts
      - Else: data[field] = PARAM_VAL (string, int, float auto-coerced by Pydantic)
3. Instantiate config class: return ConfigClass(**data)
4. Pydantic validates all fields and raises ConfigValidationError if invalid
\`\`\`

**Field Type Mappings (Per Entity):**

**LoadConfig:**
* List fields: \`merge_keys\`, \`depends_on\`, \`partition_columns\`
* Dict fields: \`autoloader_options\`, \`checkpoint_options\`
* Bool fields: \`zero_downtime\`, \`paranoid\`, \`renames_expected\`, \`active_flag\`
* Enum fields: \`engine\`, \`load_pattern\`, \`load_type\`

**TransformConfig:**
* List fields: \`scd_key_columns\`, \`dependencies\`
* Bool fields: \`active_flag\`
* Enum fields: \`transform_type\`, \`scd_type\`, \`engine\`

**DQRuleConfig:**
* Bool fields: \`active_flag\`
* Enum fields: \`rule_type\`, \`on_failure\`

### 5.5 Lossless Guarantees

**Guarantee 1: Round-Trip Integrity**  
For any config object \`c\`:  
\`ConfigClass.from_param_rows(c.to_param_rows(job_sk)) == c\`

**Guarantee 2: Type Preservation**  
All types (int, float, bool, list, dict, enum) are preserved through serialization/deserialization.

**Guarantee 3: Validation on Deserialization**  
Pydantic validators run during \`from_param_rows()\`, catching malformed PARAM data before it reaches business logic.

---

## 6. SCD2 Versioning Patterns

### 6.1 Purpose

Preserve immutable audit history of all config changes via Slowly Changing Dimension Type 2 (SCD2).

### 6.2 SCD2 Fields

**EFF_STRT_DTS (Effective Start Date)**  
Timestamp when this version became active.

**EFF_END_DTS (Effective End Date)**  
Timestamp when this version was superseded (NULL if current).

**CURR_FLG (Current Flag)**  
Boolean indicating active version (TRUE for current, FALSE for historical).

**REC_VER_NO (Record Version Number)**  
Integer version counter (1, 2, 3, ...). Increments on each update.

### 6.3 Insert Pattern (New Config)

**Scenario:** User creates a new LoadConfig.

**Steps:**
1. Generate PARAM rows via \`config.to_param_rows(job_sk)\`
2. Set SCD2 fields:
   * \`EFF_STRT_DTS = current_timestamp()\`
   * \`EFF_END_DTS = NULL\`
   * \`CURR_FLG = True\`
   * \`REC_VER_NO = 1\`
3. Append rows to \`ABC_JOB_PARAM_TBL\` (Delta append mode)

**Result:**  
New config version 1 is active.

### 6.4 Update Pattern (Config Change)

**Scenario:** User modifies an existing LoadConfig (e.g., changes \`merge_keys\`).

**Steps:**
1. Query current version (CURR_FLG = True)
2. Mark current version inactive:
   * \`UPDATE ABC_JOB_PARAM_TBL SET EFF_END_DTS = current_timestamp(), CURR_FLG = False WHERE JOB_SK = X AND PARAM_ZONE = 'load' AND CURR_FLG = True\`
3. Generate new PARAM rows for updated config
4. Set SCD2 fields for new version:
   * \`EFF_STRT_DTS = current_timestamp()\`
   * \`EFF_END_DTS = NULL\`
   * \`CURR_FLG = True\`
   * \`REC_VER_NO = <previous_version> + 1\`
5. Append new rows (Delta append mode)

**Result:**  
Old version preserved with EFF_END_DTS set. New version active.

### 6.5 Query Patterns

**Get Current Version:**
\`\`\`python
df = (
    spark.table(f"{catalog}.{schema}.ABC_JOB_PARAM_TBL")
    .filter(col("JOB_SK") == lit(job_sk))
    .filter(col("PARAM_ZONE") == lit("load"))
    .filter(col("CURR_FLG") == lit(True))  # Only active version
)
\`\`\`

**Get Historical Version (As-Of Date):**
\`\`\`python
df = (
    spark.table(f"{catalog}.{schema}.ABC_JOB_PARAM_TBL")
    .filter(col("JOB_SK") == lit(job_sk))
    .filter(col("PARAM_ZONE") == lit("load"))
    .filter(
        (col("EFF_STRT_DTS") <= lit(as_of_date)) &
        ((col("EFF_END_DTS") > lit(as_of_date)) | col("EFF_END_DTS").isNull())
    )
)
\`\`\`

**Get Version by REC_VER_NO:**
\`\`\`python
df = (
    spark.table(f"{catalog}.{schema}.ABC_JOB_PARAM_TBL")
    .filter(col("JOB_SK") == lit(job_sk))
    .filter(col("PARAM_ZONE") == lit("load"))
    .filter(col("REC_VER_NO") == lit(version_num))
)
\`\`\`

### 6.6 Immutability Enforcement

**Rule:** NEVER update or delete existing PARAM rows.

**Enforcement:**
* All save methods use Delta append mode (\`mode="append"\`)
* No DELETE or UPDATE SQL is allowed in ConfigLoader
* Audit fields (LOAD_DTS, LOAD_USER) are write-once

**Rationale:**
* Provides complete audit trail ("who changed what, when")
* Enables rollback (reactivate old version by setting CURR_FLG = True)
* Supports compliance requirements (GDPR, SOX, etc.)


---

## 7. Common Guardrails & Best Practices

**All implementation MUST follow the common guardrails defined in \`config-types-enums-spec.md\`, including:**

### 7.1 SOLID Principles

**Single Responsibility Principle (SRP):**
* ConfigLoader focuses solely on persistence layer
* Validation logic belongs in Pydantic validators (not ConfigLoader)
* Business rules belong in config entity classes (not ConfigLoader)

**Open/Closed Principle (OCP):**
* ConfigLoaderBase is abstract — extend for different backends (Unity Catalog, REST API, mock)
* New config entity types (e.g., \`AlertConfig\`) extend without modifying ConfigLoader interface

**Liskov Substitution Principle (LSP):**
* Any ConfigLoader subclass can replace ConfigLoaderBase without breaking clients
* Example: \`UCConfigLoader\`, \`MockConfigLoader\`, \`RESTConfigLoader\` all interchangeable

**Interface Segregation Principle (ISP):**
* ConfigLoader provides focused methods per entity type (get_source, get_target, etc.)
* Clients depend only on methods they use (no "fat" interface)

**Dependency Inversion Principle (DIP):**
* High-level modules (ingestion engine) depend on ConfigLoader abstraction
* Low-level modules (UCConfigLoader) implement abstraction
* Example:
  \`\`\`python
  class IngestionEngine:
      def __init__(self, config_loader: ConfigLoaderBase):  # DIP - depend on abstraction
          self.loader = config_loader
  \`\`\`

### 7.2 Design Patterns

**Repository Pattern:**
* ConfigLoader abstracts persistence mechanism (Delta tables, REST API, etc.)
* Clients access configs via clean interface without knowing storage details

**Factory Pattern (Implicit):**
* \`from_param_rows()\` is a factory method creating config objects from raw data

**Template Method Pattern:**
* \`to_param_rows()\` and \`from_param_rows()\` are template methods with consistent structure across all config types

**Strategy Pattern (Extensibility):**
* Different ConfigLoader implementations (UC, REST, Mock) are strategies for config persistence

### 7.3 Code Quality Standards

**PEP8 Compliance:**
* 4 spaces indentation (never tabs)
* Max line length: 88 characters (Black formatter compatible)
* Snake_case for functions/variables: \`get_load_config()\`, \`param_rows\`
* PascalCase for classes: \`ConfigLoaderBase\`, \`LoadConfig\`
* UPPER_CASE for constants: \`MAX_RETRIES\`, \`DEFAULT_CATALOG\`
* Two blank lines between top-level classes/functions
* One blank line between methods

**Google Docstring Style:**
* All public methods MUST have docstrings
* Format:
  \`\`\`python
  def get_load(self, load_id: str) -> LoadConfig:
      """Retrieve active LoadConfig by ID with FK validation.
      
      Args:
          load_id: Unique identifier for the load configuration.
      
      Returns:
          Validated LoadConfig instance.
      
      Raises:
          ValueError: If load_id not found or multiple active versions exist.
          FKViolationError: If source_id or target_id references are invalid.
          ConfigValidationError: If PARAM rows fail Pydantic validation.
      """
  \`\`\`

**Type Hints:**
* All method signatures MUST include type hints
* Use \`Optional[T]\` for nullable fields
* Use \`List[T]\`, \`Dict[K, V]\` for collections (not \`list\`, \`dict\`)

**Error Handling:**
* Fail fast — validate at load time, not execution time
* Provide clear error messages with context (entity ID, field name, violating value)
* Use custom exceptions (\`ConfigValidationError\`, \`FKViolationError\`, \`ParamParseError\`) for domain errors

### 7.4 Forbidden Patterns

**❌ F-String SQL (SQL Injection Risk):**
\`\`\`python
# FORBIDDEN
query = f"SELECT * FROM table WHERE id = '{user_input}'"
df = spark.sql(query)
\`\`\`

**❌ In-Place Updates (Violates SCD2):**
\`\`\`python
# FORBIDDEN
spark.sql(f"UPDATE ABC_JOB_PARAM_TBL SET PARAM_VAL = '{new_value}' WHERE PARAM_NM = 'load_name'")
\`\`\`

**❌ Deletes (Violates Immutability):**
\`\`\`python
# FORBIDDEN
spark.sql(f"DELETE FROM ABC_JOB_PARAM_TBL WHERE JOB_SK = {job_sk}")
\`\`\`

**❌ Bare Except Clauses:**
\`\`\`python
# FORBIDDEN
try:
    config = self.get_load(load_id)
except:  # Too broad - catches KeyboardInterrupt, SystemExit, etc.
    pass
\`\`\`

**❌ Mutable Default Arguments:**
\`\`\`python
# FORBIDDEN
def load_configs(config_ids: list = []):  # Mutable default creates shared state bug
    ...

# CORRECT
def load_configs(config_ids: Optional[List[str]] = None):
    if config_ids is None:
        config_ids = []
\`\`\`

---

## 8. Test Criteria

### 8.1 Unit Tests (ConfigLoader)

**Test Suite:** \`tests/unit/test_config_loader.py\`

**Coverage Requirements:**
* All ConfigLoader methods (get_*, save_*)
* PARAM row serialization (to_param_rows, from_param_rows)
* FK validation logic
* Error handling (ValueError, FKViolationError, ConfigValidationError)

**Test Cases:**

**TC-1: get_load() Success**
* Given: Valid load_id with existing PARAM rows
* When: Call \`loader.get_load(load_id)\`
* Then: Returns LoadConfig instance with correct field values
* Assert: FK validation called for source_id and target_id

**TC-2: get_load() Not Found**
* Given: load_id with no PARAM rows
* When: Call \`loader.get_load(load_id)\`
* Then: Raises ValueError with message "Load not found: {load_id}"

**TC-3: get_load() FK Violation**
* Given: load_id with valid PARAM rows but invalid source_id
* When: Call \`loader.get_load(load_id)\`
* Then: Raises FKViolationError with fk_name="source_id"

**TC-4: to_param_rows() Round-Trip**
* Given: LoadConfig instance with all fields populated
* When: Call \`config.to_param_rows(job_sk)\` then \`LoadConfig.from_param_rows(rows)\`
* Then: Resulting config equals original (lossless)

**TC-5: to_param_rows() Null Handling**
* Given: LoadConfig with \`checkpoint_location = None\`
* When: Call \`config.to_param_rows(job_sk)\`
* Then: No PARAM row generated for checkpoint_location

**TC-6: from_param_rows() JSON Decoding**
* Given: PARAM row with \`PARAM_NM = 'merge_keys'\` and \`PARAM_VAL = '["id","date"]'\`
* When: Call \`LoadConfig.from_param_rows(rows)\`
* Then: \`config.merge_keys == ["id", "date"]\` (list, not string)

**TC-7: SQL Injection Prevention**
* Given: load_id = \`"' OR '1'='1"\`
* When: Call \`loader.get_load(load_id)\`
* Then: Returns empty result (not all rows) — injection attempt fails

**TC-8: SCD2 Versioning**
* Given: Existing LoadConfig (REC_VER_NO = 1)
* When: Save modified LoadConfig
* Then: Old version has CURR_FLG = False, new version has REC_VER_NO = 2 and CURR_FLG = True

### 8.2 Integration Tests (ConfigLoader + Delta Tables)

**Test Suite:** \`tests/integration/test_config_storage.py\`

**TC-9: End-to-End Load/Save**
* Given: Fresh Unity Catalog test schema
* When: Save LoadConfig → Read back via get_load()
* Then: Read config matches saved config (all fields)

**TC-10: Multi-Version History**
* Given: LoadConfig saved 3 times with changes
* When: Query historical versions (REC_VER_NO = 1, 2, 3)
* Then: Each version has correct field values per change

**TC-11: FK Cascade**
* Given: SourceConfig, TargetConfig, LoadConfig (FK relationships)
* When: Save all three → Read LoadConfig
* Then: FK validation succeeds, LoadConfig loads correctly

**TC-12: Concurrent Writes**
* Given: Two threads saving same LoadConfig simultaneously
* When: Both call \`save_load(config)\`
* Then: Both succeed (Delta handles concurrency), REC_VER_NO increments correctly

---

## 9. Acceptance Criteria

**AC-1: EAV Storage Operational**
* All config entities serialize to PARAM rows losslessly
* Complex types (lists, dicts) JSON-encoded/decoded correctly
* SCD2 versioning preserves immutable history

**AC-2: ConfigLoader Prevents SQL Injection**
* All queries use \`spark.table().filter(col == lit())\` pattern
* Malicious input (e.g., \`' OR '1'='1\`) does not bypass filters
* Code review confirms no f-string SQL in ConfigLoader methods

**AC-3: FK Validation Fail-Fast**
* Invalid FK references raise FKViolationError at load time
* Error messages include FK name and violating value
* No runtime failures due to missing FKs

**AC-4: SCD2 Audit Trail**
* Config changes create new versions (not in-place updates)
* Historical versions queryable by date or REC_VER_NO
* CURR_FLG correctly identifies active version

**AC-5: Performance Requirements Met**
* Config load time <100ms (filter on JOB_SK + CURR_FLG index)
* Delta table partitioning by PARAM_ZONE improves query performance

**AC-6: Follows Common Guardrails**
* Implements SOLID principles (DIP, SRP, OCP, LSP, ISP)
* Uses Repository pattern for ConfigLoader
* PEP8 compliant (verified via \`flake8\`)
* Google docstrings on all public methods
* Type hints on all method signatures

---

## 10. Dependencies & References

**Depends On:**
* \`config-types-enums-spec.md\` — Shared enums, exceptions, common guardrails

**Depended On By:**
* \`source-target-spec.md\` — SourceConfig, TargetConfig entities use ConfigLoader
* \`load-config-spec.md\` — LoadConfig uses ConfigLoader
* \`transform-dq-spec.md\` — TransformConfig, DQRuleConfig use ConfigLoader
* \`config-validators-spec.md\` — Validators call ConfigLoader for FK checks

**External Dependencies:**
* PySpark (spark.table, DataFrame API)
* Unity Catalog (Delta tables)
* Pydantic (model validation)

---

## 11. Revision History

| Version | Date       | Author            | Changes                                      |
|---------|------------|-------------------|----------------------------------------------|
| 1.0     | 2026-06-23 | EY InsureLake Team | Initial spec — EAV storage, ConfigLoader base |

---

**END OF CONFIG-STORAGE-SPEC.MD**
