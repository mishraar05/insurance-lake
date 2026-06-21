---
id: dataio.load_strategy.scd2-strategy
title: SCD Type 2 Load Strategy (batch Delta MERGE)
owner: EY
status: draft
target_path: src/dataio/load_strategy/scd2/
owning_skill: framework-dev.build-ingestion-engine
backlog: [INGEST-004]
provides: [Scd2Strategy]
depends_on: [core.contracts, core.metadata]
generation_context:
  - specs/foundation/contracts-spec.md
  - specs/foundation/config-model-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/dataio/test_scd2_strategy.py"
  - "python -c 'from dataio.load_strategy import Scd2Strategy'"
regeneration: scaffold-then-edit
---

# SCD Type 2 Load Strategy - Specification

## 1. Purpose & scope
The **SCD Type 2** load strategy implementing `core.contracts.LoadStrategy` via a Delta **MERGE**: it maintains full row history with effective-dating (`__start_at` / `__end_at` / `__is_current`), closing out changed (and optionally deleted) records and inserting new versions. **Non-declarative** (batch MERGE); a sibling of `dataio.load_strategy.append-strategy`. Reused by both **ingestion** (Silver slowly-changing reference data) and **harmonization** (Gold dimensions).
- In scope: the SCD2 MERGE write, change detection, soft-delete, and `WriteResult` metric capture.
- Out of scope: **declarative** SCD via **AUTO CDC** (`create_auto_cdc_flow`) - that is the *declarative* track and lives in `framework/<engine>/declarative/` (per the two-track placement rule); *which* entities are SCD2 (config `scd_type`); schema evolution (`dataio.schema-evolution`); retry (engine); ABC (engine logs).

## 2. Requirements
**Functional**
- FR-1: Implement `LoadStrategy.apply(df, target, load, options: Optional[dict] = None) -> WriteResult` using a single Delta **MERGE**.
- FR-2: Natural key from `load.merge_keys` (**required** - SCD2 needs a business key); change detection over the **tracked columns** (default: all non-key, non-metadata columns) via a `__row_hash`.
- FR-3: Maintain metadata columns: `__start_at` (timestamp), `__end_at` (timestamp, null while current), `__is_current` (bool), `__row_hash` (string). Exactly **one** current version per key.
- FR-4: A **changed** key -> close the current version (`__end_at=now`, `__is_current=false`) **and** insert the new version; **new** key -> insert; **unchanged** key -> no-op (idempotent re-run).
- FR-5: **Soft-delete** only - never hard-delete. Optional snapshot-delete (`options["delete_detection"]="snapshot"`) closes out keys absent from the batch; default incremental infers no deletes.
- FR-6: Return `WriteResult.num_output_rows` = `numTargetRowsInserted + numTargetRowsUpdated` from the MERGE commit's `operationMetrics`.

**Non-functional**: idempotent (hash compare makes a repeat batch a no-op); single atomic MERGE; typed; no ABC; table created with the SCD2 schema on first run.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
from core.contracts import LoadStrategy, WriteResult   # structural target + return type

class Scd2Strategy:                          # implements core.contracts.LoadStrategy
    META = ["__start_at", "__end_at", "__is_current", "__row_hash"]
    def __init__(self, spark: "SparkSession") -> None: ...
    def apply(self, df: "DataFrame", target: TargetConfig, load: LoadConfig,
              options: Optional[Dict[str, str]] = None) -> WriteResult: ...
    def _ensure_table(self, fqn: str, df: "DataFrame") -> None: ...        # create with META cols on first run
    def _stage(self, df: "DataFrame", keys: list, tracked: list) -> "DataFrame": ...  # add __row_hash
    def _merge(self, fqn: str, staged: "DataFrame", keys: list) -> WriteResult: ...    # union-source SCD2 MERGE
```

## 4. Inputs / Outputs
- Input: the incoming `DataFrame`, `TargetConfig`, `LoadConfig` (`merge_keys`), engine `options` (e.g. `delete_detection`, write options from `dataio.schema-evolution`).
- Output: a `WriteResult(num_output_rows=inserted+updated, operation="MERGE")`. Side effect: a Delta MERGE maintaining SCD2 history on the target.

## 5. Design
`Scd2Strategy` matches the `LoadStrategy` protocol structurally. It uses the canonical Databricks **union-source SCD2 MERGE**: a changed key appears **twice** in the source - once keyed (to *close* the current row) and once with a NULL merge key (to *insert* the new version) - because a single MERGE row can't both update the old and insert the new. Change is detected by `__row_hash` over the tracked columns. Table properties (column mapping / type widening) are the **engine's** job (ALTER before `apply`); this strategy only writes + measures. Declarative SCD (AUTO CDC) is the *other track* and is not implemented here.

### SOLID Principles Application
* **SRP:** maintains SCD2 history and reports its row count - nothing else.
* **OCP:** `append`, `scd1`, `scd6`, `delete-insert` are **sibling** strategies on the same protocol; this class is unchanged when they're added.
* **LSP:** any `LoadStrategy` is substitutable; the engine calls `apply` uniformly and reads `WriteResult`.
* **ISP:** exposes one method (`apply`); the engine depends on nothing more.
* **DIP:** depends on the `TargetConfig`/`LoadConfig` abstractions and the `LoadStrategy`/`WriteResult` contracts, not a concrete table.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `fqn = f"{target.catalog_name}.{target.schema_name}.{target.table_name}"`; `keys = load.merge_keys` (**error if empty**).
  2. `tracked = options.get("tracked_columns") or [c for c in df.columns if c not in keys and c not in META]`.
  3. `staged = _stage(df, keys, tracked)` - add `__row_hash = sha2(concat_ws('||', *tracked), 256)`.
  4. `_ensure_table(fqn, staged)` - if absent, create with business cols + `META`, clustered on `keys`.
  5. `_merge(fqn, staged, keys)` - the union-source MERGE (below).
  6. Optional snapshot delete: if `options["delete_detection"]=="snapshot"`, close out current keys not present in `staged`.
  7. Return `WriteResult(numTargetRowsInserted + numTargetRowsUpdated, operation="MERGE")` from the commit metrics.
- **Decision rules:**
  - `merge_keys` is **required** (SCD2 has no meaning without a natural key) -> raise on empty.
  - change = `__row_hash` differs from the current version's hash; unchanged -> no-op (idempotent).
  - deletes: default **incremental** (no delete inference); `snapshot` mode soft-closes absent keys; **never** hard-delete.
  - exactly one current row per key (guaranteed by `... AND t.__is_current = true` in the MERGE `ON`).
  - `META` column names are a **stable contract** (downstream reads `__is_current`).
- **Key code fragments** (the generated code MUST contain these):
```python
from pyspark.sql import functions as F
def _stage(self, df, keys, tracked):
    return df.withColumn("__row_hash", F.sha2(F.concat_ws("||", *[F.col(c).cast("string") for c in tracked]), 256))
