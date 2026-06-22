"""Integration tests for ABC SDK."""
import pytest
from datetime import datetime
import uuid

from core.sdk import ABC, RunHandle


@pytest.fixture(scope="module")
def test_catalog():
    """Test catalog name."""
    return "insurelake_test"


@pytest.fixture(scope="module")
def test_schema():
    """Test schema name."""
    return "abc_test"


@pytest.mark.integration
def test_full_ingestion_workflow(test_catalog, test_schema):
    """Test complete ingestion workflow with ABC logging."""
    # Skip if ABC tables don't exist
    pytest.skip("Requires ABC tables in test catalog")
    
    abc = ABC(catalog=test_catalog, schema=test_schema)
    
    # Start run
    run = abc.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH_INCREMENTAL"
    )
    
    assert run.run_id is not None
    assert run.trace_id is not None
    
    try:
        # Simulate ingestion
        source_count = 10000
        target_count = 9980
        rejected_count = 20
        
        # Log audit metrics
        abc.log_audit(run.run_id, {
            "rows_read": source_count,
            "rows_written": target_count,
            "rows_rejected": rejected_count
        })
        
        # Log balance check
        abc.log_balance(run.run_id, [{
            "check_name": "src_vs_bronze_count",
            "check_type": "COUNT",
            "source_ref": "src_001",
            "source_value": source_count,
            "target_ref": "insurelake.bronze.policy",
            "target_value": target_count,
            "threshold_percent": 0.01
        }])
        
        # End run successfully
        abc.end_run(run.run_id, status="SUCCESS")
        
    except Exception as e:
        # Log exception
        abc.log_exception(run.run_id, e)
        abc.end_run(run.run_id, status="FAILED")
        raise


@pytest.mark.integration
def test_dq_workflow(test_catalog, test_schema):
    """Test DQ workflow with ABC logging."""
    pytest.skip("Requires ABC tables in test catalog")
    
    abc = ABC(catalog=test_catalog, schema=test_schema)
    
    # Start DQ run
    run = abc.start_run(
        component="data_quality",
        entity="policy",
        run_type="DQ_BATCH"
    )
    
    # Log DQ results
    abc.log_dq(run.run_id, [{
        "rule_id": "dq_001",
        "rule_name": "policy_number_not_null",
        "target_table": "insurelake.bronze.policy",
        "column_name": "policy_number",
        "check_result": "PASS",
        "failed_count": 0,
        "action_taken": "WARN"
    }])
    
    abc.end_run(run.run_id, status="SUCCESS")


@pytest.mark.integration
def test_cost_tracking(test_catalog, test_schema):
    """Test cost tracking workflow."""
    pytest.skip("Requires ABC tables in test catalog")
    
    abc = ABC(catalog=test_catalog, schema=test_schema)
    
    run = abc.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH"
    )
    
    # Log cost
    abc.log_cost(run.run_id, {
        "component": "ingestion",
        "entity": "policy",
        "dbu_seconds": 1234.5,
        "dbu_count": 2.0,
        "cost_usd": 5.67,
        "cluster_id": "cluster-123"
    })
    
    abc.end_run(run.run_id, status="SUCCESS")


@pytest.mark.integration
def test_trace_id_lineage(test_catalog, test_schema):
    """Test trace ID propagation across multiple runs."""
    pytest.skip("Requires ABC tables in test catalog")
    
    abc = ABC(catalog=test_catalog, schema=test_schema)
    
    # Parent run
    parent_trace_id = str(uuid.uuid4())
    run1 = abc.start_run(
        component="ingestion",
        entity="policy",
        run_type="BATCH",
        trace_id=parent_trace_id
    )
    abc.end_run(run1.run_id, status="SUCCESS")
    
    # Child run with same trace_id
    run2 = abc.start_run(
        component="harmonization",
        entity="policy",
        run_type="BATCH",
        trace_id=parent_trace_id
    )
    abc.end_run(run2.run_id, status="SUCCESS")
    
    # Verify both runs share trace_id
    assert run1.trace_id == run2.trace_id == parent_trace_id
