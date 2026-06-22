# Phase 2 Complete: Validation Framework Designed

**Date:** 2026-06-18  
**Status:** ✅ COMPLETE  
**Duration:** 45 minutes (estimated)

---

## Deliverables

### 1. Validation Framework Template
**File:** `insurance-lake/docs/VALIDATION_FRAMEWORK_TEMPLATE.md`

**Contents:**
- Complete §10 template structure (7 subsections)
- Validation principles (mechanical, exact counts, forbidden patterns, query safety)
- Templates for each §10 subsection (10.1-10.7)
- Automated validation script template
- Usage guidelines for spec authors, code generators, and reviewers

---

## Key Framework Features

### 🎯 Mechanical Validation
Every check is programmatically verifiable:
- ✅ Exact counts (fields, methods, enums, files)
- ✅ Type signature matching
- ✅ AST analysis for forbidden patterns (f-string SQL, bare except)
- ✅ Import/export verification

### 🚫 Forbidden Pattern Detection
Automated detection of:
- SQL injection vulnerabilities (f-string interpolation)
- Bare exception handlers
- Broad exception catching in business logic
- Missing type hints
- Circular imports

### 📋 Seven Standard Subsections
1. **§10.1 File Structure** - Exact file count, paths, tree structure
2. **§10.2 Interface** - Classes, methods, fields with exact signatures
3. **§10.3 Enums** - Exact enum names and values
4. **§10.4 Implementation Patterns** - Required patterns, forbidden anti-patterns
5. **§10.5 Imports/Exports** - Package exports, version, dependencies
6. **§10.6 Business Logic** - Validators, decision rules (omit if interface-only)
7. **§10.7 Automated Script** - Complete Python validation script

---

## Application to Each Component

### Component 1: core.contracts (LOW priority)
**§10 Additions Needed:**
- §10.1 File Structure: 6 files (engine, reader, load_strategy, check, masker, __init__)
- §10.2 Interface: 4 dataclasses + 5 Protocols with exact field/method counts
- §10.3 Enums: OMIT (no enums)
- §10.4 Implementation Patterns: OMIT (interface-only, method bodies are `...`)
- §10.5 Imports/Exports: 9 exports in __init__.py, TYPE_CHECKING pattern
- §10.6 Business Logic: OMIT (interface-only)
- §10.7 Automated Script: validate_contracts.py

**Estimated Effort:** 30 minutes

---

### Component 2: core.sdk (ABC) (MEDIUM priority)
**§10 Additions Needed:**
- §10.1 File Structure: 4 files (abc, run_handle, exceptions, __init__)
- §10.2 Interface: RunHandle dataclass (2 fields), ABC class (8 methods), 3 exceptions
- §10.3 Enums: OMIT (no enums)
- §10.4 Implementation Patterns: 
  - UUID generation (uuid.uuid4())
  - Idempotent upsert pattern
  - Resilience pattern (try-except with warning log)
  - Local fallback pattern
- §10.5 Imports/Exports: ABC, RunHandle, exceptions, __version__
- §10.6 Business Logic:
  - start_run() implementation
  - end_run() idempotency
  - log_* resilience
  - _write_local_fallback() helper
- §10.7 Automated Script: validate_abc_sdk.py

**ALSO NEEDS:** §6 upgrade from prose to exact code implementations

**Estimated Effort:** 2 hours (1 hour for §6 upgrade, 1 hour for §10)

---

### Component 3: core.metadata (HIGH priority)
**§10 Additions Needed:**
- §10.1 File Structure: 7 files (source, target, load, transform, dq_rule, config_loader, __init__)
- §10.2 Interface: 5 Pydantic models with exact field counts
- §10.3 Enums: 11 enums (SourceType, LoadType, LoadPattern, Engine, Layer, TableType, Format, DQRuleType, OnFailure, TransformType, SCDType) with exact value counts
- §10.4 Implementation Patterns:
  - Safe query pattern (spark.table().filter() with col/lit)
  - FK existence check pattern (optimized, no full SELECT)
  - NO f-string SQL interpolation
- §10.5 Imports/Exports: All models, ConfigLoader, enums, __version__
- §10.6 Business Logic:
  - LoadConfig validators (STREAM/watermark, SCD2/merge_keys, DECLARATIVE/checkpoint)
  - TargetConfig validators (EXTERNAL/location)
  - DQRuleConfig validators
  - ConfigLoader FK validation logic
- §10.7 Automated Script: validate_config_model.py

**ALSO NEEDS:** 
- §3 upgrade: Add 11 complete enum definitions
- §6 upgrade: Convert prose to exact code patterns

**Estimated Effort:** 4 hours (2 hours for §3+§6 upgrade, 2 hours for §10)

---

## Framework Standards Established

### Query Safety Standard
**REQUIRED pattern (everywhere):**
```python
from pyspark.sql.functions import col, lit

df = spark.table(table_name).filter(
    (col("id") == lit(user_value)) & (col("active_flag") == lit(True))
)
```

**FORBIDDEN pattern (detect with AST):**
```python
# ❌ SQL injection vulnerability
df = spark.sql(f"SELECT * FROM {table} WHERE id = '{user_value}'")
```

### Exception Handling Standard
**REQUIRED:**
```python
try:
    operation()
except SpecificError as e:  # Typed exception
    handle_error(e)
```

**FORBIDDEN:**
```python
try:
    operation()
except:  # Bare except
    pass
```

### Validation Script Standard
Every component gets a `validation/validate_{component}.py` script that:
1. Runs all §10 checks automatically
2. Prints ✅ for each passing check
3. Returns exit code 0 (pass) or 1 (fail)
4. Provides clear error messages on failure

---

## Next Steps

**Phase 3: Update contracts-spec.md (30 min)**
- Add §10 section using framework template
- Create validation/validate_contracts.py
- Run validation on existing code
- Verify all checks pass

**Phase 4: Update abc-sdk-spec.md (2 hours)**
- Upgrade §6 from prose to exact code
- Add §10 section using framework template
- Create validation/validate_abc_sdk.py
- Regenerate ABC SDK code (if needed)
- Run validation

**Phase 5: Update config-model-spec.md (4 hours)**
- Add 11 complete enum definitions to §3
- Upgrade §6 from prose to exact code patterns
- Add §10 section using framework template
- Create validation/validate_config_model.py
- REGENERATE all config-model code
- Run validation

---

## Success Criteria

✅ Phase 2 is complete when:
- [x] VALIDATION_FRAMEWORK_TEMPLATE.md created with all 7 subsections
- [x] Templates include both checklist and automated script patterns
- [x] Query safety standards defined
- [x] Exception handling standards defined
- [x] Validation script structure defined
- [x] Application plan documented for all 3 components

**Status:** ✅ ALL CRITERIA MET

---

**Ready to proceed to Phase 3: Update contracts-spec.md**

