---
id: dataio.readers.jdbc-readers
title: JDBC Readers Spec
owner: EY
status: draft
target_path: src/readers/
owning_skill: framework-dev
backlog: []
provides: []
depends_on: []
generation_context:
  - specs/dataio/readers/jdbc-readers-spec.md
acceptance:
  - "pytest tests/unit/test_jdbc_readers.py"
regeneration: scaffold-then-edit
---

# JDBC Readers Spec

## 1. Purpose

Implement the **Reader protocol** for JDBC data sources, enabling the framework to read from relational databases (SQL Server, PostgreSQL, Oracle, MySQL, and other JDBC-compliant databases).

**Supported databases:**
1. **SQL Server** — Microsoft SQL Server (common in insurance: PolicyAdmin, claims systems)
2. **PostgreSQL** — Open-source RDBMS
3. **Oracle** — Enterprise database (common in insurance: Guidewire, Duck Creek)
4. **MySQL** — Open-source RDBMS
5. **Generic JDBC** — Any JDBC-compliant database

**Key capabilities:**
* Query-based reads (custom SQL)
* Table-based reads (full table or column subset)
* Pushdown predicates (WHERE clause to database)
* Partitioned reads for performance (column-based partitioning)
* Connection pooling and credential management
* Secret management via Databricks Secrets

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Implements Reader protocol from engine-contracts-spec
* Returns PySpark DataFrame
* Supports batch reads (not streaming)
* ABC audit hooks for read operations

---

## 2. Inputs

### 2.1 Requirements Sources
* **PROJECT_CONTEXT.md §4** — architecture (Reader protocol, ABC framework)
* **ROADMAP.md Phase 0** — JDBC readers are Wave 1 foundation
* **metadata-models-spec.md** — Feed metadata model
* **engine-contracts-spec.md** — Reader protocol definition
* **Backlog tasks:** DATAIO-002, READER-002

### 2.2 Design Constraints
* **Protocol compliance** — implement Reader protocol (read, supports_format)
* **PySpark JDBC API** — use spark.read.format("jdbc")
* **Secret management** — retrieve credentials from Databricks Secrets
* **Performance** — use partitioning for large tables
* **Error handling** — clear messages for connection failures, query errors

---

## 3. Procedure

### 3.1 Base JDBCReader Abstract Class

**Purpose:** Common logic for all JDBC readers

```python
# dataio/readers/jdbc_readers.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pyspark.sql import DataFrame, SparkSession

from core.metadata import Feed, SourceFormat
from core.contracts import Reader
from dataio.readers import register_reader

class JDBCReader(Reader, ABC):
    """
    Abstract base class for JDBC-based readers.
    
    Subclasses implement database-specific connection properties.
    """
    
    @abstractmethod
    def _get_jdbc_url(self, feed: Feed) -> str:
        """Return JDBC connection URL."""
        pass
    
    @abstractmethod
    def _get_driver_class(self) -> str:
        """Return JDBC driver class name."""
        pass
    
    @abstractmethod
    def _get_default_options(self) -> Dict[str, Any]:
        """Return default JDBC options."""
        pass
    
    def read(self, spark: SparkSession, feed: Feed) -> DataFrame:
        """
        Read from JDBC source as DataFrame.
        
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
        
        # Get JDBC URL and credentials
        jdbc_url = self._get_jdbc_url(feed)
        user, password = self._get_credentials(feed)
        
        # Merge default options with feed options
        options = {
            **self._get_default_options(),
            **feed.file_format_options,  # JDBC uses same field for options
            "driver": self._get_driver_class(),
            "user": user,
            "password": password
        }
        
        # Determine read mode: query or table
        if "query" in feed.file_format_options:
            # Custom SQL query
            options["query"] = feed.file_format_options["query"]
        elif "dbtable" in feed.file_format_options:
            # Table name
            options["dbtable"] = feed.file_format_options["dbtable"]
        else:
            # Default: use source_location as table name
            options["dbtable"] = feed.source_location
        
        # Read data
        try:
            df = spark.read.format("jdbc") \
                .option("url", jdbc_url) \
                .options(**options) \
                .load()
            
            return df
            
        except Exception as e:
            raise ValueError(
                f"Failed to read from JDBC source {feed.source_location}: {e}"
            ) from e
    
    def _get_credentials(self, feed: Feed) -> tuple[str, str]:
        """
        Retrieve JDBC credentials from Databricks Secrets.
        
        Args:
            feed: Feed configuration
            
        Returns:
            tuple: (username, password)
            
        Raises:
            ValueError: If secret_scope or secret_keys not provided
        """
        from pyspark.dbutils import DBUtils
        
        spark = SparkSession.getActiveSession()
        if not spark:
            raise ValueError("No active SparkSession")
        
        dbutils = DBUtils(spark)
        
        # Get secret scope and keys from feed options
        secret_scope = feed.file_format_options.get("secret_scope")
        user_key = feed.file_format_options.get("secret_user_key", "jdbc_user")
        password_key = feed.file_format_options.get("secret_password_key", "jdbc_password")
        
        if not secret_scope:
            raise ValueError("JDBC reader requires 'secret_scope' in file_format_options")
        
        # Retrieve credentials
        try:
            user = dbutils.secrets.get(scope=secret_scope, key=user_key)
            password = dbutils.secrets.get(scope=secret_scope, key=password_key)
            return user, password
        except Exception as e:
            raise ValueError(f"Failed to retrieve credentials from secret scope: {e}") from e
    
    def supports_format(self, source_format: str) -> bool:
        """Check if this reader supports the given format."""
        return source_format.lower() in [
            "sqlserver", "postgres", "oracle", "mysql", "jdbc"
        ]
```

