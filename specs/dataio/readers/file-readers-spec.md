---
id: dataio.readers.file-readers
title: File Readers Spec
owner: EY
status: draft
target_path: src/readers/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/readers/file-readers-spec.md
acceptance:
  - "pytest tests/unit/test_file_readers.py"
regeneration: scaffold-then-edit
---

# File Readers Spec

## 1. Purpose

Implement the **Reader protocol** for file-based data sources, enabling the framework to read CSV, JSON, Parquet, Delta, and Avro files from various locations (Unity Catalog Volumes, cloud storage, DBFS).

**Five reader implementations:**
1. **CSVReader** — reads CSV files with configurable schema inference and options
2. **JSONReader** — reads JSON files (single-line and multi-line)
3. **ParquetReader** — reads Parquet files (columnar format)
4. **DeltaReader** — reads Delta Lake tables and files
5. **AvroReader** — reads Avro files (schema evolution support)

**Key capabilities:**
* Schema inference or explicit schema application
* Format-specific options (delimiter, header, multiLine, etc.)
* Error handling for missing files, corrupt data
* Support for wildcards and directory reads
* Unity Catalog Volume integration

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements Reader protocol from engine-contracts-spec
* Returns PySpark DataFrame (standard Databricks pattern)
* Supports both batch and streaming modes (streaming covered in separate spec)
* ABC audit hooks for read operations

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (Reader protocol, ABC framework)
* **ROADMAP.md Phase 0** — file readers are Wave 1 foundation
* **metadata-models-spec.md** — Feed metadata model
* **engine-contracts-spec.md** — Reader protocol definition
* **Backlog tasks:** DATAIO-001, READER-001

### 2.2 Design Constraints
* **Protocol compliance** — all readers implement Reader protocol (read, supports_format)
* **PySpark API** — use spark.read.format() pattern
* **Format options** — pass Feed.file_format_options to PySpark reader
* **Error handling** — raise FileNotFoundError, ValueError with clear messages
* **Performance** — leverage Spark's columnar reads, no unnecessary .collect()

---

## 3. Procedure

### 3.1 Base FileReader Abstract Class

**Purpose:** Common logic shared by all file readers

```python
# dataio/readers/file_readers.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from pyspark.sql import DataFrame, SparkSession

from core.metadata import Feed, SourceFormat
from core.contracts import Reader

class FileReader(Reader, ABC):
    """
    Abstract base class for file-based readers.
    
    Subclasses implement format-specific read logic.
    """
    
    @abstractmethod
    def _get_format(self) -> str:
        """Return Spark format string (e.g., 'csv', 'json')."""
        pass
    
    @abstractmethod
    def _get_default_options(self) -> Dict[str, Any]:
        """Return default format-specific options."""
        pass
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read file-based data source as DataFrame.
        
        Args:
            spark: Active SparkSession
            feed: Feed configuration
            
        Returns:
            DataFrame with source data
            
        Raises:
            FileNotFoundError: If source_location doesn't exist
            ValueError: If format is unsupported
        """
        # Validate format
        if not self.supports_format(feed.source_format.value):
            raise ValueError(
                f"{self.__class__.__name__} does not support format: {feed.source_format}"
            )
        
        # Merge default options with feed options
        options = {**self._get_default_options(), **feed.file_format_options}
        
        # Read data
        try:
            df = spark.read.format(self._get_format()) \
                .options(**options) \
                .load(feed.source_location)
            
            return df
            
        except Exception as e:
            # Check if file not found
            if "FileNotFoundException" in str(e) or "Path does not exist" in str(e):
                raise FileNotFoundError(
                    f"Source location not found: {feed.source_location}"
                ) from e
            else:
                raise ValueError(
                    f"Failed to read {feed.source_format} from {feed.source_location}: {e}"
                ) from e
    
    def supports_format(self, source_format: str) -> bool:
        """Check if this reader supports the given format."""
        return source_format.lower() == self._get_format().lower()
```

---

### 3.2 CSVReader Implementation

**Purpose:** Read CSV files with schema inference and configurable options

```python
from dataio.readers import register_reader
from core.metadata import SourceFormat

@register_reader(SourceFormat.CSV)
class CSVReader(FileReader):
    """
    Reader for CSV files.
    
    Default options:
    - header: true (first row is header)
    - inferSchema: true (auto-detect column types)
    - mode: PERMISSIVE (tolerant of corrupt records)
    """
    
    def _get_format(self) -> str:
        return "csv"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "header": "true",
            "inferSchema": "true",
            "mode": "PERMISSIVE",
            "columnNameOfCorruptRecord": "_corrupt_record"
        }
```

