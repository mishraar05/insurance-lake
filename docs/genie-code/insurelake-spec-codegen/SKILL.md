---
name: insurelake-spec-codegen
description: Generate an InsureLake framework component from its spec (.md). Use whenever asked to build, generate, or implement a module from a *-spec.md in this project. Translates the spec exactly — enforces its §3 interface, its §6 logic, the DAB project structure, the spec's hard constraints, and its acceptance checks. Never improvises or adds API/dependencies.
---

# InsureLake — generate code from a spec

In this project, **specs are the source of truth** and code is generated to match them. Your job is to **translate the spec, not invent.** Do **one** component per request.

## When to use
When the user asks to build / generate / implement a component and points to a `*-spec.md` (e.g. *"generate the spec-validator from reference/spec-validation-spec.md"*).

## Golden rules (do not violate)
1. **Interface is law.** Emit the signatures/classes in the spec's `## 3. Interface` block **verbatim** — identical names, parameters, and return types. Do not rename, add, or drop public API.
2. **Logic is given, not invented.** Implement `## 6. Implementation logic` literally: follow the **Procedure** steps in order, apply the **Decision rules**, include the **Key code fragments** as written, and handle **every** listed **Edge case**.
3. **Placement is fixed.** Write code ONLY to the spec's front-matter `target_path`. Use `reference/project-structure.md` to resolve where files go. Never place code at the repo root or an unmapped path.
4. **Respect hard constraints.** Obey the spec's *Constraints (hard)* exactly (e.g. pure Python + only the named libraries; no Spark/network; no ABC; single file). Add **no** dependency that the spec does not name.
5. **Tests too.** Generate the tests described in `## 9. Testing & acceptance` at the mirrored `tests/...` path.
6. **Acceptance is the definition of done.** Every command in the front-matter `acceptance:` list must pass. Self-check against them before you finish.
7. **No placeholders.** Deliver complete, runnable code — no TODOs and no `pass`-stubs for required logic.

## Procedure
1. Read the target spec end to end (front-matter + all 12 sections).
2. Read `reference/project-structure.md`; resolve the exact output path(s) from `target_path`.
3. Write the module: emit the §3 interface verbatim, then implement the §6 logic (Procedure → Decision rules → Key code fragments → Edge cases).
4. Write the tests from §9 at the mirrored `tests/` path.
5. Self-verify against the front-matter `acceptance:` commands; fix until they would pass.
6. Report every file written (full paths) and the exact commands to run `acceptance`.

## Reference files
- `reference/spec-validation-spec.md` — the spec to implement (current task).
- `reference/project-structure.md` — canonical DAB placement map.
- `reference/component-spec-template.md` — the spec contract this validator enforces (defines the required front-matter keys and the 12 section titles).

## Current task — Spec Validator
Generate from `reference/spec-validation-spec.md`:
- **Module** → `scripts/speccheck/validate_spec.py` (the §3 interface verbatim; the §6 logic literally).
- **Tests** → `tests/scripts/test_validate_spec.py` (the cases in §9).
- **Hard constraints:** pure Python + **PyYAML only**; no Spark, no network, no ABC; **report-only** (never edits a spec); single file; exit codes 0/1/2.
- **Acceptance (must pass):**
  - `python scripts/speccheck/validate_spec.py specs/` → runs, prints findings, exits 0 if no ERROR.
  - `python scripts/speccheck/validate_spec.py specs/foundation/contracts-spec.md` → validates one spec.
  - `pytest tests/scripts/test_validate_spec.py` → green.
- When done, **run** the validator on `specs/` and show the findings (it should flag the specs that have no front-matter).
