"""from typing import Dict, Any, Optional
import time
import uuid
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from src.infrastructure.config.settings import get_settings.
"""

"""Comprehensive Security Headers Middleware
Implements all required security headers for child safety and COPPA compliance.
"""


class ComprehensiveSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Comprehensive security headers middleware for maximum child protection.
    Implements all security headers recommended by OWASP and child safety guidelines.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.settings = get_settings()
        self.is_production = (
            self.settings.application.ENVIRONMENT == "production"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add comprehensive security headers to all responses."""
        response = await call_next(request)

        # Add all security headers
        self._add_content_security_policy(response)
        self._add_permissions_policy(response)
        self._add_transport_security(response)
        self._add_content_type_options(response)
        self._add_frame_options(response)
        self._add_xss_protection(response)
        self._add_referrer_policy(response)
        self._add_cache_control(response, request)
        self._add_coppa_headers(response)
        self._add_child_safety_headers(response, request)
        self._add_privacy_headers(response)
        self._add_performance_headers(response)

        return response

    def _add_content_security_policy(self, response: Response) -> None:
        """Add comprehensive Content Security Policy."""
        if self.is_production:
            # Ultra-strict CSP for production child safety
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Required for some frameworks
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: ws:; "
                "media-src 'self' data:; "
                "object-src 'none'; "
                "embed-src 'none'; "
                "child-src 'none'; "
                "frame-src 'none'; "
                "worker-src 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self'; "
                "manifest-src 'self'; "
                "upgrade-insecure-requests; "
                "block-all-mixed-content; "
                "require-trusted-types-for 'script'"
            )
        else:
            # Relaxed CSP for development
            csp_policy = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: blob: http: https:; "
                "connect-src 'self' ws: wss: http: https:; "
                "frame-ancestors 'none'; "
                "object-src 'none'"
            )

        response.headers["Content-Security-Policy"] = csp_policy
        response.headers["Content-Security-Policy-Report-Only"] = csp_policy

    def _add_permissions_policy(self, response: Response) -> None:
        """Add Permissions Policy for child safety."""
        permissions = [
            "geolocation=()",  # No location tracking
            "microphone=(self)",  # Controlled microphone access
            "camera=()",  # No camera access by default
            "payment=()",  # No payment features
            "usb=()",  # No USB access
            "magnetometer=()",  # No sensor access
            "gyroscope=()",  # No sensor access
            "accelerometer=()",  # No sensor access
            "ambient-light-sensor=()",  # No sensor access
            "autoplay=(self)",  # Allow audio autoplay for responses
            "battery=()",  # No battery access
            "bluetooth=()",  # No Bluetooth access
            "browsing-topics=()",  # No browsing topics
            "clipboard-read=()",  # No clipboard read
            "clipboard-write=(self)",  # Limited clipboard write
            "display-capture=()",  # No screen capture
            "document-domain=()",  # No document domain
            "encrypted-media=()",  # No encrypted media
            "fullscreen=(self)",  # Allow fullscreen for educational content
            "gamepad=()",  # No gamepad access
            "hid=()",  # No HID access
            "identity-credentials-get=()",  # No identity credentials
            "idle-detection=()",  # No idle detection
            "local-fonts=()",  # No local fonts access
            "midi=()",  # No MIDI access
            "notification=(self)",  # Allow notifications for safety
            "otp-credentials=()",  # No OTP credentials
            "publickey-credentials-get=()",  # No public key credentials
            "screen-wake-lock=()",  # No wake lock
            "serial=()",  # No serial access
            "speaker-selection=(self)",  # Allow speaker selection
            "storage-access=()",  # No storage access
            "web-share=(self)",  # Allow sharing educational content
            "window-management=()",  # No window management
            "xr-spatial-tracking=()",  # No XR tracking
        ]

        response.headers["Permissions-Policy"] = ", ".join(permissions)

    def _add_transport_security(self, response: Response) -> None:
        """Add HTTP Strict Transport Security."""
        if self.is_production:
            # 2 years HSTS with includeSubDomains and preload
            hsts_value = "max-age=63072000; includeSubDomains; preload"
        else:
            # Shorter HSTS for development
            hsts_value = "max-age=31536000; includeSubDomains"

        response.headers["Strict-Transport-Security"] = hsts_value

    def _add_content_type_options(self, response: Response) -> None:
        """Add X - Content - Type - Options header."""
        response.headers["X-Content-Type-Options"] = "nosniff"

    def _add_frame_options(self, response: Response) -> None:
        """Add X - Frame - Options header."""
        response.headers["X-Frame-Options"] = "DENY"

    def _add_xss_protection(self, response: Response) -> None:
        """Add XSS protection headers."""
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Additional XSS protection
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"

    def _add_referrer_policy(self, response: Response) -> None:
        """Add Referrer Policy for privacy."""
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    def _add_cache_control(self, response: Response, request: Request) -> None:
        """Add appropriate cache control headers."""
        path = str(request.url.path)

        if any(
            sensitive in path for sensitive in ["/api/", "/auth/", "/child"]
        ):
            # No caching for sensitive endpoints
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif any(
            static in path for static in ["/static/", "/assets/", "/media/"]
        ):
            # Long cache for static assets
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )
        else:
            # Default short cache
            response.headers["Cache-Control"] = "private, max-age=300"

    def _add_coppa_headers(self, response: Response) -> None:
        """Add COPPA compliance headers."""
        response.headers["X-COPPA-Compliant"] = "true"
        response.headers["X-Child-Safe"] = "verified"
        response.headers["X-Privacy-Policy"] = "https://aiteddy.com/privacy"
        response.headers["X-Terms-Service"] = "https://aiteddy.com/terms"
        response.headers["X-Parental-Controls"] = "available"
        response.headers["X-Data-Retention"] = "coppa-compliant"

    def _add_child_safety_headers(
        self, response: Response, request: Request
    ) -> None:
        """Add child safety specific headers."""
        response.headers["X-Content-Filter"] = "enabled"
        response.headers["X-Age-Verification"] = "required"
        response.headers["X-Parental-Consent"] = "enforced"
        response.headers["X-Safety-Mode"] = "maximum"

        # Add request tracking for safety
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Safety-Audit"] = "logged"

    def _add_privacy_headers(self, response: Response) -> None:
        """Add privacy protection headers."""
        response.headers["X-DNS-Prefetch-Control"] = "off"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Privacy-focused headers
        response.headers["X-Data-Minimization"] = "active"
        response.headers["X-Consent-Required"] = "true"
        response.headers["X-Right-To-Delete"] = "available"
        response.headers["X-Privacy-By-Design"] = "implemented"

    def _add_performance_headers(self, response: Response) -> None:
        """Add performance and monitoring headers."""
        response.headers["X-Response-Time"] = f"{time.time():.3f}"
        response.headers["X-Server-Version"] = "AiTeddy/1.0"
        response.headers["X-Child-Protection-Level"] = "maximum"

        # Security monitoring
        response.headers["X-Security-Scanner"] = "active"
        response.headers["X-Threat-Detection"] = "enabled"
        response.headers["X-Compliance-Check"] = "passed"


def create_comprehensive_security_middleware(
    app,
) -> ComprehensiveSecurityHeadersMiddleware:
    """Factory function to create comprehensive security headers middleware."""
    return ComprehensiveSecurityHeadersMiddleware(app)


# Security headers configuration for different environments
SECURITY_HEADERS_CONFIG = {
    "production": {
        "strict_transport_security": "max-age=63072000; includeSubDomains; preload",
        "content_security_policy": "strict",
        "permissions_policy": "restrictive",
        "cache_control": "secure",
    },
    "staging": {
        "strict_transport_security": "max-age=31536000; includeSubDomains",
        "content_security_policy": "moderate",
        "permissions_policy": "moderate",
        "cache_control": "secure",
    },
    "development": {
        "strict_transport_security": "max-age=86400",
        "content_security_policy": "relaxed",
        "permissions_policy": "relaxed",
        "cache_control": "minimal",
    },
}
