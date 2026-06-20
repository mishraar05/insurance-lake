# Glossary (shared)

- **ABC** - Audit, Balance, Control metadata framework (existing, Delta-table driven).
- **Medallion** - Bronze (raw) -> Silver (conformed/ACORD canonical) -> Gold (marts).
- **Declarative** - Lakeflow Declarative Pipelines (DLT). **Non-declarative** - classic batch PySpark + MERGE.
- **Genie Code** - Databricks agentic data-engineering surface that generates pipelines/SQL/Python from intent.
- **Skill** - a versioned, single-job capability. Families: framework-dev (build the framework) and authoring (use the framework).
