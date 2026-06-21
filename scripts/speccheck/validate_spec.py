#!/usr/bin/env python3
"""
Spec Validator - validates that any spec is well-formed and registry-ready.
Machine-checkable half of Quality Gate #1 (spec authored / structured) and #2 (placement mapped).
"""

import re
import sys
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ============================================================================
# § 3. Interface (verbatim from spec)
# ============================================================================

@dataclass
class Finding:
    spec: str          # spec file path
    check: str         # check id, e.g. "front-matter.required"
    severity: str      # "error" | "warn"
    message: str


def parse_front_matter(path: Path) -> dict:
    """Parse YAML front-matter from a spec file. Raises on malformed."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("no front-matter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("front-matter not closed")
    return yaml.safe_load(parts[1])


def check_spec(path: Path) -> list[Finding]:
    """Per-spec checks: front-matter + sections + §6 logic."""
    findings = []
    
    try:
        fm = parse_front_matter(path)
    except Exception as e:
        findings.append(Finding(
            spec=str(path),
            check="front-matter.parse",
            severity="error",
            message=f"malformed front-matter: {e}"
        ))
        return findings  # Skip remaining checks
    
    # Validate it's a dict
    if not isinstance(fm, dict):
        findings.append(Finding(
            spec=str(path),
            check="front-matter.parse",
            severity="error",
            message="front-matter is not a mapping"
        ))
        return findings
    
    # front-matter.required
    for key in REQUIRED:
        if key not in fm:
            findings.append(Finding(
                spec=str(path),
                check="front-matter.required",
                severity="error",
                message=f"missing key: {key}"
            ))
    
    # front-matter.enum
    if "status" in fm and fm["status"] not in {"draft", "active", "implemented"}:
        findings.append(Finding(
            spec=str(path),
            check="front-matter.enum",
            severity="error",
            message=f"invalid status: {fm['status']}"
        ))
    if "regeneration" in fm and fm["regeneration"] not in {"fully-generated", "scaffold-then-edit"}:
        findings.append(Finding(
            spec=str(path),
            check="front-matter.enum",
            severity="error",
            message=f"invalid regeneration: {fm['regeneration']}"
        ))
    if "capability" in fm and isinstance(fm["capability"], dict):
        if "selectable" in fm["capability"] and fm["capability"]["selectable"] not in {True, False}:
            findings.append(Finding(
                spec=str(path),
                check="front-matter.enum",
                severity="error",
                message=f"invalid capability.selectable: {fm['capability']['selectable']}"
            ))
    
    # front-matter.type
    for key in ["backlog", "provides", "depends_on", "generation_context", "acceptance"]:
        if key in fm and not isinstance(fm[key], list):
            findings.append(Finding(
                spec=str(path),
                check="front-matter.type",
                severity="error",
                message=f"{key} must be a list"
            ))
    
    # acceptance and generation_context must be non-empty
    if "acceptance" in fm and isinstance(fm["acceptance"], list) and len(fm["acceptance"]) == 0:
        findings.append(Finding(
            spec=str(path),
            check="front-matter.type",
            severity="error",
            message="acceptance must be non-empty"
        ))
    if "generation_context" in fm and isinstance(fm["generation_context"], list) and len(fm["generation_context"]) == 0:
        findings.append(Finding(
            spec=str(path),
            check="front-matter.type",
            severity="error",
            message="generation_context must be non-empty"
        ))
    
    # capability must be a mapping
    if "capability" in fm and not isinstance(fm["capability"], dict):
        findings.append(Finding(
            spec=str(path),
            check="front-matter.type",
            severity="error",
            message="capability must be a mapping"
        ))
    
    # id.format
    if "id" in fm and not ID_RE.match(fm["id"]):
        findings.append(Finding(
            spec=str(path),
            check="id.format",
            severity="error",
            message=f"id does not match pattern: {fm['id']}"
        ))
    
    # target_path.tier
    if "target_path" in fm:
        tp = fm["target_path"]
        if not any(tp.startswith(tier) for tier in TIERS):
            findings.append(Finding(
                spec=str(path),
                check="target_path.tier",
                severity="error",
                message=f"target_path not under allowed tier: {tp}"
            ))
        if not tp.endswith("/"):
            findings.append(Finding(
                spec=str(path),
                check="target_path.tier",
                severity="warn",
                message=f"target_path should end with /: {tp}"
            ))
    
    # Read body for section checks
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    
    # sections.present - all 12 sections must be present
    for n in range(1, 13):
        if not _has_section(body, n):
            findings.append(Finding(
                spec=str(path),
                check="sections.present",
                severity="error",
                message=f"missing section: ## {n}."
            ))
    
    # design.solid - §5 should contain SOLID Principles Application (REQUIRED per template)
    section_5 = _extract_section(body, 5)
    if section_5 and "SOLID Principles" not in section_5:
        findings.append(Finding(
            spec=str(path),
            check="design.solid",
            severity="warn",
            message="§5 missing SOLID Principles Application (REQUIRED for all components)"
        ))
    
    # logic.block - §6 must contain "Logic / algorithm" and the four sub-parts unless N/A
    section_6 = _extract_section(body, 6)
    if section_6:
        has_logic_header = "Logic / algorithm" in section_6
        is_na = "Logic / algorithm: N/A" in section_6 or "Logic / algorithm:N/A" in section_6
        
        if not has_logic_header:
            findings.append(Finding(
                spec=str(path),
                check="logic.block",
                severity="error",
                message="§6 missing 'Logic / algorithm'"
            ))
        elif not is_na:
            # Check for the four sub-parts
            required_parts = ["Procedure", "Decision rules", "Key code fragments", "Edge cases"]
            for part in required_parts:
                if part not in section_6:
                    findings.append(Finding(
                        spec=str(path),
                        check="logic.block",
                        severity="error",
                        message=f"§6 missing '{part}'"
                    ))
    
    # examples.counter - warn if §10 mentions counter-example
    section_10 = _extract_section(body, 10)
    if section_10 and "counter-example" not in section_10.lower():
        findings.append(Finding(
            spec=str(path),
            check="examples.counter",
            severity="warn",
            message="§10 has no counter-example"
        ))
    
    # provides.nonempty - warn if code spec with empty provides
    if "target_path" in fm and "provides" in fm:
        tp = fm["target_path"]
        is_code = any(tp.startswith(t) for t in ["src/", "scripts/"])
        if is_code and isinstance(fm["provides"], list) and len(fm["provides"]) == 0:
            findings.append(Finding(
                spec=str(path),
                check="provides.nonempty",
                severity="warn",
                message="code spec with empty provides"
            ))
    
    return findings


def check_corpus(by_id: dict[str, dict]) -> list[Finding]:
    """Cross-spec checks: ids/paths, depends_on graph, cycles, spec-per-feature."""
    findings = []
    
    # id.unique and target_path.unique
    seen_paths = {}
    for spec_id, fm in by_id.items():
        if "target_path" in fm:
            tp = fm["target_path"]
            if tp in seen_paths:
                findings.append(Finding(
                    spec=seen_paths[tp],
                    check="target_path.unique",
                    severity="error",
                    message=f"duplicate target_path: {tp} (also in {spec_id})"
                ))
            else:
                seen_paths[tp] = fm.get("_path", spec_id)
    
    # depends_on.resolve - each dep id must exist
    for spec_id, fm in by_id.items():
        if "depends_on" in fm and isinstance(fm["depends_on"], list):
            for dep_id in fm["depends_on"]:
                if dep_id not in by_id:
                    findings.append(Finding(
                        spec=fm.get("_path", spec_id),
                        check="depends_on.resolve",
                        severity="error",
                        message=f"unknown dependency: {dep_id}"
                    ))
    
    # depends_on.cycle - detect cycles
    cycle = _cycle(by_id)
    if cycle:
        findings.append(Finding(
            spec=cycle[0],
            check="depends_on.cycle",
            severity="error",
            message=f"dependency cycle: {' -> '.join(cycle)}"
        ))
    
    # capability.spec_per_feature - each (framework, feature) must be unique for selectable specs
    seen_features = {}
    for spec_id, fm in by_id.items():
        if "capability" in fm and isinstance(fm["capability"], dict):
            cap = fm["capability"]
            selectable = cap.get("selectable", False)
            
            if selectable:
                framework = cap.get("framework")
                feature = cap.get("feature")
                
                if not framework or not feature:
                    findings.append(Finding(
                        spec=fm.get("_path", spec_id),
                        check="capability.spec_per_feature",
                        severity="error",
                        message="selectable spec missing framework or feature"
                    ))
                else:
                    key = (framework, feature)
                    if key in seen_features:
                        findings.append(Finding(
                            spec=fm.get("_path", spec_id),
                            check="capability.spec_per_feature",
                            severity="error",
                            message=f"({framework}, {feature}) already used by {seen_features[key]}"
                        ))
                    else:
                        seen_features[key] = spec_id
    
    return findings


def validate(paths: list[Path], strict: bool = False) -> tuple[list[Finding], int]:
    """Run all checks; return findings + exit code."""
    findings = []
    by_id = {}
    seen_ids = {}
    
    # Resolve all spec files
    spec_files = []
    for p in paths:
        if p.is_file():
            if _should_validate(p):
                spec_files.append(p)
        elif p.is_dir():
            for md in p.rglob("*.md"):
                if _should_validate(md):
                    spec_files.append(md)
    
    if not spec_files:
        print("No specs found")
        return [], 0
    
    # Pass 1: per-spec checks
    for path in spec_files:
        spec_findings = check_spec(path)
        findings.extend(spec_findings)
        
        # Try to build by_id index for corpus checks
        try:
            fm = parse_front_matter(path)
            if isinstance(fm, dict) and "id" in fm:
                spec_id = fm["id"]
                fm["_path"] = str(path)
                
                # Check for duplicate IDs
                if spec_id in seen_ids:
                    findings.append(Finding(
                        spec=str(path),
                        check="id.unique",
                        severity="error",
                        message=f"duplicate id: {spec_id} (also in {seen_ids[spec_id]})"
                    ))
                else:
                    seen_ids[spec_id] = str(path)
                    by_id[spec_id] = fm
        except:
            pass  # Already reported in check_spec
    
    # Pass 2: corpus checks
    corpus_findings = check_corpus(by_id)
    findings.extend(corpus_findings)
    
    # Sort findings
    findings.sort(key=lambda f: (f.spec, f.severity, f.check))
    
    # Determine exit code
    if strict:
        exit_code = 1 if findings else 0
    else:
        exit_code = 1 if any(f.severity == "error" for f in findings) else 0
    
    return findings, exit_code


def main(argv: list | None = None) -> int:
    """CLI: [paths...] [--strict]"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate spec files")
    parser.add_argument("paths", nargs="*", default=["specs/"], 
                       help="Spec files or directories (default: specs/)")
    parser.add_argument("--strict", action="store_true",
                       help="Promote warnings to errors")
    
    args = parser.parse_args(argv)
    
    # Convert paths to Path objects
    paths = [Path(p) for p in args.paths]
    
    try:
        findings, exit_code = validate(paths, args.strict)
        
        # Print report
        if not findings:
            print(f"OK  {len([p for p in paths if p.exists()])} specs, 0 errors, 0 warnings")
        else:
            # Group by severity
            errors = [f for f in findings if f.severity == "error"]
            warnings = [f for f in findings if f.severity == "warn"]
            
            # Print findings
            for f in findings:
                severity_label = f.severity.upper()
                print(f"{severity_label:5}  {f.spec:50}  [{f.check:30}]  {f.message}")
            
            # Summary
            print(f"\nTotal: {len(errors)} errors, {len(warnings)} warnings")
        
        return exit_code
        
    except Exception as e:
        print(f"CRASH: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


# ============================================================================
# § 6. Key code fragments (verbatim from spec)
# ============================================================================

REQUIRED = ["id", "title", "owner", "status", "target_path", "owning_skill",
            "backlog", "provides", "depends_on", "generation_context", "acceptance", "regeneration"]

TIERS = ("src/core/", "src/dataio/", "src/services/", "src/framework/",
         "src/agents/", "src/runners/", "scripts/")

ID_RE = re.compile(r"^[a-z0-9]+\.[a-z0-9-]+$")


def _has_section(body: str, n: int) -> bool:
    """Check if section ## n. is present."""
    return re.search(rf"(?m)^##\s*{n}\.", body) is not None


def _extract_section(body: str, n: int) -> Optional[str]:
    """Extract section n content."""
    pattern = rf"(?m)^##\s*{n}\..*?$"
    match = re.search(pattern, body)
    if not match:
        return None
    
    start = match.end()
    # Find next section or end
    next_section = re.search(rf"(?m)^##\s*{n+1}\.", body[start:])
    if next_section:
        end = start + next_section.start()
        return body[start:end]
    else:
        return body[start:]


def _cycle(by_id: dict) -> list | None:
    """DFS over depends_on -> first cycle path or None."""
    visited = set()
    rec_stack = []
    
    def dfs(node_id: str) -> list | None:
        if node_id in rec_stack:
            # Found cycle
            cycle_start = rec_stack.index(node_id)
            return rec_stack[cycle_start:] + [node_id]
        
        if node_id in visited:
            return None
        
        visited.add(node_id)
        rec_stack.append(node_id)
        
        fm = by_id.get(node_id, {})
        deps = fm.get("depends_on", [])
        
        if isinstance(deps, list):
            for dep in deps:
                if dep in by_id:  # Only follow known deps
                    cycle = dfs(dep)
                    if cycle:
                        return cycle
        
        rec_stack.pop()
        return None
    
    for node_id in by_id:
        cycle = dfs(node_id)
        if cycle:
            return cycle
    
    return None


def _should_validate(path: Path) -> bool:
    """Skip non-spec files: _templates/, README*.md, STRUCTURE.txt."""
    name = path.name
    parts = path.parts
    
    # Skip templates
    if "_templates" in parts:
        return False
    
    # Skip READMEs and STRUCTURE.txt
    if name.startswith("README") or name == "STRUCTURE.txt":
        return False
    
    return True


if __name__ == "__main__":
    sys.exit(main())
