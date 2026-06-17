---
id: orchestration.framework-build
name: Framework Build (meta-skill)
category: orchestration
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Architect
runtime: agent-bricks
fe_ready: true
build_order: 5
depends_on: ['framework-dev.build-abc-sdk', 'framework-dev.build-ingestion-engine', 'framework-dev.build-harmonization-engine']
backlog_ids: ['BENCH-010']
inputs: ['framework_specs']
outputs: ['deployed_framework']
tools: ['agent-bricks', 'genie-code', 'asset-bundles']
---

# Framework Build (meta-skill)

> Compose framework-dev skills to stand up the framework from the specs in logical order.

## Purpose / when to use
Compose framework-dev skills to stand up the framework from the specs in logical order.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `framework_specs`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `deployed_framework`

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
- Backlog: BENCH-010
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
