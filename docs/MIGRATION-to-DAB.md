# Structure - STATUS: FINALIZED in this branch

Reorganized into the locked DAB layout (`../skills/_shared/project-structure.md`, spec `../specs/foundation/project-structure-spec.md`). Done by moving files in-folder, so committing this feature branch records it directly.

## Final src/ shape
- `src/core/{config, abc, common}`   (foundation libs; no `sdk/`, no `insurelake` wrapper)
- `src/framework/{engines}`
- `src/runners/`                      (entrypoints; renamed from `entrypoints` to dodge a PyPI clash)
Imports use `core.*` / `framework.*`; `pytest.ini` sets `pythonpath = src`.

## Committer checklist
1. `git add -A` (records the moves).
2. Leftovers are in gitignored `scratch/` -> NOT committed; old tracked paths show as deleted.
3. `python -m pytest` (Spark-touching tests need pyspark / Databricks).
4. `databricks bundle validate` after the `resources/*.example` become real `.yml`.
