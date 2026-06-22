# Spec Gap Analysis - Option D Retrofit

**Date:** 2026-06-18  
**Purpose:** Analyze existing specs for prescriptiveness and validation completeness  
**Target:** Upgrade all 3 specs to Option D standard (prescriptive + validated)

---

## Executive Summary

| Component | Spec Version | Prescriptiveness | Validation | Upgrade Priority |
|-----------|--------------|------------------|------------|------------------|
| 1. core.contracts | v0.2.0 | ⭐⭐⭐⭐⭐ Excellent | ❌ None | 🟢 LOW |
| 2. core.sdk (ABC) | (no version) | ⭐⭐⭐⭐ Good | ❌ None | 🟡 MEDIUM |
| 3. core.metadata | v0.1.0 | ⭐⭐ Poor | ❌ None | 🔴 HIGH |

**Key Finding:** Component 1 (contracts) is already nearly Option D compliant. Component 3 (config-model) requires major rewrite.

---

## Component 1: core.contracts (contracts-spec.md)

### ✅ What's Already Prescriptive

**§3 Interface - EXCELLENT:**
```python
# EXACT skeleton provided (lines 44-96)
@dataclass
class RunContext:
    component: str
    entity: str
    run_type: str
    params: Optional[Dict[str, Any]] = None

@runtime_checkable
class Engine(Protocol):
    def run(self, context: RunContext) -> RunResult: ...
```
- ✅ Complete dataclass definitions with exact fields
- ✅ Complete Protocol definitions with exact method signatures
- ✅ Type hints all specified
- ✅ Comments prescribe exact behavior ("method bodies are `...`")

**§6 Logic - N/A (Interface-only):**
- ✅ Explicitly states "N/A - interface-only (method bodies are `...`)"
- ✅ Correct approach for Protocol definitions

**§9 Testing - EXECUTABLE:**
```markdown
acceptance:
  - "cd src && python -c 'import core.contracts'"
  - "pytest tests/core/test_contracts.py"
  - "cd src && mypy --ignore-missing-imports core/contracts"
```
- ✅ Three executable acceptance criteria
- ✅ Specific commands (not prose)

### ⚠️ What Needs Enhancement

**Missing §10 Validation Section:**

Add exhaustive checklist:
```markdown
## 10. Generation Validation

### 10.1 File Structure
Required files (exact 6 files, no more, no less):
- [ ] src/core/contracts/engine.py
- [ ] src/core/contracts/reader.py
- [ ] src/core/contracts/load_strategy.py
- [ ] src/core/contracts/check.py
- [ ] src/core/contracts/masker.py
- [ ] src/core/contracts/__init__.py

### 10.2 Dataclass Validation
RunContext fields (exact 4 fields):
- [ ] component: str
- [ ] entity: str
- [ ] run_type: str
- [ ] params: Optional[Dict[str, Any]] = None

RunResult fields (exact 3 fields):
- [ ] status: str
- [ ] metrics: Dict[str, Any] = field(default_factory=dict)
- [ ] run_id: Optional[str] = None

WriteResult fields (exact 3 fields):
- [ ] num_output_rows: int
- [ ] operation: str = "WRITE"
- [ ] metrics: Dict[str, Any] = field(default_factory=dict)

CheckResult fields (exact 4 fields):
- [ ] rule_id: str
- [ ] passed: bool
- [ ] failed_count: int
- [ ] action: str

### 10.3 Protocol Validation
Engine protocol (exact 1 method):
- [ ] run(self, context: RunContext) -> RunResult

Reader protocol (exact 1 method):
- [ ] read(self, source: SourceConfig, load: LoadConfig) -> DataFrame

LoadStrategy protocol (exact 1 method):
- [ ] apply(self, df: DataFrame, target: TargetConfig, load: LoadConfig, options: Optional[Dict[str, str]] = None) -> WriteResult

Check protocol (exact 1 method):
- [ ] evaluate(self, df: DataFrame, rule: DQRuleConfig) -> CheckResult

Masker protocol (exact 1 method):
- [ ] mask(self, df: DataFrame, rules: List[MaskingRuleConfig]) -> DataFrame

### 10.4 Import Validation
Required imports (each file):
- [ ] from __future__ import annotations
- [ ] from typing import Protocol, runtime_checkable
- [ ] from dataclasses import dataclass, field
- [ ] from typing import TYPE_CHECKING
- [ ] if TYPE_CHECKING: from pyspark.sql import DataFrame

### 10.5 Export Validation
__init__.py exports (exact 9 items):
- [ ] __version__ = "0.2.0"
- [ ] RunContext
- [ ] RunResult
- [ ] Engine
- [ ] Reader
- [ ] LoadStrategy
- [ ] WriteResult
- [ ] Check
- [ ] CheckResult
- [ ] Masker

### 10.6 Automated Validation Script
```python
# validation/validate_contracts.py
def validate_contracts():
    # Check file count
    files = list(Path("src/core/contracts").glob("*.py"))
    assert len(files) == 6, f"Expected 6 files, got {len(files)}"
    
    # Check dataclass field counts
    from core.contracts import RunContext, RunResult, WriteResult, CheckResult
    assert len(RunContext.__dataclass_fields__) == 4
    assert len(RunResult.__dataclass_fields__) == 3
    assert len(WriteResult.__dataclass_fields__) == 3
    assert len(CheckResult.__dataclass_fields__) == 4
    
    # Check protocol method counts
    from core.contracts import Engine, Reader, LoadStrategy, Check, Masker
    assert len([m for m in dir(Engine) if not m.startswith('_')]) == 1
    assert len([m for m in dir(Reader) if not m.startswith('_')]) == 1
    # ... etc
    
    # Check version
    from core.contracts import __version__
    assert __version__ == "0.2.0"
    
    print("✅ All validation checks passed!")
