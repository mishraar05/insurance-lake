"""
Config Loader for InsureLake framework.

Loads and validates metadata/config from Unity Catalog Delta tables.
"""

from typing import List, Optional, Dict
from pyspark.sql import SparkSession

from ..metadata import (
    SourceConfig,
    TargetConfig,
    LoadConfig,
    TransformConfig,
    DQRuleConfig,
)
from ..common.exceptions import (
    ConfigNotFoundError,
    ConfigValidationError,
    CatalogConnectionError,
    ForeignKeyError,
    CircularDependencyError,
)


class ConfigLoader:
    """
    Loads configuration metadata from Unity Catalog.
    
    All config entities are stored as Delta tables in Unity Catalog
    and loaded on-demand with validation.
    
    Example:
        loader = ConfigLoader(catalog="insurelake_config", schema="config")
        load_config = loader.get_load("load_policy_batch")
        source = loader.get_source(load_config.source_id)
    """
    
    def __init__(self, catalog: str = "insurelake_config", schema: str = "config"):
        """
        Initialize ConfigLoader.
        
        Args:
            catalog: Unity Catalog catalog name
            schema: Unity Catalog schema name
        """
        self.catalog = catalog
        self.schema = schema
        self.spark = SparkSession.getActiveSession()
        
        if not self.spark:
            raise RuntimeError("No active Spark session. ConfigLoader requires Spark.")
        
        # Verify catalog and schema exist
        self._verify_catalog_connection()
    
    def _verify_catalog_connection(self):
        """Verify connection to Unity Catalog catalog and schema."""
        try:
            self.spark.sql(f"USE CATALOG {self.catalog}")
            self.spark.sql(f"USE SCHEMA {self.schema}")
        except Exception as e:
            raise CatalogConnectionError(self.catalog, self.schema, e)
    
    def _get_table_fqn(self, table_name: str) -> str:
        """Get fully qualified table name."""
        return f"{self.catalog}.{self.schema}.{table_name}"
    
    def _load_entity(self, table_name: str, id_column: str, entity_id: str):
        """Generic method to load an entity from a config table."""
        fqn = self._get_table_fqn(table_name)
        
        try:
            df = self.spark.table(fqn)
            result = df.filter(f"{id_column} = '{entity_id}'").collect()
            
            if not result:
                # Get available IDs for helpful error message
                available_ids = [row[id_column] for row in df.select(id_column).limit(50).collect()]
                raise ConfigNotFoundError(
                    entity_type=table_name.upper(),
                    entity_id=entity_id,
                    available_ids=available_ids
                )
            
            return result[0]
        except ConfigNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error loading {table_name} '{entity_id}': {str(e)}")
    
    # ========== Source ==========
    
    def get_source(self, source_id: str) -> SourceConfig:
        """
        Load a Source config by ID.
        
        Args:
            source_id: Unique source identifier
            
        Returns:
            SourceConfig object
            
        Raises:
            ConfigNotFoundError: If source_id not found
        """
        row = self._load_entity("source", "source_id", source_id)
        return SourceConfig.from_row(row)
    
    def list_sources(self, business_domain: Optional[str] = None, active_only: bool = True) -> List[SourceConfig]:
        """
        List all sources, optionally filtered.
        
        Args:
            business_domain: Filter by business domain (POLICY, CLAIM, etc.)
            active_only: Only return active sources
            
        Returns:
            List of SourceConfig objects
        """
        fqn = self._get_table_fqn("source")
        df = self.spark.table(fqn)
        
        if active_only:
            df = df.filter("active_flag = true")
        
        if business_domain:
            df = df.filter(f"business_domain = '{business_domain}'")
        
        return [SourceConfig.from_row(row) for row in df.collect()]
    
    # ========== Target ==========
    
    def get_target(self, target_id: str) -> TargetConfig:
        """
        Load a Target config by ID.
        
        Args:
            target_id: Unique target identifier
            
        Returns:
            TargetConfig object
            
        Raises:
            ConfigNotFoundError: If target_id not found
        """
        row = self._load_entity("target", "target_id", target_id)
        return TargetConfig.from_row(row)
    
    def get_target_by_fqn(self, catalog: str, schema: str, table: str) -> TargetConfig:
        """
        Load a Target config by fully qualified table name.
        
        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            
        Returns:
            TargetConfig object
            
        Raises:
            ConfigNotFoundError: If target not found
        """
        fqn = self._get_table_fqn("target")
        df = self.spark.table(fqn)
        result = df.filter(
            f"catalog_name = '{catalog}' AND schema_name = '{schema}' AND table_name = '{table}'"
        ).collect()
        
        if not result:
            raise ConfigNotFoundError(
                entity_type="TARGET",
                entity_id=f"{catalog}.{schema}.{table}",
                available_ids=[]
            )
        
        return TargetConfig.from_row(result[0])
    
    def list_targets(self, layer: Optional[str] = None, active_only: bool = True) -> List[TargetConfig]:
        """
        List all targets, optionally filtered.
        
        Args:
            layer: Filter by medallion layer (BRONZE, SILVER, GOLD)
            active_only: Only return active targets
            
        Returns:
            List of TargetConfig objects
        """
        fqn = self._get_table_fqn("target")
        df = self.spark.table(fqn)
        
        if active_only:
            df = df.filter("active_flag = true")
        
        if layer:
            df = df.filter(f"layer = '{layer}'")
        
        return [TargetConfig.from_row(row) for row in df.collect()]
    
    # ========== Load ==========
    
    def get_load(self, load_id: str) -> LoadConfig:
        """
        Load a Load config by ID.
        
        Args:
            load_id: Unique load identifier
            
        Returns:
            LoadConfig object with foreign keys validated
            
        Raises:
            ConfigNotFoundError: If load_id not found
            ForeignKeyError: If source_id or target_id references don't exist
        """
        row = self._load_entity("load", "load_id", load_id)
        load_config = LoadConfig.from_row(row)
        
        # Validate foreign keys
        try:
            self.get_source(load_config.source_id)
        except ConfigNotFoundError:
            raise ForeignKeyError(
                entity_type="Load",
                entity_id=load_id,
                fk_field="source_id",
                fk_value=load_config.source_id,
                referenced_type="Source"
            )
        
        try:
            self.get_target(load_config.target_id)
        except ConfigNotFoundError:
            raise ForeignKeyError(
                entity_type="Load",
                entity_id=load_id,
                fk_field="target_id",
                fk_value=load_config.target_id,
                referenced_type="Target"
            )
        
        return load_config
    
    def list_loads(self, active_only: bool = True) -> List[LoadConfig]:
        """
        List all loads.
        
        Args:
            active_only: Only return active loads
            
        Returns:
            List of LoadConfig objects
        """
        fqn = self._get_table_fqn("load")
        df = self.spark.table(fqn)
        
        if active_only:
            df = df.filter("active_flag = true")
        
        return [LoadConfig.from_row(row) for row in df.collect()]
    
    # ========== Transform ==========
    
    def get_transform(self, transform_id: str) -> TransformConfig:
        """
        Load a Transform config by ID.
        
        Args:
            transform_id: Unique transform identifier
            
        Returns:
            TransformConfig object with foreign keys validated
            
        Raises:
            ConfigNotFoundError: If transform_id not found
            ForeignKeyError: If target references don't exist
        """
        row = self._load_entity("transform", "transform_id", transform_id)
        transform_config = TransformConfig.from_row(row)
        
        # Validate foreign keys
        try:
            self.get_target(transform_config.source_target_id)
        except ConfigNotFoundError:
            raise ForeignKeyError(
                entity_type="Transform",
                entity_id=transform_id,
                fk_field="source_target_id",
                fk_value=transform_config.source_target_id,
                referenced_type="Target"
            )
        
        try:
            self.get_target(transform_config.destination_target_id)
        except ConfigNotFoundError:
            raise ForeignKeyError(
                entity_type="Transform",
                entity_id=transform_id,
                fk_field="destination_target_id",
                fk_value=transform_config.destination_target_id,
                referenced_type="Target"
            )
        
        return transform_config
    
    def get_transforms_by_target(self, target_id: str, upstream: bool = False) -> List[TransformConfig]:
        """
        Find all transforms that read from or write to a target.
        
        Args:
            target_id: Target ID to search for
            upstream: If True, find transforms reading FROM this target (upstream).
                     If False, find transforms writing TO this target (downstream).
            
        Returns:
            List of TransformConfig objects
        """
        fqn = self._get_table_fqn("transform")
        df = self.spark.table(fqn)
        
        if upstream:
            df = df.filter(f"source_target_id = '{target_id}'")
        else:
            df = df.filter(f"destination_target_id = '{target_id}'")
        
        return [TransformConfig.from_row(row) for row in df.collect()]
    
    # ========== DQ Rules ==========
    
    def get_dq_rule(self, dq_rule_id: str) -> DQRuleConfig:
        """
        Load a DQ rule by ID.
        
        Args:
            dq_rule_id: Unique DQ rule identifier
            
        Returns:
            DQRuleConfig object
            
        Raises:
            ConfigNotFoundError: If dq_rule_id not found
        """
        row = self._load_entity("dq_rule", "dq_rule_id", dq_rule_id)
        return DQRuleConfig.from_row(row)
    
    def get_dq_rules_by_target(self, target_id: str) -> List[DQRuleConfig]:
        """
        Get all DQ rules for a target.
        
        Args:
            target_id: Target ID
            
        Returns:
            List of DQRuleConfig objects for this target
        """
        fqn = self._get_table_fqn("dq_rule")
        df = self.spark.table(fqn)
        df = df.filter(f"target_id = '{target_id}' AND active_flag = true")
        
        return [DQRuleConfig.from_row(row) for row in df.collect()]
    
    # ========== Workflow Graph ==========
    
    def get_workflow_graph(self, load_id: Optional[str] = None) -> Dict:
        """
        Build a complete execution graph showing dependencies.
        
        Args:
            load_id: Optional load_id to start from. If None, returns entire graph.
            
        Returns:
            Dictionary representing the workflow DAG
        """
        # This is a simplified version - full implementation would build a proper DAG
        loads = self.list_loads() if not load_id else [self.get_load(load_id)]
        
        graph = {
            "loads": [load.to_dict() for load in loads],
            "sources": [],
            "targets": [],
        }
        
        # Add referenced sources and targets
        source_ids = set()
        target_ids = set()
        
        for load in loads:
            source_ids.add(load.source_id)
            target_ids.add(load.target_id)
        
        for source_id in source_ids:
            graph["sources"].append(self.get_source(source_id).to_dict())
        
        for target_id in target_ids:
            graph["targets"].append(self.get_target(target_id).to_dict())
        
        return graph
