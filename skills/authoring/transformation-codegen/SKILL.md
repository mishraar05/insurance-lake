---
id: authoring.transformation-codegen
name: Transformation Code Generation
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
fe_ready: true
build_order: 3
depends_on: ['authoring.source-target-mapping']
backlog_ids: ['AGENT-012']
inputs: ['mapping_config', 'standards']
outputs: ['transform_sql_spark', 'tests']
tools: ['genie-code']
---

# Transformation Code Generation

> Generate standardize/cleanse transform code (SQL/Spark) from the mapping config.

## Purpose / when to use
Generate standardize/cleanse transform code (SQL/Spark) from the mapping config.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `mapping_config`
- `standards`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `transform_sql_spark`
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
- Backlog: AGENT-012
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
