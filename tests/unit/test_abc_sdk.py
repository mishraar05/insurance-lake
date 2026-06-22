"""Unit tests for ABC SDK."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid

from core.sdk import ABC, RunHandle, ABCConnectionError, ABCWriteError, ABCValidationError


@pytest.fixture
def mock_spark():
    """Mock Spark session."""
    spark = Mock()
    spark.sql = Mock()
    return spark


@pytest.fixture
def abc_sdk(mock_spark):
    """ABC SDK instance with mocked Spark."""
    with patch('core.sdk.abc.SparkSession.builder.getOrCreate', return_value=mock_spark):
        abc = ABC(catalog="test_catalog", schema="test_schema", spark=mock_spark)
    return abc


def test_abc_init_success(mock_spark):
    """Test ABC initialization with valid Spark session."""
    abc = ABC(catalog="test_catalog", schema="test_schema", spark=mock_spark)
    assert abc.catalog == "test_catalog"
    assert abc.schema == "test_schema"
    assert abc.spark == mock_spark


def test_abc_init_connection_error(mock_spark):
    """Test ABC initialization with connection error."""
    mock_spark.sql.side_effect = Exception("Catalog not found")
    
    with pytest.raises(ABCConnectionError, match="Cannot connect to test_catalog.test_schema"):
        ABC(catalog="test_catalog", schema="test_schema", spark=mock_spark)


def test_start_run_generates_ids(abc_sdk, mock_spark):
    """Test start_run() generates unique run_id and trace_id."""
    run = abc_sdk.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH_INCREMENTAL"
    )
    
    assert isinstance(run, RunHandle)
    assert run.run_id is not None
    assert run.trace_id is not None
    # Verify UUID format
    uuid.UUID(run.run_id)
    uuid.UUID(run.trace_id)


def test_start_run_accepts_trace_id(abc_sdk, mock_spark):
    """Test start_run() accepts provided trace_id."""
    provided_trace_id = str(uuid.uuid4())
    
    run = abc_sdk.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH_INCREMENTAL",
        trace_id=provided_trace_id
    )
    
    assert run.trace_id == provided_trace_id


def test_start_run_validates_inputs(abc_sdk):
    """Test start_run() validates required inputs."""
    with pytest.raises(ABCValidationError, match="component and entity must not be NULL"):
        abc_sdk.start_run(component="", entity="policy", run_type="BATCH")
    
    with pytest.raises(ABCValidationError, match="component and entity must not be NULL"):
        abc_sdk.start_run(component="ingestion", entity="", run_type="BATCH")


def test_start_run_inserts_running_status(abc_sdk, mock_spark):
    """Test start_run() inserts RUNNING status into abc_audit."""
    run = abc_sdk.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH_INCREMENTAL"
    )
    
    # Verify SQL INSERT was called
    mock_spark.sql.assert_called()
    insert_sql = mock_spark.sql.call_args[0][0]
    assert "INSERT INTO test_catalog.test_schema.abc_audit" in insert_sql
    assert "'RUNNING'" in insert_sql
    assert run.run_id in insert_sql


def test_end_run_updates_status(abc_sdk, mock_spark):
    """Test end_run() updates run status to SUCCESS."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.end_run(run.run_id, status="SUCCESS")
    
    # Verify MERGE was called
    merge_sql = mock_spark.sql.call_args[0][0]
    assert "MERGE INTO test_catalog.test_schema.abc_audit" in merge_sql
    assert "status = 'SUCCESS'" in merge_sql


def test_end_run_validates_status(abc_sdk):
    """Test end_run() validates status enum."""
    with pytest.raises(ABCValidationError, match="Invalid status"):
        abc_sdk.end_run("fake_run_id", status="INVALID_STATUS")


def test_end_run_calculates_duration(abc_sdk, mock_spark):
    """Test end_run() calculates duration_seconds."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.end_run(run.run_id, status="SUCCESS")
    
    merge_sql = mock_spark.sql.call_args[0][0]
    assert "duration_seconds" in merge_sql


def test_log_audit_updates_metrics(abc_sdk, mock_spark):
    """Test log_audit() updates audit metrics."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.log_audit(run.run_id, {
        "rows_read": 10000,
        "rows_written": 9980,
        "rows_rejected": 20
    })
    
    merge_sql = mock_spark.sql.call_args[0][0]
    assert "MERGE INTO test_catalog.test_schema.abc_audit" in merge_sql
    assert "rows_read = 10000" in merge_sql
    assert "rows_written = 9980" in merge_sql


def test_log_audit_validates_run_id(abc_sdk):
    """Test log_audit() validates run_id."""
    with pytest.raises(ABCValidationError, match="run_id must not be NULL"):
        abc_sdk.log_audit("", {"rows_read": 100})


