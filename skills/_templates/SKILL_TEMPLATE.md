---
id: <category>.<slug>
name: <Skill Name>
category: <category>
version: 0.1.0
maturity: draft
status: scaffold
owner_role: <role>
runtime: <genie-code|agent-bricks|genie-space|notebook>
build_order: <0-5>
depends_on: [<dep ids>]
backlog_ids: [<TASK-IDs>]
inputs: [<inputs>]
outputs: [<outputs>]
tools: [<tools>]
---

# <Skill Name>

> <one-line purpose>

## Purpose / when to use
<one-line purpose>
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `<input>`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `<output>`

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
- Backlog: <TASK-IDs>
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
