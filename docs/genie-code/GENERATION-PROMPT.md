# Paste-ready Genie Code prompt (no-install path)

Use this if you don't want to install the Agent Skill yet — it inlines the same rules.

**1. Open Genie Code** in your Databricks workspace (in the repo / Git folder for this project).

**2. Attach or paste these two files** so Genie Code has the context:
- `specs/foundation/spec-validation-spec.md`  (the spec to implement)
- `skills/_shared/project-structure.md`        (where files go)

**3. Paste this message:**

---
You are generating ONE component from its spec. In this project, specs are the source of truth — **translate the spec, do not invent.**

**Target spec:** `spec-validation-spec.md`

**Rules:**
1. Emit the `## 3. Interface` signatures/classes **verbatim** (same names, params, return types).
2. Implement `## 6. Implementation logic` literally: the **Procedure** steps in order, the **Decision rules**, the **Key code fragments** as written, and every **Edge case**.
3. Write ONLY to the spec's `target_path`: `scripts/speccheck/validate_spec.py`. Follow `project-structure.md`.
4. Hard constraints: **pure Python + PyYAML only**; no Spark, no network, no ABC; report-only (never edits a spec); single file; exit codes 0/1/2.
5. Also generate tests at `tests/scripts/test_validate_spec.py` per `## 9`.
6. No TODOs or placeholders — complete, runnable code.

**Definition of done (must pass):**
- `python scripts/speccheck/validate_spec.py specs/` runs and exits 0 when there are no ERRORs.
- `pytest tests/scripts/test_validate_spec.py` is green.

**Output:** the full file content for each file, then the exact commands to run them. Finally, run the validator on `specs/` and show the findings.
---

**4. Verify** with the scorecard in `README.md`. Don't accept "looks done" — run the two acceptance commands.
