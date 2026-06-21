---
id: ingestion.schema-evolution
title: Schema Evolution - Decision Tree & Implementation Guide
owner: EY
status: active
target_path: src/framework/ingestion/
owning_skill: insurelake-spec-codegen
backlog: [ING-SCH-001]
provides:
  - SchemaEvolutionConfig
  - QuarantineSchemaConfig
  - apply_schema_evolution
  - validate_schema_compatibility
depends_on:
  - foundation.config-model
  - dataio.load_strategy.append-strategy
  - dataio.load_strategy.merge-strategy
generation_context:
  - specs/ingestion/schema-evolution-spec.md
  - specs/foundation/config-model-spec.md
  - specs/dataio/append-strategy-spec.md
acceptance:
  - "pytest tests/unit/test_schema_evolution.py --cov=src/framework/ingestion --cov-report=term-missing --cov-fail-under=80"
  - "mypy src/framework/ingestion/ --strict"
  - "ruff check src/framework/ingestion/"
regeneration: scaffold-then-edit
---

# ING-SCH-001 - Schema Evolution Specification

**Status:** Active · 2026-06-20 · Skill: \`insurelake-spec-codegen\`  
**Execution Mode:** Decision Tree-Based Configuration  
**Target DBR:** 15.4 LTS or later

---
