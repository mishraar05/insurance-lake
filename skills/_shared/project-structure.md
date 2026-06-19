# Project Structure (FINAL, canonical) - shared

Status: FINAL - 2026-06-18. Standard Databricks Asset Bundle (DAB) layout. Every skill and Genie Code prompt MUST place files per this map. No business-logic `.py` at the repo root.

## Decisions (locked)
- Code under `src/`, on `pythonpath = src`.
- No project-name wrapper and no `sdk/` silo. Top-level packages under `src/` are `core/`, `framework/`, `runners/`.
  - `core/` = foundation libs: `config`, `abc` (audit/balance/control), `common`.
  - `framework/` = metadata-driven engines.
  - `runners/` = thin entrypoints invoked by jobs/pipelines. (Named `runners`, not `entrypoints`, to avoid the `entrypoints` PyPI package collision.)
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
      config/                 #     metadata config model + loader
      abc/                    #     ABC SDK (audit/balance/control)
      common/                 #     session, logging, redaction, exceptions
    framework/                #   engines: ingestion/ harmonization/ dq/ reconciliation/ masking/ observability/ finops/
    runners/                  #   thin notebook/py entrypoints invoked by jobs & pipelines
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
- `from core.abc import ABC`
- `from core.common.exceptions import ConfigValidationError`
- `from framework.ingestion import ...`

## Placement rules (where generated files go)
- Foundation lib code -> `src/core/<area>/` (config | abc | common). ABC SDK = `src/core/abc/`.
- Engine code from a `build-<x>-engine` skill -> `src/framework/<x>/`.
- Entrypoints (run scripts/notebooks) -> `src/runners/`.
- Lakeflow pipeline defs -> `resources/pipelines/*.pipeline.yml`; Jobs -> `resources/jobs/*.job.yml`.
- Control-table DDL -> `conf/ddl/`; feed metadata (JSON) -> `conf/metadata/`.
- Tests -> `tests/<mirror>/` (`tests/core/`, `tests/framework/<x>/`), files `test_*.py`.
- Specs -> `specs/<domain>/`; docs -> `docs/`; skills -> `skills/`.

## Conventions
- Top-level import names under src are `core`, `framework`, `runners` (chosen to avoid stdlib/PyPI collisions; never name a top-level package `abc`, `config`, `common`, or `entrypoints` directly under src).
- One module per concern; a package (`__init__.py`) per area/engine; re-export public API in package `__init__`.
- snake_case files/modules; PascalCase classes.
- Workspace Python modules + Asset Bundles (no wheel); deps via `requirements.txt`.
- Every Genie Code prompt states the exact destination path(s) and cites this file.

## Specs organization
`specs/` is organized by epic domain (`foundation/ ingestion/ harmonization/ quality/ masking/ agentic/ finops/ observability/ orchestration/`) with per-domain READMEs and `_templates/` - see `specs/README.md`. This file is the repo-wide source of truth.
