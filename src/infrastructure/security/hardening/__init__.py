"""
Security Hardening Components for AI Teddy Bear
Comprehensive security hardening package with enterprise-grade protections
"""

from .rate_limiter import (
    RedisRateLimiter,
    ChildSafetyRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    get_rate_limiter,
    get_child_safety_limiter,
)
from .csrf_protection import (
    CSRFProtection,
    CSRFTokenManager,
    CSRFConfig,
    CSRFMiddleware,
    get_csrf_protection,
    init_csrf_protection,
    csrf_protect,
)
from .security_headers import (
    SecurityHeadersMiddleware,
    SecurityHeadersConfig,
    SecurityValidator,
    get_security_headers_config,
    init_security_headers,
    create_security_headers_middleware,
)
from .input_validation import (
    InputValidationMiddleware,
    InputSanitizer,
    InputValidationConfig,
    ValidationRule,
    ValidationSeverity,
    create_input_validation_middleware,
)

__all__ = [
    # Rate Limiting
    "RedisRateLimiter",
    "ChildSafetyRateLimiter",
    "RateLimitConfig",
    "RateLimitResult",
    "get_rate_limiter",
    "get_child_safety_limiter",
    # CSRF Protection
    "CSRFProtection",
    "CSRFTokenManager",
    "CSRFConfig",
    "CSRFMiddleware",
    "get_csrf_protection",
    "init_csrf_protection",
    "csrf_protect",
    # Security Headers
    "SecurityHeadersMiddleware",
    "SecurityHeadersConfig",
    "SecurityValidator",
    "get_security_headers_config",
    "init_security_headers",
    "create_security_headers_middleware",
    # Input Validation
    "InputValidationMiddleware",
    "InputSanitizer",
    "InputValidationConfig",
    "ValidationRule",
    "ValidationSeverity",
    "create_input_validation_middleware",
]
# Package version
__version__ = "1.0.0"
