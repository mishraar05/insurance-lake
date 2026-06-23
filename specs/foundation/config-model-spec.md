---
id: core.metadata
title: Metadata / Config Model (ABC Control plane)
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
depends_on: []
generation_context:
  - specs/foundation/config-model-spec.md
  - docs/ABC-MAPPING.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/core/metadata/test_config_model.py"
  - "pytest tests/core/metadata/test_config_loader.py"
  - "python -c 'from core.metadata import ConfigLoader, SourceConfig, TargetConfig, LoadConfig, TransformConfig, DQRuleConfig'"
  - "ruff check src/core/metadata/ tests/core/metadata/    # PEP 8 + import order + naming + Google docstrings"
  - "black --check src/core/metadata/ tests/core/metadata/ # formatting (line length 88)"
regeneration: scaffold-then-edit
capability:
  framework: control
  feature: config-model
  selectable: false
---

# Metadata / Config Model - Specification (ABC Control plane)

Status: active - the **Control** pillar of the ABC framework (Audit / Balance / **Control**). The typed config-model is the Control plane: engines read *only* typed config objects, never raw tables. Storage + decisions: `docs/ABC-MAPPING.md`.

## 1. Purpose & scope
Define the typed configuration entities that drive the metadata-driven framework, and the read-only loader that **hydrates and validates them from the ABC Control tables**. Behaviour is config, not code: the ingestion/harmonization engines and cross-cutting services consume the typed objects this spec returns.

- **In scope:** the typed models (`SourceConfig`, `TargetConfig`, `LoadConfig`, `TransformConfig`, `DQRuleConfig`) + their enums + cross-field validators; `ConfigLoader`, which reads the ABC Control tables (`ABC_JOB_CTRL_TBL`, `ABC_JOB_PARAM_TBL`, `ABC_SRC_CTRL_TBL`), decodes the EAV/PARAM rows, resolves source **by reference**, and returns validated typed objects (validation-on-read).
- **Storage model (locked):** config is stored as **zoned EAV rows** in `ABC_JOB_PARAM_TBL` (`PARAM_ZONE` / `PARAM_NM` / `PARAM_VAL`, SCD2). Complex values (lists, option dicts) are **JSON-encoded** in `PARAM_VAL`; scalars are plain strings. The typed Pydantic models are the **validation + hydration layer** over that storage - engines stay typed and unchanged.
- **Out of scope:** writing/authoring config (the loader is **read-only**; CTRL+PARAM rows are authored by a separate config process / migration / UI and versioned SCD2 there); the RUN / Audit tables and the Cycle/Step/Job state machine (those belong to `abc-sdk-spec`); the table DDL (owned by the ABC framework, names verbatim from the doc).

## 2. Requirements
**Functional**
- FR-1: Define the typed models `SourceConfig`, `TargetConfig`, `LoadConfig`, `TransformConfig`, `DQRuleConfig` with explicit enums (section 3) - no stringly-typed public fields.
- FR-2: `ConfigLoader` is **read-only**. `get_*` methods read the active (`CURR_FLG = true`) rows from the ABC Control tables, decode the PARAM EAV rows (JSON for complex values), and return a validated typed object.
- FR-3: **Source by reference** - a job's PARAM carries a `SRC_SK` pointer; `get_source(src_sk)` resolves the reusable source from `ABC_SRC_CTRL_TBL`. Source config is never duplicated per job.
- FR-4: **Validation-on-read** - construction validates enums and cross-field business rules (STREAM -> watermark, SCD2 -> merge_keys, DECLARATIVE -> checkpoint). Invalid config raises, it never returns a half-valid object.
- FR-5: One config-model `load` corresponds to one `ABC_JOB_CTRL_TBL` row + its `ABC_JOB_PARAM_TBL` rows; the typed `LoadConfig` is assembled from the `load`/`target`/`source` PARAM zones.
- FR-6: The schema-evolution policy fields on `LoadConfig`/`TargetConfig` (consumed by `ingestion.engine._build_resolution_context` -> `ResolutionContext`) are preserved.

**Non-functional**
- NFR-1: Storage is Delta in Unity Catalog now; **Lakebase (Postgres) is a future option** for the SCD2 Control plane (point reads + in-place SCD2). The loader must not assume the physical store beyond a Spark-readable table.
- NFR-2: Config reads fast (<100ms) for a single job (filter on `JOB_SK` + `CURR_FLG`).
- NFR-3: Extensible - new config types are new PARAM zones / new typed models, no change to existing models.
- NFR-4: Deterministic, typed public API; `Any` only where genuinely dynamic (decoded `PARAM_VAL`).

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, model_validator

