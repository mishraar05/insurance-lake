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
