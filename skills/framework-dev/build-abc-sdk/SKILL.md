---
id: framework-dev.build-abc-sdk
name: Build ABC SDK
category: framework-dev
version: 0.1.0
maturity: draft
status: exemplar
owner_role: Data Engineer
runtime: genie-code
fe_ready: true
build_order: 0
depends_on: ['framework-dev.build-config-model']
backlog_ids: ['FND-010', 'FND-011', 'FND-013', 'FND-014']
inputs: ['abc_sdk_spec', 'abc_table_schema']
outputs: ['abc_sdk_modules', 'unit_tests']
tools: ['genie-code', 'abc-sdk']
---

# Build ABC SDK

> Generate the ABC SDK (workspace Python modules) wrapping the existing ABC Delta tables, plus unit tests.

## Purpose / when to use
Use once, early (Wave 0), to generate the ABC SDK that every other framework component and skill calls. It wraps the existing ABC Delta tables behind a clean interface so notebooks never write ABC tables directly.

## Inputs (contract)
- `abc_sdk_spec` - the approved `.md` spec defining the SDK interface.
- `abc_table_schema` - DDL/columns of the existing ABC Audit, Balance, Control tables.
- `standards` - coding standards from `_shared/standards.md`.

## Procedure (Genie-Code-ready steps)
1. Read `abc_sdk_spec` and the existing ABC table schema; do not change the table contracts.
2. Generate workspace Python modules (no wheel) exposing: `start_run`, `end_run`, `log_audit`, `log_balance`, `log_dq`, `log_exception`, `log_cost`.
3. Make every method idempotent and safe to call from batch, streaming and DLT contexts.
4. Generate unit tests covering the run lifecycle and each log method against a test schema.
5. Self-review (`control.self-review`); on pass, stage for HITL approval.

## Outputs (contract)
- `abc_sdk_modules` - workspace `.py` files importable across the framework.
- `unit_tests` - pytest modules.
- Backward-compatibility note vs the existing ABC schema.

## Guardrails & policy
- No wheel packaging - deliver as workspace source deployed via Asset Bundles.
- Must not alter existing ABC table schemas or break current consumers.
- Secrets via Databricks secrets only; never inline.

## Govern hooks
- Output passes [[control.self-review]]; HITL approval required before merge.
- The SDK itself is what other skills use for ABC audit + cost.

## Examples
- Input: spec + 3 ABC tables -> Output: `abc_sdk/` modules + `tests/` + compat note; all tests green.

## Acceptance / eval
- SDK writes verified against ABC tables; existing consumers unaffected; coverage > 80%.

## References
- Backlog: FND-010, FND-011, FND-013, FND-014
- Shared: ../../_shared/abc-sdk-contract.md, ../../_shared/standards.md
