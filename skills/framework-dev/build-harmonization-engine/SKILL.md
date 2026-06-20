---
id: framework-dev.build-harmonization-engine
name: Build Harmonization Engine
category: framework-dev
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Data Engineer
runtime: genie-code
build_order: 1
depends_on: ['framework-dev.build-ingestion-engine', 'domain.pc-acord-canonical']
backlog_ids: ['HARM-001', 'HARM-002', 'HARM-010', 'HARM-020', 'HARM-030', 'HARM-031', 'HARM-050', 'HARM-051', 'HARM-054']
inputs: ['harmonization_spec', 'mapping_config']
outputs: ['harmonization_engine_source', 'tests']
tools: ['genie-code', 'lakeflow', 'abc-sdk']
---

# Build Harmonization Engine

> Generate the harmonization/curation engine: transforms, standardization/cleansing UDFs, SCD1/2/append, silver+gold.

## Purpose / when to use
Generate the harmonization/curation engine: transforms, standardization/cleansing UDFs, SCD1/2/append, silver+gold.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `harmonization_spec`
- `mapping_config`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `harmonization_engine_source`
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
- Backlog: HARM-001, HARM-002, HARM-010, HARM-020, HARM-030, HARM-031, HARM-050, HARM-051, HARM-054
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
