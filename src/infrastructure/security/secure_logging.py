"""Secure Logging Utilities for COPPA Compliance
This module provides secure logging functions that automatically
sanitize sensitive data to ensure COPPA compliance and child privacy.

COPPA CONDITIONAL: COPPA-specific audit logging is conditional on ENABLE_COPPA_COMPLIANCE.
When disabled, uses standard logging without COPPA audit requirements.
"""

import hashlib
import re
from collections.abc import Callable
from typing import Any

from src.infrastructure.logging_config import get_logger

from ..config.coppa_config import requires_coppa_audit_logging


class SecureLogger:
    """Secure logging utility that sanitizes sensitive data."""

    def __init__(self, name: str) -> None:
        self._logger = get_logger(name, component="security")
        self._salt = (
            "teddy_bear_secure_log_2025"  # Static salt for consistent hashing
        )

    def _sanitize_child_id(self, child_id: str) -> str:
        """Convert child_id to a safe hash for logging."""
        if not child_id:
            return "[EMPTY_CHILD_ID]"

        # Create a consistent hash that's safe for logging
        hash_obj = hashlib.sha256(f"{self._salt}_{child_id}".encode())
        short_hash = hash_obj.hexdigest()[:8]
        return f"child_{short_hash}"

    def _sanitize_parent_id(self, parent_id: str) -> str:
        """Convert parent_id to a safe hash for logging."""
        if not parent_id:
            return "[EMPTY_PARENT_ID]"

        hash_obj = hashlib.sha256(f"{self._salt}_{parent_id}".encode())
        short_hash = hash_obj.hexdigest()[:8]
        return f"parent_{short_hash}"

    def _sanitize_email(self, email: str) -> str:
        """Mask email address for logging."""
        if not email or "@" not in email:
            return "[INVALID_EMAIL]"

        parts = email.split("@")
        masked_local = "***" if len(parts[0]) <= 2 else parts[0][:2] + "***"

        return f"{masked_local}@{parts[1]}"

    def _sanitize_phone(self, phone: str) -> str:
        """Mask phone number for logging."""
        if not phone:
            return "[EMPTY_PHONE]"

        # Remove all non-digits
        digits_only = re.sub(r"\\D", "", phone)
        if len(digits_only) < 5:
            return "***"
        if len(digits_only) >= 10:
            return digits_only[:3] + "***" + digits_only[-2:]
        return digits_only[:2] + "***"

    def _sanitize_message(self, message: str, **kwargs) -> str:
        """Sanitize a log message by replacing sensitive data with safe alternatives
        Args:
            message: Original log message
            **kwargs: Additional context that might contain sensitive data
        Returns:
            Sanitized message safe for logging.
        """
        sanitized = message

        # Handle kwargs that might contain sensitive data
        for key, value in kwargs.items():
            if key == "child_id" and value:
                sanitized_value = self._sanitize_child_id(str(value))
                kwargs[key] = sanitized_value
            elif key == "parent_id" and value:
                sanitized_value = self._sanitize_parent_id(str(value))
                kwargs[key] = sanitized_value
            elif key == "email" and value:
                sanitized_value = self._sanitize_email(str(value))
                kwargs[key] = sanitized_value
            elif key == "phone" and value:
                sanitized_value = self._sanitize_phone(str(value))
                kwargs[key] = sanitized_value

        # Pattern-based sanitization for embedded sensitive data
        patterns = {
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\b": lambda m: self._sanitize_email(
                m.group(0),
            ),
            r"\\+?[\\d\\s\\-\\(\\)]{10,}": lambda m: self._sanitize_phone(
                m.group(0)
            ),
            r"\bchild_[a-zA-Z0-9\\-_]{8,}": lambda m: self._sanitize_child_id(
                m.group(0),
            ),
            r"\bparent_[a-zA-Z0-9\\-_]{8,}": lambda m: self._sanitize_parent_id(
                m.group(0),
            ),
        }

        for pattern, replacer in patterns.items():
            sanitized = re.sub(pattern, replacer, sanitized)

        return sanitized

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info level message with sanitization."""
        sanitized_message = self._sanitize_message(message, **kwargs)
        self._logger.info(sanitized_message, *args)

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug level message with sanitization."""
        sanitized_message = self._sanitize_message(message, **kwargs)
        self._logger.debug(sanitized_message, *args)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning level message with sanitization."""
        sanitized_message = self._sanitize_message(message, **kwargs)
        self._logger.warning(sanitized_message, *args)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error level message with sanitization."""
        sanitized_message = self._sanitize_message(message, **kwargs)
        self._logger.error(sanitized_message, *args)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical level message with sanitization."""
        sanitized_message = self._sanitize_message(message, **kwargs)
        self._logger.critical(sanitized_message, *args)


# Global secure logger instances cache
_secure_loggers: dict[str, SecureLogger] = {}


def get_secure_logger(name: str) -> SecureLogger:
    """Get a secure logger instance for the given name
    Args:
        name: Logger name (usually __name__).

    Returns:
        SecureLogger instance that sanitizes sensitive data

    """
    if name not in _secure_loggers:
        _secure_loggers[name] = SecureLogger(name)
    return _secure_loggers[name]


# Convenience functions for common logging patterns
def log_child_activity(
    child_id: str,
    activity: str,
    details: dict | None = None,
) -> None:
    """Log child activity with automatic ID sanitization."""
    logger = get_secure_logger("child_activity")
    safe_child_id = logger._sanitize_child_id(child_id)
    if details:
        logger.info(
            f"Child activity: {safe_child_id} - {activity} - {details}"
        )
    else:
        logger.info(f"Child activity: {safe_child_id} - {activity}")


def log_parent_action(
    parent_id: str, action: str, child_id: str | None = None
) -> None:
    """Log parent action with automatic ID sanitization."""
    logger = get_secure_logger("parent_activity")
    safe_parent_id = logger._sanitize_parent_id(parent_id)
    if child_id:
        safe_child_id = logger._sanitize_child_id(child_id)
        logger.info(
            f"Parent action: {safe_parent_id} - {action} - child: {safe_child_id}",
        )
    else:
        logger.info(f"Parent action: {safe_parent_id} - {action}")


def log_safety_event(
    child_id: str,
    event_type: str,
    severity: str,
    details: str | None = None,
) -> None:
    """Log safety event with automatic sanitization."""
    logger = get_secure_logger("child_safety")
    safe_child_id = logger._sanitize_child_id(child_id)
    if details:
        logger.warning(
            f"Safety event: {safe_child_id} - {event_type} ({severity}) - {details}",
        )
    else:
        logger.warning(
            f"Safety event: {safe_child_id} - {event_type} ({severity})"
        )


def log_coppa_event(
    child_id: str, event_type: str, consent_status: str
) -> None:
    """Log COPPA compliance event with sanitization
    COPPA CONDITIONAL: Only logs when COPPA compliance is enabled.
    """
    # COPPA CONDITIONAL: Skip COPPA logging when disabled
    if not requires_coppa_audit_logging():
        return  # No logging when COPPA disabled

    logger = get_secure_logger("coppa_compliance")
    safe_child_id = logger._sanitize_child_id(child_id)
    logger.info(
        f"COPPA event: {safe_child_id} - {event_type} - consent: {consent_status}",
    )


# Decorator for automatic logging sanitization
def secure_log_call(func: Callable) -> Callable:
    """Decorator to add secure logging to function calls."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_secure_logger(func.__module__)

        # Log function entry (sanitized)
        sanitized_args = []
        for arg in args:
            if isinstance(arg, str) and ("child_" in arg or "parent_" in arg):
                if "child_" in arg:
                    sanitized_args.append(logger._sanitize_child_id(arg))
                else:
                    sanitized_args.append(logger._sanitize_parent_id(arg))
            else:
                sanitized_args.append(str(arg)[:50])  # Truncate long args

        logger.debug(
            f"Function call: {func.__name__}({', '.join(sanitized_args)})"
        )

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function success: {func.__name__}")
            return result
        except Exception as e:
            logger.error(
                f"Function error: {func.__name__} - {type(e).__name__}"
            )
            raise

    return wrapper