**Usage:**
```python
from dataio.readers import get_reader

feed = Feed(
    feed_id="csv_feed_001",
    source_format=SourceFormat.CSV,
    source_location="/Volumes/main/bronze/policies/",
    file_format_options={"delimiter": "|", "encoding": "UTF-8"}
)

reader = get_reader(SourceFormat.CSV)
df = reader.read(spark, feed)
```

---

### 3.3 JSONReader Implementation

**Purpose:** Read JSON files (single-line and multi-line)

```python
@register_reader(SourceFormat.JSON)
class JSONReader(FileReader):
    """
    Reader for JSON files.
    
    Default options:
    - multiLine: false (one JSON object per line)
    - mode: PERMISSIVE (tolerant of corrupt records)
    
    For multi-line JSON (e.g., pretty-printed), set multiLine: true in file_format_options.
    """
    
    def _get_format(self) -> str:
        return "json"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "multiLine": "false",
            "mode": "PERMISSIVE",
            "columnNameOfCorruptRecord": "_corrupt_record"
        }
```

**Example (multi-line JSON):**
```python
feed = Feed(
    feed_id="json_feed_001",
    source_format=SourceFormat.JSON,
    source_location="/Volumes/main/bronze/claims.json",
    file_format_options={"multiLine": "true"}  # Pretty-printed JSON
)

reader = get_reader(SourceFormat.JSON)
df = reader.read(spark, feed)
```

---

### 3.4 ParquetReader Implementation

**Purpose:** Read Parquet files (columnar format)

```python
@register_reader(SourceFormat.PARQUET)
class ParquetReader(FileReader):
    """
    Reader for Parquet files.
    
    Parquet is a columnar format with built-in schema.
    No schema inference needed; schema is embedded in files.
    """
    
    def _get_format(self) -> str:
        return "parquet"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "mergeSchema": "false"  # Set to true to merge schemas across files
        }
```

**Usage:**
```python
feed = Feed(
    feed_id="parquet_feed_001",
    source_format=SourceFormat.PARQUET,
    source_location="/Volumes/main/bronze/transactions/*.parquet",
    file_format_options={"mergeSchema": "true"}  # Merge schemas if needed
)

reader = get_reader(SourceFormat.PARQUET)
df = reader.read(spark, feed)
```

---

### 3.5 DeltaReader Implementation

**Purpose:** Read Delta Lake tables and files

```python
@register_reader(SourceFormat.DELTA)
class DeltaReader(FileReader):
    """
    Reader for Delta Lake tables and files.
    
    Supports:
    - Reading Delta tables by path
    - Reading Delta tables by Unity Catalog FQN
    - Time travel (version, timestamp)
    """
    
    def _get_format(self) -> str:
        return "delta"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {}
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read Delta table.
        
        Supports two modes:
        1. Table name (e.g., "catalog.schema.table") → spark.table()
        2. Path (e.g., "/mnt/delta/table") → spark.read.format("delta").load()
        """
        # Check if source_location is a table FQN (contains dots but no slashes)
        is_table_name = "." in feed.source_location and "/" not in feed.source_location
        
        if is_table_name:
            # Read by table name (Unity Catalog)
            try:
                df = spark.table(feed.source_location)
                
                # Apply time travel if specified
                version = feed.file_format_options.get("versionAsOf")
                timestamp = feed.file_format_options.get("timestampAsOf")
                
                if version:
                    df = spark.read.format("delta").option("versionAsOf", version).table(feed.source_location)
                elif timestamp:
                    df = spark.read.format("delta").option("timestampAsOf", timestamp).table(feed.source_location)
                
                return df
                
            except Exception as e:
                raise ValueError(f"Failed to read Delta table {feed.source_location}: {e}") from e
        else:
            # Read by path
            return super().read(spark, feed)
```

**Usage (time travel):**
```python
feed = Feed(
    feed_id="delta_feed_001",
    source_format=SourceFormat.DELTA,
    source_location="main.bronze.policy_raw",
    file_format_options={"versionAsOf": "5"}  # Read version 5
)

reader = get_reader(SourceFormat.DELTA)
df = reader.read(spark, feed)
```

---

### 3.6 AvroReader Implementation

**Purpose:** Read Avro files (schema evolution support)

```python
@register_reader(SourceFormat.AVRO)
class AvroReader(FileReader):
    """
    Reader for Avro files.
    
    Avro is a row-based format with embedded schema.
    Supports schema evolution and compression.
    """
    
    def _get_format(self) -> str:
        return "avro"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "ignoreExtension": "true"  # Read files regardless of extension
        }
```

**Usage:**
```python
feed = Feed(
    feed_id="avro_feed_001",
    source_format=SourceFormat.AVRO,
    source_location="/Volumes/main/bronze/claims/*.avro",
    file_format_options={}
)

reader = get_reader(SourceFormat.AVRO)
df = reader.read(spark, feed)
```

