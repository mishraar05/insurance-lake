# Metadata-to-DDL Codegen Spec

---

## Front Matter

```yaml
id: metadata-to-ddl-spec
version: 1.0
status: approved
approved_date: 2026-06-18
tier: scripts
component: codegen
backlog_ids:
  - FND-005    # Code generation tooling
  - CODEGEN-001 # Metadata DDL generation
dependencies:
  - metadata-models-spec
runtime: Python 3.10+
purpose: Generate Delta table DDL and JSON schemas from Pydantic metadata models, ensuring ABC metadata tables match Python models (single source of truth)
inputs:
  - core/metadata/models.py (Pydantic models)
  - core/domain/acord_models.py (ACORD entities)
outputs:
  - SQL DDL files for ABC metadata tables
  - JSON schema files for validation
  - Validation report comparing DB schemas to Python models
tools_required:
  - Python inspect module
  - Pydantic model introspection
  - JSON Schema generation (pydantic.json_schema)
```

---

## 1. Purpose

Generate **Delta table DDL** and **JSON schemas** from Pydantic metadata models, ensuring the ABC metadata tables always match the Python dataclass definitions. This establishes **single source of truth (SSOT)** for metadata schemas.

**Workflow:**
1. **Introspect Pydantic models** — read Feed, Pipeline, DQCheck, MaskRule, ReconRule, TransformRule from `core/metadata/models.py`
2. **Generate Delta DDL** — CREATE TABLE statements for ABC metadata tables
3. **Generate JSON schemas** — for config file validation
4. **Validate existing tables** — compare DB schemas to Python models, report mismatches

**Benefits:**
* **No schema drift** — Python models and DB tables are always in sync
* **Automation** — DDL regenerates on model changes
* **Documentation** — JSON schemas document config file structure
* **CI/CD integration** — run as pre-deployment check

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* ABC metadata tables live in Unity Catalog
* Delta format with Liquid Clustering on primary keys
* Supports both ACORD entities and framework metadata

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — ABC framework (audit, balance, control), Unity Catalog
* **ROADMAP.md Phase 0** — codegen is Wave 0 foundation
* **metadata-models-spec.md** — Pydantic models to introspect
* **Backlog tasks:** FND-005, CODEGEN-001

### 2.2 Design Constraints
* **Python → SQL type mapping** — convert Pydantic types to Delta types (str → STRING, int → BIGINT, float → DOUBLE, date → DATE, list → ARRAY)
* **Enum → STRING** — all enums stored as STRING with CHECK constraints
* **Optional → NULL** — `Optional[T]` fields are NULLABLE
* **Unity Catalog syntax** — DDL must be UC-compatible (no Hive syntax)
* **Idempotent** — DDL uses `CREATE TABLE IF NOT EXISTS`, safe to re-run

---

## 3. Procedure

### 3.1 Pydantic Type → Delta Type Mapping

**Mapping rules:**
```python
from typing import get_origin, get_args, Union
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel

def pydantic_to_delta_type(field_type) -> str:
    """
    Convert Pydantic field type to Delta SQL type.
    
    Args:
        field_type: Python type annotation
        
    Returns:
        Delta SQL type string
    """
    # Handle Optional[T] → extract T
    origin = get_origin(field_type)
    if origin is Union:
        args = get_args(field_type)
        # Filter out None type
        non_none_types = [arg for arg in args if arg is not type(None)]
        if len(non_none_types) == 1:
            field_type = non_none_types[0]
            origin = get_origin(field_type)
    
    # Primitive types
    if field_type is str:
        return "STRING"
    elif field_type is int:
        return "BIGINT"
    elif field_type is float:
        return "DOUBLE"
    elif field_type is bool:
        return "BOOLEAN"
    elif field_type is date:
        return "DATE"
    elif field_type is datetime:
        return "TIMESTAMP"
    
    # Container types
    elif origin is list:
        args = get_args(field_type)
        element_type = pydantic_to_delta_type(args[0]) if args else "STRING"
        return f"ARRAY<{element_type}>"
    elif origin is dict:
        # Dict[str, str] → MAP<STRING, STRING>
        args = get_args(field_type)
        key_type = pydantic_to_delta_type(args[0]) if len(args) > 0 else "STRING"
        value_type = pydantic_to_delta_type(args[1]) if len(args) > 1 else "STRING"
        return f"MAP<{key_type}, {value_type}>"
    
    # Enum types
    elif isinstance(field_type, type) and issubclass(field_type, Enum):
        return "STRING"  # Enums stored as strings
    
    else:
        raise ValueError(f"Unsupported type: {field_type}")
```

