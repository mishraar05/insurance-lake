---
id: dataio.schema-evolution
title: Schema Evolution (decision-tree-driven, two-track)
owner: EY
status: draft
target_path: src/dataio/schema_evolution/
owning_skill: framework-dev.build-ingestion-engine
backlog: [INGEST-040]
provides: [ResolutionContext, SchemaEvolutionConfig, QuarantineSchemaConfig, CompatibilityResult, resolve_schema_evolution, validate_config, validate_schema_compatibility, autoloader_options, delta_table_properties, delta_write_options, capture_drift]
depends_on: [foundation.contracts]
generation_context:
  - specs/foundation/contracts-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/dataio/test_schema_evolution.py"
  - "python -c 'from dataio.schema_evolution import resolve_schema_evolution, validate_config, validate_schema_compatibility, autoloader_options, delta_write_options, capture_drift, ResolutionContext, SchemaEvolutionConfig, QuarantineSchemaConfig, CompatibilityResult'"
regeneration: scaffold-then-edit
capability:
  framework: ingestion
  feature: schema-evolution
  selectable: true
---

# Schema Evolution - Specification

## 1. Purpose & scope
Decide **how an ingestion handles schema change** and translate that decision into concrete engine options, **and** validate that a proposed change is compatible before it is applied.
- **Two tracks:** the **declarative** track (Lakeflow Declarative Pipelines + Auto Loader) uses `cloudFiles.schemaEvolutionMode` and `_rescued_data`; the **non-declarative** track (classic **batch** PySpark + Delta) uses `mergeSchema`/`overwriteSchema`, Delta **column mapping**, Delta **type widening**, and a batch **drift-capture** to quarantine. Auto Loader / `_rescued_data` are **declarative-only** (they ride on Structured Streaming, excluded for non-declarative batch).
- In scope: the typed context + config models, the decision-tree resolver, a **config-conflict validator**, a **schema-compatibility validator** (reads the target schema), and the per-track appliers.
- Out of scope: the readers/load-strategies/engines that *call* these; the quarantine table DDL; the approval UI (this spec defines the gate + timeout behavior, not the queue implementation).

## 2. Requirements
**Functional**
- FR-1: `resolve_schema_evolution(ctx: ResolutionContext) -> SchemaEvolutionConfig` maps a **typed** context to a config (tree in section 6), applying the **conflict-precedence** rules.
- FR-2: `validate_config(cfg) -> list[str]` rejects impossible combinations (e.g. `_rescued_data` on non-declarative; `merge_schema` & `overwrite_schema` together; quarantine that can fail).
- FR-3: `validate_schema_compatibility(incoming, target, cfg) -> CompatibilityResult` reads the **target** schema to detect **type narrowing**, **rename without column mapping**, and **SCD0 changes**; returns `allowed`, `reasons`, `requires_rebuild`.
- FR-4: **Declarative** applier emits Auto Loader options; **non-declarative** applier emits Delta write options + table properties; `capture_drift` is the batch `_rescued_data` equivalent.
- FR-5: Quarantine **never fails**; its `override_mode` is constrained to never-fail-compatible values.
- FR-6: Every decision/applied change is logged to **ABC** with a defined record schema and two-phase call points; governed tiers gate behind HITL approval **with a timeout**.

**Non-functional**: deterministic resolver/validators; appliers pure (config -> dict) except `capture_drift`; current Databricks option names (verify at build time); typed inputs (no stringly-typed dicts in the public API).

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
@dataclass
class ResolutionContext:
    # required (no defaults)
    layer: str                          # "bronze" | "silver" | "gold"
    engine: str                         # "declarative" | "non_declarative"
    # context (defaults)
    source_system_type: str = "stable"  # "stable" | "regulated" | "volatile"
    review_required: bool = False        # regulated: every change reviewed before ingestion
    zero_downtime: bool = False
    paranoid: bool = False
    type_changes: str = "none"          # "none" | "widening" | "strict"
    renames_expected: bool = False
    governance_tier: str = "standard"   # "standard" | "high"
    dimensional: bool = False
    scd_type: Optional[int] = None      # 0 | 1 | 2
    quarantine_strategy: str = "match_source"   # "match_source" | "independent"
    approval_timeout_s: int = 86400     # SLA before timeout -> escalate + quarantine

