---
id: dataio.load_strategy.append-strategy
title: Append Load Strategy (batch Delta)
owner: EY
status: draft
target_path: src/dataio/load_strategy/append/
owning_skill: framework-dev.build-ingestion-engine
backlog: [INGEST-003]
provides: [AppendStrategy]
depends_on: [core.contracts, core.metadata]
generation_context:
  - specs/foundation/contracts-spec.md
  - specs/foundation/config-model-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/dataio/test_append_strategy.py"
  - "python -c 'from dataio.load_strategy import AppendStrategy'"
regeneration: scaffold-then-edit
---

# Append Load Strategy - Specification

## 1. Purpose & scope
The **append** load strategy implementing `core.contracts.LoadStrategy`: write a DataFrame to a Unity Catalog Delta table in **append** mode, apply engine-supplied write options, and return a `WriteResult` carrying the **real** committed row count (`numOutputRows`) so the engine's balance check is true.
- In scope: the append write + race-safe metric capture.
- Out of scope: SCD1/SCD2/MERGE (separate strategies); table-property `ALTER` (the engine applies column-mapping/type-widening before calling `apply`); schema-evolution decisions (`dataio.schema-evolution`); retry (the engine never retries the append); ABC (the engine logs).

## 2. Requirements
**Functional**
- FR-1: Implement `LoadStrategy.apply(df, target, load, options: Optional[dict] = None) -> WriteResult`.
- FR-2: Append mode; merge the engine-supplied `options` (e.g. `mergeSchema`, `overwriteSchema`) into the writer.
- FR-3: Return `WriteResult.num_output_rows` read from the **commit's** `operationMetrics`, bracketed by table version so it reads *this* write's commit (not "the last" one) - race-safe.
- FR-4: Create the table on first write (append auto-creates).
- FR-5: **Single attempt** - this strategy never retries internally (a Delta commit is atomic; idempotency is the caller's concern).

**Non-functional**: always returns a `WriteResult` (even for 0 rows); typed; no ABC; no hard-coded catalog/table.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
from core.contracts import LoadStrategy, WriteResult   # structural target + return type

class AppendStrategy:                        # implements core.contracts.LoadStrategy
    def __init__(self, spark: "SparkSession") -> None: ...
    def apply(self, df: "DataFrame", target: TargetConfig, load: LoadConfig,
              options: Optional[Dict[str, str]] = None) -> WriteResult: ...
    def _current_version(self, fqn: str) -> Optional[int]: ...   # None if the table is absent
    def _commit_rows(self, fqn: str, v0: Optional[int]) -> int: ...  # numOutputRows of commits after v0
```

## 4. Inputs / Outputs
- Input: the `DataFrame` to write, `TargetConfig` (catalog/schema/table), `LoadConfig`, and engine `options` (write options from `dataio.schema-evolution.delta_write_options`).
- Output: a `WriteResult(num_output_rows, operation="WRITE", metrics=...)`. Side effect: a Delta append to the target.

## 5. Design
`AppendStrategy` matches the `LoadStrategy` protocol structurally. It captures the table version **before** the write, performs a single append applying `options`, then reads the `numOutputRows` from the commit(s) **after** that version - so the metric is *this* write's, immune to the `DESCRIBE HISTORY LIMIT 1` race the engine review flagged. Table properties (column mapping / type widening) are **not** this strategy's job - the engine `ALTER`s them before calling `apply`.

### SOLID Principles Application
* **SRP:** writes (append) and reports its row count - nothing else.
* **OCP:** SCD1/SCD2/overwrite are **new** strategies implementing the same protocol; this class is unchanged.
* **LSP:** any `LoadStrategy` (Append/SCD2/...) is substitutable; the engine calls `apply` uniformly and reads `WriteResult`.
* **ISP:** exposes one method (`apply`); the engine depends on nothing more.
* **DIP:** depends on the `TargetConfig`/`LoadConfig` abstractions and the `LoadStrategy`/`WriteResult` contracts, not a concrete table implementation.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `fqn = f"{target.catalog_name}.{target.schema_name}.{target.table_name}"`.
  2. `v0 = _current_version(fqn)` (None if the table does not exist yet).
  3. Build `w = df.write.format("delta").mode("append")`; apply each `options` item via `.option(k, v)`.
  4. `w.saveAsTable(fqn)` - **one** attempt.
  5. `rows = _commit_rows(fqn, v0)` - sum `numOutputRows` of commits with `version > v0` (or all if the table was absent).
  6. `return WriteResult(num_output_rows=rows, operation="WRITE")`.
- **Decision rules:**
  - Mode is always **append**; `options` come from the engine (e.g. `mergeSchema=true`) and are passed through verbatim.
  - The metric is the **commit's** `numOutputRows`, never `df.count()` or `rows_read` (that was the engine's old tautology).
  - Version bracket: read only commits **after** `v0`, so a concurrent commit before the write is excluded (single-writer-per-target is the norm for ingestion).
- **Key code fragments** (the generated code MUST contain these):
```python
def apply(self, df, target, load, options=None):
    fqn = f"{target.catalog_name}.{target.schema_name}.{target.table_name}"
    v0 = self._current_version(fqn)                  # None if absent
    w = df.write.format("delta").mode("append")
    for k, val in (options or {}).items():
        w = w.option(k, val)
    w.saveAsTable(fqn)                               # single attempt (engine never retries the write)
    return WriteResult(num_output_rows=self._commit_rows(fqn, v0), operation="WRITE")

def _commit_rows(self, fqn, v0):
    hist = self.spark.sql(f"DESCRIBE HISTORY {fqn}").select("version", "operationMetrics")
    floor = -1 if v0 is None else v0
    return sum(int((r["operationMetrics"] or {}).get("numOutputRows", 0))
               for r in hist.collect() if r["version"] > floor)
```
- **Edge cases:** target absent -> created on first append (`v0=None` -> count all commits, i.e. version 0); empty df -> commit with `numOutputRows=0` -> `WriteResult(0)` (balance still meaningful); `mergeSchema` option -> additive columns accepted; a partial write fails as a whole (Delta commit is atomic) -> `apply` raises and the engine routes the batch to quarantine `WRITE_FAILURE`; the strategy **never** retries.

**Constraints (hard):** append only; single attempt (no internal retry); always return a `WriteResult`; no table-property `ALTER` (engine's job); no ABC; typed signatures.

## 7. Validation, edge cases & versioning policy
`WriteResult.num_output_rows` is the engine's balance source - pin to Delta `operationMetrics.numOutputRows`. New load patterns (SCD1/SCD2/overwrite) are **new** strategy classes (OCP), not changes here. The `apply` signature follows `core.contracts` v0.2.0 (`options` + `WriteResult`).

## 8. Error handling + ABC instrumentation
Pure write - **no ABC** (the engine logs). On write failure, `apply` raises; the engine catches it, quarantines the batch (`WRITE_FAILURE`), and re-raises the original error. The strategy never swallows a write failure.

## 9. Testing & acceptance
Unit (local Spark): appends rows and `WriteResult.num_output_rows` equals the committed count; empty df -> `WriteResult(0)`; a `mergeSchema` option adds a new column; the table is created on first write; `_commit_rows` reads only commits after `v0` (version bracket). Plus front-matter `acceptance`; >80% coverage.

## 10. Examples
- **Append 1,000 rows:** `apply(df, target, load, options={"mergeSchema": "true"})` -> `WriteResult(num_output_rows=1000)`; the engine reads `result.num_output_rows` for its balance check.
- **Counter-examples:** do **not** return `df.count()` or `rows_read` as the metric (return the **commit's** `numOutputRows`); do **not** retry the append (a partial commit is atomic - re-running duplicates data).

## 11. Regeneration contract
`scaffold-then-edit`: the class + `apply` skeleton are fully generated; the Spark write and the version-bracketed metric read are generated then reviewed against current Delta APIs.

## 12. References
`specs/foundation/contracts-spec.md` (`LoadStrategy`, `WriteResult` v0.2.0) · `specs/foundation/config-model-spec.md` (`TargetConfig`/`LoadConfig`) · `specs/dataio/schema-evolution-spec.md` (supplies write `options`) · `specs/ingestion/ingestion-engine-spec.md` (caller; reads `WriteResult` for balance) · `skills/_shared/project-structure.md`.
Note: `INGEST-003` is a **new** backlog task - add it to `AI_Ready_Backlog`.
