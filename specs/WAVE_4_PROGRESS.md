---
id: docs.wave-4-progress
title: "Wave 4 Progress Tracker"
owner: EY
status: draft
target_path: docs/tracking/
owning_skill: documentation
backlog: []
provides: []
depends_on: []
generation_context: []
acceptance: []
regeneration: fully-generated
---

# Wave 4 Progress Tracker

**Date:** 2026-06-18  
**Status:** 🚀 **STARTED** — 0/15 specs complete (0%)

---

## Wave 4 Scope: Ops/Interaction/FinOps

**Goal:** Build operational intelligence, user interaction capabilities, and cost management features.

**Categories:**
1. **Interaction (Agentic)** — Natural language authoring, Ops Q&A chatbot, impact/lineage analysis
2. **FinOps** — Cost tracking, estimation, dashboard
3. **Runtime Ops (Optional)** — Failure triage, self-healing, anomaly detection

---

## Progress Summary

| Category | Complete | Total | Status | Priority |
|----------|----------|-------|--------|----------|
| **Interaction** | 0 | 3 | 🚧 **ACTIVE** | **HIGH** |
| **FinOps** | 0 | 3 | ⏸️ Pending | HIGH |
| **Runtime Ops** | 0 | 3 | ⏸️ Pending | MEDIUM |
| **Deployment** | 0 | 6 | ⏸️ Pending | MEDIUM |
| **TOTAL** | **0** | **15** | **0%** | - |

---

## Category 1: Interaction (Agentic) — 0/3 complete

**Purpose:** User-facing agentic capabilities for natural language interaction with the lakehouse.

### Specs to Create

1. 🎯 **ops-qa-chatbot-spec.md** (AGENT-031) — **PRIORITY 1** ← **USER FOCUS**
   - **Purpose:** Conversational Q&A chatbot for operational queries
   - **Capabilities:**
     - Answer questions about pipelines, data quality, jobs, feeds
     - Query metadata tables (Feed, Job, DQRule, ReconRule)
     - Explain lineage, dependencies, SLAs
     - Troubleshoot failures (recent errors, logs, metrics)
     - Query Unity Catalog (tables, schemas, columns)
   - **Implementation:** Databricks Genie Space over metadata tables
   - **Dependencies:** metadata-models-spec, ABC framework
   - **Status:** ⏸️ Not started

2. ⏸️ **nl-pipeline-authoring-spec.md** (AGENT-030)
   - **Purpose:** Natural language pipeline creation
   - **Capabilities:** 
     - "Create a pipeline from S3 bucket X to table Y with SCD2"
     - Parse intent → generate Feed/Job config → execute pipeline-build skill
   - **Status:** ⏸️ Not started

3. ⏸️ **impact-lineage-spec.md** (AGENT-032)
   - **Purpose:** Impact analysis and lineage visualization
   - **Capabilities:**
     - Upstream dependencies (what feeds this table?)
     - Downstream impact (what breaks if I change this?)
     - Column-level lineage
   - **Integration:** Unity Catalog lineage APIs
   - **Status:** ⏸️ Not started

---

## Category 2: FinOps — 0/3 complete

**Purpose:** Cost tracking, estimation, and financial operations dashboard.

### Existing Specs (to validate/implement)

4. ⏸️ **cost-tracking-spec.md** (FINOPS-001)
   - **Path:** `/specs/finops/cost-tracking-spec.md`
   - **Purpose:** Capture consumption metrics for all operations
   - **Status:** ✅ Spec exists, needs validation

5. ⏸️ **cost-estimation-spec.md** (FINOPS-002)
   - **Path:** `/specs/finops/cost-estimation-spec.md`
   - **Purpose:** Estimate customer costs (low/expected/high bands)
   - **Status:** ✅ Spec exists, needs validation

6. ⏸️ **finops-dashboard-spec.md** (FINOPS-003)
   - **Path:** `/specs/finops/finops-dashboard-spec.md`
   - **Purpose:** Dashboard for cost visibility and monitoring
   - **Status:** ✅ Spec exists, needs validation

---

## Category 3: Runtime Ops (Optional) — 0/3 complete

**Purpose:** Autonomous operational capabilities (triage, self-heal, anomaly detection).

### Specs to Create