---

### 3.7 Factory Registration Pattern

**Already implemented in engine-contracts-spec:**

```python
# dataio/readers/__init__.py
from typing import Dict, Type
from core.contracts import Reader
from core.metadata import SourceFormat

_READER_REGISTRY: Dict[SourceFormat, Type[Reader]] = {}

def register_reader(source_format: SourceFormat):
    """Decorator to register a Reader implementation."""
    def decorator(cls: Type[Reader]) -> Type[Reader]:
        _READER_REGISTRY[source_format] = cls
        return cls
    return decorator

def get_reader(source_format: SourceFormat) -> Reader:
    """Get Reader implementation for source format."""
    if source_format not in _READER_REGISTRY:
        raise ValueError(f"No reader registered for format: {source_format}")
    return _READER_REGISTRY[source_format]()
```

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/readers/file_readers.py`** — FileReader base class + 5 implementations
* **`dataio/readers/__init__.py`** — Factory registration (already defined in engine-contracts-spec)
* **`dataio/readers/exceptions.py`** — Custom exceptions (FileReadError, SchemaInferenceError)
* **Unit tests** — test each reader with synthetic data
* **Integration tests** — test reading from Unity Catalog Volumes

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_reader() to instantiate correct reader for Feed
* **Config-driven pipelines** — YAML configs specify source_format, readers are auto-selected

---

## 5. Guardrails

### SOLID Principles Application

**Single Responsibility Principle (SRP):**
- Each component/class has ONE reason to change
- Separate concerns: reading, transformation, writing, validation

**Open/Closed Principle (OCP):**
- Open for extension via new implementations
- Closed for modification of existing interfaces

**Liskov Substitution Principle (LSP):**
- Subclasses/implementations are substitutable for their base protocol
- All implementations honor the same contract

**Interface Segregation Principle (ISP):**
- Clients depend only on methods they use
- Separate protocols for different concerns (Reader, LoadStrategy, Engine, Check, Masker)

**Dependency Inversion Principle (DIP):**
- Depend on abstractions (protocols), not concrete implementations
- High-level modules don't depend on low-level details



### 5.1 Error Handling
* **File not found** — raise FileNotFoundError with full path
* **Corrupt data** — use PERMISSIVE mode, log corrupt records to _corrupt_record column
* **Schema mismatch** — CSV/JSON readers infer schema; Parquet/Delta/Avro have embedded schema
* **Unsupported format** — raise ValueError with supported formats list

### 5.2 Edge Cases
* **Wildcard patterns** — PySpark handles `*.csv`, `part-*.parquet` natively
* **Empty directories** — return empty DataFrame with inferred/specified schema
* **Mixed file formats in directory** — reader only reads matching format (e.g., CSV reader ignores .json files)
* **Nested JSON** — JSONReader handles nested structures; schema inference works recursively
* **Delta time travel** — DeltaReader supports versionAsOf and timestampAsOf options

### 5.3 Performance Considerations
* **Lazy evaluation** — readers return DataFrame (not materialized); caller decides when to execute
* **Partition pruning** — PySpark automatically prunes partitions for partitioned Parquet/Delta
* **Schema inference** — can be expensive for large CSV/JSON; prefer explicit schema when possible
* **Column projection** — DataFrame API allows `.select()` after read for column pruning

---

## 6. ABC Hooks

### 6.1 Audit
* **Read operations** — audit when feed is read:
  ```python
  def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
      abc_sdk.audit(
          event="feed_read_start",
          feed_id=feed.feed_id,
          source_location=feed.source_location,
          source_format=feed.source_format.value
      )
      
      try:
          df = super().read(spark, feed)
          row_count = df.count()  # Materialize for audit
          
          abc_sdk.audit(
              event="feed_read_success",
              feed_id=feed.feed_id,
              rows_read=row_count
          )
          
          return df
      except Exception as e:
          abc_sdk.audit(
              event="feed_read_failed",
              feed_id=feed.feed_id,
              error=str(e)
          )
          raise
  ```

### 6.2 Balance
* **Not applicable** — readers don't write data; balance checks happen after load

### 6.3 Cost Tracking
* **DBU consumption** — track read operations:
  ```python
  abc_sdk.cost_track(
      operation="read",
      feed_id=feed.feed_id,
      rows_processed=row_count,
      duration_seconds=elapsed_time
  )
  ```

### 6.4 Logging
* **Structured logging** — log read operations with trace ID:
  ```python
  logger.info(f"Reading feed {feed.feed_id} from {feed.source_location}", extra={
      "trace_id": trace_id,
      "source_format": feed.source_format.value,
      "file_format_options": feed.file_format_options
  })
  ```

---

## 7. Examples

### 7.1 Reading CSV with Custom Delimiter
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

# Define feed with pipe-delimited CSV
feed = Feed(
    feed_id="policy_csv",
    name="Policy Master CSV",
    source_system="PolicyAdmin",
    source_format=SourceFormat.CSV,
    source_location="/Volumes/main/bronze/policies/",
    file_format_options={
        "delimiter": "|",
        "encoding": "UTF-8",
        "nullValue": "NULL"
    },
    load_strategy=LoadStrategy.APPEND,
    target_catalog="main",
    target_schema="bronze",
    target_table="policy_raw",
    primary_keys=["policy_id"],
    partition_columns=["effective_date"],
    enabled=True
)

# Get reader and read
reader = get_reader(feed.source_format)
df = reader.read(spark, feed)

# Verify
print(f"Read {df.count()} policies")
df.printSchema()
```

