# [Pattern Name] Implementation Pattern

**Spec ID:** [EPIC-###]  
**Title:** [Pattern Name] Pattern  
**Owner:** EY  
**Date:** [YYYY-MM-DD]  
**Status:** Draft | Review | Approved | Implemented  
**Used By:** [Engines that use this pattern]

---

## 1. Purpose

**What is this pattern?**

[Description of the pattern and when to use it]

**Use Cases:**
- Use case 1
- Use case 2

---

## 2. Pattern Overview

### Problem
[What problem does this pattern solve?]

### Solution
[How does this pattern solve it?]

### Trade-offs
- **Pros:** [Benefits]
- **Cons:** [Limitations]

---

## 3. Implementation

### Declarative (Lakeflow)

```sql
-- SQL code for declarative implementation
CREATE OR REFRESH STREAMING TABLE [target]
AS
  [pattern SQL];
```

### Non-Declarative (classic batch PySpark)

```python
# Python code for non-declarative implementation
```

---

## 4. Configuration

### Required Metadata

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| [field1] | STRING | [Description] | "value" |
| [field2] | INT | [Description] | 100 |

---

## 5. Behavior

### Data Flow
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Edge Cases
- **Case 1:** [How handled]
- **Case 2:** [How handled]

---

## 6. Testing

### Test Scenarios

#### Scenario 1: [Normal operation]
**Given:** [Setup]  
**When:** [Action]  
**Then:** [Expected result]

#### Scenario 2: [Edge case]
**Given:** [Setup]  
**When:** [Action]  
**Then:** [Expected result]

---

## 7. Examples

### Example 1: [Real-world use]

**Setup:**
```sql
-- Sample source data
```

**Implementation:**
```sql
-- Pattern applied
```

**Result:**
```sql
-- Output data
```

---

## 8. References

- [Related patterns]
- [Databricks docs on this pattern]
- [Backlog tasks]
