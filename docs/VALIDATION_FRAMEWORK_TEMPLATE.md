# Validation Framework Template (Option D)

**Purpose:** Reusable §10 template for all InsureLake component specs  
**Version:** 1.0  
**Date:** 2026-06-18

---

## Overview

Every spec MUST include a **§10 Generation Validation** section that enables mechanical verification of generated code against the spec. This framework defines the standard structure and patterns.

---

## §10 Template Structure

Every component's §10 section MUST include these subsections:

```markdown
## 10. Generation Validation

### 10.1 File Structure Validation
[Exact files expected, exact count, exact paths]

### 10.2 Interface Validation
[Exact classes, methods, fields, signatures with counts]

### 10.3 Enum Validation
[Exact enum names and values with counts - omit if no enums]

### 10.4 Implementation Pattern Validation
[Exact code patterns, forbidden patterns, query templates]

### 10.5 Import/Export Validation
[Exact imports, exports, dependencies]

### 10.6 Business Logic Validation
[Exact validators, decision rules, edge cases - omit if interface-only]

### 10.7 Automated Validation Script
[Python script that mechanically checks all above]
```

---

## Validation Principles

### 1. **Mechanical Checkability**
Every validation item MUST be programmatically checkable (no human judgment).

**✅ GOOD (mechanical):**
```markdown
- [ ] SourceConfig has exactly 15 fields
- [ ] LoadPattern enum has exactly 5 values: APPEND, MERGE, UPSERT, OVERWRITE, SCD2
- [ ] get_source() method uses spark.table().filter() pattern (no f-strings in WHERE)
```

**❌ BAD (subjective):**
```markdown
- [ ] Code is well-structured
- [ ] Error handling is appropriate
- [ ] Performance is optimized
```

### 2. **Exact Counts**
Specify exact numbers, not ranges or "at least."

**✅ GOOD:**
```markdown
- [ ] ABC class has exactly 8 public methods
- [ ] RunHandle dataclass has exactly 2 fields
```

**❌ BAD:**
```markdown
- [ ] ABC class has at least 7 methods
- [ ] RunHandle has a few fields
```

### 3. **Forbidden Patterns**
Explicitly list anti-patterns that MUST NOT appear.

```markdown
### Forbidden Patterns
- [ ] No f-string SQL interpolation (e.g., `spark.sql(f"SELECT * FROM {table}")`)
- [ ] No bare `except:` clauses
- [ ] No `Any` types in public signatures (except explicitly allowed)
- [ ] No direct imports of concrete implementations in Protocol files
```

### 4. **Query Safety**
All SQL/Spark queries MUST use safe patterns.

**Required Pattern (SQL-injection safe):**
```python
from pyspark.sql.functions import col, lit

# ✅ SAFE: Use spark.table().filter()
df = spark.table(table_name).filter(
    (col("id") == lit(user_input)) & (col("active") == lit(True))
)

# ❌ FORBIDDEN: f-string interpolation
df = spark.sql(f"SELECT * FROM {table} WHERE id = '{user_input}'")
```

---

## §10.1 File Structure Validation Template

```markdown
### 10.1 File Structure Validation

**Required files (exact {N} files, no more, no less):**

<component_path>/
├── file1.py          # Purpose: {description}
├── file2.py          # Purpose: {description}
├── file3.py          # Purpose: {description}
└── __init__.py       # Purpose: Package exports

**Validation checklist:**
- [ ] Exactly {N} .py files in {component_path}/
- [ ] All files listed above exist
- [ ] No additional .py files present
- [ ] __init__.py exports all public classes/functions

**Automated check:**
```python
from pathlib import Path

def validate_file_structure():
    component_path = Path("src/{component_path}")
    py_files = list(component_path.glob("*.py"))
    
    expected_files = {
        "file1.py",
        "file2.py",
        "file3.py",
        "__init__.py"
    }
    
    actual_files = {f.name for f in py_files}
    
    assert len(py_files) == {N}, f"Expected {N} files, got {len(py_files)}"
    assert actual_files == expected_files, f"File mismatch: {actual_files ^ expected_files}"
    
    print(f"✅ File structure valid: {N} files")
```
```

---

## §10.2 Interface Validation Template

```markdown
### 10.2 Interface Validation

**Classes:**
- [ ] {ClassName1} (dataclass/BaseModel/Protocol)
  - Field count: exactly {N} fields
  - Fields: {field1}: {type1}, {field2}: {type2}, ...
  
- [ ] {ClassName2} (Protocol)
  - Method count: exactly {M} public methods
  - Methods: {method1}({params}) -> {return_type}

**Validation checklist:**
- [ ] {ClassName1} has exactly {N} fields
- [ ] {ClassName1}.{field1} is type {type1}
- [ ] {ClassName2} is marked @runtime_checkable
- [ ] {ClassName2}.{method1} signature matches spec exactly

**Automated check:**
```python
def validate_interfaces():
    from {module} import {ClassName1}, {ClassName2}
    
    # Dataclass field count
    assert len({ClassName1}.__dataclass_fields__) == {N}, \
        f"Expected {N} fields in {ClassName1}"
    
    # Field types
    fields = {ClassName1}.__dataclass_fields__
    assert fields['{field1}'].type == {type1}
    
    # Protocol method count
    methods = [m for m in dir({ClassName2}) if not m.startswith('_')]
    assert len(methods) == {M}, f"Expected {M} methods in {ClassName2}"
    
    print(f"✅ Interfaces valid")
