---
id: dataio.quarantine
title: Quarantine Sink (unified, multi-reason)
owner: EY
status: draft
target_path: src/dataio/quarantine/
owning_skill: framework-dev.build-ingestion-engine
backlog: [INGEST-041]
provides: [QuarantineReason, QuarantineResult, quarantine_table_name, ensure_quarantine_table, write_quarantine]
depends_on: [foundation.contracts, foundation.config-model]
generation_context:
  - specs/foundation/contracts-spec.md
  - specs/foundation/config-model-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/dataio/test_quarantine.py"
  - "python -c 'from dataio.quarantine import QuarantineReason, QuarantineResult, quarantine_table_name, ensure_quarantine_table, write_quarantine'"
regeneration: scaffold-then-edit
---

# Quarantine Sink - Specification

## 1. Purpose & scope
One **shared quarantine sink** that many producers write to, for **all** quarantine reasons - not only schema drift. Schema drift (`dataio.schema-evolution.capture_drift`) is one feeder; readers feed corrupt/cast records; the engine feeds batch-level write/read failures and key violations.
- In scope: the quarantine **table** (name + lazy create), a **reason taxonomy**, and a **writer** that stamps metadata and appends. The table schema is derived from the **payload being quarantined** (+ metadata), never from the target table, and accepts schema drift (`mergeSchema`) so it can never reject data.
- Out of scope: deciding *whether* to quarantine (the producer decides); the ABC audit record (written by the calling engine); record-level vs batch-level policy (the producer chooses what DataFrame to hand in).

## 2. Requirements
**Functional**
- FR-1: `QuarantineReason` enumerates the categories: `SCHEMA_DRIFT`, `CORRUPT_RECORD`, `CAST_FAILURE`, `MISSING_KEY`, `DUP_KEY`, `WRITE_FAILURE`, `READ_FAILURE`.
- FR-2: `quarantine_table_name(target)` -> `{catalog}.{schema}.{table}_quarantine`.
- FR-3: `ensure_quarantine_table(spark, target, payload_schema=None)` creates the table lazily with payload columns (if known) + the fixed metadata columns, partitioned by a **stored** `quarantine_date` column.
- FR-4: `write_quarantine(spark, target, df, reason, run_id, detail="")` stamps metadata, appends with `mergeSchema=true`, returns a `QuarantineResult` with the row count.
- FR-5: A quarantine write **must not silently lose data**; on writer failure it raises `QuarantineWriteError` for the caller to handle (the caller decides whether to suppress the original error).

**Non-functional**: the table accepts any payload schema (drift-tolerant); deterministic table naming; metadata columns are stable; `DataFrame`/`StructType`/`TargetConfig` typing from `core/contracts` + `core/metadata`.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
class QuarantineReason(str, Enum):
    SCHEMA_DRIFT   = "SCHEMA_DRIFT"
    CORRUPT_RECORD = "CORRUPT_RECORD"
    CAST_FAILURE   = "CAST_FAILURE"
    MISSING_KEY    = "MISSING_KEY"
    DUP_KEY        = "DUP_KEY"
    WRITE_FAILURE  = "WRITE_FAILURE"
    READ_FAILURE   = "READ_FAILURE"

@dataclass
class QuarantineResult:
    table: str
    reason: str
    rows: int

class QuarantineWriteError(Exception): ...

# metadata columns added to every quarantined payload
META_COLUMNS = ["quarantine_id", "run_id", "reason_category", "reason_detail",
                "quarantine_timestamp", "quarantine_date"]

def quarantine_table_name(target: "TargetConfig") -> str: ...
def ensure_quarantine_table(spark: "SparkSession", target: "TargetConfig",
                            payload_schema: "StructType | None" = None) -> None: ...
def write_quarantine(spark: "SparkSession", target: "TargetConfig", df: "DataFrame",
                     reason: QuarantineReason, run_id: str, detail: str = "") -> QuarantineResult: ...