```
```

**Recommended Action:** Add §10 with validation checklist and script. Estimated effort: 30 minutes.

---

## Component 2: core.sdk / ABC (abc-sdk-spec.md)

### ✅ What's Already Prescriptive

**§3 Interface - GOOD:**
```python
# Lines 85-174 provide:
@dataclass
class RunHandle:
    run_id: str
    trace_id: str

class ABC:
    def __init__(self, catalog: str = "insurelake_abc", schema: str = "config", spark: Optional[SparkSession] = None): ...
    def start_run(self, component: str, entity: str, run_type: str, trace_id: Optional[str] = None) -> RunHandle: ...
    def end_run(self, run_id: str, status: str, metrics: Optional[Dict] = None): ...
    def log_audit(self, run_id: str, metrics: Dict): ...
    def log_balance(self, run_id: str, checks: List[Dict]): ...
    def log_dq(self, run_id: str, results: List[Dict]): ...
    def log_exception(self, run_id: str, error: Exception): ...
    def log_cost(self, run_id: str, consumption: Dict): ...
```
- ✅ Complete ABC class signature
- ✅ All 7 method signatures specified
- ✅ RunHandle dataclass complete

**§6 Logic - PROSE (needs code):**
```markdown
### start_run() Flow
1. Generate UUID for `run_id`
2. Generate or accept `trace_id`
3. Insert RUNNING status into `abc_audit`
4. Return `RunHandle(run_id, trace_id)`
```
- ⚠️ This is prose, not code
- ⚠️ "Generate UUID" - which library? uuid.uuid4()? uuid.uuid1()?
- ⚠️ "Insert RUNNING status" - using spark.sql? DataFrame API?

### ⚠️ What Needs Enhancement

**§6 Logic - Convert to Exact Code:**

**Current (prose):**
```markdown
### start_run() Flow
1. Generate UUID for `run_id`
2. Generate or accept `trace_id`
3. Insert RUNNING status into `abc_audit`
4. Return `RunHandle(run_id, trace_id)`
```

**Should be (exact code):**
```python
def start_run(
    self,
    component: str,
    entity: str,
    run_type: str,
    trace_id: Optional[str] = None
) -> RunHandle:
    """Start a new run and return RunHandle."""
    import uuid
    from datetime import datetime
    from pyspark.sql.functions import col, lit
    
    # Step 1: Generate run_id
    run_id = str(uuid.uuid4())
    
    # Step 2: Generate or accept trace_id
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    
    # Step 3: Get current identity
    identity = self.spark.conf.get("spark.databricks.user.email", "unknown")
    
    # Step 4: Insert RUNNING status into abc_audit (idempotent upsert)
    audit_data = {
        "run_id": run_id,
        "trace_id": trace_id,
        "component": component,
        "entity": entity,
        "run_type": run_type,
        "status": "RUNNING",
        "start_ts": datetime.utcnow(),
        "identity": identity,
        "created_ts": datetime.utcnow()
    }
    
    try:
        df = self.spark.createDataFrame([audit_data])
        df.write.format("delta").mode("append").saveAsTable(
            f"{self.catalog}.{self.schema}.abc_audit"
        )
    except Exception as e:
        # Resilience: log warning, continue
        logger.warning(f"ABC write failed: {e}")
        self._write_local_fallback("abc_audit", audit_data)
    
    # Step 5: Return handle
    return RunHandle(run_id=run_id, trace_id=trace_id)
```

**Similarly for all other methods:**
- `end_run()` - exact upsert logic
- `log_audit()` - exact merge/upsert pattern
- `log_balance()` - exact write with FK handling
- `log_dq()` - exact pattern
- `log_exception()` - exact exception serialization
- `log_cost()` - exact cost data structure

**Missing §10 Validation Section:**

