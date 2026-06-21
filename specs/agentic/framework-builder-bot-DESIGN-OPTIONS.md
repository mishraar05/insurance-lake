---
id: agentic.framework-builder-bot-DESIGN-OPTIONS
title: Framework Builder Bot — Design Options
owner: EY
status: draft
target_path: src/agentic/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/agentic/framework-builder-bot-DESIGN-OPTIONS.md
acceptance:
  - "pytest tests/unit/test_framework_builder_bot_DESIGN_OPTIONS.py"
regeneration: scaffold-then-edit
---

# Framework Builder Bot — Design Options

**Purpose:** Evaluate architectural approaches for the Insurance Lake Framework Builder Bot  
**Date:** 2026-06-18  
**Status:** Design Review  
**Backlog ID:** AGENT-030 (NL Pipeline Authoring)

---

## Context

**Problem:** Developers need to build Insurance Lake frameworks (Ingestion, Harmonization, DQ, etc.) by selecting capabilities from a menu, and the bot generates the framework code automatically.

**Key Requirements:**
* **Capability-driven menu** — user selects frameworks, features, load strategies
* **Spec-based generation** — each capability maps to specs (spec-per-feature)
* **Code generation** — generate actual framework code (notebooks, pipelines, SQL)
* **Dependency resolution** — auto-pull dependent specs
* **Fast creation** — generate framework in minutes, not days
* **Reusable IP** — specs are portable, code is generated

---

## Use Case Flow

### Example Conversation

```
Bot: "Welcome! What framework do you want to build?"
     A. Ingestion Framework
     B. Harmonization/Curation Framework
     C. Data Quality Framework
     D. Masking Framework

User: "A. Ingestion"

Bot: "What ingestion capabilities do you need?"
     A. Batch Ingestion
     B. Streaming Ingestion
     C. Both

User: "A. Batch"

Bot: "Declarative or Non-Declarative?"
     A. Declarative (Lakeflow Spark Declarative Pipelines)
     B. Non-Declarative (PySpark + MERGE on Lakeflow Jobs)

User: "A. Declarative"

Bot: "What load strategy?"
     A. Append (insert-only)
     B. SCD1 (upsert without history)
     C. SCD2 (maintain history)
     D. Full Refresh (truncate + reload)

User: "C. SCD2"

Bot: "What source formats do you need to read?"
     [x] CSV
     [x] JSON
     [ ] Parquet
     [x] Delta
     [ ] Avro
     [ ] Excel
     [ ] JDBC (SQL Server, Postgres, etc.)

User: [selects CSV, JSON, Delta]

Bot: "Great! I'll build your Ingestion Framework with:
     - Batch ingestion (declarative)
     - SCD2 load strategy
     - CSV, JSON, Delta readers
     
     Pulling specs:
     ✓ file-readers-spec.md (CSV, JSON, Delta)
     ✓ scd2-strategy-spec.md
     ✓ engine-contracts-spec.md (dependencies)
     ✓ metadata-models-spec.md (dependencies)
     
     Generating code via Genie Code...
     
     ✅ Done! Your framework is ready:
     📂 /pipelines/ingestion_scd2/
        ├── readers/
        │   ├── csv_reader.py
        │   ├── json_reader.py
        │   └── delta_reader.py
        ├── strategies/
        │   └── scd2_strategy.py
        ├── engine/
        │   └── ingestion_engine.py
        ├── config/
        │   └── feed_config.yaml
        └── tests/
            └── test_ingestion.py
     
     Next steps:
     1. Review generated code
     2. Configure your feeds in feed_config.yaml
     3. Run the pipeline!"
```

---

## Design Option 1: Menu-Driven Chatbot (Structured Selections)

### Architecture

**Components:**
* **Chat Interface** — Databricks Assistant, Slack bot, or custom UI
* **Capability Registry** — maps capabilities → specs (from capability-registry-spec.md)
* **Spec Resolver** — pulls specs + dependencies
* **Genie Code Integration** — generates code from specs
* **Git/Workspace Writer** — saves generated code to workspace