```
```

---

## §10.3 Enum Validation Template

```markdown
### 10.3 Enum Validation

**Enums (if applicable):**

**{EnumName1} (exactly {N} values):**
- [ ] {VALUE1}
- [ ] {VALUE2}
- [ ] {VALUE3}

**{EnumName2} (exactly {M} values):**
- [ ] {VALUE1}
- [ ] {VALUE2}

**Validation checklist:**
- [ ] {EnumName1} has exactly {N} values
- [ ] {EnumName1} values match spec exactly
- [ ] All enum values are uppercase with underscores

**Automated check:**
```python
def validate_enums():
    from {module} import {EnumName1}, {EnumName2}
    
    # Check value count
    assert len({EnumName1}) == {N}, f"Expected {N} values in {EnumName1}"
    
    # Check exact values
    expected_values = {'{VALUE1}', '{VALUE2}', '{VALUE3}'}
    actual_values = {e.value for e in {EnumName1}}
    assert actual_values == expected_values, \
        f"Enum value mismatch: {actual_values ^ expected_values}"
    
    print(f"✅ Enums valid")
```
```

---

## §10.4 Implementation Pattern Validation Template

```markdown
### 10.4 Implementation Pattern Validation

**Required Patterns:**

**Pattern 1: {PatternName} (e.g., Safe Query Pattern)**
```python
# REQUIRED: Use this exact pattern for all queries
from pyspark.sql.functions import col, lit

df = spark.table(table_name).filter(
    (col("id_column") == lit(id_value)) & 
    (col("active_flag") == lit(True))
)
```

**Pattern 2: {PatternName} (e.g., FK Validation Pattern)**
```python
# REQUIRED: Use existence check, not full SELECT
def _fk_exists(self, table: str, id_col: str, id_val: str) -> bool:
    return self.spark.table(f"{self.catalog}.{self.schema}.{table}") \
        .filter((col(id_col) == lit(id_val)) & (col("active_flag") == lit(True))) \
        .limit(1).count() > 0
```

**Forbidden Patterns:**
- [ ] No f-string SQL: `spark.sql(f"SELECT * FROM {table} WHERE id = '{value}'")`
- [ ] No bare except: `except:` (must specify exception type)
- [ ] No broad except: `except Exception:` for business logic (catch specific)
- [ ] No return None for FK validation (return bool or raise)

**Validation checklist:**
- [ ] All Spark queries use spark.table().filter() with col() and lit()
- [ ] No f-string interpolation in SQL strings
- [ ] All FK checks use optimized existence pattern
- [ ] All exceptions are typed (no bare except)

**Automated check:**
```python
import ast
import re

def validate_patterns():
    # Parse source code
    with open('src/{component}/{file}.py') as f:
        tree = ast.parse(f.read())
    
    # Check for forbidden f-string SQL
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if hasattr(node.func, 'attr') and node.func.attr == 'sql':
                for arg in node.args:
                    if isinstance(arg, ast.JoinedStr):  # f-string
                        raise AssertionError(
                            f"Forbidden f-string SQL found at line {node.lineno}"
                        )
    
    # Check for bare except
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                raise AssertionError(
                    f"Bare except clause found at line {node.lineno}"
                )
    
    print(f"✅ Implementation patterns valid")
```
```

---

## §10.5 Import/Export Validation Template

```markdown
### 10.5 Import/Export Validation

**__init__.py exports (exactly {N} items):**
- [ ] __version__ = "{version}"
- [ ] {Export1}
- [ ] {Export2}
- [ ] {Export3}

**Required imports (each module):**
- [ ] from __future__ import annotations
- [ ] from typing import ...
- [ ] from pydantic import BaseModel (if using Pydantic)

**Forbidden imports:**
- [ ] No direct concrete imports in Protocol files (use TYPE_CHECKING)
- [ ] No pyspark imports outside TYPE_CHECKING (for Protocol files)

**Validation checklist:**
- [ ] __init__.py exports exactly {N} public items
- [ ] __version__ matches spec version
- [ ] All Protocol files use TYPE_CHECKING for DataFrame
- [ ] No circular imports

**Automated check:**
```python
def validate_imports_exports():
    # Check __init__.py exports
    import {module}
    
    exports = [name for name in dir({module}) if not name.startswith('_')]
    exports.append('__version__')  # Include version
    
    expected_exports = {N}
    assert len(exports) == expected_exports, \
        f"Expected {expected_exports} exports, got {len(exports)}"
    
    # Check version
    assert {module}.__version__ == "{version}"
    
    print(f"✅ Imports/exports valid")
```
```

---

## §10.6 Business Logic Validation Template

