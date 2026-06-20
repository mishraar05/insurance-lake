# Genie Code grounding pack — InsureLake spec → code

**Purpose.** Genie Code (the AI coding assistant) wandered earlier because it had **no grounding** in this project and was handed an oversized, vague task. This pack fixes that: it gives Genie Code your conventions + one complete spec + a tight "generate exactly this" instruction, so it acts as a focused **per-spec generator** instead of guessing.

**First target:** the **Spec Validator** (`spec-validation-spec.md`) — pure Python, zero dependencies on other specs, and once generated you can run it on `specs/` to flag the 35 stub specs. A real, measurable result.

> Mental model: **Genie Code = the worker** that generates one component from one spec. The menu-driven chatbot that *orchestrates* builds is a separate, later thing (Agent Bricks / Agent Framework, Phase 4). Don't ask Genie Code to be the orchestrator.

---

## Two ways to use it

### Path A — Install as an Agent Skill (recommended)
Databricks Agent Skills load from `/Users/{you}/.assistant/skills/`. Copy the skill folder there:

```
cp -r docs/genie-code/insurelake-spec-codegen  /Users/<you>/.assistant/skills/
```

(or back it with a Git folder per Databricks' guidance). Then in **Genie Code**:

> *Use the `insurelake-spec-codegen` skill to generate the Spec Validator from `reference/spec-validation-spec.md`.*

The skill carries the golden rules + the target task + the reference files, so the instruction stays short.

### Path B — No install (paste path)
Open `GENERATION-PROMPT.md`, attach the two named files in Genie Code, and paste the prompt. Same rules, nothing to install.

---

## Run steps (either path)
1. Run Genie Code with the skill/prompt above.
2. Let it write `scripts/speccheck/validate_spec.py` **and** `tests/scripts/test_validate_spec.py`.
3. **Run the acceptance commands yourself** (don't trust "looks done"):
   - `python scripts/speccheck/validate_spec.py specs/`
   - `pytest tests/scripts/test_validate_spec.py`
4. Score it with the table below.

---

## Fidelity scorecard (this is the benchmark)
Score each Y/N — the count of Y's is your **spec → Genie-Code fidelity** for this slice (feeds the PoC benchmark in `specs/foundation/benchmark-plan.md`).

| # | Check | Y/N |
|---|-------|-----|
| 1 | **Interface match** — emitted exactly the §3 API: `Finding` + `parse_front_matter`, `check_spec`, `check_corpus`, `validate`, `main` (same params/returns) | |
| 2 | **Logic match** — §6 key fragments present: `REQUIRED` list, `TIERS`, `ID_RE`, the `## n.` section regex, the depends_on cycle DFS | |
| 3 | **Placement** — landed in `scripts/speccheck/validate_spec.py` (+ tests in `tests/scripts/`), nothing at repo root | |
| 4 | **Constraints honored** — pure Python + PyYAML only; no Spark / network / ABC; report-only; single file | |
| 5 | **Acceptance passes** — both commands above succeed | |
| 6 | **No invention** — no extra public functions, flags, or dependencies beyond the spec | |

**Interpreting the score:** 6/6 = the spec is generation-ready and the loop works — repeat on the next spec. < 6 = note exactly which row failed; that tells us whether to tighten the **spec** (logic/interface under-specified) or the **grounding** (rules not landing). Either way you've isolated the cause instead of "the bot is confused."

---

## If it still wanders
- It's likely not loading the reference files → confirm the skill folder copied correctly (SKILL.md at its root, `reference/` beside it), or use Path B and **attach** the files explicitly.
- Keep the ask to **one** component. If you ask for "the framework," it will wander again — that's an orchestration task, not a Genie Code task.
- Make sure you pointed it at a **logic-complete** spec (this one is). Don't feed it the stub specs.
