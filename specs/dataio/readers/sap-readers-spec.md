---
id: dataio.readers.sap-readers
title: SAP Readers Spec
owner: EY
status: draft
target_path: src/dataio/readers/sap/
owning_skill: framework-dev
backlog: []
provides: [SAPHANAReader]
depends_on: []
generation_context:
  - specs/dataio/readers/sap-readers-spec.md
acceptance:
  - "pytest tests/unit/test_sap_readers.py"
regeneration: scaffold-then-edit
---

# SAP Readers Spec

## 1. Purpose

Implement the **Reader protocol** for SAP systems, enabling the framework to read data from SAP ERP systems.

**Supported SAP sources:**
1. **SAP HANA** — in-memory database (JDBC-based)
2. **Partner connectors** (optional) — Theobald Xtract, CData, etc.

**Key capabilities:**
* **SAP HANA** — read tables and views via JDBC
* **Table extraction** — read SAP tables (BKPF, BSEG, KNA1, etc.)
* **Custom extractors** — optional partner connectors for complex SAP extraction
* **Secret management** — retrieve credentials from Databricks Secrets

**Use cases:**
* General Ledger (GL) data for financial reporting
* HR data for workforce analytics
* Vendor/customer master data
* Enterprise resource planning (ERP) integration

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements Reader protocol from engine-contracts-spec
* SAP HANA uses JDBC (extends JDBCReader)
* Returns PySpark DataFrame
* ABC audit hooks for read operations

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (Reader protocol, ABC framework)
* **ROADMAP.md Phase 0** — SAP readers are Wave 1 optional capability
* **metadata-models-spec.md** — Feed metadata model
* **engine-contracts-spec.md** — Reader protocol definition
* **jdbc-readers-spec.md** — JDBC base pattern
* **Backlog tasks:** DATAIO-005, READER-005

### 2.2 Design Constraints
* **Protocol compliance** — implement Reader protocol (read, supports_format)
* **SAP HANA via JDBC** — use PySpark JDBC with SAP HANA driver
* **Secret management** — retrieve credentials from Databricks Secrets
* **Partner connectors** — optional integration for complex SAP scenarios
* **Error handling** — clear messages for connection failures

---

## 3. Procedure

### 3.1 SAP HANA Reader (JDBC-Based)

**Purpose:** Read from SAP HANA database via JDBC

```python
# dataio/readers/sap_readers.py
from typing import Dict, Any
from pyspark.sql import DataFrame, SparkSession

from core.metadata import Feed, SourceFormat
from dataio.readers.jdbc_readers import JDBCReader
from dataio.readers import register_reader

@register_reader(SourceFormat.SAP_HANA)
class SAPHANAReader(JDBCReader):
    """
    Reader for SAP HANA database.
    
    Uses JDBC driver: com.sap.db.jdbc.Driver
    
    Installation:
    - SAP HANA JDBC driver must be installed on cluster
    - Download from SAP Support Portal: ngdbc.jar
    - Install via cluster init script or Maven coordinates
    """
    
    def _get_jdbc_url(self, feed: Feed) -> str:
        """
        Construct SAP HANA JDBC URL.
        
        Expected feed.source_location format:
        - "server:port/database" (e.g., "hana.example.com:30015/HDB")
        - OR provide full jdbc_url in file_format_options
        """
        if "jdbc_url" in feed.file_format_options:
            return feed.file_format_options["jdbc_url"]
        
        parts = feed.source_location.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid source_location format: {feed.source_location}. "
                "Expected: server:port/database"
            )
        
        server_port = parts[0]
        database = parts[1]
        
        return f"jdbc:sap://{server_port}/?databaseName={database}"
    
    def _get_driver_class(self) -> str:
        return "com.sap.db.jdbc.Driver"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "fetchsize": "1000"
        }
```

**Usage:**
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

# Read SAP HANA table
feed = Feed(
    feed_id="sap_gl_data",
    source_format=SourceFormat.SAP_HANA,
    source_location="hana.example.com:30015/HDB",
    file_format_options={
        "dbtable": "SAPSR3.BKPF",  # SAP accounting header table
        "secret_scope": "sap_secrets",
        "secret_user_key": "sap_hana_user",
        "secret_password_key": "sap_hana_password"
    },
    ...
)

reader = get_reader(SourceFormat.SAP_HANA)
df = reader.read(spark, feed)
```

---

### 3.2 Partner SAP Connectors (Optional)

**Purpose:** Guidance for using partner connectors for complex SAP extraction

**Common partner connectors:**
1. **Theobald Xtract** — SAP extraction suite
2. **CData** — SAP JDBC/ODBC drivers
3. **SAP Data Services** — SAP native ETL tool
4. **Fivetran / Airbyte** — Managed connectors

**Integration pattern:**
```python
# Example: Partner connector exports to Delta, then read Delta
# (Partner connector -> Delta Lake -> Framework reads Delta)

feed = Feed(
    feed_id="sap_extract_via_theobald",
    source_format=SourceFormat.DELTA,  # Read Delta output
    source_location="main.bronze.sap_bkpf_raw",  # Delta table
    file_format_options={},
    ...
)

