# InsureLake SDK

**Version**: 0.1.0  
**Task**: FND-003  
**Status**: Initial Implementation

## Overview

The InsureLake SDK provides typed configuration loading and validation for the InsureLake P&C framework. It reads metadata from Unity Catalog Delta tables and provides a clean Python interface for framework components.

## Features

✅ **Typed Config Objects** - Dataclasses for all 8 config entities  
✅ **Foreign Key Validation** - Automatic validation of references between entities  
✅ **Helpful Error Messages** - Clear, actionable errors with available alternatives  
✅ **Unity Catalog Integration** - Direct loading from Delta tables  
✅ **Workflow Graph Building** - Understand dependencies and execution order  

## Installation

The SDK is deployed as workspace Python modules (no wheel packaging). To use:

```python
import sys
sys.path.append("/Workspace/Users/<your-email>/insurance-lake")

from sdk import ConfigLoader
```

## Quick Start

### 1. Load Configuration

```python
from sdk import ConfigLoader

# Initialize loader
loader = ConfigLoader(catalog="insurelake_config", schema="config")

# Load a load configuration
load_config = loader.get_load("load_policy_batch")
print(f"Load: {load_config.load_name}")
print(f"Type: {load_config.load_type}")
print(f"Engine: {load_config.engine}")

# Load related source and target
source = loader.get_source(load_config.source_id)
target = loader.get_target(load_config.target_id)

print(f"Source: {source.source_name} ({source.source_type})")
print(f"Target: {target.fully_qualified_name} ({target.layer})")
```

### 2. List and Filter

```python
# List all BRONZE targets
bronze_targets = loader.list_targets(layer="BRONZE", active_only=True)

# List all POLICY domain sources
policy_sources = loader.list_sources(business_domain="POLICY")

# Get all DQ rules for a target
dq_rules = loader.get_dq_rules_by_target("tgt_bronze_policy")
for rule in dq_rules:
    print(f"Rule: {rule.rule_name} - {rule.rule_type} on {rule.column_name}")
```

### 3. Build Workflow Graph

```python
# Get complete workflow for a load
workflow = loader.get_workflow_graph(load_id="load_policy_batch")

print(f"Loads: {len(workflow['loads'])}")
print(f"Sources: {len(workflow['sources'])}")
print(f"Targets: {len(workflow['targets'])}")
```

### 4. Find Transforms

```python
# Find all transforms writing TO a target (downstream)
downstream_transforms = loader.get_transforms_by_target("tgt_silver_policy", upstream=False)

# Find all transforms reading FROM a target (upstream)
upstream_transforms = loader.get_transforms_by_target("tgt_silver_policy", upstream=True)
```

## Configuration Models

### SourceConfig
External data source (file, table, stream, API, CDC)

**Key Fields**: `source_id`, `source_type`, `source_system`, `connection_string`, `file_format`, `business_domain`, `pii_flag`

### TargetConfig
Unity Catalog destination table

**Key Fields**: `target_id`, `catalog_name`, `schema_name`, `table_name`, `layer`, `partition_columns`, `acord_entity`

### LoadConfig
Data load operation from source to target

**Key Fields**: `load_id`, `source_id`, `target_id`, `load_type`, `load_pattern`, `engine`, `checkpoint_location`

### TransformConfig
Data transformation between targets

**Key Fields**: `transform_id`, `source_target_id`, `destination_target_id`, `transform_type`, `transform_sql`, `scd_type`

### DQRuleConfig
Data quality rule

**Key Fields**: `dq_rule_id`, `target_id`, `rule_type`, `column_name`, `threshold_percent`, `on_failure`

## Error Handling

The SDK provides helpful, actionable errors:

### ConfigNotFoundError
```python
try:
    load = loader.get_load("nonexistent_load")
except ConfigNotFoundError as e:
    print(e)
    # Output: LOAD 'nonexistent_load' not found in config.load. 
    #         Available LOADs: ['load_policy_batch', 'load_claim_stream', ...]
```

### ForeignKeyError
```python
# If a load references a non-existent source
# ForeignKeyError: Load 'load_policy_batch': Foreign key violation: 
#   source_id='bad_source' references non-existent Source. 
#   Check config.source table.
```

### ConfigValidationError
```python
# If a config violates validation rules
# ConfigValidationError: Validation failed for Load 'load_policy_batch':
#   - load_type 'STREAM_APPEND' requires checkpoint_location
```

## Validation Rules

All config models have built-in validation:

**Source**:
* FILE sources require `file_format` and `connection_string`
* PII sources require `data_classification` = CONFIDENTIAL or RESTRICTED

**Target**:
* `partition_columns` and `liquid_clustering_columns` are mutually exclusive
* SILVER ACORD mappings require valid ACORD entity

**Load**:
* STREAM_* loads require `checkpoint_location`
* DECLARATIVE engine requires APPEND or SCD2 pattern
* MERGE/SCD2/CDC patterns require `merge_keys`

**Transform**:
* `source_target_id` ≠ `destination_target_id`
* SCD2 with DECLARATIVE requires `scd_key_columns` and `scd_timestamp_column`

**DQ Rule**:
* Non-CUSTOM_SQL rules require `column_name`
* `threshold_percent` must be 0-1
* `on_failure` must be WARN, FAIL, or QUARANTINE

## Integration with ABC SDK

The Config Loader is designed to work alongside the ABC SDK (FND-011):

```python
from sdk import ConfigLoader, ABCInstrumentor

# Load config
loader = ConfigLoader()
load_config = loader.get_load("load_policy_batch")

# Instrument with ABC
abc = ABCInstrumentor(catalog="insurelake_config", schema="abc")
master_run_id = abc.start_master(
    workflow_run_id=workflow_id,
    master_name=load_config.load_name,
    master_type="LOAD"
)

# ... execute load ...

abc.end_master(master_run_id, status="SUCCESS", output_row_count=5432)
```

## Testing

Unit tests are located in `/tests/test_config_loader.py`. To run:

```python
%run /Workspace/Users/<your-email>/insurance-lake/tests/test_config_loader
```

## Next Steps

* **FND-004**: Seed example P&C configs (policy feed + harmonization)
* **FND-005**: Add config versioning and history support
* **FND-010/011**: Implement ABC SDK to work alongside Config Loader
* Add remaining models: ReconRule, MaskingRule, Dependency

## References

* FND-001: Metadata/Config Model Specification
* FND-002: Control Tables DDL Specification
* Unity Catalog: https://docs.databricks.com/unity-catalog/