@dataclass
class QuarantineSchemaConfig:
    override_mode: Optional[str] = None # None -> inherit; constrained to never-fail values (see validate_config)
    always_capture: bool = True
    enable_column_mapping: bool = True
    enable_type_widening: bool = True

@dataclass
class SchemaEvolutionConfig:
    # required (no defaults) - set by the resolver
    ingestion_layer: str                # "bronze" | "silver" | "gold"
    engine: str                         # "declarative" | "non_declarative"
    mode: str                           # "addNewColumns" | "rescue" | "failOnNewColumns" | "none"
    # source / context
    source_system_type: str = "stable"
    # delta features (non-declarative batch)
    merge_schema: bool = False
    overwrite_schema: bool = False
    enable_column_mapping: bool = False
    column_mapping_mode: str = "none"   # "none" | "name"
    enable_type_widening: bool = False
    # safety
    enable_rescued_data: bool = False        # declarative-only: _rescued_data column
    capture_drift_to_quarantine: bool = False # non-declarative batch "rescue" equivalent
    evolve_and_rescue: bool = False          # paranoid: addNewColumns + keep rescued column (declarative) / merge + drift (batch)
    max_rescued_columns: int = 200           # cap on _rescued_data width (truncate + flag beyond this)
    # governance
    require_approval: bool = False
    approval_timeout_s: int = 86400
    log_schema_changes_to_abc: bool = True
    # quarantine
    quarantine: Optional[QuarantineSchemaConfig] = None

@dataclass
class CompatibilityResult:
    allowed: bool
    reasons: list[str]
    requires_rebuild: bool = False

def resolve_schema_evolution(ctx: ResolutionContext) -> SchemaEvolutionConfig: ...   # decision tree + precedence
def validate_config(cfg: SchemaEvolutionConfig) -> list[str]: ...                    # config-conflict guard (errors)
def validate_schema_compatibility(incoming: "StructType", target: "StructType",
                                  cfg: SchemaEvolutionConfig) -> CompatibilityResult: ...
def autoloader_options(cfg: SchemaEvolutionConfig) -> dict: ...                      # declarative track
def delta_table_properties(cfg: SchemaEvolutionConfig) -> dict: ...                  # non-declarative: TBLPROPERTIES
def delta_write_options(cfg: SchemaEvolutionConfig) -> dict: ...                     # non-declarative: write options
def capture_drift(df: "DataFrame", expected_columns: list[str],
                  cfg: SchemaEvolutionConfig) -> tuple["DataFrame", "DataFrame"]: ...  # (clean, quarantine)
```

## 4. Inputs / Outputs
- Input: a typed `ResolutionContext`; for compatibility, the **incoming** and **target** `StructType`; for `capture_drift`, a DataFrame + expected columns.
- Output: a `SchemaEvolutionConfig`; a list of config-conflict errors; a `CompatibilityResult`; engine option/property dicts; a `(clean, quarantine)` DataFrame pair. Side effects: none in the appliers - ABC audit is written by the **calling engine** (section 8).

## 5. Design
Pipeline: **`resolve` -> `validate_config` -> `validate_schema_compatibility` -> applier -> engine writes -> ABC**. The resolver is a pure layer-aware decision tree producing one config; the two validators are pure guards (config conflicts, and schema compatibility against the live target); appliers are **track-specific** and never mix. `_rescued_data` exists **only** declaratively; batch synthesizes it via `capture_drift`. `StructType`/`DataFrame` typing comes from `core/contracts` (TYPE_CHECKING import) - that is why `foundation.contracts` is a dependency. Config models live **local to this component** (not `core/metadata`, not codegen SSOT). This is a **selectable** capability under the `ingestion` menu group.

**Naming convention (deliberate):** appliers are named for the technology they emit options for - `autoloader_options` (declarative) vs `delta_write_options`/`delta_table_properties` (non-declarative) - because each is product-specific and the name disambiguates the track. They are never called together.

### Resolver -> applier -> engine flow (with failure paths)
```
ResolutionContext
   -> resolve_schema_evolution  -> SchemaEvolutionConfig
   -> validate_config           -> [errors]? --yes--> raise ConfigError (build-time)
   -> validate_schema_compatibility(incoming, target)
        allowed=False --> route batch to QUARANTINE + ABC(rejected) + (HITL if governed)
        allowed=True  --> applier (autoloader_options | delta_*) -> engine write
                           write fails / capture_drift fails --> QUARANTINE + ABC(failed)
   -> ABC(applied)               (two-phase: decision[pending] -> applied|failed|timeout)
