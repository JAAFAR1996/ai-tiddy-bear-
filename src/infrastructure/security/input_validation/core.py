"""from datetime import datetime
from typing import List, Optional
import re.
"""

"""Core input validation models and threat detection classes."""


class SecurityThreat:
    """Represents a detected security threat in input."""

    def __init__(
        self,
        threat_type: str,
        severity: str,
        field: str,
        value: str,
        description: str,
    ) -> None:
        self.threat_type = threat_type
        self.severity = severity
        self.field = field
        self.value = value[:100]  # Limit stored value for security
        self.description = description
        self.detected_at = datetime.utcnow()


class InputValidationResult:
    """Result of input validation check."""

    def __init__(
        self,
        is_valid: bool,
        threats: Optional[List[SecurityThreat]] = None,
        errors: Optional[List[str]] = None,
        child_safety_violations: Optional[List[str]] = None,
    ) -> None:
        self.is_valid = is_valid
        self.threats = threats or []
        self.errors = errors or []
        self.child_safety_violations = child_safety_violations or []
        self.has_critical_threats = any(
            t.severity == "critical" for t in self.threats
        )
        self.has_child_safety_issues = len(self.child_safety_violations) > 0
