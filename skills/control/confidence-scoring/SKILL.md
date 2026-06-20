---
id: control.confidence-scoring
name: confidence-scoring
category: control
version: 0.1.0
maturity: draft
status: active
owner_role: ML/AI Engineer
runtime: agent-bricks
build_order: 0
depends_on: ['control.self-review']
backlog_ids: ['FND-021']
inputs: ['artifact', 'review_result']
outputs: ['confidence_score', 'route']
tools: ['standards']
---

# Confidence Scoring

> Attach a calibrated confidence score to each agent output and route low-confidence results to a human.

## Purpose / when to use
Run immediately after [[control.self-review]] and before the HITL gate. It attaches a calibrated 0-1 confidence score to an agent output so the router can auto-pass high-confidence work and escalate the rest to a human.

## Inputs (contract)
- `artifact` - the generated object (config, code, mapping, rule).
- `review_result` - the output of [[control.self-review]] (passed flag + issues).
- `context` - artifact_type, task complexity, and how novel/ambiguous the inputs were.

## Procedure (Genie-Code-ready steps)
1. Gather signals: self-review pass/fail and warn count; schema/validation result; input ambiguity; similarity to known-good patterns; the model's self-reported uncertainty.
2. Combine signals into a 0-1 score using a documented rubric (weights live in config, not hardcoded).
3. Map the score to a band: high / medium / low, with per-artifact-type thresholds.
4. Decide route: `auto` only if band = high AND zero blockers; otherwise `hitl` with the reasons attached.
5. Log score, band, signals and rationale to ABC via [[control.logging]].

## Outputs (contract)
- `confidence_score` (0-1), `band` (high|medium|low), `route` (auto|hitl), `rationale`.

## Guardrails & policy
- Any blocker from self-review forces `low`/`hitl` - never override a blocker.
- Thresholds and weights are configuration; calibrate from labeled history.
- Score is advisory to the router, never a substitute for the HITL gate on managed-asset writes.

## Govern hooks
- Consumes [[control.self-review]]; emits to ABC; feeds the [[orchestration.router]] HITL gate.

## Examples
- Clean self-review + familiar SCD2 config -> 0.86 high -> auto.
- Ambiguous source->target mapping with 2 warns -> 0.40 low -> hitl with reasons.

## Acceptance / eval
- On a labeled set (good + seeded-bad), low-confidence routing flags 100% of blocker artifacts (no false negatives); calibration error within tolerance.

## References
- Backlog: FND-021
- Shared: ../../_shared/standards.md
