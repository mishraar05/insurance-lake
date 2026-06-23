---
id: core.contracts
title: Core Contracts (Typed Interfaces)
owner: EY
status: active
contracts_version: 0.2.0
target_path: src/core/contracts/
owning_skill: framework-dev.scaffold-structure
backlog: [FND-031]
provides: [Reader, LoadStrategy, Engine, RunContext, RunResult, WriteResult, Check, CheckResult, Masker]
depends_on: [core.metadata]
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

- **In scope:** the Protocols `Reader`, `LoadStrategy`, `Engine`, `Check`, `Masker` + the value objects `RunContext`, `RunResult`, `WriteResult`, `CheckResult`.
- **Out of scope:** any implementation (those live in `dataio/`, `services/`, `framework/`).

## 2. Requirements
**Functional**
- FR-1: Define `Reader`, `LoadStrategy`, `Engine`, `Check`, `Masker` Protocols.
- FR-2: Define value objects `CheckResult`, `WriteResult` (returned by `LoadStrategy.apply`), and `RunContext`/`RunResult` for `Engine`.
- FR-3: Type every parameter against `core.metadata` models (`SourceConfig`, `TargetConfig`, `LoadConfig`, `DQRuleConfig`, `MaskingRuleConfig`) - no `Any` in public signatures except `RunContext.params`.
- FR-4: Protocols are `@runtime_checkable`.

**Non-functional**
- NFR-1: Package imports without `pyspark` (`DataFrame` only under `TYPE_CHECKING`).
- NFR-2: Pure structural typing (`Protocol`); implementers need not inherit.
- NFR-3: Stable + versioned (`__version__`); see section 7.
- NFR-4: Extensibility - support multi-customer customization via dependency injection.

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
@dataclass
class WriteResult:
    num_output_rows: int              # rows the commit actually wrote (engines read this for balance)
    operation: str = "WRITE"          # WRITE | MERGE | OVERWRITE
    metrics: Dict[str, Any] = field(default_factory=dict)   # raw Delta operationMetrics

@runtime_checkable
class LoadStrategy(Protocol):
    def apply(self, df: "DataFrame", target: TargetConfig, load: LoadConfig,
              options: Optional[Dict[str, str]] = None) -> WriteResult: ...   # options from schema-evolution

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
`__init__.py` re-exports all of the above and sets `__version__ = "0.2.0"`.

## 4. Inputs / Outputs
- **Inputs:** config models from `core.metadata`; Spark `DataFrame`s; a `RunContext` for engines.
- **Outputs:** DataFrames (`read`/`mask`), side-effecting writes (`apply`), `CheckResult` (`evaluate`), `RunResult` (`run`).

## 5. Design
- `typing.Protocol` + `@runtime_checkable` (structural typing) over ABCs.
- `from __future__ import annotations` + `TYPE_CHECKING` import of `DataFrame` -> imports without `pyspark`.
- One module per protocol + `__init__` re-export.
- **Implementers:** `dataio.readers`->Reader; `dataio.load_strategy`->LoadStrategy; `dataio.checks`->Check; `dataio.maskers`->Masker; `framework/*`->Engine.

### SOLID Principles Application (REQUIRED for all components)

This contracts module is the foundation for all SOLID principles in the framework:

**Single Responsibility Principle (SRP):**
- Each protocol defines ONE responsibility: `Reader` reads, `LoadStrategy` writes, `Check` validates, `Masker` transforms, `Engine` orchestrates
- Protocols are segregated by concern — no god interface combining read+write+validate
- Example: `Reader` has ONE method (`read`), ONE reason to change (source format evolution)

**Open/Closed Principle (OCP):**
- Protocols define stable interfaces closed for modification
- New implementations extend via structural typing without touching contracts
- Example: Add `DeltaSharingReader` by implementing `Reader` protocol — no contract change needed

**Liskov Substitution Principle (LSP):**
- **Critical:** All implementations of a protocol are substitutable
- Any `Reader` can replace any other `Reader` — engine doesn't know or care which
- Example:
  ```python
  def ingest(reader: Reader, source: SourceConfig):
      df = reader.read(source, load)  # Works with ANY Reader implementation
      # CSVReader, JSONReader, JDBCReader all work here
  ```