```

### SOLID Principles Application
* **SRP (Single Responsibility):** `resolve_schema_evolution` decides; `validate_config` checks config legality; `validate_schema_compatibility` checks the change against the target; each applier translates config to one engine's options; `capture_drift` splits a DataFrame. One reason to change each.
* **OCP (Open/Closed):** new layers, source types, or SCD types extend the resolver's branches; a new engine adds an applier - neither touches the others or the config dataclasses.
* **LSP (Liskov Substitution):** every applier returns a `dict`; both validators return their typed result; configs are interchangeable inputs, so callers compose them uniformly.
* **ISP (Interface Segregation):** declarative callers import only `autoloader_options`; batch callers import only `delta_*` + `capture_drift`; neither depends on the other track's surface.
* **DIP (Dependency Inversion):** depends on the `SchemaEvolutionConfig` abstraction and `core/contracts` `DataFrame`/`StructType` types, not on concrete readers, writers, or table implementations.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):

- **Procedure:**
  1. Build a `SchemaEvolutionConfig` from `ctx` per the Decision rules; apply the **precedence** order on conflict.
  2. Run `validate_config`; any error is a build-time defect -> raise (do not ship a contradictory config).
  3. At run time, the engine calls `validate_schema_compatibility(incoming, target, cfg)`. If not `allowed`, route the batch to quarantine and record `rejected` (governed tiers also raise HITL); never silently drop.
  4. Resolve the `quarantine` sub-config (inherit or override; default never-fail).
  5. Apply via the track-appropriate applier; on any write/drift failure, route the batch to quarantine and record `failed`.
  6. Log the two-phase ABC record (section 8).

- **Decision rules:**
  - **Conflict precedence (highest first)** - resolves the zero-downtime-vs-regulated and similar clashes:
    1. Gold **SCD0** -> `mode='none'`; any incoming change -> quarantine + HITL (never silent, never auto-applied).
    2. **Regulated + review_required** -> `mode='failOnNewColumns'` + `require_approval=true`, **but** a failing batch routes to quarantine instead of hard-halting (compliance wins; data preserved; availability kept).
    3. **zero_downtime** -> `mode='rescue'` (declarative `_rescued_data` / batch `capture_drift`); never fails.
    4. **paranoid** -> `evolve_and_rescue=true`.
    5. Otherwise the layer/source defaults below.
  - **Bronze:** `stable` -> `addNewColumns` (declarative) / `merge_schema=true` (batch). `regulated` -> precedence #2. `volatile` -> `rescue` (declarative `_rescued_data` / batch `capture_drift_to_quarantine`).
  - **Silver:** `type_changes='widening'` -> `enable_type_widening=true`; `'strict'` -> none (fail on type mismatch). `renames_expected` -> `enable_column_mapping=true`, `column_mapping_mode='name'`; else `'none'` + `merge_schema=true`. `governance_tier='high'` -> `require_approval=true` + full audit + schema versioning.
  - **Gold:** dimensional -> by `scd_type`: **0** -> reject (precedence #1); **1** -> adds only (`merge_schema=true`, no rename/drop); **2** -> `enable_column_mapping=true` for renames + **row-level** soft-delete (SCD2 history flags; Delta has **no** column soft-delete, so a removed column is *retained and stops being populated*, never hard-dropped). Non-dimensional (fact/aggregate) -> as Silver, stricter (deny renames/type changes unless explicit).
  - **Quarantine:** `match_source` -> always capture; `independent` -> inherit the main `mode`. `override_mode` constrained to never-fail values (`rescue`/`addNewColumns`/`none`); `failOnNewColumns` is rejected by `validate_config`.
  - **`evolve_and_rescue` (the former `dual_mode`, corrected):** declarative = `mode='addNewColumns'` **plus** `cloudFiles.rescuedDataColumn='_rescued_data'` (known new columns evolve; residual type-mismatched values are rescued) - **not** two evolution modes at once. Batch = `merge_schema=true` + `capture_drift_to_quarantine=true`.

- **Key code fragments** (the generated code MUST contain these):
```python
def autoloader_options(cfg):                       # declarative
    o = {"cloudFiles.schemaEvolutionMode": cfg.mode}
    if cfg.enable_rescued_data or cfg.evolve_and_rescue or cfg.mode == "rescue":
        o["cloudFiles.rescuedDataColumn"] = "_rescued_data"
    return o