### 3.2 DDL Generation Algorithm

**For each Pydantic model:**
```python
from pydantic import BaseModel
from typing import get_type_hints

def generate_ddl(model_class: type[BaseModel], table_fqn: str, primary_key: str) -> str:
    """
    Generate CREATE TABLE DDL for a Pydantic model.
    
    Args:
        model_class: Pydantic model class (e.g., Feed)
        table_fqn: Fully qualified table name (e.g., "main.abc.feed_metadata")
        primary_key: Primary key column name
        
    Returns:
        SQL CREATE TABLE statement
    """
    # Get field definitions
    fields = model_class.model_fields
    type_hints = get_type_hints(model_class)
    
    columns = []
    
    for field_name, field_info in fields.items():
        # Get field type
        field_type = type_hints[field_name]
        
        # Map to Delta type
        sql_type = pydantic_to_delta_type(field_type)
        
        # Determine nullability
        nullable = not field_info.is_required()
        null_constraint = "" if nullable else "NOT NULL"
        
        # Get docstring as comment
        description = field_info.description or ""
        comment = f"COMMENT '{description}'" if description else ""
        
        columns.append(f"  {field_name} {sql_type} {null_constraint} {comment}".strip())
    
    # Build DDL
    columns_ddl = ",\n".join(columns)
    
    ddl = f"""
CREATE TABLE IF NOT EXISTS {table_fqn} (
{columns_ddl},
  CONSTRAINT {table_fqn.split('.')[-1]}_pk PRIMARY KEY ({primary_key})
)
USING DELTA
CLUSTER BY ({primary_key})
COMMENT 'ABC metadata table for {model_class.__name__}';
""".strip()
    
    return ddl
```

### 3.3 Metadata Tables to Generate

**ABC Metadata Tables:**
1. **`{catalog}.abc.feed_metadata`** — stores Feed configs
2. **`{catalog}.abc.pipeline_metadata`** — stores Pipeline configs
3. **`{catalog}.abc.transform_metadata`** — stores TransformRule configs
4. **`{catalog}.abc.dq_check_metadata`** — stores DQCheck configs
5. **`{catalog}.abc.mask_rule_metadata`** — stores MaskRule configs
6. **`{catalog}.abc.recon_rule_metadata`** — stores ReconRule configs

**ABC Control Tables (from abc-sdk-spec):**
7. **`{catalog}.abc.audit_log`** — audit events
8. **`{catalog}.abc.balance_log`** — reconciliation results
9. **`{catalog}.abc.cost_log`** — cost tracking

**ACORD Tables (from ACORD_CANONICAL_SCHEMA.md):**
10. **`{catalog}.silver.party`** — ACORD Party entity
11. **`{catalog}.silver.policy`** — ACORD Policy entity
12. **`{catalog}.silver.coverage`** — ACORD Coverage entity
13. **`{catalog}.silver.claim`** — ACORD Claim entity
14. **`{catalog}.silver.payment`** — ACORD Payment entity
15. **`{catalog}.silver.loss`** — ACORD Loss entity

### 3.4 JSON Schema Generation

**Use Pydantic's built-in JSON schema generation:**
```python
import json
from pydantic import BaseModel

def generate_json_schema(model_class: type[BaseModel], output_path: str):
    """
    Generate JSON schema for a Pydantic model.
    
    Args:
        model_class: Pydantic model class
        output_path: Output file path (e.g., "schemas/feed_schema.json")
    """
    # Generate schema
    schema = model_class.model_json_schema()
    
    # Write to file
    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"Generated JSON schema: {output_path}")
```

### 3.5 Schema Validation (Compare DB to Python)