# Framework reads Delta table (partner connector populates it)
reader = get_reader(SourceFormat.DELTA)
df = reader.read(spark, feed)
```

**Decision:** Framework focuses on SAP HANA (JDBC). Complex SAP extraction (R/3, ECC, S/4) delegated to partner connectors that export to Delta/Parquet.

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/readers/sap_readers.py`** — SAPHANAReader implementation
* **`dataio/readers/__init__.py`** — Factory registration (extends pattern)
* **Unit tests** — test SAP HANA JDBC URL construction
* **Integration tests** — test reading from test SAP HANA database (if available)
* **Documentation** — guidance for partner connector integration

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_reader(SourceFormat.SAP_HANA) for SAP data
* **Config-driven pipelines** — YAML configs specify source_format: sap_hana

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
* **Driver not found** — raise ValueError with installation instructions
* **Connection failure** — raise ValueError with connection details
* **Invalid table** — raise ValueError with table name

### 5.2 Edge Cases
* **Large SAP tables** — use partitioned reads (partitionColumn)
* **SAP schema names** — typically "SAPSR3" or "SAP<SID>"
* **Client parameter** — SAP requires client (mandt) in queries

### 5.3 Performance Considerations
* **SAP HANA performance** — SAP HANA is optimized for fast reads
* **Partitioned reads** — use partitionColumn for very large tables
* **Column projection** — specify columns in query (don't SELECT *)

---

## 6. ABC Hooks

### 6.1 Audit
* **Read operations** — audit SAP reads:
  ```python
  abc_sdk.audit(
      event="sap_read_start",
      feed_id=feed.feed_id,
      sap_table=feed.file_format_options.get("dbtable")
  )
  ```

### 6.2 Balance
* **Row count validation** — compare source and target:
  ```python
  abc_sdk.balance(
      check_type="sap_row_count",
      source="sap_hana",
      target=target_table_fqn,
      source_count=df.count()
  )
  ```

### 6.3 Cost Tracking
* **DBU consumption** — track SAP reads:
  ```python
  abc_sdk.cost_track(
      operation="sap_read",
      feed_id=feed.feed_id,
      rows_processed=df.count(),
      duration_seconds=elapsed_time
  )
  ```

---

## 7. Examples

### 7.1 Read SAP HANA Table
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

# Read SAP General Ledger data
feed = Feed(
    feed_id="sap_gl",
    source_format=SourceFormat.SAP_HANA,
    source_location="hana.example.com:30015/HDB",
    file_format_options={
        "dbtable": "SAPSR3.BKPF",  # Accounting document header
        "secret_scope": "sap_secrets"
    },
    ...
)

reader = get_reader(SourceFormat.SAP_HANA)
df = reader.read(spark, feed)

print(f"Read {df.count()} accounting documents")
df.show(5)
```

### 7.2 Read with Custom Query
```python
# Read specific SAP client data
feed = Feed(
    feed_id="sap_gl_client_100",
    source_format=SourceFormat.SAP_HANA,
    source_location="hana.example.com:30015/HDB",
    file_format_options={
        "secret_scope": "sap_secrets",
        "query": """
            (SELECT MANDT, BUKRS, BELNR, GJAHR, BLDAT
             FROM SAPSR3.BKPF
             WHERE MANDT = '100'
               AND GJAHR = '2024') AS sap_gl
        """
    },
    ...
)

reader = get_reader(SourceFormat.SAP_HANA)
df = reader.read(spark, feed)
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **SAP HANA URL** — test JDBC URL construction
2. **Driver class** — test com.sap.db.jdbc.Driver
3. **Query-based reads** — test custom SQL queries
4. **Error handling** — test connection failure, invalid table

### 8.2 Integration Tests
* **SAP HANA database** — test reading from test SAP HANA instance (if available)
* **Partner connector integration** — test reading Delta output from partner connector

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — Reader protocol
* `metadata-models-spec.md` — Feed metadata
* `jdbc-readers-spec.md` — JDBC base pattern

### 9.2 External Standards
* **SAP HANA JDBC** — https://help.sap.com/docs/SAP_HANA_PLATFORM/0eec0d68141541d1b07893a39944924e/ff15928cf5594d78b841fbbe649f04b4.html
* **SAP Tables** — https://www.se80.co.uk/saptables/ (SAP table reference)

### 9.3 Databricks Documentation
* **Partner SAP connectors** — https://docs.databricks.com/integrations/index.html

---

## 10. Decisions Made

1. **SAP HANA via JDBC** — primary implementation (extends JDBCReader)
2. **Driver** — com.sap.db.jdbc.Driver (requires manual installation)
3. **Partner connectors** — recommended for complex SAP extraction
4. **Delta Lake integration** — partner

## 11. Regeneration contract
`scaffold-then-edit`: the class + method skeleton are fully generated; the Spark/connector-touching parts are generated then reviewed against current Databricks/driver docs.

## 12. References
`specs/foundation/contracts-spec.md` (`Reader`/`LoadStrategy`/`WriteResult`) · `specs/foundation/config-model-spec.md` (`SourceConfig`/`TargetConfig`/`LoadConfig`) · `specs/dataio/schema-evolution-spec.md` · `skills/_shared/project-structure.md`.