```markdown
### 10.6 Business Logic Validation

**(Omit this section for interface-only components like contracts)**

**Business Rules:**

**Rule 1: {RuleName}**
- **Trigger:** {condition}
- **Validation:** {validation_logic}
- **Error:** {ErrorType}("{error_message}")

**Example:**
```python
@model_validator(mode='after')
def validate_stream_watermark(self) -> 'LoadConfig':
    """Validate STREAM loads require watermark (spec §6, Rule 1)."""
    if self.load_type == LoadType.STREAM and not self.watermark_column:
        raise ValueError(
            "STREAM load_type requires watermark_column (spec §6, Rule 1)"
        )
    return self
```

**Validation checklist:**
- [ ] Rule 1 implemented as @model_validator
- [ ] Rule 1 raises {ErrorType} with exact message
- [ ] Rule 2 implemented as @model_validator
- [ ] All rules reference spec section (e.g., "spec §6, Rule 1")

**Automated check:**
```python
def validate_business_rules():
    from {module} import {Model}
    import pytest
    
    # Test Rule 1: STREAM requires watermark
    with pytest.raises(ValueError, match="STREAM.*watermark"):
        {Model}(
            load_type=LoadType.STREAM,
            watermark_column=None,  # Missing watermark
            # ... other required fields
        )
    
    print(f"✅ Business rules valid")
```
```

---

## §10.7 Automated Validation Script Template

```markdown
### 10.7 Automated Validation Script

**Script location:** `validation/validate_{component_name}.py`

**Usage:**
```bash
# From repo root
python validation/validate_{component_name}.py

# Expected output:
# ✅ File structure valid: {N} files
# ✅ Interfaces valid
# ✅ Enums valid (if applicable)
# ✅ Implementation patterns valid
# ✅ Imports/exports valid
# ✅ Business rules valid (if applicable)
# ✅ All {component_name} validation checks passed!
```

**Complete script template:**
```python
#!/usr/bin/env python3
"""
Validation script for {component_name} component.
Mechanically verifies generated code matches spec §10.

Usage:
    python validation/validate_{component_name}.py
"""

import sys
from pathlib import Path
import ast

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def validate_file_structure():
    """§10.1: Validate file structure."""
    component_path = Path("src/{component_path}")
    py_files = list(component_path.glob("*.py"))
    
    expected_count = {N}
    actual_count = len(py_files)
    
    assert actual_count == expected_count, \
        f"Expected {expected_count} files, got {actual_count}"
    
    print(f"✅ File structure valid: {expected_count} files")

def validate_interfaces():
    """§10.2: Validate class interfaces."""
    from {module} import {ClassName1}, {ClassName2}
    
    # Check field/method counts
    # ... (see §10.2 template)
    
    print(f"✅ Interfaces valid")

def validate_enums():
    """§10.3: Validate enum definitions."""
    # ... (see §10.3 template)
    print(f"✅ Enums valid")

def validate_patterns():
    """§10.4: Validate implementation patterns."""
    # ... (see §10.4 template)
    print(f"✅ Implementation patterns valid")

def validate_imports_exports():
    """§10.5: Validate imports and exports."""
    # ... (see §10.5 template)
    print(f"✅ Imports/exports valid")

def validate_business_rules():
    """§10.6: Validate business logic."""
    # ... (see §10.6 template)
    print(f"✅ Business rules valid")

def main():
    """Run all validation checks."""
    try:
        validate_file_structure()
        validate_interfaces()
        validate_enums()  # Skip if no enums
        validate_patterns()
        validate_imports_exports()
        validate_business_rules()  # Skip if interface-only
        
        print("\n" + "="*60)
        print(f"✅ All {component_name} validation checks passed!")
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
```

---

## Usage Guidelines

### For Spec Authors

When writing/updating a spec, use this template to create §10:

1. **Copy the template structure** - Use all 7 subsections
2. **Fill in exact values** - Replace `{N}`, `{ClassName}`, etc. with actual values
3. **Add component-specific checks** - Extend with domain-specific validation
4. **Write the validation script** - Use §10.7 template
5. **Test the script** - Ensure it passes on conformant code, fails on non-conformant

### For Code Generators

When generating code from a spec:

1. **Read §10 first** - Understand validation requirements
2. **Generate to pass §10** - Code must pass all validation checks
3. **Run validation script** - Execute `validation/validate_{component}.py` after generation
4. **Fix failures** - Iterate until all checks pass

### For Code Reviewers

When reviewing generated code:

1. **Run validation script** - `python validation/validate_{component}.py`
2. **Check script output** - Must show all ✅ checks passing
3. **Spot-check key items** - Verify a sample of validation items manually
4. **Approve only if valid** - Do not approve if validation script fails

---

## Examples

See these specs for reference implementations:
- `specs/foundation/contracts-spec.md` (interface-only, no business rules)
- `specs/foundation/abc-sdk-spec.md` (medium complexity)
- `specs/foundation/config-model-spec.md` (high complexity with enums + validators)

---

**END OF TEMPLATE**
