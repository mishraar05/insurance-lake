---
id: authoring.data-profiling
name: Data Profiling
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
fe_ready: true
build_order: 3
depends_on: ['control.self-review']
backlog_ids: ['AGENT-010']
inputs: ['source_connection', 'sample_data']
outputs: ['profile_report']
tools: ['genie-code', 'unity-catalog']
---

# Data Profiling

> Profile a source (types, keys, distributions, candidate watermarks) to feed metadata population and rule suggestion.

## Purpose / when to use
Profile a source (types, keys, distributions, candidate watermarks) to feed metadata population and rule suggestion.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `source_connection`
- `sample_data`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `profile_report`

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
- Backlog: AGENT-010
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
