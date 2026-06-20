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
- FR-2 (per-spec): required keys present; enums valid; `id` matches `<domain>.<component>`; `target_path` under an allowed tier; all 12 sections (`## 1.`..`## 12.`) present; the §6 logic-block rule.
- FR-3 (cross-spec): `id` and `target_path` unique; every `depends_on` resolves to a known spec id; no dependency cycles; **spec-per-feature** - each `(framework, feature)` maps to exactly one selectable spec, and `selectable: true` requires `framework` + `feature`.
- FR-4: Classify every finding `error|warn`; print a deterministic, grouped report; return exit **0** (no error) / **1** (≥1 error) / **2** (tool crash). `--strict` promotes warnings to errors.
- FR-5: Skip non-spec files - `_templates/`, `README*.md`, `STRUCTURE.txt` (no front-matter expected).

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

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth - the generator translates this, it does not invent it):
- **Procedure:**
  1. Resolve target files: expand each arg (file or dir) to `*.md`; **exclude** `_templates/`, `README*.md`, `STRUCTURE.txt`.
  2. For each file: extract the front-matter block (between the first two `---` fences) and `yaml.safe_load` it. Missing or non-dict → `error` `front-matter.parse`; skip this file's remaining per-spec checks.
  3. Per-spec checks → Findings:
     - `front-matter.required` (error): every required key present (the 12 keys in FR-2).
     - `front-matter.enum` (error): `status` ∈ {draft, active, implemented}; `regeneration` ∈ {fully-generated, scaffold-then-edit}; `capability.selectable` ∈ {true, false}.
     - `front-matter.type` (error): `backlog`/`provides`/`depends_on`/`generation_context`/`acceptance` are lists; **`acceptance` and `generation_context` must be non-empty**; `capability` (if present) is a mapping. (`depends_on` may be empty; empty `provides` on a code spec or empty `backlog` → warn.)
     - `id.format` (error): matches `^[a-z0-9]+\.[a-z0-9-]+$`.
     - `target_path.tier` (error): starts with one of the allowed tiers; (warn) if it does not end with `/`.
     - `sections.present` (error): a heading line `^##\s*{n}\.` exists for **n = 1..12**.
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
  - *severity*: structural / front-matter / graph-integrity = **error**; advisory style (no counter-example, empty `provides`, missing trailing slash) = **warn**. `--strict` promotes warn → error.
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

def _cycle(by_id: dict) -> list | None:             # DFS over depends_on -> first cycle path or None
    ...
```
- **Edge cases:** CRLF line endings; a spec whose §6 is just "Logic / algorithm: N/A" (interface spec) **passes**; a `capability` with `selectable: false` is validated for shape but **excluded** from the menu-uniqueness check; a forward `depends_on` to a not-yet-written spec → **error** (broken graph - add the dep spec or fix the id); duplicate `target_path` across two specs → error; an empty `specs/` → exit 0 with a "no specs found" notice; templates/READMEs skipped.

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
- a logic spec whose §6 lacks "Edge cases" (and is not N/A) → `logic.block` error;
- two specs both tagged `(ingestion, batch)` → `capability.spec_per_feature` error;
- `A depends_on B`, `B depends_on A` → `depends_on.cycle` error;
- `depends_on` to an unknown id → `depends_on.resolve` error;
- `--strict` turns a lone warn into a non-zero exit.
Plus front-matter `acceptance`. Target >80% coverage.

## 10. Examples
Passing:
```
$ python scripts/speccheck/validate_spec.py specs/
OK  9 specs, 0 errors, 1 warning
WARN  specs/foundation/codegen-spec.md  [examples.counter]  §10 has no counter-example
exit 0
```
Failing:
```
$ python scripts/speccheck/validate_spec.py specs/ingestion/
ERROR  specs/ingestion/batch-spec.md      [front-matter.required]        missing key: acceptance
ERROR  specs/ingestion/batch-spec.md      [logic.block]                  §6 missing 'Edge cases'
ERROR  specs/ingestion/streaming-spec.md  [capability.spec_per_feature]  (ingestion, batch) already used by ingestion/batch-spec.md
exit 1
```
Counter-example (what NOT to do): the validator must **not** auto-insert the missing section or rewrite front-matter - it reports only; fixing is the author's / HITL's job.

## 11. Regeneration contract
`regeneration: fully-generated`. Regenerate the tool when the `component-spec` template or the Quality Gate changes; never hand-edit it to diverge from the template it enforces.

## 12. References
`specs/_templates/component-spec.md` (the contract it enforces) · `specs/agentic/capability-registry-spec.md` (shared front-matter parsing; this validator guarantees the well-formedness the registry assumes) · `docs/ROADMAP.md` (Quality Gate #1/#2) · `specs/foundation/codegen-spec.md` (sibling build-time tool pattern) · `control.self-review` skill (invokes it; records outcome to ABC → confidence-scoring → HITL).
Note: `FND-006` is a **new** backlog task introduced by the Quality-Gate discipline - add it to `AI_Ready_Backlog`.
