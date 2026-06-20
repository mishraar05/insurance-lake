# Streaming Readers Spec

---

## Front Matter

```yaml
id: streaming-readers-spec
version: 1.0
status: approved
approved_date: 2026-06-18
tier: dataio
component: readers
backlog_ids:
  - DATAIO-002  # Streaming reader implementations
  - READER-002  # Auto Loader / Kafka readers
dependencies:
  - metadata-models-spec
  - engine-contracts-spec
  - file-readers-spec
runtime: Python 3.10+ with PySpark + Structured Streaming
purpose: Implement Reader protocol for streaming data sources (Auto Loader, Kafka)
inputs:
  - Feed metadata (source_location, source_format, file_format_options)
  - engine-contracts-spec (Reader protocol)
outputs:
  - StreamingReader implementation classes
  - Factory registration for streaming formats
  - Unit/integration tests
tools_required:
  - PySpark Structured Streaming API
  - Databricks Auto Loader (cloudFiles)
  - Kafka (optional)
```

---

## 1. Purpose

Implement the **Reader protocol** for streaming data sources, enabling the framework to continuously ingest files via **Auto Loader** and optionally read from **Kafka** streams.

**Two reader implementations:**
1. **AutoLoaderReader** — incrementally loads files from cloud storage using Databricks Auto Loader (cloudFiles format)
2. **KafkaReader** (optional) — reads from Kafka topics for real-time event streams

**Key capabilities:**
* Incremental file ingestion with Auto Loader (schema inference, checkpoint management)
* Support for all file formats (CSV, JSON, Parquet, Avro)
* Automatic schema evolution
* Exactly-once semantics via checkpointing
* Kafka integration for event-driven pipelines (optional)

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements Reader protocol from engine-contracts-spec
* Returns streaming DataFrame (not materialized)
* Supports both batch and streaming modes (batch covered in file-readers-spec)
* ABC audit hooks for stream starts

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (Reader protocol, streaming support)
* **ROADMAP.md Phase 0** — streaming readers are Wave 1 foundation
* **metadata-models-spec.md** — Feed metadata model
* **engine-contracts-spec.md** — Reader protocol definition
* **file-readers-spec.md** — file format patterns
* **Backlog tasks:** DATAIO-002, READER-002

### 2.2 Design Constraints
* **Protocol compliance** — all readers implement Reader protocol (read, supports_format)
* **Streaming DataFrame** — return spark.readStream.format() result
* **Checkpointing** — Auto Loader manages checkpoints automatically
* **Schema inference** — Auto Loader infers schema from first file
* **Schema evolution** — Auto Loader handles schema changes via rescuedDataColumn
* **Performance** — leverage Auto Loader's optimized file listing and ingestion

---

## 3. Procedure

### 3.1 AutoLoaderReader Implementation

**Purpose:** Incrementally load files from cloud storage using Auto Loader

**Key features:**
* Automatically discovers new files
* Tracks processed files via checkpoint
* Handles schema evolution
* Supports all file formats (CSV, JSON, Parquet, Avro, Delta)
* Optimized file listing (uses cloud provider APIs)

