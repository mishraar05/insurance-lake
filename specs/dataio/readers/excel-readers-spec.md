---
id: dataio.readers.excel-readers
title: Excel Readers Spec
owner: EY
status: draft
target_path: src/dataio/readers/excel/
owning_skill: framework-dev
backlog: []
provides: [ExcelReader, read, supports_format]
depends_on: []
generation_context:
  - specs/dataio/readers/excel-readers-spec.md
acceptance:
  - "pytest tests/unit/test_excel_readers.py"
regeneration: scaffold-then-edit
---

# Excel Readers Spec

## 1. Purpose

Implement the **Reader protocol** for Excel files (.xlsx, .xls), enabling the framework to read tabular data from Excel workbooks.

**Key capabilities:**
* **Multiple worksheets** — read from specific worksheet or all worksheets
* **Cell ranges** — read specific cell ranges (A1:D100)
* **Header rows** — detect and use header rows
* **Merged cells** — handle merged cells gracefully
* **Formula evaluation** — read formula results (not formulas)
* **Data types** — preserve numeric, date, and text types

**Use cases:**
* Rate sheets (actuarial tables)
* Underwriting rules (business logic)
* Reference data (codes, mappings)
* Business user uploads (manual data entry)
* Reports from external systems (agent commissions, vendor data)

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements Reader protocol from engine-contracts-spec
* Returns PySpark DataFrame
* Supports batch reads (not streaming)
* ABC audit hooks for read operations

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (Reader protocol, ABC framework)
* **ROADMAP.md Phase 0** — Excel readers are Wave 1 capability
* **metadata-models-spec.md** — Feed metadata model
* **engine-contracts-spec.md** — Reader protocol definition
* **Backlog tasks:** DATAIO-004, READER-004

### 2.2 Design Constraints
* **Protocol compliance** — implement Reader protocol (read, supports_format)
* **PySpark integration** — use spark.read.format("com.crealytics.spark.excel")
* **File size limits** — Excel files typically < 100MB (memory-bound)
* **Schema inference** — auto-detect data types from cells
* **Error handling** — clear messages for missing worksheets, invalid ranges

---

## 3. Procedure

### 3.1 ExcelReader Implementation

**Purpose:** Read from Excel files with worksheet and range selection

```python
# dataio/readers/excel_readers.py
from typing import Dict, Any
from pyspark.sql import DataFrame, SparkSession

from core.metadata import Feed, SourceFormat
from core.contracts import Reader
from dataio.readers import register_reader

@register_reader(SourceFormat.EXCEL)
class ExcelReader(Reader):
    """
    Reader for Excel files (.xlsx, .xls).
    
    Supports:
    - Multiple worksheets
    - Cell range selection (A1:D100)
    - Header row detection
    - Data type inference
    
    Uses Spark Excel library (com.crealytics.spark.excel).
    """
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read from Excel file as DataFrame.
        
        Args:
            spark: Active SparkSession
            feed: Feed configuration
            
        Returns:
            DataFrame with Excel data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If worksheet or range invalid
        """
        # Validate format
        if not self.supports_format(feed.source_format.value):
            raise ValueError(
                f"{self.__class__.__name__} does not support format: {feed.source_format}"
            )
        
        # Get file path from source_location
        file_path = feed.source_location
        
        # Get Excel options
        worksheet = feed.file_format_options.get("worksheet", "0")  # Default: first sheet
        cell_range = feed.file_format_options.get("cell_range")  # Optional: A1:D100
        header = feed.file_format_options.get("header", "true")  # Default: first row is header
        infer_schema = feed.file_format_options.get("inferSchema", "true")
        
        # Build reader options
        reader = spark.read.format("com.crealytics.spark.excel") \
            .option("header", header) \
            .option("inferSchema", infer_schema) \
            .option("dataAddress", f"'{worksheet}'!{cell_range}" if cell_range else f"'{worksheet}'!")
        
        # Merge additional options
        for key, value in feed.file_format_options.items():
            if key not in ["worksheet", "cell_range", "header", "inferSchema"]:
                reader = reader.option(key, value)
        
        # Read file
        try:
            df = reader.load(file_path)
            return df
            
        except Exception as e:
            if "FileNotFoundException" in str(e) or "Path does not exist" in str(e):
                raise FileNotFoundError(
                    f"Excel file not found: {file_path}"
                ) from e
            else:
                raise ValueError(
                    f"Failed to read Excel file {file_path}: {e}"
                ) from e
    
    def supports_format(self, source_format: str) -> bool:
        """Check if this reader supports the given format."""
        return source_format.lower() in ["excel", "xlsx", "xls"]
```

---

### 3.2 Usage Patterns

**Read from first worksheet:**
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

feed = Feed(
    feed_id="rate_sheet",
    source_format=SourceFormat.EXCEL,
    source_location="/Volumes/main/raw/rates/auto_rates_2024.xlsx",
    file_format_options={
        "worksheet": "0",  # First sheet (can use name: "RateTable")
        "header": "true",
        "inferSchema": "true"
    },
    ...
)

reader = get_reader(SourceFormat.EXCEL)
df = reader.read(spark, feed)
```

**Read specific worksheet by name:**
```python
feed = Feed(
    feed_id="underwriting_rules",
    source_format=SourceFormat.EXCEL,
    source_location="/Volumes/main/raw/rules/underwriting_rules.xlsx",
    file_format_options={
        "worksheet": "CommercialAuto",  # Worksheet name
        "header": "true"
    },
    ...
)

