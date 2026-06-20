---
id: framework-dev.build-dq-engine
name: Build Data Quality Engine
category: framework-dev
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Data Engineer
runtime: genie-code
build_order: 2
depends_on: ['framework-dev.build-harmonization-engine']
backlog_ids: ['DQ-001', 'DQ-002', 'DQ-010', 'DQ-011', 'DQ-030', 'DQ-040']
inputs: ['dq_spec', 'rule_config']
outputs: ['dq_engine_source', 'tests']
tools: ['genie-code', 'lakeflow', 'lakehouse-monitoring', 'abc-sdk']
---

# Build Data Quality Engine

> Generate the DQ engine: rule model, in-motion (expectations/inline) + at-rest (monitoring), warn/block/quarantine actions.

## Purpose / when to use
Generate the DQ engine: rule model, in-motion (expectations/inline) + at-rest (monitoring), warn/block/quarantine actions.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `dq_spec`
- `rule_config`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `dq_engine_source`
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
- Backlog: DQ-001, DQ-002, DQ-010, DQ-011, DQ-030, DQ-040
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
