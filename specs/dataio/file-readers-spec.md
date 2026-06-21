---
id: dataio.file-readers
title: File Readers (batch, multi-format)
owner: EY
status: draft
target_path: src/dataio/readers/
owning_skill: framework-dev.build-ingestion-engine
backlog: [INGEST-002]
provides: [FileReader, ReaderFactory, get_reader]
depends_on: [foundation.contracts, foundation.config-model]
generation_context:
  - specs/foundation/contracts-spec.md
  - specs/foundation/config-model-spec.md
  - skills/_shared/project-structure.md
acceptance:
  - "pytest tests/dataio/test_readers.py"
  - "python -c 'from dataio.readers import FileReader, ReaderFactory, get_reader'"
regeneration: scaffold-then-edit
---

# File Readers - Specification

## 1. Purpose & scope
Batch, file-based **readers** implementing the `core.contracts.Reader` protocol: read CSV / JSON / Parquet / Delta / Avro into a Spark `DataFrame` for the non-declarative ingestion engine. Reads surface **corrupt records** (PERMISSIVE + `_corrupt_record`) so the engine can route them to `dataio.quarantine` (`CORRUPT_RECORD`).
- In scope: the `Reader` implementation, a format dispatch, and an extensibility factory.
- Out of scope: Auto Loader / streaming (declarative track); JDBC/API/CDC readers (separate specs); schema evolution (`dataio.schema-evolution`); writing/ABC (the engine owns those). The reader returns a **lazy** DataFrame - it never counts or materializes.

## 2. Requirements
**Functional**
- FR-1: Implement `Reader.read(source: SourceConfig, load: LoadConfig) -> DataFrame`.
- FR-2: Dispatch by `source.file_format` (csv | json | parquet | delta | avro).
- FR-3: Text formats (csv/json) read in **PERMISSIVE** mode with `columnNameOfCorruptRecord="_corrupt_record"` so malformed rows are surfaced, not dropped.
- FR-4: Honor `source.schema_location` (read with an explicit schema when provided; otherwise infer).
- FR-5: `ReaderFactory` lets new formats be registered without changing the engine (OCP).

**Non-functional**: returns an **unmaterialized** DataFrame (the engine materializes inside its retry); pure read (no writes, no ABC); typed (`SourceConfig`/`LoadConfig`); no hard-coded paths/formats.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
from core.contracts import Reader            # structural target (no inheritance needed)

class FileReader:                            # implements core.contracts.Reader
    def __init__(self, spark: "SparkSession") -> None: ...
    def read(self, source: SourceConfig, load: LoadConfig) -> "DataFrame": ...

class ReaderFactory:
    @classmethod
    def register(cls, fmt: str, options: dict) -> None: ...   # add/override a format's reader options
    @classmethod
    def options_for(cls, fmt: str) -> dict: ...               # default options for a format