# --- enums (values grounded in the readers / load_strategy families + the two-track decision; confirm/extend per domain) ---
class SourceType(str, Enum):
    FILE = "FILE"; EXCEL = "EXCEL"; JDBC = "JDBC"; ODBC = "ODBC"; SAP = "SAP"; STREAMING = "STREAMING"

class LoadType(str, Enum):
    FULL = "FULL"; INCREMENTAL = "INCREMENTAL"; STREAM = "STREAM"

class LoadPattern(str, Enum):
    APPEND = "APPEND"; MERGE = "MERGE"; UPSERT = "UPSERT"
    OVERWRITE = "OVERWRITE"; FULL_REFRESH = "FULL_REFRESH"; SCD1 = "SCD1"; SCD2 = "SCD2"

class Engine(str, Enum):                       # the two-track selector
    DECLARATIVE = "DECLARATIVE"                 # Lakeflow Declarative Pipelines + Auto Loader
    NON_DECLARATIVE = "NON_DECLARATIVE"         # classic batch PySpark + Delta MERGE

class Layer(str, Enum):
    BRONZE = "BRONZE"; SILVER = "SILVER"; GOLD = "GOLD"

class TableType(str, Enum):
    MANAGED = "MANAGED"; EXTERNAL = "EXTERNAL"

class Format(str, Enum):
    DELTA = "DELTA"; PARQUET = "PARQUET"

class DQRuleType(str, Enum):
    NOT_NULL = "NOT_NULL"; UNIQUE = "UNIQUE"; RANGE = "RANGE"
    REGEX = "REGEX"; REFERENTIAL = "REFERENTIAL"; CUSTOM_SQL = "CUSTOM_SQL"

class OnFailure(str, Enum):
    WARN = "WARN"; FAIL = "FAIL"; QUARANTINE = "QUARANTINE"

class TransformType(str, Enum):
    SQL = "SQL"; PYTHON = "PYTHON"; ACORD_MAPPING = "ACORD_MAPPING"

class SCDType(str, Enum):
    NONE = "NONE"; SCD1 = "SCD1"; SCD2 = "SCD2"

# --- typed config models (hydrated + validated on read) ---
class SourceConfig(BaseModel):                  # reusable; from ABC_SRC_CTRL_TBL by SRC_SK
    source_sk: str                              # = ABC_SRC_CTRL_TBL.SRC_SK
    source_name: str
    source_type: SourceType
    source_system: str
    table_name: Optional[str] = None            # ABC_SRC_CTRL_TBL.TBL_NM
    watermark_column: Optional[str] = None      # ABC_SRC_CTRL_TBL.CTRL_CLMN (extract control column)
    load_mode: LoadType = LoadType.INCREMENTAL  # ABC_SRC_CTRL_TBL.LOAD_FLG (F=FULL / I=INCREMENTAL)
    connection_options: dict = {}               # JSON-decoded option bag (host/path/driver/etc.)
    credential_scope: Optional[str] = None
    credential_key: Optional[str] = None
    business_domain: Optional[str] = None
    pii_flag: bool = False
    data_classification: Optional[str] = None
    sla_hours: Optional[int] = None
    active_flag: bool = True

class TargetConfig(BaseModel):
    target_name: str
    catalog_name: str
    schema_name: str
    table_name: str
    layer: Layer
    table_type: TableType = TableType.MANAGED
    format: Format = Format.DELTA
    partition_columns: List[str] = []
    liquid_clustering_columns: List[str] = []
    primary_key: List[str] = []
    acord_entity: Optional[str] = None
    retention_days: Optional[int] = None
    enable_cdf: bool = False
    dimensional: bool = False                   # gold star/snowflake -> drives schema-evolution SCD handling
    active_flag: bool = True

class LoadConfig(BaseModel):
    job_sk: str                                 # = ABC_JOB_CTRL_TBL.JOB_SK (one load == one Job)
    load_name: str
    source_sk: str                              # reference -> SourceConfig (resolved by the loader)
    source: Optional[SourceConfig] = None       # populated by the loader (by reference)
    target: TargetConfig
    load_type: LoadType
    load_pattern: LoadPattern
    engine: Engine
    watermark_column: Optional[str] = None
    checkpoint_location: Optional[str] = None
    merge_keys: Optional[List[str]] = None
    scd_type: SCDType = SCDType.NONE
    autoloader_options: dict = {}               # JSON-decoded option bag (declarative track)
    write_options: dict = {}                    # JSON-decoded option bag (non-declarative track)
    # schema-evolution policy (consumed by ingestion.engine._build_resolution_context -> ResolutionContext)
    source_system_type: str = "stable"          # stable | regulated | volatile
    governance_tier: str = "standard"           # standard | high
    zero_downtime: bool = False
    paranoid: bool = False
    type_changes: str = "none"                  # none | widening | strict
    renames_expected: bool = False
    active_flag: bool = True

    @model_validator(mode="after")
    def _business_rules(self) -> "LoadConfig": ...   # STREAM->watermark, SCD2->merge_keys, DECLARATIVE->checkpoint

