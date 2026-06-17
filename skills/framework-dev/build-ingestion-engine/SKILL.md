---
id: framework-dev.build-ingestion-engine
name: Build Ingestion Engine
category: framework-dev
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Data Engineer
runtime: genie-code
fe_ready: true
build_order: 1
depends_on: ['framework-dev.build-abc-sdk', 'framework-dev.build-config-model']
backlog_ids: ['ING-001', 'ING-002', 'ING-010', 'ING-012', 'ING-020', 'ING-030', 'ING-031', 'ING-052']
inputs: ['ingestion_spec', 'config_model']
outputs: ['ingestion_engine_source', 'tests']
tools: ['genie-code', 'lakeflow', 'auto-loader', 'abc-sdk']
---

# Build Ingestion Engine

> Generate the metadata-driven ingestion engine: batch + stream, declarative + non-declarative, append + SCD2, with ABC hooks.

## Purpose / when to use
Generate the metadata-driven ingestion engine: batch + stream, declarative + non-declarative, append + SCD2, with ABC hooks.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `ingestion_spec`
- `config_model`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `ingestion_engine_source`
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
- Backlog: ING-001, ING-002, ING-010, ING-012, ING-020, ING-030, ING-031, ING-052
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