7. ⏸️ **failure-triage-spec.md** (AGENT-020)
   - **Purpose:** Automated failure analysis and RCA
   - **Capabilities:** Parse logs, identify root cause, suggest fixes
   - **Status:** ⏸️ Not started

8. ⏸️ **self-healing-spec.md** (AGENT-021)
   - **Purpose:** Automatic remediation of common failures
   - **Capabilities:** Retry with backoff, schema drift repair, credential refresh
   - **Status:** ⏸️ Not started

9. ⏸️ **anomaly-detection-spec.md** (AGENT-022)
   - **Purpose:** Detect data quality drift and anomalies
   - **Capabilities:** Statistical anomaly detection, alerting
   - **Status:** ⏸️ Not started

---

## Category 4: Deployment & Integration — 0/6 complete

**Purpose:** Deploy Wave 4 capabilities as Databricks assets.

### Specs to Create

10. ⏸️ **genie-space-setup-spec.md** (AGENT-031-DEPLOY)
    - **Purpose:** Deploy Ops Q&A as Databricks Genie Space
    - **Capabilities:** Configure Genie Space, connect to metadata tables, instructions
    - **Status:** ⏸️ Not started

11. ⏸️ **chatbot-api-spec.md** (AGENT-031-API)
    - **Purpose:** API wrapper for chatbot (optional, for external integration)
    - **Status:** ⏸️ Not started

12. ⏸️ **dashboard-deployment-spec.md** (FINOPS-003-DEPLOY)
    - **Purpose:** Deploy FinOps dashboard as Lakeview dashboard
    - **Status:** ⏸️ Not started

13. ⏸️ **agent-orchestration-spec.md** (AGENT-003)
    - **Purpose:** Router/Supervisor agent (Agent Bricks) for intent classification
    - **Status:** ⏸️ Not started

14. ⏸️ **metadata-query-api-spec.md** (AGENT-040)
    - **Purpose:** REST API for metadata queries (for external tools)
    - **Status:** ⏸️ Not started

15. ⏸️ **integration-tests-spec.md** (WAVE4-TESTS)
    - **Purpose:** End-to-end tests for Wave 4 capabilities
    - **Status:** ⏸️ Not started

---

## Recommended Sequence

### Phase 1: Chatbot Foundation (User Priority)
1. ✅ **ops-qa-chatbot-spec.md** — Core chatbot spec ← **START HERE**
2. Validate existing FinOps specs (cost-tracking, cost-estimation, finops-dashboard)
3. **genie-space-setup-spec.md** — Deploy chatbot as Genie Space

### Phase 2: FinOps Implementation
4. Implement cost-tracking-spec.md
5. Implement cost-estimation-spec.md
6. Implement finops-dashboard-spec.md

### Phase 3: Advanced Interaction
7. nl-pipeline-authoring-spec.md
8. impact-lineage-spec.md

### Phase 4: Runtime Ops (Optional)
9. failure-triage-spec.md
10. self-healing-spec.md
11. anomaly-detection-spec.md

### Phase 5: Integration & Deployment
12. Agent orchestration (router)
13. API wrappers
14. Integration tests

---

## Next Steps

**IMMEDIATE:** Start with **ops-qa-chatbot-spec.md** (AGENT-031)

This spec will define:
* Chatbot capabilities and use cases
* Metadata tables to query (Feed, Job, DQRule, etc.)
* Genie Space configuration
* Sample questions and answers
* Integration with ABC framework
* Deployment as Databricks Genie Space

---

## Dependencies

**Prerequisites (from earlier waves):**
* ✅ Wave 0: Foundation (metadata models, ABC framework)
* 🚧 Wave 1: Data I/O (50% complete)
* ⏸️ Wave 2: Quality/Recon/Masking (not started)
* ⏸️ Wave 3: Agentic Authoring (not started)

**Wave 4 can proceed in parallel** because:
* Chatbot queries metadata tables (already defined in Wave 0)
* FinOps specs already exist (just need validation/implementation)
* Runtime ops are independent features

---

## Notes

* **User Priority:** Chatbot (ops-qa-chatbot-spec.md) is the top priority
* **Existing Assets:** FinOps specs already exist, just need validation
* **Genie Space:** Primary deployment mechanism for chatbot (Unity Catalog integration)
* **Validation Framework:** Apply same 9-point validation to all Wave 4 specs

---

**Status:** Ready to start with ops-qa-chatbot-spec.md
