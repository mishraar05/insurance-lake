---
id: authoring.recon-rule-gen
name: Reconciliation Rule Generation
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
fe_ready: true
build_order: 3
depends_on: ['authoring.metadata-population']
backlog_ids: ['AGENT-014', 'REC-002']
inputs: ['metadata', 'financial_columns']
outputs: ['recon_rules']
tools: ['genie-code']
---

# Reconciliation Rule Generation

> Propose count and financial control-total reconciliation checks per layer.

## Purpose / when to use
Propose count and financial control-total reconciliation checks per layer.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `metadata`
- `financial_columns`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `recon_rules`

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
- Backlog: AGENT-014, REC-002
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
