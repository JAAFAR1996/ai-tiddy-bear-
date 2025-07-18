"""HTTPS Middleware for secure communication"""

from datetime import datetime
from typing import Callable
import logging

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="security")

try:
    from fastapi import Request, Response
    from fastapi.responses import RedirectResponse
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    class Request:
        pass

    class Response:
        pass

    class BaseHTTPMiddleware:
        pass

    class HTTPSRedirectMiddleware:
        pass


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS in production environment."""

    def __init__(
        self,
        app,
        enforce_https: bool = False,
        hsts_max_age: int = 31536000,
    ) -> None:
        super().__init__(app)
        self.enforce_https = enforce_https
        self.hsts_max_age = hsts_max_age

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        if not FASTAPI_AVAILABLE:
            return await call_next(request)

        # HTTPS redirect for production
        if self.enforce_https:
            scheme = request.headers.get(
                "X-Forwarded-Proto", request.url.scheme
            )
            if scheme != "https":
                https_url = request.url.replace(scheme="https")
                logger.info(
                    f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}"
                )
                return RedirectResponse(url=str(https_url), status_code=301)

        # Process request
        response = await call_next(request)

        # Add security headers
        if self.enforce_https:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = (
                "strict-origin-when-cross-origin"
            )
            csp_policy = (
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'"
            )
            response.headers["Content-Security-Policy"] = csp_policy

        return response


def create_https_middleware(
    environment: str = "development",
) -> HTTPSEnforcementMiddleware:
    """Create HTTPS middleware based on environment."""
    enforce_https = environment == "production"
    if enforce_https:
        logger.info("HTTPS enforcement enabled for production environment")
    else:
        logger.info("HTTPS enforcement disabled for development environment")

    return HTTPSEnforcementMiddleware(
        app=None,
        enforce_https=enforce_https,
        hsts_max_age=31536000,  # 1 year
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        if not FASTAPI_AVAILABLE:
            return await call_next(request)

        response = await call_next(request)

        # Add comprehensive security headers
        csp_policy = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
            "font-src 'self' https:; connect-src 'self' https:; "
            "media-src 'self' https:; object-src 'none'; child-src 'none'; "
            "worker-src 'none'; frame-ancestors 'none'; form-action 'self'; "
            "base-uri 'self'; manifest-src 'self'"
        )

        permissions_policy = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
            "magnetometer=(), gyroscope=(), accelerometer=(), "
            "ambient-light-sensor=(), autoplay=(), encrypted-media=(), "
            "fullscreen=(), picture-in-picture=()"
        )

        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": csp_policy,
            "Permissions-Policy": permissions_policy,
        }

        for header, value in security_headers.items():
            response.headers[header] = value

        return response


def setup_https_middleware(app, settings) -> None:
    """Setup HTTPS and security middleware."""
    if not FASTAPI_AVAILABLE:
        logger.warning(
            "FastAPI not available, skipping HTTPS middleware setup"
        )
        return

    # Add HTTPS enforcement middleware
    create_https_middleware(settings.ENVIRONMENT)
    app.add_middleware(
        HTTPSEnforcementMiddleware,
        enforce_https=settings.ENVIRONMENT == "production",
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("HTTPS and security middleware configured")


# Configuration for different environments
HTTPS_CONFIG = {
    "development": {
        "enforce_https": False,
        "hsts_max_age": 0,
        "require_ssl": False,
    },
    "staging": {
        "enforce_https": True,
        "hsts_max_age": 86400,  # 1 day
        "require_ssl": True,
    },
    "production": {
        "enforce_https": True,
        "hsts_max_age": 31536000,  # 1 year
        "require_ssl": True,
    },
}