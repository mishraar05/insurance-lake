"""Integration tests for ConfigLoader."""
import pytest
from unittest.mock import Mock, MagicMock
from pyspark.sql import Row

from core.metadata import (
    ConfigLoader, SourceConfig, SourceType, TargetConfig, LoadConfig,
    ConfigNotFoundError, FKViolationError
)


@pytest.fixture
def mock_spark():
    """Mock Spark session."""
    spark = Mock()
    return spark


@pytest.fixture
def config_loader(mock_spark):
    """ConfigLoader with mocked Spark."""
    return ConfigLoader(
        catalog="test_catalog",
        schema="test_schema",
        spark=mock_spark
    )


def test_get_source_success(config_loader, mock_spark):
    """Test get_source() retrieves source configuration."""
    # Mock DataFrame and row
    mock_df = Mock()
    mock_row = Row(
        source_id="src_001",
        source_name="test_source",
        source_type="FILE",
        source_system="TestSystem",
        connection_string="/path/to/data",
        file_format="CSV",
        schema_location=None,
        credential_scope=None,
        credential_key=None,
        business_domain="POLICY",
        pii_flag=False,
        data_classification="PUBLIC",
        sla_hours=24,
        active_flag=True
    )
    mock_df.collect.return_value = [mock_row]
    mock_spark.sql.return_value = mock_df
    
    # Call get_source
    source = config_loader.get_source("src_001")
    
    # Verify
    assert source.source_id == "src_001"
    assert source.source_type == SourceType.FILE
    assert source.file_format == "CSV"
    mock_spark.sql.assert_called_once()


def test_get_source_not_found(config_loader, mock_spark):
    """Test get_source() raises ConfigNotFoundError when not found."""
    # Mock empty result
    mock_df = Mock()
    mock_df.collect.return_value = []
    mock_spark.sql.return_value = mock_df
    
    # Should raise ConfigNotFoundError
    with pytest.raises(ConfigNotFoundError, match="Source not found: src_999"):
        config_loader.get_source("src_999")


def test_get_target_success(config_loader, mock_spark):
    """Test get_target() retrieves target configuration."""
    # Mock DataFrame and row
    mock_df = Mock()
    mock_row = Row(
        target_id="tgt_001",
        target_name="test_target",
        catalog_name="test_catalog",
        schema_name="bronze",
        table_name="test_table",
        layer="BRONZE",
        table_type="MANAGED",
        format="DELTA",
        partition_columns=["date"],
        liquid_clustering_columns=["id"],
        primary_key=["id"],
        acord_entity="Policy",
        retention_days=365,
        enable_cdf=True,
        dimensional=False,
        active_flag=True
    )
    mock_df.collect.return_value = [mock_row]
    mock_spark.sql.return_value = mock_df
    
    # Call get_target
    target = config_loader.get_target("tgt_001")
    
    # Verify
    assert target.target_id == "tgt_001"
    assert target.layer == "BRONZE"
    assert target.enable_cdf is True


def test_get_load_success_with_fk_validation(config_loader, mock_spark):
    """Test get_load() validates FK references."""
    # Mock load config row
    load_row = Row(
        load_id="load_001",
        load_name="test_load",
        source_id="src_001",
        target_id="tgt_001",
        load_type="BATCH",
        load_pattern="APPEND",
        engine="AUTOLOADER",
        watermark_column=None,
        watermark_type=None,
        checkpoint_location="/checkpoints",
        trigger_interval=None,
        merge_keys=None,
        autoloader_options={},
        schedule_cron=None,
        depends_on=None,
        source_system_type="stable",
        governance_tier="standard",
        zero_downtime=False,
        paranoid=False,
        type_changes="none",
        renames_expected=False,
        active_flag=True
    )
    
    # Mock source row
    source_row = Row(
        source_id="src_001",
        source_name="test_source",
        source_type="FILE",
        source_system="TestSystem",
        connection_string="/path",
        file_format="CSV",
        schema_location=None,
        credential_scope=None,
        credential_key=None,
        business_domain="POLICY",
        pii_flag=False,
        data_classification="PUBLIC",
        sla_hours=24,
        active_flag=True
    )
    
    # Mock target row
    target_row = Row(
        target_id="tgt_001",
        target_name="test_target",
        catalog_name="catalog",
        schema_name="schema",
        table_name="table",
        layer="BRONZE",
        table_type="MANAGED",
        format="DELTA",
        partition_columns=[],
        liquid_clustering_columns=[],
        primary_key=["id"],
        acord_entity=None,
        retention_days=90,
        enable_cdf=False,
        dimensional=False,
        active_flag=True
    )
    
    # Mock DataFrame returns
    def mock_sql(query):
        mock_df = Mock()
        if "cfg_load" in query:
            mock_df.collect.return_value = [load_row]
        elif "cfg_source" in query:
            mock_df.collect.return_value = [source_row]
        elif "cfg_target" in query:
            mock_df.collect.return_value = [target_row]
        return mock_df
    
    mock_spark.sql.side_effect = mock_sql
    
    # Call get_load
    load = config_loader.get_load("load_001")
    
    # Verify
    assert load.load_id == "load_001"
    assert load.source_id == "src_001"
    assert load.target_id == "tgt_001"


