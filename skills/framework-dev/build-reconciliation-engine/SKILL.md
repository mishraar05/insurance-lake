---
id: framework-dev.build-reconciliation-engine
name: Build Reconciliation Engine
category: framework-dev
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Data Engineer
runtime: genie-code
build_order: 2
depends_on: ['framework-dev.build-harmonization-engine']
backlog_ids: ['REC-001', 'REC-002', 'REC-010', 'REC-011', 'REC-020']
inputs: ['recon_spec', 'recon_config']
outputs: ['recon_engine_source', 'tests']
tools: ['genie-code', 'abc-sdk']
---

# Build Reconciliation Engine

> Generate the reconciliation engine: count + financial control-total checks across layers, feeding ABC Balance.

## Purpose / when to use
Generate the reconciliation engine: count + financial control-total checks across layers, feeding ABC Balance.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `recon_spec`
- `recon_config`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `recon_engine_source`
- `tests`

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
- Backlog: REC-001, REC-002, REC-010, REC-011, REC-020
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
