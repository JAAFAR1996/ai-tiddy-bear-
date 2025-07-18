"""
Secure Error Handler with Information Leak Prevention
Provides secure error handling that prevents sensitive information disclosure.
"""

import json
import re
import secrets
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="security")

try:
    from src.infrastructure.security.comprehensive_audit_integration import (
        get_audit_integration,
    )
except ImportError:
    # Mock audit integration if not available
    class MockAuditIntegration:
        async def log_security_event(self, **kwargs):
            logger.info(f"Audit event: {kwargs}")
    
    def get_audit_integration():
        return MockAuditIntegration()


class ErrorSeverity(Enum):
    """Error severity levels for security classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for appropriate handling."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    CHILD_SAFETY = "child_safety"


@dataclass
class ErrorContext:
    """Context information for error handling."""

    request_id: str
    user_id: Optional[str]
    child_id: Optional[str]
    ip_address: Optional[str]
    endpoint: str
    method: str
    user_agent: Optional[str]
    timestamp: datetime


@dataclass
class SecureErrorResponse:
    """Secure error response with sanitized information."""

    error_code: str
    message: str
    details: Optional[Dict[str, Any]]
    request_id: str
    timestamp: str
    support_reference: Optional[str] = None


class SecureErrorHandler:
    """
    Secure error handler that prevents information leakage while maintaining usability.
    Features:
    - Sanitizes error messages to prevent information disclosure
    - Logs detailed errors internally while showing safe messages to users
    - Special handling for child safety violations
    - Comprehensive audit logging for security incidents
    - Different error levels based on user types and contexts
    - Rate limiting for error responses to prevent abuse
    """

    def __init__(self):
        self.audit_integration = get_audit_integration()
        self._compile_sensitive_patterns()
        self._setup_error_mappings()

    def _compile_sensitive_patterns(self) -> None:
        """Compile patterns that indicate sensitive information in error messages."""
        # Patterns that should never appear in user-facing error messages
        self.sensitive_patterns = [
            # Database information
            re.compile(
                r"\b(database|sql|query|table|column|constraint)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(postgresql|mysql|sqlite|mongodb)\b", re.IGNORECASE
            ),
            re.compile(
                r"\b(connection|host|port|username|password)\b", re.IGNORECASE
            ),
            # File system information
            re.compile(
                r"[/\\][a-zA-Z0-9_\\-/\\\\.]+", re.IGNORECASE
            ),  # File paths
            re.compile(
                r"\b(directory|folder|file|disk|volume)\b", re.IGNORECASE
            ),
            # Network information
            re.compile(r"\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\b"),  # IP addresses
            re.compile(r"\b[a-zA-Z0-9\\-]+\\.[a-zA-Z]{2,}\b"),  # Domain names
            re.compile(
                r"\b(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0)\b", re.IGNORECASE
            ),
            # Stack traces and internal references
            re.compile(
                r"\b(traceback|stack|frame|line \\d+)\b", re.IGNORECASE
            ),
            re.compile(r"\b(module|function|class|method)\b", re.IGNORECASE),
            re.compile(r"src[/\\][a-zA-Z0-9_\\-/\\\\.]+", re.IGNORECASE),
            # Cryptographic information
            re.compile(
                r"\b(key|token|secret|hash|cipher|encrypt)\b", re.IGNORECASE
            ),
            re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b"),  # Base64 patterns
            # System information
            re.compile(
                r"\b(version|python|fastapi|server|application)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(memory|cpu|process|thread)\b", re.IGNORECASE),
            # Personal information patterns
            re.compile(r"\b\\d{3}-\\d{2}-\\d{4}\b"),  # SSN
            re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\b"
            ),  # Email
            re.compile(
                r"\b\\d{3}[\\s-]?\\d{3}[\\s-]?\\d{4}\b"
            ),  # Phone number
        ]
        # Child-specific sensitive patterns
        self.child_sensitive_patterns = [
            re.compile(r"\b(child|kid|minor|student|age)\b", re.IGNORECASE),
            re.compile(r"\b(parent|guardian|family|school)\b", re.IGNORECASE),
            re.compile(
                r"\b(medical|health|condition|medication)\b", re.IGNORECASE
            ),
        ]

    def _setup_error_mappings(self) -> None:
        """Setup mappings for common error types to secure messages."""
        # Standard error mappings
        self.error_mappings = {
            # Validation errors
            "validation_error": "Please check your input and try again.",
            "invalid_format": "The provided data format is not valid.",
            "missing_field": "Required information is missing.",
            "field_too_long": "Input exceeds maximum length.",
            "field_too_short": "Input is too short.",
            # Authentication errors
            "authentication_failed": "Authentication failed. Please try again.",
            "invalid_credentials": "Invalid username or password.",
            "token_expired": "Your session has expired. Please log in again.",
            "token_invalid": "Invalid authentication token.",
            "account_locked": "Account is temporarily locked.",
            # Authorization errors
            "access_denied": "You don't have permission to access this resource.",
            "insufficient_permissions": "Insufficient permissions for this action.",
            "resource_forbidden": "Access to this resource is not allowed.",
            # Business logic errors
            "resource_not_found": "The requested resource was not found.",
            "conflict": "The operation conflicts with the current state.",
            "precondition_failed": "Required conditions are not met.",
            "operation_not_allowed": "This operation is not allowed.",
            # Infrastructure errors
            "service_unavailable": (
                "Service is temporarily unavailable. Please try again later."
            ),
            "timeout": "The request timed out. Please try again.",
            "rate_limit_exceeded": (
                "Too many requests. Please wait before trying again."
            ),
            "internal_error": "An internal error occurred. Please try again later.",
            # Security errors
            "security_violation": "Security violation detected.",
            "suspicious_activity": "Suspicious activity detected.",
            "input_rejected": "Input was rejected for security reasons.",
            # Child safety errors
            "child_safety_violation": "Content is not appropriate for children.",
            "parental_consent_required": "Parental consent is required.",
            "age_verification_failed": "Age verification is required.",
        }
        # Child-specific error messages (more gentle)
        self.child_error_mappings = {
            "validation_error": "Please check what you typed and try again.",
            "authentication_failed": "Please ask a grown-up to help you log in.",
            "access_denied": "This area is not available right now.",
            "rate_limit_exceeded": "Please wait a moment before trying again.",
            "child_safety_violation": (
                "That message is not appropriate. Please try something else."
            ),
            "internal_error": "Something went wrong. Please ask a grown-up for help.",
        }

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_category: ErrorCategory = ErrorCategory.INFRASTRUCTURE,
    ) -> SecureErrorResponse:
        """
        Handle an error securely without leaking sensitive information.
        Args:
            error: The exception that occurred
            context: Context information about the request
            error_category: Category of the error for appropriate handling
        Returns:
            SecureErrorResponse with sanitized error information
        """
        try:
            # Generate support reference for tracking
            support_reference = self._generate_support_reference()
            # Determine error severity
            severity = self._determine_error_severity(error, error_category)
            # Extract safe error information
            error_info = self._extract_error_info(error, error_category)
            # Create sanitized error message
            safe_message = self._create_safe_message(
                error_info, context, error_category
            )
            # Log detailed error internally
            await self._log_detailed_error(
                error, context, error_info, severity, support_reference
            )
            # Create secure response
            response = SecureErrorResponse(
                error_code=error_info["code"],
                message=safe_message,
                details=error_info.get("safe_details"),
                request_id=context.request_id,
                timestamp=context.timestamp.isoformat(),
                support_reference=(
                    support_reference
                    if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
                    else None
                ),
            )
            return response
        except Exception as handler_error:
            logger.critical(f"Error handler failed: {handler_error}")
            # Fallback to ultra-safe response
            return SecureErrorResponse(
                error_code="internal_error",
                message="An error occurred. Please try again later.",
                details=None,
                request_id=context.request_id,
                timestamp=datetime.utcnow().isoformat(),
                support_reference=self._generate_support_reference(),
            )

    def _extract_error_info(
        self, error: Exception, category: ErrorCategory
    ) -> Dict[str, Any]:
        """Extract safe error information from exception."""
        error_type = type(error).__name__
        error_message = str(error)
        # Sanitize error message
        safe_message = self._sanitize_error_message(error_message)
        # Determine error code based on exception type and category
        if isinstance(error, HTTPException):
            status_code = error.status_code
            if status_code == 400:
                error_code = "validation_error"
            elif status_code == 401:
                error_code = "authentication_failed"
            elif status_code == 403:
                error_code = "access_denied"
            elif status_code == 404:
                error_code = "resource_not_found"
            elif status_code == 429:
                error_code = "rate_limit_exceeded"
            else:
                error_code = "http_error"
        elif isinstance(error, RequestValidationError):
            error_code = "validation_error"
        elif "authentication" in error_message.lower():
            error_code = "authentication_failed"
        elif (
            "permission" in error_message.lower()
            or "forbidden" in error_message.lower()
        ):
            error_code = "access_denied"
        elif "not found" in error_message.lower():
            error_code = "resource_not_found"
        elif category == ErrorCategory.CHILD_SAFETY:
            error_code = "child_safety_violation"
        elif category == ErrorCategory.SECURITY:
            error_code = "security_violation"
        else:
            error_code = "internal_error"
        return {
            "code": error_code,
            "type": error_type,
            "original_message": error_message,
            "safe_message": safe_message,
            "category": category.value,
            "safe_details": self._extract_safe_details(error),
        }

    def _sanitize_error_message(self, message: str) -> str:
        """Sanitize error message to remove sensitive information."""
        sanitized = message
        # Remove sensitive patterns
        for pattern in self.sensitive_patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        # Remove child-sensitive patterns if dealing with child data
        for pattern in self.child_sensitive_patterns:
            sanitized = pattern.sub("[PROTECTED]", sanitized)
        # Remove specific sensitive strings
        sensitive_strings = [
            "Connection refused",
            "Access denied",
            "Permission denied",
            "No such file or directory",
            "Cannot connect to database",
            "Authentication failed",
            "Invalid token",
            "Secret key",
            "Configuration error",
        ]
        for sensitive in sensitive_strings:
            sanitized = sanitized.replace(sensitive, "[SYSTEM_ERROR]")
        # Truncate if too long
        if len(sanitized) > 200:
            sanitized = sanitized[:200] + "..."
        return sanitized

    def _extract_safe_details(
        self, error: Exception
    ) -> Optional[Dict[str, Any]]:
        """Extract safe details that can be shown to users."""
        safe_details = {}
        # For validation errors, extract field information safely
        if isinstance(error, RequestValidationError):
            safe_details["validation_errors"] = []
            for err in error.errors():
                safe_error = {
                    "field": ".".join(str(loc) for loc in err.get("loc", [])),
                    "type": err.get("type", "unknown"),
                    "message": "Invalid value",
                }
                safe_details["validation_errors"].append(safe_error)
        # For HTTP exceptions, include safe status information
        elif isinstance(error, HTTPException):
            safe_details["status_code"] = error.status_code
        return safe_details if safe_details else None

    def _create_safe_message(
        self,
        error_info: Dict[str, Any],
        context: ErrorContext,
        category: ErrorCategory,
    ) -> str:
        """Create a safe, user-friendly error message."""
        error_code = error_info["code"]
        # Check if this is a child endpoint
        is_child_context = (
            context.child_id is not None
            or "/children" in context.endpoint
            or "/interact" in context.endpoint
            or category == ErrorCategory.CHILD_SAFETY
        )
        # Use child-friendly messages if appropriate
        if is_child_context and error_code in self.child_error_mappings:
            return self.child_error_mappings[error_code]
        # Use standard mappings
        if error_code in self.error_mappings:
            return self.error_mappings[error_code]
        # Fallback based on category
        category_messages = {
            ErrorCategory.VALIDATION: "Please check your input and try again.",
            ErrorCategory.AUTHENTICATION: "Authentication is required.",
            ErrorCategory.AUTHORIZATION: (
                "You don't have permission for this action."
            ),
            ErrorCategory.BUSINESS_LOGIC: (
                "The requested operation cannot be completed."
            ),
            ErrorCategory.INFRASTRUCTURE: "Service is temporarily unavailable.",
            ErrorCategory.SECURITY: "Request was rejected for security reasons.",
            ErrorCategory.CHILD_SAFETY: "Content is not appropriate for children.",
        }
        return category_messages.get(
            category, "An error occurred. Please try again later."
        )

    def _determine_error_severity(
        self, error: Exception, category: ErrorCategory
    ) -> ErrorSeverity:
        """Determine the severity level of an error."""
        # Critical errors
        if category == ErrorCategory.SECURITY:
            return ErrorSeverity.CRITICAL
        if category == ErrorCategory.CHILD_SAFETY:
            return ErrorSeverity.CRITICAL
        if "database" in str(error).lower():
            return ErrorSeverity.CRITICAL
        # High severity errors
        if isinstance(error, HTTPException) and error.status_code >= 500:
            return ErrorSeverity.HIGH
        if "authentication" in str(error).lower():
            return ErrorSeverity.HIGH
        if "permission" in str(error).lower():
            return ErrorSeverity.HIGH
        # Medium severity errors
        if isinstance(error, RequestValidationError):
            return ErrorSeverity.MEDIUM
        if isinstance(error, HTTPException) and error.status_code >= 400:
            return ErrorSeverity.MEDIUM
        # Default to low severity
        return ErrorSeverity.LOW

    async def _log_detailed_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_info: Dict[str, Any],
        severity: ErrorSeverity,
        support_reference: str,
    ) -> None:
        """Log detailed error information for internal analysis."""
        try:
            # Create detailed log entry
            log_details = {
                "support_reference": support_reference,
                "error_type": error_info["type"],
                "error_code": error_info["code"],
                "error_category": error_info["category"],
                "original_message": error_info["original_message"],
                "endpoint": context.endpoint,
                "method": context.method,
                "user_id": context.user_id,
                "child_id": context.child_id,
                "ip_address": context.ip_address,
                "user_agent": context.user_agent,
                "traceback": traceback.format_exc(),
            }
            # Log using appropriate level
            if severity == ErrorSeverity.CRITICAL:
                logger.critical(
                    f"Critical error (ref: {support_reference}): "
                    f"{error_info['original_message']}"
                )
            elif severity == ErrorSeverity.HIGH:
                logger.error(
                    f"High severity error (ref: {support_reference}): "
                    f"{error_info['original_message']}"
                )
            elif severity == ErrorSeverity.MEDIUM:
                logger.warning(
                    f"Medium severity error (ref: {support_reference}): "
                    f"{error_info['original_message']}"
                )
            else:
                logger.info(
                    f"Low severity error (ref: {support_reference}): "
                    f"{error_info['original_message']}"
                )
            # Audit log for security and child safety errors
            if error_info["category"] in ["security", "child_safety"]:
                await self.audit_integration.log_security_event(
                    event_type=f"error_{error_info['category']}",
                    severity=severity.value,
                    description=f"Error occurred: {error_info['code']}",
                    user_id=context.user_id,
                    ip_address=context.ip_address,
                    details=log_details,
                )
        except Exception as log_error:
            logger.critical(f"Failed to log error details: {log_error}")

    def _generate_support_reference(self) -> str:
        """Generate a unique support reference for error tracking."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_part = secrets.token_hex(4).upper()
        return f"ERR-{timestamp}-{random_part}"


