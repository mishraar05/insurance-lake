"""
Shared pytest fixtures for InsureLake SDK tests.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


@pytest.fixture(scope="session")
def test_catalog():
    """Test catalog name for all tests."""
    return "insurelake_test"


@pytest.fixture(scope="session")
def test_schema():
    """Test schema name for all tests."""
    return "config_test"


@pytest.fixture
def mock_spark_session():
    """Mock Spark session fixture available to all tests."""
    spark = Mock()
    spark.sql = Mock()
    spark.table = Mock()
    return spark


@pytest.fixture
def sample_timestamp():
    """Standard timestamp for test data."""
    return datetime(2026, 6, 18, 12, 0, 0)
