"""
Unit tests for InsureLake Config Loader SDK.

Tests cover:
- ConfigLoader initialization and connection handling
- Loading individual config entities (Source, Target, Load, Transform, DQ)
- Foreign key validation
- Listing and filtering operations
- Error handling and helpful error messages
- Model validation rules

Coverage target: >80%

Task: FND-003
Author: create-unit-tests skill
Date: 2026-06-18
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import sys

sys.path.append("/Workspace/Users/cleancoding109@gmail.com/insurance-lake")

from sdk import ConfigLoader
from sdk.models import (
    SourceConfig,
    TargetConfig,
    LoadConfig,
    TransformConfig,
    DQRuleConfig,
)
from sdk.exceptions import (
    ConfigNotFoundError,
    ConfigValidationError,
    ForeignKeyError,
    CatalogConnectionError,
)


# ========== Fixtures ==========

@pytest.fixture
def mock_spark():
    """Mock Spark session for testing."""
    spark = Mock()
    spark.sql = Mock()
    spark.table = Mock()
    return spark


@pytest.fixture
def sample_source_row():
    """Sample source config row (as dict simulating Spark Row)."""
    return {
        "source_id": "src_policy_mainframe",
        "source_name": "Policy System Mainframe",
        "source_type": "FILE",
        "source_system": "PolicyCenter",
        "connection_string": "s3://insurance-lake-raw/policy/",
        "file_format": "CSV",
        "schema_location": None,
        "credential_scope": "aws_secrets",
        "credential_key": "s3_policy_key",
        "business_domain": "POLICY",
        "pii_flag": False,
        "data_classification": "INTERNAL",
        "sla_hours": 24,
        "active_flag": True,
        "created_by": "admin",
        "created_ts": datetime(2026, 6, 1),
        "updated_by": None,
        "updated_ts": None,
    }


@pytest.fixture
def sample_target_row():
    """Sample target config row."""
    return {
        "target_id": "tgt_bronze_policy",
        "target_name": "Bronze Policy Table",
        "catalog_name": "insurelake",
        "schema_name": "bronze",
        "table_name": "policy_raw",
        "layer": "BRONZE",
        "table_type": "MANAGED",
        "format": "DELTA",
        "partition_columns": ["load_date"],
        "liquid_clustering_columns": None,
        "primary_key": ["policy_number"],
        "acord_entity": None,
        "retention_days": 365,
        "enable_cdf": True,
        "active_flag": True,
        "created_by": "admin",
        "created_ts": datetime(2026, 6, 1),
        "updated_by": None,
        "updated_ts": None,
    }


@pytest.fixture
def sample_load_row():
    """Sample load config row."""
    return {
        "load_id": "load_policy_batch",
        "load_name": "Daily Policy Load",
        "source_id": "src_policy_mainframe",
        "target_id": "tgt_bronze_policy",
        "load_type": "BATCH_INCREMENTAL",
        "load_pattern": "APPEND",
        "engine": "AUTOLOADER",
        "watermark_column": "modified_date",
        "watermark_type": "TIMESTAMP",
        "checkpoint_location": None,
        "trigger_interval": None,
        "merge_keys": None,
        "autoloader_options": {"cloudFiles.format": "csv", "cloudFiles.schemaLocation": "/schemas/policy"},
        "schedule_cron": "0 2 * * *",
        "depends_on": None,
        "active_flag": True,
        "created_by": "admin",
        "created_ts": datetime(2026, 6, 1),
        "updated_by": None,
        "updated_ts": None,
    }


@pytest.fixture
def sample_transform_row():
    """Sample transform config row."""
    return {
        "transform_id": "xform_policy_to_silver",
        "transform_name": "Bronze to Silver Policy Transform",
        "source_target_id": "tgt_bronze_policy",
        "destination_target_id": "tgt_silver_policy",
        "transform_type": "SQL",
        "transform_sql": "SELECT * FROM bronze.policy_raw WHERE status = 'ACTIVE'",
        "transform_python": None,
        "acord_mapping_template": "acord_policy_v1",
        "scd_type": "SCD2",
        "scd_key_columns": "policy_number",
        "scd_timestamp_column": "effective_date",
        "engine": "DECLARATIVE",
        "dependencies": None,
        "active_flag": True,
        "created_by": "admin",
        "created_ts": datetime(2026, 6, 1),
        "updated_by": None,
        "updated_ts": None,
    }


@pytest.fixture
def sample_dq_rule_row():
    """Sample DQ rule config row."""
    return {
        "dq_rule_id": "dq_policy_number_not_null",
        "rule_name": "Policy Number Not Null",
        "target_id": "tgt_bronze_policy",
        "rule_type": "NOT_NULL",
        "column_name": "policy_number",
        "rule_expression": None,
        "threshold_percent": 1.0,
        "on_failure": "FAIL",
        "active_flag": True,
        "created_by": "admin",
        "created_ts": datetime(2026, 6, 1),
        "updated_by": None,
        "updated_ts": None,
    }


# ========== ConfigLoader Initialization Tests ==========

class TestConfigLoaderInit:
    """Tests for ConfigLoader initialization."""

    def test_init_success_with_defaults(self, mock_spark):
        """Test ConfigLoader initialization with default catalog/schema."""
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            assert loader.catalog == "insurelake_config"
            assert loader.schema == "config"
            assert loader.spark == mock_spark
            
            # Verify USE statements were called
            assert mock_spark.sql.call_count == 2
            mock_spark.sql.assert_any_call("USE CATALOG insurelake_config")
            mock_spark.sql.assert_any_call("USE SCHEMA config")

    def test_init_success_with_custom_catalog_schema(self, mock_spark):
        """Test ConfigLoader initialization with custom catalog/schema."""
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader(catalog="test_catalog", schema="test_schema")
            assert loader.catalog == "test_catalog"
            assert loader.schema == "test_schema"
            
            mock_spark.sql.assert_any_call("USE CATALOG test_catalog")
            mock_spark.sql.assert_any_call("USE SCHEMA test_schema")

    def test_init_no_spark_session_raises_error(self):
        """Test ConfigLoader initialization fails without active Spark session."""
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=None):
            with pytest.raises(RuntimeError, match="No active Spark session"):
                ConfigLoader()

    def test_init_catalog_connection_error(self, mock_spark):
        """Test ConfigLoader initialization fails with invalid catalog/schema."""
        mock_spark.sql.side_effect = Exception("Catalog not found")
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            with pytest.raises(CatalogConnectionError) as exc_info:
                ConfigLoader(catalog="nonexistent", schema="config")
            
            assert "nonexistent" in str(exc_info.value)
            assert "Catalog not found" in str(exc_info.value)


# ========== Source Loading Tests ==========

class TestConfigLoaderGetSource:
    """Tests for loading Source configs."""

    def test_get_source_success(self, mock_spark, sample_source_row):
        """Test get_source returns SourceConfig for valid ID."""
        # Setup mock
        mock_df = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = sample_source_row
        mock_df.filter.return_value.collect.return_value = [mock_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            source = loader.get_source("src_policy_mainframe")
            
            assert isinstance(source, SourceConfig)
            assert source.source_id == "src_policy_mainframe"
            assert source.source_name == "Policy System Mainframe"
            assert source.source_type == "FILE"
            assert source.file_format == "CSV"
            assert source.business_domain == "POLICY"
            assert source.pii_flag is False
            
            # Verify correct table was queried
            mock_spark.table.assert_called_with("insurelake_config.config.source")

    def test_get_source_not_found_raises_error_with_alternatives(self, mock_spark):
        """Test get_source raises ConfigNotFoundError with helpful alternatives."""
        # Setup mock to return empty result
        mock_df = Mock()
        mock_df.filter.return_value.collect.return_value = []
        
        # Mock available IDs
        mock_id_row1 = Mock()
        mock_id_row1.__getitem__.return_value = "src_policy_mainframe"
        mock_id_row2 = Mock()
        mock_id_row2.__getitem__.return_value = "src_claim_system"
        mock_df.select.return_value.limit.return_value.collect.return_value = [mock_id_row1, mock_id_row2]
        
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            
            with pytest.raises(ConfigNotFoundError) as exc_info:
                loader.get_source("nonexistent_source")
            
            error_msg = str(exc_info.value)
            assert "nonexistent_source" in error_msg
            assert "not found" in error_msg
            assert "Available" in error_msg

    def test_list_sources_all(self, mock_spark, sample_source_row):
        """Test list_sources returns all sources."""
        mock_df = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = sample_source_row
        mock_df.filter.return_value.collect.return_value = [mock_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            sources = loader.list_sources(active_only=True)
            
            assert len(sources) == 1
            assert isinstance(sources[0], SourceConfig)
            mock_df.filter.assert_called_once_with("active_flag = true")

    def test_list_sources_filtered_by_domain(self, mock_spark, sample_source_row):
        """Test list_sources filters by business domain."""
        mock_df = Mock()
        filtered_df = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = sample_source_row
        filtered_df.collect.return_value = [mock_row]
        mock_df.filter.return_value = filtered_df
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            sources = loader.list_sources(business_domain="POLICY", active_only=False)
            
            # Verify domain filter was applied
            calls = mock_df.filter.call_args_list
            assert any("POLICY" in str(call) for call in calls)


# ========== Target Loading Tests ==========

class TestConfigLoaderGetTarget:
    """Tests for loading Target configs."""

    def test_get_target_success(self, mock_spark, sample_target_row):
        """Test get_target returns TargetConfig for valid ID."""
        mock_df = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = sample_target_row
        mock_df.filter.return_value.collect.return_value = [mock_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            target = loader.get_target("tgt_bronze_policy")
            
            assert isinstance(target, TargetConfig)
            assert target.target_id == "tgt_bronze_policy"
            assert target.layer == "BRONZE"
            assert target.fully_qualified_name == "insurelake.bronze.policy_raw"

    def test_get_target_by_fqn_success(self, mock_spark, sample_target_row):
        """Test get_target_by_fqn returns TargetConfig for valid FQN."""
        mock_df = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = sample_target_row
        mock_df.filter.return_value.collect.return_value = [mock_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            target = loader.get_target_by_fqn("insurelake", "bronze", "policy_raw")
            
            assert isinstance(target, TargetConfig)
            assert target.catalog_name == "insurelake"
            assert target.schema_name == "bronze"
            assert target.table_name == "policy_raw"

    def test_list_targets_filtered_by_layer(self, mock_spark, sample_target_row):
        """Test list_targets filters by medallion layer."""
        mock_df = Mock()
        filtered_df = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = sample_target_row
        filtered_df.collect.return_value = [mock_row]
        mock_df.filter.return_value = filtered_df
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            targets = loader.list_targets(layer="BRONZE")
            
            assert len(targets) == 1
            assert targets[0].layer == "BRONZE"


# ========== Load Configuration Tests ==========

class TestConfigLoaderGetLoad:
    """Tests for loading Load configs with FK validation."""

    def test_get_load_success_with_valid_fks(self, mock_spark, sample_load_row, sample_source_row, sample_target_row):
        """Test get_load returns LoadConfig when FKs are valid."""
        mock_df = Mock()
        
        # Setup mock for load query
        load_row = Mock()
        load_row.asDict.return_value = sample_load_row
        
        # Setup mock for FK validation queries
        source_row = Mock()
        source_row.asDict.return_value = sample_source_row
        target_row = Mock()
        target_row.asDict.return_value = sample_target_row
        
        def table_side_effect(table_name):
            df = Mock()
            if "load" in table_name:
                df.filter.return_value.collect.return_value = [load_row]
            elif "source" in table_name:
                df.filter.return_value.collect.return_value = [source_row]
            elif "target" in table_name:
                df.filter.return_value.collect.return_value = [target_row]
            df.select.return_value.limit.return_value.collect.return_value = []
            return df
        
        mock_spark.table.side_effect = table_side_effect
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            load = loader.get_load("load_policy_batch")
            
            assert isinstance(load, LoadConfig)
            assert load.load_id == "load_policy_batch"
            assert load.source_id == "src_policy_mainframe"
            assert load.target_id == "tgt_bronze_policy"

    def test_get_load_invalid_source_fk_raises_error(self, mock_spark, sample_load_row):
        """Test get_load raises ForeignKeyError when source_id is invalid."""
        def table_side_effect(table_name):
            df = Mock()
            if "load" in table_name:
                load_row = Mock()
                load_row.asDict.return_value = sample_load_row
                df.filter.return_value.collect.return_value = [load_row]
            else:
                # source/target not found
                df.filter.return_value.collect.return_value = []
            df.select.return_value.limit.return_value.collect.return_value = []
            return df
        
        mock_spark.table.side_effect = table_side_effect
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            
            with pytest.raises(ForeignKeyError) as exc_info:
                loader.get_load("load_policy_batch")
            
            error_msg = str(exc_info.value)
            assert "source_id" in error_msg
            assert "src_policy_mainframe" in error_msg
            assert "Foreign key violation" in error_msg


# ========== Transform Configuration Tests ==========

class TestConfigLoaderGetTransform:
    """Tests for loading Transform configs."""

    def test_get_transforms_by_target_downstream(self, mock_spark, sample_transform_row):
        """Test get_transforms_by_target finds downstream transforms (writing TO target)."""
        mock_df = Mock()
        transform_row = Mock()
        transform_row.asDict.return_value = sample_transform_row
        mock_df.filter.return_value.collect.return_value = [transform_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            transforms = loader.get_transforms_by_target("tgt_silver_policy", upstream=False)
            
            assert len(transforms) == 1
            # Verify filter for destination_target_id
            mock_df.filter.assert_called_with("destination_target_id = 'tgt_silver_policy'")

    def test_get_transforms_by_target_upstream(self, mock_spark, sample_transform_row):
        """Test get_transforms_by_target finds upstream transforms (reading FROM target)."""
        mock_df = Mock()
        transform_row = Mock()
        transform_row.asDict.return_value = sample_transform_row
        mock_df.filter.return_value.collect.return_value = [transform_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            transforms = loader.get_transforms_by_target("tgt_bronze_policy", upstream=True)
            
            assert len(transforms) == 1
            # Verify filter for source_target_id
            mock_df.filter.assert_called_with("source_target_id = 'tgt_bronze_policy'")


# ========== DQ Rule Tests ==========

class TestConfigLoaderGetDQRule:
    """Tests for loading DQ rule configs."""

    def test_get_dq_rules_by_target(self, mock_spark, sample_dq_rule_row):
        """Test get_dq_rules_by_target returns all DQ rules for a target."""
        mock_df = Mock()
        dq_row = Mock()
        dq_row.asDict.return_value = sample_dq_rule_row
        mock_df.filter.return_value.collect.return_value = [dq_row]
        mock_spark.table.return_value = mock_df
        
        with patch('pyspark.sql.SparkSession.getActiveSession', return_value=mock_spark):
            loader = ConfigLoader()
            rules = loader.get_dq_rules_by_target("tgt_bronze_policy")
            
            assert len(rules) == 1
            assert isinstance(rules[0], DQRuleConfig)
            assert rules[0].target_id == "tgt_bronze_policy"
            assert rules[0].rule_type == "NOT_NULL"


# ========== Model Validation Tests ==========

class TestSourceConfigValidation:
    """Tests for SourceConfig dataclass validation."""

    def test_file_source_valid(self):
        """Test FILE source with all required fields passes validation."""
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
        assert source.source_type == "FILE"

    def test_file_source_missing_format_raises_error(self):
        """Test FILE source without file_format raises ValueError."""
        with pytest.raises(ValueError, match="requires file_format"):
            SourceConfig(
                source_id="src_test",
                source_name="Test Source",
                source_type="FILE",
                source_system="TestSystem",
                connection_string="s3://bucket/path",
                file_format=None,
                business_domain="POLICY",
                pii_flag=False,
                data_classification="INTERNAL"
            )

    def test_file_source_missing_connection_string_raises_error(self):
        """Test FILE source without connection_string raises ValueError."""
        with pytest.raises(ValueError, match="requires connection_string"):
            SourceConfig(
                source_id="src_test",
                source_name="Test Source",
                source_type="FILE",
                source_system="TestSystem",
                connection_string=None,
                file_format="CSV",
                business_domain="POLICY",
                pii_flag=False,
                data_classification="INTERNAL"
            )

    def test_pii_source_requires_confidential_or_restricted(self):
        """Test PII source requires CONFIDENTIAL or RESTRICTED classification."""
        with pytest.raises(ValueError, match="CONFIDENTIAL.*RESTRICTED"):
            SourceConfig(
                source_id="src_test",
                source_name="Test Source",
                source_type="FILE",
                source_system="TestSystem",
                connection_string="s3://bucket/path",
                file_format="CSV",
                business_domain="POLICY",
                pii_flag=True,
                data_classification="INTERNAL"  # Invalid for PII!
            )

    def test_pii_source_with_confidential_passes(self):
        """Test PII source with CONFIDENTIAL classification passes."""
        source = SourceConfig(
            source_id="src_test",
            source_name="Test Source",
            source_type="FILE",
            source_system="TestSystem",
            connection_string="s3://bucket/path",
            file_format="CSV",
            business_domain="POLICY",
            pii_flag=True,
            data_classification="CONFIDENTIAL"
        )
        assert source.pii_flag is True
        assert source.data_classification == "CONFIDENTIAL"


class TestTargetConfigValidation:
    """Tests for TargetConfig dataclass validation."""

    def test_partition_and_clustering_mutually_exclusive(self):
        """Test that partition_columns and liquid_clustering_columns cannot both be set."""
        with pytest.raises(ValueError, match="mutually exclusive"):
            TargetConfig(
                target_id="tgt_test",
                target_name="Test Target",
                catalog_name="catalog",
                schema_name="schema",
                table_name="table",
                layer="BRONZE",
                table_type="MANAGED",
                partition_columns=["date"],
                liquid_clustering_columns=["id"]  # Both set!
            )

    def test_partition_columns_only_valid(self):
        """Test that partition_columns alone is valid."""
        target = TargetConfig(
            target_id="tgt_test",
            target_name="Test Target",
            catalog_name="catalog",
            schema_name="schema",
            table_name="table",
            layer="BRONZE",
            table_type="MANAGED",
            partition_columns=["date"],
            liquid_clustering_columns=None
        )
        assert target.partition_columns == ["date"]

    def test_liquid_clustering_only_valid(self):
        """Test that liquid_clustering_columns alone is valid."""
        target = TargetConfig(
            target_id="tgt_test",
            target_name="Test Target",
            catalog_name="catalog",
            schema_name="schema",
            table_name="table",
            layer="BRONZE",
            table_type="MANAGED",
            partition_columns=None,
            liquid_clustering_columns=["id"]
        )
        assert target.liquid_clustering_columns == ["id"]

    def test_invalid_acord_entity_raises_error(self):
        """Test that invalid ACORD entity raises ValueError."""
        with pytest.raises(ValueError, match="invalid acord_entity"):
            TargetConfig(
                target_id="tgt_test",
                target_name="Test Target",
                catalog_name="catalog",
                schema_name="schema",
                table_name="table",
                layer="SILVER",
                table_type="MANAGED",
                acord_entity="InvalidEntity"
            )

    def test_valid_acord_entity_passes(self):
        """Test that valid ACORD entities pass validation."""
        for entity in ["Party", "Policy", "Coverage", "Claim", "Payment", "Loss"]:
            target = TargetConfig(
                target_id="tgt_test",
                target_name="Test Target",
                catalog_name="catalog",
                schema_name="schema",
                table_name="table",
                layer="SILVER",
                table_type="MANAGED",
                acord_entity=entity
            )
            assert target.acord_entity == entity


class TestLoadConfigValidation:
    """Tests for LoadConfig dataclass validation."""

    def test_stream_load_requires_checkpoint(self):
        """Test that STREAM_* loads require checkpoint_location."""
        with pytest.raises(ValueError, match="requires checkpoint_location"):
            LoadConfig(
                load_id="load_test",
                load_name="Test Load",
                source_id="src_test",
                target_id="tgt_test",
                load_type="STREAM_APPEND",
                load_pattern="APPEND",
                engine="AUTOLOADER",
                checkpoint_location=None  # Missing!
            )

    def test_stream_load_with_checkpoint_passes(self):
        """Test that STREAM_* loads with checkpoint_location pass."""
        load = LoadConfig(
            load_id="load_test",
            load_name="Test Load",
            source_id="src_test",
            target_id="tgt_test",
            load_type="STREAM_APPEND",
            load_pattern="APPEND",
            engine="AUTOLOADER",
            checkpoint_location="/checkpoints/test"
        )
        assert load.checkpoint_location == "/checkpoints/test"

    def test_declarative_engine_requires_append_or_scd2(self):
        """Test that DECLARATIVE engine requires APPEND or SCD2 pattern."""
        with pytest.raises(ValueError, match="APPEND.*SCD2"):
            LoadConfig(
                load_id="load_test",
                load_name="Test Load",
                source_id="src_test",
                target_id="tgt_test",
                load_type="BATCH_FULL",
                load_pattern="OVERWRITE",  # Invalid for DECLARATIVE
                engine="DECLARATIVE"
            )

    def test_merge_pattern_requires_merge_keys(self):
        """Test that MERGE pattern requires merge_keys."""
        with pytest.raises(ValueError, match="requires merge_keys"):
            LoadConfig(
                load_id="load_test",
                load_name="Test Load",
                source_id="src_test",
                target_id="tgt_test",
                load_type="BATCH_INCREMENTAL",
                load_pattern="MERGE",
                engine="STRUCTURED_STREAMING",
                merge_keys=None  # Missing!
            )


class TestTransformConfigValidation:
    """Tests for TransformConfig dataclass validation."""

    def test_source_and_destination_must_differ(self):
        """Test that source_target_id and destination_target_id must be different."""
        with pytest.raises(ValueError, match="must be different"):
            TransformConfig(
                transform_id="xform_test",
                transform_name="Test Transform",
                source_target_id="tgt_same",
                destination_target_id="tgt_same",  # Same as source!
                transform_type="SQL",
                transform_sql="SELECT * FROM table"
            )

    def test_scd2_declarative_requires_key_columns(self):
        """Test that SCD2 with DECLARATIVE requires key columns and timestamp."""
        with pytest.raises(ValueError, match="requires scd_key_columns and scd_timestamp_column"):
            TransformConfig(
                transform_id="xform_test",
                transform_name="Test Transform",
                source_target_id="tgt_source",
                destination_target_id="tgt_dest",
                transform_type="SQL",
                transform_sql="SELECT * FROM table",
                scd_type="SCD2",
                engine="DECLARATIVE",
                scd_key_columns=None,  # Missing!
                scd_timestamp_column=None  # Missing!
            )

    def test_sql_or_python_required(self):
        """Test that either transform_sql or transform_python must be specified."""
        with pytest.raises(ValueError, match="requires either transform_sql or transform_python"):
            TransformConfig(
                transform_id="xform_test",
                transform_name="Test Transform",
                source_target_id="tgt_source",
                destination_target_id="tgt_dest",
                transform_type="SQL",
                transform_sql=None,  # Both missing!
                transform_python=None
            )


class TestDQRuleConfigValidation:
    """Tests for DQRuleConfig dataclass validation."""

    def test_non_custom_sql_requires_column_name(self):
        """Test that non-CUSTOM_SQL rules require column_name."""
        with pytest.raises(ValueError, match="requires column_name"):
            DQRuleConfig(
                dq_rule_id="dq_test",
                rule_name="Test Rule",
                target_id="tgt_test",
                rule_type="NOT_NULL",
                column_name=None  # Missing!
            )

    def test_threshold_must_be_between_0_and_1(self):
        """Test that threshold_percent must be between 0 and 1."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            DQRuleConfig(
                dq_rule_id="dq_test",
                rule_name="Test Rule",
                target_id="tgt_test",
                rule_type="NOT_NULL",
                column_name="col1",
                threshold_percent=1.5  # Invalid!
            )

    def test_on_failure_must_be_valid_action(self):
        """Test that on_failure must be WARN, FAIL, or QUARANTINE."""
        with pytest.raises(ValueError, match="invalid on_failure"):
            DQRuleConfig(
                dq_rule_id="dq_test",
                rule_name="Test Rule",
                target_id="tgt_test",
                rule_type="NOT_NULL",
                column_name="col1",
                on_failure="IGNORE"  # Invalid!
            )

    def test_custom_sql_does_not_require_column_name(self):
        """Test that CUSTOM_SQL rules do not require column_name."""
        rule = DQRuleConfig(
            dq_rule_id="dq_test",
            rule_name="Test Rule",
            target_id="tgt_test",
            rule_type="CUSTOM_SQL",
            column_name=None,  # OK for CUSTOM_SQL
            rule_expression="SELECT COUNT(*) FROM table WHERE status IS NULL"
        )
        assert rule.rule_type == "CUSTOM_SQL"


# ========== Test Execution ==========

if __name__ == "__main__":
    # Run with: python -m pytest tests/test_config_loader.py -v --cov=sdk --cov-report=term-missing
    import subprocess
    subprocess.run([
        "python", "-m", "pytest",
        __file__,
        "-v",
        "--cov=sdk",
        "--cov-report=term-missing",
        "--cov-report=html"
    ])
