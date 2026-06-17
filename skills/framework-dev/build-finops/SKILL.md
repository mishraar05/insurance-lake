---
id: framework-dev.build-finops
name: Build FinOps
category: framework-dev
version: 0.1.0
maturity: draft
status: scaffold
owner_role: FinOps/Analyst
runtime: genie-code
fe_ready: true
build_order: 4
depends_on: ['control.cost-tracking']
backlog_ids: ['FINOPS-001', 'FINOPS-002', 'FINOPS-010', 'FINOPS-020']
inputs: ['finops_spec', 'consumption_metrics']
outputs: ['cost_mart', 'finops_dashboard']
tools: ['genie-code', 'system.billing', 'abc-sdk']
---

# Build FinOps

> Generate the FinOps consumption capture, cost mart and AI/BI cost dashboard (Genie + warehouse DBUs, unit costs).

## Purpose / when to use
Generate the FinOps consumption capture, cost mart and AI/BI cost dashboard (Genie + warehouse DBUs, unit costs).
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `finops_spec`
- `consumption_metrics`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `cost_mart`
- `finops_dashboard`

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
- Backlog: FINOPS-001, FINOPS-002, FINOPS-010, FINOPS-020
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
