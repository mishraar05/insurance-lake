---
id: dataio.readers.odbc-readers
title: ODBC Readers Spec
owner: EY
status: draft
target_path: src/readers/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/readers/odbc-readers-spec.md
acceptance:
  - "pytest tests/unit/test_odbc_readers.py"
regeneration: scaffold-then-edit
---

# ODBC Readers Spec

## 1. Purpose

Implement the **Reader protocol** for ODBC data sources, enabling the framework to read from legacy databases and proprietary systems not covered by JDBC.

**Supported scenarios:**
* **Legacy databases** — AS/400, Informix, Sybase, DB2
* **Proprietary systems** — Mainframe databases, custom databases
* **Windows-specific databases** — Microsoft Access
* **NoSQL with ODBC drivers** — Cassandra, MongoDB (if ODBC driver available)

**Key capabilities:**
* **ODBC driver support** — use installed ODBC drivers
* **Connection string-based** — flexible connection configuration
* **Query and table-based reads** — custom SQL or full table
* **Secret management** — retrieve credentials from Databricks Secrets

**Use cases:**
* Mainframe policy systems (AS/400)
* Legacy claim systems (Informix, Sybase)
* Vendor databases with ODBC drivers only
* Microsoft Access databases (business user reports)

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements Reader protocol from engine-contracts-spec
* Uses pyodbc for ODBC connectivity
* Returns PySpark DataFrame
* ABC audit hooks for read operations

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (Reader protocol, ABC framework)
* **ROADMAP.md Phase 0** — ODBC readers are Wave 1 optional capability
* **metadata-models-spec.md** — Feed metadata model
* **engine-contracts-spec.md** — Reader protocol definition
* **Backlog tasks:** DATAIO-006, READER-006

### 2.2 Design Constraints
* **Protocol compliance** — implement Reader protocol (read, supports_format)
* **pyodbc integration** — use pyodbc for ODBC connections
* **Driver installation** — ODBC drivers must be pre-installed on cluster
* **Secret management** — retrieve credentials from Databricks Secrets
* **Performance** — ODBC typically slower than JDBC (no native Spark support)

---

## 3. Procedure

### 3.1 ODBCReader Implementation

**Purpose:** Read from ODBC data sources via pyodbc

```python
# dataio/readers/odbc_readers.py
from typing import Dict, Any, List
import pyodbc
from pyspark.sql import DataFrame, SparkSession

from core.metadata import Feed, SourceFormat
from core.contracts import Reader
from dataio.readers import register_reader

@register_reader(SourceFormat.ODBC)
class ODBCReader(Reader):
    """
    Reader for ODBC data sources.
    
    Requires:
    - ODBC drivers installed on cluster
    - pyodbc library installed (via cluster init script)
    
    Supported databases:
    - AS/400, Informix, Sybase, DB2
    - Microsoft Access
    - Any database with ODBC driver
    """
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read from ODBC source as DataFrame.
        
        Args:
            spark: Active SparkSession
            feed: Feed configuration
            
        Returns:
            DataFrame with source data
            
        Raises:
            ValueError: If connection fails or query invalid
        """
        # Validate format
        if not self.supports_format(feed.source_format.value):
            raise ValueError(
                f"{self.__class__.__name__} does not support format: {feed.source_format}"
            )
        
        # Get connection string
        connection_string = self._build_connection_string(feed)
        
        # Determine query or table
        if "query" in feed.file_format_options:
            query = feed.file_format_options["query"]
        elif "dbtable" in feed.file_format_options:
            table_name = feed.file_format_options["dbtable"]
            query = f"SELECT * FROM {table_name}"
        else:
            # Use source_location as table name
            query = f"SELECT * FROM {feed.source_location}"
        
        # Fetch data via pyodbc
        try:
            records = self._fetch_via_pyodbc(connection_string, query)
            
            # Convert to DataFrame
            if not records:
                raise ValueError(f"No data returned from ODBC query: {query}")
            
            df = spark.createDataFrame(records)
            return df
            
        except Exception as e:
            raise ValueError(
                f"Failed to read from ODBC source {feed.source_location}: {e}"
            ) from e
    
    def _build_connection_string(self, feed: Feed) -> str:
        """
        Build ODBC connection string from feed configuration.
        
        Options:
        1. Full connection string in file_format_options['connection_string']
        2. Build from components: driver, server, database, uid, pwd
        
        Args:
            feed: Feed configuration
            
        Returns:
            ODBC connection string
        """
        from pyspark.dbutils import DBUtils
        
        # Option 1: Full connection string provided
        if "connection_string" in feed.file_format_options:
            conn_str = feed.file_format_options["connection_string"]
            
            # Replace {username} and {password} with secrets
            secret_scope = feed.file_format_options.get("secret_scope")
            if secret_scope:
                spark = SparkSession.getActiveSession()
                dbutils = DBUtils(spark)
                
                username = dbutils.secrets.get(scope=secret_scope, key="odbc_username")
                password = dbutils.secrets.get(scope=secret_scope, key="odbc_password")
                
                conn_str = conn_str.replace("{username}", username)
                conn_str = conn_str.replace("{password}", password)
            
            return conn_str
        
        # Option 2: Build from components
        driver = feed.file_format_options.get("odbc_driver")
        server = feed.file_format_options.get("server")
        database = feed.file_format_options.get("database")
        
        if not all([driver, server, database]):
            raise ValueError(
                "ODBC reader requires either 'connection_string' or "
                "'odbc_driver', 'server', and 'database' in file_format_options"
            )
        
        # Retrieve credentials
        secret_scope = feed.file_format_options.get("secret_scope")
        if not secret_scope:
            raise ValueError("ODBC reader requires 'secret_scope' for credentials")
        
        spark = SparkSession.getActiveSession()
        dbutils = DBUtils(spark)
        username = dbutils.secrets.get(scope=secret_scope, key="odbc_username")
        password = dbutils.secrets.get(scope=secret_scope, key="odbc_password")
        
        # Build connection string
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
        )
        
        return conn_str
    
    def _fetch_via_pyodbc(self, connection_string: str, query: str) -> List[Dict[str, Any]]:
        """
        Fetch data using pyodbc.
        
        Args:
            connection_string: ODBC connection string
            query: SQL query to execute
            
        Returns:
            list: Records as dicts
        """
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            # Convert to list of dicts
            records = []
            for row in rows:
                record = {columns[i]: row[i] for i in range(len(columns))}
                records.append(record)
            
            return records
            
        finally:
            cursor.close()
            conn.close()
    
    def supports_format(self, source_format: str) -> bool:
        """Check if this reader supports the given format."""
        return source_format.lower() == "odbc"
```

