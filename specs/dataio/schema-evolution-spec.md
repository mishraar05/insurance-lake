---
id: dataio.schema-evolution
title: Schema Evolution (decision-tree-driven, two-track)
owner: EY
status: draft
target_path: src/dataio/schema_evolution/
owning_skill: framework-dev.build-ingestion-engine
backlog: [INGEST-040]
provides: [SchemaEvolutionConfig, QuarantineSchemaConfig, resolve_schema_evolution, autoloader_options, delta_table_properties, delta_write_options, capture_drift]
depends_on: [foundation.contracts]
generation_context:
  - specs/foundation/contracts-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/dataio/test_schema_evolution.py"
  - "python -c 'from dataio.schema_evolution import resolve_schema_evolution, autoloader_options, delta_write_options, capture_drift, SchemaEvolutionConfig, QuarantineSchemaConfig'"
regeneration: scaffold-then-edit
capability:
  framework: ingestion
  feature: schema-evolution
  selectable: true
---

# Schema Evolution - Specification

## 1. Purpose & scope
Decide **how an ingestion handles schema change** and translate that decision into concrete engine options. A layer-aware decision tree (Bronze / Silver / Gold, plus a Quarantine branch) produces a `SchemaEvolutionConfig`; appliers turn that config into the right options for whichever engine is running.
- **Two tracks** (per the architecture decision): the **declarative** track (Lakeflow Declarative Pipelines + Auto Loader) uses `cloudFiles.schemaEvolutionMode` and `_rescued_data`; the **non-declarative** track (classic **batch** PySpark + Delta) uses `mergeSchema` / `overwriteSchema`, Delta **column mapping**, Delta **type widening**, and a batch **drift-capture** to quarantine. Auto Loader / `_rescued_data` are **declarative-only** (they ride on Structured Streaming, which is excluded for non-declarative batch).
- In scope: the config models, the decision-tree resolver, and the per-track appliers.
- Out of scope: the readers/load-strategies/engines that *call* these (separate specs); the quarantine table's own DDL.

## 2. Requirements
**Functional**
- FR-1: `resolve_schema_evolution(ctx)` maps `{layer, engine, source_system_type, zero_downtime, paranoid, type_changes, renames, governance_tier, dimensional, scd_type, quarantine_strategy}` to a `SchemaEvolutionConfig` (see the tree in §6).
- FR-2: **Declarative** applier emits Auto Loader options (`cloudFiles.schemaEvolutionMode`, optional `cloudFiles.rescuedDataColumn`).
- FR-3: **Non-declarative** applier emits Delta write options (`mergeSchema` / `overwriteSchema`) + table properties (`delta.columnMapping.mode`, `delta.enableTypeWidening`).
- FR-4: **Drift-capture** (`capture_drift`) is the batch equivalent of `_rescued_data`: split an incoming DataFrame into `(clean, quarantine)` so the pipeline never fails on unexpected columns.
- FR-5: Quarantine config may inherit the main mode or override it; the default quarantine posture **never fails**.
- FR-6: Every resolved decision and applied schema change is logged to **ABC** (audit); governed tiers gate evolution behind HITL approval.

**Non-functional**: deterministic resolver (same inputs -> same config); appliers are pure (config -> option dict), no Spark needed except `capture_drift`; current Databricks option names (verify at build time).

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
@dataclass
class QuarantineSchemaConfig:
    override_mode: Optional[str] = None       # None -> inherit the main table's mode
    always_capture: bool = True               # never fail: declarative _rescued_data / batch capture_drift
    enable_column_mapping: bool = True
    enable_type_widening: bool = True

@dataclass
class SchemaEvolutionConfig:
    # required (no defaults) - set by the resolver
    ingestion_layer: str                      # "bronze" | "silver" | "gold"
    engine: str                               # "declarative" | "non_declarative"
    mode: str                                 # "addNewColumns" | "rescue" | "failOnNewColumns" | "none"
    # source / context
    source_system_type: str = "stable"        # "stable" | "regulated" | "volatile"
    # delta features (non-declarative batch)
    merge_schema: bool = False
    overwrite_schema: bool = False
    enable_column_mapping: bool = False
    column_mapping_mode: str = "none"         # "none" | "name"
    enable_type_widening: bool = False
    # safety
    enable_rescued_data: bool = False         # declarative-only: _rescued_data column
    capture_drift_to_quarantine: bool = False # non-declarative batch "rescue" equivalent
    dual_mode: bool = False                   # declarative: rescue + addNewColumns
    # governance
    require_approval: bool = False            # HITL gate before evolution
    log_schema_changes_to_abc: bool = True
    # quarantine
    quarantine: Optional[QuarantineSchemaConfig] = None

