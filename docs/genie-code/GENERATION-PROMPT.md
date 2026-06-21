# Genie Code - spec-faithful prompts (gap protocol)

**Set Genie Code's approval mode to "Ask first"** (not Auto-approve) so it pauses before every file write/run. Accepted code does **not** auto-run - you control execution. Pick a spec that already passes your `spec-validator` (so Phase-1 gaps reflect real under-specification, not a truncated file).

Open Genie Code in the workspace (the repo Git folder). Either install the `insurelake-spec-codegen` skill, or paste the two prompts below.

## Phase 1 - GAP ANALYSIS (no code)
---
You are generating ONE component strictly from its spec. The spec is the ONLY source of truth - never invent names, types, values, option strings, defaults, paths, or behaviour it does not state.

Target spec: `specs/foundation/spec-validation-spec.md`   (change to your spec)

Do a GAP ANALYSIS only - write NO code. Read the spec end to end and output a `## SPEC GAPS` list. A gap = any detail you would need that is not in this spec or a depends_on spec: an undefined class/type/function, an option/value/SQL the spec references but does not give, an ambiguous §3 signature or §6 step, a behaviour implied but unspecified, or an import from a module not in depends_on / generation_context. For each gap: the §ref, what is missing, and the one question to resolve it. If there are none, say `NO GAPS - ready to generate`. Then STOP.
---

## Phase 2 - GENERATE (only after you have enriched the spec for any gaps)
---
Now generate, strictly per `specs/foundation/spec-validation-spec.md`:
1. Emit the `## 3. Interface` signatures/classes VERBATIM.
2. Implement `## 6` literally - Procedure in order, Decision rules, Key code fragments as written, every Edge case.
3. Write ONLY to the spec's target_path: `scripts/speccheck/validate_spec.py`; tests at `tests/scripts/test_validate_spec.py`.
4. Hard constraints: pure Python + PyYAML only; no Spark / network / ABC; report-only; single file.
5. No TODOs/placeholders. If you hit any detail not in the spec, STOP and report it as a new SPEC GAP - do not invent.
Output each file's full content + the commands to run. Then run `python scripts/speccheck/validate_spec.py specs/` and show the findings.
---

## Then verify (deterministic - do not trust "looks done")
- Diff the generated public signatures against the spec's §3 (must match exactly).
- Run the spec's `acceptance:` commands yourself.
- Score with the table in `README.md`.
