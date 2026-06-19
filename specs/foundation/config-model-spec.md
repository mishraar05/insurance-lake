# FND-001 - Metadata / Config Model Specification

Status: active · 2026-06-18 · Skill: `framework-dev.build-config-model`
Schema: `insurelake_config.config` (Unity Catalog). All tables are Delta, audited, and linked to the existing ABC framework (they do not duplicate ABC).

## Purpose
Define the configuration entities that drive the metadata-driven framework. The ingestion and harmonization engines and all cross-cutting services read only from these tables; behaviour is config, not code.

## Entities (8)
Implemented in the SDK today: **source, target, load, transform, dq_rule**. Planned (FND-001 design, not yet built): **recon_rule, masking_rule, dependency**.

### source  (cfg_source)
Describes a feed's origin. PK `source_id`.
Fields: source_id, source_name, source_type (FILE|TABLE|STREAM|API|CDC), source_system (PolicyCenter, ClaimCenter, ...), connection_string, file_format (CSV|JSON|PARQUET|AVRO|XML|DELTA|FIXEDWIDTH), schema_location, credential_scope, credential_key, business_domain (POLICY|CLAIM|BILLING|PARTY|PAYMENT|LOSS), pii_flag, data_classification (PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED), sla_hours, active_flag, + audit (created_by/ts, updated_by/ts).

### target  (cfg_target)
Describes a destination table. PK `target_id`.
Fields: target_id, target_name, catalog_name, schema_name, table_name, layer (BRONZE|SILVER|GOLD), table_type (MANAGED|EXTERNAL), format (DELTA), partition_columns[], liquid_clustering_columns[], primary_key[], acord_entity (Party|Policy|Coverage|Claim|Payment|Loss), retention_days, enable_cdf, active_flag, + audit.

### load  (cfg_load)
Source -> bronze loading rule. PK `load_id`; FK source_id -> cfg_source, target_id -> cfg_target.
Fields: load_id, load_name, source_id, target_id, load_type (BATCH_FULL|BATCH_INCREMENTAL|STREAM_APPEND|STREAM_CDC|STREAM_UPSERT), load_pattern (APPEND|OVERWRITE|MERGE|SCD2|CDC), engine (DECLARATIVE|AUTOLOADER|COPY_INTO|STRUCTURED_STREAMING), watermark_column, watermark_type (TIMESTAMP|SEQUENCE|FILENAME), checkpoint_location, trigger_interval, merge_keys, autoloader_options{}, schedule_cron, depends_on, active_flag, + audit.

### transform  (cfg_transform)
Bronze->silver->gold transformation rule. PK `transform_id`; FK source_target_id / destination_target_id -> cfg_target.
Fields: transform_id, transform_name, source_target_id, destination_target_id, transform_type (SQL|PYTHON|ACORD_MAPPING|LOOKUP|AGGREGATION|PIVOT), transform_sql, transform_python, acord_mapping_template, scd_type (SCD1|SCD2), scd_key_columns, scd_timestamp_column, engine (DECLARATIVE|STRUCTURED_STREAMING|BATCH), dependencies, active_flag, + audit.

### dq_rule  (cfg_dq_rule)
Data-quality rule bound to a target. PK `dq_rule_id`; FK target_id -> cfg_target.
Fields: dq_rule_id, rule_name, target_id, rule_type (NOT_NULL|UNIQUE|RANGE|REGEX|CUSTOM_SQL|REFERENTIAL_INTEGRITY|FRESHNESS), column_name, rule_expression, threshold_percent (0-1), on_failure (WARN|FAIL|QUARANTINE), active_flag, + audit.

### recon_rule  (cfg_recon_rule) - PLANNED
Reconciliation check. PK `recon_rule_id`.
Fields: recon_rule_id, rule_name, load_id, target_id, recon_type (ROW_COUNT|CONTROL_TOTAL|CROSS_LAYER|SOURCE_OF_RECORD), source_ref, target_ref, measure_column (for control totals), tolerance_percent, on_break (WARN|FAIL), active_flag, + audit.

### masking_rule  (cfg_masking_rule) - PLANNED
PII handling. PK `masking_rule_id`; FK target_id.
Fields: masking_rule_id, rule_name, target_id, column_name, classification (CONFIDENTIAL|RESTRICTED), technique (UC_COLUMN_MASK|ROW_FILTER|TOKENIZE|HASH), mask_function, reversible_flag, active_flag, + audit.

### dependency  (cfg_dependency) - PLANNED
Normalized DAG edges. PK `dependency_id`.
Fields: dependency_id, object_type (LOAD|TRANSFORM), object_id, depends_on_id, dependency_type, active_flag, + audit.

## Key validation rules (enforced by the loader)
- FILE sources require file_format and connection_string.
- PII sources (pii_flag) require CONFIDENTIAL or RESTRICTED classification.
- partition_columns and liquid_clustering_columns are mutually exclusive.
- STREAM loads require checkpoint_location.
- DECLARATIVE engine requires APPEND or SCD2 pattern.
- MERGE / SCD2 / CDC patterns require merge_keys.
- transform source_target_id != destination_target_id (no self-transform).
- SCD2 + DECLARATIVE requires key columns and a timestamp.
- dq threshold_percent in [0,1]; on_failure in {WARN, FAIL, QUARANTINE}.
- non-CUSTOM_SQL dq rules require column_name.
- All FKs validated on load (ForeignKeyError); dependency graphs checked for cycles (CircularDependencyError).

## Versioning & change audit (FND-005)
Every insert/update/delete to a config table writes a change record (who, when, before/after) to ABC. Config is versioned so a run can be reproduced against the config as-of a point in time.