### 7.2 Reading Multi-Line JSON
```python
feed = Feed(
    feed_id="claim_json",
    source_format=SourceFormat.JSON,
    source_location="/Volumes/main/bronze/claims.json",
    file_format_options={"multiLine": "true"},
    ...
)

reader = get_reader(SourceFormat.JSON)
df = reader.read(spark, feed)
```

### 7.3 Reading Delta Table with Time Travel
```python
feed = Feed(
    feed_id="policy_delta_v5",
    source_format=SourceFormat.DELTA,
    source_location="main.bronze.policy_raw",
    file_format_options={"versionAsOf": "5"},  # Read version 5
    ...
)

reader = get_reader(SourceFormat.DELTA)
df = reader.read(spark, feed)
```

### 7.4 Reading Parquet with Schema Merge
```python
feed = Feed(
    feed_id="transaction_parquet",
    source_format=SourceFormat.PARQUET,
    source_location="/Volumes/main/bronze/transactions/*.parquet",
    file_format_options={"mergeSchema": "true"},  # Merge schemas
    ...
)

reader = get_reader(SourceFormat.PARQUET)
df = reader.read(spark, feed)
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **CSVReader** — test default options, custom delimiter, header/no-header, schema inference
2. **JSONReader** — test single-line and multi-line JSON, nested structures
3. **ParquetReader** — test simple read, schema merge, wildcard patterns
4. **DeltaReader** — test table name read, path read, time travel (version, timestamp)
5. **AvroReader** — test read with schema evolution
6. **Error handling** — test FileNotFoundError, corrupt data, unsupported format
7. **Factory pattern** — test register_reader and get_reader

### 8.2 Integration Tests
* **Unity Catalog Volumes** — read CSV/JSON/Parquet from /Volumes/catalog/schema/volume/
* **Cloud storage** — read from S3 (s3://bucket/path), ABFSS (abfss://container@account)
* **Mixed formats** — verify CSV reader ignores JSON files in same directory

### 8.3 Synthetic Data Tests
* **Generate test files** — create sample CSV/JSON/Parquet/Delta/Avro files
* **Validate schema** — assert inferred schema matches expected schema
* **Validate data** — assert row counts and column values

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — Reader protocol definition
* `metadata-models-spec.md` — Feed metadata model
* `PROJECT_CONTEXT.md` §4 — architecture decisions

### 9.2 External Standards
* **PySpark DataFrameReader** — https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrameReader.html
* **CSV options** — https://spark.apache.org/docs/latest/sql-data-sources-csv.html
* **JSON options** — https://spark.apache.org/docs/latest/sql-data-sources-json.html
* **Parquet** — https://spark.apache.org/docs/latest/sql-data-sources-parquet.html
* **Delta Lake** — https://docs.databricks.com/aws/en/delta/index.html
* **Avro** — https://spark.apache.org/docs/latest/sql-data-sources-avro.html

### 9.3 Databricks Documentation
* **Unity Catalog Volumes** — https://docs.databricks.com/aws/en/data-governance/unity-catalog/volumes.html
* **Delta time travel** — https://docs.databricks.com/aws/en/delta/history.html

---

## 10. Decisions Made

All design decisions:

1. **Base class** — FileReader abstract class shares common read logic; subclasses override format/options
2. **Error handling** — Catch FileNotFoundException, wrap in FileNotFoundError with clear message
3. **Default options** — Each reader provides sensible defaults (header=true for CSV, multiLine=false for JSON)
4. **Schema inference** — Enabled by default for CSV/JSON; embedded in Parquet/Delta/Avro
5. **Corrupt records** — PERMISSIVE mode with _corrupt_record column (don't fail on bad data)
6. **Delta table reads** — Support both FQN (catalog.schema.table) and path (/mnt/delta/table)
7. **Time travel** — DeltaReader supports versionAsOf and timestampAsOf via file_format_options
8. **Factory pattern** — Use decorator-based registration from engine-contracts-spec

---

**End of File Readers Spec (Approved)**
