# PROJECT CONTEXT — P&C Insurance Lakehouse Accelerator (Databricks)

Status: living document · Last updated: 2026-06-17 · Owner: Clean
Purpose: single source of truth for everything decided so far, so the team (and any AI assistant) can resume with full context.

---

## 1. Goal & vision
Build a reusable, customer-presentable **accelerator** for Property & Casualty (P&C) insurance on the Databricks Data Intelligence Platform: a **metadata-driven data engineering framework** (working name "InsureLake") that stands up a governed Lakehouse and a curated set of P&C use cases. The framework is built and operated with the help of an **agentic solution (Databricks Genie Code)**.

## 2. Operating model / workflow
1. **Plan** — a low-level task backlog (Excel) defines the work.
2. **Specs** — author Genie-Code-ready `.md` specs in Claude Cowork. Specs are the **portable IP** and stay **edition-neutral**.
3. **Build** — feed specs to **Genie Code**; it generates the Lakeflow pipelines / SQL / Python.
4. **Benchmark on Free Edition** — prove the loop on Databricks Free Edition: (a) spec->Genie-Code fidelity, (b) functional correctness.
5. **Build on Paid** — reuse the same specs to build the full framework on the paid workspace.

Free Edition is a **benchmark harness**, not the build target. Free-Edition limits are captured as a "PoC profile", never baked into spec logic.

## 3. Scope — frameworks on the ABC foundation
Existing foundation: **ABC = Audit, Balance, Control** — a Delta-table-driven metadata framework with an existing data model and notebooks (to be modernized into a clean SDK).

Frameworks to build (all instrument ABC):
- **Ingestion** — batch + stream; declarative + non-declarative (selectable); append + SCD2.
- **Harmonization / Curation** — query- or Spark-based transforms; standardization & cleansing UDFs; declarative + non-declarative; micro-batch + near-real-time; SCD1/SCD2/append; silver + gold.
- **Data Quality** — at-rest + in-motion; rule definition; warn/block/quarantine; monitoring.
- **Reconciliation** — count + financial control-total checks across layers (feeds ABC Balance).
- **Data Masking** — PII/PHI classification; dynamic (UC) + physical (tokenize/hash) techniques.
- **Agentic** — metadata build, query/transform build, and more (see section 7).
- **FinOps** — cost monitoring + customer cost estimation (see section 8).
- **Observability** and **CI/CD** — cross-cutting.

## 4. Architecture decisions
- Medallion: Bronze (raw) -> Silver (conformed, **ACORD-aligned canonical model**: party, policy, coverage, claim, payment, loss) -> Gold (marts).
- Governance via **Unity Catalog** (access, masking, lineage, audit, model governance).
- Declarative = **Lakeflow Declarative Pipelines** (APPLY CHANGES for SCD); non-declarative = **Structured Streaming/batch + MERGE** on Lakeflow Jobs.
- A single **metadata/config contract** drives both engines; ABC is the audit/balance/control plane.
- Real-time/operational option: **Lakebase** + Spark real-time mode (paid).

## 5. Platform & tooling decisions
- **No wheel files.** Framework code = **Databricks workspace source** (notebooks / `.py` / `.sql` / Lakeflow pipeline definitions) in a Git folder (Repos), deployed via **Asset Bundles referencing source**.
- **Skills are Databricks-only** (not a Cowork/Claude plugin), markdown-first source of truth, compiled to runtime (Genie Code / Agent Bricks / Genie space / notebook).
- **Free Edition limits** (PoC profile): serverless-only; one active pipeline per type; max 5 concurrent job tasks; one 2X-Small SQL warehouse; limited model serving (no GPU / provisioned throughput / batch inference); one Vector Search endpoint; one workspace + one metastore; no account console; restricted outbound internet; daily quotas.
- On Free Edition: use **synthetic data** (no live CDC); heavier agentic/serving skills are **paid-only**.

