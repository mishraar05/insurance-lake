# Framework-Building Skills

Markdown-first, Databricks-targeted skills used to **develop the P&C metadata-driven framework** and to **operate it**. Each `SKILL.md` is the portable source of truth, compiled to its runtime (Genie Code / Agent Bricks / Genie space / notebook). See `../PROJECT_CONTEXT.md`.

## Two families
- **framework-dev/** - build the reusable framework components from their `.md` specs (run once).
- **authoring/** - capabilities the finished framework uses to onboard feeds repeatedly.
- **control/**, **domain/** shared; **runtime/**, **interaction/** operate; **orchestration/** (incl. the `router` supervisor) composes the rest.

## Build order (logical waves, tied to backlog)

### Wave 0 - Foundation

| Skill | Category | Runtime | FE | Backlog | Depends on |
|---|---|---|---|---|---|
| `confidence-scoring` | control | agent-bricks | yes | FND-021 | control.self-review |
| `cost-tracking` | control | notebook | yes | FND-022 | - |
| `logging` | control | notebook | yes | FND-023 | - |
| `self-review` | control | agent-bricks | yes | FND-020 | - |
| `pc-acord-canonical` | domain | agent-bricks | yes | HARM-021 | - |
| `build-abc-sdk` | framework-dev | genie-code | yes | FND-010, FND-011, FND-013, FND-014 | framework-dev.build-config-model |
| `build-config-model` | framework-dev | genie-code | yes | FND-001, FND-002, FND-003, FND-005 | domain.pc-acord-canonical |

### Wave 1 - Core engines

| Skill | Category | Runtime | FE | Backlog | Depends on |
|---|---|---|---|---|---|
| `build-harmonization-engine` | framework-dev | genie-code | yes | HARM-001, HARM-002, HARM-010, HARM-020, HARM-030, HARM-031, HARM-050, HARM-051, HARM-054 | framework-dev.build-ingestion-engine, domain.pc-acord-canonical |
| `build-ingestion-engine` | framework-dev | genie-code | yes | ING-001, ING-002, ING-010, ING-012, ING-020, ING-030, ING-031, ING-052 | framework-dev.build-abc-sdk, framework-dev.build-config-model |
| `build-orchestration` | framework-dev | genie-code | yes | HARM-040, DEVOPS-010 | framework-dev.build-ingestion-engine, framework-dev.build-harmonization-engine |

### Wave 2 - Quality, recon & masking

| Skill | Category | Runtime | FE | Backlog | Depends on |
|---|---|---|---|---|---|
| `build-dq-engine` | framework-dev | genie-code | yes | DQ-001, DQ-002, DQ-010, DQ-011, DQ-030, DQ-040 | framework-dev.build-harmonization-engine |
| `build-masking-engine` | framework-dev | genie-code | - | MASK-001, MASK-002, MASK-010, MASK-020, MASK-021 | framework-dev.build-harmonization-engine |
| `build-reconciliation-engine` | framework-dev | genie-code | yes | REC-001, REC-002, REC-010, REC-011, REC-020 | framework-dev.build-harmonization-engine |

### Wave 3 - Agentic authoring

| Skill | Category | Runtime | FE | Backlog | Depends on |
|---|---|---|---|---|---|
| `data-profiling` | authoring | genie-code | yes | AGENT-010 | control.self-review |
| `doc-generation` | authoring | genie-code | yes | AGENT-017 | authoring.metadata-population |
| `dq-rule-suggestion` | authoring | genie-code | yes | AGENT-013, DQ-002 | authoring.data-profiling |
| `metadata-population` | authoring | genie-code | yes | AGENT-010, FND-003 | authoring.data-profiling, control.confidence-scoring, domain.pc-acord-canonical |
| `pii-masking-classification` | authoring | genie-code | - | AGENT-015, MASK-002 | authoring.data-profiling |
| `recon-rule-gen` | authoring | genie-code | yes | AGENT-014, REC-002 | authoring.metadata-population |
| `source-target-mapping` | authoring | genie-code | yes | AGENT-011, HARM-020 | authoring.metadata-population, domain.pc-acord-canonical |
| `test-synthetic-data` | authoring | genie-code | yes | AGENT-016, ING-041 | authoring.metadata-population |
| `transformation-codegen` | authoring | genie-code | yes | AGENT-012 | authoring.source-target-mapping |
| `pipeline-build` | orchestration | agent-bricks | yes | AGENT-002 | authoring.metadata-population, authoring.transformation-codegen, authoring.dq-rule-suggestion |

### Wave 4 - Ops, interaction, FinOps

| Skill | Category | Runtime | FE | Backlog | Depends on |
|---|---|---|---|---|---|
| `build-finops` | framework-dev | genie-code | yes | FINOPS-001, FINOPS-002, FINOPS-010, FINOPS-020 | control.cost-tracking |
| `build-observability` | framework-dev | genie-code | yes | OBS-001, OBS-010, OBS-011, OBS-020 | framework-dev.build-abc-sdk |
| `impact-lineage` | interaction | agent-bricks | - | AGENT-032 | interaction.ops-qa |
| `nl-pipeline-authoring` | interaction | genie-code | yes | AGENT-030 | authoring.metadata-population |
| `ops-qa` | interaction | genie-space | yes | AGENT-031 | control.logging |
| `anomaly-drift` | runtime | agent-bricks | - | AGENT-022, ING-050 | control.logging |
| `failure-triage` | runtime | agent-bricks | - | AGENT-020 | control.logging |
| `self-healing` | runtime | agent-bricks | - | AGENT-021 | runtime.failure-triage |

### Wave 5 - Delivery

| Skill | Category | Runtime | FE | Backlog | Depends on |
|---|---|---|---|---|---|
| `build-cicd` | framework-dev | genie-code | - | DEVOPS-001, DEVOPS-010, DEVOPS-012 | framework-dev.build-orchestration |
| `framework-build` | orchestration | agent-bricks | yes | BENCH-010 | framework-dev.build-abc-sdk, framework-dev.build-ingestion-engine, framework-dev.build-harmonization-engine |
| `router` | orchestration | agent-bricks | - | AGENT-003 | orchestration.framework-build, orchestration.pipeline-build, control.self-review, control.confidence-scoring |

> All skills target Databricks (Premium).