---
id: foundation.spec-validator
title: Spec Validator (validate any spec after authoring)
owner: EY
status: active
target_path: scripts/speccheck/
owning_skill: control.self-review
backlog: [FND-006]
provides: [Finding, parse_front_matter, check_spec, check_corpus, validate, main]
depends_on: []
generation_context:
  - specs/_templates/component-spec.md
  - specs/agentic/capability-registry-spec.md
  - docs/ROADMAP.md
acceptance:
  - "python scripts/speccheck/validate_spec.py specs/                                # validate all specs; exit 0 if no ERROR"
  - "python scripts/speccheck/validate_spec.py specs/foundation/contracts-spec.md    # one spec"
  - "pytest tests/scripts/test_validate_spec.py"
  - "ruff check scripts/speccheck/ tests/scripts/                                    # PEP 8 + import order + naming + Google docstrings"
  - "black --check scripts/speccheck/ tests/scripts/                                 # formatting (line length 88)"
regeneration: fully-generated
---

# Spec Validator - Specification

## 1. Purpose & scope
Validate that **any** spec is well-formed and registry-ready the moment it is authored. It is the machine-checkable half of Quality Gate **#1** (spec authored / structured) and **#2** (placement mapped): it enforces the `component-spec` template (front-matter + the 12 sections + the §6 logic-block rule) and the cross-spec graph the **capability-registry** relies on.
- In scope: parsing + validating spec `.md` files; per-spec **and** cross-spec checks; a findings report (error/warn) + an exit code.
- Out of scope: **CI wiring** - by decision this is *not* a CI gate; it runs in the authoring loop and is callable by `control.self-review` before the registry loads a spec. Also out: generating or mutating specs (**report-only, never auto-fixes**), and the dynamic gate points (generation, tests, benchmark, govern) which are runtime/HITL.

## 2. Requirements
**Functional**
- FR-1: Parse each target spec's YAML front-matter; malformed/missing → a fatal `front-matter.parse` finding (skip that spec's remaining per-spec checks).
- FR-2 (per-spec): required keys present; enums valid; `id` matches `<tier>.<family?>.<component>` (path-mirroring, 2-3 segments); `target_path` under an allowed tier; all 12 sections (`## 1.`..`## 12.`) present; the §6 logic-block rule.
- FR-3 (cross-spec): `id` and `target_path` unique; every `depends_on` resolves to a known spec id; no dependency cycles; **spec-per-feature** - each `(framework, feature)` maps to exactly one selectable spec, and `selectable: true` requires `framework` + `feature`.
- FR-4: Classify every finding `error|warn`; print a deterministic, grouped report; return exit **0** (no error) / **1** (≥1 error) / **2** (tool crash). `--strict` promotes warnings to errors.
- FR-5: Skip non-spec files - `_templates/`, `README*.md`, `STRUCTURE.txt`, `*.VALIDATION.md` (reports; no front-matter expected).

**Non-functional**: pure Python (**PyYAML only**; no pyspark/network); deterministic, stable ordering; runs on a single file, a directory, or the whole `specs/` tree; fast (<1s for the corpus).

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
@dataclass
class Finding:
    spec: str          # spec file path
    check: str         # check id, e.g. "front-matter.required"
    severity: str      # "error" | "warn"
    message: str

