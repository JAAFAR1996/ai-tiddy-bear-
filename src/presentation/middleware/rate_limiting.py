"""
from datetime import datetime
from typing import Dict, Optional, Callable, Awaitable
import logging
import re
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from src.infrastructure.security.rate_limiter import (
"""

"""Unified Rate Limiting Middleware"""
    limiter,
    get_rate_limit_for_endpoint,
    rate_limit_child_request,
    child_safety_limiter)

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="middleware")

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive rate limiting middleware with child safety features.
    """
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        # Define endpoint patterns and their rate limits
        self.endpoint_limits = {
            # Authentication endpoints - strict limits
            r"/auth/login": "5/minute",
            r"/auth/register": "3/minute",
            r"/auth/refresh": "10/minute",
            r"/auth/password-reset": "3/hour",
            
            # Child interaction endpoints - safety limits
            r"/esp32/": "30/minute",  # Child device interactions
            r"/ai/generate": "20/minute",  # AI responses
            r"/audio/": "15/minute",  # Audio processing
            
            # Parent dashboard - moderate limits
            r"/dashboard/": "100/minute",
            r"/children/": "50/minute",
            r"/reports/": "30/minute",
            
            # Health checks - high limits
            r"/health": "1000/minute",
            r"/metrics": "1000/minute",
            
            # API documentation - moderate limits
            r"/docs": "60/minute",
            r"/redoc": "60/minute",
            r"/openapi.json": "60/minute",
            
            # Default for all other endpoints
            r".*": "60/minute"
        }
        
        # Compile regex patterns
        self.compiled_patterns = [
            (re.compile(pattern), limit)
            for pattern, limit in self.endpoint_limits.items()
        ]
        
        logger.info("Rate limiting middleware initialized with comprehensive limits")

    def get_limit_for_path(self, path: str) -> str:
        """Get appropriate rate limit for given path"""
        for pattern, limit in self.compiled_patterns:
            if pattern.match(path):
                return limit
        return "60/minute"  # Default fallback

    def extract_child_id(self, request: Request) -> Optional[str]:
        """Extract child ID from request if present"""
        # Check path parameters
        if hasattr(request, "path_params"):
            child_id = request.path_params.get("child_id")
            if child_id:
                return child_id
        
        # Check headers for child device
        device_id = request.headers.get("X-Device-ID")
        if device_id and device_id.startswith("teddy_"):
            return device_id
        
        return None

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Apply rate limiting to all requests"""
        try:
            # Skip rate limiting for excluded paths
            if self._is_excluded_path(request.url.path):
                return await call_next(request)
            
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Check if this is a child interaction
            child_id = self.extract_child_id(request)
            if child_id:
                # Apply child-specific rate limiting
                try:
                    await rate_limit_child_request(
                        request,
                        child_id,
                        request_type=self._get_request_type(request)
                    )
                except HTTPException as e:
                    # Return child-friendly error
                    return JSONResponse(
                        status_code=e.status_code,
                        content=e.detail if isinstance(e.detail, dict) else {"message": e.detail}
                    )
            
            # Apply general rate limiting
            rate_limit = self.get_limit_for_path(request.url.path)
            
            # Store rate limit info for logging
            request.state.rate_limit = rate_limit
            request.state.client_ip = client_ip
            
            # Log rate limit application
            logger.debug(f"Applying rate limit {rate_limit} to {request.url.path} from {client_ip}")
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = rate_limit
            response.headers["X-RateLimit-Path"] = request.url.path
            
            return response
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Don't block requests on middleware errors
            return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting"""
        excluded_patterns = [
            r"^/static/",
            r"^/favicon.ico$",
            r"^/_next/",
            r"^/\.well-known/"
        ]
        for pattern in excluded_patterns:
            if re.match(pattern, path):
                return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Direct IP
        if request.client:
            return request.client.host
        
        return "unknown"

    def _get_request_type(self, request: Request) -> str:
        """Determine request type for child safety tracking"""
        path = request.url.path.lower()
        if "/audio" in path:
            return "audio"
        elif "/ai" in path or "/generate" in path:
            return "ai_interaction"
        elif "/esp32" in path:
            return "device"
        else:
            return "general"

def create_rate_limit_decorator(limit: str) -> Callable:
    """
    Create a rate limit decorator for specific endpoints.
    Usage: 
    @router.get("/endpoint")
    @rate_limit("10/minute") 
    async def endpoint(): ...
    """
    def decorator(func: Callable) -> Callable:
        # Store rate limit in function metadata
        func._rate_limit = limit
        return func
    return decorator

# Export convenient rate limit decorators
rate_limit = create_rate_limit_decorator
strict_rate_limit = lambda: create_rate_limit_decorator("5/minute")
moderate_rate_limit = lambda: create_rate_limit_decorator("30/minute")
relaxed_rate_limit = lambda: create_rate_limit_decorator("100/minute")

# Child safety rate limiters
async def enforce_child_hourly_limit(child_id: str, limit: int = 100) -> None:
    """
    Enforce hourly interaction limits for child safety.
    """
    interactions = len(child_safety_limiter.child_interactions.get(child_id, []))
    if interactions >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "You've been very active today! Let's take a longer break.",
                "child_friendly": True,
                "suggestion": "How about drawing or playing outside for a while?",
                "cooldown_minutes": 30
            }
        )

async def check_parent_override(parent_id: str, child_id: str) -> bool:
    """
    Check if parent has temporarily overridden rate limits.
    """
    # Check if parent has active rate limit override for their child
    # This would typically check a database table like 'parent_overrides'
    # with columns: parent_id, child_id, override_active, expiry_time
    # For now, return False as database implementation requires full setup
    # Future implementation:
    # override = await db.get_parent_override(parent_id, child_id)
    # return override and override.active and override.expiry > datetime.utcnow()
    return False