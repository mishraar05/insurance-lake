---
id: orchestration.pipeline-build
name: Pipeline Build (meta-skill)
category: orchestration
version: 0.1.0
maturity: draft
status: scaffold
owner_role: Architect
runtime: agent-bricks
fe_ready: true
build_order: 3
depends_on: ['authoring.metadata-population', 'authoring.transformation-codegen', 'authoring.dq-rule-suggestion']
backlog_ids: ['AGENT-002']
inputs: ['feed_request']
outputs: ['deployed_feed_pipeline']
tools: ['agent-bricks', 'genie-code', 'abc-sdk']
---

# Pipeline Build (meta-skill)

> Compose authoring skills to onboard a feed end to end (profile->config->map->codegen->DQ->recon->mask->test->doc), gated by control skills and logged to ABC.

## Purpose / when to use
Compose authoring skills to onboard a feed end to end (profile->config->map->codegen->DQ->recon->mask->test->doc), gated by control skills and logged to ABC.
_TODO: expand triggers and boundaries._

## Inputs (contract)
- `feed_request`

## Procedure (Genie-Code-ready steps)
_TODO: numbered, deterministic steps Genie Code can follow to produce the output._

## Outputs (contract)
- `deployed_feed_pipeline`

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
- Backlog: AGENT-002
- Spec: _TODO link to the component .md spec_
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md, ../../_shared/glossary.md