```python
# dataio/readers/streaming_readers.py
from typing import Dict, Any
from pyspark.sql import DataFrame, SparkSession

from core.metadata import Feed, SourceFormat
from core.contracts import Reader
from dataio.readers import register_reader

@register_reader(SourceFormat.STREAMING_CSV)
@register_reader(SourceFormat.STREAMING_JSON)
@register_reader(SourceFormat.STREAMING_PARQUET)
@register_reader(SourceFormat.STREAMING_AVRO)
class AutoLoaderReader(Reader):
    """
    Reader for streaming file ingestion using Databricks Auto Loader.
    
    Auto Loader (cloudFiles) features:
    - Automatic file discovery
    - Checkpoint-based exactly-once semantics
    - Schema inference and evolution
    - Optimized file listing
    - Support for all file formats
    
    Format mapping:
    - SourceFormat.STREAMING_CSV → cloudFiles format with CSV options
    - SourceFormat.STREAMING_JSON → cloudFiles format with JSON options
    - SourceFormat.STREAMING_PARQUET → cloudFiles format with Parquet options
    - SourceFormat.STREAMING_AVRO → cloudFiles format with Avro options
    """
    
    def _get_underlying_format(self, source_format: SourceFormat) -> str:
        """Map streaming source format to underlying file format."""
        format_map = {
            SourceFormat.STREAMING_CSV: "csv",
            SourceFormat.STREAMING_JSON: "json",
            SourceFormat.STREAMING_PARQUET: "parquet",
            SourceFormat.STREAMING_AVRO: "avro"
        }
        return format_map.get(source_format, "")
    
    def _get_default_options(self, underlying_format: str) -> Dict[str, Any]:
        """Return default Auto Loader options."""
        base_options = {
            "cloudFiles.format": underlying_format,
            "cloudFiles.schemaLocation": None,  # Must be set by caller
            "cloudFiles.inferColumnTypes": "true",
            "cloudFiles.schemaEvolutionMode": "addNewColumns",
            "rescuedDataColumn": "_rescued_data"
        }
        
        # Add format-specific defaults
        if underlying_format == "csv":
            base_options.update({
                "header": "true",
                "inferSchema": "true",
                "mode": "PERMISSIVE"
            })
        elif underlying_format == "json":
            base_options.update({
                "multiLine": "false",
                "mode": "PERMISSIVE"
            })
        
        return base_options
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read streaming data using Auto Loader.
        
        Args:
            spark: Active SparkSession
            feed: Feed configuration
            
        Returns:
            Streaming DataFrame
            
        Raises:
            ValueError: If schema location not specified, or format unsupported
        """
        # Validate format
        if not self.supports_format(feed.source_format.value):
            raise ValueError(
                f"AutoLoaderReader does not support format: {feed.source_format}"
            )
        
        # Get underlying file format
        underlying_format = self._get_underlying_format(feed.source_format)
        
        # Merge default options with feed options
        options = {**self._get_default_options(underlying_format), **feed.file_format_options}
        
        # Require schema location for checkpointing
        if not options.get("cloudFiles.schemaLocation"):
            # Generate default schema location
            schema_location = f"/tmp/checkpoints/{feed.feed_id}/schema"
            options["cloudFiles.schemaLocation"] = schema_location
        
        # Read streaming data
        try:
            df = spark.readStream.format("cloudFiles") \
                .options(**options) \
                .load(feed.source_location)
            
            return df
            
        except Exception as e:
            raise ValueError(
                f"Failed to read streaming {feed.source_format} from {feed.source_location}: {e}"
            ) from e
    
    def supports_format(self, source_format: str) -> bool:
        """Check if this reader supports the given streaming format."""
        supported = ["streaming_csv", "streaming_json", "streaming_parquet", "streaming_avro"]
        return source_format.lower() in supported
```

**Usage:**
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

# Define streaming feed
feed = Feed(
    feed_id="policy_stream",
    name="Policy Streaming Ingestion",
    source_system="PolicyAdmin",
    source_format=SourceFormat.STREAMING_CSV,
    source_location="/Volumes/main/raw/policies/",
    file_format_options={
        "cloudFiles.schemaLocation": "/mnt/checkpoints/policy_stream/schema",
        "delimiter": "|",
        "header": "true"
    },
    load_strategy=LoadStrategy.APPEND,
    target_catalog="main",
    target_schema="bronze",
    target_table="policy_raw",
    primary_keys=["policy_id"],
    partition_columns=["effective_date"],
    enabled=True
)

# Get reader and read (returns streaming DataFrame)
reader = get_reader(SourceFormat.STREAMING_CSV)
streaming_df = reader.read(spark, feed)

# Write stream to target table
streaming_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/mnt/checkpoints/policy_stream/target") \
    .toTable(feed.target_table_fqn)
