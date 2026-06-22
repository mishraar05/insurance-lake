# src/core/metadata/config_loader.py
"""ConfigLoader - Loads configuration from Unity Catalog tables."""
from pyspark.sql import SparkSession
from typing import Optional
import logging

from .source import SourceConfig, SourceType
from .target import TargetConfig
from .load import LoadConfig
from .transform import TransformConfig
from .dq_rule import DQRuleConfig
from core.sdk import ABC

logger = logging.getLogger(__name__)


class ConfigNotFoundError(Exception):
    """Raised when config entity not found."""
    pass


class FKViolationError(Exception):
    """Raised when FK constraint violated."""
    def __init__(self, fk_name: str, fk_value: str):
        self.fk_name = fk_name
        self.fk_value = fk_value
        super().__init__(f"FK violation: {fk_name} -> {fk_value}")


class ConfigLoader:
    """Loads configuration from Unity Catalog tables."""
    
    def __init__(
        self,
        catalog: str = "insurelake_config",
        schema: str = "config",
        spark: Optional[SparkSession] = None,
        abc: Optional[ABC] = None
    ):
        """Initialize ConfigLoader."""
        self.catalog = catalog
        self.schema = schema
        self.spark = spark or SparkSession.builder.getOrCreate()
        self.abc = abc
    
    def get_source(self, source_id: str) -> SourceConfig:
        """Retrieve source configuration by ID."""
        table_name = f"{self.catalog}.{self.schema}.cfg_source"
        
        try:
            df = self.spark.sql(f"""
                SELECT * FROM {table_name}
                WHERE source_id = '{source_id}' AND active_flag = true
            """)
            
            rows = df.collect()
            if not rows:
                raise ConfigNotFoundError(f"Source not found: {source_id}")
            
            row = rows[0]
            return SourceConfig(
                source_id=row.source_id,
                source_name=row.source_name,
                source_type=SourceType(row.source_type),
                source_system=row.source_system,
                connection_string=row.connection_string,
                file_format=row.file_format,
                schema_location=row.schema_location,
                credential_scope=row.credential_scope,
                credential_key=row.credential_key,
                business_domain=row.business_domain,
                pii_flag=row.pii_flag,
                data_classification=row.data_classification,
                sla_hours=row.sla_hours,
                active_flag=row.active_flag
            )
        except Exception as e:
            logger.error(f"Failed to load source {source_id}: {e}")
            if self.abc:
                self.abc.log_audit("config_loader", {
                    "event": "config_load_error",
                    "config_type": "source",
                    "config_id": source_id,
                    "error": str(e)
                })
            raise
    
    def get_target(self, target_id: str) -> TargetConfig:
        """Retrieve target configuration by ID."""
        table_name = f"{self.catalog}.{self.schema}.cfg_target"
        
        try:
            df = self.spark.sql(f"""
                SELECT * FROM {table_name}
                WHERE target_id = '{target_id}' AND active_flag = true
            """)
            
            rows = df.collect()
            if not rows:
                raise ConfigNotFoundError(f"Target not found: {target_id}")
            
            row = rows[0]
            return TargetConfig(
                target_id=row.target_id,
                target_name=row.target_name,
                catalog_name=row.catalog_name,
                schema_name=row.schema_name,
                table_name=row.table_name,
                layer=row.layer,
                table_type=row.table_type,
                format=row.format,
                partition_columns=row.partition_columns if row.partition_columns else [],
                liquid_clustering_columns=row.liquid_clustering_columns if row.liquid_clustering_columns else [],
                primary_key=row.primary_key if row.primary_key else [],
                acord_entity=row.acord_entity,
                retention_days=row.retention_days,
                enable_cdf=row.enable_cdf,
                dimensional=row.dimensional if hasattr(row, 'dimensional') else False,
                active_flag=row.active_flag
            )
        except Exception as e:
            logger.error(f"Failed to load target {target_id}: {e}")
            if self.abc:
                self.abc.log_audit("config_loader", {
                    "event": "config_load_error",
                    "config_type": "target",
                    "config_id": target_id,
                    "error": str(e)
                })
            raise
    
    def get_load(self, load_id: str) -> LoadConfig:
        """Retrieve load configuration by ID."""
        table_name = f"{self.catalog}.{self.schema}.cfg_load"
        
        try:
            df = self.spark.sql(f"""
                SELECT * FROM {table_name}
                WHERE load_id = '{load_id}' AND active_flag = true
            """)
            
            rows = df.collect()
            if not rows:
                raise ConfigNotFoundError(f"Load not found: {load_id}")
            
            row = rows[0]
            
            # Validate FK references
            try:
                self.get_source(row.source_id)
            except ConfigNotFoundError:
                raise FKViolationError("source_id", row.source_id)
            
            try:
                self.get_target(row.target_id)
            except ConfigNotFoundError:
                raise FKViolationError("target_id", row.target_id)
            
            return LoadConfig(
                load_id=row.load_id,
                load_name=row.load_name,
                source_id=row.source_id,
                target_id=row.target_id,
                load_type=row.load_type,
                load_pattern=row.load_pattern,
                engine=row.engine,
                watermark_column=row.watermark_column,
                watermark_type=row.watermark_type,
                checkpoint_location=row.checkpoint_location,
                trigger_interval=row.trigger_interval,
                merge_keys=row.merge_keys if row.merge_keys else None,
                autoloader_options=row.autoloader_options if row.autoloader_options else {},
                schedule_cron=row.schedule_cron,
                depends_on=row.depends_on if row.depends_on else None,
                source_system_type=row.source_system_type if hasattr(row, 'source_system_type') else "stable",
                governance_tier=row.governance_tier if hasattr(row, 'governance_tier') else "standard",
                zero_downtime=row.zero_downtime if hasattr(row, 'zero_downtime') else False,
                paranoid=row.paranoid if hasattr(row, 'paranoid') else False,
                type_changes=row.type_changes if hasattr(row, 'type_changes') else "none",
                renames_expected=row.renames_expected if hasattr(row, 'renames_expected') else False,
                active_flag=row.active_flag
            )
        except Exception as e:
            logger.error(f"Failed to load load config {load_id}: {e}")
            if self.abc:
                self.abc.log_audit("config_loader", {
                    "event": "config_load_error",
                    "config_type": "load",
                    "config_id": load_id,
                    "error": str(e)
                })
            raise
    
    def get_transform(self, transform_id: str) -> TransformConfig:
        """Retrieve transform configuration by ID."""
        table_name = f"{self.catalog}.{self.schema}.cfg_transform"
        
        try:
            df = self.spark.sql(f"""
                SELECT * FROM {table_name}
                WHERE transform_id = '{transform_id}' AND active_flag = true
            """)
            
            rows = df.collect()
            if not rows:
                raise ConfigNotFoundError(f"Transform not found: {transform_id}")
            
            row = rows[0]
            return TransformConfig(
                transform_id=row.transform_id,
                transform_name=row.transform_name,
                source_target_id=row.source_target_id,
                destination_target_id=row.destination_target_id,
                transform_type=row.transform_type,
                transform_sql=row.transform_sql,
                transform_python=row.transform_python,
                acord_mapping_template=row.acord_mapping_template,
                scd_type=row.scd_type,
                scd_key_columns=row.scd_key_columns if row.scd_key_columns else None,
                scd_timestamp_column=row.scd_timestamp_column,
                engine=row.engine,
                dependencies=row.dependencies if row.dependencies else None,
                active_flag=row.active_flag
            )
        except Exception as e:
            logger.error(f"Failed to load transform {transform_id}: {e}")
            if self.abc:
                self.abc.log_audit("config_loader", {
                    "event": "config_load_error",
                    "config_type": "transform",
                    "config_id": transform_id,
                    "error": str(e)
                })
            raise
    
    def get_dq_rule(self, dq_rule_id: str) -> DQRuleConfig:
        """Retrieve DQ rule configuration by ID."""
        table_name = f"{self.catalog}.{self.schema}.cfg_dq_rule"
        
        try:
            df = self.spark.sql(f"""
                SELECT * FROM {table_name}
                WHERE dq_rule_id = '{dq_rule_id}' AND active_flag = true
            """)
            
            rows = df.collect()
            if not rows:
                raise ConfigNotFoundError(f"DQ rule not found: {dq_rule_id}")
            
            row = rows[0]
            return DQRuleConfig(
                dq_rule_id=row.dq_rule_id,
                rule_name=row.rule_name,
                target_id=row.target_id,
                rule_type=row.rule_type,
                column_name=row.column_name,
                rule_expression=row.rule_expression,
                threshold_percent=row.threshold_percent,
                on_failure=row.on_failure,
                active_flag=row.active_flag
            )
        except Exception as e:
            logger.error(f"Failed to load DQ rule {dq_rule_id}: {e}")
            if self.abc:
                self.abc.log_audit("config_loader", {
                    "event": "config_load_error",
                    "config_type": "dq_rule",
                    "config_id": dq_rule_id,
                    "error": str(e)
                })
            raise
    
    def save_source(self, config: SourceConfig) -> None:
        """Save source configuration."""
        table_name = f"{self.catalog}.{self.schema}.cfg_source"
        
        # Log config change via ABC
        if self.abc:
            self.abc.log_audit("config_loader", {
                "event": "config_save",
                "config_type": "source",
                "config_id": config.source_id
            })
        
        # Insert/update logic would go here
        # For now, placeholder
        raise NotImplementedError("save_source not yet implemented")
    
    def save_target(self, config: TargetConfig) -> None:
        """Save target configuration."""
        table_name = f"{self.catalog}.{self.schema}.cfg_target"
        
        # Log config change via ABC
        if self.abc:
            self.abc.log_audit("config_loader", {
                "event": "config_save",
                "config_type": "target",
                "config_id": config.target_id
            })
        
        # Insert/update logic would go here
        # For now, placeholder
        raise NotImplementedError("save_target not yet implemented")
    
    def save_load(self, config: LoadConfig) -> None:
        """Save load configuration."""
        table_name = f"{self.catalog}.{self.schema}.cfg_load"
        
        # Log config change via ABC
        if self.abc:
            self.abc.log_audit("config_loader", {
                "event": "config_save",
                "config_type": "load",
                "config_id": config.load_id
            })
        
        # Insert/update logic would go here
        # For now, placeholder
        raise NotImplementedError("save_load not yet implemented")
