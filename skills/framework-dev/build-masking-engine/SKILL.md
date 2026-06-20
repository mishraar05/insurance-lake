---
id: framework-dev.build-masking-engine
name: Build Masking Engine
category: framework-dev
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Data Engineer
runtime: genie-code
build_order: 2
depends_on: ['framework-dev.build-harmonization-engine']
backlog_ids: ['MASK-001', 'MASK-002', 'MASK-010', 'MASK-020', 'MASK-021']
inputs: ['masking_spec', 'classification_config']
outputs: ['masking_engine_source', 'tests']
tools: ['genie-code', 'unity-catalog', 'abc-sdk']
---

# Build Masking Engine

> Generate the masking engine: PII classification/tagging, UC dynamic masks + physical tokenize/hash, policy applier.

## Purpose / when to use
Generate the masking engine: PII classification/tagging, UC dynamic masks + physical tokenize/hash, policy applier.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `masking_spec`
- `classification_config`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `masking_engine_source`
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
- Backlog: MASK-001, MASK-002, MASK-010, MASK-020, MASK-021
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
