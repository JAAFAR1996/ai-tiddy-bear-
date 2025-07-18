"""from typing import Dict, Any, Optional
import time
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from src.infrastructure.config.settings import get_settings.
"""

"""Rate Limiting Middleware for AI Teddy Bear
Implements rate limiting for child safety and abuse prevention
"""


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for child safety and abuse prevention.
    Features: - Per - IP rate limiting - Endpoint - specific limits - Progressive delays for violations - Child - safety focused limits - Integration with RateLimiter service.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.settings = get_settings()

        # Import rate limiter service
        try:
            from src.infrastructure.security.rate_limiter import (
                RateLimiter,
                child_safety_limiter,
                rate_limit_child_request,
            )

            self.child_safety_limiter = child_safety_limiter
            self.rate_limit_child_request = rate_limit_child_request
            self.rate_limiter = RateLimiter()
            self.limiter_available = True
        except ImportError:
            self.limiter_available = False
            self.request_tracking = {}  # Fallback to in-memory tracking

        # Configure rate limits for different endpoints from settings
        self.rate_limits = self.settings.security.RATE_LIMITS

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Apply rate limiting based on IP and endpoint.
        Args: request: Incoming HTTP request
            call_next: Next middleware / endpoint
        Returns: Response with rate limiting enforced.
        """
        client_ip = self._get_client_ip(request)
        endpoint = self._get_rate_limit_key(request.url.path)

        # Check for child-specific endpoints
        child_id = self._extract_child_id(request)
        if child_id and self.limiter_available:
            # Apply child safety rate limiting
            try:
                await self.rate_limit_child_request(
                    request, child_id, endpoint
                )
            except Exception:
                # Return child-friendly error
                return Response(
                    content='{"message": "Let\\\'s take a little break! I need a moment to rest.", "child_friendly": true}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60", "X-Child-Safety": "active"},
                )

        # Check general rate limit
        if self.limiter_available and hasattr(
            self.rate_limiter, "check_rate_limit"
        ):
            # Use RateLimiter service
            allowed = await self.rate_limiter.check_rate_limit(
                f"{client_ip}:{endpoint}",
                max_requests=self.rate_limits[endpoint]["requests"],
            )
            if not allowed:
                return self._rate_limit_exceeded_response(request, endpoint)
        else:
            # Fallback to in-memory tracking
            rate_limit_result = self._check_rate_limit(client_ip, endpoint)
            if not rate_limit_result["allowed"]:
                return Response(
                    content=f"Rate limit exceeded. Try again in {rate_limit_result['retry_after']} seconds.",
                    status_code=429,
                    headers={
                        "Retry-After": str(rate_limit_result["retry_after"]),
                        "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(
                            rate_limit_result["reset_time"]
                        ),
                    },
                )

        # Process request
        response = await call_next(request)

        # Add rate limiting headers
        if not self.limiter_available:
            rate_limit_result = self._get_current_limit_status(
                client_ip, endpoint
            )
            self._add_rate_limit_headers(response, rate_limit_result)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _get_rate_limit_key(self, path: str) -> str:
        """Get rate limit configuration key for the path."""
        for endpoint in self.rate_limits:
            if endpoint != "default" and path.startswith(endpoint):
                return endpoint

        return "default"

    def _check_rate_limit(
        self, client_ip: str, endpoint: str
    ) -> Dict[str, Any]:
        """Check if request is within rate limits.
        Args: client_ip: Client IP address
            endpoint: Endpoint being accessed
        Returns: Dict with rate limit check results.
        """
        current_time = int(time.time())
        limits = self.rate_limits[endpoint]
        window_start = current_time - limits["window"]

        # Create tracking key
        key = f"{client_ip}:{endpoint}"

        # Get or create request history
        if key not in self.request_tracking:
            self.request_tracking[key] = []

        # Clean old requests outside window
        self.request_tracking[key] = [
            req_time
            for req_time in self.request_tracking[key]
            if req_time > window_start
        ]

        # Check if within limits
        request_count = len(self.request_tracking[key])
        if request_count >= limits["requests"]:
            # Rate limit exceeded
            oldest_request = min(self.request_tracking[key])
            retry_after = oldest_request + limits["window"] - current_time
            return {
                "allowed": False,
                "limit": limits["requests"],
                "remaining": 0,
                "retry_after": max(retry_after, 1),
                "reset_time": oldest_request + limits["window"],
            }

        # Add current request
        self.request_tracking[key].append(current_time)

        return {
            "allowed": True,
            "limit": limits["requests"],
            "remaining": limits["requests"] - request_count - 1,
            "retry_after": 0,
            "reset_time": current_time + limits["window"],
        }

    def _get_current_limit_status(
        self,
        client_ip: str,
        endpoint: str,
    ) -> Dict[str, Any]:
        """Get current rate limit status without modifying counters."""
        current_time = int(time.time())
        limits = self.rate_limits[endpoint]
        window_start = current_time - limits["window"]
        key = f"{client_ip}:{endpoint}"

        if key not in self.request_tracking:
            return {
                "allowed": True,
                "limit": limits["requests"],
                "remaining": limits["requests"],
                "retry_after": 0,
                "reset_time": current_time + limits["window"],
            }

        # Count recent requests
        recent_requests = [
            req_time
            for req_time in self.request_tracking[key]
            if req_time > window_start
        ]
        request_count = len(recent_requests)

        return {
            "allowed": request_count < limits["requests"],
            "limit": limits["requests"],
            "remaining": max(0, limits["requests"] - request_count),
            "retry_after": 0,
            "reset_time": current_time + limits["window"],
        }

    def _add_rate_limit_headers(
        self,
        response: Response,
        rate_limit_result: Dict[str, Any],
    ) -> None:
        """Add rate limiting headers to response."""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(
            rate_limit_result["remaining"]
        )
        response.headers["X-RateLimit-Reset"] = str(
            rate_limit_result["reset_time"]
        )

    def _extract_child_id(self, request: Request) -> Optional[str]:
        """Extract child ID from request if present."""
        # Check path parameters
        if hasattr(request, "path_params"):
            child_id = request.path_params.get("child_id")
            if child_id:
                return child_id

        # Check headers for child device
        device_id = request.headers.get("X-Device-ID")
        if device_id and device_id.startswith("teddy_"):
            return device_id

        # Check headers for child ID
        child_id_header = request.headers.get("X-Child-ID")
        if child_id_header:
            return child_id_header

        return None

    def _rate_limit_exceeded_response(
        self,
        request: Request,
        endpoint: str,
    ) -> Response:
        """Create appropriate rate limit exceeded response."""
        # Check if this is a child-facing endpoint
        child_endpoints = ["/esp32", "/ai/generate", "/audio", "/voice"]
        is_child_endpoint = any(
            endpoint.startswith(ep) for ep in child_endpoints
        )

        if is_child_endpoint:
            return Response(
                content='{"message": "Wow, you\\\'re really chatty today! Let\\\'s take a short break.", "child_friendly": true, "suggestion": "Maybe we can play a different game?"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60", "X-Child-Safety": "active"},
            )
        return Response(
            content='{"detail": "Rate limit exceeded. Please try again later."}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": "60"},
        )

    def get_rate_limit_status(
        self,
        client_ip: str,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get current rate limit status for debugging / monitoring.
        Args: client_ip: Client IP address
            endpoint: Optional specific endpoint
        Returns: Rate limit status information.
        """
        if endpoint is None:
            endpoint = "default"

        endpoint_key = self._get_rate_limit_key(endpoint)
        status = self._get_current_limit_status(client_ip, endpoint_key)

        return {
            "client_ip": client_ip,
            "endpoint": endpoint,
            "rate_limit_config": self.rate_limits[endpoint_key],
            "current_status": status,
            "limiter_available": self.limiter_available,
        }