```

## 4. Inputs / Outputs
- Input: a `TargetConfig` (for the table name), the `DataFrame` to quarantine, a `QuarantineReason`, a `run_id`, optional `detail`.
- Output: a `QuarantineResult` (`table`, `reason`, `rows`). Side effect: an append to the quarantine Delta table. ABC audit is the **caller's** job (the result gives it the count).

## 5. Design
A single sink with many producers. The table schema = **payload columns of the df being written** + the fixed `META_COLUMNS`; it is created lazily from the first payload and uses `mergeSchema=true` on every write so later payloads with different columns are accepted rather than rejected (quarantine must never lose data). Partitioning is by a **real stored** `quarantine_date` column (not a derived expression). The writer is intentionally small and reason-agnostic; producers map their failure to a `QuarantineReason`. `DataFrame`/`StructType` typing comes from `core/contracts`; `TargetConfig` from `core/metadata`.

### SOLID Principles Application
* **SRP:** the module does one thing - stamp + append quarantined rows; it neither decides to quarantine nor logs ABC.
* **OCP:** new reasons are added to `QuarantineReason` without touching the writer; new producers reuse `write_quarantine` unchanged.
* **LSP:** every producer hands in a `DataFrame` + a `QuarantineReason`; all are written through the same path uniformly.
* **ISP:** producers depend only on `write_quarantine` (+ the enum); they don't see table-creation internals.
* **DIP:** depends on the `TargetConfig` abstraction and `core/contracts` types, not on a concrete catalog/table implementation.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `name = quarantine_table_name(target)` = `{catalog}.{schema}.{table}_quarantine`.
  2. `ensure_quarantine_table(spark, target, df.schema)`: if the table is absent, create it from the payload schema + `META_COLUMNS`, partitioned by `quarantine_date`.
  3. Stamp metadata on the payload: `quarantine_id` (uuid4), `run_id`, `reason_category` (`reason.value`), `reason_detail` (truncated to a max length), `quarantine_timestamp` (now), `quarantine_date` (`to_date(quarantine_timestamp)`).
  4. Append with `.option("mergeSchema","true")` so payload drift is accepted.
  5. Return `QuarantineResult(name, reason.value, count)`. On any failure raise `QuarantineWriteError`.
- **Decision rules:**
  - Table schema source = the **payload** df (+ metadata), **never** the target table (that was the create-vs-write mismatch bug).
  - Partition column = the stored `quarantine_date` column (a real column), not `partitionBy(to_date(...))`.
  - `reason` must be a `QuarantineReason`; `reason_detail` is truncated (e.g. 4000 chars).
  - Writes always use `mergeSchema=true` (accept anything).
- **Key code fragments** (the generated code MUST contain these):
```python
def quarantine_table_name(target):
    return f"{target.catalog_name}.{target.schema_name}.{target.table_name}_quarantine"

def write_quarantine(spark, target, df, reason, run_id, detail=""):
    from pyspark.sql import functions as F
    import uuid
    name = quarantine_table_name(target)
    stamped = (df.withColumn("quarantine_id", F.lit(str(uuid.uuid4())))
                 .withColumn("run_id", F.lit(run_id))
                 .withColumn("reason_category", F.lit(reason.value))
                 .withColumn("reason_detail", F.lit(detail[:4000]))
                 .withColumn("quarantine_timestamp", F.current_timestamp())
                 .withColumn("quarantine_date", F.to_date(F.current_timestamp())))
    ensure_quarantine_table(spark, target, stamped.schema)
    try:
        rows = stamped.count()
        stamped.write.mode("append").option("mergeSchema", "true").saveAsTable(name)
    except Exception as e:
        raise QuarantineWriteError(f"quarantine write failed for {name}: {e}") from e
    return QuarantineResult(name, reason.value, rows)
```
- **Edge cases:** table absent -> created lazily from the payload; **payload schema differs across batches** -> `mergeSchema=true` accepts it; empty df -> 0 rows (no-op write is fine); oversized `reason_detail` -> truncated; quarantine write itself fails -> `QuarantineWriteError` (caller logs + decides, never silently drops); partition column is stored so `OPTIMIZE`/retention work normally.

**Constraints (hard):** payload-derived schema (not target); stored `quarantine_date` partition column; `mergeSchema` on every write; no ABC inside the writer (caller owns it); single package `src/dataio/quarantine/`.

## 7. Validation, edge cases & versioning policy
`META_COLUMNS` is a stable contract - reordering/removing one is breaking (consumers query them). Adding a new `QuarantineReason` is additive. The quarantine table is append-only and drift-tolerant, so payload evolution never requires a rebuild.

## 8. Error handling + ABC instrumentation
No ABC inside the writer - it returns the row count and the **calling engine** logs `rows_rejected` + the reason to ABC. The writer raises `QuarantineWriteError` on failure so the caller can record it and choose whether to suppress the original error; the writer never silently swallows a failed quarantine (that would lose data).

## 9. Testing & acceptance
Unit (mock Spark): `quarantine_table_name` formats correctly; `write_quarantine` stamps all `META_COLUMNS` and returns the right count; two payloads with **different** columns both write (mergeSchema). Integration (Spark): table created lazily, partitioned by `quarantine_date`; a `QuarantineWriteError` is raised when the write fails. Plus front-matter `acceptance`; >80% coverage.

## 10. Examples
- **Schema drift:** `clean, q = capture_drift(df, expected, cfg)` then `write_quarantine(spark, target, q, QuarantineReason.SCHEMA_DRIFT, run_id)`.
- **Corrupt records:** a reader filters `_corrupt_record IS NOT NULL` -> `write_quarantine(..., QuarantineReason.CORRUPT_RECORD, run_id, detail="PERMISSIVE parse")`.
- **Counter-example (what NOT to do):** do not build the quarantine table from the **target** table's schema - derive it from the payload, or a drifting/partial payload won't fit and data is lost.

## 11. Regeneration contract
`scaffold-then-edit`: the enum, table-name, and result types are fully generated; the Spark writer + lazy DDL are generated then reviewed.

## 12. References
`specs/foundation/contracts-spec.md` (DataFrame/StructType) · `specs/foundation/config-model-spec.md` (TargetConfig) · `specs/dataio/schema-evolution-spec.md` (the drift feeder - `capture_drift`) · `specs/ingestion/ingestion-engine-spec.md` (a producer) · `skills/_shared/project-structure.md`.
Note: `INGEST-041` is a **new** backlog task - add it to `AI_Ready_Backlog`.
