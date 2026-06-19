# Coding & Design Standards (shared)

- Metadata-driven: behaviour comes from config, not hardcoding.
- Idempotent + restartable; deterministic outputs.
- No `SELECT *` into managed tables; explicit schemas.
- Secrets via Databricks secrets only.
- PII never logged; masking handled by the masking engine / classification skill.
- Every run calls the ABC SDK (audit + balance + cost).
- Declarative path = Lakeflow Declarative Pipelines; non-declarative = Structured Streaming/batch + MERGE.
- Packaging: workspace source deployed via Asset Bundles (no wheels).
- Naming: snake_case tables/columns; component prefixes match backlog IDs.

## File placement
All generated files follow `_shared/project-structure.md` (canonical layout + placement rules). No business-logic `.py` at the repo root.
