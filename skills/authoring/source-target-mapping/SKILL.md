---
id: authoring.source-target-mapping
name: Source-to-Target Mapping
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
build_order: 3
depends_on: ['authoring.metadata-population', 'domain.pc-acord-canonical']
backlog_ids: ['AGENT-011', 'HARM-020']
inputs: ['source_schema', 'canonical_model']
outputs: ['mapping_config']
tools: ['genie-code']
---

# Source-to-Target Mapping

> Propose bronze->silver->gold column mappings using schema, profiling and the ACORD canonical model.

## Purpose / when to use
Propose bronze->silver->gold column mappings using schema, profiling and the ACORD canonical model.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `source_schema`
- `canonical_model`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `mapping_config`

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
- Backlog: AGENT-011, HARM-020
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
