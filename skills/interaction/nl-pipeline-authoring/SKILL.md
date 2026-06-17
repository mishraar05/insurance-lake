---
id: interaction.nl-pipeline-authoring
name: NL Pipeline Authoring
category: interaction
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-code
fe_ready: true
build_order: 4
depends_on: ['authoring.metadata-population']
backlog_ids: ['AGENT-030']
inputs: ['nl_request']
outputs: ['config_draft']
tools: ['genie-code']
---

# NL Pipeline Authoring

> Turn a natural-language request into a draft pipeline config via Genie Code.

## Purpose / when to use
Turn a natural-language request into a draft pipeline config via Genie Code.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `nl_request`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `config_draft`

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
- Backlog: AGENT-030
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
