---
id: framework-dev.build-config-model
name: build-config-model
category: framework-dev
version: 0.1.0
maturity: draft
status: active
owner_role: Data Engineer
runtime: genie-code
fe_ready: true
build_order: 0
depends_on: ['domain.pc-acord-canonical']
backlog_ids: ['FND-001', 'FND-002', 'FND-003', 'FND-005']
inputs: ['config_model_spec']
outputs: ['control_table_ddl', 'config_loader', 'validator']
tools: ['genie-code', 'unity-catalog']
---

# Build Config Model

> Generate the metadata/config control tables and the config loader/validator from the config-model spec.

## Purpose / when to use
Run once, early (Wave 0), to generate and evolve the metadata/config layer the whole framework reads: the Unity Catalog control tables, the typed config models, and the ConfigLoader + validator. FND-003 (loader + validator) is already implemented; this skill also owns the DDL (FND-002), seed configs (FND-004), config versioning/change-audit (FND-005), and the remaining entities (recon_rule, masking_rule, dependency).

## Inputs (contract)
- `config_model_spec` - the approved spec (`specs/FND-001_config-model-spec.md`).
- `abc_schema` - the existing ABC table schema (to align/link, not duplicate).
- `standards` - `_shared/standards.md`.

## Procedure (Genie-Code-ready steps)
1. From the spec, generate Unity Catalog DDL for the config tables (source, target, load, transform, dq_rule, recon_rule, masking_rule, dependency) in `insurelake_config.config` (see `specs/FND-002_control-tables-ddl.sql`).
2. Generate/maintain the typed config models + `ConfigLoader` with FK + business-rule validation (FND-003 done; extend with the 3 remaining models).
3. Add config versioning + change audit (FND-005): every config change records who/when/what to ABC.
4. Seed example P&C configs (FND-004) - the synthetic `policy` feed (source -> bronze load -> silver transform -> DQ rules).
5. Self-review -> confidence-score -> HITL; deploy DDL + code via Asset Bundles.

## Outputs (contract)
- `control_table_ddl` (8 tables), `config_loader` + `validator` (done), `seed_configs`, change-audit hooks.

## Guardrails & policy
- Align to / link the existing ABC schema; never duplicate ABC.
- Workspace source + Asset Bundles (no wheel); validation fails closed.
- PII columns flagged here drive [[framework-dev.build-masking-engine]].

## Govern hooks
- self-review -> [[control.confidence-scoring]] -> HITL; config changes logged to ABC via [[control.logging]].

## Examples
- Input: FND-001 spec -> Output: 8 CREATE TABLE statements + loader extensions + a seeded `policy` config that drives an end-to-end run.

## Acceptance / eval
- DDL deploys to Unity Catalog; ConfigLoader loads + validates the seed config with FK checks; a seeded feed runs end to end (feeds BENCH).

## Status (2026-06-18)
- FND-003 (loader+validator) DONE - 37 tests. FND-001 spec + FND-002 DDL authored. Pending: FND-004 seed configs, FND-005 versioning, and recon_rule / masking_rule / dependency models.

## References
- Backlog: FND-001, FND-002, FND-003, FND-005
- Specs: ../../../specs/FND-001_config-model-spec.md, ../../../specs/FND-002_control-tables-ddl.sql
- Shared: ../../_shared/standards.md, ../../_shared/abc-sdk-contract.md
