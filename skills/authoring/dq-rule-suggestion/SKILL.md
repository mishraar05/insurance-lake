---
id: authoring.dq-rule-suggestion
name: DQ Rule Suggestion
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
build_order: 3
depends_on: ['authoring.data-profiling']
backlog_ids: ['AGENT-013', 'DQ-002']
inputs: ['profile_report']
outputs: ['dq_rules']
tools: ['genie-code']
---

# DQ Rule Suggestion

> Propose DQ rules, thresholds and actions from data profiles for human review.

## Purpose / when to use
Propose DQ rules, thresholds and actions from data profiles for human review.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `profile_report`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `dq_rules`

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
- Backlog: AGENT-013, DQ-002
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
