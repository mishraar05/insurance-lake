---
id: authoring.metadata-population
name: Metadata Population
category: authoring
version: 0.1.0
maturity: draft
status: exemplar
owner_role: ML/AI Engineer
runtime: genie-code
build_order: 3
depends_on: ['authoring.data-profiling', 'control.confidence-scoring', 'domain.pc-acord-canonical']
backlog_ids: ['AGENT-010', 'FND-003']
inputs: ['source_connection', 'profile_report', 'target_layer']
outputs: ['ingestion_config', 'harmonization_config']
tools: ['genie-code', 'config-loader', 'abc-sdk']
---

# Metadata Population

> Profile a source and draft the ingestion + harmonization config for human approval.

## Purpose / when to use
Use when onboarding a new source feed. Given a source, the skill profiles it and drafts the ingestion + harmonization config rows the framework needs - turning a multi-hour manual task into a reviewed draft.

## Inputs (contract)
- `source_connection` - connection/reference to the source (a synthetic dataset for the PoC, or the live source).
- `profile_report` - from [[authoring.data-profiling]].
- `target_layer` - bronze and the intended silver/gold targets.

## Procedure (Genie-Code-ready steps)
1. Pull the source schema + `profile_report` (types, keys, distributions, candidate watermark).
2. Infer load type (full vs incremental/CDC), watermark column, partition strategy, append vs SCD2.
3. Map source entities to the ACORD canonical model via [[domain.pc-acord-canonical]].
4. Emit `ingestion_config` and `harmonization_config` rows conforming to the config schema (`_shared`).
5. Run [[control.self-review]] then [[control.confidence-scoring]]; route low-confidence fields to HITL.
6. On approval, write configs via the config loader and log audit + cost to ABC.

## Outputs (contract)
- `ingestion_config` - validated config rows for the ingestion engine.
- `harmonization_config` - mapping + load-pattern config for the harmonization engine.
- Confidence-annotated diff for human approval.

## Guardrails & policy
- Never write config without HITL approval.
- Flag suspected PII columns and hand to [[authoring.pii-masking-classification]] (do not guess masking).
- Configs must validate against the schema or the skill fails closed.

## Govern hooks
- Self-review + confidence scoring mandatory; all proposals and approvals logged to ABC.

## Examples
- Input: a `policy` source + profile -> Output: incremental+SCD2 ingestion config, mapping to canonical `policy`/`coverage`, 3 fields flagged low-confidence for review.

## Acceptance / eval
- On the synthetic P&C `policy` feed, generated config drives an end-to-end run with correct SCD2 and zero schema validation errors (feeds BENCH-011/012).

## References
- Backlog: AGENT-010, FND-003
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
