# InsureLake Spec Registry

**Generated:** 2026-06-20 17:29:04  
**Purpose:** Comprehensive inventory of all component specifications with metadata, dependencies, and status tracking

---

## 📊 Summary Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Spec Files** | 52 | 100.0% |
| **✅ With Valid YAML Front-matter** | 22 | 42.3% |
| **❌ Missing Front-matter (Phase 1 Pending)** | 30 | 57.7% |
| **Capabilities Provided** | 38 | — |
| **Dependencies Declared** | 2 | — |

---

## 📂 Specs by Domain

### AGENTIC

| Spec ID | Title | Status | Target Path | Provides | Depends On |
|---------|-------|--------|-------------|----------|------------|
| `agentic.capability-registry` | Capability Registry & Resolver | active | `src/agents/registry/` | Capability, load_registry, menu (+2 more) | None |
| `ops-qa-chatbot-spec` | N/A | draft | `N/A` |  | None |

### CORE

| Spec ID | Title | Status | Target Path | Provides | Depends On |
|---------|-------|--------|-------------|----------|------------|
| `core.contracts.engine-contracts` | Engine Contracts Spec | draft | `src/core/contracts/` |  | None |
| `core.metadata.metadata-models` | Metadata Models Spec | draft | `src/core/metadata/` |  | None |

### DATAIO

| Spec ID | Title | Status | Target Path | Provides | Depends On |
|---------|-------|--------|-------------|----------|------------|
| `dataio.load_strategy.append-strategy` | Append Strategy Spec | draft | `src/load_strategy/` |  | None |
| `dataio.load_strategy.full-refresh-strategy` | Full Refresh Strategy Spec | draft | `src/load_strategy/` |  | None |
| `dataio.load_strategy.scd1-strategy` | SCD1 Strategy Spec | draft | `src/load_strategy/` |  | None |
| `dataio.load_strategy.scd2-strategy` | SCD2 Strategy Spec | draft | `src/load_strategy/` |  | None |
| `dataio.readers.excel-readers` | Excel Readers Spec | draft | `src/readers/` |  | None |
| `dataio.readers.file-readers` | File Readers Spec | draft | `src/readers/` |  | None |
| `dataio.readers.jdbc-readers` | JDBC Readers Spec | draft | `src/readers/` |  | None |
| `dataio.readers.odbc-readers` | ODBC Readers Spec | draft | `src/readers/` |  | None |
| `dataio.readers.sap-readers` | SAP Readers Spec | draft | `src/readers/` |  | None |
| `dataio.readers.streaming-readers` | Streaming Readers Spec | draft | `src/readers/` |  | None |

### FOUNDATION

| Spec ID | Title | Status | Target Path | Provides | Depends On |
|---------|-------|--------|-------------|----------|------------|
| `foundation.abc-sdk` | ABC SDK (Audit, Balance, Control) | active | `src/core/sdk/` | ABC, RunHandle, start_run (+6 more) | None |
| `foundation.codegen` | Schema Codegen (metadata -> DDL + JSON-schema) | active | `scripts/codegen/` | sql_type, model_to_ddl, model_to_jsonschema (+2 more) | foundation.config-model |
| `foundation.config-model` | Metadata / Config Model | active | `src/core/metadata/` | SourceConfig, TargetConfig, LoadConfig (+3 more) | abc-sdk-spec |
| `foundation.contracts` | Core Contracts (Typed Interfaces) | active | `src/core/contracts/` | Reader, LoadStrategy, Engine (+5 more) | foundation.config-model |
| `foundation.control-tables-ddl` | FND-002 - Control Tables DDL Specification | draft | `src/core/` |  | None |
| `foundation.project-structure` | FND-030 - Project Structure Specification (DAB Scaffold) | draft | `src/core/` |  | None |
| `foundation.spec-validator` | Spec Validator (validate any spec after authoring) | active | `scripts/speccheck/` | Finding, parse_front_matter, check_spec (+3 more) | None |

### SCRIPTS

| Spec ID | Title | Status | Target Path | Provides | Depends On |
|---------|-------|--------|-------------|----------|------------|
| `scripts.codegen.metadata-to-ddl` | Metadata-to-DDL Codegen Spec | draft | `scripts/codegen/` |  | None |

---

## ❌ Specs Pending Phase 1 Conversion (30 files)

These specs exist but lack valid YAML front-matter and SOLID principles documentation.

### AGENTIC (5 pending)

* `agentic/code-generation-spec.md` — No front-matter
* `agentic/data-profiling-spec.md` — No front-matter
* `agentic/mapping-generation-spec.md` — No front-matter
* `agentic/metadata-population-spec.md` — No front-matter
* `agentic/synthetic-data-spec.md` — No front-matter

### DATAIO (1 pending)

* `dataio/readers/api-readers-spec.md` — No front-matter

### FINOPS (3 pending)

* `finops/cost-estimation-spec.md` — No front-matter
* `finops/cost-tracking-spec.md` — No front-matter
* `finops/finops-dashboard-spec.md` — No front-matter

### HARMONIZATION (4 pending)

* `harmonization/acord-mapping-spec.md` — No front-matter
* `harmonization/harmonization-engine-spec.md` — No front-matter
* `harmonization/silver-gold-spec.md` — No front-matter
* `harmonization/transformation-patterns-spec.md` — No front-matter

### INGESTION (4 pending)

