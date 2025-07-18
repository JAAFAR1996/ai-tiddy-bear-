"""from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any.
"""

"""Validation Types and Common Structures
Provides shared types and enums for the validation system."""


@dataclass
class ValidationResult:
    """Structured validation result with comprehensive metadata."""

    valid: bool
    sanitized_value: Optional[Any] = None
    original_value: Optional[Any] = None
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    security_flags: List[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
        if self.security_flags is None:
            self.security_flags = []


class ValidationSeverity(Enum):
    """Validation issue severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationError(Exception):
    """Custom exception for validation errors.
    Provides structured error information for debugging and user feedback.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        code: str | None = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "message": self.message,
            "field": self.field,
            "code": self.code,
            "severity": self.severity.value,
        }
