# Genie Code grounding pack - spec-faithful generation (gap protocol)

**Goal:** make Genie Code generate a component **strictly from its spec**, and when the spec is missing a needed detail, **report a SPEC GAP and stop** so you can enrich the spec - instead of inventing. There is no magic "halt" switch in an LLM agent, so this pack stacks three levers + two deterministic backstops.

## The 3 levers (make it follow + pause)
1. **Approval mode = "Ask first"** (Genie Code Settings; *not* Auto-approve). Genie Code proposes a plan and asks before every tool action (file write, run). Accepted code does **not** auto-run. This is your enforced checkpoint - inspect each step, Allow / Skip / redirect.
2. **The Agent Skill `insurelake-spec-codegen`** carries the **spec-gap protocol** + golden rules (the spec is the only source of truth; never invent; emit §3 verbatim; implement §6 literally). Skills are the documented way to make Genie Code follow your standards.
3. **Two-phase prompting** (`GENERATION-PROMPT.md`): **Phase 1 = GAP ANALYSIS only (no code)** -> Genie Code lists every detail missing from the spec and stops; you enrich the spec; **Phase 2 = GENERATE**. This forces gaps to surface *before* code.

## The 2 deterministic backstops (catch what slips - no trust in the model)
4. **The spec's `acceptance:` + your `spec-validator`.** Diff the generated public signatures against the spec's §3 and run the spec's `acceptance:` commands. A mismatch or failure is objective proof of drift - no LLM goodwill required.
5. **Unity Catalog governance.** Genie Code only touches assets you're authorized for and asks before modifying tables.

> The *pause* comes from "Ask first" + Phase-1 gap analysis; the *no-invention guarantee* comes from the validator/acceptance check.

## How to use
**Path A - install the skill (recommended).** Copy the skill folder to where Genie Code loads skills:
```
cp -r docs/genie-code/insurelake-spec-codegen  /Users/<you>/.assistant/skills/
```
Then in Genie Code (Ask-first mode): *"Use `insurelake-spec-codegen`. Phase 1 gap analysis only for `specs/foundation/spec-validation-spec.md`."*

**Path B - paste prompts.** Open `GENERATION-PROMPT.md`, run Phase 1, enrich the spec for any gaps, then run Phase 2.

## Fidelity scorecard (score after Phase 2)
| # | Check | Y/N |
|---|-------|-----|
| 1 | **Gaps surfaced first** - Phase 1 reported real missing detail (or a clean `NO GAPS`) before any code | |
| 2 | **Interface match** - generated public API equals §3 exactly (names/params/returns) | |
| 3 | **Logic match** - §6 Procedure / Decision rules / Key fragments / Edge cases all present | |
| 4 | **Placement** - landed in the spec's `target_path` (+ tests mirrored), nothing at repo root | |
| 5 | **Constraints honored** - only the spec's named deps; no Spark/network/ABC if forbidden | |
| 6 | **Acceptance passes** - the spec's `acceptance:` commands succeed | |
| 7 | **No invention** - nothing added that the spec doesn't state | |

6/6-7 = the spec is generation-ready and the loop works. < that = the failing row tells you whether to enrich the **spec** or tighten the **skill**.

## If it still invents instead of pausing
- Confirm approval mode is **"Ask first"**, not Auto-approve.
- Keep the ask to **one** component and **Phase 1 first** - don't say "build it".
- Make sure the skill loaded (SKILL.md at the skill-folder root, `reference/` beside it).

Sources: Databricks [Extend Genie Code with agent skills](https://docs.databricks.com/aws/en/genie-code/skills) · [Use Genie Code (approval modes, accept/reject)](https://docs.databricks.com/aws/en/genie-code/use-genie-code) · [Personalizing Genie Code: instructions, skills, memory, MCP](https://www.databricks.com/blog/personalizing-genie-code-instructions-skills-memory-and-mcp) · [databricks-solutions/genie-code-skills-demo](https://github.com/databricks-solutions/genie-code-skills-demo).
