# ABC Framework — Mapping & Decisions

**Status:** decisions locked 2026-06-23. Basis for rewriting `config-model-spec` (the Control plane) and `abc-sdk-spec` (orchestrator + recorder). Model source of truth: uploaded `ABC_Framework_Document.docx` (Feb 2025). **Names kept verbatim from the doc; only datatypes refactored** where wrong. Storage modernized to Databricks / Unity Catalog.

## 1. ABC = Audit · Balance · Control (· Cost, later)
- **Control** = the configuration metadata that drives execution. Tables: `ABC_CYC_CTRL_TBL`, `ABC_STEP_CTRL_TBL`, `ABC_JOB_CTRL_TBL`, `ABC_JOB_PARAM_TBL`, `ABC_SRC_CTRL_TBL` (all SCD2). **The typed config-model IS this pillar.**
- **Audit** = what ran. Tables: `ABC_CYC_RUN_TBL`, `ABC_STEP_RUN_TBL`, `ABC_JOB_RUN_TABLE` (append-only). Status, timings, record counts, errors, DQ results.
- **Balance** = did it tie out. `THROUGHPUT` flag on `ABC_JOB_RUN_TABLE`, driven by a `JOB_TYP_CD='RECON'` job. (Optional detailed balance store can be added later — the old SDK's `abc_balance`; the doc itself only carries the flag.)
- **Cost** = deferred. A cost table at job-run grain for **AI cost + compute cost** (future).

## 2. Locked decisions
| Topic | Decision |
|---|---|
| Grain | one entity/table load = **Job**; Step = layer-to-layer group of jobs; Cycle = workstream |
| Role | **ABC is both orchestrator and recorder** — drives the Cycle▸Step▸Job state machine (sequential steps; jobs in parallel **batches of 20**; restart **only failed** jobs) *and* writes CTRL/RUN. No separate runner. |
| Dispatch | each Job's task is resolved by `JOB_TYP_CD` to a registered **engine/handler** (ingestion, harmonization, dq, recon). **Hybrid registry + config**: engines self-register under a logical name; `JOB_TYP_CD` picks among registered handlers; contract = `JobHandler` (reuse the `Engine` Protocol) in `core/contracts`; ABC imports no concrete engine. ABC calls it, captures metrics, closes the job. |
| RUN persistence | **append-only status events** — an `I` row at start, a separate `S`/`F` row at end. `*_RUN_SK` is the grouping key, so the PK is composite (`*_RUN_SK` + `*_STS_CD` + `AUD_DT_TM`) or a new event surrogate — *structural, not a rename*. |
| Storage | **Delta in Unity Catalog** now; `PL_RUN_ID` carries the Databricks job/run id. **Lakebase (Postgres) a future option**, esp. for the SCD2 Control plane. |
| Config authoring | SDK is **read-only on Control config**; CTRL+PARAM rows authored elsewhere (config process / migration / UI). One config-model `load` → one `ABC_JOB_CTRL_TBL` row + its `ABC_JOB_PARAM_TBL` rows. |
| Naming | **keep the doc's table + column names verbatim**; only refactor datatypes (see §5). Status values stay `I`/`S`/`F`. |

## 3. Control plane = the config-model, stored in PARAM
- All Source/Target/Load config persists as **zoned EAV rows** in `ABC_JOB_PARAM_TBL` (`PARAM_ZONE` ∈ source/target/load, `PARAM_NM`, `PARAM_VAL`), SCD2. `PARAM_NM` = the config-model field name (e.g. `load_pattern`, `merge_keys`); complex values (lists, option dicts) are **JSON-encoded** in `PARAM_VAL`; scalars plain.
- **Source by reference:** a job's PARAM carries a `SRC_SK` pointer; source identity + watermark/CDC live once in reusable `ABC_SRC_CTRL_TBL`. No per-job duplication. (The doc has a source registry but no target registry — targets stay in PARAM zone=target unless we add one.)
- **Validation-on-read:** `ConfigLoader` reads a job's PARAM rows, coerces + validates (enums + cross-field rules) via the Pydantic models, returns typed `SourceConfig`/`TargetConfig`/`LoadConfig`. Engines stay typed and unchanged.
- Config-model Pydantic field names (snake_case) are a separate namespace from the ABC table column names (doc’s); both kept as-is.

## 4. Existing (old flat ABC SDK) → new
| Old | New |
|---|---|
| `RunHandle.run_id` (UUID) | `JOB_RUN_SK` = `{JOB_SK}_int` (+ optional `trace_id` column added for cross-grain lineage) |
| `start_run(component, entity, run_type)` | `cycle_start` / `step_start` / `job_start`; job_start writes the `I` event |
| `end_run(run_id, status)` | `job_end` writes the `S`/`F` event + audit counts; step/cycle roll-up |
| `log_audit(metrics)` | audit columns on `ABC_JOB_RUN_TABLE` (`RCRD_READ_CNT`/`RCRD_LD_CNT`/`RCRD_INS_CNT`/`RCRD_UPD_CNT`, `DATA_READ`/`DATA_WRITTEN`, `AUD_DT_TM`) |
| `log_balance(checks)` | `THROUGHPUT` on `ABC_JOB_RUN_TABLE`; recon = `JOB_TYP_CD='RECON'` job |
| `log_dq(results)` | DQ **results** → Audit (run history); DQ **rule defs** → Control (config) |
| `log_exception(error)` | `ERR_MSG` on `ABC_JOB_RUN_TABLE` (+ status `F`) |
| `log_cost(consumption)` | deferred cost table (AI + compute) |
| `abc_audit` (fused config+run) | split → `ABC_JOB_CTRL_TBL` (static config) + `ABC_JOB_RUN_TABLE` (append-only history) |
| — | NEW: cycle & step grains, CTRL/RUN split + SCD2, `ABC_SRC_CTRL_TBL`, `ABC_BUS_DAY_TBL`, `ABC_JOB_PARAM_TBL` |

**Kept strengths:** idempotent-safe + non-blocking + local fallback; typed exceptions; `trace_id` lineage (added column); SDK-as-sole-writer.

## 5. Datatype refactor (column names unchanged)
Fix only the doc's wrong/oversized types; **names stay exactly as the doc**.
- `ERR_MSG`: `INTEGER` → **STRING** (it's an error message)
- `THROUGHPUT`: `INTEGER` → **BOOLEAN** (balanced-or-not flag; name kept though it reads oddly)
- `DATA_READ` `VARCHAR(20)` / `DATA_WRITTEN` `VARCHAR(1)` → **BIGINT** (byte sizes)
- `RCRD_READ_CNT` / `RCRD_LD_CNT`: `VARCHAR(100)` → **BIGINT**; `RCRD_INS_CNT` / `RCRD_UPD_CNT`: `INTEGER` → **BIGINT** (avoid overflow on large loads)
- `JOB_STRDT_TM` `VARCHAR(255)` / `JOB_ENDDT_TM` `VARCHAR(20)` → **TIMESTAMP**
- `JOB_STS_CD` `VARCHAR(100)` → **VARCHAR(1)/STRING** (status code `I`/`S`/`F`)
- `STEP_RUN_SK` in `ABC_JOB_RUN_TABLE` `VARCHAR(70)` → **INTEGER** (FK must match `ABC_STEP_RUN_TBL.STEP_RUN_SK`)
- SCD2 `CURR_FLG` `VARCHAR(1)` → **BOOLEAN** (optional; keep `Y`/`N` string if you prefer the legacy convention)
- `PL_RUN_ID` stays **STRING** (now holds the Databricks job/run id — value change, not a rename)

## 6. Open / deferred
- **JobHandler dispatch** — DECIDED: hybrid registry + config (engines self-register under a logical name; `JOB_TYP_CD` selects; contract = `JobHandler` ≈ the `Engine` Protocol, in `core/contracts`; ABC imports no engine). Handler returns a `JobResult`/`RunResult` carrying the audit counts ABC writes.
- **Cost** — AI (tokens/$) + compute (DBU/$) at job-run grain; not now.
- **Lakebase** — future store for the Control plane (Postgres/OLTP fit for SCD2 + point reads).
- **Balance detail table** — keep just `THROUGHPUT`, or add a variance/threshold store (old `abc_balance`)?

## 7. Next steps
1. Rewrite `config-model-spec` → Control plane: PARAM-backed storage, source by reference, validation-on-read `ConfigLoader`.
2. Rewrite `abc-sdk-spec` → orchestrator + recorder over Cycle▸Step▸Job, append-only RUN, SCD2 Control read, dispatch-by-`JOB_TYP_CD`.
3. Regenerate from the hardened specs, one component at a time, lint backstop on.