---

## 4. Examples

### 4.1 Read from AS/400 (IBM i)
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

feed = Feed(
    feed_id="as400_policy_data",
    source_format=SourceFormat.ODBC,
    source_location="POLMAST",  # Table name
    file_format_options={
        "odbc_driver": "IBM i Access ODBC Driver",
        "server": "as400.example.com",
        "database": "PRODLIB",
        "secret_scope": "odbc_secrets"
    },
    ...
)

reader = get_reader(SourceFormat.ODBC)
df = reader.read(spark, feed)
```

### 4.2 Read with Full Connection String
```python
feed = Feed(
    feed_id="informix_claims",
    source_format=SourceFormat.ODBC,
    source_location="claims",  # Table name
    file_format_options={
        "connection_string": (
            "DRIVER={IBM INFORMIX ODBC DRIVER};"
            "HOST=informix.example.com;"
            "SERVICE=1526;"
            "DATABASE=claimsdb;"
            "UID={username};"
            "PWD={password};"
        ),
        "secret_scope": "odbc_secrets"
    },
    ...
)

reader = get_reader(SourceFormat.ODBC)
df = reader.read(spark, feed)
```

### 4.3 Read with Custom Query
```python
feed = Feed(
    feed_id="sybase_active_policies",
    source_format=SourceFormat.ODBC,
    source_location="",  # Not used (query provided)
    file_format_options={
        "odbc_driver": "Adaptive Server Enterprise",
        "server": "sybase.example.com",
        "database": "PolicyDB",
        "secret_scope": "odbc_secrets",
        "query": """
            SELECT policy_id, policy_number, status, effective_date
            FROM policies
            WHERE status = 'Active'
              AND effective_date >= '2024-01-01'
        """
    },
    ...
)

reader = get_reader(SourceFormat.ODBC)
df = reader.read(spark, feed)
```

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
* **Driver not found** — raise ValueError with driver name and installation instructions
* **Connection failure** — raise ValueError with connection details (without credentials)
* **Query error** — raise ValueError with SQL error message
* **Secret not found** — raise ValueError with secret scope/key

### 5.2 Edge Cases
* **Large result sets** — pyodbc loads all data into memory (not suitable for huge tables)
* **Driver compatibility** — ODBC drivers must be compatible with cluster OS
* **Null values** — pyodbc handles NULL → None conversion
* **Data types** — PySpark infers types from pyodbc result set

### 5.3 Performance Considerations
* **Not optimized for Spark** — ODBC reads are single-threaded (no parallelization)
* **Use for small tables only** — recommend < 1M rows
* **For large tables** — consider JDBC if available, or export to files first
* **Network latency** — ODBC over network can be slow

---

## 6. Acceptance Criteria

### 6.1 Unit Tests (>80% coverage)
1. **Connection string** — test building from components and from full string
2. **Credential retrieval** — test Databricks Secrets integration
3. **Query execution** — test pyodbc query execution
4. **Error handling** — test connection failure, invalid query

### 6.2 Integration Tests
* **Test ODBC source** — test reading from test ODBC database (if available)
* **Mock pyodbc** — test with mocked pyodbc connection

---

## 7. References

### 7.1 Internal Documents
* `engine-contracts-spec.md` — Reader protocol
* `metadata-models-spec.md` — Feed metadata
* `jdbc-readers-spec.md` — Similar pattern

### 7.2 External Standards
* **pyodbc** — https://github.com/mkleehammer/pyodbc
* **ODBC** — https://en.wikipedia.org/wiki/Open_Database_Connectivity

### 7.3 Databricks Documentation
* **pyodbc on Databricks** — https://docs.databricks.com/external-data/odbc.html

---

## 8. Decisions Made

1. **pyodbc library** — use pyodbc for ODBC connectivity
2. **Single-threaded** — no parallelization (ODBC limitation)
3. **Small tables only** — recommend < 1M rows (memory-bound)
4. **Connection string** — support full string or component-based
5. **Credential placeholders** — {username} and {password} replaced from secrets
6. **Driver installation** — ODBC drivers installed via cluster init script

---

**End of ODBC Readers Spec (Approved)**