```markdown
## 10. Generation Validation

### 10.1 File Structure
Required files (exact 4 files):
- [ ] src/core/sdk/abc.py
- [ ] src/core/sdk/run_handle.py
- [ ] src/core/sdk/exceptions.py
- [ ] src/core/sdk/__init__.py

### 10.2 RunHandle Dataclass
Fields (exact 2 fields):
- [ ] run_id: str
- [ ] trace_id: str

### 10.3 ABC Class Methods
Must have exactly 9 methods:
- [ ] __init__(self, catalog: str = "insurelake_abc", schema: str = "abc", spark: Optional[SparkSession] = None)
- [ ] start_run(self, component: str, entity: str, run_type: str, trace_id: Optional[str] = None) -> RunHandle
- [ ] end_run(self, run_id: str, status: str, metrics: Optional[Dict] = None) -> None
- [ ] log_audit(self, run_id: str, metrics: Dict) -> None
- [ ] log_balance(self, run_id: str, checks: List[Dict]) -> None
- [ ] log_dq(self, run_id: str, results: List[Dict]) -> None
- [ ] log_exception(self, run_id: str, error: Exception) -> None
- [ ] log_cost(self, run_id: str, consumption: Dict) -> None
- [ ] _write_local_fallback(self, table: str, data: Dict) -> None (private helper)

### 10.4 Exception Classes
Must have exactly 3 exception classes:
- [ ] ABCConnectionError(Exception)
- [ ] ABCWriteError(Exception)
- [ ] ABCValidationError(Exception)

### 10.5 Implementation Pattern Validation
start_run() implementation must include:
- [ ] UUID generation using uuid.uuid4()
- [ ] Trace ID propagation logic
- [ ] INSERT into abc_audit table
- [ ] Resilience: try-except with warning log
- [ ] Returns RunHandle

end_run() implementation must include:
- [ ] UPDATE abc_audit with end_ts, duration, status
- [ ] Idempotent (safe to call multiple times)
- [ ] Resilience: try-except with warning log

All log_* methods must include:
- [ ] run_id validation (not None)
- [ ] Upsert semantics (MERGE or INSERT with conflict resolution)
- [ ] Resilience: ABC failures don't crash pipelines
- [ ] Local fallback on write failure

### 10.6 Idempotency Validation
Test: Call end_run() twice with same run_id
- [ ] Second call updates existing row (no duplicate)
- [ ] No error raised

Test: Call log_audit() twice with same run_id
- [ ] Second call merges metrics (upsert)
- [ ] No duplicate rows

### 10.7 Resilience Validation
Test: ABC table write fails (permissions error)
- [ ] Warning logged
- [ ] Local file written to /tmp/abc_fallback/
- [ ] Method returns normally (no exception raised)

### 10.8 Automated Validation Script
```python
# validation/validate_abc_sdk.py
def validate_abc_sdk():
    from core.sdk import ABC, RunHandle
    from core.sdk.exceptions import ABCConnectionError, ABCWriteError, ABCValidationError
    
    # Check RunHandle fields
    assert len(RunHandle.__dataclass_fields__) == 2
    
    # Check ABC methods
    abc_methods = [m for m in dir(ABC) if not m.startswith('_') or m == '_write_local_fallback']
    assert len(abc_methods) == 9, f"Expected 9 methods, got {len(abc_methods)}"
    
    # Check exception classes
    assert issubclass(ABCConnectionError, Exception)
    assert issubclass(ABCWriteError, Exception)
    assert issubclass(ABCValidationError, Exception)
    
    print("✅ All validation checks passed!")
```
```

**Recommended Action:** 
1. Convert §6 prose to exact code implementations (60 min)
2. Add §10 validation section (45 min)

---

## Component 3: core.metadata (config-model-spec.md)

### ❌ What's Missing / Ambiguous

**§3 Interface - INCOMPLETE:**

**Current:**
```python
class SourceConfig(BaseModel):
    source_id: str
    source_name: str
    source_type: SourceType  # ✅ Enum
    source_system: str
    # ... fields listed
    active_flag: bool = True
```

**Missing:**
- ❌ No `SourceType` enum definition (only mentioned)
- ❌ No `Layer` enum (just comment "BRONZE|SILVER|GOLD")
- ❌ No `TableType` enum (just comment "MANAGED|EXTERNAL")
- ❌ No `Format` enum (just "DELTA")
- ❌ No `LoadPattern` enum (just comment "APPEND|MERGE|UPSERT|OVERWRITE|SCD2")
- ❌ No `Engine` enum (just comment "AUTOLOADER|DECLARATIVE|STRUCTURED_STREAMING")
- ❌ No `DQRuleType` enum
- ❌ No `OnFailure` enum
- ❌ No `TransformType` enum
- ❌ No `SCDType` enum
- ❌ No `LoadType` enum

**§6 Logic - PROSE:**