```
```sql
-- union-source SCD2 MERGE (changed keys appear twice: keyed = close old, NULL = insert new)
MERGE INTO {fqn} t
USING (
  SELECT s.*, s.{key} AS __mergeKey FROM staged s
  UNION ALL
  SELECT s.*, NULL AS __mergeKey
  FROM staged s JOIN {fqn} t ON s.{key} = t.{key} AND t.__is_current = true
  WHERE s.__row_hash <> t.__row_hash               -- only changed keys get the insert-new arm
) src
ON t.{key} = src.__mergeKey AND t.__is_current = true
WHEN MATCHED AND t.__row_hash <> src.__row_hash THEN
  UPDATE SET t.__is_current = false, t.__end_at = current_timestamp()
WHEN NOT MATCHED THEN
  INSERT (<cols>, __row_hash, __start_at, __end_at, __is_current)
  VALUES (<vals>, src.__row_hash, current_timestamp(), NULL, true)
```
- **Edge cases:** brand-new key -> 1 current version; **unchanged** key -> no-op (re-run is idempotent); changed key -> old closed + new inserted; snapshot delete -> current soft-closed (`__is_current=false`), never hard-deleted; table absent -> created with the SCD2 schema; null/empty natural key -> reject (should be caught upstream as `MISSING_KEY` quarantine); multi-column key -> the `ON`/join uses all `keys`; out-of-order arrivals -> `__start_at = current_timestamp()` unless an event-time column is configured.

**Constraints (hard):** single MERGE (atomic); never hard-delete; `merge_keys` required; always return a `WriteResult`; no ABC (engine logs); no table-property ALTER (engine's job); typed signatures.

## 7. Validation, edge cases & versioning policy
`META` column names + "one current row per key" are stable contracts. `WriteResult.num_output_rows` (= inserted + updated) is the engine's balance source. The **declarative** SCD equivalent is **AUTO CDC** in `framework/<engine>/declarative/` (not this spec). New patterns (SCD1, SCD6, delete-insert) are **new** sibling strategies (OCP).

## 8. Error handling + ABC instrumentation
Pure write - **no ABC** (the engine logs). On MERGE failure, `apply` raises; the engine quarantines the batch (`WRITE_FAILURE`) and re-raises the original error. Never swallow a failed MERGE.

## 9. Testing & acceptance
Unit (local Spark): a new key -> 1 current version; **re-running the same batch -> zero new versions** (idempotent via hash); a changed tracked column -> old row `__is_current=false` + `__end_at` set AND a new current row; an **untracked** column change -> no new version; `WriteResult.num_output_rows == inserted + updated`; `delete_detection="snapshot"` closes an absent key; empty `merge_keys` -> error. Plus front-matter `acceptance`; >80% coverage.

## 10. Examples
- **Policy dimension:** `policy_id` key; a `status` change -> the prior row is closed (`__end_at=now`, `__is_current=false`) and a new current row is inserted; queries filter `__is_current = true` for the latest, or use `__start_at`/`__end_at` for as-of history.
- **Counter-examples:** do **not** hard-delete a removed key (close it out - history must survive); do **not** use `append-strategy` for an entity that needs history; do **not** put AUTO CDC / declarative logic here (that is the declarative track); do **not** return `df.count()` as the metric (return `inserted + updated` from the commit).

## 11. Regeneration contract
`scaffold-then-edit`: the class + `apply`/`_stage` skeleton are fully generated; the MERGE SQL and the metric read are generated then reviewed against current Delta MERGE semantics.

## 12. References
`specs/foundation/contracts-spec.md` (`LoadStrategy`, `WriteResult`) · `specs/foundation/config-model-spec.md` (`merge_keys`, `scd_key_columns`, `scd_timestamp_column`) · `specs/dataio/append-strategy-spec.md` (sibling strategy) · `specs/dataio/schema-evolution-spec.md` (Gold SCD policy + write options) · `skills/_shared/project-structure.md` (two-track: declarative AUTO CDC -> `framework/<engine>/declarative/`) · Databricks: [SCD Type 2 with MERGE](https://docs.databricks.com/aws/en/delta/merge#scd-type-2).
Note: `INGEST-004` is a **new** backlog task - add it to `AI_Ready_Backlog`. The **declarative** SCD2 (AUTO CDC) is a separate, future spec on the declarative track.
