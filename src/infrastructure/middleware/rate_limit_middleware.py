"""
Production Rate Limiting Middleware
"""

from datetime import datetime
from typing import Optional
import hashlib
import json
import time

# Enterprise - grade request rate limiting with Redis backend

from src.infrastructure.logging_config import get_logger

# Import constants for consistent configuration
from src.common.constants import (
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_REQUESTS_PER_HOUR,
    DEFAULT_REQUESTS_PER_DAY,
    DEFAULT_BURST_LIMIT,
    DEFAULT_BLOCK_DURATION_MINUTES,
)

logger = get_logger(__name__, component="infrastructure")

# Production-only imports - no fallbacks allowed
try:
    from fastapi import Request, HTTPException, status
    from starlette.middleware.base import BaseHTTPMiddleware
    import redis.asyncio as redis
except ImportError as e:
    logger.critical(
        f"CRITICAL ERROR: Rate limiting dependencies required: {e}"
    )
    logger.critical("Install required dependencies: pip install fastapi redis")
    raise ImportError(
        f"Missing required dependencies for rate limiting: {e}"
    ) from e


class RateLimitConfig:
    """Rate limiting configuration."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 600,
        requests_per_day: int = 5000,
        burst_limit: int = 10,
        block_duration_minutes: int = 60,
        exempt_ips: Optional[list] = None,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_limit = burst_limit
        self.block_duration_minutes = block_duration_minutes
        self.exempt_ips = exempt_ips or []


class RateLimitResult:
    """Rate limit check result."""

    def __init__(
        self,
        allowed: bool,
        limit_type: str = "",
        reset_time: Optional[datetime] = None,
        remaining_requests: int = 0,
        retry_after_seconds: int = 0,
    ) -> None:
        self.allowed = allowed
        self.limit_type = limit_type
        self.reset_time = reset_time
        self.remaining_requests = remaining_requests
        self.retry_after_seconds = retry_after_seconds


class ProductionRateLimiter:
    """Production - grade rate limiter using Redis with sliding window algorithm."""

    def __init__(
        self, redis_client: redis.Redis, config: RateLimitConfig
    ) -> None:
        self.redis = redis_client
        self.config = config

    async def check_rate_limit(
        self, client_id: str, endpoint: str = ""
    ) -> RateLimitResult:
        """
        Check if request is within rate limits using sliding window algorithm.
        Returns RateLimitResult with decision and metadata.
        """
        try:
            # Check if IP is exempt
            if client_id in self.config.exempt_ips:
                return RateLimitResult(allowed=True)

            # Check if IP is currently blocked
            block_key = f"rate_limit:blocked:{client_id}"
            is_blocked = await self.redis.get(block_key)
            if is_blocked:
                block_expires = await self.redis.ttl(block_key)
                return RateLimitResult(
                    allowed=False,
                    limit_type="blocked",
                    retry_after_seconds=max(block_expires, 0),
                )

            current_time = time.time()

            # Check burst limit (last 10 seconds)
            burst_result = await self._check_burst_limit(
                client_id, current_time
            )
            if not burst_result.allowed:
                await self._record_violation(client_id, "burst")
                return burst_result

            # Check minute limit
            minute_result = await self._check_time_window(
                client_id,
                current_time,
                60,
                self.config.requests_per_minute,
                "minute",
            )
            if not minute_result.allowed:
                await self._record_violation(client_id, "minute")
                return minute_result

            # Check hour limit
            hour_result = await self._check_time_window(
                client_id,
                current_time,
                3600,
                self.config.requests_per_hour,
                "hour",
            )
            if not hour_result.allowed:
                await self._record_violation(client_id, "hour")
                return hour_result

            # Check day limit
            day_result = await self._check_time_window(
                client_id,
                current_time,
                86400,
                self.config.requests_per_day,
                "day",
            )
            if not day_result.allowed:
                await self._record_violation(client_id, "day")
                return day_result

            # All checks passed - record the request
            await self._record_request(client_id, current_time, endpoint)

            return RateLimitResult(
                allowed=True,
                remaining_requests=self.config.requests_per_minute
                - minute_result.remaining_requests,
            )
        except Exception as e:
            logger.error(f"Rate limiting error for {client_id}: {e}")
            # Fail open - allow request but log error
            return RateLimitResult(allowed=True)

    async def _check_burst_limit(
        self, client_id: str, current_time: float
    ) -> RateLimitResult:
        """Check burst limit using sliding window."""
        window_start = current_time - 10  # 10 seconds
        key = f"rate_limit:burst:{client_id}"

        # Remove old entries and count current requests
        pipeline = self.redis.pipeline()
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.expire(key, 60)  # Keep for 1 minute
        results = await pipeline.execute()
        current_count = results[1]

        if current_count >= self.config.burst_limit:
            return RateLimitResult(
                allowed=False, limit_type="burst", retry_after_seconds=10
            )

        # Add current request
        await self.redis.zadd(key, {str(current_time): current_time})

        return RateLimitResult(
            allowed=True,
            remaining_requests=self.config.burst_limit - current_count,
        )

    async def _check_time_window(
        self,
        client_id: str,
        current_time: float,
        window_seconds: int,
        limit: int,
        window_type: str,
    ) -> RateLimitResult:
        """Check rate limit for a specific time window."""
        window_start = current_time - window_seconds
        key = f"rate_limit:{window_type}:{client_id}"

        # Remove old entries and count current requests
        pipeline = self.redis.pipeline()
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.expire(key, window_seconds * 2)  # Keep for 2x window duration
        results = await pipeline.execute()
        current_count = results[1]

        if current_count >= limit:
            reset_time = datetime.fromtimestamp(current_time + window_seconds)
            return RateLimitResult(
                allowed=False,
                limit_type=window_type,
                reset_time=reset_time,
                retry_after_seconds=window_seconds,
                remaining_requests=0,
            )

        # Add current request
        await self.redis.zadd(key, {str(current_time): current_time})

        return RateLimitResult(
            allowed=True, remaining_requests=limit - current_count - 1
        )

    async def _record_request(
        self, client_id: str, timestamp: float, endpoint: str
    ) -> None:
        """Record request for analytics and monitoring."""
        try:
            # Store request metadata
            request_data = {
                "timestamp": timestamp,
                "endpoint": endpoint,
                "client_id": client_id,
            }

            # Add to analytics stream
            analytics_key = f"rate_limit:analytics:{datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d:%H')}"
            await self.redis.lpush(analytics_key, json.dumps(request_data))
            await self.redis.expire(analytics_key, 86400)  # Keep for 24 hours
        except Exception as e:
            logger.error(f"Error recording request analytics: {e}")

    async def _record_violation(
        self, client_id: str, violation_type: str
    ) -> None:
        """Record rate limit violation and potentially block IP."""
        try:
            violation_key = f"rate_limit:violations:{client_id}"

            # Increment violation count
            violations = await self.redis.incr(violation_key)
            await self.redis.expire(
                violation_key, 3600
            )  # Reset violations every hour

            # Log violation
            logger.warning(
                f"Rate limit violation: {client_id} - {violation_type} (total: {violations})"
            )

            # Block IP after multiple violations
            if violations >= 5:
                block_key = f"rate_limit:blocked:{client_id}"
                await self.redis.setex(
                    block_key,
                    self.config.block_duration_minutes * 60,
                    f"blocked_at_{time.time()}",
                )
                logger.critical(
                    f"IP blocked due to repeated violations: {client_id}"
                )

                # Send alert for critical rate limiting event
                await self._send_rate_limit_alert(client_id, violations)
        except Exception as e:
            logger.error(f"Error recording violation: {e}")

    async def _send_rate_limit_alert(
        self, client_id: str, violation_count: int
    ) -> None:
        """Send alert for critical rate limiting events."""
        try:
            alert_data = {
                "type": "rate_limit_block",
                "client_id": client_id,
                "violation_count": violation_count,
                "timestamp": datetime.now().isoformat(),
                "severity": "high",
            }

            # Store alert for monitoring systems
            await self.redis.lpush("security:alerts", json.dumps(alert_data))
            await self.redis.ltrim(
                "security:alerts", 0, 1000
            )  # Keep last 1000 alerts

            logger.critical(f"SECURITY ALERT: Rate limit block - {alert_data}")
        except Exception as e:
            logger.error(f"Error sending rate limit alert: {e}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for request rate limiting."""

    def __init__(self, app, redis_url: str, config: RateLimitConfig) -> None:
        super().__init__(app)
        self.config = config
        self.redis_url = redis_url
        self.rate_limiter: Optional[ProductionRateLimiter] = None

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        try:
            # Initialize rate limiter if needed
            if not self.rate_limiter:
                redis_client = redis.from_url(
                    self.redis_url, decode_responses=True
                )
                self.rate_limiter = ProductionRateLimiter(
                    redis_client, self.config
                )

            # Get client identifier
            client_id = self._get_client_identifier(request)
            endpoint = f"{request.method} {request.url.path}"

            # Check rate limit
            result = await self.rate_limiter.check_rate_limit(
                client_id, endpoint
            )

            if not result.allowed:
                # Rate limit exceeded
                headers = {
                    "X-RateLimit-Limit": str(
                        self._get_limit_for_type(result.limit_type)
                    ),
                    "X-RateLimit-Remaining": str(result.remaining_requests),
                    "X-RateLimit-Reset": (
                        str(int(result.reset_time.timestamp()))
                        if result.reset_time
                        else ""
                    ),
                    "Retry-After": str(result.retry_after_seconds),
                }
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {result.limit_type}",
                    headers=headers,
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(
                self.config.requests_per_minute
            )
            response.headers["X-RateLimit-Remaining"] = str(
                result.remaining_requests
            )

            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Fail open - allow request but log error
            return await call_next(request)

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier for rate limiting."""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.headers.get(
                "X-Real-IP", getattr(request.client, "host", "127.0.0.1")
            )

        # For authenticated requests, also consider user ID
        # This would require integration with auth middleware
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Create a hash of IP + auth token for rate limiting
            # This provides user-based rate limiting while preserving privacy
            user_hash = hashlib.sha256(
                f"{client_ip}:{auth_header}".encode()
            ).hexdigest()[:16]
            return f"user:{user_hash}"

        return f"ip:{client_ip}"

    def _get_limit_for_type(self, limit_type: str) -> int:
        """Get the limit value for a specific limit type."""
        limit_map = {
            "burst": self.config.burst_limit,
            "minute": self.config.requests_per_minute,
            "hour": self.config.requests_per_hour,
            "day": self.config.requests_per_day,
        }
        return limit_map.get(limit_type, self.config.requests_per_minute)


def create_rate_limit_middleware(
    redis_url: str, **kwargs
) -> RateLimitMiddleware:
    """Factory function to create rate limiting middleware."""
    config = RateLimitConfig(**kwargs)
    return RateLimitMiddleware(None, redis_url, config)


# Default configuration for AI Teddy Bear
DEFAULT_RATE_LIMIT_CONFIG = {
    "requests_per_minute": DEFAULT_REQUESTS_PER_MINUTE,
    "requests_per_hour": DEFAULT_REQUESTS_PER_HOUR,
    "requests_per_day": DEFAULT_REQUESTS_PER_DAY,
    "burst_limit": DEFAULT_BURST_LIMIT,
    "block_duration_minutes": DEFAULT_BLOCK_DURATION_MINUTES,
    "exempt_ips": ["127.0.0.1", "::1"],  # Localhost exemptions
}