# Migration utility to update existing log statements
def create_logging_migration_script():
    """Create a script to help migrate existing unsafe logging statements."""
    migration_patterns = [
        {
            "pattern": r'logger\\.(info|debug|warning|error|critical)\\(f"([^"]*\\{child_id\\}[^"]*)"',
            "replacement": r'secure_logger.\1(f"\2", child_id=child_id)',
            "description": "Replace direct child_id logging with secure logging",
        },
        {
            "pattern": r'logger\\.(info|debug|warning|error|critical)\\(f"([^"]*\\{parent_id\\}[^"]*)"',
            "replacement": r'secure_logger.\1(f"\2", parent_id=parent_id)',
            "description": "Replace direct parent_id logging with secure logging",
        },
        {
            "pattern": r'logger\\.(info|debug|warning|error|critical)\\(f"([^"]*\\{email\\}[^"]*)"',
            "replacement": r'secure_logger.\1(f"\2", email=email)',
            "description": "Replace direct email logging with secure logging",
        },
    ]

    script_content = """#!/usr/bin/env python3
# Automated migration script for secure logging
# Generated by AI Teddy Bear security system

import re
import os
from pathlib import Path

MIGRATION_PATTERNS = """
    script_content += str(migration_patterns)
    script_content += """

def migrate_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content
    for pattern_info in MIGRATION_PATTERNS:
        content = re.sub(
            pattern_info['pattern'],
            pattern_info['replacement'],
            content
        )

    if content != original_content:
        logger.info(f"Migrating: {file_path}")
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main() -> None:
    src_dir = Path("src")
    migrated_files = 0
    for py_file in src_dir.rglob("*.py"):
        if migrate_file(py_file):
            migrated_files += 1

    logger.info(f"Migration complete: {migrated_files} files updated")

if __name__ == "__main__":
    main()"""

    with open("migrate_to_secure_logging.py", "w") as f:
        f.write(script_content)

    logger.info("✅ Created migration script: migrate_to_secure_logging.py")


if __name__ == "__main__":
    # Test the secure logger
    logger = get_secure_logger(__name__)

    # Test various sanitization scenarios
    test_child_id = "child_abc123_def456"
    test_parent_id = "parent_xyz789_uvw"
    test_email = "parent@example.com"
    test_phone = "+1234567890"

    logger.info(f"Testing child logging: {test_child_id}")
    logger.info(f"Testing parent logging: {test_parent_id}")
    logger.info(f"Testing email logging: {test_email}")
    logger.info(f"Testing phone logging: {test_phone}")

    logger.info(
        "✅ Secure logging tests completed - check logs for sanitized output"
    )