---

### 3.2 SQL Server Reader

**Purpose:** Read from Microsoft SQL Server

```python
@register_reader(SourceFormat.SQL_SERVER)
class SQLServerReader(JDBCReader):
    """
    Reader for Microsoft SQL Server.
    
    JDBC driver: com.microsoft.sqlserver.jdbc.SQLServerDriver
    (included in Databricks Runtime)
    """
    
    def _get_jdbc_url(self, feed: Feed) -> str:
        """
        Construct SQL Server JDBC URL.
        
        Expected feed.source_location format:
        - "server:port/database" (e.g., "sqlserver.example.com:1433/PolicyDB")
        - OR provide full jdbc_url in file_format_options
        """
        if "jdbc_url" in feed.file_format_options:
            return feed.file_format_options["jdbc_url"]
        
        # Parse source_location
        parts = feed.source_location.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid source_location format: {feed.source_location}. "
                "Expected: server:port/database"
            )
        
        server_port = parts[0]
        database = parts[1]
        
        return f"jdbc:sqlserver://{server_port};databaseName={database}"
    
    def _get_driver_class(self) -> str:
        return "com.microsoft.sqlserver.jdbc.SQLServerDriver"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "fetchsize": "1000",  # Rows to fetch per round trip
            "queryTimeout": "0"   # 0 = no timeout
        }
```

**Usage:**
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

# Define feed
feed = Feed(
    feed_id="policy_sql_server",
    source_format=SourceFormat.SQL_SERVER,
    source_location="sqlserver.example.com:1433/PolicyDB",
    file_format_options={
        "dbtable": "dbo.Policy",
        "secret_scope": "jdbc_secrets",
        "secret_user_key": "sqlserver_user",
        "secret_password_key": "sqlserver_password"
    },
    ...
)