**Current (lines 284-311):**
```markdown
- **Procedure:**
  1. ConfigLoader reads the requested config row from its UC table
  2. Resolve FK dependencies by ID lookup
  3. Validate before returning the typed object
  4. On any config write, append an ABC audit record
  5. Build the execution plan from load.engine

- **Decision rules:**
  - FK integrity: every source_id/target_id must resolve, else FKViolationError
  - Enum validation: source_type, load_pattern, engine must be valid enum values
  - Business rules: STREAM load types require watermark_column
```

**Problems:**
- ⚠️ "reads the requested config row" - HOW? spark.sql? spark.table().filter()?
- ⚠️ "Resolve FK dependencies by ID lookup" - EXACT pattern?
- ⚠️ No code fragments provided
- ⚠️ Business rules described in prose, not @model_validator code

**Should be:**
```python
# EXACT query pattern (REQUIRED - use this everywhere)
from pyspark.sql.functions import col, lit

def get_source(self, source_id: str) -> SourceConfig:
    table_name = f"{self.catalog}.{self.schema}.cfg_source"
    
    # REQUIRED: Use spark.table().filter() pattern (SQL injection safe)
    df = self.spark.table(table_name).filter(
        (col("source_id") == lit(source_id)) & (col("active_flag") == lit(True))
    )
    
    rows = df.collect()
    if not rows:
        raise ConfigNotFoundError(f"Source not found: {source_id}")
    
    row = rows[0]
    return SourceConfig(
        source_id=row.source_id,
        source_name=row.source_name,
        source_type=SourceType(row.source_type),
        # ... all fields explicitly mapped
    )

# EXACT FK validation pattern
def _fk_exists(self, table: str, id_col: str, id_val: str) -> bool:
    """Check if FK reference exists (optimized - no full SELECT)."""
    from pyspark.sql.functions import col, lit
    return self.spark.table(f"{self.catalog}.{self.schema}.{table}") \
        .filter((col(id_col) == lit(id_val)) & (col("active_flag") == lit(True))) \
        .limit(1).count() > 0

# EXACT business rule validation
class LoadConfig(BaseModel):
    # ... fields ...
    
    @model_validator(mode='after')
    def validate_business_rules(self) -> 'LoadConfig':
        """Validate cross-field business rules per spec §6."""
        
        # Rule 1: STREAM loads require watermark
        if self.load_type == LoadType.STREAM and not self.watermark_column:
            raise ValueError(
                "STREAM load types require watermark_column (spec §6)"
            )
        
        # Rule 2: SCD2 pattern requires merge keys
        if self.load_pattern == LoadPattern.SCD2 and not self.merge_keys:
            raise ValueError(
                "SCD2 load_pattern requires merge_keys (spec §6)"
            )
        
        # Rule 3: DECLARATIVE engine requires checkpoint
        if self.engine == Engine.DECLARATIVE and not self.checkpoint_location:
            raise ValueError(
                "DECLARATIVE engine requires checkpoint_location (spec §6)"
            )
        
        return self
```

**Missing §10 Validation Section:**

(See full checklist in earlier critical review - 11 enums, 5 models, ConfigLoader methods, query patterns, business validation)

**Recommended Action:**
1. Add complete enum definitions to §3 (30 min)
2. Convert §6 to exact code patterns (60 min)
3. Add comprehensive §10 validation section (90 min)
4. REGENERATE Component 3 code using updated spec (30 min)

**Total estimated: 3.5 hours**

---

## Summary & Recommendations

### Upgrade Priority

**🟢 Component 1 (contracts):** LOW priority
- Already 95% Option D compliant
- Only needs §10 validation section
- Estimated effort: 30 minutes

**🟡 Component 2 (ABC SDK):** MEDIUM priority
- Good interface, weak implementation logic
- Convert §6 prose to exact code
- Add §10 validation section
- Estimated effort: 2 hours

**🔴 Component 3 (config-model):** HIGH priority
- Major gaps in §3 (missing 11 enums)
- Weak §6 (prose vs. exact code)
- No §10 validation
- Requires code regeneration after spec update
- Estimated effort: 4 hours

### Recommended Execution Order

**Phase 3: Component 1 (contracts)** - 30 min
- Quick win, establishes validation pattern
- Template for other components

**Phase 4: Component 2 (ABC SDK)** - 2 hours
- Moderate complexity
- Builds on contracts pattern

**Phase 5: Component 3 (config-model)** - 4 hours
- Most complex, most critical
- Requires full regeneration

### Total Effort
- Analysis (Phase 1): ✅ DONE (1 hour)
- Framework Design (Phase 2): 45 min (next)
- Spec Updates (Phases 3-5): 6.5 hours
- **Grand Total: 8.25 hours**

---

**Next Step:** Proceed to Phase 2 (Design Validation Framework)?