def resolve_schema_evolution(ctx: dict) -> SchemaEvolutionConfig: ...        # the decision tree
def autoloader_options(cfg: SchemaEvolutionConfig) -> dict: ...              # declarative track
def delta_table_properties(cfg: SchemaEvolutionConfig) -> dict: ...          # non-declarative: TBLPROPERTIES
def delta_write_options(cfg: SchemaEvolutionConfig) -> dict: ...             # non-declarative: write options
def capture_drift(df: "DataFrame", expected_columns: list[str],
                  cfg: SchemaEvolutionConfig) -> tuple["DataFrame", "DataFrame"]: ...  # (clean, quarantine)
```

## 4. Inputs / Outputs
- Input: a resolution `ctx` (the answers to the decision tree) + the active `engine`; for `capture_drift`, an incoming DataFrame + the target's expected columns.
- Output: a `SchemaEvolutionConfig`; option/property dicts for the engine; a `(clean, quarantine)` DataFrame pair. Side effect: ABC audit records (via the caller / ABC SDK).

## 5. Design
The resolver is a pure layer-aware decision tree (§6) producing one config object. Appliers are **track-specific** and never mix: declarative -> `autoloader_options`; non-declarative batch -> `delta_table_properties` + `delta_write_options` (+ `capture_drift` for the rescue intent). `_rescued_data` exists **only** on the declarative track; the batch track synthesizes an equivalent `_rescued_data` column inside `capture_drift`. Config models live **local to this component** (`src/dataio/schema_evolution/`) by decision - they are not in `core/metadata` and are not part of the control-table codegen SSOT. This is a **selectable** capability under the `ingestion` menu group.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):

- **Procedure:**
  1. Read `ctx`: `layer`, `engine`, and the layer-specific answers.
  2. Branch on `layer` and fill the config per the Decision rules below.
  3. Resolve the `quarantine` sub-config (inherit or override; default = never-fail).
  4. Normalize for the active `engine`: declarative keeps `mode` + `enable_rescued_data`; non-declarative maps `mode` -> Delta flags (`merge_schema` / `capture_drift_to_quarantine` / strict-fail) and clears `enable_rescued_data`.
  5. Return the config. The caller applies it via the track-appropriate applier and logs the decision to ABC.

- **Decision rules:**
  - **Bronze** (raw landing, source-aligned):
    - `source_system_type=stable` -> `mode=addNewColumns`; declarative: schemaEvolutionMode=addNewColumns; non-declarative: `merge_schema=true`.
    - `source_system_type=regulated` -> if every change must be reviewed first: `mode=failOnNewColumns`, `enable_column_mapping=true`, `require_approval=true`, ABC schema audit; else `mode=addNewColumns` + ABC notification.
    - `source_system_type=volatile` -> `mode=rescue`; declarative: `enable_rescued_data=true`; non-declarative: `capture_drift_to_quarantine=true`. Never fail.
    - `zero_downtime=true` -> force `mode=rescue` (declarative `_rescued_data` / batch capture_drift).
    - `paranoid=true` -> `dual_mode=true` (declarative: rescue + addNewColumns; batch: `merge_schema=true` + `capture_drift_to_quarantine=true`).
  - **Silver** (curated, conformed):
    - `type_changes=widening` -> `enable_type_widening=true`; strict types -> leave false (fail on type mismatch).
    - `renames=true` -> `enable_column_mapping=true`, `column_mapping_mode='name'`; additive-only -> `column_mapping_mode='none'`, `merge_schema=true`.
    - `governance_tier=high` -> `require_approval=true` + full ABC audit + schema versioning; `standard` -> auto-merge + post-notification.
  - **Gold** (analytics-ready):
    - `dimensional=true` -> by `scd_type`: **0** -> reject evolution (`mode='none'`, no adds); **1** -> column **adds only** (`merge_schema=true`, no rename/drop); **2** -> `enable_column_mapping=true` (`'name'`) + soft deletes.
    - `dimensional=false` (fact / aggregate) -> same as Silver, **stricter** validation (default deny renames/type changes unless explicitly allowed).
  - **Quarantine** (failed/rejected records):
    - `quarantine_strategy=match_source` -> always capture (declarative `_rescued_data` / batch capture_drift); `independent` -> inherit the main `mode`.
    - column mapping / type widening per `QuarantineSchemaConfig`.
    - **Default quarantine** = never-fail: declarative `rescue` + `_rescued_data` + column mapping + type widening; non-declarative `capture_drift_to_quarantine` + column mapping + type widening.

- **Key code fragments** (the generated code MUST contain these):
```python
def autoloader_options(cfg):                       # declarative (Lakeflow Declarative Pipelines + Auto Loader)
    o = {"cloudFiles.schemaEvolutionMode": cfg.mode}
    if cfg.enable_rescued_data or cfg.mode == "rescue":
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

