# ABC Framework - Genie build prompt (direction-driven)

**Source of truth:** `docs/ABC-MAPPING.md` (the direction). Genie builds the framework from it, **one component at a time**. Set Genie Code to **Ask-first** approval so it pauses before every write/run, and open it in the repo Git folder.

## Build order (framework-build; pipeline-build comes after)
1. `core.contracts` -> `src/core/contracts/` (Protocols incl. `Engine`/`JobHandler`, value objects)
2. `core.metadata` -> `src/core/metadata/` (typed config-model + enums + validators + `ControlStore` port + **read-only** `ConfigLoader`)
3. `core.sdk` -> `src/core/sdk/` (ABC **recorder**: `cycle/step/job_start|end`, **append-only** RUN writes)
4. `runners` -> `src/runners/` (CycleRunner -> StepRunner -> JobRunner; sequential|parallel per config)
5. dispatch registry -> `JOB_TYP_CD` -> JobHandler (self-registration; ABC imports no engine)
6. handlers -> `src/framework/{ingestion,curation,dq,reconciliation}/`
7. load strategies -> `src/dataio/load_strategy/` (Append / SCD2 / Merge / Overwrite)

## The prompt - paste into Genie (Ask-first), then drive component by component
```
You are building the InsureLake ABC framework strictly from ONE direction document:
docs/ABC-MAPPING.md. That doc is the ONLY source of truth for architecture, components,
folder placement, contracts, tables (names verbatim), and the cross-cutting rules.
Do NOT invent architecture, folders, or table/column names. Use ONLY the layout in the
"Components & placement" table - never src/sdk, src/orchestration, or src/engines.

Rules:
- Build ONE component at a time, in the "framework-build order". Do not start the next
  until I say "next".
- Platform-neutral: implement the behaviour the direction describes; put platform-specific
  code (Spark/Delta) ONLY behind the ControlStore / handler ports. Target platform = Databricks first.
- Read-only at runtime: the config-model loader never writes config (only the pipeline-build
  track authors config). Do not add write paths or RUN-table writes to the config-model.
- Code style: PEP 8, Google-style docstrings on every public module/class/function, type hints;
  ruff and black must pass.
- If the direction is missing or ambiguous for anything you need, add it to a `## DIRECTION GAPS`
  list and STOP. Do not guess - I will enrich docs/ABC-MAPPING.md.

Two phases per component:
- PHASE 1 (no code): read docs/ABC-MAPPING.md, then for the named component output
  (a) a `## DIRECTION GAPS` list (or "NO GAPS"), and (b) the proposed PUBLIC INTERFACE
  (classes/functions/signatures) + the exact files you will create at the direction's
  placement. Then STOP for my approval.
- PHASE 2 (only after I say "go"): generate the component + a smoke/unit test, full docstrings,
  ruff/black clean. List every file written + the command to run the test. Then STOP for review;
  do NOT proceed to the next component.

Start with component 1: core.contracts (src/core/contracts/). PHASE 1 only.
```

## How to drive it
1. Paste the prompt -> Genie returns Phase 1 (gaps + proposed interface) for `core.contracts`. **No code yet.**
2. If there are gaps, **enrich `docs/ABC-MAPPING.md`** yourself (don't let Genie invent), then tell it to re-run Phase 1.
3. When the interface looks right, say **"go"** -> Genie generates Phase 2 (code + test), ruff/black clean.
4. Review, run the test, then say **"next"** to move to `core.metadata` (Phase 1) - and so on down the build order.

## If it drifts
- Re-point it at `docs/ABC-MAPPING.md` + the "Components & placement" table; reject any `src/sdk`/`src/orchestration`/`src/engines` layout or invented table names.
- Keep it to **one** component, **Phase 1 first** - never "build the framework".
