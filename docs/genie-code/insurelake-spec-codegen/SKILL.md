---
name: insurelake-spec-codegen
description: Generate an InsureLake framework component from its spec (.md), strictly. Use whenever asked to build, generate, or implement a module from a *-spec.md in this project. Translates the spec EXACTLY - enforces its §3 interface, §6 logic, the DAB project structure, hard constraints, and acceptance checks. NEVER invents; if any needed detail is missing from the spec it reports a SPEC GAP and stops.
---

# InsureLake - spec-faithful code generation (with gap protocol)

In this project, **the spec is the ONLY source of truth.** Your job is to **translate the spec, not invent.** If the spec does not state it, you do not decide it - you **report it as a gap and stop.** Do **one** component per request.

## The spec-gap protocol (the most important rule)
- **Never invent** a name, type, value, option string, config, default, file path, or behaviour the spec does not state. A "reasonable guess" is a violation.
- If you need any detail that is **not in the spec**, add it to a `## SPEC GAPS` list and **STOP**. Do not fill it in. Wait for the human to enrich the spec.
- A **gap** is any of:
  - a class / function / type the code must use that is **not** defined in this spec's §3 **nor** in a `depends_on` spec's interface;
  - an option / string / SQL / value / default the spec references but does not give (e.g. an exact Databricks option name the spec only says to "verify at build time");
  - a §3 signature or §6 step that is **ambiguous** or self-contradictory;
  - a behaviour implied by §1/§2 but **not specified** in §6;
  - an import from a module **not** listed in `depends_on` / `generation_context`.
- When in doubt, it is a gap. **Reporting a gap is success, not failure.**

## Two-phase mode (always run this way)
- **Phase 1 - GAP ANALYSIS (no code).** Read the target spec end to end. Output ONLY a `## SPEC GAPS` section: for each gap give the §ref, exactly what is missing, and the one question that resolves it. Write **no code**. If there are none, say `NO GAPS - ready to generate` and still stop for go-ahead.
- **Phase 2 - GENERATE (only after the human says go).** With gaps resolved in the spec, generate strictly per the rules below. If you hit a **new** gap mid-generation, stop and report it - do not improvise.

## Golden rules (Phase 2)
1. **Interface is law.** Emit the §3 `Interface` signatures/classes **verbatim** - identical names, params, return types. Do not rename / add / drop public API.
2. **Logic is given, not invented.** Implement §6 literally: the **Procedure** in order, the **Decision rules**, the **Key code fragments** as written, and **every** **Edge case**.
3. **Placement is fixed.** Write code ONLY to the spec's front-matter `target_path` (resolve via `reference/project-structure.md`). Never the repo root or an unmapped path.
4. **Hard constraints.** Obey §6 *Constraints (hard)* exactly; add **no** dependency the spec does not name.
5. **Tests too.** Generate the §9 tests at the mirrored `tests/...` path.
6. **Acceptance = done.** Every front-matter `acceptance:` command must pass; self-check before finishing.
7. **No placeholders / no invention.** Complete, runnable code - no TODOs. If completing it needs a detail not in the spec, that is a Phase-2 gap -> stop and report.

## Procedure
1. Read the target spec end to end (front-matter + 12 sections) + `reference/project-structure.md`.
2. **Phase 1:** produce the `## SPEC GAPS` list (or `NO GAPS`). Stop.
3. **Phase 2 (after go-ahead):** emit §3 verbatim -> implement §6 -> write §9 tests -> self-verify against `acceptance:`.
4. Report every file written (full paths) + the exact `acceptance` commands, then run them and show the output.

## Reference files
- the **target spec** the user names (in `specs/...`) - the source of truth for THIS task.
- `reference/project-structure.md` - canonical DAB placement map.
- `reference/component-spec-template.md` - the spec contract (required front-matter keys + the 12 section titles).

## Example task - Spec Validator
Target spec: `specs/foundation/spec-validation-spec.md`. **Phase 1 first** (report gaps); then on go-ahead generate the §3 interface into `scripts/speccheck/validate_spec.py` + tests into `tests/scripts/test_validate_spec.py`. Hard constraints: pure Python + PyYAML only; no Spark / network / ABC; report-only; single file. Acceptance: `python scripts/speccheck/validate_spec.py specs/` runs (exit 0 if no ERROR) and `pytest tests/scripts/test_validate_spec.py` is green. Then run the validator on `specs/` and show the findings.
