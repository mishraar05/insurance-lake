# [Component Name] Specification

**Spec ID:** [EPIC-###]  
**Title:** [Component Name]  
**Owner:** EY  
**Date:** [YYYY-MM-DD]  
**Status:** Draft | Review | Approved | Implemented  
**Depends On:** [List spec IDs or "None"]

---

## 1. Purpose

**What problem does this solve?**

[Clear description of the business/technical problem this component addresses]

**Scope:**
- In scope: [List what IS included]
- Out of scope: [List what is NOT included]

---

## 2. Requirements

### Functional Requirements
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

### Non-Functional Requirements
- **Performance:** [Response time, throughput, concurrency]
- **Scalability:** [Data volume, growth expectations]
- **Reliability:** [SLA, error tolerance, recovery]
- **Security:** [Authentication, authorization, encryption]
- **Maintainability:** [Code quality, documentation, testability]
- **Extensibility:** [Customer customization, config-driven behavior]

---

## 3. Architecture

### High-Level Design

```
[ASCII diagram or description of component architecture]
```

### Components
- **Component 1:** [Description]
- **Component 2:** [Description]

### SOLID Principles & Design Patterns

**This component follows SOLID principles:**

**Single Responsibility (SRP):**
- Each class/module has ONE reason to change
- [Describe how this component separates concerns]

**Open/Closed (OCP):**
- Open for extension, closed for modification
- [Describe extension points - strategies, plugins, configs]

**Liskov Substitution (LSP):**
- Subclasses are substitutable for base classes
- [Describe interface hierarchies and substitutability]

**Interface Segregation (ISP):**
- Many client-specific interfaces > one fat interface
- [Describe how interfaces are segregated by client needs]

**Dependency Inversion (DIP):**
- Depend on abstractions, not concretions
- [Describe dependency injection and abstraction usage]

**Applicable Design Patterns:**

1. **[Pattern Name]**: [Why it applies to this component]
   - Example: Strategy Pattern for load strategies
   - Example: Factory Pattern for reader creation
   - Example: Template Method for engine workflows

2. **[Pattern Name]**: [Why it applies]

**Extensibility Strategy:**
- Config-driven customization vs. code-driven
- Customer-specific behavior injection points
- Multi-tenant design considerations

### Data Flow
1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## 4. Data Model

### Tables

#### Table: [table_name]
```sql
CREATE TABLE [catalog].[schema].[table_name] (
  [column1] [type] COMMENT '[description]',
  [column2] [type] COMMENT '[description]',
  ...
) USING DELTA
[PARTITIONED BY ...]
[CLUSTER BY ...]
COMMENT '[table purpose]';
```

**Relationships:**
- Foreign key to [other_table] on [column]
- Referenced by [dependent_table]

---

## 5. Implementation Details

### Code Structure
```
[Directory/module structure]
```

### Key Functions/Classes

#### Function: [function_name]
**Purpose:** [What it does]  
**Inputs:** [Parameters]  
**Outputs:** [Return value]  
**Algorithm:**
1. [Step 1]
2. [Step 2]

**SOLID Compliance:**
- SRP: [How this function has single responsibility]
- DIP: [How dependencies are abstracted]

### Dependencies
- **External libraries:** [List packages]
- **Databricks features:** [Lakeflow, Unity Catalog, etc.]
- **Internal modules:** [Other SDK components]

**Dependency Injection:**
```python
# Example showing DIP
def __init__(
    self,
    dependency1: AbstractInterface,  # Not concrete implementation
    dependency2: AbstractInterface
):
    self._dep1 = dependency1
    self._dep2 = dependency2
```

---

## 6. Validation Rules

1. **Rule 1:** [Validation logic]
   - **On failure:** [Error message / action]

2. **Rule 2:** [Validation logic]
   - **On failure:** [Error message / action]

---

## 7. Error Handling

### Error Scenarios

| Error | Cause | Message | Recovery Action |
|-------|-------|---------|--------------------|
| [ErrorType1] | [What triggers it] | "[Exact message]" | [How to recover] |
| [ErrorType2] | [What triggers it] | "[Exact message]" | [How to recover] |

---

## 8. Testing

### Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]
- [ ] SOLID compliance verified (SRP, OCP, LSP, ISP, DIP)

### Test Scenarios

#### Scenario 1: [Happy path]
**Given:** [Initial state]  
**When:** [Action]  
**Then:** [Expected result]

#### Scenario 2: [Error case]
**Given:** [Initial state]  
**When:** [Action]  
**Then:** [Expected error]

### SOLID Testing

**SRP Tests:**
- Each test class tests ONE component/responsibility
- Tests verify single reason to change

**OCP Tests:**
- Tests verify extension without modification
- New strategies/behaviors work without changing base

**LSP Tests:**
- Base class tests run against all subclasses
- Subclasses are substitutable for base

**ISP Tests:**
- Tests verify clients only depend on methods they use
- No dependencies on unused interface methods

**DIP Tests:**
- Tests use mocks/stubs for dependencies
- Tests verify abstraction boundaries

---

## 9. Examples

### Example 1: [Use case name]

```python
# Sample code
```

**Input:**
```
[Sample input data]
```

**Output:**
```
[Expected output]
```

### SOLID Example: Good vs. Bad

**BAD (Violates SOLID):**
```python
# Example showing anti-patterns
class GodClass:
    def do_everything(self):
        # Reads, validates, transforms, writes, logs (violates SRP)
        # Hard-coded dependencies (violates DIP)
        pass
```

**GOOD (Follows SOLID):**
```python
# Example showing proper separation
class Reader:
    """Single responsibility: reading data"""
    def read(self, source: str) -> DataFrame:
        pass

class Validator:
    """Single responsibility: validation"""
    def validate(self, df: DataFrame, schema: Schema) -> bool:
        pass

class Processor:
    """Orchestrates with injected dependencies (DIP)"""
    def __init__(
        self,
        reader: Reader,  # Abstraction, not concrete
        validator: Validator  # Abstraction, not concrete
    ):
        self._reader = reader
        self._validator = validator
    
    def process(self, source: str):
        df = self._reader.read(source)
        self._validator.validate(df, schema)
        return df
```

---

## 10. References

- [Link 1 - Related spec]
- [Link 2 - Databricks docs]
- [Link 3 - ADR or decision log]
- [Link 4 - Backlog task]
- SOLID Principles: Robert C. Martin (Clean Code, Clean Architecture)
- Design Patterns: Gang of Four (GoF)

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| [YYYY-MM-DD] | [Name] | Initial draft |
