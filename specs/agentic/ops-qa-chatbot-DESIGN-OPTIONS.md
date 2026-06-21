---
id: agentic.ops-qa-chatbot-DESIGN-OPTIONS
title: Ops Q&A Chatbot — Design Options
owner: EY
status: draft
target_path: src/agentic/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/agentic/ops-qa-chatbot-DESIGN-OPTIONS.md
acceptance:
  - "pytest tests/unit/test_ops_qa_chatbot_DESIGN_OPTIONS.py"
regeneration: scaffold-then-edit
---

# Ops Q&A Chatbot — Design Options

**Purpose:** Evaluate architectural approaches for the Insurance Lake Ops Q&A Chatbot  
**Date:** 2026-06-18  
**Status:** Design Review

---

## Context

**Problem:** Operations teams need a conversational interface to query Insurance Lake metadata (feeds, jobs, DQ rules, failures) without writing SQL.

**Key Requirements:**
* Natural language understanding (not SQL)
* Query operational metadata (Feed, Job, DQRule, ReconRule, AuditLog)
* Unity Catalog integration
* Fast response times (<5 seconds)
* Security: respect UC access controls
* Auditability: log all queries

---

## Design Option 1: Databricks Genie Space (Recommended in Spec)

### Architecture

**Components:**
* **Genie Space** — Databricks-native conversational AI
* **SQL Warehouse** — executes generated SQL queries
* **Metadata Tables** — Feed, Job, DQRule, etc. (Unity Catalog tables)
* **System Instructions** — custom prompt engineering for domain knowledge

**User Flow:**
1. User asks question in Genie Space UI
2. Genie translates to SQL query
3. SQL executes on SQL Warehouse
4. Results formatted and returned to user

### Pros

✅ **Native Databricks integration** — no external infrastructure  
✅ **Unity Catalog built-in** — automatic table discovery, access control  
✅ **Fast time-to-value** — deploy in minutes, not weeks  
✅ **Serverless** — no compute management  
✅ **Cost-effective** — pay per query (SQL Warehouse DBU)  
✅ **Automatic schema inference** — Genie discovers table structures  
✅ **User authentication** — inherits Databricks workspace auth  
✅ **SQL transparency** — users see generated SQL (learning opportunity)

### Cons

❌ **Limited customization** — constrained by Genie capabilities  
❌ **SQL-only** — can't execute Python/Scala code  
❌ **No multi-step reasoning** — single query per question (no chaining)  
❌ **UI-only** — no API for external integrations (mobile app, Slack)  
❌ **Prompt engineering limits** — system instructions have character limits  
❌ **No custom tools** — can't add external data sources (e.g., Jira, ServiceNow)  
❌ **Query optimization** — limited control over generated SQL efficiency

### Implementation Complexity

**Effort:** 🟢 **LOW** (1-2 days)

**Steps:**
1. Create Genie Space in Databricks workspace
2. Connect metadata tables (Feed, Job, DQRule, etc.)
3. Configure system instructions (domain knowledge)
4. Test sample questions
5. Refine instructions based on results

**Skills Required:** Databricks admin, SQL, prompt engineering

### Cost Estimate

**Infrastructure:** $0 (uses existing SQL Warehouse)  
**Usage Cost:**  
* SQL Warehouse: ~$0.22/DBU (Serverless SQL Pro)
* Estimated usage: 100 queries/day × 0.1 DBU/query = 10 DBU/day = **~$2.20/day** (~$66/month)

**Genie Pricing (as of Jul 2026):**
* 150 DBU/user/month free (LLM only)
* Pay-as-you-go after free tier

### Best For

* **MVP / Proof of Concept** — validate chatbot value quickly
* **Small to medium teams** — 10-100 users
* **SQL-answerable questions** — operational metadata queries
* **Unity Catalog-centric** — all data in UC tables

---

## Design Option 2: Custom LLM Chatbot (LangChain + Mosaic AI)

### Architecture

**Components:**
* **Mosaic AI Gateway** — LLM routing (OpenAI, Anthropic, DBRX, Llama)
* **LangChain** — orchestration framework (agents, chains, tools)
* **Custom Tools** — Python functions for metadata queries
* **Vector Database** — embeddings for semantic search (optional)
* **FastAPI Backend** — REST API for chatbot
* **Frontend** — React/Streamlit UI or Slack integration