reader = get_reader(SourceFormat.EXCEL)
df = reader.read(spark, feed)
```

**Read specific cell range:**
```python
feed = Feed(
    feed_id="commission_table",
    source_format=SourceFormat.EXCEL,
    source_location="/Volumes/main/raw/commissions/agent_commissions.xlsx",
    file_format_options={
        "worksheet": "Q1_2024",
        "cell_range": "A5:F100",  # Skip header rows, read data range
        "header": "true"
    },
    ...
)

reader = get_reader(SourceFormat.EXCEL)
df = reader.read(spark, feed)
```

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/readers/excel_readers.py`** — ExcelReader implementation
* **`dataio/readers/__init__.py`** — Factory registration (extends pattern)
* **Unit tests** — test worksheet selection, cell ranges
* **Integration tests** — test reading from sample Excel files

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_reader(SourceFormat.EXCEL) for business user uploads
* **Config-driven pipelines** — YAML configs specify source_format: excel

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
* **File not found** — raise FileNotFoundError with file path
* **Worksheet not found** — raise ValueError with worksheet name
* **Invalid cell range** — raise ValueError with range format hint (A1:D100)
* **Empty worksheet** — return empty DataFrame with inferred schema

### 5.2 Edge Cases
* **Multiple worksheets** — read one worksheet at a time (not all worksheets)
* **Merged cells** — Spark Excel library unmerges cells (repeats values)
* **Formulas** — read formula results (not formula text)
* **Hidden rows/columns** — included in read (not filtered)
* **Date formats** — PySpark infers as DateType or StringType

### 5.3 Performance Considerations
* **File size** — Excel files > 100MB may cause memory issues
* **Large worksheets** — 100K+ rows may be slow (consider CSV export)
* **No partitioning** — Excel files read as single partition
* **Schema inference** — can be slow for large files

---

## 6. ABC Hooks

### 6.1 Audit
* **Read operations** — audit Excel reads:
  ```python
  abc_sdk.audit(
      event="excel_read_start",
      feed_id=feed.feed_id,
      file_path=feed.source_location,
      worksheet=feed.file_format_options.get("worksheet")
  )
  ```

### 6.2 Balance
* **Row count validation** — compare source and target:
  ```python
  abc_sdk.balance(
      check_type="row_count",
      source="excel_file",
      target=target_table_fqn,
      source_count=df.count()
  )
  ```

### 6.3 Cost Tracking
* **DBU consumption** — track Excel reads:
  ```python
  abc_sdk.cost_track(
      operation="excel_read",
      feed_id=feed.feed_id,
      rows_processed=df.count(),
      duration_seconds=elapsed_time
  )
  ```

---

## 7. Examples

### 7.1 Read Rate Sheet
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

feed = Feed(
    feed_id="auto_rates",
    source_format=SourceFormat.EXCEL,
    source_location="/Volumes/main/raw/rates/auto_rates_2024.xlsx",
    file_format_options={
        "worksheet": "RateTable",
        "header": "true",
        "inferSchema": "true"
    },
    ...
)

reader = get_reader(SourceFormat.EXCEL)
df = reader.read(spark, feed)

print(f"Read {df.count()} rate records")
df.show(5)
```

### 7.2 Read with Cell Range (Skip Header Rows)
```python
# Excel file has title rows before data table
feed = Feed(
    feed_id="underwriting_rules",
    source_format=SourceFormat.EXCEL,
    source_location="/Volumes/main/raw/rules/rules_2024.xlsx",
    file_format_options={
        "worksheet": "CommercialAuto",
        "cell_range": "A10:H500",  # Skip title rows (1-9)
        "header": "true"  # Row 10 is header
    },
    ...
)

reader = get_reader(SourceFormat.EXCEL)
df = reader.read(spark, feed)
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **Worksheet selection** — test by index and name
2. **Cell range** — test specific range (A1:D100)
3. **Header row** — test header=true and header=false
4. **Schema inference** — test inferSchema=true
5. **Error handling** — test file not found, invalid worksheet

### 8.2 Integration Tests
* **Sample Excel files** — test reading from test .xlsx files
* **Multiple worksheets** — test reading different worksheets
* **Cell ranges** — test various range formats

### 8.3 Performance Tests
* **Large worksheet** — test 10K+ rows

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — Reader protocol
* `metadata-models-spec.md` — Feed metadata
* `file-readers-spec.md` — Base Reader pattern

### 9.2 External Standards
* **Spark Excel** — https://github.com/crealytics/spark-excel
* **Excel formats** — https://support.microsoft.com/en-us/excel

### 9.3 Databricks Documentation
* **Spark Excel** — https://docs.databricks.com/aws/en/external-data/excel.html

---

## 10. Decisions Made

1. **Spark Excel library** — use com.crealytics.spark.excel (bundled in Databricks)
2. **Worksheet selection** — by index (0-based) or name
3. *

## 11. Regeneration contract
`scaffold-then-edit`: the class + method skeleton are fully generated; the Spark/connector-touching parts are generated then reviewed against current Databricks/driver docs.

## 12. References
`specs/foundation/contracts-spec.md` (`Reader`/`LoadStrategy`/`WriteResult`) · `specs/foundation/config-model-spec.md` (`SourceConfig`/`TargetConfig`/`LoadConfig`) · `specs/dataio/schema-evolution-spec.md` · `skills/_shared/project-structure.md`.
