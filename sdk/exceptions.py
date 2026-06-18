"""
Custom exceptions for InsureLake SDK.

Provides clear, actionable error messages for config validation failures.
"""

class InsureLakeSDKError(Exception):
    """Base exception for all InsureLake SDK errors."""
    pass


class ConfigNotFoundError(InsureLakeSDKError):
    """Raised when a config entity is not found in Unity Catalog."""
    
    def __init__(self, entity_type: str, entity_id: str, available_ids: list = None):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.available_ids = available_ids or []
        
        message = f"{entity_type} '{entity_id}' not found in config.{entity_type.lower()}"
        if self.available_ids:
            message += f". Available {entity_type}s: {self.available_ids[:10]}"
            if len(self.available_ids) > 10:
                message += f" (and {len(self.available_ids) - 10} more)"
        
        super().__init__(message)


class ConfigValidationError(InsureLakeSDKError):
    """Raised when config validation fails."""
    
    def __init__(self, entity_type: str, entity_id: str, validation_errors: list):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.validation_errors = validation_errors
        
        message = f"Validation failed for {entity_type} '{entity_id}':\n"
        for error in validation_errors:
            message += f"  - {error}\n"
        
        super().__init__(message.rstrip())


class ForeignKeyError(ConfigValidationError):
    """Raised when a foreign key reference is invalid."""
    
    def __init__(self, entity_type: str, entity_id: str, fk_field: str, fk_value: str, referenced_type: str):
        self.fk_field = fk_field
        self.fk_value = fk_value
        self.referenced_type = referenced_type
        
        error_msg = (
            f"Foreign key violation: {fk_field}='{fk_value}' references non-existent "
            f"{referenced_type}. Check config.{referenced_type.lower()} table."
        )
        
        super().__init__(entity_type, entity_id, [error_msg])


class CircularDependencyError(ConfigValidationError):
    """Raised when circular dependencies are detected."""
    
    def __init__(self, cycle: list):
        self.cycle = cycle
        
        cycle_str = " -> ".join(cycle + [cycle[0]])
        error_msg = f"Circular dependency detected: {cycle_str}"
        
        super().__init__("Dependency", "dependency_graph", [error_msg])


class InvalidConfigError(ConfigValidationError):
    """Raised when config has invalid field values."""
    pass


class CatalogConnectionError(InsureLakeSDKError):
    """Raised when unable to connect to Unity Catalog."""
    
    def __init__(self, catalog: str, schema: str, original_error: Exception):
        self.catalog = catalog
        self.schema = schema
        self.original_error = original_error
        
        message = (
            f"Failed to connect to Unity Catalog {catalog}.{schema}. "
            f"Error: {str(original_error)}"
        )
        
        super().__init__(message)
