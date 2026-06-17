# ABC SDK Contract (shared)

Every skill instruments runs through the ABC SDK rather than writing ABC tables directly.

| Method | Purpose |
|---|---|
| `start_run(component, entity, run_type)` | open a run; returns `run_id`/`trace_id` |
| `end_run(run_id, status)` | close a run with final status |
| `log_audit(run_id, metrics)` | rows read/written/rejected, timings, identity |
| `log_balance(run_id, checks)` | counts + financial control totals (Balance) |
| `log_dq(run_id, results)` | DQ rule outcomes + action taken (Control) |
| `log_exception(run_id, error)` | structured error capture |
| `log_cost(run_id, consumption)` | DBU/time/Genie-session consumption (FinOps) |

Notes: methods are idempotent and safe from batch, streaming and DLT contexts. Delivered as workspace Python modules (no wheel).