**Validate existing tables match Python models:**
```python
from pyspark.sql import SparkSession
from typing import get_type_hints

def validate_table_schema(spark: SparkSession, table_fqn: str, model_class: type[BaseModel]) -> list[str]:
    """
    Compare DB table schema to Pydantic model.
    
    Args:
        spark: Active SparkSession
        table_fqn: Fully qualified table name
        model_class: Pydantic model class
        
    Returns:
        List of validation error messages (empty = schemas match)
    """
    errors = []
    
    # Get DB schema
    try:
        db_schema = spark.table(table_fqn).schema
    except Exception as e:
        errors.append(f"Table {table_fqn} not found: {e}")
        return errors
    
    # Get Python model fields
    model_fields = model_class.model_fields
    type_hints = get_type_hints(model_class)
    
    # Compare field names
    db_columns = {field.name for field in db_schema.fields}
    model_columns = set(model_fields.keys())
    
    missing_in_db = model_columns - db_columns
    extra_in_db = db_columns - model_columns
    
    if missing_in_db:
        errors.append(f"Columns missing in DB: {missing_in_db}")
    if extra_in_db:
        errors.append(f"Extra columns in DB: {extra_in_db}")
    
    # Compare types for matching columns
    for field in db_schema.fields:
        if field.name in model_fields:
            model_type = type_hints[field.name]
            expected_sql_type = pydantic_to_delta_type(model_type)
            actual_sql_type = field.dataType.simpleString().upper()
            
            if expected_sql_type != actual_sql_type:
                errors.append(f"Type mismatch for {field.name}: DB has {actual_sql_type}, model expects {expected_sql_type}")
    
    return errors
```

### 3.6 Main Codegen Script

**Entry point:**
```python
# scripts/codegen/generate_metadata_ddl.py
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from typing import get_type_hints

from core.metadata import Feed, Pipeline, TransformRule, DQCheck, MaskRule, ReconRule
from core.domain.acord_models import Party, Policy, Coverage, Claim, Payment, Loss

def main(catalog: str = "main", output_dir: str = "generated"):
    """
    Generate DDL and JSON schemas for all metadata models.
    
    Args:
        catalog: Unity Catalog name
        output_dir: Output directory for DDL and JSON schemas
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define models and their table mappings
    metadata_models = [
        (Feed, f"{catalog}.abc.feed_metadata", "feed_id"),
        (Pipeline, f"{catalog}.abc.pipeline_metadata", "pipeline_id"),
        (TransformRule, f"{catalog}.abc.transform_metadata", "transform_id"),
        (DQCheck, f"{catalog}.abc.dq_check_metadata", "check_id"),
        (MaskRule, f"{catalog}.abc.mask_rule_metadata", "mask_id"),
        (ReconRule, f"{catalog}.abc.recon_rule_metadata", "recon_id"),
    ]
    
    acord_models = [
        (Party, f"{catalog}.silver.party", "party_id"),
        (Policy, f"{catalog}.silver.policy", "policy_id"),
        (Coverage, f"{catalog}.silver.coverage", "coverage_id"),
        (Claim, f"{catalog}.silver.claim", "claim_id"),
        (Payment, f"{catalog}.silver.payment", "payment_id"),
        (Loss, f"{catalog}.silver.loss", "loss_id"),
    ]
    
    all_models = metadata_models + acord_models
    
    # Generate DDL files
    for model_class, table_fqn, primary_key in all_models:
        ddl = generate_ddl(model_class, table_fqn, primary_key)
        
        # Write DDL to file
        table_name = table_fqn.split('.')[-1]
        ddl_file = output_path / f"{table_name}.sql"
        with open(ddl_file, 'w') as f:
            f.write(ddl)
        print(f"Generated DDL: {ddl_file}")
        
        # Generate JSON schema
        json_schema_file = output_path / f"{table_name}_schema.json"
        generate_json_schema(model_class, str(json_schema_file))
    
    # Validate existing tables (if Spark available)
    try:
        spark = SparkSession.builder.appName("DDL Validation").getOrCreate()
        
        print("\n=== Validating Existing Tables ===")
        for model_class, table_fqn, _ in all_models:
            errors = validate_table_schema(spark, table_fqn, model_class)
            if errors:
                print(f"❌ {table_fqn}: {', '.join(errors)}")
            else:
                print(f"✅ {table_fqn}: Schema matches model")
    except Exception as e:
        print(f"⚠️ Spark not available, skipping validation: {e}")
    
    print(f"\n✅ Generated {len(all_models)} DDL files and JSON schemas in {output_dir}/")

if __name__ == "__main__":
    catalog = sys.argv[1] if len(sys.argv) > 1 else "main"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "generated"
    main(catalog, output_dir)
```