* `ingestion/autoloader-patterns-spec.md` — No front-matter
* `ingestion/ingestion-engine-spec.md` — No front-matter
* `ingestion/scd-patterns-spec.md` — No front-matter
* `ingestion/streaming-patterns-spec.md` — No front-matter

### MASKING (3 pending)

* `masking/masking-engine-spec.md` — No front-matter
* `masking/masking-techniques-spec.md` — No front-matter
* `masking/pii-classification-spec.md` — No front-matter

### OBSERVABILITY (3 pending)

* `observability/logging-spec.md` — No front-matter
* `observability/monitoring-spec.md` — No front-matter
* `observability/observability-spec.md` — No front-matter

### ORCHESTRATION (3 pending)

* `orchestration/cicd-spec.md` — No front-matter
* `orchestration/pipeline-dependencies-spec.md` — No front-matter
* `orchestration/workflow-orchestration-spec.md` — No front-matter

### QUALITY (4 pending)

* `quality/dq-engine-spec.md` — No front-matter
* `quality/dq-rules-catalog-spec.md` — No front-matter
* `quality/recon-patterns-spec.md` — No front-matter
* `quality/reconciliation-engine-spec.md` — No front-matter

---

## 🔍 Capability Index

Find which spec provides a specific capability (function, class, or feature).

| Capability | Provided By Spec(s) |
|------------|---------------------|
| `ABC` | `foundation.abc-sdk` |
| `Capability` | `agentic.capability-registry` |
| `Check` | `foundation.contracts` |
| `CheckResult` | `foundation.contracts` |
| `ConfigLoader` | `foundation.config-model` |
| `DQRuleConfig` | `foundation.config-model` |
| `Engine` | `foundation.contracts` |
| `Finding` | `foundation.spec-validator` |
| `LoadConfig` | `foundation.config-model` |
| `LoadStrategy` | `foundation.contracts` |
| `Masker` | `foundation.contracts` |
| `Reader` | `foundation.contracts` |
| `RunContext` | `foundation.contracts` |
| `RunHandle` | `foundation.abc-sdk` |
| `RunResult` | `foundation.contracts` |
| `SourceConfig` | `foundation.config-model` |
| `TargetConfig` | `foundation.config-model` |
| `TransformConfig` | `foundation.config-model` |
| `build_plan` | `agentic.capability-registry` |
| `check_corpus` | `foundation.spec-validator` |
| `check_spec` | `foundation.spec-validator` |
| `end_run` | `foundation.abc-sdk` |
| `generate` | `foundation.codegen` |
| `load_registry` | `agentic.capability-registry` |
| `log_audit` | `foundation.abc-sdk` |
| `log_balance` | `foundation.abc-sdk` |
| `log_cost` | `foundation.abc-sdk` |
| `log_dq` | `foundation.abc-sdk` |
| `log_exception` | `foundation.abc-sdk` |
| `main` | `foundation.codegen`, `foundation.spec-validator` |
| `menu` | `agentic.capability-registry` |
| `model_to_ddl` | `foundation.codegen` |
| `model_to_jsonschema` | `foundation.codegen` |
| `parse_front_matter` | `foundation.spec-validator` |
| `resolve_selection` | `agentic.capability-registry` |
| `sql_type` | `foundation.codegen` |
| `start_run` | `foundation.abc-sdk` |
| `validate` | `foundation.spec-validator` |


---

## 🔗 Dependency Analysis

**Total unique capabilities provided:** 38  
**Total unique dependencies declared:** 2  
**Missing dependencies:** 2

### ⚠️ Missing Dependencies

These capabilities are required but not yet provided by any spec:

* `abc-sdk-spec`
* `foundation.config-model`

### Specs with Dependencies

| Spec | Depends On |
|------|------------|
| `foundation.config-model` | `abc-sdk-spec` |
| `foundation.codegen` | `foundation.config-model` |
| `foundation.contracts` | `foundation.config-model` |


---

## 📖 How to Use This Registry

### Finding a Spec by Capability

1. **Search the Capability Index** to find which spec provides a specific function, class, or feature
2. Look up that spec in the **Specs by Domain** section for full details

**Example:**
```
Need: ConfigLoader class
→ Capability Index shows: provided by foundation.config-model
→ Check foundation.config-model-spec.md
```

### Understanding Dependencies

Before generating code from a spec:

1. Check the **Depends On** column in the domain tables
2. Ensure all dependency specs are generated first
3. Review the **Missing Dependencies** section for gaps

### Tracking Phase 1 Progress

* ✅ **42.3% complete** — 22 specs have valid YAML front-matter and SOLID documentation
* ❌ **57.7% pending** — 30 specs need front-matter conversion (see "Specs Pending Phase 1 Conversion")

### Regenerating This Registry

This registry is auto-generated. To refresh:

```python
# Run the spec registry generator
%run /Workspace/Users/cleancoding109@gmail.com/insurance-lake/scripts/generate_spec_registry.py
```

---

## 🔧 Maintenance

* **Generated by:** Genie Code spec registry builder
* **Update frequency:** On-demand or after batch spec updates
* **Source:** All `*-spec.md` files in `/specs` directory
* **Template:** Front-matter must follow `/specs/_templates/component-spec.md` format

---

## 📞 Questions?

See:
* **[specs/README.md](README.md)** — Spec authoring workflow
* **[PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md)** — Project principles
* **[skills/insurelake-spec-codegen](../skills/insurelake-spec-codegen/)** — Code generation from specs

---

**END OF REGISTRY**
