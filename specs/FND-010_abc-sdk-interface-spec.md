# FND-010 - ABC SDK Interface Specification

Status: active · 2026-06-18 · Skill: `framework-dev.build-abc-sdk` · Build task: FND-011
Delivered as **workspace Python modules** (no wheel). Wraps the existing ABC (Audit/Balance/Control) Delta tables so no component writes ABC tables directly.

## Why
Every framework component and skill must record what ran (Audit), whether data balanced (Balance), quality outcomes and control decisions (Control), and consumption (FinOps). The SDK is the single, idempotent interface for that. It unblocks `control.cost-tracking` and `control.logging`.

## Interface
| Method | Signature | Purpose | Writes to |
|---|---|---|---|
| start_run | `start_run(component, entity, run_type) -> RunHandle{run_id, trace_id}` | open a run; mint run_id + trace_id | ABC Audit (run open) |
| end_run | `end_run(run_id, status, metrics=None)` | close a run with final status | ABC Audit (run close) |
| log_audit | `log_audit(run_id, metrics: dict)` | rows read/written/rejected, timings, identity | ABC Audit |
| log_balance | `log_balance(run_id, checks: list)` | counts + financial control totals | ABC Balance |
| log_dq | `log_dq(run_id, results: list)` | DQ rule outcomes + action taken | ABC Control |
| log_exception | `log_exception(run_id, error)` | structured error capture | ABC Control/Exception |
| log_cost | `log_cost(run_id, consumption: dict)` | DBU/time/Genie-session consumption | ABC Cost (FinOps) |

## Semantics
- **Idempotent**: safe to call from batch, Structured Streaming, and Lakeflow Declarative Pipeline contexts; repeated calls with the same keys upsert, not duplicate.
- **Trace id**: minted in `start_run`, propagated by `control.logging` to every event so a run is reconstructable end-to-end (ingestion -> gold).
- **Non-blocking**: an ABC write failure logs locally and never fails the parent data run.
- **Mapping**: methods map onto the existing ABC table schema (provided at build time) - the SDK adapts to ABC, ABC is not redesigned.

## Errors
Raise typed errors (`ABCConnectionError`, `ABCWriteError`) but downgrade to warning+local-log when invoked inside a data pipeline (resilience over strictness).

## Usage
```
from sdk.abc import ABC
abc = ABC(catalog="insurelake_abc", schema="abc")
run = abc.start_run(component="ingestion", entity="policy", run_type="BATCH_INCREMENTAL")
try:
    abc.log_audit(run.run_id, {"rows_read": 10000, "rows_written": 9980, "rows_rejected": 20})
    abc.log_balance(run.run_id, [{"check": "src_vs_bronze_count", "src": 10000, "tgt": 9980}])
    abc.log_cost(run.run_id, {"dbu_seconds": 1234, "genie_dbu": 0.4})
    abc.end_run(run.run_id, status="SUCCESS")
except Exception as e:
    abc.log_exception(run.run_id, e); abc.end_run(run.run_id, status="FAILED")
```

## Acceptance
- All 7 methods write to the mapped ABC tables; idempotent re-runs do not duplicate; >80% unit coverage (use `framework-dev.create-unit-tests`); existing ABC consumers unaffected (FND-014).
