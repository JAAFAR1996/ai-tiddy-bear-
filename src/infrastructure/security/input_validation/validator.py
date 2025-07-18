"""from typing import Dict, Any, Optional
import json
import logging
from .core import InputValidationResult, SecurityThreat
from .detectors import ThreatDetectors
from src.infrastructure.security.comprehensive_audit_integration import get_audit_integration.
"""

"""Main input validation service implementation."""

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="security")


class ComprehensiveInputValidator(ThreatDetectors):
    """Comprehensive input validator with security threat detection and child safety.
    Features:
    - SQL injection detection
    - XSS attack prevention
    - Path traversal detection
    - LDAP injection detection
    - Command injection detection
    - Child - inappropriate content detection
    - PII detection and sanitization
    - File upload validation
    - Request size limits.
    """

    def __init__(self):
        super().__init__()
        self.audit_integration = get_audit_integration()

    async def validate_input(
        self,
        data: Any,
        field_name: str = "input",
        context: Optional[Dict[str, Any]] = None,
    ) -> InputValidationResult:
        """Validate input data for security threats and child safety.

        Args:
            data: Input data to validate
            field_name: Name of the field being validated
            context: Additional context(user info, endpoint, etc.)

        Returns:
            InputValidationResult with validation results

        """
        threats = []
        errors = []
        child_safety_violations = []

        try:
            # Convert data to string for pattern matching
            if isinstance(data, dict):
                text_data = json.dumps(data)
            elif isinstance(data, list | int | float | bool):
                text_data = str(data)
            elif data is None:
                return InputValidationResult(True)
            else:
                text_data = str(data)

            # Check for security threats
            threats.extend(
                await self.detect_sql_injection(text_data, field_name)
            )
            threats.extend(await self.detect_xss(text_data, field_name))
            threats.extend(
                await self.detect_path_traversal(text_data, field_name)
            )
            threats.extend(
                await self.detect_command_injection(text_data, field_name)
            )
            threats.extend(
                await self.detect_ldap_injection(text_data, field_name)
            )
            threats.extend(
                await self.detect_template_injection(text_data, field_name)
            )

            # Check for child safety issues
            child_safety_violations.extend(
                await self.detect_inappropriate_content(text_data, field_name),
            )
            child_safety_violations.extend(
                await self.detect_pii(text_data, field_name)
            )

            # Validate input size
            if len(text_data) > 100000:  # 100KB limit
                threats.append(
                    SecurityThreat(
                        "oversized_input",
                        "high",
                        field_name,
                        text_data[:100],
                        "Input exceeds maximum size limit",
                    ),
                )

            # Check for encoding attacks
            threats.extend(
                await self.detect_encoding_attacks(text_data, field_name)
            )

            # Determine if input is valid
            critical_threats = [t for t in threats if t.severity == "critical"]
            high_threats = [t for t in threats if t.severity == "high"]
            is_valid = (
                len(critical_threats) == 0
                and len(high_threats) == 0
                and len(child_safety_violations) == 0
            )

            return InputValidationResult(
                is_valid=is_valid,
                threats=threats,
                errors=errors,
                child_safety_violations=child_safety_violations,
            )
        except Exception as e:
            logger.error(f"Input validation error for {field_name}: {e}")
            errors.append(f"Validation failed: {e!s}")
            return InputValidationResult(
                False,
                threats,
                errors,
                child_safety_violations,
            )


# Global validator instance for direct use
_global_validator: Optional[ComprehensiveInputValidator] = None


def get_input_validator() -> ComprehensiveInputValidator:
    """Get global input validator instance."""
    global _global_validator
    if _global_validator is None:
        _global_validator = ComprehensiveInputValidator()
    return _global_validator


# Convenience functions for manual validation
async def validate_user_input(
    data: Any,
    field_name: str = "input",
    require_child_safe: bool = False,
) -> InputValidationResult:
    """Validate user input manually."""
    validator = get_input_validator()
    result = await validator.validate_input(data, field_name)
    if require_child_safe and result.child_safety_violations:
        result.is_valid = False
    return result


async def validate_child_message(message: str) -> InputValidationResult:
    """Validate message content for child safety."""
    return await validate_user_input(
        message, "message", require_child_safe=True
    )