def get_reader(spark: "SparkSession") -> FileReader: ...      # convenience constructor
```

## 4. Inputs / Outputs
- Input: a `SourceConfig` (`file_format`, `connection_string` path, optional `schema_location`) + `LoadConfig`.
- Output: a lazy `DataFrame` (with `_corrupt_record` present for text formats). No side effects.

## 5. Design
`FileReader` matches the `Reader` protocol structurally (no inheritance). `read` resolves `file_format`, builds `spark.read.format(fmt)` with the format's option defaults (from `ReaderFactory`), applies an explicit schema if `schema_location` is set, and returns `.load(path)` **without** triggering an action. The factory holds per-format default options so new formats are additive.

### SOLID Principles Application
* **SRP:** reads only - no writing, validation, schema evolution, or ABC.
* **OCP:** add a format by registering options in `ReaderFactory`; `read` and the engine are untouched.
* **LSP:** any `FileReader` is substitutable for any `Reader`; the engine never branches on concrete reader type.
* **ISP:** implements only `read` - it does not carry write/validate/mask methods.
* **DIP:** depends on the `SourceConfig`/`LoadConfig` abstractions and the `Reader` protocol, not on a concrete catalog or file system.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. `fmt = source.file_format.lower()`; look up its default options via `ReaderFactory.options_for(fmt)`.
  2. `reader = spark.read.format(fmt).options(**opts)`.
  3. For **csv/json**, set `mode="PERMISSIVE"`, `columnNameOfCorruptRecord="_corrupt_record"` (csv also `header`, json also `multiLine` as configured).
  4. If `source.schema_location` is set, load that schema and `reader = reader.schema(schema)` (no inference); else allow inference.
  5. `return reader.load(source.connection_string)` - **lazy**; do not `count()`/`collect()`.
- **Decision rules:**
  - Format dispatch: `csv|json|parquet|delta|avro`; unknown -> `ValueError(f"unsupported file_format: {fmt}")`.
  - Corrupt-record capture applies to **text** formats (csv/json) only; binary formats (parquet/delta/avro) don't need it.
  - Explicit schema (`schema_location`) disables inference; without it, infer (and accept the perf cost).
- **Key code fragments** (the generated code MUST contain these):
```python
TEXT = {"csv", "json"}
def read(self, source, load):
    fmt = source.file_format.lower()
    opts = dict(ReaderFactory.options_for(fmt))
    if fmt in TEXT:
        opts.update(mode="PERMISSIVE", columnNameOfCorruptRecord="_corrupt_record")
    r = self.spark.read.format(fmt).options(**opts)
    if source.schema_location:
        r = r.schema(self._load_schema(source.schema_location))
    return r.load(source.connection_string)        # lazy - engine materializes
```
- **Edge cases:** malformed rows land in `_corrupt_record` (the **engine** routes them to quarantine `CORRUPT_RECORD` - not the reader's job); missing path -> `read` raises (the engine classifies fatal vs transient); empty file -> empty DataFrame; schema drift -> the reader does **not** evolve (that is `dataio.schema-evolution`); `avro` requires the `spark-avro` package at runtime.

**Constraints (hard):** lazy (no action in `read`); pure (no writes/ABC); no hard-coded paths/formats; one concern (reading); typed signatures.

## 7. Validation, edge cases & versioning policy
The `Reader` protocol signature is the stable contract; adding a format is additive via `ReaderFactory`. Removing/renaming a format default is breaking for configs that reference it. Corrupt-record column name (`_corrupt_record`) is a contract shared with the engine/quarantine - keep it stable.

## 8. Error handling + ABC instrumentation
The reader is **pure** - no ABC. Read failures propagate to the engine, which classifies transient vs fatal and instruments. Corrupt **data** is surfaced via `_corrupt_record` (a column), never as an exception.

## 9. Testing & acceptance
Unit (mock/local Spark): reads each format; a malformed CSV row is captured in `_corrupt_record` (PERMISSIVE); `schema_location` disables inference; an unknown format raises `ValueError`; `read` returns a DataFrame **without** triggering a count (lazy). Plus front-matter `acceptance`; >80% coverage.

## 10. Examples
- **CSV:** `read(source(file_format="csv", connection_string="/Volumes/.../claims/"), load)` -> DataFrame with declared columns + `_corrupt_record`; the engine filters `_corrupt_record IS NOT NULL` -> quarantine `CORRUPT_RECORD`.
- **Counter-examples:** do **not** `count()`/`collect()` inside `read` (return lazy - the engine materializes once, inside its retry); do **not** evolve or drop columns here (that is `dataio.schema-evolution`).

## 11. Regeneration contract
`scaffold-then-edit`: the `FileReader` + `ReaderFactory` skeleton and the dispatch are fully generated; per-format option tuning is reviewed against current Spark reader docs.

## 12. References
`specs/foundation/contracts-spec.md` (`Reader`) · `specs/foundation/config-model-spec.md` (`SourceConfig`/`LoadConfig`) · `specs/dataio/schema-evolution-spec.md` · `specs/dataio/quarantine-spec.md` (`CORRUPT_RECORD` destination) · `specs/ingestion/ingestion-engine-spec.md` (caller) · `skills/_shared/project-structure.md`.
Note: `INGEST-002` is a **new** backlog task - add it to `AI_Ready_Backlog`.
