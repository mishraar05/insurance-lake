---
id: ingestion.engine
title: Ingestion Engine - Batch Orchestrator
owner: EY
status: draft
target_path: src/framework/ingestion/
owning_skill: framework-dev.build-ingestion-engine
backlog: [ING-001]
provides: [IngestionEngine, IngestionConfig, RetryConfig, NullRunHandle, IngestionError, ConfigurationError, TransientError, MaxRetriesExceededError, run_batch_append, validate_config]
depends_on: [core.contracts, foundation.abc-sdk, core.metadata, dataio.readers.file-readers, dataio.load_strategy.append-strategy, dataio.schema-evolution, dataio.quarantine]
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
Orchestrate metadata-driven **batch** ingestion from file sources into Unity Catalog Delta tables, with ABC instrumentation, bounded retry, and quarantine - **delegating** schema-evolution to `dataio.schema-evolution` and the quarantine sink to `dataio.quarantine`. This is the **non-declarative** (batch) engine; `engine="non_declarative"` is fixed.
- In scope: single/multi-source **append** (Phase 1); config validation; the **schema-evolution handshake**; a **real** balance check from the write result; retry of the **read**; routing failed/drift/corrupt data to the shared quarantine sink; ABC audit/balance/cost + **two-phase** schema-decision logging.
- Out of scope: SCD1/2 + MERGE; streaming / Auto Loader (declarative track); transformations; the schema-evolution decision logic; the quarantine table/writer; synchronous HITL approval (the engine **defers**, it does not block).

## 2. Requirements
**Functional**
- FR-1: Metadata-driven - no hard-coded catalogs/paths/formats.
- FR-2: Single- and multi-source append into one target; multi-source schema mismatch requires explicit `allow_source_schema_mismatch` (else fail), and the **union null-fill** is audited.
- FR-3: **Append** only; the write is **single-attempt** (never retried) - no duplicate data.
- FR-4: **Real balance** - `rows_written` comes from `WriteResult.num_output_rows` returned by `strategy.apply` (not `DESCRIBE HISTORY`, not an assumption).
- FR-5: Retry only the **idempotent** read, bounded backoff, on **typed** `TransientError`.
- FR-6: **Schema-evolution handshake** - `_build_resolution_context(config)` -> `resolve_schema_evolution` -> `validate_schema_compatibility` -> branch (reject/defer/apply) -> `delta_table_properties` (ALTER) + `delta_write_options` (write) + `capture_drift`; drift rows -> quarantine.
- FR-7: Delegate quarantine to `dataio.quarantine.write_quarantine(...)` (separate `{table}_quarantine`) with a `QuarantineReason`.
- FR-8: ABC: governed feeds (`abc_required`) fail if `start_run` can't record; mid-run ABC failures degrade (flagged `abc_degraded`). Schema decisions use **two-phase** logging (pending -> applied/failed/deferred) under one `trace_id`.

**Non-functional**: mypy `--strict`, no `Any` in public signatures; >80% coverage; identifiers validated before interpolation into SQL.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
class IngestionError(Exception): ...
class ConfigurationError(IngestionError): ...
class TransientError(IngestionError): ...            # readers/strategies raise this for retryable failures
class MaxRetriesExceededError(IngestionError): ...

@dataclass
class NullRunHandle:                                  # used only when ABC unavailable AND not required
    run_id: str = "UNKNOWN"
    trace_id: str = "UNKNOWN"
    def __bool__(self) -> bool: return False          # so `if run_handle:` detects degraded mode

@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff: str = "exponential"                      # "exponential" | "linear"
    initial_delay_sec: float = 1.0
    max_delay_sec: float = 60.0
    multiplier: float = 2.0                           # > 1.0 for exponential

@dataclass
class IngestionConfig:
    load: LoadConfig
    sources: list[SourceConfig]
    target: TargetConfig
    retry: Optional[RetryConfig] = None
    enable_quarantine: bool = True
    abc_required: bool = False                        # governed feeds: fail if ABC can't start
    allow_source_schema_mismatch: bool = False        # multi-source: opt in to union null-fill
    validate_source_format: bool = True
    cost_usd: Optional[float] = None                  # None until Phase 2 (no fake 0.0)

    @classmethod
    def from_params(cls, params) -> "IngestionConfig": ...   # accepts dict OR IngestionConfig; builds NESTED
                                                              # dataclasses; raises ConfigurationError on missing keys

