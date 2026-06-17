---
id: control.confidence-scoring
name: Confidence Scoring
category: control
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: agent-bricks
fe_ready: true
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
Attach a calibrated confidence score to each agent output and route low-confidence results to a human.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `artifact`
- `review_result`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `confidence_score`
- `route`

## Guardrails & policy
_TODO: PII handling, coding/naming standards, must-nots._

## Govern hooks
- Self-review: see [[control.self-review]]
- Confidence scoring: see [[control.confidence-scoring]]
- HITL gate: required before any write to a managed asset
- ABC audit + cost: log via [[control.logging]] and [[control.cost-tracking]]

## Examples
_TODO: 1-2 few-shot input -> output examples._

## Acceptance / eval
_TODO: golden test(s) + success metric (ties to BENCH scorecard)._

## References
- Backlog: FND-021
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
