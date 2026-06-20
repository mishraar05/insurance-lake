---
id: control.self-review
name: Self-Review
category: control
version: 0.1.0
maturity: draft
status: exemplar
owner_role: ML/AI Engineer
runtime: agent-bricks
build_order: 0
depends_on: []
backlog_ids: ['FND-020']
inputs: ['artifact', 'standards']
outputs: ['review_result', 'issues']
tools: ['standards']
---

# Self-Review

> Validate any agent-generated artifact (config, code, spec) against standards before it is submitted for human approval.

## Purpose / when to use
Run immediately after any other skill produces an artifact (config, transform code, spec, DQ rule) and before it is shown to a human for approval. It is the first line of the govern loop.

## Inputs (contract)
- `artifact` - the generated object (code string, config JSON, or markdown).
- `artifact_type` - one of: config | sql | pyspark | spec | dq_rule | mapping.
- `standards` - the relevant section(s) of `_shared/standards.md`.

## Procedure (Genie-Code-ready steps)
1. Load the checklist for `artifact_type` from `_shared/standards.md`.
2. Statically check the artifact against each rule (naming, idempotency, no hardcoded secrets, PII handling, ABC hooks present, no `SELECT *` into managed tables, deterministic output).
3. For code, dry-parse / compile where possible; for config, validate against the config schema.
4. Produce `issues[]` each with severity (blocker | warn | info), rule id, location, and suggested fix.
5. Set `passed = true` only if there are zero blockers.

## Outputs (contract)
- `review_result`: { passed: bool, issues: [...], checklist_version }
- Emits an ABC audit event via [[control.logging]].

## Guardrails & policy
- Never auto-fix and submit; only annotate. Fixes route back to the producing skill.
- A failed self-review blocks the HITL submission.

## Govern hooks
- This skill IS a govern primitive; it still logs its own run to ABC.
- Feeds [[control.confidence-scoring]] (a clean review raises confidence).

## Examples
- Input: a transform with `SELECT *` and no audit hook -> Output: passed=false, 2 blockers (banned `SELECT *`, missing ABC hook).

## Acceptance / eval
- Golden set of 10 artifacts (5 good, 5 with seeded violations); skill must flag all blockers with no false negatives.

## References
- Backlog: FND-020
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md