```

---

### 3.2 Schema Evolution Handling

**Purpose:** Handle schema changes in source files

Auto Loader's `schemaEvolutionMode` options:
1. **addNewColumns** (default) — add new columns, fill with nulls for old files
2. **rescue** — store schema-mismatched data in _rescued_data column
3. **failOnNewColumns** — fail if new columns detected

**Example configuration:**
```python
feed.file_format_options = {
    "cloudFiles.schemaLocation": "/mnt/checkpoints/policy_stream/schema",
    "cloudFiles.schemaEvolutionMode": "addNewColumns",  # Allow schema evolution
    "cloudFiles.schemaHints": "effective_date DATE, premium DOUBLE",  # Type hints
    "rescuedDataColumn": "_rescued_data"  # Rescue malformed records
}
```

---

### 3.3 KafkaReader Implementation (Optional)

**Purpose:** Read from Kafka topics for real-time event streams

```python
@register_reader(SourceFormat.KAFKA)
class KafkaReader(Reader):
    """
    Reader for Kafka streaming data.
    
    Requires:
    - Kafka broker connection string (feed.source_location = "kafka.broker:9092")
    - Topic name (feed.file_format_options["subscribe"] = "topic_name")
    - Optional: startingOffsets, endingOffsets
    """
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read streaming data from Kafka.
        
        Args:
            spark: Active SparkSession
            feed: Feed configuration
            
        Returns:
            Streaming DataFrame with Kafka schema (key, value, timestamp, partition, offset)
            
        Raises:
            ValueError: If kafka broker or topic not specified
        """
        # Validate Kafka-specific options
        if "subscribe" not in feed.file_format_options:
            raise ValueError("Kafka reader requires 'subscribe' option with topic name")
        
        # Default options
        options = {
            "kafka.bootstrap.servers": feed.source_location,
            "subscribe": feed.file_format_options["subscribe"],
            "startingOffsets": feed.file_format_options.get("startingOffsets", "earliest"),
            **feed.file_format_options
        }
        
        # Read streaming data from Kafka
        try:
            df = spark.readStream.format("kafka") \
                .options(**options) \
                .load()
            
            # Kafka returns: key, value (both binary), topic, partition, offset, timestamp
            return df
            
        except Exception as e:
            raise ValueError(
                f"Failed to read from Kafka topic {options['subscribe']}: {e}"
            ) from e
    
    def supports_format(self, source_format: str) -> bool:
        """Check if this reader supports Kafka format."""
        return source_format.lower() == "kafka"
```

**Usage (Kafka):**
```python
feed = Feed(
    feed_id="claim_kafka",
    source_format=SourceFormat.KAFKA,
    source_location="kafka.broker.example.com:9092",
    file_format_options={
        "subscribe": "claims_topic",
        "startingOffsets": "latest"
    },
    ...
)

reader = get_reader(SourceFormat.KAFKA)
streaming_df = reader.read(spark, feed)

# Parse Kafka value column (JSON)
from pyspark.sql.functions import from_json, col

parsed_df = streaming_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")
```

---

### 3.4 Checkpoint Management

**Purpose:** Ensure exactly-once processing semantics

Auto Loader checkpoints track:
* Processed files
* Schema versions
* File offsets (for Kafka)

**Best practices:**
```python
# Separate checkpoints for schema and data
schema_checkpoint = f"/mnt/checkpoints/{feed.feed_id}/schema"
data_checkpoint = f"/mnt/checkpoints/{feed.feed_id}/target"

# Schema location for Auto Loader
feed.file_format_options["cloudFiles.schemaLocation"] = schema_checkpoint

# Checkpoint location for writeStream
streaming_df.writeStream \
    .option("checkpointLocation", data_checkpoint) \
    .toTable(target_table)
```

**Checkpoint recovery:**
* If checkpoint exists, Auto Loader resumes from last processed file
* If checkpoint deleted, Auto Loader reprocesses all files (use startingVersion for Delta)

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/readers/streaming_readers.py`** — AutoLoaderReader + KafkaReader implementations
* **`dataio/readers/__init__.py`** — Factory registration (extends file_readers registry)
* **Unit tests** — test Auto Loader with synthetic files, Kafka with embedded broker
* **Integration tests** — test streaming ingestion end-to-end

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_reader() for streaming feeds
* **Config-driven pipelines** — YAML configs specify streaming_csv/streaming_json formats

---

## 5. Guardrails

### 5.1 Error Handling
* **Missing schema location** — generate default from feed_id if not specified
* **Schema mismatch** — use rescuedDataColumn to capture malformed records
* **Kafka connection failure** — raise ValueError with broker/topic details
* **Checkpoint corruption** — document recovery procedure (delete and reprocess)

### 5.2 Edge Cases
* **Empty source directory** — Auto Loader waits for new files, doesn't fail
* **Schema evolution** — addNewColumns mode handles new columns gracefully
* **Late-arriving files** — Auto Loader picks up files regardless of timestamp
* **Duplicate files** — Auto Loader tracks processed files by path, skips duplicates
* **Kafka offset reset** — use startingOffsets="earliest" to reprocess from beginning

### 5.3 Performance Considerations
* **File listing optimization** — Auto Loader uses cloud provider APIs (S3 ListObjects, ADLS List Blobs)
* **Micro-batch sizing** — Spark Streaming auto-tunes batch sizes
* **Schema inference overhead** — first batch infers schema; subsequent batches reuse
* **Checkpoint overhead** — checkpoint writes are asynchronous, minimal impact

---

## 6. ABC Hooks

### 6.1 Audit
* **Stream start** — audit when streaming read begins:
  ```python
  abc_sdk.audit(
      event="stream_start",
      feed_id=feed.feed_id,
      source_location=feed.source_location,
      checkpoint_location=checkpoint_location
  )
  ```

### 6.2 Balance
* **Not applicable for readers** — balance checks happen after load

### 6.3 Cost Tracking
* **Streaming DBU consumption** — track per micro-batch:
  ```python
  # In streaming query listener
  abc_sdk.cost_track(
      operation="streaming_read",
      feed_id=feed.feed_id,
      rows_processed=batch_df.count(),
      duration_seconds=batch_duration
  )
  ```

### 6.4 Logging
* **Structured logging** — log stream start and progress:
  ```python
  logger.info(f"Starting stream for feed {feed.feed_id}", extra={
      "trace_id": trace_id,
      "source_format": feed.source_format.value,
      "checkpoint_location": checkpoint_location
  })
  ```

---

## 7. Examples

### 7.1 Auto Loader CSV Stream
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat, LoadStrategy

feed = Feed(
    feed_id="policy_stream_csv",
    name="Policy CSV Stream",
    source_system="PolicyAdmin",
    source_format=SourceFormat.STREAMING_CSV,
    source_location="/Volumes/main/raw/policies/",
    file_format_options={
        "cloudFiles.schemaLocation": "/tmp/checkpoints/policy_stream/schema",
        "delimiter": "|",
        "header": "true",
        "cloudFiles.schemaEvolutionMode": "addNewColumns"
    },
    load_strategy=LoadStrategy.APPEND,
    target_catalog="main",
    target_schema="bronze",
    target_table="policy_raw",
    primary_keys=["policy_id"],
    partition_columns=["effective_date"],
    enabled=True
)

reader = get_reader(SourceFormat.STREAMING_CSV)
streaming_df = reader.read(spark, feed)

# Write stream
query = streaming_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoints/policy_stream/target") \
    .toTable("main.bronze.policy_raw")

query.awaitTermination()
```

### 7.2 Auto Loader JSON Stream with Schema Hints
```python
feed = Feed(
    feed_id="claim_stream_json",
    source_format=SourceFormat.STREAMING_JSON,
    source_location="/Volumes/main/raw/claims/",
    file_format_options={
        "cloudFiles.schemaLocation": "/tmp/checkpoints/claim_stream/schema",
        "cloudFiles.schemaHints": "claim_id STRING, claim_date DATE, amount DOUBLE",
        "multiLine": "true"
    },
    ...
)

reader = get_reader(SourceFormat.STREAMING_JSON)
streaming_df = reader.read(spark, feed)
```

### 7.3 Kafka Stream with JSON Parsing
```python
feed = Feed(
    feed_id="event_kafka",
    source_format=SourceFormat.KAFKA,
    source_location="kafka-broker.example.com:9092",
    file_format_options={
        "subscribe": "insurance_events",
        "startingOffsets": "latest"
    },
    ...
)

reader = get_reader(SourceFormat.KAFKA)
kafka_df = reader.read(spark, feed)

# Parse JSON value
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

schema = StructType([
    StructField("event_id", StringType()),
    StructField("event_type", StringType()),
    StructField("amount", DoubleType())
])

parsed_df = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Write to Delta
parsed_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoints/kafka_stream/target") \
    .toTable("main.bronze.events")
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **AutoLoaderReader** — test CSV, JSON, Parquet, Avro streaming reads
2. **Schema location** — test default generation if not specified
3. **Schema evolution** — test addNewColumns mode, verify new columns added
4. **KafkaReader** — test Kafka read with embedded broker (optional)
5. **Error handling** — test missing schema location, invalid format
6. **Factory pattern** — test @register_reader for streaming formats

### 8.2 Integration Tests
* **End-to-end stream** — write test files, start Auto Loader, verify ingestion
* **Checkpoint recovery** — stop stream, restart, verify resumes from checkpoint
* **Schema evolution** — add column to source file, verify column added to target

### 8.3 Synthetic Data Tests
* **Generate test files** — create sample CSV/JSON files
* **Simulate continuous arrival** — write files incrementally, verify Auto Loader picks up
* **Verify exactly-once** — ensure no duplicates, no missed files

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — Reader protocol definition
* `metadata-models-spec.md` — Feed metadata model
* `file-readers-spec.md` — file format patterns
* `PROJECT_CONTEXT.md` §4 — architecture decisions

### 9.2 External Standards
* **PySpark Structured Streaming** — https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
* **Auto Loader** — https://docs.databricks.com/aws/en/ingestion/auto-loader/
* **Kafka integration** — https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html

### 9.3 Databricks Documentation
* **Auto Loader schema inference** — https://docs.databricks.com/aws/en/ingestion/auto-loader/schema.html
* **Auto Loader options** — https://docs.databricks.com/aws/en/ingestion/auto-loader/options.html
* **Checkpoint management** — https://docs.databricks.com/aws/en/structured-streaming/checkpoints.html

---

## 10. Decisions Made

All design decisions:

1. **Auto Loader as primary streaming reader** — use cloudFiles format for file streaming
2. **Schema location required** — generate default if not specified (f"/tmp/checkpoints/{feed_id}/schema")
3. **Schema evolution mode** — default to "addNewColumns" (most flexible)
4. **Rescued data column** — capture schema-mismatched records in _rescued_data
5. **Kafka support** — optional, for event-driven pipelines
6. **Checkpoint separation** — separate schema checkpoint from data checkpoint
7. **Format mapping** — STREAMING_CSV → cloudFiles(csv), STREAMING_JSON → cloudFiles(json), etc.
8. **Factory pattern** — use @register_reader decorator for streaming formats

---

**End of Streaming Readers Spec (Approved)**
