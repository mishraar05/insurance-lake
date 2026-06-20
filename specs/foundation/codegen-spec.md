---
id: foundation.codegen
title: Schema Codegen (metadata -> DDL + JSON-schema)
owner: EY
status: active
target_path: scripts/codegen/
owning_skill: framework-dev.build-config-model
backlog: [FND-002, FND-004]
provides: [sql_type, model_to_ddl, model_to_jsonschema, generate, main]
depends_on: [foundation.config-model]
generation_context:
  - src/core/metadata/*.py
  - specs/foundation/config-model-spec.md
  - specs/foundation/control-tables-ddl-spec.md
acceptance:
  - "python scripts/codegen/gen_schema.py             # writes conf/ddl + conf/metadata/_schema.json"
  - "python scripts/codegen/gen_schema.py --check     # exit 0 only if outputs are up to date"
  - "test -f conf/ddl/control_tables.sql && test -f conf/metadata/_schema.json"
regeneration: fully-generated
---

# Schema Codegen - Specification

## 1. Purpose & scope
Generate the Unity Catalog control-table **DDL** and a **JSON-schema** library **from** the `core.metadata` dataclasses, so the three representations (dataclasses, DDL, JSON) cannot drift - the dataclasses are the single source of truth.
- In scope: the generator tool + its two outputs.
- Out of scope: the models (see `config-model-spec`); FK semantics beyond the known FK map.

## 2. Requirements
**Functional**
- FR-1: Introspect `core.metadata.MODELS`.
- FR-2: Map Python types -> Spark SQL types.
- FR-3: Emit `CREATE TABLE` per model in `insurelake_config.config` with PK (first field) + FKs from a known FK map.
- FR-4: Emit `conf/metadata/_schema.json` with a `$defs` entry per model (properties + required).
- FR-5: `--check` mode: render in-memory, diff vs on-disk, exit 1 if stale.

**Non-functional**: pure Python (no pyspark); deterministic, byte-stable output; idempotent; CI-runnable.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
def sql_type(t) -> str: ...                    # python type -> Spark SQL type
def model_to_ddl(model: type) -> str: ...      # one CREATE TABLE statement
def model_to_jsonschema(model: type) -> dict: ...
def generate(check: bool = False) -> int: ...  # writes outputs, or checks staleness; returns exit code
def main(argv: list | None = None) -> int: ... # CLI entry: [--check]
```

## 4. Inputs / Outputs
- Input: `core.metadata.MODELS` (the 8 dataclasses).
- Outputs: `conf/ddl/control_tables.sql`, `conf/metadata/_schema.json`.

## 5. Design
Introspect with `typing.get_type_hints` + `dataclasses.fields`. Use an **explicit `TABLE` map** (model name -> table) to avoid CamelCase->snake edge cases (e.g. `DQRuleConfig`->`cfg_dq_rule`), and an explicit `FK_MAP`. Deterministic ordering = `MODELS` order then field order.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this):
- **Procedure:**
  1. Import `MODELS`, `TABLE`, `FK_MAP`.
  2. For each model: `table = TABLE[model.__name__]`; `hints = get_type_hints(model)`; columns = `[(f.name, sql_type(hints[f.name])) for f in fields(model)]`; PK = `fields(model)[0].name` (emit `NOT NULL`).
  3. Emit `CREATE TABLE IF NOT EXISTS insurelake_config.config.{table} (<cols>, CONSTRAINT pk_{table} PRIMARY KEY ({pk}) [, FK constraints]) USING DELTA;` prefixed once with `CREATE CATALOG/SCHEMA IF NOT EXISTS`.
  4. JSON-schema: `$defs[ModelName] = {type:object, properties:{field: json_type}, required:[fields with no default]}`; wrap in `{$schema, $defs}`.
  5. Write both files. `--check`: render to strings, compare to on-disk; return `1` if any differ else `0`.
- **Decision rules (type map):** `str->STRING`, `bool->BOOLEAN`, `int->INT`, `float->DOUBLE`, `datetime->TIMESTAMP`, `List[str]->ARRAY<STRING>`, `Dict[str,str]->MAP<STRING,STRING>`, `Optional[X]->sql_type(X)` (nullable).
- **Key code fragments:**
```python
from typing import get_type_hints, get_origin, get_args, Union
import dataclasses, datetime
TYPE_MAP = {str:"STRING", bool:"BOOLEAN", int:"INT", float:"DOUBLE", datetime.datetime:"TIMESTAMP"}
def sql_type(t):
    o = get_origin(t)
    if o is Union: return sql_type([a for a in get_args(t) if a is not type(None)][0])
    if o in (list,):  return "ARRAY<STRING>"
    if o in (dict,):  return "MAP<STRING,STRING>"
    return TYPE_MAP.get(t, "STRING")
```
- **Edge cases:** unwrap `Optional`; a new model in `MODELS` is auto-included; field order preserved; FK only for tables present in `FK_MAP`; output must be byte-stable so `--check` is reliable.

**Constraints (hard):** pure Python (no pyspark/network); deterministic; single file `scripts/codegen/gen_schema.py`; this is a **build-time tool, not a pipeline run -> NO ABC instrumentation**; on error `sys.exit(2)`.

## 7. Validation, edge cases & versioning policy
`--check` is the drift guard (CI fails if `conf/ddl` is out of date vs the models). Adding/removing a model field -> regenerate. Output format changes are breaking for `--check`; regenerate in the same change.

## 8. Error handling + ABC instrumentation
Build-time tool, not a data run -> no ABC. On exception: print the cause, `sys.exit(2)`.

## 9. Testing & acceptance
Unit: `sql_type(Optional[str]) == "STRING"`; `sql_type(List[str]) == "ARRAY<STRING>"`; `model_to_ddl(SourceConfig)` contains `cfg_source`, `STRING`, `PRIMARY KEY (source_id)`. Plus front-matter `acceptance` (generate, then `--check` exits 0).

## 10. Examples
`SourceConfig` ->
```sql
CREATE TABLE IF NOT EXISTS insurelake_config.config.cfg_source (
  source_id STRING NOT NULL, source_name STRING, ... ,
  CONSTRAINT pk_cfg_source PRIMARY KEY (source_id)
) USING DELTA;
```

## 11. Regeneration contract
`regeneration: fully-generated`. The tool **and its outputs** (`conf/ddl/control_tables.sql`, `conf/metadata/_schema.json`) are generated - never hand-edit the outputs; change the models and regenerate.

## 12. References
`foundation/config-model-spec.md` · `foundation/control-tables-ddl-spec.md` · `skills/_shared/project-structure.md`.