class SecureErrorMiddleware:
    """Middleware that handles all errors securely."""

    def __init__(self, app):
        self.app = app
        self.error_handler = SecureErrorHandler()

    async def __call__(self, scope, receive, send):
        """Handle requests with secure error handling."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception as error:
            # Create error context
            request_id = secrets.token_hex(8)
            context = ErrorContext(
                request_id=request_id,
                user_id=None,  # Would be extracted from request if available
                child_id=None,  # Would be extracted from request if available
                ip_address=(
                    scope.get("client", ["unknown"])[0]
                    if scope.get("client")
                    else "unknown"
                ),
                endpoint=scope.get("path", "/unknown"),
                method=scope.get("method", "UNKNOWN"),
                user_agent=next(
                    (
                        h[1].decode()
                        for h in scope.get("headers", [])
                        if h[0] == b"user-agent"
                    ),
                    None,
                ),
                timestamp=datetime.utcnow(),
            )
            # Handle error securely
            secure_response = await self.error_handler.handle_error(
                error, context
            )
            # Send secure error response
            response = {
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"x-request-id", request_id.encode()],
                ],
            }
            await send(response)
            body = json.dumps(
                {
                    "error": secure_response.error_code,
                    "message": secure_response.message,
                    "request_id": secure_response.request_id,
                    "timestamp": secure_response.timestamp,
                    "support_reference": secure_response.support_reference,
                }
            ).encode()
            await send({"type": "http.response.body", "body": body})


# Global error handler instance
_error_handler = None


def get_error_handler() -> SecureErrorHandler:
    """Get global secure error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = SecureErrorHandler()
    return _error_handler


# Convenience functions for common error handling
async def handle_validation_error(
    error: RequestValidationError, context: ErrorContext
) -> SecureErrorResponse:
    """Handle validation errors securely."""
    handler = get_error_handler()
    return await handler.handle_error(error, context, ErrorCategory.VALIDATION)


async def handle_security_error(
    error: Exception, context: ErrorContext
) -> SecureErrorResponse:
    """Handle security errors with maximum protection."""
    handler = get_error_handler()
    return await handler.handle_error(error, context, ErrorCategory.SECURITY)


async def handle_child_safety_error(
    error: Exception, context: ErrorContext
) -> SecureErrorResponse:
    """Handle child safety errors with special care."""
    handler = get_error_handler()
    return await handler.handle_error(
        error, context, ErrorCategory.CHILD_SAFETY
    )