**User Experience:**
* Bot presents multiple-choice questions
* User selects options (A/B/C or checkboxes)
* Bot validates selections (e.g., can't pick Streaming + Full Refresh)
* Bot shows selected capabilities before generation
* User confirms → Bot generates

### Pros

✅ **Clear user intent** — no ambiguity, explicit choices  
✅ **Validation built-in** — can enforce valid combinations  
✅ **Easy to implement** — simpler than NLP  
✅ **Guided experience** — users discover available capabilities  
✅ **Reproducible** — same selections = same output  
✅ **Lower LLM costs** — minimal token usage (no long prompts)

### Cons

❌ **Not truly conversational** — feels like a form  
❌ **Multiple turns** — many questions before generation  
❌ **Not flexible** — can't say "I want batch SCD2 for CSV files"  
❌ **Limited discovery** — users must navigate menu tree

### Implementation Details

**Conversation State Machine:**
```
State 1: Framework Selection
  ├─ Ingestion → State 2A
  ├─ Harmonization → State 2B
  └─ Data Quality → State 2C

State 2A: Ingestion Capabilities
  ├─ Batch → State 3A
  └─ Streaming → State 3B

State 3A: Declarative vs. Non-Declarative
  ├─ Declarative → State 4A
  └─ Non-Declarative → State 4B

State 4A: Load Strategy
  ├─ Append → State 5
  ├─ SCD1 → State 5
  ├─ SCD2 → State 5
  └─ Full Refresh → State 5

State 5: Source Formats
  └─ [CSV, JSON, Parquet, Delta, Avro, Excel, JDBC] → State 6

State 6: Confirmation & Generation
  └─ Generate → Done
```

**Capability Registry (Example):**
```yaml
frameworks:
  - id: ingestion
    name: "Ingestion Framework"
    capabilities:
      - id: batch
        name: "Batch Ingestion"
        specs: [batch-ingestion-spec.md]
        options:
          - id: declarative
            name: "Declarative (Lakeflow SDP)"
            specs: [declarative-ingestion-spec.md]
          - id: non-declarative
            name: "Non-Declarative (PySpark)"
            specs: [non-declarative-ingestion-spec.md]
      
      - id: streaming
        name: "Streaming Ingestion"
        specs: [streaming-readers-spec.md]
    
    load_strategies:
      - id: append
        name: "Append (insert-only)"
        specs: [append-strategy-spec.md]
      - id: scd1
        name: "SCD1 (upsert)"
        specs: [scd1-strategy-spec.md]
      - id: scd2
        name: "SCD2 (history)"
        specs: [scd2-strategy-spec.md]
      - id: full_refresh
        name: "Full Refresh"
        specs: [full-refresh-strategy-spec.md]
    
    readers:
      - id: csv
        name: "CSV"
        specs: [file-readers-spec.md]
      - id: json
        name: "JSON"
        specs: [file-readers-spec.md]
      # ... etc
```

**Code Generation Process:**
```python
# 1. Resolve specs from selections
selected_specs = resolve_specs(user_selections)

# 2. Pull dependencies
all_specs = resolve_dependencies(selected_specs)

# 3. Generate prompts for Genie Code
genie_prompt = f"""
Generate a {framework_type} framework with:
- Capabilities: {capabilities}
- Load Strategy: {load_strategy}
- Readers: {readers}

Use these specs as reference:
{all_specs}

Generate:
1. Reader implementations
2. Load strategy implementation
3. Ingestion engine
4. Config templates
5. Unit tests
"""

# 4. Call Genie Code
generated_code = genie_code.generate(genie_prompt, specs=all_specs)

# 5. Save to workspace
save_to_workspace(generated_code, output_path)
```

### Cost Estimate

**Infrastructure:** $0 (uses Databricks Assistant or Slack bot)  
**LLM Usage:**
* Menu navigation: minimal tokens (~100 tokens/question)
* Code generation: Genie Code (~5K-10K tokens/framework)
* **Total:** ~$0.30 per framework generation

### Best For

* **First-time users** — guided experience helps discovery
* **Standardized frameworks** — limited variation, clear options
* **Fast selection** — users know what they want
* **Low cost** — minimal LLM token usage

---

## Design Option 2: Natural Language (Conversational)

### Architecture

**Components:**
* **LLM Agent (LangChain)** — parses natural language intent
* **Capability Registry** — same as Option 1
* **Intent Classifier** — maps NL to capabilities
* **Slot Filler** — extracts framework, capabilities, load strategy, readers
* **Spec Resolver** — same as Option 1
* **Genie Code Integration** — same as Option 1

**User Experience:**
* User describes what they want in natural language
* Bot asks clarifying questions only when needed
* Bot confirms understanding before generation
* Bot generates framework

### Example Conversation

```
User: "I need a batch ingestion pipeline with SCD2 for CSV and JSON files"

Bot: "Got it! I'll create a batch ingestion framework with:
     - SCD2 load strategy
     - CSV and JSON readers
     
     Should this be Declarative (Lakeflow SDP) or Non-Declarative (PySpark)?"

User: "Declarative"

Bot: "Perfect! Generating your framework...
     
     ✅ Done! Your framework is ready at /pipelines/ingestion_scd2/"
```

### Pros

✅ **Natural conversation** — feels like talking to a human  
✅ **Fast for experts** — one message can specify everything  
✅ **Flexible** — can describe requirements in any order  
✅ **Better UX** — less clicking through menus

### Cons

❌ **Ambiguity** — "I need an ingestion pipeline" (batch or streaming?)  
❌ **Higher LLM costs** — more tokens for parsing intent  
❌ **Complex implementation** — NLP, intent classification, slot filling  
❌ **Error-prone** — misinterpretation possible  
❌ **Requires clarification** — may need follow-up questions

### Implementation Details

**Intent Classification:**
```python
user_input = "I need batch SCD2 for CSV and JSON"

# Parse with LLM
parsed_intent = llm.parse_intent(user_input)
# {
#   "framework": "ingestion",
#   "capabilities": ["batch"],
#   "load_strategy": "scd2",
#   "readers": ["csv", "json"],
#   "execution_mode": null  # needs clarification
# }

# Check for missing slots
missing = ["execution_mode"]

# Ask clarifying question
bot.ask("Should this be Declarative or Non-Declarative?")
```

**Slot Filling Logic:**
```python
required_slots = {
    "framework": ["ingestion", "harmonization", "dq"],
    "capabilities": ["batch", "streaming"],
    "execution_mode": ["declarative", "non-declarative"],
    "load_strategy": ["append", "scd1", "scd2", "full_refresh"],
    "readers": ["csv", "json", "parquet", "delta", ...]
}

# Extract slots from user message
slots = extract_slots(user_input, required_slots)

# Fill missing slots with clarifying questions
while not all_slots_filled(slots):
    missing_slot = next_missing_slot(slots)
    response = ask_clarifying_question(missing_slot)
    slots[missing_slot] = parse_response(response)

# Generate framework
generate_framework(slots)
```

### Cost Estimate

**Infrastructure:** $0 (uses existing LLM)  
**LLM Usage:**
* Intent parsing: ~1K tokens/message
* Clarifying questions: ~500 tokens/question
* Code generation: ~5K-10K tokens/framework
* **Total:** ~$0.80 per framework generation (2-3x Option 1)

### Best For

* **Expert users** — know exactly what they want
* **Complex requirements** — many capabilities in one request
* **Better UX** — prefer natural conversation over menus

---

## Design Option 3: Hybrid (Menu + NL)

### Architecture

**Components:**
* **Entry Point** — user chooses menu or NL mode
* **NL Parser** — if NL mode, parse intent first
* **Menu Fallback** — if ambiguous, show menu
* **Capability Registry** — shared by both modes
* **Code Generation** — shared

**User Experience:**
* **Power users:** Type full request in NL
* **New users:** Use menu for guided experience
* **Ambiguous cases:** Bot shows menu to clarify

### Example Flow

```
Bot: "What do you want to build? (You can type a description or select from menu)"

User: "I need a batch ingestion pipeline"

Bot: "Got it! A few more details:
     
     What load strategy?
     A. Append
     B. SCD1
     C. SCD2
     D. Full Refresh"

User: "C"

Bot: "What readers do you need?"
     [Menu with checkboxes: CSV, JSON, Parquet, Delta, ...]

User: [selects CSV, JSON]

Bot: "Generating your framework..."
```

### Pros

✅ **Best of both worlds** — flexible + guided  
✅ **User choice** — pick interaction style  
✅ **Graceful degradation** — NL → menu fallback  
✅ **Discovery + speed** — new users guided, experts fast

### Cons

❌ **More complex** — two interaction modes  
❌ **Inconsistent UX** — switching between modes  
❌ **Higher cost** — NL parsing adds overhead

### Cost Estimate

**LLM Usage:**
* 50% menu mode: ~$0.30/framework
* 50% NL mode: ~$0.80/framework
* **Average:** ~$0.55/framework

### Best For

* **Mixed user base** — new + expert users
* **Transitional** — start with menu, learn NL later
* **Flexibility** — accommodate different preferences

---

## Design Option 4: Pre-built Templates (No Bot)

### Architecture

**Components:**
* **Template Catalog** — pre-built framework templates
* **Parameterization** — users fill in config files
* **No Code Generation** — templates are ready-to-use

**User Experience:**
1. User browses template catalog
2. User selects template (e.g., "Batch Ingestion SCD2")
3. User copies template to their workspace
4. User edits config files (feed paths, table names, etc.)
5. User runs template

### Pros

✅ **Zero LLM cost** — no generation  
✅ **Instant** — copy template, edit config  
✅ **Tested** — templates are pre-validated  
✅ **Simple** — no bot complexity

### Cons

❌ **Not a bot** — doesn't meet conversational requirement  
❌ **Limited flexibility** — only pre-built combinations  
❌ **Maintenance burden** — maintain N templates  
❌ **No customization** — users must edit code manually

### Cost Estimate

**Infrastructure:** $0  
**LLM Usage:** $0

### Best For

* **No bot requirement** — templates meet the need
* **Standardized use cases** — limited variation
* **Lowest cost** — no LLM usage

---

## Comparison Matrix

| Criteria | Option 1: Menu | Option 2: NL | Option 3: Hybrid | Option 4: Templates |
|----------|---------------|--------------|------------------|---------------------|
| **Time to Implement** | 2-3 weeks | 4-6 weeks | 5-7 weeks | 1 week (build templates) |
| **Cost per Generation** | ~$0.30 | ~$0.80 | ~$0.55 | $0 |
| **User Experience** | Guided | Natural | Flexible | Manual |
| **Ambiguity Handling** | None (explicit) | High (needs clarification) | Medium | N/A |
| **Learning Curve** | Low (menu obvious) | Medium (learn syntax) | Low (both modes) | Low |
| **Customization** | High (generate from specs) | High | High | Low (edit templates) |
| **Discovery** | Excellent (menu shows options) | Poor (must know what to ask) | Good | Poor |
| **Speed (expert users)** | Slow (many clicks) | Fast (one message) | Fast | Fastest (no generation) |
| **Validation** | Built-in | Manual | Built-in (menu mode) | Manual |
| **Maintenance** | Low (one capability registry) | Medium (NL training) | Medium | High (N templates) |

---

## Recommendation

### Phase 1: **Option 1 (Menu-Driven)** — Start Here

**Why:**
* **Clear requirements** — no ambiguity, explicit selections
* **Guided discovery** — users learn available capabilities
* **Validation built-in** — enforce valid combinations
* **Lower cost** — minimal LLM token usage
* **Faster implementation** — simpler than NL
* **Better for PoC** — prove value before adding complexity

**Implementation Plan:**
1. Build capability registry (map capabilities → specs)
2. Design conversation state machine
3. Implement menu bot (Databricks Assistant or Slack)
4. Integrate with Genie Code for generation
5. Test with pilot users

### Phase 2: Add **Option 3 (Hybrid)** — Scale Up

**When:** After validating menu-driven bot with pilot users

**Why:**
* **Expert users** — benefit from NL shortcuts
* **Maintain menu** — new users still guided
* **Incremental** — add NL parser on top of menu

**Implementation Plan:**
1. Build NL intent parser (LangChain + LLM)
2. Map NL intents to menu selections
3. Route to menu for clarification when needed
4. Track NL vs. menu usage patterns

### Phase 3: Evaluate **Option 4 (Templates)** — Fallback

**When:** If bot complexity outweighs benefits

**Why:**
* **Simpler alternative** — if bot adoption is low
* **Faster for common cases** — pre-built templates
* **Lower cost** — no LLM usage

---

## Key Design Decisions

### Decision 1: How to Store Capability Registry?

**Options:**
A. **YAML file** in `/specs/agentic/capability-registry.yaml`  
B. **Delta table** in Unity Catalog  
C. **Python dict** in bot code

**Recommendation:** A (YAML file)
* **Pros:** Version controlled, human-readable, easy to edit
* **Cons:** Requires parsing on bot startup

### Decision 2: How to Generate Code?

**Options:**
A. **Genie Code** — feed specs to Genie, generate from scratch  
B. **Templates** — pre-built code, fill in placeholders  
C. **Hybrid** — Templates + Genie for customization

**Recommendation:** A (Genie Code)
* **Pros:** Leverages specs as portable IP, flexible, minimal maintenance
* **Cons:** Generation time (~30-60 seconds per framework)

### Decision 3: Where to Deploy Bot?

**Options:**
A. **Databricks Assistant** — native chat interface  
B. **Slack Bot** — external integration  
C. **Web UI** — custom React app  
D. **Notebook Widget** — interactive widget in notebook

**Recommendation:** A (Databricks Assistant) for Phase 1
* **Pros:** Native, authenticated, UC-integrated, no hosting
* **Cons:** Workspace-only (no external access)

### Decision 4: How to Handle Invalid Combinations?

**Example:** User selects "Streaming + Full Refresh" (invalid)

**Options:**
A. **Block selection** — disable invalid options dynamically  
B. **Warn + allow** — show warning but let user proceed  
C. **Reject + explain** — reject and explain why

**Recommendation:** A (Block selection)
* **Pros:** Prevents errors, guides users to valid combinations
* **Cons:** More complex UI logic

### Decision 5: How to Handle Dependencies?

**Example:** User selects SCD2 → auto-pull scd2-strategy-spec.md + engine-contracts-spec.md

**Options:**
A. **Auto-resolve** — bot pulls all dependencies automatically  
B. **Confirm** — bot shows dependencies, asks user to confirm  
C. **Manual** — user must select dependencies

**Recommendation:** A (Auto-resolve)
* **Pros:** Simpler UX, users don't need to understand dependencies
* **Cons:** Larger generated code (may include unused specs)

---

## Next Steps

1. **Review design options** with team
2. **Choose Option 1 (Menu-Driven)** for MVP
3. **Build capability registry** (capability-registry-spec.md → YAML)
4. **Design conversation flow** (state machine)
5. **Implement menu bot** (Databricks Assistant integration)
6. **Integrate Genie Code** (spec → code generation)
7. **Test with pilot** (build 3-5 frameworks)
8. **Measure success:**
   - Generation success rate (>90%)
   - Generation time (<2 minutes)
   - User satisfaction
9. **Decide on Phase 2:**
   - Add NL mode (Option 3)
   - Or stay with menu

---

## Open Questions

1. **Q:** Should generated code be saved to Git Repos or Workspace Files?  
   **Impact:** Git = version controlled; Workspace = simpler

2. **Q:** Should bot create Databricks Jobs/Pipelines, or just generate code?  
   **Impact:** Full automation vs. user control

3. **Q:** Should bot support editing existing frameworks, or only create new?  
   **Impact:** More complex if editing is needed

4. **Q:** How to handle custom modifications after generation?  
   **Impact:** Regeneration overwrites changes (need merge strategy)

5. **Q:** Should bot validate source paths/tables before generation?  
   **Impact:** Better UX but adds latency

---

**END OF DESIGN OPTIONS DOCUMENT**
