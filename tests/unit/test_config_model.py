"""Unit tests for config models."""
import pytest
from pydantic import ValidationError

from core.metadata import (
    SourceConfig, SourceType, TargetConfig, LoadConfig, 
    TransformConfig, DQRuleConfig
)


def test_source_config_valid():
    """Test SourceConfig with valid data."""
    source = SourceConfig(
        source_id="src_001",
        source_name="policies_salesforce",
        source_type=SourceType.API,
        source_system="Salesforce",
        connection_string="https://api.salesforce.com/policies",
        file_format="JSON",
        business_domain="POLICY",
        pii_flag=True,
        data_classification="CONFIDENTIAL",
        sla_hours=4
    )
    
    assert source.source_id == "src_001"
    assert source.source_type == SourceType.API
    assert source.pii_flag is True
    assert source.active_flag is True  # default


def test_source_config_enum_validation():
    """Test SourceConfig validates source_type enum."""
    with pytest.raises(ValidationError):
        SourceConfig(
            source_id="src_001",
            source_name="test",
            source_type="INVALID_TYPE",  # Invalid enum
            source_system="System",
            business_domain="POLICY",
            pii_flag=False,
            data_classification="PUBLIC",
            sla_hours=24
        )


def test_source_config_missing_required():
    """Test SourceConfig validates required fields."""
    with pytest.raises(ValidationError):
        SourceConfig(
            source_id="src_001",
            source_name="test"
            # Missing required fields
        )


def test_target_config_valid():
    """Test TargetConfig with valid data."""
    target = TargetConfig(
        target_id="tgt_001",
        target_name="policies_bronze",
        catalog_name="insurelake",
        schema_name="bronze",
        table_name="policies_raw",
        layer="BRONZE",
        table_type="MANAGED",
        format="DELTA",
        partition_columns=["ingest_date"],
        liquid_clustering_columns=["policy_number"],
        primary_key=["policy_id"],
        retention_days=365,
        enable_cdf=True
    )
    
    assert target.target_id == "tgt_001"
    assert target.layer == "BRONZE"
    assert len(target.primary_key) == 1
    assert target.dimensional is False  # default


def test_target_config_empty_lists():
    """Test TargetConfig with empty lists."""
    target = TargetConfig(
        target_id="tgt_002",
        target_name="test_target",
        catalog_name="catalog",
        schema_name="schema",
        table_name="table",
        layer="SILVER",
        table_type="MANAGED",
        format="DELTA",
        partition_columns=[],
        liquid_clustering_columns=[],
        primary_key=["id"],
        retention_days=90,
        enable_cdf=False
    )
    
    assert len(target.partition_columns) == 0
    assert len(target.liquid_clustering_columns) == 0


def test_load_config_valid():
    """Test LoadConfig with valid data."""
    load = LoadConfig(
        load_id="load_001",
        load_name="ingest_policies",
        source_id="src_001",
        target_id="tgt_001",
        load_type="BATCH_INCREMENTAL",
        load_pattern="APPEND",
        engine="AUTOLOADER",
        checkpoint_location="/checkpoints/policies",
        autoloader_options={"cloudFiles.format": "json"}
    )
    
    assert load.load_id == "load_001"
    assert load.load_pattern == "APPEND"
    assert load.source_system_type == "stable"  # default
    assert load.governance_tier == "standard"  # default


def test_load_config_schema_evolution_fields():
    """Test LoadConfig schema-evolution policy fields."""
    load = LoadConfig(
        load_id="load_002",
        load_name="test",
        source_id="src_001",
        target_id="tgt_001",
        load_type="BATCH",
        load_pattern="MERGE",
        engine="AUTOLOADER",
        checkpoint_location="/checkpoints",
        autoloader_options={},
        source_system_type="volatile",
        governance_tier="high",
        zero_downtime=True,
        paranoid=True,
        type_changes="widening",
        renames_expected=True
    )
    
    assert load.source_system_type == "volatile"
    assert load.governance_tier == "high"
    assert load.zero_downtime is True
    assert load.paranoid is True
    assert load.type_changes == "widening"
    assert load.renames_expected is True