class IngestionEngine:                                # implements core.contracts.Engine
    def __init__(self, spark: "SparkSession", abc: "ABC",
                 reader: "Reader", strategy: "LoadStrategy") -> None: ...   # hasattr(...) duck-typed checks
    def run(self, context: RunContext) -> RunResult: ...
    def run_batch_append(self, config: IngestionConfig, run_handle) -> RunResult: ...
    def validate_config(self, config: IngestionConfig) -> None: ...
    def _build_resolution_context(self, config: IngestionConfig) -> "ResolutionContext": ...
    # private: _read_sources, _retry_read, _safe_abc
```
Refines two contracts (flagged in section 12): `LoadStrategy.apply(df, target, load, options: dict) -> WriteResult` (returns `num_output_rows`); `core.contracts.WriteResult` is added there.

## 4. Inputs / Outputs
- Input: `RunContext` (params -> `IngestionConfig.from_params`); file sources (CSV/JSON/Parquet/Delta) on UC Volumes / cloud storage.
- Output: a Delta append; quarantine rows via `dataio.quarantine`; ABC audit/balance/cost + two-phase schema-decision records; `RunResult(status, metrics, run_id)`.

## 5. Design
Thin orchestrator with injected `Reader`/`LoadStrategy`/`ABC`; schema-evolution and quarantine called as their module contracts (patchable for tests). The engine never reads, writes, evolves schema, or owns the quarantine table.

**Schema-evolution handshake (the integration contract):**
1. `ctx = _build_resolution_context(config)` - `engine="non_declarative"` fixed; `layer` from `TargetConfig.layer`; `source_system_type`/`governance_tier`/`zero_downtime`/`paranoid`/`type_changes`/`renames_expected`/`dimensional`/`scd_type` from `LoadConfig`/`TargetConfig` where present, else the schema-evolution defaults. (Requires `core.metadata` to expose `layer` + `source_system_type` - see section 12.)
2. `cfg = resolve_schema_evolution(ctx)`; `errs = validate_config(cfg)` (schema-evolution's own conflict guard) -> raise on any.
3. `compat = validate_schema_compatibility(incoming, target_schema, cfg)`:
   - `allowed=False` -> **reject branch**: ABC phase-2 `failed`; quarantine the batch (`SCHEMA_DRIFT`, detail=reasons); do **not** apply. If `requires_rebuild`, surface it in `RunResult`.
   - `cfg.require_approval` -> **defer branch**: ABC phase-1 `pending`; quarantine the batch (`SCHEMA_DRIFT`, detail="awaiting approval"); do **not** apply the change. The engine never blocks - the change applies on a later run after approval.
   - else **apply branch** (below).
4. Apply branch: ALTER the existing target with `delta_table_properties(cfg)` **before** the write (or set them immediately after first-write create); compute `write_options = delta_write_options(cfg)`; if `cfg.capture_drift_to_quarantine`, `clean, drift = capture_drift(df, expected, cfg)` and quarantine `drift` (`SCHEMA_DRIFT`); else `clean = df`.

**Balance** uses `strategy.apply(...).num_output_rows` (the commit's own metric) - immune to the concurrent-write race of `DESCRIBE HISTORY LIMIT 1`.

### SOLID Principles Application
* **SRP:** orchestration only; read/write/schema-evolution/quarantine each live in their own component.
* **OCP:** new patterns add a `LoadStrategy`; new sources add a `Reader`; new quarantine reasons live in `dataio.quarantine` - no engine change.
* **LSP:** any protocol-honoring `Reader`/`LoadStrategy` is substitutable; the engine never branches on concrete types.
* **ISP:** the engine calls only `Reader.read`, `LoadStrategy.apply`, the ABC methods it uses, and the two delegate entry points.
* **DIP:** depends on protocols + the schema-evolution/quarantine contracts, not concrete implementations.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `config = IngestionConfig.from_params(context.params["config"])` (dict or object; nested build; `ConfigurationError` on missing keys).
  2. `validate_config(config)` - fail fast (fields, catalog/schema exist, source paths+format, `APPEND` only, **retry config**: `max_attempts>0`, `initial_delay_sec>=0`, `max_delay_sec>=initial_delay_sec`, `multiplier>1.0` for exponential).
  3. `run_handle = abc.start_run(...)`; on failure -> `raise` if `abc_required` else `NullRunHandle()`.
  4. `df = _retry_read(lambda: _read_sources(config), config)` - materialized **inside** the retry; multi-source uses `unionByName(allowMissingColumns=True)` **only if** `allow_source_schema_mismatch`, else fail; a null-fill is audited (`UNION_NULL_FILL`).
  5. Schema-evolution handshake (section 5) -> `clean` + applied table props/write options, or reject/defer (return early with the quarantine outcome).
  6. `result = strategy.apply(clean, config.target, config.load, options=write_options)` - **single attempt**.
  7. `rows_read = df.count()` (already materialized); `landed = result.num_output_rows`.
  8. Balance: `delta = rows_read - landed`; `reconciliation = "PASS" if delta == 0 else "FAIL"`; log to ABC.
  9. Cost: duration only; `cost_usd=None` (Phase 2). `end_run(status, abc_degraded)`; return `RunResult`.
  On a **write** failure: if `enable_quarantine`, `write_quarantine(spark, target, clean, WRITE_FAILURE, run_id, detail=str(e))`; if that raises `QuarantineWriteError`, `_safe_abc` log it - then **re-raise the original write error** (never hide it behind the quarantine error).
- **Decision rules:**
  - Retry **iff** `isinstance(e, TransientError)`; wraps the **read only**; the append is single-attempt.
  - Compatibility `allowed=False` -> quarantine + no apply; `require_approval` -> defer + quarantine + no apply; else apply.
  - Multi-source mismatch -> fail unless `allow_source_schema_mismatch`; then null-fill + audit.
  - ABC: `abc_required` gates `start_run` only; mid-run failures degrade (`abc_degraded=True`), the run still completes (data > audit-completeness mid-run, and the degradation is itself recorded).
  - Guard quarantine with `df is not None` (never DataFrame truthiness / `locals()`).
- **Key code fragments** (the generated code MUST contain these):
```python
def _build_resolution_context(self, config):
    t, l = config.target, config.load
    return ResolutionContext(
        layer=t.layer, engine="non_declarative",
        source_system_type=getattr(l, "source_system_type", "stable"),
        governance_tier=getattr(l, "governance_tier", "standard"),
        zero_downtime=getattr(l, "zero_downtime", False),
        paranoid=getattr(l, "paranoid", False),
        type_changes=getattr(l, "type_changes", "none"),
        renames_expected=getattr(l, "renames_expected", False),
        dimensional=getattr(t, "dimensional", False),
        scd_type=getattr(l, "scd_type", None))

