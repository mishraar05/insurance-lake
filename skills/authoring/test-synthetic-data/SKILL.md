---
id: authoring.test-synthetic-data
name: Test + Synthetic Data Generation
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
fe_ready: true
build_order: 3
depends_on: ['authoring.metadata-population']
backlog_ids: ['AGENT-016', 'ING-041']
inputs: ['schema', 'rules']
outputs: ['unit_tests', 'synthetic_data']
tools: ['genie-code']
---

# Test + Synthetic Data Generation

> Generate unit tests for transforms/rules and edge-case synthetic data (also the PoC demo dataset).

## Purpose / when to use
Generate unit tests for transforms/rules and edge-case synthetic data (also the PoC demo dataset).
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `schema`
- `rules`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `unit_tests`
- `synthetic_data`

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
- Backlog: AGENT-016, ING-041
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
