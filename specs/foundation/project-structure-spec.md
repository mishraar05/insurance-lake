# FND-030 - Project Structure Specification (DAB Scaffold)

Status: active · 2026-06-18 · Skill: `framework-dev.scaffold-structure`
Canonical layout: `../../skills/_shared/project-structure.md`

## Purpose
Define and create the standard Databricks Asset Bundle (DAB) repository structure for InsureLake and keep every generated artifact in its mapped home. Wave 0 task owned by this spec + the `scaffold-structure` skill (run via Genie Code) - not manual git steps.

## src/ layout (locked)
- `src/core/` - foundation libs: `config/`, `abc/` (audit/balance/control), `common/`. No `sdk/` silo, no project-name wrapper.
- `src/framework/` - engines: ingestion, harmonization, dq, reconciliation, masking, observability, finops.
- `src/runners/` - thin entrypoints invoked by jobs/pipelines (named `runners`, not `entrypoints`, to avoid the PyPI `entrypoints` collision).
Imports: `from core.config import ConfigLoader`, `from core.abc import ABC`, `from framework.ingestion import ...`. `pythonpath = src`.

## Procedure (Genie-Code-ready / scaffold-structure)
1. Create the tree (with `__init__.py` per package, `.gitkeep` for empty asset dirs).
2. Place artifacts by type: foundation -> `src/core/<area>/`; engines -> `src/framework/<x>/`; runners -> `src/runners/`; pipelines/jobs -> `resources/`; DDL -> `conf/ddl/`; metadata -> `conf/metadata/`; tests -> `tests/<mirror>/`.
3. Re-export public API in package `__init__` (e.g. `core.config` -> `ConfigLoader`).
4. Never name a top-level src package `abc`, `config`, `common`, or `entrypoints` (stdlib/PyPI collisions) - keep them under `core/`.
5. Validate: no business-logic `.py` at repo root; nothing outside its mapped home.

## Acceptance
- Layout matches `project-structure.md`; `python -m pytest` discovers tests under `src`; `databricks bundle validate` passes once `resources/` are populated.

## References
- Backlog: FND-030 · Skill: `../../skills/framework-dev/scaffold-structure/SKILL.md` · Layout: `../../skills/_shared/project-structure.md`