## 6. Skills structure
Two families of single-job, versioned skills (see `skills/README.md` for the full catalog + build order):
- **framework-dev/** — build the reusable framework components from their specs (run once).
- **authoring/** — capabilities the finished framework uses to onboard feeds repeatedly.
- Shared: **control/** (self-review, confidence-scoring, cost-tracking, logging), **domain/** (pc-acord-canonical).
- Operate: **runtime/** (triage, self-heal, anomaly-drift), **interaction/** (NL authoring, ops-Q&A, impact-lineage).
- **orchestration/** — `router` (Agent Bricks Supervisor; single front door) routing to `framework-build` (composes framework-dev) and `pipeline-build` (composes authoring).

Anatomy: front-matter contract (id, runtime, fe_ready, depends_on, **backlog_ids**, inputs/outputs/tools) + body (Purpose / Inputs / Procedure / Outputs / Guardrails / Govern hooks / Examples / Acceptance / References). Govern loop: self-review -> confidence-scoring -> HITL -> ABC audit + cost on every skill.

Build waves: 0 Foundation -> 1 Core engines -> 2 Quality/recon/masking -> 3 Agentic authoring -> 4 Ops/interaction/FinOps -> 5 Delivery.

## 7. Agentic skills (summary)
Build-time: data-profiling, metadata-population, source-to-target mapping, transformation code-gen, DQ-rule suggestion, recon-rule generation, PII+masking classification, test+synthetic-data, doc-generation. Run-time: failure-triage/RCA, self-healing, anomaly/drift. Interaction: NL pipeline authoring, ops Q&A (Genie space), impact/lineage. Orchestration: a **Router/Supervisor agent** (Agent Bricks) is the single front door that classifies intent and routes to the right skills in dependency order. Principle: LLM stays in the **control plane** (author/operate), never the **data plane** (no per-row LLM).

## 8. FinOps & cost-estimation approach
Method: measure **consumption** on Free Edition (Genie Code DBUs, SQL-warehouse DBU-time, run time) -> derive **unit costs** (per feed / transform / Genie generation / run) -> apply **paid list prices** -> scale by customer **volume** = **probable cost** (low/expected/high bands).
Genie billing facts (verified Jun 2026): Genie Code launches a `PREMIUM_ALL_PURPOSE_SERVERLESS_COMPUTE` cluster (~$0.75/DBU); the SQL warehouse that runs generated queries is billed separately by DBU-time; from **2026-07-06** Genie moves to a free monthly allowance (150 DBU/identified user, LLM only) then pay-as-you-go; spend is tagged `databricks-product: genie` in `system.billing.usage` and governed via Unity AI Gateway + budgets. On Free Edition there is no dollar billing -> model cost from consumption x list price. The ABC **Cost-Tracking** control skill captures consumption everywhere.

## 9. Benchmark definition (Free Edition PoC)
(a) **Spec -> Genie Code fidelity** — can Genie Code generate a correct, working framework slice from the specs, and effort saved. (b) **Functional correctness** — generated ingestion/harmonization/DQ produce correct results end-to-end. Thin vertical slice: one synthetic feed -> ingest -> harmonize -> DQ -> recon -> mask; scorecard feeds the paid build and the customer estimate.

## 10. Deliverables to date (in this folder)
- `InsureLake_PnC_Accelerator_Ideation_Brief.docx` — the accelerator ideation brief.
- `InsureLake_Reference_Architecture.png` — Lakehouse reference architecture diagram.
- `AI_Ready_Backlog_Tasks*.xlsx` — 115 low-level tasks (Epic->Feature->Story->Task; 13 columns; Backlog/Legend/Summary).
- `skills/` — 34 framework-building + operating skills (scaffolded, backlog-linked, logically ordered) incl. the router + README catalog + template + `_shared` contracts.
- `PROJECT_CONTEXT.md` — this document.

## 11. Decision log
- 2026-06-17 — First deliverable = ideation brief (P&C, Lakehouse, mixed audience). Pitch deck deferred to last.
- 2026-06-17 — Build two frameworks (ingestion + harmonization) on the existing ABC framework; modernize ABC notebooks.
- 2026-06-17 — Task backlog: match AI_Ready_Backlog workbook; Epic->Feature->Story->Task; full scope incl. agentic; T-shirt sizing; 13 confirmed columns (no Notes — Free/paid encoded in Phase).
- 2026-06-17 — Develop via Databricks Free Edition + Genie Code to benchmark the PoC; move specs to paid edition for the real build.
- 2026-06-17 — Add a FinOps dashboard + customer cost-estimation model (probable cost with bands).
- 2026-06-17 — Skills: markdown-first source of truth; one skill per capability; add framework-dev skills; Databricks-only; no wheels; runtime defaults accepted.
- 2026-06-17 — Add a **Router / Supervisor agent** (Agent Bricks, GA) as the single front door orchestrating framework creation: classifies intent and routes to skills in dependency order, govern-looped + ABC-logged (skill `orchestration.router`; backlog `AGENT-003`).

## 12. Open items / next steps
- Author the remaining `SKILL.md` bodies (start at Wave 0/1: build-config-model, build-ingestion-engine, then the control + domain skills).
- Author the component `.md` specs the framework-dev skills consume.
- Confirm target cloud/region for the paid build and the FinOps list-price basis.
- Confirm the two lighthouse use cases for the accelerator demo (from the ideation brief).
- Decide first feed for the Free Edition benchmark slice (default: synthetic `policy`).

## 13. References
- Databricks Free Edition limitations — https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- Genie Code — https://docs.databricks.com/aws/en/genie-code/
- Agentic data engineering with Genie Code and Lakeflow — https://www.databricks.com/blog/agentic-data-engineering-genie-code-and-lakeflow
- Agent Bricks Supervisor Agent (multi-agent) — https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor
- Monitor costs using system tables — https://docs.databricks.com/aws/en/admin/usage/system-tables
- Manage budgets and cost controls for Genie — https://learn.microsoft.com/en-us/azure/databricks/genie/budgets

## 14. Refined build plan & agentic execution layer (2026-06-18)
The build follows a bottom-up, quality-gated roadmap (`core -> dataio/services -> framework -> runners/agents`) with the **Agentic Execution Layer** as the primary UX: a governed chatbot where you pick from all framework capabilities, converse to produce a spec, and skills + Genie Code build the pipeline (control plane only; Spark/DLT runs the data). Every build step must pass a 9-point Quality Gate. Full plan: `docs/ROADMAP.md`.

Decision log:
- 2026-06-18 - Adopt the agentic chatbot (capability registry -> conversational spec-authoring -> router -> skills/Genie -> pipeline) as the primary execution UX, governed by HITL + ABC audit; control plane only. Build bottom-up by tier with a 9-point Quality Gate per step (`docs/ROADMAP.md`).