**User Flow:**
1. User asks question via UI/Slack/API
2. LangChain agent parses intent
3. Agent selects tools (SQL query, Python function, external API)
4. Tools execute (query metadata, call Jira API, etc.)
5. Agent synthesizes results into natural language response

### Pros

✅ **Full customization** — complete control over behavior  
✅ **Multi-step reasoning** — agent can chain multiple queries  
✅ **Custom tools** — integrate Jira, ServiceNow, PagerDuty, etc.  
✅ **API-first** — expose REST API for Slack, mobile, external tools  
✅ **Advanced features** — RAG (documentation), function calling, memory  
✅ **Multi-modal** — can return charts, dashboards, not just text  
✅ **Python execution** — run profiling, aggregations, complex logic  
✅ **LLM choice** — switch between models (cost vs. quality)

### Cons

❌ **High complexity** — requires LangChain, backend, frontend, hosting  
❌ **Infrastructure overhead** — need to deploy and manage services  
❌ **Security concerns** — must implement auth, access control, rate limiting  
❌ **Cost management** — LLM token costs can be unpredictable  
❌ **Longer time-to-value** — 4-6 weeks to build and test  
❌ **Maintenance burden** — more code to maintain and debug  
❌ **Requires ML/AI expertise** — prompt engineering, agent design, RAG tuning

### Implementation Complexity

**Effort:** 🟡 **MEDIUM-HIGH** (4-6 weeks)

**Architecture:**
```
┌─────────────┐
│ User (Slack,│
│  UI, API)   │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│ FastAPI Backend (hosted on Databricks Jobs) │
│ - Authentication (OAuth)                     │
│ - Rate limiting                              │
│ - Request routing                            │
└──────┬──────────────────────────────────────┘
       │
┌──────▼───────────────────────────────────────┐
│ LangChain Agent                              │
│ - Intent classification                       │
│ - Tool selection                              │
│ - Multi-step reasoning                        │
│ - Response generation                         │
└──────┬───────────────────────────────────────┘
       │
       ├─────────┬─────────┬─────────┬─────────┐
       │         │         │         │         │
┌──────▼──┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────┐ ┌─▼──────┐
│SQL Tool │ │Python │ │Jira   │ │Vector  │ │External│
│(metadata│ │Tool   │ │API    │ │Search  │ │APIs    │
│queries) │ │(UDFs) │ │Tool   │ │(docs)  │ │        │
└─────────┘ └───────┘ └───────┘ └────────┘ └────────┘
```

**Steps:**
1. Set up Mosaic AI Gateway (LLM routing)
2. Build LangChain agent with custom tools
3. Implement SQL query tool (metadata tables)
4. Implement Python execution tool (UDFs, profiling)
5. Add external integrations (Jira, PagerDuty)
6. Build FastAPI backend (REST API)
7. Build frontend (Streamlit or React)
8. Deploy on Databricks Jobs (scheduled API service)
9. Configure auth, rate limiting, monitoring

**Skills Required:** Python, LangChain, FastAPI, React/Streamlit, LLM engineering, DevOps

### Cost Estimate

**Infrastructure:**
* Databricks Job (API backend): ~$0.07/DBU × 24/7 = ~$50/day (~$1,500/month)
* Vector DB (if RAG): ~$100/month (Pinecone, Weaviate)

**LLM Usage:**
* OpenAI GPT-4: ~$0.03/1K tokens (input) + ~$0.06/1K tokens (output)
* 100 queries/day × 5K tokens = 500K tokens/day = **~$20/day** (~$600/month)

**Total:** ~$2,200/month (vs. $66/month for Genie)

### Best For

* **Advanced use cases** — multi-step reasoning, external integrations
* **API-first** — need Slack bot, mobile app, external tools
* **Custom workflows** — e.g., "analyze this failure and create Jira ticket"
* **Long-term investment** — willing to invest in custom solution

---

## Design Option 3: Hybrid (Genie + Agent Extensions)

### Architecture

