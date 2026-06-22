# src/core/sdk/exceptions.py
"""Exception classes for ABC SDK."""


class ABCConnectionError(Exception):
    """Raised when cannot connect to ABC catalog/schema."""
    pass


class ABCWriteError(Exception):
    """Raised when write to ABC table fails."""
    pass


class ABCValidationError(ValueError):
    """Raised when input validation fails."""
    pass