def _retry_read(self, fn, config):
    rc = config.retry or RetryConfig()
    for attempt in range(1, rc.max_attempts + 1):
        try:
            df = fn().cache(); df.count()                 # force execution INSIDE the retry
            return df
        except Exception as e:
            if not isinstance(e, TransientError):
                raise
            if attempt == rc.max_attempts:
                raise MaxRetriesExceededError(f"read failed after {attempt} attempts: {e}") from e
            delay = (rc.initial_delay_sec * rc.multiplier ** (attempt - 1)
                     if rc.backoff == "exponential" else rc.initial_delay_sec * attempt)
            time.sleep(min(delay, rc.max_delay_sec))

# balance from the write's own metric (no DESCRIBE HISTORY race):
result = self.strategy.apply(clean, config.target, config.load, options=write_options)
landed = result.num_output_rows
```
- **Edge cases:** empty source -> `rows_read=0`, `landed=0`, balance PASS (guarded by `df is not None`, never `if df:`); **append fails mid-commit** -> Delta leaves the table consistent (atomic commit), NOT retried, failed rows reprocessed from source; **quarantine write fails** -> log via `_safe_abc`, re-raise the **original** error; compatibility reject/defer -> batch quarantined, change not applied; multi-source mismatch without opt-in -> `ConfigurationError`; large reads -> `cache()` may be `persist(DISK_ONLY)` to avoid OOM.

**Constraints (hard):** no hard-coded catalog/path/format; append never retried; no fake metrics (`cost_usd=None`); duck-typed protocol checks; delegate schema-evolution + quarantine; validate identifiers before SQL interpolation; instrument via ABC.

## 7. Validation, edge cases & versioning policy
`validate_config` is fail-fast (fields, catalog/schema existence, source access+format, `APPEND`-only, retry sanity). Adding load patterns/readers is additive. Breaking changes: `IngestionConfig` shape, and the `LoadStrategy.apply -> WriteResult` contract (section 12). External contracts to pin: Delta commit `num_output_rows`; current Auto Loader/Delta option names (via the delegate). **Config-model requirement:** `TargetConfig.layer` and `LoadConfig.source_system_type` (+ optional governance fields) must exist for `_build_resolution_context`; absent optionals fall back to schema-evolution defaults.

## 8. Error handling + ABC instrumentation
Classes: **Configuration** (fail fast), **Transient** (typed -> retry read), **Fatal** (fail now), **ABC** (degrade via `_safe_abc`, except the `start_run` gate). **Two-phase schema-decision logging** under one `trace_id`: phase-1 `decision`(`pending`) before apply (or before defer/reject); phase-2 terminal `applied`/`failed`/`deferred` after. Audit points: start; per-source + total `rows_read`; `landed`; balance (`rows_read`,`landed`,`delta`,`reconciliation`); retry attempts (typed); quarantine events (reason + count from `QuarantineResult`); union null-fill; end (`status`,`duration_sec`,`cost_usd=None`,`abc_degraded`). Governed feeds: `abc_required=True` makes a failed `start_run` fatal; a mid-run ABC failure sets `abc_degraded=True` but does not lose data.

## 9. Testing & acceptance
Unit (mock Spark/ABC/Reader/Strategy): `from_params` builds nested dataclasses from a dict AND passes through an object, raising `ConfigurationError` on a missing `load`; `validate_config` rejects each bad case incl. retry config; `_build_resolution_context` maps fields + fixes `engine="non_declarative"`; `_retry_read` retries `TransientError`, gives up after `max_attempts`, does **not** retry a non-transient error; the **append is called once** even when it raises (then quarantine + re-raise original); balance uses `result.num_output_rows` and FAILs when `landed != rows_read`; compatibility `allowed=False` -> quarantine + no apply; `require_approval` -> defer + quarantine; multi-source mismatch without opt-in -> `ConfigurationError`; `abc_required` raises on ABC-start failure; `NullRunHandle.__bool__ is False`. Integration (Spark): single/multi-source append; drift -> `SCHEMA_DRIFT` quarantine; write failure -> `WRITE_FAILURE` quarantine. Plus front-matter `acceptance`.

## 10. Examples
- **Single-source append:** retry-read (materialized) -> apply once -> `landed = result.num_output_rows` -> balance PASS -> `RunResult(SUCCESS, {rows_read, rows_written: landed, duration_sec})`.
- **Bronze volatile with drift:** `_build_resolution_context` -> `resolve` (rescue/capture mode) -> compatibility allowed -> `clean, drift = capture_drift(df, expected, cfg)` -> apply `clean` once -> quarantine `drift` (`SCHEMA_DRIFT`) -> balance on `clean` only.
- **Governed change pending approval:** `cfg.require_approval` -> ABC phase-1 `pending` -> quarantine batch (await approval) -> run completes without applying; the change lands on a later approved run.
- **Counter-examples:** do **not** set `rows_written = rows_read`; do **not** retry the append; do **not** reimplement quarantine/schema-evolution; do **not** read balance from `DESCRIBE HISTORY LIMIT 1` (race).

## 11. Regeneration contract
`scaffold-then-edit`: dataclasses, exceptions, `from_params`, `_build_resolution_context`, and orchestration are fully generated; the Spark-touching parts and the delegate calls are generated then reviewed against current Delta/Spark APIs.

## 12. References
`specs/foundation/contracts-spec.md` (Engine/Reader/LoadStrategy, RunContext/RunResult; **must add `WriteResult` + refine `LoadStrategy.apply(df, target, load, options) -> WriteResult`**) · `specs/foundation/abc-sdk-spec.md` (ABC, two-phase) · `specs/foundation/config-model-spec.md` (**must expose `TargetConfig.layer`, `LoadConfig.source_system_type`**) · `specs/dataio/schema-evolution-spec.md` (the handshake) · `specs/dataio/quarantine-spec.md` (delegated sink) · `skills/_shared/project-structure.md`.
Note: `depends_on` keeps forward refs `dataio.readers.file-readers` + `dataio.load_strategy.append-strategy` (single-dot ids); the validator flags them until authored - that is the intended signal, not a `pending_deps` field.
