---
id: framework-dev.create-unit-tests
name: Create Unit Tests
category: framework-dev
version: 0.1.0
maturity: exemplar
status: active
owner_role: Data Engineer
runtime: genie-code
build_order: 0
depends_on: []
backlog_ids: ['FND-013', 'TST-001', 'TST-002']
inputs: ['module_path', 'module_source']
outputs: ['test_module', 'coverage_report']
tools: ['genie-code', 'pytest']
---

# Create Unit Tests

> Automatically generate comprehensive unit tests for any Python module with pytest.

## Purpose / when to use

Use this skill whenever a new Python module or class is created or updated. It generates comprehensive pytest unit tests covering:

* **Happy path** - Normal execution with valid inputs
* **Edge cases** - Boundary conditions, empty inputs, nulls
* **Error cases** - Invalid inputs, exceptions, validation failures
* **Integration** - Tests involving external dependencies (mocked)
* **Coverage** - Aim for >80% code coverage

**Triggers**:
* After implementing any new module (e.g., FND-003 Config Loader)
* When module logic changes (update existing tests)
* Before merging to main branch
* As part of CI/CD pipeline

## Inputs (contract)

* `module_path` - Workspace path to the module to test (e.g., `/sdk/config_loader.py`)
* `module_source` - Optional: source code if not reading from file
* `test_framework` - Default: `pytest` (supports `unittest` as fallback)
* `coverage_target` - Default: 80% (minimum coverage threshold)

## Procedure (Genie-Code-ready steps)

1. **Read module source**
   - Parse Python module to identify: classes, methods, functions
   - Extract function signatures, docstrings, type hints
   - Identify dependencies (imports, external calls)

2. **Analyze test requirements**
   - For each class/function, determine:
     - Valid input combinations (happy path)
     - Invalid input combinations (error cases)
     - Edge cases (boundary conditions)
     - Dependencies that need mocking

3. **Generate test structure**
   - Create test file: `test_<module_name>.py`
   - Set up fixtures for common test data
   - Create test classes mirroring module structure
   - Group related tests together