---

## 4. Outputs

### 4.1 Deliverables
* **`scripts/codegen/generate_metadata_ddl.py`** — main codegen script
* **`generated/*.sql`** — DDL files for each table (12 files)
* **`generated/*_schema.json`** — JSON schemas for each model (12 files)
* **Validation report** — console output showing schema match/mismatch

### 4.2 Example Output Files

**`generated/feed_metadata.sql`:**
```sql
CREATE TABLE IF NOT EXISTS main.abc.feed_metadata (
  feed_id STRING NOT NULL COMMENT 'Unique identifier',
  name STRING NOT NULL COMMENT 'Human-readable name',
  source_system STRING NOT NULL COMMENT 'Source system name',
  source_format STRING NOT NULL COMMENT 'File format or connection type',
  source_location STRING NOT NULL COMMENT 'Path or JDBC connection string',
  jdbc_db_type STRING COMMENT 'DB type for JDBC sources',
  load_strategy STRING NOT NULL COMMENT 'Data load strategy',
  target_catalog STRING NOT NULL COMMENT 'UC catalog for Bronze table',
  target_schema STRING NOT NULL COMMENT 'UC schema for Bronze table',
  target_table STRING NOT NULL COMMENT 'Table name in Bronze layer',
  primary_keys ARRAY<STRING> NOT NULL COMMENT 'Primary key columns',
  partition_columns ARRAY<STRING> NOT NULL COMMENT 'Partitioning columns',
  file_format_options MAP<STRING, STRING> NOT NULL COMMENT 'Format-specific options',
  enabled BOOLEAN NOT NULL COMMENT 'Whether feed is active',
  CONSTRAINT feed_metadata_pk PRIMARY KEY (feed_id)
)
USING DELTA
CLUSTER BY (feed_id)
COMMENT 'ABC metadata table for Feed';
```

**`generated/feed_metadata_schema.json`:**
```json
{
  "$defs": {
    "SourceFormat": {
      "enum": ["csv", "json", "parquet", "delta", "avro", "jdbc"],
      "title": "SourceFormat",
      "type": "string"
    },
    "LoadStrategy": {
      "enum": ["append", "scd1", "scd2", "full_refresh"],
      "title": "LoadStrategy",
      "type": "string"
    }
  },
  "properties": {
    "feed_id": {"title": "Feed Id", "type": "string"},
    "name": {"title": "Name", "type": "string"},
    "source_system": {"title": "Source System", "type": "string"},
    "source_format": {"$ref": "#/$defs/SourceFormat"},
    "source_location": {"title": "Source Location", "type": "string"},
    "jdbc_db_type": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "Jdbc Db Type"},
    "load_strategy": {"$ref": "#/$defs/LoadStrategy"}
  },
  "required": ["feed_id", "name", "source_system", "source_format", "source_location", "load_strategy"],
  "title": "Feed",
  "type": "object"
}
```

### 4.3 Downstream Consumption
* **CI/CD pipeline** — run codegen on model changes, commit DDL to Git
* **Deployment** — DDL files can be executed via Databricks SQL or notebooks
* **Config validation** — use JSON schemas to validate YAML/JSON config files before loading

---

## 5. Guardrails

### 5.1 Error Handling
* **Unsupported types** — raise `ValueError` with clear message listing supported types
* **Missing descriptions** — warn if Pydantic field has no docstring (comment will be empty)
* **Table not found** — validation reports missing tables, continues with other tables

### 5.2 Edge Cases
* **Enum values** — DDL includes CHECK constraint with allowed values (optional, not in minimal version)
* **Nested models** — not supported; flatten to JSON STRING or separate table
* **List of dicts** — stored as ARRAY<STRING> with JSON serialization

### 5.3 Performance Considerations
* **Codegen is fast** — introspection + file I/O < 1 second for 12 models
* **Validation** — only runs if Spark available; skips if not

---

## 6. ABC Hooks

### 6.1 Audit
* **DDL generation** — audit when codegen runs:
  ```python
  abc_sdk.audit(
      event="ddl_generation",
      user=current_user,
      models_generated=len(all_models),
      output_dir=output_dir
  )
  ```

