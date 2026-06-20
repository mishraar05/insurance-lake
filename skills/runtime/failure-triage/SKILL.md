---
id: runtime.failure-triage
name: Failure Triage / RCA
category: runtime
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: agent-bricks
build_order: 4
depends_on: ['control.logging']
backlog_ids: ['AGENT-020']
inputs: ['event_log', 'abc_exceptions']
outputs: ['diagnosis', 'proposed_fix']
tools: ['agent-bricks', 'abc-sdk', 'system-tables']
---

# Failure Triage / RCA

> Read DLT event log + ABC exceptions + traces to diagnose a failure and propose or run a fix.

## Purpose / when to use
Read DLT event log + ABC exceptions + traces to diagnose a failure and propose or run a fix.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `event_log`
- `abc_exceptions`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `diagnosis`
- `proposed_fix`

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
- Backlog: AGENT-020
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