def test_log_balance_inserts_checks(abc_sdk, mock_spark):
    """Test log_balance() inserts balance checks."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.log_balance(run.run_id, [{
        "check_name": "src_vs_bronze_count",
        "check_type": "COUNT",
        "source_ref": "src_001",
        "source_value": 10000,
        "target_ref": "insurelake.bronze.policy",
        "target_value": 10000,
        "threshold_percent": 0.01
    }])
    
    insert_sql = mock_spark.sql.call_args[0][0]
    assert "INSERT INTO test_catalog.test_schema.abc_balance" in insert_sql
    assert "src_vs_bronze_count" in insert_sql


def test_log_balance_validates_required_fields(abc_sdk):
    """Test log_balance() validates source_value and target_value."""
    run_id = str(uuid.uuid4())
    
    with pytest.raises(ABCValidationError, match="Balance checks must include source_value and target_value"):
        abc_sdk.log_balance(run_id, [{"check_name": "test"}])


def test_log_balance_calculates_variance(abc_sdk, mock_spark):
    """Test log_balance() calculates variance and balanced flag."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.log_balance(run.run_id, [{
        "source_value": 10000,
        "target_value": 9990,
        "threshold_percent": 1.0  # 1% tolerance
    }])
    
    insert_sql = mock_spark.sql.call_args[0][0]
    # Variance = 10000 - 9990 = 10
    # Variance % = (10 / 10000) * 100 = 0.1%
    # Balanced = True (0.1% <= 1.0%)
    assert "True" in insert_sql  # balanced flag


def test_log_dq_inserts_results(abc_sdk, mock_spark):
    """Test log_dq() inserts DQ rule outcomes."""
    run = abc_sdk.start_run(component="dq", entity="policy", run_type="DQ_BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.log_dq(run.run_id, [{
        "rule_id": "dq_001",
        "rule_name": "policy_number_not_null",
        "target_table": "insurelake.bronze.policy",
        "column_name": "policy_number",
        "check_result": "PASS",
        "failed_count": 0,
        "action_taken": "WARN"
    }])
    
    insert_sql = mock_spark.sql.call_args[0][0]
    assert "INSERT INTO test_catalog.test_schema.abc_control" in insert_sql
    assert "DQ_RULE" in insert_sql
    assert "policy_number_not_null" in insert_sql


def test_log_exception_inserts_error(abc_sdk, mock_spark):
    """Test log_exception() logs structured exception."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    try:
        raise ValueError("Test error message")
    except ValueError as e:
        abc_sdk.log_exception(run.run_id, e)
    
    insert_sql = mock_spark.sql.call_args[0][0]
    assert "INSERT INTO test_catalog.test_schema.abc_control" in insert_sql
    assert "EXCEPTION" in insert_sql
    assert "Test error message" in insert_sql


def test_log_cost_inserts_consumption(abc_sdk, mock_spark):
    """Test log_cost() logs cost and consumption metrics."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Clear previous calls
    mock_spark.sql.reset_mock()
    
    abc_sdk.log_cost(run.run_id, {
        "component": "ingestion",
        "entity": "policy",
        "dbu_seconds": 1234.5,
        "dbu_count": 2.0,
        "cost_usd": 5.67,
        "cluster_id": "cluster-123"
    })
    
    insert_sql = mock_spark.sql.call_args[0][0]
    assert "INSERT INTO test_catalog.test_schema.abc_cost" in insert_sql
    assert "1234.5" in insert_sql
    assert "cluster-123" in insert_sql


def test_abc_write_failure_resilience(abc_sdk, mock_spark):
    """Test ABC write failures don't crash (resilience)."""
    mock_spark.sql.side_effect = Exception("Connection lost")
    
    # start_run should not raise exception in production
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    assert run is not None
    
    # log_audit should not raise exception
    abc_sdk.log_audit(run.run_id, {"rows_read": 100})
    
    # end_run should not raise exception
    abc_sdk.end_run(run.run_id, status="SUCCESS")


def test_idempotent_operations(abc_sdk, mock_spark):
    """Test operations are idempotent (safe to re-run)."""
    run = abc_sdk.start_run(component="ingestion", entity="policy", run_type="BATCH")
    
    # Call end_run twice with same run_id
    abc_sdk.end_run(run.run_id, status="SUCCESS")
    abc_sdk.end_run(run.run_id, status="SUCCESS")
    
    # Should use MERGE (upsert), not INSERT
    calls = [call[0][0] for call in mock_spark.sql.call_args_list]
    merge_calls = [c for c in calls if "MERGE INTO" in c]
    assert len(merge_calls) >= 2


def test_trace_id_propagation(abc_sdk):
    """Test trace_id propagates across runs."""
    parent_trace_id = str(uuid.uuid4())
    
    # Start run with trace_id
    run1 = abc_sdk.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH",
        trace_id=parent_trace_id
    )
    
    # Verify trace_id is preserved
    assert run1.trace_id == parent_trace_id
    
    # Start child run with same trace_id
    run2 = abc_sdk.start_run(
        component="harmonization",
        entity="policy",
        run_type="BATCH",
        trace_id=parent_trace_id
    )
    
    # Both runs share same trace_id
    assert run2.trace_id == parent_trace_id
    assert run1.trace_id == run2.trace_id


def test_runhandle_dataclass():
    """Test RunHandle dataclass."""
    run_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    handle = RunHandle(run_id=run_id, trace_id=trace_id)
    
    assert handle.run_id == run_id
    assert handle.trace_id == trace_id


def test_exception_classes():
    """Test custom exception classes."""
    assert issubclass(ABCConnectionError, Exception)
    assert issubclass(ABCWriteError, Exception)
    assert issubclass(ABCValidationError, ValueError)
    
    # Test raising
    with pytest.raises(ABCConnectionError):
        raise ABCConnectionError("Connection failed")
    
    with pytest.raises(ABCWriteError):
        raise ABCWriteError("Write failed")
    
    with pytest.raises(ABCValidationError):
        raise ABCValidationError("Validation failed")
