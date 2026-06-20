---
id: interaction.ops-qa
name: Ops Q&A
category: interaction
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: genie-space
build_order: 4
depends_on: ['control.logging']
backlog_ids: ['AGENT-031']
inputs: ['nl_question']
outputs: ['answer']
tools: ['genie-space', 'abc-sdk', 'system-tables']
---

# Ops Q&A

> Genie space answering operational questions over ABC + system tables.

## Purpose / when to use
Genie space answering operational questions over ABC + system tables.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `nl_question`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `answer`

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
- Backlog: AGENT-031
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
