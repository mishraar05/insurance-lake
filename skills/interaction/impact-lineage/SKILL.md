---
id: interaction.impact-lineage
name: Impact / Lineage Analysis
category: interaction
version: 0.1.0
maturity: draft
status: scaffold
owner_role: ML/AI Engineer
runtime: agent-bricks
fe_ready: false
build_order: 4
depends_on: ['interaction.ops-qa']
backlog_ids: ['AGENT-032']
inputs: ['change_request']
outputs: ['impact_report']
tools: ['agent-bricks', 'unity-catalog']
---

# Impact / Lineage Analysis

> Answer downstream-impact questions using Unity Catalog lineage.

## Purpose / when to use
Answer downstream-impact questions using Unity Catalog lineage.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `change_request`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `impact_report`

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
- Backlog: AGENT-032
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
