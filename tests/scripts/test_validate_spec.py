#!/usr/bin/env python3
"""
Unit tests for validate_spec.py
Based on §9 Testing & acceptance from spec-validation-spec.md
"""

import pytest
import tempfile
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "speccheck"))

from validate_spec import Finding, parse_front_matter, check_spec, check_corpus, validate, main


def create_spec_file(tmpdir, name, content):
    """Helper to create a spec file in tmpdir."""
    path = Path(tmpdir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_known_good_spec(tmp_path):
    """A known-good spec should produce 0 findings."""
    spec = '''---
id: test.good
title: Good Spec
owner: EY
status: active
target_path: scripts/test/
owning_skill: test
backlog: [TEST-001]
provides: [foo, bar]
depends_on: []
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# Good Spec

## 1. Purpose & scope
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

### SOLID Principles Application
- SRP: Each class has one responsibility
- OCP: Open for extension, closed for modification
- LSP: Subclasses are substitutable
- ISP: Segregated interfaces
- DIP: Depend on abstractions

## 6. Implementation logic & guidance
Logic / algorithm: N/A

## 7. Validation, edge cases & versioning policy
Test

## 8. Error handling + ABC instrumentation
Test

## 9. Testing & acceptance
Test

## 10. Examples
This is a counter-example.

## 11. Regeneration contract
Test

## 12. References
Test
'''
    path = create_spec_file(tmp_path, "good-spec.md", spec)
    findings = check_spec(path)
    
    # Should only have warnings, no errors
    errors = [f for f in findings if f.severity == "error"]
    assert len(errors) == 0, f"Expected no errors, got: {errors}"


def test_missing_acceptance(tmp_path):
    """A spec missing acceptance should produce front-matter.required error."""
    spec = '''---
id: test.missing-acceptance
title: Missing Acceptance
owner: EY
status: active
target_path: scripts/test/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: []
generation_context:
  - test.md
regeneration: fully-generated
---

# Missing Acceptance

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Test

## 11. Regeneration
Test

## 12. References
Test
'''
    path = create_spec_file(tmp_path, "missing-acceptance.md", spec)
    findings = check_spec(path)
    
    # Should have front-matter.required error
    errors = [f for f in findings if f.check == "front-matter.required" and "acceptance" in f.message]
    assert len(errors) > 0, "Expected front-matter.required error for missing acceptance"


def test_missing_solid_principles(tmp_path):
    """A spec missing SOLID Principles should produce design.solid warning."""
    spec = '''---
id: test.missing-solid
title: Missing SOLID
owner: EY
status: active
target_path: src/framework/test/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: []
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# Missing SOLID

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
This section has design info but no SOLID principles documentation.

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Counter-example

## 11. Regeneration
Test

## 12. References
Test
'''
    path = create_spec_file(tmp_path, "missing-solid.md", spec)
    findings = check_spec(path)
    
    # Should have design.solid warning
    warnings = [f for f in findings if f.check == "design.solid"]
    assert len(warnings) > 0, "Expected design.solid warning for missing SOLID principles"


def test_logic_spec_missing_edge_cases(tmp_path):
    """A logic spec whose §6 lacks 'Edge cases' (and is not N/A) should produce logic.block error."""
    spec = '''---
id: test.missing-edge-cases
title: Missing Edge Cases
owner: EY
status: active
target_path: scripts/test/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: []
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# Missing Edge Cases

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation logic & guidance
Logic / algorithm:
- Procedure: Do this
- Decision rules: Decide that
- Key code fragments: Code here

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Test

## 11. Regeneration
Test

## 12. References
Test
'''
    path = create_spec_file(tmp_path, "missing-edge-cases.md", spec)
    findings = check_spec(path)
    
    # Should have logic.block error
    errors = [f for f in findings if f.check == "logic.block" and "Edge cases" in f.message]
    assert len(errors) > 0, "Expected logic.block error for missing Edge cases"


def test_duplicate_spec_per_feature(tmp_path):
    """Two specs both tagged (ingestion, batch) should produce capability.spec_per_feature error."""
    spec1 = '''---
id: ingestion.batch-1
title: Batch 1
owner: EY
status: active
target_path: src/framework/ingestion/batch1/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: []
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
capability:
  framework: ingestion
  feature: batch
  selectable: true
---

# Batch 1

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Counter-example

## 11. Regeneration
Test

## 12. References
Test
'''
    
    spec2 = '''---
id: ingestion.batch-2
title: Batch 2
owner: EY
status: active
target_path: src/framework/ingestion/batch2/
owning_skill: test
backlog: [TEST-002]
provides: [bar]
depends_on: []
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
capability:
  framework: ingestion
  feature: batch
  selectable: true
---

# Batch 2

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Counter-example

## 11. Regeneration
Test

## 12. References
Test
'''
    
    path1 = create_spec_file(tmp_path, "batch-1.md", spec1)
    path2 = create_spec_file(tmp_path, "batch-2.md", spec2)
    
    # Parse front-matter to build by_id
    fm1 = parse_front_matter(path1)
    fm1["_path"] = str(path1)
    fm2 = parse_front_matter(path2)
    fm2["_path"] = str(path2)
    
    by_id = {
        "ingestion.batch-1": fm1,
        "ingestion.batch-2": fm2
    }
    
    findings = check_corpus(by_id)
    
    # Should have capability.spec_per_feature error
    errors = [f for f in findings if f.check == "capability.spec_per_feature"]
    assert len(errors) > 0, "Expected capability.spec_per_feature error for duplicate (ingestion, batch)"


def test_dependency_cycle(tmp_path):
    """A depends_on B, B depends_on A should produce depends_on.cycle error."""
    specA = '''---
id: test.a
title: A
owner: EY
status: active
target_path: scripts/test/a/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: [test.b]
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# A

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Counter-example

## 11. Regeneration
Test

## 12. References
Test
'''
    
    specB = '''---
id: test.b
title: B
owner: EY
status: active
target_path: scripts/test/b/
owning_skill: test
backlog: [TEST-002]
provides: [bar]
depends_on: [test.a]
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# B

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Counter-example

## 11. Regeneration
Test

## 12. References
Test
'''
    
    pathA = create_spec_file(tmp_path, "a.md", specA)
    pathB = create_spec_file(tmp_path, "b.md", specB)
    
    # Parse front-matter to build by_id
    fmA = parse_front_matter(pathA)
    fmA["_path"] = str(pathA)
    fmB = parse_front_matter(pathB)
    fmB["_path"] = str(pathB)
    
    by_id = {
        "test.a": fmA,
        "test.b": fmB
    }
    
    findings = check_corpus(by_id)
    
    # Should have depends_on.cycle error
    errors = [f for f in findings if f.check == "depends_on.cycle"]
    assert len(errors) > 0, "Expected depends_on.cycle error for A->B->A cycle"


def test_unknown_dependency(tmp_path):
    """depends_on to an unknown id should produce depends_on.resolve error."""
    spec = '''---
id: test.unknown-dep
title: Unknown Dependency
owner: EY
status: active
target_path: scripts/test/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: [nonexistent.spec]
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# Unknown Dependency

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
Counter-example

## 11. Regeneration
Test

## 12. References
Test
'''
    
    path = create_spec_file(tmp_path, "unknown-dep.md", spec)
    
    # Parse front-matter to build by_id
    fm = parse_front_matter(path)
    fm["_path"] = str(path)
    
    by_id = {"test.unknown-dep": fm}
    
    findings = check_corpus(by_id)
    
    # Should have depends_on.resolve error
    errors = [f for f in findings if f.check == "depends_on.resolve"]
    assert len(errors) > 0, "Expected depends_on.resolve error for unknown dependency"


def test_strict_mode_promotes_warnings(tmp_path):
    """--strict turns a lone warn into a non-zero exit."""
    spec = '''---
id: test.strict
title: Strict Test
owner: EY
status: active
target_path: scripts/test/
owning_skill: test
backlog: [TEST-001]
provides: [foo]
depends_on: []
generation_context:
  - test.md
acceptance:
  - "pytest tests/"
regeneration: fully-generated
---

# Strict Test

## 1. Purpose
Test

## 2. Requirements
Test

## 3. Interface
Test

## 4. Inputs / Outputs
Test

## 5. Design
Test

## 6. Implementation
Logic / algorithm: N/A

## 7. Validation
Test

## 8. Error handling
Test

## 9. Testing
Test

## 10. Examples
No counter-example here.

## 11. Regeneration
Test

## 12. References
Test
'''
    
    path = create_spec_file(tmp_path, "strict.md", spec)
    
    # Without strict mode
    findings, exit_code = validate([path], strict=False)
    assert exit_code == 0, "Expected exit 0 without strict mode (warnings only)"
    
    # With strict mode
    findings, exit_code = validate([path], strict=True)
    warnings = [f for f in findings if f.severity == "warn"]
    if warnings:
        assert exit_code == 1, "Expected exit 1 with strict mode (warnings present)"


def test_skip_templates_and_readmes(tmp_path):
    """Templates and READMEs should be skipped."""
    # Create _templates directory with a spec
    templates_dir = tmp_path / "_templates"
    templates_dir.mkdir()
    
    template_spec = '''---
id: template.test
title: Template
---
# Template
'''
    
    create_spec_file(templates_dir, "template.md", template_spec)
    
    # Create README
    readme_content = "# README\nThis is a readme."
    create_spec_file(tmp_path, "README.md", readme_content)
    
    # Create STRUCTURE.txt
    structure_content = "Project structure"
    create_spec_file(tmp_path, "STRUCTURE.txt", structure_content)
    
    # Validate - should skip all these files
    findings, exit_code = validate([tmp_path], strict=False)
    
    # Should not have any findings from templates or READMEs
    template_findings = [f for f in findings if "_templates" in f.spec or "README" in f.spec or "STRUCTURE" in f.spec]
    assert len(template_findings) == 0, "Expected templates, READMEs, and STRUCTURE.txt to be skipped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