class TransformConfig(BaseModel):
    transform_sk: str
    transform_name: str
    target: TargetConfig
    transform_type: TransformType
    transform_sql: Optional[str] = None
    transform_python: Optional[str] = None
    acord_mapping_template: Optional[str] = None
    scd_type: SCDType = SCDType.NONE
    scd_key_columns: Optional[List[str]] = None
    engine: Engine = Engine.NON_DECLARATIVE
    active_flag: bool = True

class DQRuleConfig(BaseModel):
    dq_rule_sk: str
    rule_name: str
    rule_type: DQRuleType
    column_name: Optional[str] = None
    rule_expression: Optional[str] = None
    threshold_percent: float = 0.0
    on_failure: OnFailure = OnFailure.WARN
    active_flag: bool = True

class ConfigLoader:
    """Read-only loader: hydrates + validates typed config from the ABC Control tables."""
    def __init__(self, spark, catalog: str = "insurelake_abc", schema: str = "abc") -> None: ...
    def get_source(self, source_sk: str) -> SourceConfig: ...          # from ABC_SRC_CTRL_TBL (reusable)
    def get_load(self, job_sk: str) -> LoadConfig: ...                 # PARAM zones load/target + source by reference
    def get_target(self, job_sk: str) -> TargetConfig: ...            # PARAM zone 'target'
    def get_transform(self, job_sk: str) -> TransformConfig: ...      # PARAM zone 'transform'
    def get_dq_rules(self, job_sk: str) -> List[DQRuleConfig]: ...    # PARAM zone 'dq' (0..n)
    # NO save_* methods - Control config is authored externally; the loader never writes.