### 6.2 Balance
* **Not applicable** — codegen doesn't move data

### 6.3 Cost Tracking
* **Not applicable** — codegen is a local script, no DBU consumption

### 6.4 Logging
* **Structured logging** — log each DDL file generated:
  ```python
  logger.info(f"Generated DDL for {model_class.__name__}", extra={
      "trace_id": trace_id,
      "table_fqn": table_fqn,
      "output_file": str(ddl_file)
  })
  ```

---

## 7. Examples

### 7.1 Running the Script
```bash
# Generate DDL for 'main' catalog
python scripts/codegen/generate_metadata_ddl.py main generated/

# Output:
# Generated DDL: generated/feed_metadata.sql
# Generated JSON schema: generated/feed_metadata_schema.json
# Generated DDL: generated/pipeline_metadata.sql
# Generated JSON schema: generated/pipeline_metadata_schema.json
# ...
# === Validating Existing Tables ===
# ✅ main.abc.feed_metadata: Schema matches model
# ✅ main.abc.pipeline_metadata: Schema matches model
# ...
# ✅ Generated 12 DDL files and JSON schemas in generated/
```

### 7.2 Deploying DDL to Databricks
**Note:** DDL files can be executed in multiple ways:
* Via Databricks SQL editor (copy/paste)
* Via notebook cells (read SQL file content and execute)
* Via CI/CD pipelines using Databricks REST API

### 7.3 Validating Config Files with JSON Schema
```python
import yaml
import json
import jsonschema

# Load config file
with open("config/feeds/policy_feed.yaml") as f:
    feed_config = yaml.safe_load(f)

# Load JSON schema
with open("generated/feed_metadata_schema.json") as f:
    schema = json.load(f)

# Validate
try:
    jsonschema.validate(instance=feed_config, schema=schema)
    print("✅ Config is valid")
except jsonschema.ValidationError as e:
    print(f"❌ Config validation failed: {e.message}")
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **Type mapping** — test `pydantic_to_delta_type()` for all supported types (str, int, float, bool, date, list, dict, enum)
2. **DDL generation** — test `generate_ddl()` produces valid SQL for Feed model
3. **JSON schema** — test `generate_json_schema()` produces valid JSON schema
4. **Schema validation** — test `validate_table_schema()` detects mismatches (missing column, type mismatch)
5. **Main script** — test `main()` generates all 12 DDL files

### 8.2 Integration Tests
* **End-to-end** — run script, execute DDL in Databricks, validate tables match models
* **CI/CD** — integrate into GitHub Actions or Databricks Workflows

### 8.3 Regression Tests
* **Model changes** — modify Feed model (add field), re-run codegen, assert new field in DDL
* **Type changes** — change field type, re-run codegen, assert SQL type updated

---

## 9. References

### 9.1 Internal Documents
* `metadata-models-spec.md` — Pydantic models to introspect
* `ACORD_CANONICAL_SCHEMA.md` — ACORD entity definitions
* `PROJECT_CONTEXT.md` §4 — ABC framework, Unity Catalog

### 9.2 External Standards
* **Pydantic JSON Schema** — https://docs.pydantic.dev/latest/concepts/json_schema/
* **Delta Lake DDL** — https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html
* **JSON Schema** — https://json-schema.org/

### 9.3 Databricks Documentation
* **Unity Catalog CREATE TABLE** — https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table.html
* **Liquid Clustering** — https://docs.databricks.com/aws/en/delta/clustering.html

---

## 10. Decisions Made

All design decisions:

1. **Pydantic introspection** — Use `model_fields` and `get_type_hints()` for field metadata
2. **Type mapping** — Map Python types to Delta SQL types; enums → STRING
3. **Idempotent DDL** — Use `CREATE TABLE IF NOT EXISTS` for safe re-runs
4. **JSON schema** — Use Pydantic's built-in `model_json_schema()` for automatic generation
5. **Validation** — Compare DB schema to Python models; report mismatches, don't fail
6. **Output structure** — One DDL file + one JSON schema file per model
7. **Primary keys** — All tables have primary key with CLUSTER BY for performance

---

**End of Metadata-to-DDL Codegen Spec (Approved)**