# Read
reader = get_reader(SourceFormat.SQL_SERVER)
df = reader.read(spark, feed)
```

---

### 3.3 PostgreSQL Reader

**Purpose:** Read from PostgreSQL

```python
@register_reader(SourceFormat.POSTGRES)
class PostgresReader(JDBCReader):
    """
    Reader for PostgreSQL.
    
    JDBC driver: org.postgresql.Driver
    (included in Databricks Runtime)
    """
    
    def _get_jdbc_url(self, feed: Feed) -> str:
        """
        Construct PostgreSQL JDBC URL.
        
        Expected feed.source_location format:
        - "server:port/database" (e.g., "postgres.example.com:5432/claims_db")
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
        
        return f"jdbc:postgresql://{server_port}/{database}"
    
    def _get_driver_class(self) -> str:
        return "org.postgresql.Driver"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "fetchsize": "1000",
            "batchsize": "1000"
        }
```

---

### 3.4 Oracle Reader

**Purpose:** Read from Oracle Database

```python
@register_reader(SourceFormat.ORACLE)
class OracleReader(JDBCReader):
    """
    Reader for Oracle Database.
    
    JDBC driver: oracle.jdbc.OracleDriver
    (included in Databricks Runtime)
    """
    
    def _get_jdbc_url(self, feed: Feed) -> str:
        """
        Construct Oracle JDBC URL.
        
        Expected feed.source_location format:
        - "server:port/service_name" (e.g., "oracle.example.com:1521/ORCL")
        - OR "server:port:sid" for SID-based connection
        """
        if "jdbc_url" in feed.file_format_options:
            return feed.file_format_options["jdbc_url"]
        
        parts = feed.source_location.split("/")
        if len(parts) == 2:
            # Service name format
            server_port = parts[0]
            service_name = parts[1]
            return f"jdbc:oracle:thin:@//{server_port}/{service_name}"
        else:
            # SID format (deprecated but still used)
            return f"jdbc:oracle:thin:@{feed.source_location}"
    
    def _get_driver_class(self) -> str:
        return "oracle.jdbc.OracleDriver"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "fetchsize": "1000"
        }
```

---

### 3.5 MySQL Reader

**Purpose:** Read from MySQL

```python
@register_reader(SourceFormat.MYSQL)
class MySQLReader(JDBCReader):
    """
    Reader for MySQL.
    
    JDBC driver: com.mysql.jdbc.Driver
    (included in Databricks Runtime)
    """
    
    def _get_jdbc_url(self, feed: Feed) -> str:
        """Construct MySQL JDBC URL."""
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
        
        return f"jdbc:mysql://{server_port}/{database}"
    
    def _get_driver_class(self) -> str:
        return "com.mysql.jdbc.Driver"
    
    def _get_default_options(self) -> Dict[str, Any]:
        return {
            "fetchsize": "1000"
        }
```

---

### 3.6 Partitioned Reads (Performance Optimization)

**Purpose:** Parallelize JDBC reads across executors

```python
# Example: Partitioned read for large tables
feed = Feed(
    feed_id="large_policy_table",
    source_format=SourceFormat.SQL_SERVER,
    source_location="sqlserver.example.com:1433/PolicyDB",
    file_format_options={
        "dbtable": "dbo.Policy",
        "secret_scope": "jdbc_secrets",
        
        # Partitioning options (for parallel reads)
        "partitionColumn": "policy_id",  # Numeric column for partitioning
        "lowerBound": "1",               # Min value
        "upperBound": "1000000",         # Max value
        "numPartitions": "10"            # Number of parallel reads
    },
    ...
)

# PySpark will issue 10 parallel queries:
# SELECT * FROM dbo.Policy WHERE policy_id >= 1 AND policy_id < 100000
# SELECT * FROM dbo.Policy WHERE policy_id >= 100000 AND policy_id < 200000
# ...
```

---

### 3.7 Custom SQL Queries

**Purpose:** Read using custom SQL instead of full table

```python
# Query-based read
feed = Feed(
    feed_id="active_policies",
    source_format=SourceFormat.SQL_SERVER,
    source_location="sqlserver.example.com:1433/PolicyDB",
    file_format_options={
        "secret_scope": "jdbc_secrets",
        
        # Custom SQL query
        "query": """
            (SELECT policy_id, policy_number, status, effective_date
             FROM dbo.Policy
             WHERE status = 'Active'
               AND effective_date >= '2024-01-01') AS active_policies
        """
    },
    ...
)

# Note: Query must be wrapped in parentheses and aliased
```

---

## 4. Outputs

### 4.1 Deliverables
* **`dataio/readers/jdbc_readers.py`** — JDBCReader base class + 5 implementations
* **`dataio/readers/__init__.py`** — Factory registration (extends pattern)
* **Unit tests** — test each reader with mock connections
* **Integration tests** — test reading from test databases

### 4.2 Downstream Consumption
* **IngestionEngine** — uses get_reader(SourceFormat.SQL_SERVER) to read operational data
* **Config-driven pipelines** — YAML configs specify source_format: sqlserver

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
* **Connection failure** — raise ValueError with connection details (without credentials)
* **Query error** — raise ValueError with SQL error message
* **Secret not found** — raise ValueError with secret scope/key
* **Driver not found** — raise ValueError with driver class name

### 5.2 Edge Cases
* **Large tables** — use partitioned reads (partitionColumn, numPartitions)
* **Complex queries** — wrap in parentheses and alias: `(SELECT ...) AS subquery`
* **Special characters in password** — Databricks Secrets handles encoding
* **Null values** — PySpark handles NULL → None conversion
* **Schema mismatch** — PySpark infers schema from JDBC metadata

### 5.3 Performance Considerations
* **Partitioned reads** — parallelize across executors for large tables
* **Pushdown predicates** — use WHERE clause in query (executed on database)
* **Column projection** — specify columns in query (don't SELECT *)
* **fetchsize** — tune for network latency vs. memory usage
* **Connection pooling** — PySpark handles connection pool internally

---

## 6. ABC Hooks

### 6.1 Audit
* **Read operations** — audit JDBC queries:
  ```python
  abc_sdk.audit(
      event="jdbc_read_start",
      feed_id=feed.feed_id,
      jdbc_url=jdbc_url,  # Without credentials
      table=feed.file_format_options.get("dbtable")
  )
  ```

### 6.2 Balance
* **Row count validation** — compare source and target:
  ```python
  abc_sdk.balance(
      check_type="jdbc_row_count",
      source="jdbc_source",
      target=target_table_fqn,
      source_count=df.count()
  )
  ```

### 6.3 Cost Tracking
* **DBU consumption** — track JDBC reads:
  ```python
  abc_sdk.cost_track(
      operation="jdbc_read",
      feed_id=feed.feed_id,
      rows_processed=df.count(),
      duration_seconds=elapsed_time
  )
  ```

---

## 7. Examples

### 7.1 Read Full Table from SQL Server
```python
from dataio.readers import get_reader
from core.metadata import Feed, SourceFormat

feed = Feed(
    feed_id="policy_master",
    source_format=SourceFormat.SQL_SERVER,
    source_location="sqlserver.example.com:1433/PolicyDB",
    file_format_options={
        "dbtable": "dbo.Policy",
        "secret_scope": "jdbc_secrets"
    },
    ...
)

reader = get_reader(SourceFormat.SQL_SERVER)
df = reader.read(spark, feed)

print(f"Read {df.count()} policies")
df.printSchema()
```

### 7.2 Read with Custom Query (Filtered Data)
```python
feed = Feed(
    feed_id="active_claims",
    source_format=SourceFormat.POSTGRES,
    source_location="postgres.example.com:5432/claims_db",
    file_format_options={
        "secret_scope": "jdbc_secrets",
        "query": """
            (SELECT claim_id, policy_id, claim_date, claim_amount
             FROM claims
             WHERE claim_status = 'Open'
               AND claim_date >= CURRENT_DATE - INTERVAL '30 days') AS recent_claims
        """
    },
    ...
)

reader = get_reader(SourceFormat.POSTGRES)
df = reader.read(spark, feed)
```

### 7.3 Partitioned Read (Large Table)
```python
feed = Feed(
    feed_id="large_transaction_table",
    source_format=SourceFormat.ORACLE,
    source_location="oracle.example.com:1521/ORCL",
    file_format_options={
        "dbtable": "TRANSACTIONS",
        "secret_scope": "jdbc_secrets",
        
        # Partition for parallel reads
        "partitionColumn": "transaction_id",
        "lowerBound": "1",
        "upperBound": "10000000",
        "numPartitions": "20"  # 20 parallel connections
    },
    ...
)

reader = get_reader(SourceFormat.ORACLE)
df = reader.read(spark, feed)  # 20 executors read in parallel
```

---

## 8. Acceptance Criteria

### 8.1 Unit Tests (>80% coverage)
1. **SQL Server reader** — test URL construction, driver class
2. **PostgreSQL reader** — test URL construction
3. **Oracle reader** — test service name and SID formats
4. **MySQL reader** — test URL construction
5. **Credential retrieval** — test Databricks Secrets integration
6. **Error handling** — test connection failure, invalid query
7. **Partitioned reads** — test partitionColumn options

### 8.2 Integration Tests
* **SQL Server** — read from test SQL Server database
* **PostgreSQL** — read from test Postgres database
* **Query-based reads** — test custom SQL queries
* **Partitioned reads** — verify parallel execution

### 8.3 Performance Tests
* **Large table read** — test partitioned read (10M+ rows)
* **Query pushdown** — verify WHERE clause executed on database

---

## 9. References

### 9.1 Internal Documents
* `engine-contracts-spec.md` — Reader protocol
* `metadata-models-spec.md` — Feed metadata
* `file-readers-spec.md` — Base Reader pattern

### 9.2 External Standards
* **JDBC API** — https://docs.oracle.com/javase/8/docs/technotes/guides/jdbc/
* **PySpark JDBC** — https://spark.apache.org/docs/latest/sql-data-sources-jdbc.html

### 9.3 Databricks Documentation
* **JDBC data sources** — https://docs.databricks.com/aws/en/external-data/jdbc.html
* **Databricks Secrets** — https://docs.databricks.com/aws/en/security/secrets/index.html

---

## 10. Decisions Made

1. **Base class** — JDBCReader abstract class for common logic
2. **Secret management** — use Databricks Secrets for credentials
3. **URL format** — source_location as "server:port/database"
4. **Query wrapping** — custom queries wrapped in `(SELECT ...) AS alias`
5. **Partitioning** — support partitionColumn for parallel reads
6. **Driver classes** — use Databricks Runtime bundled drivers
7. **fetchsize** — default 1000 rows per fetch
8. **Credential keys** — default to "jdbc_user" and "jdbc_password"

---

**End of JDBC Readers Spec (Approved)**
