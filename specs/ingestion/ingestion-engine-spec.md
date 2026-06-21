---
id: ingestion.engine
title: Ingestion Engine - Batch Orchestrator
owner: EY
status: draft
target_path: src/framework/ingestion/
owning_skill: framework-dev.build-ingestion-engine
backlog: [ING-001]
provides: [IngestionEngine, IngestionConfig, RetryConfig, NullRunHandle, IngestionError, ConfigurationError, TransientError, MaxRetriesExceededError, run_batch_append, validate_config]
depends_on: [foundation.contracts, foundation.abc-sdk, foundation.config-model, dataio.file-readers, dataio.append-strategy, dataio.schema-evolution, dataio.quarantine]
generation_context:
  - specs/foundation/contracts-spec.md
  - specs/foundation/abc-sdk-spec.md
  - specs/foundation/config-model-spec.md
  - specs/dataio/schema-evolution-spec.md
  - specs/dataio/quarantine-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/framework/ingestion/test_engine.py --cov=src/framework/ingestion --cov-fail-under=80"
  - "pytest tests/integration/test_ingestion_batch_append.py"
  - "mypy --strict src/framework/ingestion/"
  - "python -c 'from framework.ingestion import IngestionEngine, IngestionConfig, RetryConfig'"
regeneration: scaffold-then-edit
capability:
  framework: ingestion
  feature: batch-append
  selectable: true
---

# Ingestion Engine - Specification

## 1. Purpose & scope
Orchestrate metadata-driven **batch** ingestion from file sources into Unity Catalog Delta tables, with ABC instrumentation, bounded retry, and quarantine - **delegating** schema-evolution to `dataio.schema-evolution` and the quarantine sink to `dataio.quarantine` rather than reimplementing them.
- In scope: single- and multi-source **append** (Phase 1); config validation; a **real** balance check; retry of the **read**; routing failed/drift/corrupt data to the shared quarantine sink; ABC audit/balance/cost hooks.
- Out of scope: SCD1/2 + MERGE (load-strategy specs); streaming / Auto Loader (declarative track); transformations (harmonization); the schema-evolution decision logic (`dataio.schema-evolution`); the quarantine **table/writer** (`dataio.quarantine`); record-level DQ (deferred).

## 2. Requirements
**Functional**
- FR-1: Fully metadata-driven - no hard-coded catalogs, paths, or formats; everything from `LoadConfig`/`SourceConfig`/`TargetConfig`.
- FR-2: Single-source and multi-source (union) read into one target.
- FR-3: **Append** only (Phase 1); the write is **single-attempt** (never retried) to avoid duplicate data.
- FR-4: **Real balance** - compare source `rows_read` against rows **actually committed** (Delta `operationMetrics.numOutputRows`), not an assumed `rows_written = rows_read`.
- FR-5: Retry only the **idempotent** read, with bounded exponential/linear backoff, on **typed** transient errors.
- FR-6: Delegate schema evolution to `dataio.schema-evolution` (resolve + appliers + `capture_drift`); route drift rows to quarantine.
- FR-7: Delegate quarantine to `dataio.quarantine.write_quarantine(...)` with a `QuarantineReason` (`WRITE_FAILURE`, `READ_FAILURE`, `SCHEMA_DRIFT`, `CORRUPT_RECORD`, ...).
- FR-8: ABC instrumentation; **governed feeds** (`abc_required=True`) fail if ABC cannot record; others degrade via `NullRunHandle`.

**Non-functional**: idempotent re-runs are the load-strategy's job; mypy `--strict`, no `Any` in public signatures; >80% coverage; ABC logging never crashes the run (except the governed-feed gate).

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
class IngestionError(Exception): ...
class ConfigurationError(IngestionError): ...
class TransientError(IngestionError): ...            # base for retryable errors (readers/strategies raise this)
class MaxRetriesExceededError(IngestionError): ...

@dataclass
class NullRunHandle:                                  # used only when ABC is unavailable AND not required
    run_id: str = "UNKNOWN"
    trace_id: str = "UNKNOWN"

@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff: str = "exponential"                      # "exponential" | "linear"
    initial_delay_sec: float = 1.0
    max_delay_sec: float = 60.0
    multiplier: float = 2.0

@dataclass
class IngestionConfig:
    load: LoadConfig
    sources: list[SourceConfig]
    target: TargetConfig
    retry: Optional[RetryConfig] = None
    enable_quarantine: bool = True
    abc_required: bool = False                        # governed feeds: fail if ABC can't record
    validate_source_format: bool = True

    @classmethod
    def from_params(cls, params: dict) -> "IngestionConfig": ...   # build NESTED dataclasses (not **params)

class IngestionEngine:                                # implements core.contracts.Engine
    def __init__(self, spark: "SparkSession", abc: "ABC",
                 reader: "Reader", strategy: "LoadStrategy") -> None: ...
    def run(self, context: RunContext) -> RunResult: ...               # Engine protocol entry
    def run_batch_append(self, config: IngestionConfig, run_handle) -> RunResult: ...
    def validate_config(self, config: IngestionConfig) -> None: ...     # fail fast
    # private: _read_sources, _retry_read, _measure_landed, _safe_abc, _classify