def parse_front_matter(path: Path) -> dict: ...                       # YAML header -> dict; raises on malformed
def check_spec(path: Path) -> list[Finding]: ...                      # per-spec: front-matter + sections + §6 logic
def check_corpus(by_id: dict[str, dict]) -> list[Finding]: ...        # cross-spec: ids/paths, depends_on graph, cycles, spec-per-feature
def validate(paths: list[Path], strict: bool = False) -> tuple[list[Finding], int]: ...  # run all; findings + exit code
def main(argv: list | None = None) -> int: ...                        # CLI: [paths...] [--strict]
```
Net-new component: full stub above.

## 4. Inputs / Outputs
- Input: spec paths - a file, a directory, or the default `specs/`.
- Output: a list of `Finding`, a printed report grouped by file, and an exit code. **No file writes** (report-only).

## 5. Design
Two passes. **Pass 1 (per-spec)** parses front-matter + checks structure, building an index `by_id[id] -> front-matter`. **Pass 2 (corpus)** runs the graph + uniqueness + spec-per-feature checks over that index. Position in the loop: *author / Genie writes a spec → `validate_spec` → fix ERRORs → spec is registry-ready → `capability-registry` loads it → `build_plan`.* This offloads the registry's "validated at load time" assumption onto a dedicated tool and makes the same rules reusable by `control.self-review` (which feeds confidence-scoring → HITL). Deliberately decoupled from CI; exit codes still let the authoring agent / router branch on the result.

### SOLID Principles Application
* **SRP (Single Responsibility)**: Each function has one clear purpose - `parse_front_matter` extracts YAML, `check_spec` validates individual spec structure, `check_corpus` validates cross-spec integrity, `validate` orchestrates the workflow, `main` handles CLI concerns. Helper functions (`_has_section`, `_extract_section`, `_cycle`) are focused on single operations.
* **OCP (Open/Closed)**: New validation checks can be added to `check_spec` or `check_corpus` without modifying the core validation workflow or the `Finding` data structure. The two-pass architecture separates extensible per-spec and corpus checks from the stable orchestration logic.
* **LSP (Liskov Substitution)**: The `Finding` dataclass is immutable and type-stable. All check functions return `list[Finding]`, making them substitutable in the aggregation step.
* **ISP (Interface Segregation)**: Clean separation of concerns - parsing (`parse_front_matter`), per-spec validation (`check_spec`), corpus validation (`check_corpus`), orchestration (`validate`), and CLI (`main`). Each interface exposes only what its callers need.
* **DIP (Dependency Inversion)**: Depends on abstractions (`Path`, `dict`, `list`) not concrete implementations. The validator is decoupled from file systems (operates on `Path`), spec formats (operates on parsed `dict`), and output destinations (returns structured `Finding` list).

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. Resolve target files: expand each arg (file or dir) to `*.md`; **exclude** `_templates/`, `README*.md`, `STRUCTURE.txt`, `*.VALIDATION.md`.
  2. For each file: extract the front-matter block (between the first two `---` fences) and `yaml.safe_load` it. Missing or non-dict → `error` `front-matter.parse`; skip this file's remaining per-spec checks.
  3. Per-spec checks → Findings:
     - `front-matter.required` (error): every required key present (the 12 keys in FR-2).
     - `front-matter.enum` (error): `status` ∈ {draft, active, implemented}; `regeneration` ∈ {fully-generated, scaffold-then-edit}; `capability.selectable` ∈ {true, false}.
     - `front-matter.type` (error): `backlog`/`provides`/`depends_on`/`generation_context`/`acceptance` are lists; **`acceptance` and `generation_context` must be non-empty**; `capability` (if present) is a mapping. (`depends_on` may be empty; empty `provides` on a code spec or empty `backlog` → warn.)
     - `id.format` (error): matches `^[a-z0-9]+(\.[a-z0-9_-]+){1,2}$` (2-3 path-mirroring segments).
     - `target_path.tier` (error): starts with one of the allowed tiers; (warn) if it does not end with `/`.
     - `sections.present` (error): a heading line `^##\s*{n}\.` exists for **n = 1..12**.
     - `design.solid` (warn): §5 contains "SOLID Principles" subsection (REQUIRED for all components).
     - `logic.block` (error): §6 contains "Logic / algorithm"; **unless** it declares "N/A", it must contain all four sub-parts: *Procedure*, *Decision rules*, *Key code fragments*, *Edge cases*.
     - `examples.counter` (warn): §10 mentions a counter-example.
  4. Record `by_id[id] = front-matter` (flag duplicate ids while inserting).
  5. Corpus checks → Findings:
     - `id.unique` (error) and `target_path.unique` (error).
     - `depends_on.resolve` (error): each dep id ∈ `by_id`.
     - `depends_on.cycle` (error): DFS over `depends_on`; a back-edge reports the cycle path.
     - `capability.spec_per_feature` (error): for `selectable: true` specs, `(framework, feature)` is unique; missing `framework`/`feature` on a selectable spec → error.
     - `provides.nonempty` (warn): a code spec (`target_path` under `src/` or `scripts/`) with empty `provides`.
  6. Sort findings by (path, severity, check); print; return `1` if any `error` (or any finding under `--strict`) else `0`.