def delta_write_options(cfg):                      # non-declarative batch
    if cfg.overwrite_schema: return {"overwriteSchema": "true"}
    if cfg.merge_schema:     return {"mergeSchema": "true"}
    return {}

def delta_table_properties(cfg):
    p = {}
    if cfg.enable_column_mapping: p["delta.columnMapping.mode"] = "name"
    if cfg.enable_type_widening:  p["delta.enableTypeWidening"] = "true"
    return p

def validate_config(cfg):                          # config-conflict guard
    e = []
    if cfg.engine == "non_declarative" and cfg.enable_rescued_data:
        e.append("enable_rescued_data is declarative-only")
    if cfg.engine == "declarative" and cfg.capture_drift_to_quarantine:
        e.append("capture_drift_to_quarantine is non-declarative-only")
    if cfg.merge_schema and cfg.overwrite_schema:
        e.append("merge_schema and overwrite_schema are mutually exclusive")
    if cfg.column_mapping_mode == "name" and not cfg.enable_column_mapping:
        e.append("column_mapping_mode='name' requires enable_column_mapping=true")
    if cfg.quarantine and cfg.quarantine.override_mode == "failOnNewColumns":
        e.append("quarantine must never fail; override_mode cannot be failOnNewColumns")
    return e

def capture_drift(df, expected_columns, cfg):      # batch equivalent of _rescued_data
    from pyspark.sql import functions as F
    expected = set(expected_columns)
    extra = [c for c in df.columns if c not in expected]
    if not extra:
        return df, df.limit(0)
    capped = extra[: cfg.max_rescued_columns]       # bound _rescued_data width
    clean = df.select(*[c for c in df.columns if c in expected])
    quarantine = (df.withColumn("_rescued_data", F.to_json(F.struct(*[F.col(c) for c in capped])))
                    .withColumn("_rescued_truncated", F.lit(len(extra) > len(capped))))
    return clean, quarantine