4. **Write test cases**
   - **Happy path tests**: Test expected behavior with valid inputs
   - **Validation tests**: Test input validation and error messages
   - **Exception tests**: Test exception handling with \`pytest.raises\`
   - **Mock tests**: Mock external dependencies (Spark, databases, APIs)
   - **Edge case tests**: Empty inputs, null values, boundary conditions

5. **Add test fixtures**
   - Create reusable fixtures for common test data
   - Use \`@pytest.fixture\` for setup/teardown
   - Mock Spark sessions, database connections, file systems

6. **Generate assertions**
   - Validate return values match expectations
   - Check exception types and messages
   - Verify mock calls (call count, arguments)
   - Assert state changes (before/after)

7. **Add coverage configuration**
   - Create \`.coveragerc\` or \`pytest.ini\` config
   - Exclude test files from coverage
   - Set coverage thresholds

8. **Self-review**
   - Verify all public methods are tested
   - Check coverage meets threshold (>80%)
   - Ensure tests are independent (no order dependency)
   - Validate test names are descriptive

## Outputs (contract)

* \`test_module\` - Complete pytest test file with:
  - Test classes and methods
  - Fixtures for test data
  - Mocks for external dependencies
  - Assertions with clear error messages
* \`coverage_report\` - Coverage analysis showing:
  - Overall coverage percentage
  - Uncovered lines
  - Suggestions for additional tests
* \`pytest.ini\` - pytest configuration file

## Guardrails & policy

* **Independent tests**: Each test should be runnable in isolation
* **No hardcoded secrets**: Use fixtures or environment variables
* **Descriptive names**: Test names should explain what they test
  - Pattern: \`test_<method>_<scenario>_<expected_result>\`
  - Example: \`test_get_source_invalid_id_raises_not_found_error\`
* **Clear assertions**: Use specific assertions with helpful messages
* **Mock external I/O**: Never hit real databases, APIs, or file systems
* **Fast execution**: All tests should complete in <5 seconds
* **No flaky tests**: Tests must be deterministic (no random data, time dependencies)

## Govern hooks

* Self-review: see [[control.self-review]]
* Coverage check: Fail if coverage < threshold
* HITL gate: Required if module handles PII or financial data
* ABC audit: Log test execution to ABC control tables

## Test Structure Template

\`\`\`python
"""
Unit tests for <module_name>.

Tests cover:
- Happy path scenarios
- Input validation and error handling
- Edge cases and boundary conditions
- Integration with dependencies (mocked)

Coverage target: >80%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pyspark.sql import SparkSession
import sys

sys.path.append("/Workspace/Users/cleancoding109@gmail.com/insurance-lake")

from sdk import ConfigLoader
from sdk.models import SourceConfig
from sdk.exceptions import ConfigNotFoundError, ForeignKeyError

# ========== Fixtures ==========

@pytest.fixture
def mock_spark():
    """Mock Spark session for testing."""
    spark = Mock(spec=SparkSession)
    return spark

@pytest.fixture
def sample_source_row():
    """Sample source config row."""
    return {
        "source_id": "src_policy_mainframe",
        "source_name": "Policy System Mainframe",
        "source_type": "FILE",
        "source_system": "PolicyCenter",
        "connection_string": "s3://bucket/policy/",
        "file_format": "CSV",
        "business_domain": "POLICY",
        "pii_flag": False,
        "data_classification": "INTERNAL",
        "active_flag": True,
    }

# ========== Test Classes ==========

class TestConfigLoader:
    """Tests for ConfigLoader class."""
    
    def test_init_success(self, mock_spark):
        """Test ConfigLoader initialization with valid catalog/schema."""
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader(catalog="test_catalog", schema="test_schema")
            assert loader.catalog == "test_catalog"
            assert loader.schema == "test_schema"
    
    def test_init_no_spark_raises_error(self):
        """Test ConfigLoader initialization fails without Spark session."""
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=None):
            with pytest.raises(RuntimeError, match="No active Spark session"):
                ConfigLoader()
    
    def test_get_source_success(self, mock_spark, sample_source_row):
        """Test get_source returns SourceConfig for valid ID."""
        # Setup mock
        mock_df = Mock()
        mock_df.filter.return_value.collect.return_value = [sample_source_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            source = loader.get_source("src_policy_mainframe")
            
            assert isinstance(source, SourceConfig)
            assert source.source_id == "src_policy_mainframe"
            assert source.source_type == "FILE"
    
    def test_get_source_not_found_raises_error(self, mock_spark):
        """Test get_source raises ConfigNotFoundError for invalid ID."""
        # Setup mock to return empty result
        mock_df = Mock()
        mock_df.filter.return_value.collect.return_value = []
        mock_df.select.return_value.limit.return_value.collect.return_value = [
            {"source_id": "src_1"}, {"source_id": "src_2"}
        ]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            
            with pytest.raises(ConfigNotFoundError) as exc_info:
                loader.get_source("nonexistent_id")
            
            # Verify error message is helpful
            assert "nonexistent_id" in str(exc_info.value)
            assert "Available" in str(exc_info.value)

class TestSourceConfig:
    """Tests for SourceConfig dataclass."""
    
    def test_file_source_validation_success(self):
        """Test FILE source with valid fields passes validation."""
        source = SourceConfig(
            source_id="src_test",
            source_name="Test Source",
            source_type="FILE",
            source_system="TestSystem",
            connection_string="s3://bucket/path",
            file_format="CSV",
            business_domain="POLICY",
            pii_flag=False,
            data_classification="INTERNAL"
        )
        assert source.source_id == "src_test"
    
    def test_file_source_missing_format_raises_error(self):
        """Test FILE source without file_format raises ValueError."""
        with pytest.raises(ValueError, match="requires file_format"):
            SourceConfig(
                source_id="src_test",
                source_name="Test Source",
                source_type="FILE",
                source_system="TestSystem",
                connection_string="s3://bucket/path",
                file_format=None,  # Missing!
                business_domain="POLICY",
                pii_flag=False,
                data_classification="INTERNAL"
            )
    
    def test_pii_source_requires_restricted_classification(self):
        """Test PII source with PUBLIC classification raises ValueError."""
        with pytest.raises(ValueError, match="CONFIDENTIAL.*RESTRICTED"):
            SourceConfig(
                source_id="src_test",
                source_name="Test Source",
                source_type="FILE",
                source_system="TestSystem",
                connection_string="s3://bucket/path",
                file_format="CSV",
                business_domain="POLICY",
                pii_flag=True,  # PII data
                data_classification="PUBLIC"  # Invalid for PII!
            )

# ========== Test Execution ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=sdk", "--cov-report=term-missing"])
\`\`\`

## Examples

### Example 1: Generate tests for Config Loader

**Input**:
\`\`\`python
module_path = "/sdk/config_loader.py"
coverage_target = 80
\`\`\`

**Output**: \`test_config_loader.py\` with:
* 25+ test methods covering all ConfigLoader methods
* Fixtures for mock Spark, sample data rows
* Tests for happy path, validation, error cases
* Mocked external dependencies (Spark tables)
* 85% code coverage

### Example 2: Generate tests for data models

**Input**:
\`\`\`python
module_path = "/sdk/models/source.py"
\`\`\`

**Output**: \`test_source.py\` with:
* Tests for each validation rule in \`__post_init__\`
* Tests for \`from_row()\` classmethod
* Tests for \`to_dict()\` method
* Edge cases (null values, missing fields)

## Acceptance / eval

✅ **Complete**: All public methods have at least one test
✅ **Coverage**: >80% code coverage achieved
✅ **Independent**: Tests pass in any order (\`pytest --random-order\`)
✅ **Fast**: All tests complete in <5 seconds
✅ **Clear**: Test names explain what they test
✅ **Helpful errors**: Failed assertions show why test failed

## References

* Backlog: FND-013 (ABC SDK tests), TST-001, TST-002
* pytest documentation: https://docs.pytest.org/
* pytest-cov: https://pytest-cov.readthedocs.io/
* Mocking guide: https://docs.python.org/3/library/unittest.mock.html
* Shared: ../../_shared/standards.md
