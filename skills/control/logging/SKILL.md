---
id: control.logging
name: logging
category: control
version: 0.1.0
maturity: draft
status: active
owner_role: Data Engineer
runtime: notebook
fe_ready: true
build_order: 0
depends_on: []
backlog_ids: ['FND-023']
inputs: ['run_context', 'event']
outputs: ['log_records', 'trace_id']
tools: ['abc-sdk']
---

# Structured Logging

> Emit standardized, correlated run/event logs with trace IDs to ABC.

## Purpose / when to use
The observability substrate every skill and engine calls. It emits standardized, correlated run/event logs with a trace id to ABC so a run can be reconstructed end-to-end (ingestion -> gold). Pairs with ABC SDK `log_audit` / `log_exception`.

## Inputs (contract)
- `run_context` - run_id, component, entity.
- `event` - level, message, structured fields.
- `trace_id` - generated at run start, propagated to every downstream step.

## Procedure (Genie-Code-ready steps)
1. Generate or propagate a `trace_id` at run start; attach it to all events in the run.
2. Emit structured records (JSON: timestamp, run_id, trace_id, component, entity, level, event, fields).
3. Redact PII/secret fields before emit (redaction list from standards).
4. Route records to ABC (`log_audit` / `log_exception`) and to the platform log (DLT event log / driver logs).
5. Keep levels and schema consistent across batch, streaming and DLT contexts.

## Outputs (contract)
- `log_records` (structured), `trace_id` for cross-component correlation.

## Guardrails & policy
- Never log PII or secrets (enforced redaction); consistent schema; non-blocking (logging failure must not fail the run).

## Govern hooks
- Underpins [[runtime.failure-triage]] (reads these), observability, and the agent audit trail; writes through the ABC SDK.

## Examples
- A harmonization run emits start / step / quality / end events under one trace_id; a failure additionally emits `log_exception`.

## Acceptance / eval
- All events for one run share a single trace_id and are queryable in ABC; no PII present; failure-triage can reconstruct the run from them.

## References
- Backlog: FND-023 (depends on the ABC SDK, FND-011)
- Shared: ../../_shared/abc-sdk-contract.md, ../../_shared/standards.md