def test_get_load_fk_violation(config_loader, mock_spark):
    """Test get_load() raises FKViolationError for invalid FK."""
    # Mock load with invalid source_id
    load_row = Row(
        load_id="load_001",
        load_name="test_load",
        source_id="src_999",  # Invalid FK
        target_id="tgt_001",
        load_type="BATCH",
        load_pattern="APPEND",
        engine="AUTOLOADER",
        watermark_column=None,
        watermark_type=None,
        checkpoint_location="/checkpoints",
        trigger_interval=None,
        merge_keys=None,
        autoloader_options={},
        schedule_cron=None,
        depends_on=None,
        active_flag=True
    )
    
    def mock_sql(query):
        mock_df = Mock()
        if "cfg_load" in query:
            mock_df.collect.return_value = [load_row]
        else:
            mock_df.collect.return_value = []  # FK not found
        return mock_df
    
    mock_spark.sql.side_effect = mock_sql
    
    # Should raise FKViolationError
    with pytest.raises(FKViolationError, match="source_id"):
        config_loader.get_load("load_001")


def test_get_transform_success(config_loader, mock_spark):
    """Test get_transform() retrieves transform configuration."""
    mock_df = Mock()
    mock_row = Row(
        transform_id="txf_001",
        transform_name="test_transform",
        source_target_id="tgt_bronze",
        destination_target_id="tgt_silver",
        transform_type="SQL",
        transform_sql="SELECT * FROM source",
        transform_python=None,
        acord_mapping_template=None,
        scd_type=None,
        scd_key_columns=None,
        scd_timestamp_column=None,
        engine="SPARK_SQL",
        dependencies=None,
        active_flag=True
    )
    mock_df.collect.return_value = [mock_row]
    mock_spark.sql.return_value = mock_df
    
    transform = config_loader.get_transform("txf_001")
    
    assert transform.transform_id == "txf_001"
    assert transform.transform_type == "SQL"


def test_get_dq_rule_success(config_loader, mock_spark):
    """Test get_dq_rule() retrieves DQ rule configuration."""
    mock_df = Mock()
    mock_row = Row(
        dq_rule_id="dq_001",
        rule_name="not_null_check",
        target_id="tgt_001",
        rule_type="NOT_NULL",
        column_name="policy_id",
        rule_expression=None,
        threshold_percent=0.0,
        on_failure="FAIL",
        active_flag=True
    )
    mock_df.collect.return_value = [mock_row]
    mock_spark.sql.return_value = mock_df
    
    rule = config_loader.get_dq_rule("dq_001")
    
    assert rule.dq_rule_id == "dq_001"
    assert rule.rule_type == "NOT_NULL"
    assert rule.on_failure == "FAIL"


def test_save_methods_not_implemented(config_loader):
    """Test save methods raise NotImplementedError."""
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
    
    with pytest.raises(NotImplementedError):
        config_loader.save_source(source)


@pytest.mark.integration
def test_end_to_end_config_flow():
    """Test end-to-end config load workflow."""
    pytest.skip("Requires actual Unity Catalog tables")
    
    # This would test against real UC tables
    loader = ConfigLoader(
        catalog="insurelake_test",
        schema="config_test"
    )
    
    # Load source
    source = loader.get_source("test_src_001")
    assert source.source_id is not None
    
    # Load target
    target = loader.get_target("test_tgt_001")
    assert target.target_id is not None
    
    # Load config with FK validation
    load = loader.get_load("test_load_001")
    assert load.source_id == source.source_id
    assert load.target_id == target.target_id
