# Project Structure (FINAL, canonical) - shared

Status: FINAL - 2026-06-18. Standard Databricks Asset Bundle (DAB) layout. Every skill and Genie Code prompt MUST place files per this map. No business-logic `.py` at the repo root.

## Decisions (locked)
- Code under `src/`, on `pythonpath = src`.
- No project-name wrapper and no `sdk/` silo. Top-level packages under `src/` are `core/`, `dataio/`, `services/`, `framework/`, `runners/`, `agents/`.
  - `core/` = foundation libs: `contracts`, `metadata`/`config`, `common`.
  - `dataio/` = reusable primitives + shared policy: `readers`, `load_strategy`, `schema_evolution`, `quarantine`, `checks`, `maskers`, `transform`.
  - `services/` = cross-cutting services: `abc` (audit/balance/control), `observability`, `finops`.
  - `framework/` = metadata-driven engines (the orchestrators).
  - `runners/` = thin entrypoints invoked by jobs/pipelines. (Named `runners`, not `entrypoints`, to avoid the `entrypoints` PyPI package collision.)
  - `agents/` = agentic control plane: capability registry, router.
- **Two-track flavor placement.** `LoadConfig.engine` (`declarative` | `non_declarative`) selects the flavor. **Decision/policy** modules (schema_evolution, quarantine, checks, maskers, config) live **once** and emit per-track outputs by dispatching on `engine`. **Execution** modules split per track: *non-declarative* = `core/contracts` impls in `dataio/` + `framework/<engine>/` + `resources/jobs/`; *declarative* = Lakeflow `@dlt`/AUTO CDC/`cloudFiles` in `framework/<engine>/declarative/` + `resources/pipelines/`.
- Feed metadata in `conf/metadata/` as JSON; control-table DDL in `conf/ddl/`.
- DAB resources in `resources/` with `jobs/` + `pipelines/` subfolders.
- No wheel: code deploys as workspace files; deps via `requirements.txt` on serverless.

## Layout
```
insurance-lake/
  databricks.yml              # DAB bundle: name, include resources/**, variables, targets dev/staging/prod
  requirements.txt            # dev/test deps (no wheel)
  pytest.ini, README.md, PROJECT_CONTEXT.md
  resources/
    pipelines/                #   *.pipeline.yml (Lakeflow Declarative Pipelines)
    jobs/                     #   *.job.yml (Lakeflow Jobs)
  src/                        # all Python (workspace files; pythonpath=src)
    core/                     #   foundation libs (no sdk silo)
      contracts/              #     typed protocols (Reader/LoadStrategy/Engine) + value objects
      metadata/  (config/)    #     metadata config model + loader
      common/                 #     session, logging, redaction, exceptions
    dataio/                   #   reusable primitives + shared policy (BOTH flavors live here)
      readers/ load_strategy/ schema_evolution/ quarantine/ checks/ maskers/ transform/
    services/                 #   cross-cutting: abc/ (audit/balance/control) observability/ finops/
    framework/                #   metadata-driven engines: ingestion/ harmonization/ dq/ reconciliation/ masking/ ...
      <engine>/               #     NON-declarative (imperative batch Engine.run)
      <engine>/declarative/   #     declarative (Lakeflow @dlt / AUTO CDC / cloudFiles)
    runners/                  #   thin notebook/py entrypoints invoked by jobs & pipelines
    agents/                   #   agentic control plane: capability registry, router
  conf/
    ddl/                      # control-table DDL (.sql)
    metadata/                 # feed metadata as JSON (one file per feed); examples/
    environments/             # per-target params
  tests/                      # pytest, mirrors src: tests/core/, tests/framework/
  specs/                      # portable IP - domain taxonomy (foundation/ ingestion/ ... + _templates/)
  skills/                     # agent skills
  docs/                       # runbooks, data dictionary, ADRs, completion notes
  scratch/                    # experiments (gitignored)
```

## Imports
- `from core.config import ConfigLoader`
- `from services.abc import ABC`
- `from core.common.exceptions import ConfigValidationError`
- `from framework.ingestion import ...`

## Placement rules (where generated files go)
- Foundation lib code -> `src/core/<area>/` (contracts | metadata/config | common); reusable primitives + shared policy -> `src/dataio/<area>/`; cross-cutting services (ABC SDK, observability, finops) -> `src/services/<area>/`.
- Engine code from a `build-<x>-engine` skill -> `src/framework/<x>/` (non-declarative, imperative) **and** `src/framework/<x>/declarative/` (declarative Lakeflow `@dlt`/AUTO CDC).
- **Flavor split:** `LoadConfig.engine` selects the track - decision/policy modules emit both, execution modules split (`resources/jobs/` vs `resources/pipelines/` deploy them).
- Entrypoints (run scripts/notebooks) -> `src/runners/`.
- Lakeflow pipeline defs -> `resources/pipelines/*.pipeline.yml`; Jobs -> `resources/jobs/*.job.yml`.
- Control-table DDL -> `conf/ddl/`; feed metadata (JSON) -> `conf/metadata/`.
- Tests -> `tests/<mirror>/` (`tests/core/`, `tests/framework/<x>/`), files `test_*.py`.
- Specs -> `specs/<domain>/`; docs -> `docs/`; skills -> `skills/`.

## Conventions
- Top-level import names under src are `core`, `framework`, `runners` (chosen to avoid stdlib/PyPI collisions; never name a top-level package `abc`, `config`, `common`, or `entrypoints` directly under src).
- One module per concern; a package (`__init__.py`) per area/engine; re-export public API in package `__init__`.
- snake_case files/modules; PascalCase classes.
- **Spec ids mirror the src package path** (2-3 segments): `core.contracts`, `core.metadata`, `dataio.load_strategy.scd2-strategy`, `dataio.readers.file-readers`.
- Workspace Python modules + Asset Bundles (no wheel); deps via `requirements.txt`.
- Every Genie Code prompt states the exact destination path(s) and cites this file.

## Specs organization
`specs/` is organized by epic domain (`foundation/ ingestion/ harmonization/ quality/ masking/ agentic/ finops/ observability/ orchestration/`) with per-domain READMEs and `_templates/` - see `specs/README.md`. This file is the repo-wide source of truth.
