# InsureLake - Refined Build Roadmap

Status: active · 2026-06-18 · Owner: EY
Companions: `../PROJECT_CONTEXT.md` (context) · `../skills/_shared/project-structure.md` (layout).

## Strategy (how we build)
- **Bottom-up by tier:** `core -> dataio/services -> framework -> runners/agents`. Build primitives before engines so engines stay thin.
- **Spec-first, structure-pinned:** spec -> Genie Code generates into the mapped path -> test -> benchmark.
- **Single source of truth:** `core/metadata` dataclasses generate DDL + JSON-schema (`scripts/codegen`).
- **Execution mode built once** (`framework/_base`), reused by every engine.
- **Continuous benchmark (PoC);** the scorecard gates the full build.
- **Agentic execution layer is the primary UX:** chat -> spec -> skills/Genie -> pipeline (control plane only; Spark/DLT runs the data).

## Quality Gate - Definition of Done for EVERY build step
A step is DONE only when ALL nine pass:
1. **Spec** - component spec authored, self-reviewed, human-approved (before any code).
2. **Placement** - output in its mapped path (`scaffold-structure` validation); nothing at repo root / unmapped.
3. **Contract** - implements the relevant `core/contracts` interface (typed).
4. **Generation** - Genie Code output passes self-review (idempotent, no `SELECT *`, secrets via scopes, no PII in logs, ABC hooks present) and compiles.
5. **Tests** - unit tests via `create-unit-tests`, >80% coverage, all green; integration test where Spark is required.
6. **Instrumentation** - calls the ABC SDK (audit/balance/cost) + structured logging with a trace id.
7. **Benchmark** - functional correctness vs golden outputs + consumption recorded (slice).
8. **Govern** - confidence-scored; HITL approved; agent actions audited to ABC.
9. **Integration** - `databricks bundle validate` passes; smoke test on the target.

No step advances to the next until its gate is green. This is the quality contract.

## Phases (bottom-up)

### Phase 0 - Foundation lock (Wave 0)
- 0.1 Apply the revised structure (`core/{metadata,config,common,contracts}`, `dataio/`, `services/`, `framework/_base`, `agents/`, `scripts/codegen/`).
- 0.2 `core/contracts` - Reader, LoadStrategy, Engine, Check, Masker protocols.
- 0.3 `scripts/codegen` - `core/metadata` -> DDL + JSON-schema (SSOT).
- 0.4 `services/abc` - ABC SDK (FND-011) from `abc-sdk-spec.md`.
- 0.5 Wire control skills (`cost-tracking`, `logging`) to `services/abc`.
- 0.6 Re-baseline the backlog + PROJECT_CONTEXT to the revised tiers.

### Phase 1 - Reusable primitives (dataio + services)
- 1.1 `dataio/readers` · 1.2 `dataio/load_strategy` · 1.3 `dataio/transform` · 1.4 `dataio/checks` + `dataio/maskers` · 1.5 `services/observability` + `services/finops`.

### Phase 2 - Engines (framework)
- 2.1 `framework/_base` (Engine + declarative + imperative builders).
- 2.2 ingestion · 2.3 harmonization · 2.4 dq · 2.5 reconciliation · 2.6 masking.

### Phase 3 - Wire & benchmark
- 3.1 `runners/jobs` + `runners/pipelines` + `resources/` (DAB) for the synthetic policy feed.
- 3.2 benchmark: thin slice (ingest -> harmonize -> dq -> recon -> mask) -> scorecard (fidelity + correctness + consumption).

### Phase 4 - Scale & hardening
- 4.1 CI/CD (Asset Bundles + tests), env promotion, secrets.
- 4.2 observability + finops dashboards + customer cost-estimation model.

## Track A - Agentic Execution Layer (the primary UX)
Goal: a governed chatbot where you see all framework capabilities, converse to produce a **spec**, and skills + Genie Code build the pipeline. Control plane only - the bot builds; Spark/DLT runs.

- **A0 Capability Registry** - machine-readable catalog of every capability (sources, load strategies, transforms, DQ rules/actions, masking techniques, engine modes), derived from skills/specs front-matter. The chatbot's menu. *(start early)*
- **A1 Conversational Spec-Authoring** - chat gathers requirements -> emits a spec (`.md`) or metadata JSON (`metadata-population` + spec templates). *(start early, parallel to Phase 1-2)*
- **A2 Router Wiring** - chatbot -> `agents/router` (Agent Bricks Supervisor) -> framework-dev/authoring skills + Genie Code -> pipeline. *(after Phase 2 - needs engines)*
- **A3 Govern + Memory** - HITL approval, confidence thresholds, ABC audit of agent actions, feedback loop. *(with A2)*
- **A4 Chat Surface** - Genie space / Databricks App exposing the menu + conversation; end-to-end demo (onboard a feed by chat). *(Phase 4)*

Quality for Track A: every agent-produced spec and every generated pipeline must pass the full Quality Gate; golden-conversation + generation-fidelity evals; nothing writes a managed asset without HITL. The bot can only build what the framework provides, so the framework (Phases 0-2) comes first; A0+A1 run in parallel from Phase 1, A2-A4 land in Phase 4.

## Dependency summary
`core -> dataio/services -> framework -> runners/agents`; Track A: A0/A1 parallel early, A2-A4 after engines.

## Environment
Everything targets Databricks (Premium). The framework + primitives + a thin engine slice are built and benchmarked first (Genie Code); the full Supervisor chatbot, scale, and CI/CD follow.

## Status (2026-06-18)
Done: structure finalized; FND-003 config loader (in `core/config`); Wave 0 specs (config-model, control-tables-ddl, abc-sdk, benchmark-plan, project-structure); control + foundation skills authored. Next executable: Phase 0 step 0.1 (apply revised structure).
