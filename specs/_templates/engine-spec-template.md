# [Engine Name] Specification

**Spec ID:** [EPIC-###, EPIC-###, ...]  
**Title:** [Engine Name] - [Brief description]  
**Owner:** EY  
**Date:** [YYYY-MM-DD]  
**Status:** Draft | Review | Approved | Implemented  
**Depends On:** [List spec IDs]

---

## 1. Purpose

**What does this engine do?**

[Description of the engine's role in the framework]

**Key Features:**
- Feature 1
- Feature 2
- Feature 3

---

## 2. Architecture

### Engine Components

```
┌─────────────────────────────────────┐
│  [Component Diagram]                │
│                                     │
│  Config → Reader → Processor → Writer│
└─────────────────────────────────────┘
```

### SOLID Principles & Design Patterns

**Architecture follows SOLID principles:**

**Single Responsibility (SRP):**
- Each component (Reader, Processor, Writer) has ONE responsibility
- Config loading is separate from business logic
- Validation is separate from transformation

**Open/Closed (OCP):**
- Extensible via strategy pattern (e.g., load strategies: Append, SCD1, SCD2)
- New strategies can be added without modifying engine core
- Closed for modification, open for extension

**Liskov Substitution (LSP):**
- All readers implement common `Reader` interface
- Any reader subclass works interchangeably
- All strategies implement common `LoadStrategy` interface

**Interface Segregation (ISP):**
- Separate interfaces for batch vs. streaming readers
- Clients depend only on methods they need
- No fat interfaces with unused methods

**Dependency Inversion (DIP):**
- Engine depends on abstractions (interfaces), not concrete implementations
- Readers, strategies, and processors are injected
- Testable via dependency injection

**Key Design Patterns:**

1. **Strategy Pattern**: 
   - Load strategies (Append, SCD1, SCD2, Full Refresh)
   - Transformation strategies (customer-specific logic)
   
2. **Factory Pattern**:
   - Reader factory creates appropriate reader based on source type
   - Strategy factory creates appropriate strategy based on load pattern
   
3. **Template Method**:
   - Engine defines workflow template
   - Subclasses implement specific steps (read, transform, write)
   
4. **Dependency Injection**:
   - Config, readers, strategies injected into engine
   - Enables testing and customer-specific customization

**Component Structure:**
```python
# Example architecture following SOLID

class EngineTemplate(ABC):
    """Template for engine workflow (Template Method pattern)"""
    
    def __init__(
        self,
        config_loader: ConfigLoader,  # DIP - depend on abstraction
        reader: Reader,                # DIP - depend on abstraction
        strategy: LoadStrategy         # DIP - depend on abstraction
    ):
        self._config = config_loader
        self._reader = reader
        self._strategy = strategy
    
    def execute(self, feed_id: str) -> dict:
        """Template method - fixed workflow"""
        # 1. Load config
        config = self._config.load(feed_id)
        
        # 2. Read (delegated to reader)
        df = self._reader.read(config)
        
        # 3. Transform (implemented by subclass)
        df = self.transform(df, config)
        
        # 4. Write (delegated to strategy)
        result = self._strategy.write(df, config.target_table)
        
        return result
    
    @abstractmethod
    def transform(self, df: DataFrame, config: dict) -> DataFrame:
        """Subclasses implement transformation logic"""
        pass
```

**Extensibility:**
- Customer-specific config via `CustomerConfig` abstraction
- Strategy pattern allows customer-specific load patterns
- Factory pattern enables dynamic reader/strategy selection
- Config-driven customization (no code changes for new customers)

### Processing Modes
1. **Batch:** [Description]
2. **Streaming:** [Description]
3. **Hybrid:** [Description]

---

## 3. Configuration

### Configuration Tables

#### Table: [engine_config]
```sql
CREATE TABLE insurelake_config.config.[engine_config] (
  config_id STRING PRIMARY KEY,
  [field1] STRING,
  [field2] INT,
  ...
) USING DELTA;
```

### Configuration Model

```python
@dataclass
class [Engine]Config:
    config_id: str
    [field1]: str
    [field2]: int
    ...
```

---

## 4. Processing Logic

### Step 1: [Name]
**Purpose:** [What this step does]

**Algorithm:**
```
1. [Substep]
2. [Substep]
3. [Substep]
```

**Code Pattern:**
```python
# Pseudocode or actual implementation
```

### Step 2: [Name]
[Similar structure]

---

## 5. Patterns Supported

### Pattern 1: [Pattern name]
**When to use:** [Conditions]  
**Implementation:**
```sql
-- Sample SQL or Python
```

### Pattern 2: [Pattern name]
[Similar structure]

---

## 6. ABC Integration

### Audit
- **Logged:** [What gets logged]
- **Location:** `abc_catalog.abc.audit`

### Balance
- **Counts tracked:** [What gets counted]
- **Location:** `abc_catalog.abc.balance`

### Control
- **Validation:** [What gets validated]
- **Location:** `abc_catalog.abc.control`

---

## 7. Error Handling & Recovery

### Failure Modes

| Failure | Detection | Recovery | Alert |
|---------|-----------|----------|-------|
| [Type 1] | [How detected] | [Recovery action] | [Alert mechanism] |
| [Type 2] | [How detected] | [Recovery action] | [Alert mechanism] |

---

## 8. Performance & Optimization

### Performance Targets
- **Throughput:** [Records per second/minute]
- **Latency:** [Processing time]
- **Concurrency:** [Parallel jobs]

### Optimization Techniques
1. [Technique 1]
2. [Technique 2]

---

## 9. Testing Strategy

### Unit Tests
- Test [component 1]
- Test [component 2]

**SOLID Testing:**
- **SRP**: Each test class tests ONE component (reader, strategy, engine)
- **OCP**: Tests verify extension points work without modifying base
- **LSP**: Base class tests run against all subclasses (substitutability)
- **ISP**: Tests verify clients only use methods they need
- **DIP**: Tests use mocks for dependencies (verify abstractions)

### Integration Tests
- End-to-end pipeline test
- Error scenario tests

### Performance Tests
- Volume test: [X records]
- Concurrency test: [Y parallel jobs]

---

## 10. Deployment

### Prerequisites
- Unity Catalog: [catalog.schema]
- Lakeflow: [Pipeline or Job]
- Permissions: [Required grants]

### Deployment Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## 11. Examples

### Example 1: [Common use case]

**Configuration:**
```json
{
  "config_id": "...",
  "field1": "..."
}
```

**Execution:**
```python
# Code
```

**Result:**
```
[Output description]
```

### SOLID Example: Good vs. Bad

**BAD (Violates SRP, DIP):**
```python
class IngestionEngine:
    def __init__(self):
        self.reader = CSVReader()  # Hard-coded, violates DIP
        self.strategy = SCD2Strategy()  # Hard-coded, violates DIP
    
    def ingest(self):
        df = self.reader.read()
        # ... validation, transformation, logging all in one method (violates SRP)
        self.strategy.write(df)
```

**GOOD (Follows SOLID):**
```python
class IngestionEngine:
    def __init__(
        self,
        reader: Reader,  # DIP - depend on abstraction
        strategy: LoadStrategy,  # DIP - depend on abstraction
        validator: SchemaValidator,  # SRP - separate validation
        logger: StructuredLogger  # SRP - separate logging
    ):
        self._reader = reader
        self._strategy = strategy
        self._validator = validator
        self._logger = logger
    
    def ingest(self, config: dict):
        # Each step delegates to single-responsibility components
        df = self._reader.read(config)
        self._validator.validate(df, config.schema)
        result = self._strategy.write(df, config.target)
        self._logger.log_result(result)
        return result
```

---

## 12. References

- [Related specs]
- [Databricks docs]
- [Backlog tasks]
- SOLID Principles: Robert C. Martin (Clean Code, Clean Architecture)
- Design Patterns: Gang of Four (GoF)
