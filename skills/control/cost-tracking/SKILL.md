---
id: control.cost-tracking
name: Cost Tracking
category: control
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Data Engineer
runtime: notebook
fe_ready: true
build_order: 0
depends_on: []
backlog_ids: ['FND-022']
inputs: ['run_context']
outputs: ['consumption_metrics']
tools: ['abc-sdk', 'system.billing']
---

# Cost Tracking

> Capture per-run DBU/time/Genie-session consumption and write it to ABC for FinOps.

## Purpose / when to use
Capture per-run DBU/time/Genie-session consumption and write it to ABC for FinOps.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `run_context`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `consumption_metrics`

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
- Backlog: FND-022
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