def test_transform_config_valid():
    """Test TransformConfig with valid data."""
    transform = TransformConfig(
        transform_id="txf_001",
        transform_name="enrich_policies",
        source_target_id="tgt_bronze_policy",
        destination_target_id="tgt_silver_policy",
        transform_type="SQL",
        transform_sql="SELECT * FROM source WHERE status = 'ACTIVE'",
        engine="SPARK_SQL"
    )
    
    assert transform.transform_id == "txf_001"
    assert transform.transform_type == "SQL"
    assert transform.transform_sql is not None


def test_transform_config_scd_fields():
    """Test TransformConfig with SCD fields."""
    transform = TransformConfig(
        transform_id="txf_002",
        transform_name="scd2_customers",
        source_target_id="tgt_bronze_customer",
        destination_target_id="tgt_silver_customer",
        transform_type="SCD2",
        scd_type="TYPE2",
        scd_key_columns=["customer_id"],
        scd_timestamp_column="effective_date",
        engine="SPARK_SQL"
    )
    
    assert transform.scd_type == "TYPE2"
    assert len(transform.scd_key_columns) == 1
    assert transform.scd_timestamp_column == "effective_date"


def test_dq_rule_config_valid():
    """Test DQRuleConfig with valid data."""
    rule = DQRuleConfig(
        dq_rule_id="dq_001",
        rule_name="policy_number_not_null",
        target_id="tgt_bronze_policy",
        rule_type="NOT_NULL",
        column_name="policy_number",
        threshold_percent=0.0,
        on_failure="FAIL"
    )
    
    assert rule.dq_rule_id == "dq_001"
    assert rule.rule_type == "NOT_NULL"
    assert rule.on_failure == "FAIL"
    assert rule.active_flag is True


def test_dq_rule_config_with_expression():
    """Test DQRuleConfig with custom expression."""
    rule = DQRuleConfig(
        dq_rule_id="dq_002",
        rule_name="premium_range_check",
        target_id="tgt_bronze_policy",
        rule_type="CUSTOM",
        column_name="premium_amount",
        rule_expression="premium_amount > 0 AND premium_amount < 1000000",
        threshold_percent=1.0,
        on_failure="WARN"
    )
    
    assert rule.rule_expression is not None
    assert rule.threshold_percent == 1.0
    assert rule.on_failure == "WARN"


def test_pydantic_validation():
    """Test Pydantic validates types."""
    with pytest.raises(ValidationError):
        SourceConfig(
            source_id="src_001",
            source_name="test",
            source_type=SourceType.FILE,
            source_system="System",
            business_domain="POLICY",
            pii_flag="not_a_bool",  # Should be bool
            data_classification="PUBLIC",
            sla_hours="not_an_int"  # Should be int
        )


def test_optional_fields():
    """Test optional fields can be None."""
    source = SourceConfig(
        source_id="src_001",
        source_name="test",
        source_type=SourceType.TABLE,
        source_system="System",
        connection_string=None,  # Optional
        file_format=None,  # Optional
        schema_location=None,  # Optional
        credential_scope=None,  # Optional
        credential_key=None,  # Optional
        business_domain="POLICY",
        pii_flag=False,
        data_classification="PUBLIC",
        sla_hours=24
    )
    
    assert source.connection_string is None
    assert source.file_format is None


def test_config_serialization():
    """Test Pydantic models serialize to dict."""
    source = SourceConfig(
        source_id="src_001",
        source_name="test",
        source_type=SourceType.FILE,
        source_system="System",
        business_domain="POLICY",
        pii_flag=False,
        data_classification="PUBLIC",
        sla_hours=24
    )
    
    data = source.dict()
    assert data["source_id"] == "src_001"
    assert data["source_type"] == "FILE"  # Enum serialized
    assert "active_flag" in data


def test_config_deserialization():
    """Test Pydantic models deserialize from dict."""
    data = {
        "source_id": "src_001",
        "source_name": "test",
        "source_type": "API",
        "source_system": "System",
        "business_domain": "POLICY",
        "pii_flag": True,
        "data_classification": "RESTRICTED",
        "sla_hours": 8,
        "active_flag": True
    }
    
    source = SourceConfig(**data)
    assert source.source_id == "src_001"
    assert source.source_type == SourceType.API