**Components:**
* **Genie Space** — primary interface for simple queries
* **Custom Agent** — handles complex multi-step queries
* **Router** — classifies queries and routes to Genie or Agent
* **Shared Metadata** — both access same UC tables

**User Flow:**
1. User asks question
2. Router classifies intent (simple vs. complex)
3. **If simple:** route to Genie Space (fast, SQL-only)
4. **If complex:** route to custom Agent (multi-step, external APIs)
5. Return results to user

### Pros

✅ **Best of both worlds** — Genie for speed, Agent for complexity  
✅ **Cost-optimized** — most queries use cheap Genie, complex ones use Agent  
✅ **Incremental complexity** — start with Genie, add Agent later  
✅ **Flexibility** — can add tools to Agent over time  
✅ **Fallback** — if Genie fails, route to Agent

### Cons

❌ **Two systems to maintain** — Genie + Agent infrastructure  
❌ **Router complexity** — need intelligent routing logic  
❌ **Inconsistent UX** — users may not know which backend answered  
❌ **Split codebase** — Genie instructions + Agent code

### Implementation Complexity

**Effort:** 🟡 **MEDIUM** (3-4 weeks)

**Phase 1:** Deploy Genie (1 week)  
**Phase 2:** Build router + simple Agent (2 weeks)  
**Phase 3:** Add complex tools to Agent (1 week)

### Cost Estimate

**Hybrid Cost:**
* 80% queries → Genie: $2/day
* 20% queries → Agent: $4/day
* **Total:** ~$6/day (~$180/month)

### Best For

* **Phased rollout** — validate with Genie, scale with Agent
* **Cost-conscious** — optimize for simple queries
* **Mixed complexity** — some questions are simple, some need reasoning

---

## Design Option 4: SQL Analytics Dashboard (No Chatbot)

### Architecture

**Components:**
* **Lakeview Dashboard** — pre-built operational dashboards
* **Parameterized Widgets** — dropdowns, date pickers for filtering
* **Scheduled Alerts** — proactive notifications (no chat needed)

**User Flow:**
1. User opens dashboard (feeds, jobs, DQ, failures)
2. User selects filters (date range, feed name, job status)
3. Dashboard refreshes with filtered data
4. Alerts notify users of critical failures (email/Slack)

### Pros

✅ **Zero infrastructure** — dashboards are native to Databricks  
✅ **No LLM costs** — just SQL queries  
✅ **Visual insights** — charts, trends, not just text  
✅ **Proactive alerts** — users don't need to ask  
✅ **Easy to build** — drag-and-drop dashboard builder  
✅ **Lowest cost** — SQL Warehouse only

### Cons

❌ **Not conversational** — users must navigate dashboards  
❌ **Limited flexibility** — only pre-defined queries  
❌ **No natural language** — users must know what to look for  
❌ **Not a chatbot** — doesn't meet "conversational" requirement

### Implementation Complexity

**Effort:** 🟢 **LOW** (2-3 days)

**Steps:**
1. Create Lakeview dashboards (feeds, jobs, DQ, failures)
2. Add parameterized filters (date, feed, status)
3. Configure scheduled alerts (email/Slack)

### Cost Estimate

**Infrastructure:** $0 (uses existing SQL Warehouse)  
**Usage Cost:** ~$1/day (~$30/month)

### Best For

* **No chatbot requirement** — dashboards meet the need
* **Visual insights** — prefer charts over text
* **Lowest cost** — minimal infrastructure
* **Complement to chatbot** — use dashboards + chatbot together

---

## Comparison Matrix

| Criteria | Option 1: Genie | Option 2: Custom Agent | Option 3: Hybrid | Option 4: Dashboard |
|----------|----------------|------------------------|------------------|---------------------|
| **Time to Deploy** | 1-2 days | 4-6 weeks | 3-4 weeks | 2-3 days |
| **Cost (monthly)** | ~$66 | ~$2,200 | ~$180 | ~$30 |
| **Natural Language** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Multi-step Reasoning** | ❌ No | ✅ Yes | ✅ Yes (Agent) | ❌ No |
| **External Integrations** | ❌ No | ✅ Yes | ✅ Yes (Agent) | ❌ No |
| **API Available** | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| **Customization** | Low | High | Medium | Low |
| **Maintenance Effort** | Low | High | Medium | Low |
| **LLM Token Costs** | Low | High | Medium | None |
| **Unity Catalog Integration** | ✅ Native | ⚠️ Manual | ✅ Native (Genie) | ✅ Native |
| **SQL Transparency** | ✅ Yes | ⚠️ Optional | ✅ Yes (Genie) | ✅ Yes |
| **Skills Required** | SQL, Databricks | Python, ML, DevOps | Both | SQL, Databricks |