```
Constructor uses duck-typing (`hasattr(reader, "read")`, `hasattr(strategy, "apply")`), not `isinstance`, for protocol checks.

## 4. Inputs / Outputs
- Input: `RunContext` (component, entity, run_type, params); params -> `IngestionConfig.from_params`. Data: file sources (CSV/JSON/Parquet/Delta) on UC Volumes or cloud storage.
- Output: a Delta append to the target; quarantine rows via `dataio.quarantine`; ABC records (audit/balance/cost); a `RunResult(status, metrics, run_id)`.

## 5. Design
Dependency injection: `Reader`, `LoadStrategy`, `ABC` are injected; schema-evolution and quarantine are called as their module contracts (mockable). The engine is a thin orchestrator - it does not read, write, evolve schema, or own the quarantine table.

Flow (batch append): `from_params -> validate_config -> ABC.start_run -> _retry_read (materialized) -> [schema-evolution: resolve + validate_schema_compatibility + capture_drift] -> strategy.apply (single attempt) -> _measure_landed (Delta numOutputRows) -> balance(rows_read vs landed) -> ABC.cost/end`. Drift rows from `capture_drift`, corrupt rows from the reader, and a failed write all route to `dataio.quarantine.write_quarantine(reason=...)`.

**Real balance** replaces the old tautology: `rows_written` is read from the append commit's `operationMetrics.numOutputRows`, so the balance can actually detect under/over-writes.

### SOLID Principles Application
* **SRP:** the engine only orchestrates; reading, writing, schema evolution, and quarantine each live in their own component.
* **OCP:** new load patterns add a `LoadStrategy`; new sources add a `Reader`; new quarantine reasons live in `dataio.quarantine` - all without engine changes.
* **LSP:** any `Reader`/`LoadStrategy` honoring its protocol is substitutable; the engine never branches on concrete types.
* **ISP:** the engine calls only `Reader.read`, `LoadStrategy.apply`, the ABC methods it uses, and the two delegate entry points.
* **DIP:** depends on the `Reader`/`LoadStrategy` protocols and the schema-evolution/quarantine contracts, not concrete implementations (all injectable/patchable for tests).

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `config = IngestionConfig.from_params(context.params["config"])` - builds the **nested** `LoadConfig`/`SourceConfig`/`TargetConfig` (never `IngestionConfig(**dict)`).
  2. `validate_config(config)` - fail fast (required fields, catalog/schema exist, source paths + format, `load_pattern == "APPEND"`, retry config sane).
  3. Start ABC: `run_handle = abc.start_run(...)`; on failure, if `abc_required` -> raise, else `run_handle = NullRunHandle()`.
  4. `df = _retry_read(lambda: _read_sources(config), config)` - the read is **materialized inside** the retry (`cache()` + `count()`), so transient read errors are actually caught and retried.
  5. Schema evolution (delegated): `cfg = resolve_schema_evolution(ctx)`; `validate_schema_compatibility(df.schema, target_schema, cfg)`; if drift handling applies, `clean, drift = capture_drift(df, expected, cfg)` and `write_quarantine(spark, target, drift, SCHEMA_DRIFT, run_id)`; apply `delta_table_properties`/`delta_write_options(cfg)` to the write.
  6. `strategy.apply(clean, target, load)` - **single attempt** (append is not idempotent; never retried).
  7. `landed = _measure_landed(target)` (Delta `numOutputRows`); `rows_read = df.count()` (already materialized).
  8. Balance: `delta = rows_read - landed`; `reconciliation = "PASS" if delta == 0 else "FAIL"`; log to ABC.
  9. Cost: log duration; DBU/$ deferred (Phase 2) - recorded explicitly as `0.0` with a `cost_estimated=False` flag (no fake numbers).
  10. `ABC.end_run(status)`; return `RunResult`.
  On a **write** failure: `write_quarantine(spark, target, clean, WRITE_FAILURE, run_id, detail=str(e))` (if `enable_quarantine`), then re-raise.
- **Decision rules:**
  - Retry **iff** the error is a `TransientError` (typed) - readers/strategies raise it for network/throttle/503; everything else fails fast. No "retry everything not fatal".
  - Retry wraps the **read only**; the **append is single-attempt**.
  - Single vs multi source: `len(sources) == 1` -> direct read; else `unionByName(..., allowMissingColumns=True)` **and** log a `schema_drift` balance note so silent nulls are visible.
  - ABC unavailable: `abc_required` -> raise; else continue with `NullRunHandle` (degraded, audited as such).
- **Key code fragments** (the generated code MUST contain these):
```python
def _retry_read(self, fn, config):                    # retry an IDEMPOTENT, materialized read
    rc = config.retry or RetryConfig()
    for attempt in range(1, rc.max_attempts + 1):
        try:
            df = fn().cache()
            df.count()                                # force execution INSIDE the retry
            return df
        except Exception as e:
            if not isinstance(e, TransientError) or attempt == rc.max_attempts:
                if attempt == rc.max_attempts:
                    raise MaxRetriesExceededError(f"read failed after {attempt} attempts: {e}") from e
                raise
            delay = (rc.initial_delay_sec * rc.multiplier ** (attempt - 1)
                     if rc.backoff == "exponential" else rc.initial_delay_sec * attempt)
            time.sleep(min(delay, rc.max_delay_sec))