```
Net-new vs current: enums fully defined; `ConfigLoader` is read-only (the `save_*` methods are removed); identifiers use the ABC surrogate keys (`source_sk`/`job_sk`); `LoadConfig` carries the resolved `source` + a `target`.

## 4. Inputs / Outputs
- **Input:** a `SparkSession` + a `job_sk` (or `source_sk`); the loader reads the ABC Control tables. PARAM rows are `(PARAM_ZONE, PARAM_NM, PARAM_VAL, CURR_FLG, ...)`.
- **Output:** validated typed config objects (`SourceConfig`/`TargetConfig`/`LoadConfig`/...). **No writes, no side effects** (the loader does not touch RUN/Audit tables; those are the engine/ABC SDK's job).

## 5. Design
`ConfigLoader` is a **Repository** over the ABC Control tables, returning typed objects so engines depend on abstractions, not on Delta/EAV layout. Two ideas carry the design: **EAV storage + validation-on-read** (PARAM rows are decoded, then handed to a Pydantic model that enforces the schema at the boundary), and **source-by-reference** (the reusable source lives once in `ABC_SRC_CTRL_TBL`; jobs point at it via `SRC_SK`). Because `PARAM_VAL` is text, the typed layer is what makes EAV safe - it coerces scalars, JSON-decodes lists/dicts, and rejects invalid enums/business-rule combinations.

### SOLID Principles Application
* **SRP:** each model owns one concern (source / target / load / transform / dq); `ConfigLoader` owns read+hydrate+validate only (no writes, no execution).
* **OCP:** a new config type is a new PARAM zone + a new typed model; existing models and the loader's read loop are untouched.
* **LSP:** every `get_*` returns a fully-validated model of its declared type; callers never receive a partially-built object.
* **ISP:** engines read only what they need (`get_load` for ingestion; `get_transform` for harmonization; `get_dq_rules` for DQ) - no fat "get everything" call.
* **DIP:** engines depend on the typed models + `ConfigLoader` abstraction, not on the EAV/Delta layout or the physical store (Delta today, Lakebase later).

### Design Patterns
- **Repository** (`ConfigLoader` abstracts the Control store), **Factory** (readers/strategies selected from `source_type`/`load_pattern`/`engine` by downstream engines), **Strategy** (DQ rule execution by `rule_type`).

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `get_load(job_sk)`: read `ABC_JOB_PARAM_TBL` where `JOB_SK = job_sk` **and `CURR_FLG = true`** (active SCD2 version), for `PARAM_ZONE` in {`load`, `target`, `source`}.
  2. Group rows by `PARAM_ZONE` into `{PARAM_NM: decode(PARAM_VAL)}` dicts.
  3. `decode`: if the value starts with `[` or `{`, `json.loads` it (lists like `merge_keys`, dicts like `autoloader_options`); else keep the string (Pydantic coerces bool/int/enum).
  4. **Source by reference:** read `SRC_SK` from the `source`/`load` zone and call `get_source(SRC_SK)` -> `SourceConfig` from `ABC_SRC_CTRL_TBL` (also `CURR_FLG = true`).
  5. Construct + validate: `TargetConfig(**target)`, then `LoadConfig(**load, source=<resolved>, target=<resolved>)`. Pydantic enforces enums + the `@model_validator` business rules; on failure raise `ConfigValidationError`.
  6. Return the typed object(s). **Never write** (read-only).
- **Decision rules:**
  - *active version:* always filter `CURR_FLG = true`; if none, raise `ConfigNotFoundError`.
  - *value decoding:* `PARAM_VAL` is text; `[`/`{` -> JSON; otherwise scalar string coerced by the model.
  - *enum validation:* `source_type` / `load_type` / `load_pattern` / `engine` / ... must be valid enum members, else `ConfigValidationError`.
  - *business rules (`@model_validator`):* `STREAM` load_type requires `watermark_column`; `SCD2` load_pattern requires `merge_keys`; `DECLARATIVE` engine requires `checkpoint_location`.
  - *source-by-reference:* never read source fields from a job's PARAM beyond `SRC_SK`; resolve via `get_source`.
  - *read-only:* the loader never writes Control config; authoring + SCD2 versioning happen in a separate process.
- **Key code fragments** (the generated code MUST contain these):
```python
import json
from pyspark.sql.functions import col, lit

def get_load(self, job_sk: str) -> LoadConfig:
    rows = (self.spark.table(f"{self.catalog}.{self.schema}.ABC_JOB_PARAM_TBL")
            .filter((col("JOB_SK") == lit(job_sk)) & (col("CURR_FLG") == lit(True)))
            .collect())
    if not rows:
        raise ConfigNotFoundError(f"No active config for job_sk={job_sk}")
    by_zone: dict[str, dict] = {}
    for r in rows:
        by_zone.setdefault(r["PARAM_ZONE"], {})[r["PARAM_NM"]] = _decode(r["PARAM_VAL"])
    load = by_zone.get("load", {})
    target = TargetConfig(**by_zone.get("target", {}))
    source = self.get_source(load["source_sk"])          # source by reference
    return LoadConfig(**load, source=source, target=target)   # Pydantic validates enums + business rules

def _decode(v):
    if isinstance(v, str) and v[:1] in ("[", "{"):
        return json.loads(v)        # lists (merge_keys), dicts (autoloader_options/write_options)
    return v                        # scalar; Pydantic coerces bool/int/enum

@model_validator(mode="after")
def _business_rules(self) -> "LoadConfig":
    if self.load_type == LoadType.STREAM and not self.watermark_column:
        raise ValueError("STREAM load requires watermark_column")
    if self.load_pattern == LoadPattern.SCD2 and not self.merge_keys:
        raise ValueError("SCD2 load_pattern requires merge_keys")
    if self.engine == Engine.DECLARATIVE and not self.checkpoint_location:
        raise ValueError("DECLARATIVE engine requires checkpoint_location")
    return self
```
- **Edge cases:** no active rows (`CURR_FLG`) -> `ConfigNotFoundError`; malformed JSON in `PARAM_VAL` -> `ConfigValidationError` (never silently pass a string where a list is expected); unknown enum value -> `ValidationError` listing the valid set; dangling `SRC_SK` (not in `ABC_SRC_CTRL_TBL`) -> `FKViolationError`; empty zone -> model defaults apply; whitespace/CRLF around `PARAM_VAL` -> strip before `_decode`; a `PARAM_NM` not on the model -> ignored or `ConfigValidationError` under strict mode (default: ignore + warn).

**Guidance:** single package `src/core/metadata/` (one module per model + `config_loader.py` + `enums.py` + `exceptions.py`); use `col`/`lit` filters (never f-string SQL); no writes.
**Constraints (hard):** read-only (no `save_*`, no table writes); PySpark read + Pydantic + stdlib `json` only; no ABC RUN/Audit writes (loader is not a data-plane run); typed public API (no bare `Any` except decoded `PARAM_VAL`); **code style** per `_shared/standards.md` (PEP 8 + black + Google docstrings; `ruff`/`black` must pass).

## 7. Validation, edge cases & versioning policy
Validation is **on read** (Pydantic at the boundary). SCD2 history lives in storage (`EFF_STRT_DTS`/`EFF_END_DTS`/`CURR_FLG`/`REC_VER_NO`); the loader always reads the current version. Adding a field is backward-compatible (new optional model field + new `PARAM_NM`); removing/renaming a public model field is a breaking change (bump the spec + downstream). Config **authoring/versioning is out of scope** (separate process); this spec only reads.

## 8. Error handling + ABC instrumentation
Typed exceptions: `ConfigNotFoundError` (no active rows), `ConfigValidationError` (enum/business-rule/JSON failure), `FKViolationError` (dangling `SRC_SK`). The loader is a **build/read utility, not a data-plane run -> no ABC RUN/Audit instrumentation here**; the *consuming engine* records the run, and the external config-authoring process audits config changes. Failures raise (fail-fast at config-load time), they are not swallowed.

## 9. Testing & acceptance
Unit (mock Spark rows):
- a known job -> `get_load` returns a validated `LoadConfig` with `source` resolved by reference;
- `merge_keys`/`autoloader_options` round-trip through JSON `_decode`;
- `STREAM` without `watermark_column` -> `ConfigValidationError`; `SCD2` without `merge_keys` -> `ConfigValidationError`; `DECLARATIVE` without `checkpoint_location` -> `ConfigValidationError`;
- unknown `source_type` -> validation error; dangling `SRC_SK` -> `FKViolationError`; no `CURR_FLG` rows -> `ConfigNotFoundError`.
Integration (real Spark + seeded Control tables): `get_load` for a seeded job returns the expected typed graph; only `CURR_FLG=true` rows are read. Acceptance = the front-matter `acceptance:` block (pytest + import smoke + `ruff`/`black`).

## 10. Examples
**Example 1 - hydrate a load (validation-on-read + source by reference):**
```python
loader = ConfigLoader(spark)            # read-only
load = loader.get_load("JOB_5101001")   # reads PARAM (load/target zones) + resolves SRC_SK
assert isinstance(load.engine, Engine)  # typed
assert load.source.source_sk == load.source_sk   # source resolved by reference
```
**Example 2 - the PARAM rows behind that job (`ABC_JOB_PARAM_TBL`, `CURR_FLG=true`):**
```text
JOB_SK      PARAM_ZONE  PARAM_NM            PARAM_VAL
JOB_5101001 load        load_pattern        SCD2
JOB_5101001 load        engine              DECLARATIVE
JOB_5101001 load        merge_keys          ["policy_id","version"]     # JSON list
JOB_5101001 load        checkpoint_location /chk/policy
JOB_5101001 load        source_sk           SRC_GWPC_POLICY
JOB_5101001 target      table_name          policy_raw
JOB_5101001 target      layer               BRONZE
```
**Example 3 - counter-example (DON'T): duplicating source in PARAM instead of by reference**
```python
# BAD: copying every source field into each job's PARAM (zone='source')
#   PARAM source.connection_options, source.credential_key, ... per job
# Problem: the same source is duplicated across every job that reads it; watermark state
#          has no single home. CORRECT: store source once in ABC_SRC_CTRL_TBL; jobs carry SRC_SK.
```

## 11. Regeneration contract
`scaffold-then-edit`. **Generate:** the enums, the Pydantic models + validators, and the read-only `ConfigLoader` (read -> `_decode` -> resolve `SRC_SK` -> validate). **Do NOT generate:** the Control-table DDL (owned by the ABC framework; names verbatim from the doc) or any write/authoring path. Custom domain enum *values* are human-confirmed (see section 3 note).

## 12. References
- `docs/ABC-MAPPING.md` - the locked ABC decisions (Control = config-model; PARAM storage; source-by-reference; validation-on-read; read-only loader).
- `abc-sdk-spec.md` - the orchestrator+recorder that reads config through this loader and owns the RUN/Audit tables + Cycle/Step/Job CTRL.
- `schema-evolution-spec.md` - `ResolutionContext` is populated from `LoadConfig`/`TargetConfig` policy fields.
- `ingestion-engine-spec.md` - consumes `LoadConfig` (+ resolved `source`/`target`).
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) - validation-on-read.
