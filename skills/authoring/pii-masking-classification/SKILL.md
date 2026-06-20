---
id: authoring.pii-masking-classification
name: PII + Masking Classification
category: authoring
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
build_order: 3
depends_on: ['authoring.data-profiling']
backlog_ids: ['AGENT-015', 'MASK-002']
inputs: ['profile_report', 'sample_data']
outputs: ['pii_classification', 'masking_policy']
tools: ['genie-code', 'unity-catalog']
---

# PII + Masking Classification

> Classify PII/PHI columns and suggest a masking policy/config.

## Purpose / when to use
Classify PII/PHI columns and suggest a masking policy/config.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `profile_report`
- `sample_data`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `pii_classification`
- `masking_policy`

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
- Backlog: AGENT-015, MASK-002
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
