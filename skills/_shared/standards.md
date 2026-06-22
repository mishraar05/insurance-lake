# Coding & Design Standards (shared)

- Metadata-driven: behaviour comes from config, not hardcoding.
- Idempotent + restartable; deterministic outputs.
- No `SELECT *` into managed tables; explicit schemas.
- Secrets via Databricks secrets only.
- PII never logged; masking handled by the masking engine / classification skill.
- Every run calls the ABC SDK (audit + balance + cost).
- Declarative path = Lakeflow Declarative Pipelines; non-declarative = classic batch PySpark + MERGE.
- Packaging: workspace source deployed via Asset Bundles (no wheels).
- Naming: snake_case tables/columns; component prefixes match backlog IDs.

## Code style & documentation (enforced)
All generated Python MUST satisfy these — they are machine-checked by `pyproject.toml` (ruff + black), so a generated module is not "done" until both pass:
- **PEP 8** via `ruff` (pycodestyle E/W, pyflakes F, import order I, pep8-naming N); **black** formatting (line length 88).
- **Docstrings on every public module, class, and function** — **Google style** (`Args:` / `Returns:` / `Raises:`), enforced by ruff `D` with `convention = "google"`.
- **Type hints** on every public signature (no bare `Any`; see §6 hard constraints).
- **Comments** explaining non-obvious logic, the *why* of each decision branch, and any Databricks-specific option (guidance — not lint-checked, but required).
- Run before commit: `ruff check --fix . && black .`; the check form (`ruff check ...`, `black --check ...`) belongs in each code spec's `acceptance:`.

## File placement
All generated files follow `_shared/project-structure.md` (canonical layout + placement rules). No business-logic `.py` at the repo root.