```

- **Edge cases:**
  - **Approval timeout** (`approval_timeout_s`): on timeout -> escalate + route the batch to quarantine; **never** auto-apply; pipeline keeps running (zero-downtime preserved), change held.
  - **`capture_drift` failure** (OOM / corrupt): the **engine** catches it, routes the whole batch to quarantine (raw row + `_rescued_data`), emits an ABC exception; the parent run does not fail.
  - **Rename before column mapping:** `validate_schema_compatibility` returns `allowed=False, requires_rebuild=True` - column mapping must be enabled **before** the rename arrives.
  - **Type narrowing / incompatible change:** detected by comparing `incoming` vs `target`; rejected (type widening only widens).
  - **Wide drift:** `_rescued_data` capped at `max_rescued_columns`; overflow flagged via `_rescued_truncated`.
  - **Gold SCD0:** reject any add/remove; SCD2 never hard-drops a column.
  - Empty input; idempotent re-run; `addNewColumns` auto-restarts the stream **only** inside Lakeflow Declarative Pipelines (unavailable in pure batch - hence the two tracks).

**Constraints (hard):** no Auto Loader / Structured Streaming on the non-declarative track; appliers add no Spark dependency except `capture_drift`; no `Any` in public signatures; schema decisions instrumented via the ABC SDK by the calling engine.

## 7. Validation, edge cases & versioning policy
The resolver's branches mirror this tree; changing it is a behavior change (add a per-branch test). Option-name drift (Auto Loader / Delta) is the main external risk - pin to current docs and cover with tests.

**Migration - which config changes are safe vs require a rebuild:**

| Change | In-place? | Notes |
|---|---|---|
| `enable_type_widening` | Yes (`ALTER ... SET TBLPROPERTIES`) | Applies to **future** widenings; existing columns untouched. |
| `enable_column_mapping` ('name') | Yes, but **one-way protocol upgrade** | Raises `minReader`/`minWriter`; affects all readers; cannot be cleanly reverted. Enable **before** the first rename. |
| `mergeSchema` (additive) | Yes (per write) | Adds columns only. |
| Rename a column | Yes, only **with** column mapping already enabled | Otherwise rejected (`requires_rebuild`). |
| Narrow a type | **No** | Requires rebuild/backfill - rejected by compatibility check. |
| Drop a column (hard) | **No** for SCD2 | SCD2 retains + stops populating; hard drop = rewrite. |
| Remove column mapping | **No** | Requires table recreation. |

## 8. Error handling + ABC instrumentation
Appliers stay **pure**; the **calling engine** owns ABC. **Two-phase** to avoid stale records: (1) log a `decision` record before applying (`approval_status='pending'` when `require_approval`); (2) after the write, log the terminal state (`applied` / `failed` / `rejected` / `timeout`) under the **same `trace_id`**. A pending record is always resolved by a later terminal record.

**Audit record schema** (`schema_change_audit`):
`run_id, trace_id, component, entity, ingestion_layer, engine, resolved_mode, evolve_and_rescue, columns_added[], columns_rescued[], drift_row_count, type_changes[], compat_allowed, compat_reasons[], approval_status, requires_rebuild, applied, ts`.

`capture_drift`/write failures never fail the parent run - they route to quarantine and record an exception. Governed tiers (`require_approval`) block the change until approved or `approval_timeout_s` elapses (-> `timeout` -> quarantine + escalate).

## 9. Testing & acceptance
Unit (resolver/validators, pure): each tree branch -> expected config; **precedence** (regulated + zero_downtime -> fail-to-quarantine, not silent rescue); `validate_config` catches `enable_rescued_data` on non-declarative, `merge_schema`+`overwrite_schema` together, `column_mapping_mode='name'` without `enable_column_mapping`, quarantine `override_mode='failOnNewColumns'`; `validate_schema_compatibility` flags **type narrowing**, **rename-without-column-mapping** (`requires_rebuild`), and **SCD0** changes. Appliers emit the exact dicts above. Integration (Spark): `capture_drift` splits clean/quarantine, caps width, sets `_rescued_truncated`; resolver->applier round-trip for a non-declarative volatile feed. Plus front-matter `acceptance`; >80% coverage.

## 10. Examples
- **Declarative, Bronze stable:** `resolve(...)` -> `mode='addNewColumns'`; `autoloader_options` -> `{"cloudFiles.schemaEvolutionMode":"addNewColumns"}`; Lakeflow auto-restarts on a new column; type mismatches land in `_rescued_data`.
- **Non-declarative, Bronze volatile:** `mode='rescue', capture_drift_to_quarantine=true`; the engine calls `capture_drift(df, expected)`, writes the quarantine side - pipeline never fails.
- **Silver, high governance, widening:** `enable_type_widening=true, require_approval=true` -> HITL approves (or times out -> quarantine), table set `delta.enableTypeWidening=true`, write `mergeSchema=true`, two-phase audit recorded.
- **Counter-example (what NOT to do):** do not emit `_rescued_data` / `cloudFiles.*` on the **non-declarative** track (Auto Loader doesn't run there - `validate_config` errors); use `capture_drift`.

## 11. Regeneration contract
`scaffold-then-edit`: context/config models, resolver, validators, and pure appliers are fully generated; `capture_drift` (Spark) and the engine's ABC two-phase hooks are generated then reviewed.

## 12. References
`specs/foundation/contracts-spec.md` (DataFrame/StructType typing) · `skills/_shared/project-structure.md` (placement) · `specs/ingestion/ingestion-engine-spec.md` (the consumer + where ABC two-phase logging lives) · Databricks: [Auto Loader schema evolution](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema), [Delta type widening](https://docs.databricks.com/aws/en/delta/type-widening), [Delta column mapping](https://docs.databricks.com/aws/en/delta/delta-column-mapping), [Schema evolution in Databricks](https://docs.databricks.com/aws/en/data-engineering/schema-evolution).
Note: `INGEST-040` is a **new** backlog task - add it to `AI_Ready_Backlog`. Bronze/Silver/Gold per `PROJECT_CONTEXT` medallion (RDL/SDL/CDL acronyms dropped).
