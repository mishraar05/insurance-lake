---
id: runtime.self-healing
name: Self-Healing
category: runtime
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: agent-bricks
fe_ready: false
build_order: 4
depends_on: ['runtime.failure-triage']
backlog_ids: ['AGENT-021']
inputs: ['diagnosis', 'control_rules']
outputs: ['remediation_action']
tools: ['agent-bricks', 'abc-sdk']
---

# Self-Healing

> Retry/backoff, reprocess failed micro-batches, quarantine-and-replay - gated by control rules.

## Purpose / when to use
Retry/backoff, reprocess failed micro-batches, quarantine-and-replay - gated by control rules.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `diagnosis`
- `control_rules`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `remediation_action`

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
- Backlog: AGENT-021
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
