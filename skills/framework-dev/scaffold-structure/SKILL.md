---
id: framework-dev.scaffold-structure
name: scaffold-structure
category: framework-dev
version: 0.1.0
maturity: active
status: active
owner_role: Platform/DevOps
runtime: genie-code
build_order: 0
depends_on: []
backlog_ids: ['FND-030']
inputs: ['repo_root']
outputs: ['directory_tree', 'placement_rules']
tools: ['genie-code']
---

# scaffold-structure

> Define, create and enforce the canonical Databricks Asset Bundle layout so every generated file lands in a predictable place.

## Purpose / when to use
Run first (Wave 0) and reference from every other skill and Genie Code prompt. It is the single source of truth for where code, pipelines, DDL, metadata, tests and docs live - the fix for scattered `.py` files when specs are generated in Databricks.

## Inputs (contract)
- `repo_root` - the insurance-lake workspace / Git folder (the DAB bundle root).

## Procedure (Genie-Code-ready steps)
1. Read the canonical layout in `_shared/project-structure.md`.
2. Create any missing directories (`__init__.py` for Python packages, `.gitkeep` for empty asset dirs).
3. Resolve every artifact's destination from the placement rules: SDK -> `src/core/<area>/`; engines -> `src/framework/<x>/`; entrypoints -> `src/runners/`; pipelines/jobs -> `resources/pipelines|jobs/`; DDL -> `conf/ddl/`; feed metadata (JSON) -> `conf/metadata/`; tests -> `tests/<mirror>/`.
4. Validate: fail if a generated file would land at the repo root or outside its mapped home.

## Outputs (contract)
- `directory_tree` - the created/validated layout.
- `placement_rules` - the resolved destination for each artifact type.

## Guardrails & policy
- No business-logic `.py` at the repo root.
- Never invent a new top-level folder without updating `_shared/project-structure.md` first.
- Single core/framework package; workspace source + Asset Bundles (no wheel).

## Govern hooks
- Cited by all `framework-dev/*` and `authoring/*` skills; the [[orchestration.router]] passes the resolved destination path into each build step.

## Examples
- build-ingestion-engine output -> `src/framework/ingestion/` + tests in `tests/framework/ingestion/`; its pipeline -> `resources/pipelines/ingestion.pipeline.yml`.
- ABC SDK -> `src/core/abc/`; its tests -> `tests/core/test_abc.py`.

## Acceptance / eval
- Running any build skill places files only in mapped locations; a validation pass reports zero root-level or unmapped source files.

## References
- Backlog: FND-030
- Shared: ../../_shared/project-structure.md, ../../_shared/standards.md
