---
id: control.cost-tracking
name: cost-tracking
category: control
version: 0.1.0
maturity: draft
status: active
owner_role: Data Engineer
runtime: notebook
build_order: 0
depends_on: []
backlog_ids: ['FND-022']
inputs: ['run_context']
outputs: ['consumption_metrics']
tools: ['abc-sdk', 'system.billing']
---

# Cost Tracking

> Capture per-run DBU/time/Genie-session consumption and write it to ABC for FinOps.

## Purpose / when to use
Wrap every framework/skill run to capture consumption (DBU / time / Genie session) and write it to ABC. It is the data source for the FinOps dashboard and the customer cost estimate. Pairs with the ABC SDK `log_cost` method.

## Inputs (contract)
- `run_context` - run_id, component, entity, start/end timestamps.
- compute identifiers - warehouse_id, cluster_id, job_run_id, Genie session id.

## Procedure (Genie-Code-ready steps)
1. On run start, record start time + compute identifiers (via ABC `start_run`).
2. On run end, gather consumption: run duration, SQL-warehouse DBU-time, Genie Code serverless DBUs (tag `databricks-product: genie`), token counts if available.
3. Join to `system.billing.usage` by tag/SKU for billable usage; capture raw consumption (DBU-seconds, durations).
4. Attribute consumption to unit keys (per feed / transform / Genie generation / run).
5. Write via ABC `log_cost(run_id, consumption)`.

## Outputs (contract)
- `consumption_metrics` - DBUs, durations, Genie sessions, tokens + attribution keys.

## Guardrails & policy
- Consumption metrics captured; $ is modeled by build-finops using list prices.
- Never fail the parent run on a cost-capture error - log and continue.
- Respect the `databricks-product: genie` tag and Unity AI Gateway budgets.

## Govern hooks
- Writes through the ABC SDK (`log_cost`); feeds [[framework-dev.build-finops]] (FINOPS-002/010).

## Examples
- A `build-ingestion-engine` Genie Code run logs Genie serverless DBU-seconds + warehouse DBU-time, keyed to the component and feed.

## Acceptance / eval
- Every run has a cost record in ABC; consumption reconciles with `system.billing.usage`; build-finops can compute a unit cost from it.

## References
- Backlog: FND-022 (depends on the ABC SDK, FND-011)
- Shared: ../../_shared/abc-sdk-contract.md
