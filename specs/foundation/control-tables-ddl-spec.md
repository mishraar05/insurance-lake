---
id: foundation.control-tables-ddl
title: FND-002 - Control Tables DDL Specification
owner: EY
status: draft
target_path: src/core/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/foundation/control-tables-ddl-spec.md
acceptance:
  - "pytest tests/unit/test_control_tables_ddl.py"
regeneration: scaffold-then-edit
---

# FND-002 - Control Tables DDL Specification

Status: complete · Skill: `framework-dev.build-config-model`
Deployable DDL: `../../conf/ddl/control_tables.sql`

Defines the 8 Unity Catalog Delta control tables in `insurelake_config.config` that drive the framework:
- Implemented: `cfg_source`, `cfg_target`, `cfg_load`, `cfg_transform`, `cfg_dq_rule`
- Planned: `cfg_recon_rule`, `cfg_masking_rule`, `cfg_dependency`

Keys: each table has a PRIMARY KEY; `cfg_load` / `cfg_transform` / `cfg_dq_rule` carry FOREIGN KEYs to `cfg_source` / `cfg_target`.
Entity field definitions: see `./config-model-spec.md` (FND-001). Deploy by running `conf/ddl/control_tables.sql`.
