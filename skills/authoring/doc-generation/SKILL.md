---
id: authoring.doc-generation
name: Documentation Generation
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
build_order: 3
depends_on: ['authoring.metadata-population']
backlog_ids: ['AGENT-017']
inputs: ['metadata', 'lineage']
outputs: ['data_dictionary', 'runbooks']
tools: ['genie-code', 'unity-catalog']
---

# Documentation Generation

> Generate data dictionary, lineage notes and runbooks from metadata and Unity Catalog.

## Purpose / when to use
Generate data dictionary, lineage notes and runbooks from metadata and Unity Catalog.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `metadata`
- `lineage`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `data_dictionary`
- `runbooks`

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
- Backlog: AGENT-017
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
