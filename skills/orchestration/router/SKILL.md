---
id: orchestration.router
name: Router / Supervisor Agent
category: orchestration
version: 0.1.0
maturity: draft
status: exemplar
owner_role: Architect
runtime: agent-bricks
fe_ready: false
build_order: 5
depends_on: ['orchestration.framework-build', 'orchestration.pipeline-build', 'control.self-review', 'control.confidence-scoring']
backlog_ids: ['AGENT-003']
inputs: ['intent', 'skill_registry', 'run_ledger']
outputs: ['execution_plan', 'step_results', 'status_report']
tools: ['agent-bricks', 'genie-code', 'genie-space', 'abc-sdk', 'unity-catalog']
---

# Router / Supervisor Agent

> Single front-door supervisor: classify intent and route to framework-dev / authoring / runtime / interaction skills in dependency order, govern-looped and ABC-logged.

## Purpose / when to use
The single front door for the framework-creation process and, later, for onboarding feeds and operating the framework. Given an intent, the supervisor decides which skills to call and in what order. It is **control-plane only** - it orchestrates code generation and operations, and never processes data rows itself.

## Inputs (contract)
- `intent` - NL or structured request, e.g. "stand up the framework", "build Wave 1", "build the ingestion engine", "onboard the policy feed", "why did the claims run fail last night".
- `skill_registry` - the front-matter of all skills (category, build_order, depends_on, backlog_ids, fe_ready).
- `run_ledger` - ABC-backed state of what has already been built / deployed.

## Procedure (Genie-Code-ready steps)
1. Classify `intent` and pick a route: BUILD -> framework-build (framework-dev/*), ONBOARD -> pipeline-build (authoring/*), OPERATE -> runtime/*, ASK -> interaction/*.
2. Select the candidate skills from `skill_registry`; build a dependency graph from `depends_on` + `build_order`.
3. Reconcile with `run_ledger`: drop completed steps; produce the ordered, minimal execution plan.
4. For each step: check `fe_ready` vs the target edition; invoke the worker (Genie Code for codegen, Genie space for Q&A, agent endpoint / UC function for control & authoring skills).
5. Govern loop: run control.self-review then control.confidence-scoring; if confidence < threshold OR the step writes a managed asset, open an HITL gate.
6. On approval, execute; capture outputs; log audit + cost to ABC via the SDK; update `run_ledger`.
7. Synthesize a status report (done / next / blocked) and emit benchmark metrics.

## Outputs (contract)
- `execution_plan` - ordered steps with skill ids + backlog ids.
- `step_results` - per-step artifacts + confidence + approval status.
- `status_report` - progress vs backlog, next actions, blockers.

## Guardrails & policy
- Control plane only; never transform data rows.
- No managed-asset write without HITL approval.
- Respect `fe_ready`: on Free Edition route through the Genie-Code sequencer stand-in and defer paid-only workers.
- Every routed step is logged to ABC (audit + cost) under one trace id.

## Govern hooks
- Embeds [[control.self-review]] + [[control.confidence-scoring]] on every step; HITL gate before writes; full agent audit trail (decisions, prompts, approvals) to ABC.

## Examples
- Intent "build Wave 0" -> plan: build-config-model -> build-abc-sdk (with control skills), in dependency order; each HITL-gated; ledger updated.
- Intent "onboard policy feed" -> route ONBOARD -> pipeline-build -> data-profiling -> metadata-population -> ... -> doc-generation.

## Acceptance / eval
- For a target wave the router produces a correct topological plan that matches the backlog dependencies, executes the FE-ready slice end to end, and the ledger reflects completion (feeds the BENCH scorecard).

## Runtime
- Target: Agent Bricks Supervisor Agent (paid, Unity-Catalog governed); workers = Genie spaces / agent endpoints / UC functions / Genie Code.
- Free-Edition benchmark: a lightweight Genie-Code sequencer that runs the same plan over `fe_ready` skills.

## References
- Backlog: AGENT-003 (depends AGENT-002)
- Routes: [[orchestration.framework-build]], [[orchestration.pipeline-build]]
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md