---

## Recommendation

### Phase 1: Start with **Option 1 (Genie Space)** — MVP

**Why:**
* Fastest time-to-value (1-2 days)
* Lowest cost ($66/month)
* Validates chatbot value with minimal investment
* Native UC integration (security, access control)
* Easiest to maintain

**Acceptance Criteria:**
* 90% of common operational questions answered correctly
* <5 second response times
* User feedback indicates value

### Phase 2: Evaluate Extension

**If successful, choose next step:**

**A. Satisfied with Genie?** → Stay with Option 1, optimize system instructions

**B. Need API/Slack/External Integrations?** → Upgrade to **Option 3 (Hybrid)**
* Add custom Agent for complex queries
* Keep Genie for simple queries
* Build Slack bot, API wrappers

**C. Need Full Control?** → Build **Option 2 (Custom Agent)**
* Replace Genie with custom LangChain agent
* Add RAG (documentation search)
* Integrate Jira, PagerDuty, ServiceNow

**D. Chatbot Not Needed?** → Fall back to **Option 4 (Dashboards)**
* Build operational dashboards
* Add scheduled alerts
* Focus on visual insights

---

## Decision Criteria

Use this decision tree:

```
Q1: Is natural language conversational interface required?
├─ NO → Option 4 (Dashboards)
└─ YES → Q2

Q2: Do you need external integrations (Jira, Slack, API)?
├─ NO → Q3
└─ YES → Q4

Q3: Can questions be answered with single SQL query?
├─ YES → Option 1 (Genie) — START HERE
└─ NO → Option 2 (Custom Agent)

Q4: Can you start with simple queries, add complexity later?
├─ YES → Option 3 (Hybrid)
└─ NO → Option 2 (Custom Agent)
```

---

## Risks & Mitigations

### Risk 1: Genie Can't Handle Complex Questions
**Mitigation:** Start with Option 1, track "unanswerable" questions, upgrade to Option 3 if >20% fail

### Risk 2: LLM Token Costs Explode (Option 2)
**Mitigation:** Set budgets, rate limits, cache responses, use cheaper models (DBRX, Llama)

### Risk 3: Users Don't Adopt Chatbot
**Mitigation:** Run pilot with 10 users, measure adoption, iterate on UX

### Risk 4: Security/Access Control Issues
**Mitigation:** Use Unity Catalog for all options, test with restricted users

---

## Next Steps

1. **Review design options** with stakeholders
2. **Choose Option 1 (Genie)** for MVP (recommended)
3. **Deploy Genie Space** (1-2 days)
4. **Test with pilot users** (1 week)
5. **Measure success metrics:**
   - Query success rate (>90%)
   - Response time (<5 sec)
   - User satisfaction (NPS)
   - Adoption rate (queries/user/day)
6. **Decide on Phase 2:**
   - Stay with Genie (if successful)
   - Upgrade to Hybrid (if need API/Slack)
   - Build Custom Agent (if need full control)

---

## Open Questions

1. **Q:** Do we need Slack integration?  
   **Impact:** If yes, lean toward Option 2 or 3

2. **Q:** Do we need to integrate with external ticketing (Jira, ServiceNow)?  
   **Impact:** If yes, Option 2 or 3 required

3. **Q:** What's the budget for LLM costs?  
   **Impact:** If <$200/month, Option 1 or 3 only

4. **Q:** What's the team's ML/Python expertise?  
   **Impact:** If limited, Option 1 or 4 only

5. **Q:** How many users will use the chatbot?  
   **Impact:** If >100, consider cost/scalability of Option 2

---

**END OF DESIGN OPTIONS DOCUMENT**
