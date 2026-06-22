# src/core/sdk/abc.py
"""ABC SDK - Single interface for Audit/Balance/Control logging."""
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, List
from pyspark.sql import SparkSession
import logging

from .run_handle import RunHandle
from .exceptions import ABCConnectionError, ABCWriteError, ABCValidationError

logger = logging.getLogger(__name__)


class ABC:
    """
    ABC SDK - Single interface for Audit/Balance/Control logging.
    
    Usage:
        abc = ABC(catalog="insurelake_abc", schema="abc")
        run = abc.start_run(component="ingestion", entity="policy", run_type="BATCH_INCREMENTAL")
        abc.log_audit(run.run_id, {"rows_read": 10000, "rows_written": 9980})
        abc.end_run(run.run_id, status="SUCCESS")
    """
    
    def __init__(
        self,
        catalog: str = "insurelake_abc",
        schema: str = "abc",
        spark: Optional[SparkSession] = None
    ):
        """Initialize ABC SDK."""
        self.catalog = catalog
        self.schema = schema
        self.spark = spark or SparkSession.builder.getOrCreate()
        self._start_times: Dict[str, datetime] = {}
        
        # Validate connectivity
        try:
            self.spark.sql(f"USE CATALOG {self.catalog}")
            self.spark.sql(f"USE SCHEMA {self.schema}")
        except Exception as e:
            raise ABCConnectionError(
                f"Cannot connect to {self.catalog}.{self.schema}: {e}"
            )
    
    def start_run(
        self,
        component: str,
        entity: str,
        run_type: str,
        trace_id: Optional[str] = None
    ) -> RunHandle:
        """
        Start a new run and return RunHandle.
        
        Args:
            component: Framework component (ingestion, harmonization, dq, etc.)
            entity: Entity being processed (policy, claim, payment, etc.)
            run_type: BATCH_FULL, BATCH_INCREMENTAL, STREAM_APPEND, etc.
            trace_id: Optional trace ID (if propagating from upstream)
        
        Returns:
            RunHandle with run_id and trace_id
        """
        # Validation
        if not component or not entity:
            raise ABCValidationError("component and entity must not be NULL")
        
        # Generate IDs
        run_id = str(uuid.uuid4())
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        # Record start time
        start_ts = datetime.now()
        self._start_times[run_id] = start_ts
        
        # Insert RUNNING status into abc_audit
        try:
            self.spark.sql(f"""
                INSERT INTO {self.catalog}.{self.schema}.abc_audit
                (run_id, trace_id, component, entity, run_type, status, start_ts, created_ts)
                VALUES (
                    '{run_id}',
                    '{trace_id}',
                    '{component}',
                    '{entity}',
                    '{run_type}',
                    'RUNNING',
                    '{start_ts.isoformat()}',
                    '{datetime.now().isoformat()}'
                )
            """)
        except Exception as e:
            logger.warning(f"Failed to write to abc_audit: {e}")
            self._write_local_fallback("abc_audit", {
                "run_id": run_id,
                "trace_id": trace_id,
                "component": component,
                "entity": entity,
                "run_type": run_type,
                "status": "RUNNING",
                "start_ts": start_ts.isoformat()
            })
        
        return RunHandle(run_id=run_id, trace_id=trace_id)
    
    def end_run(
        self,
        run_id: str,
        status: str,
        metrics: Optional[Dict] = None
    ):
        """
        Close a run with final status.
        
        Args:
            run_id: Run ID from start_run()
            status: SUCCESS, FAILED, TIMEOUT
            metrics: Optional final metrics dict
        """
        # Validation
        if status not in ["SUCCESS", "FAILED", "TIMEOUT"]:
            raise ABCValidationError(
                f"Invalid status: {status}. Must be SUCCESS, FAILED, or TIMEOUT"
            )
        
        # Calculate duration
        end_ts = datetime.now()
        duration_seconds = None
        if run_id in self._start_times:
            duration_seconds = (end_ts - self._start_times[run_id]).total_seconds()
            del self._start_times[run_id]
        
        # Build update clause
        update_fields = [
            f"status = '{status}'",
            f"end_ts = '{end_ts.isoformat()}'"
        ]
        if duration_seconds is not None:
            update_fields.append(f"duration_seconds = {duration_seconds}")
        
        # Merge metrics if provided
        if metrics:
            for key, value in metrics.items():
                if key in ["rows_read", "rows_written", "rows_rejected"]:
                    update_fields.append(f"{key} = {value}")
        
        # Update abc_audit (idempotent)
        try:
            self.spark.sql(f"""
                MERGE INTO {self.catalog}.{self.schema}.abc_audit AS target
                USING (SELECT '{run_id}' AS run_id) AS source
                ON target.run_id = source.run_id
                WHEN MATCHED THEN UPDATE SET {', '.join(update_fields)}
            """)
        except Exception as e:
            logger.warning(f"Failed to update abc_audit: {e}")
            self._write_local_fallback("abc_audit_update", {
                "run_id": run_id,
                "status": status,
                "end_ts": end_ts.isoformat(),
                "duration_seconds": duration_seconds,
                "metrics": metrics
            })
    
    def log_audit(self, run_id: str, metrics: Dict):
        """Log audit metrics (rows read/written/rejected, timings)."""
        if not run_id:
            raise ABCValidationError("run_id must not be NULL")
        
        # Build update clause from metrics
        update_fields = []
        for key, value in metrics.items():
            if key in ["rows_read", "rows_written", "rows_rejected", "duration_seconds"]:
                update_fields.append(f"{key} = {value}")
            elif key == "identity":
                update_fields.append(f"identity = '{value}'")
            elif key == "spark_job_id":
                update_fields.append(f"spark_job_id = '{value}'")
        
        if not update_fields:
            logger.warning(f"No valid audit metrics provided for run_id {run_id}")
            return
        
        # Idempotent update
        try:
            self.spark.sql(f"""
                MERGE INTO {self.catalog}.{self.schema}.abc_audit AS target
                USING (SELECT '{run_id}' AS run_id) AS source
                ON target.run_id = source.run_id
                WHEN MATCHED THEN UPDATE SET {', '.join(update_fields)}
            """)
        except Exception as e:
            logger.warning(f"Failed to log_audit: {e}")
            self._write_local_fallback("abc_audit_metrics", {
                "run_id": run_id,
                "metrics": metrics
            })
    
    def log_balance(self, run_id: str, checks: List[Dict]):
        """Log balance checks (count + financial reconciliation)."""
        if not run_id:
            raise ABCValidationError("run_id must not be NULL")
        
        for check in checks:
            # Validation
            if "source_value" not in check or "target_value" not in check:
                raise ABCValidationError(
                    "Balance checks must include source_value and target_value"
                )
            
            balance_id = str(uuid.uuid4())
            source_value = check["source_value"]
            target_value = check["target_value"]
            variance = source_value - target_value
            threshold = check.get("threshold_percent", 0.0)
            
            # Calculate variance percent
            variance_percent = 0.0
            if source_value > 0:
                variance_percent = (variance / source_value) * 100
            
            # Check if balanced
            balanced = abs(variance_percent) <= threshold
            
            # Insert balance check (idempotent on balance_id)
            try:
                self.spark.sql(f"""
                    INSERT INTO {self.catalog}.{self.schema}.abc_balance
                    (balance_id, run_id, check_name, check_type, source_ref, source_value,
                     target_ref, target_value, variance, variance_percent, threshold_percent,
                     balanced, created_ts)
                    VALUES (
                        '{balance_id}',
                        '{run_id}',
                        '{check.get("check_name", "unnamed")}',
                        '{check.get("check_type", "COUNT")}',
                        '{check.get("source_ref", "")}',
                        {source_value},
                        '{check.get("target_ref", "")}',
                        {target_value},
                        {variance},
                        {variance_percent},
                        {threshold},
                        {balanced},
                        '{datetime.now().isoformat()}'
                    )
                """)
            except Exception as e:
                logger.warning(f"Failed to log_balance: {e}")
                self._write_local_fallback("abc_balance", check)
    
    def log_dq(self, run_id: str, results: List[Dict]):
        """Log DQ rule outcomes."""
        if not run_id:
            raise ABCValidationError("run_id must not be NULL")
        
        for result in results:
            control_id = str(uuid.uuid4())
            
            # Insert DQ result (idempotent on control_id)
            try:
                self.spark.sql(f"""
                    INSERT INTO {self.catalog}.{self.schema}.abc_control
                    (control_id, run_id, control_type, rule_id, rule_name, target_table,
                     column_name, check_result, failed_count, action_taken, created_ts)
                    VALUES (
                        '{control_id}',
                        '{run_id}',
                        'DQ_RULE',
                        '{result.get("rule_id", "")}',
                        '{result.get("rule_name", "")}',
                        '{result.get("target_table", "")}',
                        '{result.get("column_name", "")}',
                        '{result.get("check_result", "UNKNOWN")}',
                        {result.get("failed_count", 0)},
                        '{result.get("action_taken", "WARN")}',
                        '{datetime.now().isoformat()}'
                    )
                """)
            except Exception as e:
                logger.warning(f"Failed to log_dq: {e}")
                self._write_local_fallback("abc_control", result)
    
    def log_exception(self, run_id: str, error: Exception):
        """Log structured exception."""
        if not run_id:
            raise ABCValidationError("run_id must not be NULL")
        
        control_id = str(uuid.uuid4())
        error_message = str(error)
        stack_trace = ""
        
        # Get stack trace if available
        import traceback
        stack_trace = traceback.format_exc()
        
        # Insert exception (idempotent on control_id)
        try:
            # Escape single quotes in error message and stack trace
            error_message_escaped = error_message.replace("'", "''")
            stack_trace_escaped = stack_trace.replace("'", "''")
            
            self.spark.sql(f"""
                INSERT INTO {self.catalog}.{self.schema}.abc_control
                (control_id, run_id, control_type, error_message, stack_trace, created_ts)
                VALUES (
                    '{control_id}',
                    '{run_id}',
                    'EXCEPTION',
                    '{error_message_escaped}',
                    '{stack_trace_escaped}',
                    '{datetime.now().isoformat()}'
                )
            """)
        except Exception as e:
            logger.warning(f"Failed to log_exception: {e}")
            self._write_local_fallback("abc_control_exception", {
                "run_id": run_id,
                "error_message": error_message,
                "stack_trace": stack_trace
            })
    
    def log_cost(self, run_id: str, consumption: Dict):
        """Log cost and consumption metrics."""
        if not run_id:
            raise ABCValidationError("run_id must not be NULL")
        
        cost_id = str(uuid.uuid4())
        
        # Insert cost record (idempotent on cost_id)
        try:
            self.spark.sql(f"""
                INSERT INTO {self.catalog}.{self.schema}.abc_cost
                (cost_id, run_id, component, entity, dbu_seconds, dbu_count,
                 sql_warehouse_seconds, cost_usd, cluster_id, warehouse_id, created_ts)
                VALUES (
                    '{cost_id}',
                    '{run_id}',
                    '{consumption.get("component", "")}',
                    '{consumption.get("entity", "")}',
                    {consumption.get("dbu_seconds", 0.0)},
                    {consumption.get("dbu_count", 0.0)},
                    {consumption.get("sql_warehouse_seconds", 0.0)},
                    {consumption.get("cost_usd", 0.0)},
                    '{consumption.get("cluster_id", "")}',
                    '{consumption.get("warehouse_id", "")}',
                    '{datetime.now().isoformat()}'
                )
            """)
        except Exception as e:
            logger.warning(f"Failed to log_cost: {e}")
            self._write_local_fallback("abc_cost", consumption)
    
    def _write_local_fallback(self, table_name: str, data: Dict):
        """Write ABC entry to local JSON file if Delta writes fail."""
        try:
            import os
            fallback_dir = "/tmp/abc_fallback"
            os.makedirs(fallback_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{fallback_dir}/{table_name}_{timestamp}_{uuid.uuid4()}.json"
            
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"ABC fallback written to {filename}")
        except Exception as e:
            logger.error(f"Failed to write ABC fallback: {e}")