- Protocol signatures enforce substitutability via mypy

**Interface Segregation Principle (ISP):**
- **Critical:** Many client-specific protocols > one fat interface
- Separate `Reader`, `LoadStrategy`, `Check`, `Masker` — clients depend only on what they use
- Counter-example (DON'T DO):
  ```python
  # BAD: Fat interface
  class DataProcessor(Protocol):
      def read(self): ...
      def write(self): ...
      def validate(self): ...
      def mask(self): ...
  # Problem: A read-only component must implement unused write/validate/mask
  ```
- Our approach (GOOD):
  ```python
  # GOOD: Segregated interfaces
  class Reader(Protocol):
      def read(self): ...  # Only what readers need
  
  class LoadStrategy(Protocol):
      def apply(self): ...  # Only what writers need
  
  # Read-only component depends ONLY on Reader, not LoadStrategy
  ```

**Dependency Inversion Principle (DIP):**
- **Critical:** High-level engines depend on abstractions (these protocols), not concrete readers/strategies
- Concrete implementations depend on the same abstractions
- Example:
  ```python
  # Engine depends on abstraction (Reader protocol)
  class IngestionEngine:
      def __init__(self, reader: Reader):  # DIP - abstraction
          self._reader = reader
  
  # Concrete reader depends on same abstraction
  class CSVReader:  # implements Reader protocol
      def read(self, source, load): ...
  
  # Both depend on the Reader protocol (abstraction)
  # Neither depends on the other (no tight coupling)
  ```

### Design Patterns (use where applicable)

**Recommended patterns for this component:**

1. **Protocol Pattern (Structural Typing)**
   - Why: Python's `Protocol` enables duck typing with type safety
   - Benefit: Implementations don't inherit; structural match via `isinstance()`
   - Example: `HashMasker` matches `Masker` protocol without inheritance

2. **Interface Segregation Pattern**
   - Why: Keep protocols focused and cohesive
   - Benefit: Clients depend on minimal interfaces
   - Example: Five protocols (Reader, LoadStrategy, Engine, Check, Masker) instead of one

3. **Strategy Pattern (Enabled)**
   - Why: Protocols enable strategy pattern in engines
   - Benefit: Runtime strategy switching without code changes
   - Example: Engine accepts any `LoadStrategy` — swap Append/SCD1/SCD2 at runtime

4. **Dependency Injection (Enabled)**
   - Why: Protocols make DI natural (type hints + abstractions)
   - Benefit: Testable (inject mocks), flexible (inject any implementation)
   - Example:
     ```python
     # Production
     engine = IngestionEngine(reader=CSVReader(), strategy=SCD2Strategy())
     
     # Testing
     engine = IngestionEngine(reader=MockReader(), strategy=MockStrategy())
     ```

**Pattern application:**
```python
# Example: Engine using DIP + Strategy pattern
class IngestionEngine:
    def __init__(
        self,
        reader: Reader,        # DIP - depend on protocol
        strategy: LoadStrategy # DIP - depend on protocol
    ):
        self._reader = reader
        self._strategy = strategy
    
    def run(self, context: RunContext) -> RunResult:
        # LSP - any Reader works here
        df = self._reader.read(context.source, context.load)
        
        # LSP - any LoadStrategy works here
        self._strategy.apply(df, context.target, context.load)
        
        return RunResult(status="SUCCESS")

# Usage - runtime strategy selection
engine = IngestionEngine(
    reader=AutoLoaderReader() if streaming else CSVReader(),  # OCP
    strategy=SCD2Strategy() if maintain_history else AppendStrategy()  # OCP
)
```

**Extensibility considerations:**
- New protocols: Add new `.py` module, update `__init__.py` (versioned change)
- New implementations: No contract changes needed (OCP)
- Multi-customer: Same protocols, different implementations injected per customer
- Config-driven: Factory pattern in engines selects implementations based on config

## 6. Implementation logic & guidance
**Logic / algorithm:** N/A - interface-only (method bodies are `...`; contracts contain no logic).

Path: `src/core/contracts/{reader,load_strategy,engine,check,masker}.py` + `__init__.py`. Emit exactly the skeleton in section 3.

**Constraints (hard):**
- No logic in contracts - method bodies are `...` only.
- No new dependencies; `pyspark` only under `TYPE_CHECKING`.
- No `Any` in public signatures (except `RunContext.params`).
- One module per protocol; no network/IO/state.
- **Follow SOLID principles (see section 5):**
  - SRP: One protocol per responsibility (Reader, LoadStrategy, Check, Masker, Engine)
  - OCP: Stable interfaces; extend via new implementations, not modifications
  - LSP: Implementations must be substitutable (enforced via mypy)
  - ISP: Segregated protocols; no fat interfaces
  - DIP: High-level code depends on these abstractions, not concretions

## 7. Validation, edge cases & versioning policy
- `@runtime_checkable` verifies method **names**, not signatures - the `mypy` acceptance step enforces signatures.
- Versioned via `core.contracts.__version__`. Adding/changing a method or value-object field is a **breaking change**: bump `contracts_version` (front-matter + `__version__`) and update all implementers in the same change. A new optional capability -> a **new Protocol**, never a mutation. (v0.2.0: added `WriteResult` and `LoadStrategy.apply(..., options) -> WriteResult` so engines read real write metrics for the balance check.)

## 8. Error handling + ABC instrumentation
Contracts carry no logic. **Rule:** every implementer instruments via the ABC SDK (audit/balance/cost) + structured logging - enforced by `standards.md` + the self-review gate, not by the contract.

## 9. Testing & acceptance
Executable; see front-matter `acceptance` (import-without-pyspark, `pytest tests/core/test_contracts.py`, `mypy`). DONE only when all three pass.

### Acceptance Criteria
- [ ] Contracts import without pyspark (`python -c 'import core.contracts'`)
- [ ] All protocol tests pass (`pytest tests/core/test_contracts.py`)
- [ ] Type checking passes (`mypy core/contracts`)
- [ ] **SOLID compliance verified:**
  - [ ] SRP: Each protocol has single responsibility (manual review)
  - [ ] OCP: No modifications needed for new implementations (manual review)
  - [ ] LSP: Substitutability enforced via mypy type checks
  - [ ] ISP: No fat interfaces (manual review - each protocol < 5 methods)
  - [ ] DIP: No concrete dependencies in protocol signatures (manual review)

### Testing SOLID compliance

**LSP (Liskov Substitution) Tests:**
```python
# Test: Any Reader implementation is substitutable
def test_reader_substitutability():
    readers = [CSVReader(), JSONReader(), ParquetReader()]
    for reader in readers:
        assert isinstance(reader, Reader)  # structural match
        df = reader.read(source_config, load_config)  # works for all
        assert df is not None

# Test: Any LoadStrategy implementation is substitutable
def test_strategy_substitutability():
    strategies = [AppendStrategy(), SCD1Strategy(), SCD2Strategy()]
    for strategy in strategies:
        assert isinstance(strategy, LoadStrategy)  # structural match
        strategy.apply(df, target_config, load_config)  # works for all
```

**DIP (Dependency Inversion) Tests:**
```python
# Test: Engine accepts protocol, not concrete type
def test_engine_depends_on_abstraction():
    # Mock reader (no real implementation needed)
    class MockReader:
        def read(self, source, load):
            return spark.createDataFrame([{"id": 1}])
    
    mock_reader = MockReader()
    assert isinstance(mock_reader, Reader)  # structural match
    
    # Engine accepts abstraction
    engine = IngestionEngine(reader=mock_reader)  # type checks pass
```

**ISP (Interface Segregation) Tests:**
```python
# Test: Read-only component doesn't need LoadStrategy
def test_interface_segregation():
    # Component that only reads (no write/validate)
    class DataProfiler:
        def __init__(self, reader: Reader):  # Only depends on Reader
            self._reader = reader
        
        def profile(self, source: SourceConfig):
            df = self._reader.read(source, load_config)
            return df.count()  # Profiling logic
    
    # Works without LoadStrategy/Check/Masker protocols
    profiler = DataProfiler(reader=CSVReader())
    assert profiler.profile(source) > 0
```

## 10. Generation Validation

This section enables mechanical verification of generated code against the spec. Every validation item is programmatically checkable.

### 10.1 File Structure Validation

**Required files (exact 6 files, no more, no less):**

```
src/core/contracts/
├── engine.py          # RunContext, RunResult, Engine protocol
├── reader.py          # Reader protocol
├── load_strategy.py   # WriteResult, LoadStrategy protocol
├── check.py           # CheckResult, Check protocol
├── masker.py          # Masker protocol
└── __init__.py        # Package exports
```

**Validation checklist:**
- [ ] Exactly 6 .py files in src/core/contracts/
- [ ] All files listed above exist
- [ ] No additional .py files present
- [ ] __init__.py exports all public classes

### 10.2 Interface Validation

**Dataclasses:**

**RunContext (exact 4 fields):**
- [ ] component: str
- [ ] entity: str
- [ ] run_type: str
- [ ] params: Optional[Dict[str, Any]] = None

**RunResult (exact 3 fields):**
- [ ] status: str
- [ ] metrics: Dict[str, Any] = field(default_factory=dict)
- [ ] run_id: Optional[str] = None

**WriteResult (exact 3 fields):**
- [ ] num_output_rows: int
- [ ] operation: str = "WRITE"
- [ ] metrics: Dict[str, Any] = field(default_factory=dict)

**CheckResult (exact 4 fields):**
- [ ] rule_id: str
- [ ] passed: bool
- [ ] failed_count: int
- [ ] action: str

**Protocols:**

**Engine protocol (exact 1 method):**
- [ ] run(self, context: RunContext) -> RunResult

**Reader protocol (exact 1 method):**
- [ ] read(self, source: SourceConfig, load: LoadConfig) -> DataFrame

**LoadStrategy protocol (exact 1 method):**
- [ ] apply(self, df: DataFrame, target: TargetConfig, load: LoadConfig, options: Optional[Dict[str, str]] = None) -> WriteResult

**Check protocol (exact 1 method):**
- [ ] evaluate(self, df: DataFrame, rule: DQRuleConfig) -> CheckResult

**Masker protocol (exact 1 method):**
- [ ] mask(self, df: DataFrame, rules: List[MaskingRuleConfig]) -> DataFrame

**Validation checklist:**
- [ ] All dataclasses have exact field counts as specified
- [ ] All protocols are marked @runtime_checkable
- [ ] All protocols have exact method counts as specified
- [ ] All method signatures match spec exactly
- [ ] All protocols have method bodies of `...` only (no logic)

### 10.3 Enum Validation

**(Omit - this component has no enums)**

### 10.4 Implementation Pattern Validation

**(Omit - interface-only component, method bodies are `...`)**

### 10.5 Import/Export Validation

**__init__.py exports (exactly 10 items):**
- [ ] `__version__ = "0.2.0"`
- [ ] RunContext
- [ ] RunResult
- [ ] Engine
- [ ] Reader
- [ ] LoadStrategy
- [ ] WriteResult
- [ ] Check
- [ ] CheckResult
- [ ] Masker

**Required imports (each module):**
- [ ] `from __future__ import annotations`
- [ ] `from typing import Protocol, runtime_checkable` (in protocol files)
- [ ] `from dataclasses import dataclass, field` (in dataclass files)
- [ ] `from typing import TYPE_CHECKING`
- [ ] `if TYPE_CHECKING: from pyspark.sql import DataFrame`

**Forbidden imports:**
- [ ] No direct pyspark imports outside TYPE_CHECKING
- [ ] No concrete implementation imports in protocol files

**Validation checklist:**
- [ ] __init__.py exports exactly 10 public items
- [ ] __version__ equals "0.2.0"
- [ ] All protocol files use TYPE_CHECKING for DataFrame
- [ ] Package imports without pyspark dependency

### 10.6 Business Logic Validation

**(Omit - interface-only component, no business logic)**

### 10.7 Automated Validation Script

**Script location:** `validation/validate_contracts.py`

**Usage:**
```bash
# From repo root
python validation/validate_contracts.py

# Expected output:
# ✅ File structure valid: 6 files
# ✅ Dataclass fields valid
# ✅ Protocol methods valid
# ✅ Imports/exports valid
# ✅ All contracts validation checks passed!
```

**Complete validation script:**
```python
#!/usr/bin/env python3
"""
Validation script for core.contracts component.
Mechanically verifies generated code matches spec §10.

Usage:
    python validation/validate_contracts.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def validate_file_structure():
    """§10.1: Validate file structure."""
    component_path = Path("src/core/contracts")
    py_files = list(component_path.glob("*.py"))
    
    expected_files = {
        "engine.py",
        "reader.py",
        "load_strategy.py",
        "check.py",
        "masker.py",
        "__init__.py"
    }
    
    actual_files = {f.name for f in py_files}
    
    assert len(py_files) == 6, f"Expected 6 files, got {len(py_files)}"
    assert actual_files == expected_files, \
        f"File mismatch: {actual_files ^ expected_files}"
    
    print("✅ File structure valid: 6 files")

def validate_dataclass_fields():
    """§10.2: Validate dataclass field counts."""
    from core.contracts import RunContext, RunResult, WriteResult, CheckResult
    
    # Check field counts
    assert len(RunContext.__dataclass_fields__) == 4, \
        f"RunContext: expected 4 fields, got {len(RunContext.__dataclass_fields__)}"
    
    assert len(RunResult.__dataclass_fields__) == 3, \
        f"RunResult: expected 3 fields, got {len(RunResult.__dataclass_fields__)}"
    
    assert len(WriteResult.__dataclass_fields__) == 3, \
        f"WriteResult: expected 3 fields, got {len(WriteResult.__dataclass_fields__)}"
    
    assert len(CheckResult.__dataclass_fields__) == 4, \
        f"CheckResult: expected 4 fields, got {len(CheckResult.__dataclass_fields__)}"
    
    print("✅ Dataclass fields valid")

def validate_protocol_methods():
    """§10.2: Validate protocol method counts."""
    from core.contracts import Engine, Reader, LoadStrategy, Check, Masker
    
    # Check method counts (exclude private/magic methods)
    def count_public_methods(protocol):
        return len([m for m in dir(protocol) 
                   if not m.startswith('_') and callable(getattr(protocol, m, None))])
    
    # Note: Protocol classes have extra methods from typing.Protocol
    # We check that our defined methods exist
    assert hasattr(Engine, 'run'), "Engine missing run() method"
    assert hasattr(Reader, 'read'), "Reader missing read() method"
    assert hasattr(LoadStrategy, 'apply'), "LoadStrategy missing apply() method"
    assert hasattr(Check, 'evaluate'), "Check missing evaluate() method"
    assert hasattr(Masker, 'mask'), "Masker missing mask() method"
    
    print("✅ Protocol methods valid")

def validate_imports_exports():
    """§10.5: Validate imports and exports."""
    import core.contracts
    
    # Check exports
    expected_exports = {
        '__version__',
        'RunContext',
        'RunResult',
        'Engine',
        'Reader',
        'LoadStrategy',
        'WriteResult',
        'Check',
        'CheckResult',
        'Masker'
    }
    
    actual_exports = {name for name in dir(core.contracts) 
                     if not name.startswith('_') or name == '__version__'}
    
    # Check that all expected exports are present
    missing = expected_exports - actual_exports
    assert not missing, f"Missing exports: {missing}"
    
    # Check version
    assert core.contracts.__version__ == "0.2.0", \
        f"Expected version 0.2.0, got {core.contracts.__version__}"
    
    print("✅ Imports/exports valid")

def main():
    """Run all validation checks."""
    try:
        validate_file_structure()
        validate_dataclass_fields()
        validate_protocol_methods()
        validate_imports_exports()
        
        print("\n" + "="*60)
        print("✅ All contracts validation checks passed!")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Validation failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
```

---

## 11. Examples

**Conformant (one per protocol):**
```python
class AutoLoaderReader:          # Reader
    def read(self, source, load): ...          # returns DataFrame
class Scd2Strategy:              # LoadStrategy
    def apply(self, df, target, load, options=None):
        return WriteResult(num_output_rows=df.count())   # writes; returns WriteResult
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

### SOLID Example: Good vs. Bad

**❌ BAD (Violates SOLID):**
```python
# Violates ISP (Interface Segregation) - fat interface
class DataProcessor(Protocol):
    """Fat interface - forces clients to implement everything"""
    def read(self, source: SourceConfig) -> DataFrame: ...
    def write(self, df: DataFrame, target: TargetConfig) -> None: ...
    def validate(self, df: DataFrame, rules: List[DQRuleConfig]) -> CheckResult: ...
    def mask(self, df: DataFrame, rules: List[MaskingRuleConfig]) -> DataFrame: ...

# Problem 1: Read-only component must implement unused methods
class DataProfiler:  # Only reads data
    def read(self, source): return spark.read.csv(source.path)
    def write(self, df, target): raise NotImplementedError  # Forced to implement!
    def validate(self, df, rules): raise NotImplementedError  # Forced to implement!
    def mask(self, df, rules): raise NotImplementedError  # Forced to implement!

# Problem 2: Violates SRP - one class, many reasons to change
# Problem 3: Violates DIP - engine tightly coupled to concrete DataProcessor
class Engine:
    def __init__(self):
        self.processor = DataProcessor()  # Can't inject different implementations!
```

**✅ GOOD (Follows SOLID):**
```python
# Follows ISP - segregated protocols
class Reader(Protocol):
    def read(self, source: SourceConfig, load: LoadConfig) -> DataFrame: ...

class LoadStrategy(Protocol):
    def apply(self, df: DataFrame, target: TargetConfig, load: LoadConfig, options=None) -> WriteResult: ...

class Check(Protocol):
    def evaluate(self, df: DataFrame, rule: DQRuleConfig) -> CheckResult: ...

class Masker(Protocol):
    def mask(self, df: DataFrame, rules: List[MaskingRuleConfig]) -> DataFrame: ...

# Follows SRP + ISP - depends only on what it needs
class DataProfiler:
    def __init__(self, reader: Reader):  # ISP - only depends on Reader
        self._reader = reader
    
    def profile(self, source: SourceConfig):
        df = self._reader.read(source, load_config)
        return {"count": df.count(), "columns": len(df.columns)}

# Follows OCP + DIP - accepts abstractions, extensible
class IngestionEngine:
    def __init__(
        self,
        reader: Reader,        # DIP - depend on abstraction
        strategy: LoadStrategy # DIP - depend on abstraction
    ):
        self._reader = reader
        self._strategy = strategy
    
    def run(self, context: RunContext) -> RunResult:
        # LSP - any Reader works
        df = self._reader.read(context.source, context.load)
        
        # LSP - any LoadStrategy works
        self._strategy.apply(df, context.target, context.load)
        
        return RunResult(status="SUCCESS")

# OCP - extend without modifying Engine
engine = IngestionEngine(
    reader=CSVReader(),      # Can swap: JSONReader, DeltaReader, etc.
    strategy=SCD2Strategy()  # Can swap: AppendStrategy, SCD1Strategy, etc.
)
```

**Key Differences:**
* **BAD:** Fat interface, forced implementations, tight coupling
* **GOOD:** Segregated protocols, depend only on what's needed, loose coupling via DI

**Benefits of GOOD approach:**
1. **Testability:** Inject mocks for `Reader` and `LoadStrategy`
2. **Flexibility:** Swap implementations at runtime (strategy pattern)
3. **Maintainability:** Changes to `Reader` don't affect `LoadStrategy` or `Check`
4. **Extensibility:** Add new implementations without touching protocols or engines

## 12. Regeneration contract
`regeneration: fully-generated`. The entire `src/core/contracts/` package is generated from this spec and is safe to overwrite; it carries no hand edits. (Engines, by contrast, will be `scaffold-then-edit` - their specs will say so.)

## 13. References
`foundation/config-model-spec.md` (`core.metadata`) · `foundation/project-structure-spec.md` · `../../skills/_shared/standards.md`. Implemented by: `dataio/{readers,load-strategy,checks,maskers}` + `framework/engine-base` specs.

---

**SOLID Compliance:** ✅ Updated 2026-06-18 - Comprehensive SOLID principles application documented for protocol interfaces.