def _measure_landed(self, table):                     # rows actually committed (no full scan, no assumption)
    metrics = (self.spark.sql(f"DESCRIBE HISTORY {table} LIMIT 1")
                   .select("operationMetrics").collect()[0][0]) or {}
    return int(metrics.get("numOutputRows", 0))

def _safe_abc(self, fn, *a, **k):                     # logging never crashes the run
    try: fn(*a, **k)
    except Exception as e: print(f"WARNING: ABC logging failed: {e}", file=sys.stderr)
```
- **Edge cases:** empty source -> `rows_read=0`, `landed=0`, balance PASS; **append write fails mid-way** -> NOT retried (no duplicates); the batch routes to quarantine `WRITE_FAILURE` then the error re-raises; multi-source missing columns -> filled null **and** flagged; target table absent -> `strategy.apply` creates it (first write); ABC tables absent -> ABC SDK self-heals, else degraded; `df is not None` guards quarantine (no `'df' in locals()` reflection).

**Constraints (hard):** no hard-coded catalog/path/format; the append is never retried; no fake metrics (cost flagged un-estimated); duck-typed protocol checks; delegate schema-evolution + quarantine (do not reimplement); instrument via ABC.

## 7. Validation, edge cases & versioning policy
`validate_config` fails fast on missing fields, absent catalog/schema, inaccessible/format-mismatched sources, non-`APPEND` patterns (Phase 1), and bad retry config. Adding load patterns/readers is additive (new strategy/reader). Changing the `IngestionConfig` shape is breaking - bump and regenerate. The Delta `operationMetrics` key (`numOutputRows`) is the external contract for balance; pin to current Databricks docs.

## 8. Error handling + ABC instrumentation
Four classes: **Configuration** (fail fast), **Transient** (typed -> retry the read), **Fatal** (fail immediately), **ABC** (log & continue, except the governed gate). ABC calls go through `_safe_abc` so logging never kills the run - **except** when `abc_required=True` and `start_run` fails, which raises (governed feeds must be auditable). Audit points: start; per-source + total `rows_read`; `landed`; balance (`rows_read`, `landed`, `delta`, `reconciliation`); retry attempts (with typed classification); quarantine events (reason + count, from the `QuarantineResult`); end (`status`, `duration_sec`, `cost_estimated=False`).

## 9. Testing & acceptance
Unit (mock Spark/ABC/Reader/Strategy): `from_params` builds nested dataclasses; `validate_config` rejects each bad case; `_retry_read` retries a `TransientError` and gives up after `max_attempts`; a **non-transient** read error is not retried; the **append is never retried** (write raised once -> one call, then quarantine + raise); `_measure_landed` reads `numOutputRows`; balance FAIL when `landed != rows_read`; `abc_required` raises on ABC-start failure; `NullRunHandle` path when not required. Integration (Spark): single- and multi-source append end-to-end; drift -> quarantine `SCHEMA_DRIFT`; write failure -> quarantine `WRITE_FAILURE`. Plus front-matter `acceptance`.

## 10. Examples
- **Single-source append:** read 1 source (retried, materialized) -> apply append once -> `landed = numOutputRows` -> balance PASS -> `RunResult(SUCCESS, {rows_read, rows_written: landed, duration_sec})`.
- **Multi-source union:** read each source, `unionByName(allowMissingColumns=True)`, flag the null-fill, append once, balance against `landed`.
- **Counter-examples (what NOT to do):**
  - Do **not** set `rows_written = rows_read` for the balance check - measure `numOutputRows` (the old version made balance always PASS).
  - Do **not** wrap the append in retry - a partial write + retry duplicates data.
  - Do **not** reimplement quarantine or schema evolution here - call `dataio.quarantine` / `dataio.schema-evolution`.

## 11. Regeneration contract
`scaffold-then-edit`: the dataclasses, exceptions, `from_params`, and orchestration are fully generated; the Spark-touching parts (`_read_sources`, `_measure_landed`, the delegate calls) are generated then reviewed against current Delta/Spark APIs.

## 12. References
`specs/foundation/contracts-spec.md` (Engine/Reader/LoadStrategy, RunContext/RunResult) · `specs/foundation/abc-sdk-spec.md` (ABC) · `specs/foundation/config-model-spec.md` (Load/Source/TargetConfig) · `specs/dataio/schema-evolution-spec.md` (delegated schema evolution) · `specs/dataio/quarantine-spec.md` (delegated quarantine sink) · `skills/_shared/project-structure.md`.
Note: `depends_on` includes forward refs `dataio.file-readers` and `dataio.append-strategy` (corrected single-dot ids) - these resolve once those specs are authored; the validator will flag them until then.
