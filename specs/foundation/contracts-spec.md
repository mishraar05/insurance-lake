---
id: foundation.contracts
title: Core Contracts (Typed Interfaces)
owner: EY
status: active
contracts_version: 0.1.0
target_path: src/core/contracts/
owning_skill: framework-dev.scaffold-structure
backlog: [FND-031]
provides: [Reader, LoadStrategy, Engine, RunContext, RunResult, Check, CheckResult, Masker]
depends_on: [foundation.config-model]
generation_context:            # the ONLY files the generator should read to build this
  - src/core/metadata/*.py
  - skills/_shared/standards.md
acceptance:                    # executable; ALL must pass (run from repo root unless noted)
  - "cd src && python -c 'import core.contracts'                 # imports without pyspark"
  - "pytest tests/core/test_contracts.py"
  - "cd src && mypy --ignore-missing-imports --follow-imports=silent core/contracts"
regeneration: fully-generated  # whole package is generated from this spec; safe to overwrite; no hand edits
---

# Core Contracts (Typed Interfaces) - Specification

## 1. Purpose & scope
Define the stable, typed boundaries that decouple the engines (`framework/`) from the reusable primitives (`dataio/`) and services. Implementations depend on these Protocols, never on each other - this keeps the dependency direction clean (`core <- dataio/services <- framework`) and lets us swap a reader or load-strategy without touching an engine.

- **In scope:** the Protocols `Reader`, `LoadStrategy`, `Engine`, `Check`, `Masker` + the value objects `RunContext`, `RunResult`, `CheckResult`.
- **Out of scope:** any implementation (those live in `dataio/`, `services/`, `framework/`).

## 2. Requirements
**Functional**
- FR-1: Define `Reader`, `LoadStrategy`, `Engine`, `Check`, `Masker` Protocols.
- FR-2: Define value objects `CheckResult`, and `RunContext`/`RunResult` for `Engine`.
- FR-3: Type every parameter against `core.metadata` models (`SourceConfig`, `TargetConfig`, `LoadConfig`, `DQRuleConfig`, `MaskingRuleConfig`) - no `Any` in public signatures except `RunContext.params`.
- FR-4: Protocols are `@runtime_checkable`.

**Non-functional**
- NFR-1: Package imports without `pyspark` (`DataFrame` only under `TYPE_CHECKING`).
- NFR-2: Pure structural typing (`Protocol`); implementers need not inherit.
- NFR-3: Stable + versioned (`__version__`); see section 7.

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
# src/core/contracts/engine.py
@dataclass
class RunContext:
    component: str
    entity: str
    run_type: str
    params: Optional[Dict[str, Any]] = None

@dataclass
class RunResult:
    status: str                       # SUCCESS | FAILED
    metrics: Dict[str, Any] = field(default_factory=dict)
    run_id: Optional[str] = None

@runtime_checkable
class Engine(Protocol):
    def run(self, context: RunContext) -> RunResult: ...

# src/core/contracts/reader.py
@runtime_checkable
class Reader(Protocol):
    def read(self, source: SourceConfig, load: LoadConfig) -> "DataFrame": ...

# src/core/contracts/load_strategy.py
@runtime_checkable
class LoadStrategy(Protocol):
    def apply(self, df: "DataFrame", target: TargetConfig, load: LoadConfig) -> None: ...

# src/core/contracts/check.py
@dataclass
class CheckResult:
    rule_id: str
    passed: bool
    failed_count: int
    action: str                       # WARN | FAIL | QUARANTINE

@runtime_checkable
class Check(Protocol):
    def evaluate(self, df: "DataFrame", rule: DQRuleConfig) -> CheckResult: ...

# src/core/contracts/masker.py
@runtime_checkable
class Masker(Protocol):
    def mask(self, df: "DataFrame", rules: List[MaskingRuleConfig]) -> "DataFrame": ...
```
`__init__.py` re-exports all of the above and sets `__version__ = "0.1.0"`.

## 4. Inputs / Outputs
- **Inputs:** config models from `core.metadata`; Spark `DataFrame`s; a `RunContext` for engines.
- **Outputs:** DataFrames (`read`/`mask`), side-effecting writes (`apply`), `CheckResult` (`evaluate`), `RunResult` (`run`).

## 5. Design
- `typing.Protocol` + `@runtime_checkable` (structural typing) over ABCs.
- `from __future__ import annotations` + `TYPE_CHECKING` import of `DataFrame` -> imports without `pyspark`.
- One module per protocol + `__init__` re-export.
- **Implementers:** `dataio.readers`->Reader; `dataio.load_strategy`->LoadStrategy; `dataio.checks`->Check; `dataio.maskers`->Masker; `framework/*`->Engine.

## 6. Implementation logic & guidance
**Logic / algorithm:** N/A - interface-only (method bodies are `...`; contracts contain no logic).

Path: `src/core/contracts/{reader,load_strategy,engine,check,masker}.py` + `__init__.py`. Emit exactly the skeleton in section 3.
**Constraints (hard):**
- No logic in contracts - method bodies are `...` only.
- No new dependencies; `pyspark` only under `TYPE_CHECKING`.
- No `Any` in public signatures (except `RunContext.params`).
- One module per protocol; no network/IO/state.

## 7. Validation, edge cases & versioning policy
- `@runtime_checkable` verifies method **names**, not signatures - the `mypy` acceptance step enforces signatures.
- Versioned via `core.contracts.__version__`. Adding/changing a method or value-object field is a **breaking change**: bump `contracts_version` (front-matter + `__version__`) and update all implementers in the same change. A new optional capability -> a **new Protocol**, never a mutation.

## 8. Error handling + ABC instrumentation
Contracts carry no logic. **Rule:** every implementer instruments via the ABC SDK (audit/balance/cost) + structured logging - enforced by `standards.md` + the self-review gate, not by the contract.

## 9. Testing & acceptance
Executable; see front-matter `acceptance` (import-without-pyspark, `pytest tests/core/test_contracts.py`, `mypy`). DONE only when all three pass.

## 10. Examples
**Conformant (one per protocol):**
```python
class AutoLoaderReader:          # Reader
    def read(self, source, load): ...          # returns DataFrame
class Scd2Strategy:              # LoadStrategy
    def apply(self, df, target, load): ...     # writes; returns None
class HashMasker:                # Masker
    def mask(self, df, rules): return df
assert isinstance(HashMasker(), Masker)        # structural match, no inheritance
```
**Counter-examples (DO NOT):**
```python
class BadMasker:
    def apply_mask(self, df): ...   # wrong name -> isinstance(_, Masker) is False
class SneakyMasker:
    def mask(self, df): return df   # right name, wrong signature: passes isinstance
                                    # but the mypy acceptance step FAILS it (missing 'rules')
```

## 11. Regeneration contract
`regeneration: fully-generated`. The entire `src/core/contracts/` package is generated from this spec and is safe to overwrite; it carries no hand edits. (Engines, by contrast, will be `scaffold-then-edit` - their specs will say so.)

## 12. References
`foundation/config-model-spec.md` (`core.metadata`) · `foundation/project-structure-spec.md` · `../../skills/_shared/standards.md`. Implemented by: `dataio/{readers,load-strategy,checks,maskers}` + `framework/engine-base` specs.