def capture_drift(df, expected_columns, cfg):      # batch equivalent of _rescued_data
    from pyspark.sql import functions as F
    expected = set(expected_columns)
    unexpected = [c for c in df.columns if c not in expected]
    if not unexpected:
        return df, df.limit(0)
    clean = df.select(*[c for c in df.columns if c in expected])
    quarantine = df.withColumn("_rescued_data", F.to_json(F.struct(*[F.col(c) for c in unexpected])))
    return clean, quarantine
```

- **Edge cases:**
  - `addNewColumns` restarts the stream and is handled automatically **only** inside Lakeflow Declarative Pipelines -> it is unavailable in pure batch (hence the two tracks).
  - Type **narrowing** / incompatible change -> reject (type widening only widens).
  - A **rename** arriving without column mapping already enabled -> write fails; column mapping must be enabled **before** the rename.
  - Gold **SCD 0** -> reject any evolution; Gold **SCD 1** -> adds only (no rename/drop); **SCD 2** -> soft-delete, never hard-drop.
  - Quarantine must **never** fail (always capture).
  - Non-declarative has no Auto Loader `_rescued_data`; the column is **synthesized** by `capture_drift`.
  - Empty input; idempotent re-run; governed tier -> `require_approval` blocks the schema change until HITL approves (then apply + audit).

**Guidance:** target `src/dataio/schema_evolution/`; verify the exact Databricks option names at build time (they evolve); keep appliers pure and track-separated.
**Constraints (hard):** no Auto Loader / Structured Streaming on the non-declarative track; appliers add no Spark dependency except `capture_drift`; instrument schema decisions via the ABC SDK; no `Any` in public signatures.

## 7. Validation, edge cases & versioning policy
The resolver's branches mirror this tree; changing the tree is a behavior change (add a test per branch). Option-name drift (Auto Loader / Delta) is the main external risk - pin to current docs and cover with unit tests. Adding a new layer or SCD type is additive; removing a `mode` value is breaking.

## 8. Error handling + ABC instrumentation
Every resolved decision and every applied schema change MUST be logged to **ABC** (audit): layer, source type, resolved `mode`, columns added/rescued, drift counts (balance), and approval status. Governed tiers (`require_approval=true`) route through HITL before the property/schema change is applied. `capture_drift` failures must not fail the parent run; on an unexpected error, route the whole batch to quarantine and record an exception.

## 9. Testing & acceptance
Unit (resolver, pure): `bronze+stable -> addNewColumns & merge_schema`; `bronze+volatile -> rescue & capture_drift_to_quarantine`; `bronze+regulated+review -> failOnNewColumns & require_approval`; `silver+widening -> enable_type_widening`; `silver+renames -> column_mapping_mode='name'`; `gold+scd0 -> mode='none'`; quarantine default -> never-fail. Appliers: `autoloader_options` and `delta_write_options`/`delta_table_properties` emit the exact dicts above. Integration (Spark): `capture_drift` splits clean vs quarantine and synthesizes `_rescued_data`. Plus front-matter `acceptance`; >80% coverage.

## 10. Examples
- **Bronze, volatile, non-declarative:** `resolve(...)` -> `mode='rescue', capture_drift_to_quarantine=true`; the engine calls `capture_drift(df, expected)` and writes the quarantine side to the quarantine table - pipeline never fails.
- **Silver, high governance, widening:** `enable_type_widening=true, require_approval=true` -> HITL approves, table set `delta.enableTypeWidening=true`, write with `mergeSchema=true`, audit recorded.
- **Counter-example (what NOT to do):** do not emit `_rescued_data` / `cloudFiles.*` on the **non-declarative** track - Auto Loader doesn't run there; use `capture_drift` instead.

## 11. Regeneration contract
`scaffold-then-edit`: the config models, resolver, and pure appliers are fully generated; `capture_drift` (Spark) and the ABC hooks are generated then reviewed.

## 12. References
`specs/foundation/contracts-spec.md` (DataFrame typing) · `skills/_shared/project-structure.md` (placement) · `specs/ingestion/ingestion-engine-spec.md` (the consumer) · Databricks: [Auto Loader schema evolution](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema), [Delta type widening](https://docs.databricks.com/aws/en/delta/type-widening), [Schema evolution in Databricks](https://docs.databricks.com/aws/en/data-engineering/schema-evolution).
Note: `INGEST-040` is a **new** backlog task for this capability - add it to `AI_Ready_Backlog`. Bronze/Silver/Gold per `PROJECT_CONTEXT` medallion (RDL/SDL/CDL acronyms dropped).