- **Decision rules:**
  - *severity*: structural / front-matter / graph-integrity = **error**; advisory style (no counter-example, empty `provides`, missing trailing slash, missing SOLID documentation) = **warn**. `--strict` promotes warn → error.
  - *logic-bearing vs interface-only*: interface/data specs (e.g. contracts, metadata) declare `Logic / algorithm: N/A` in §6; **everything else** must carry the four-part logic block.
- **Key code fragments** (the generated code MUST contain these):
```python
import re, yaml
from pathlib import Path
REQUIRED = ["id","title","owner","status","target_path","owning_skill",
            "backlog","provides","depends_on","generation_context","acceptance","regeneration"]
TIERS = ("src/core/","src/dataio/","src/services/","src/framework/",
         "src/agents/","src/runners/","scripts/")
ID_RE = re.compile(r"^[a-z0-9]+\.[a-z0-9-]+$")

def parse_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("no front-matter")
    return yaml.safe_load(text.split("---", 2)[1])

def _has_section(body: str, n: int) -> bool:        # "## 3." present
    return re.search(rf"(?m)^##\s*{n}\.", body) is not None

def _extract_section(body: str, n: int) -> Optional[str]:  # extract section n content
    ...

def _cycle(by_id: dict) -> list | None:             # DFS over depends_on -> first cycle path or None
    ...
```
- **Edge cases:** CRLF line endings; a spec whose §6 is just "Logic / algorithm: N/A" (interface spec) **passes**; a `capability` with `selectable: false` is validated for shape but **excluded** from the menu-uniqueness check; a forward `depends_on` to a not-yet-written spec → **error** (broken graph - add the dep spec or fix the id); duplicate `target_path` across two specs → error; an empty `specs/` → exit 0 with a "no specs found" notice; templates/READMEs skipped; a spec missing SOLID documentation in §5 → **warn** (not error, to allow gradual adoption).

**Guidance:** single file `scripts/speccheck/validate_spec.py`; sibling to `scripts/codegen/gen_schema.py`; mirror its style (argparse, byte-stable output, `sys.exit`).
**Constraints (hard):** pure Python (PyYAML only; no pyspark/network); deterministic, stable ordering; **report-only - NEVER edits a spec**; build-time/authoring tool, not a data-plane run → **NO ABC instrumentation** (the owning skill records the outcome); exit codes 0/1/2.

## 7. Validation, edge cases & versioning policy
The rule set is the **executable encoding of `component-spec.md`** (required sections + front-matter keys + the §6 logic-block rule) plus the Quality Gate's static points. When the template's required sections/keys or the front-matter schema change, **update this validator in the same change** - it is to *spec shape* what `codegen --check` is to the *metadata schema*. By decision it is **not** wired into CI; it runs in the authoring loop and via `control.self-review`. Adding a new check is backward-compatible; removing/renaming a `check` id is a breaking change for anyone scripting on the output.

## 8. Error handling + ABC instrumentation
Build-time/authoring tool, not a data run → **no ABC in the tool itself** (consistent with `codegen`). Validation failures are **Findings, not exceptions**. On an unexpected crash, print the cause and `sys.exit(2)`. When invoked inside an agent/self-review action, the **owning skill** (`control.self-review`) logs the validation outcome (pass/fail + finding counts) to ABC and feeds confidence-scoring → HITL.

## 9. Testing & acceptance
Unit fixtures (mock spec files in a temp dir):
- a known-good spec → 0 findings;
- a spec missing `acceptance` → `front-matter.required` error;
- a spec missing SOLID Principles in §5 → `design.solid` warning;
- a logic spec whose §6