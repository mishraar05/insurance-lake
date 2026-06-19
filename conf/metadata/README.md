# Feed Metadata (conf/metadata)

Source-controlled **feed definitions** (JSON) that get loaded into the Unity Catalog control tables
(`insurelake_config.config.*`) by the config loader. One JSON file per feed; each bundles the
`source`, `target(s)`, `load`, `transform(s)` and `dq_rules` for that feed.

- DDL for the control tables: `../ddl/control_tables.sql`
- Entity field definitions: `../../specs/foundation/config-model-spec.md`
- Examples: `./examples/`
