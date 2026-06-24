# ABC Framework - Architecture & Direction (for Genie to implement)

**Purpose:** the single, clear direction Genie Code builds the ABC framework from - the WHAT, the components, the flow, the tables, the contracts. **Not a line-by-line spec.** Platform-neutral (Databricks now; Snowflake / Lakebase later). Decisions locked 2026-06-23. Model source of truth: uploaded `ABC_Framework_Document.docx`; table/column **names verbatim**, only datatypes refactored.

## 1. Two build tracks (both skill/spec-driven, run sequentially)
- **framework-build** - generate the framework code (runners, recorder SDK, config-model, engines, strategies). One-time, then **additive** new capabilities without disturbing the productionized framework.
- **pipeline-build** - a *separate* skill/spec set that **populates ABC Control metadata** (CYC/STEP/JOB CTRL + PARAM + DQ/recon rule tables) per pipeline. Writes **config only - never the RUN tables**. Runs **after** framework-build.
- Therefore the runtime framework is **read-only on config**; pipeline-build is the author.

## 2. Runtime execution model
Entry = a **DAB job** whose yaml hardcodes the cycle: `run(cyc_sk)`.
```
DAB yaml (cyc_sk) -> CycleRunner -> StepRunner -> JobRunner -> JobHandler[JOB_TYP_CD]
```
- **CycleRunner**(cyc_sk): read cycle config; `cycle_start` (append 'I' to ABC_CYC_RUN); run its steps; `cycle_end` ('S'/'F').
- **StepRunner**(step): `step_start`; run its jobs; `step_end` ('F' if any job failed). Steps run **sequentially OR in parallel - per config**.
- **JobRunner**(job): `job_start` ('I'); dispatch by `JOB_TYP_CD` -> handler; `job_end` ('S'/'F' + record counts / ERR_MSG / THROUGHPUT). Jobs run **sequentially OR in parallel batches - per config**; on restart, **only failed jobs** re-run.
- RUN tables are **append-only** status events (an 'I' row, then a separate 'S'/'F' row).

## 3. Components & placement
| Component | Role | Location |
|---|---|---|
| CycleRunner / StepRunner / JobRunner | the ABC **orchestrator** (drives Cycle-Step-Job) | `src/runners/` |
| ABC recorder SDK | **records** RUN events; `*_start`/`*_end`; reads config via ConfigLoader | `src/core/sdk/` |
| ConfigLoader + typed models + ControlStore | the **Control plane** (read-only, validation-on-read) | `src/core/metadata/` |
| JobHandlers (one per job type) | the actual work; **self-register** under `JOB_TYP_CD` | `src/framework/<type>/` |
| Load strategies | Append / SCD2 / Merge / Overwrite writers | `src/dataio/load_strategy/` |
| DQ + Recon shared services | used **in-motion** (by engines) **and at-rest** (as jobs) | `src/framework/dq`, `src/framework/reconciliation` |

ABC = orchestrator (runners) + recorder (SDK): one framework, internally split. ABC imports **no** concrete engine - it dispatches via the registry.

## 4. Job types (`JOB_TYP_CD`)
`INGESTION` | `CURATION` (silver + gold transform) | `DQ_AT_REST` | `RECON_AT_REST`. Plus **in-motion** DQ and Recon - the same DQ/Recon services invoked inline by the ingestion/curation handlers as data flows. Each job type = one registered **JobHandler** (the `Engine` protocol in `core/contracts`). Curation/Transformation is its **own cycle or step** (pipeline design, at the client architect's discretion).

## 5. Dispatch
**Hybrid registry + `JOB_TYP_CD`:** handlers self-register under a logical name; the JobRunner selects among registered handlers; ABC imports no engine. Within a load, the **two-track engine** still applies: `DECLARATIVE` (Lakeflow + Auto Loader) vs `NON_DECLARATIVE` (classic batch + Delta MERGE).

## 6. ABC tables
- **Control (config, SCD2, authored by pipeline-build):** `ABC_CYC_CTRL_TBL`, `ABC_STEP_CTRL_TBL`, `ABC_JOB_CTRL_TBL`, `ABC_JOB_PARAM_TBL` (zoned EAV: source / target / load / **curation / transform**), `ABC_SRC_CTRL_TBL` (reusable source + watermark), **`ABC_DQ_RULE_TBL`**, **`ABC_RECON_RULE_TBL`** (dedicated rule definitions).
- **Audit / Run (append-only, written at runtime):** `ABC_CYC_RUN_TBL`, `ABC_STEP_RUN_TBL`, `ABC_JOB_RUN_TABLE`; plus `ABC_BUS_DAY_TBL` (extract window).
- **Balance:** `THROUGHPUT` flag on `ABC_JOB_RUN_TABLE` + a `JOB_TYP_CD='RECON'` job. **Cost:** deferred (AI + compute).
- Names **verbatim** from the doc; new tables (`ABC_DQ_RULE_TBL`, `ABC_RECON_RULE_TBL`) follow the `ABC_*_TBL` style.

**Datatype refactor (names unchanged, fix wrong types):** `ERR_MSG` -> STRING; `THROUGHPUT` -> BOOLEAN; `RCRD_*_CNT` / `DATA_READ` / `DATA_WRITTEN` -> BIGINT; `JOB_STRDT_TM` / `JOB_ENDDT_TM` -> TIMESTAMP; `STEP_RUN_SK` (in job-run) -> INTEGER; `CURR_FLG` -> BOOLEAN (or keep legacy Y/N). Append-only RUN needs a PK that isn't `*_RUN_SK` alone (composite or an event surrogate).

## 7. Config model (Control plane)
- Typed Pydantic models + enums + cross-field validators are the **contract**; engines stay typed.
- Stored as **zoned EAV** in `ABC_JOB_PARAM_TBL` (source / target / load / curation / transform); complex values **JSON-encoded**; **source by reference** (`SRC_SK` -> `ABC_SRC_CTRL_TBL`). **DQ/recon configs come from their dedicated tables**, not PARAM.
- **Validation-on-read** at `ConfigLoader`; **read-only** at runtime; resolves the **whole cycle tree** from `cyc_sk` (cycle -> steps -> jobs -> params).
- **`ControlStore` port** = platform neutrality: one implementation per platform (Databricks Spark/Delta, Snowflake Snowpark/SQL, Lakebase/Postgres SQL). The loader's logic is **platform-neutral** (algorithm, not platform API).
- Enum values grounded in the readers / load_strategy families + the two-track decision (confirm/extend per domain).

## 8. Cross-cutting
- **Platform-neutral:** direction expresses the **algorithm**, not platform code; platform binding is via ports + at generation time (Databricks / Snowflake / Lakebase).
- **Status** `I`/`S`/`F`; keys `{JOB_SK}_int`; `trace_id` for end-to-end lineage.

## 9. Open / deferred
- Balance detail table (THROUGHPUT-only vs a variance/threshold store).
- Cost (AI + compute) at job-run grain - later.
- Lakebase (Postgres) Control-plane store - later.

## 10. framework-build order (then pipeline-build)
`core.contracts` -> `core.metadata` (config-model + ControlStore) -> `core.sdk` (recorder) -> `runners` (cycle/step/job) -> dispatch registry -> handlers (ingestion, curation, dq, recon) -> load strategies. **Then** the separate **pipeline-build** track authors the metadata.