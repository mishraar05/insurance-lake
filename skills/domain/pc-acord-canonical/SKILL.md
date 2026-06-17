---
id: domain.pc-acord-canonical
name: P&C ACORD Canonical Knowledge
category: domain
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Architect
runtime: agent-bricks
fe_ready: true
build_order: 0
depends_on: []
backlog_ids: ['HARM-021']
inputs: ['entity_request']
outputs: ['canonical_definitions']
tools: ['unity-catalog']
---

# P&C ACORD Canonical Knowledge

> Authoritative P&C / ACORD canonical model knowledge (party, policy, coverage, claim, payment, loss) used by build and authoring skills.

## Purpose / when to use
Authoritative P&C / ACORD canonical model knowledge (party, policy, coverage, claim, payment, loss) used by build and authoring skills.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `entity_request`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `canonical_definitions`

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
- Backlog: HARM-021
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
