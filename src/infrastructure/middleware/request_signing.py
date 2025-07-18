from datetime import datetime
from typing import Dict, Optional, Any
import hashlib
import json
import time
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import hmac

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="infrastructure")


class RequestSigningMiddleware(BaseHTTPMiddleware):
    """
    HMAC - SHA256 request signature validation middleware.
    Features:
    - Request tampering prevention
    - Replay attack protection with timestamp validation
    - Configurable signature algorithms
    - Audit logging for security monitoring
    - Performance optimized with async operations
    """

    def __init__(
        self,
        app,
        secret_key: str,
        signature_header: str = "X-Signature",
        timestamp_header: str = "X-Timestamp",
        max_age_seconds: int = 300,  # 5 minutes
        require_timestamp: bool = True,
        exempt_paths: Optional[list] = None,
    ) -> None:
        """
        Initialize request signing middleware.
        Args:
            secret_key: HMAC secret key for signature generation
            signature_header: HTTP header containing the signature
            timestamp_header: HTTP header containing request timestamp
            max_age_seconds: Maximum age for timestamp validation
            require_timestamp: Whether timestamp validation is required
            exempt_paths: Paths that do not require signatures (e.g., health checks)
        """
        super().__init__(app)
        if not secret_key or len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        self.secret_key = secret_key.encode("utf-8")
        self.signature_header = signature_header
        self.timestamp_header = timestamp_header
        self.max_age_seconds = max_age_seconds
        self.require_timestamp = require_timestamp
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        # Performance tracking
        self.signature_checks = 0
        self.signature_failures = 0
        self.timestamp_failures = 0

        logger.info(
            f"Request signing middleware initialized with {len(self.exempt_paths)} exempt paths"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with signature validation."""
        start_time = time.time()
        try:
            # Check if path is exempt from signing
            if self._is_exempt_path(request.url.path):
                return await call_next(request)

            # Validate request signature
            validation_result = await self._validate_request_signature(request)
            if not validation_result["valid"]:
                self.signature_failures += 1
                # Log security event
                await self._log_security_event(
                    request,
                    "signature_validation_failed",
                    validation_result["reason"],
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Invalid request signature",
                        "code": "SIGNATURE_INVALID",
                        "message": validation_result["reason"],
                    },
                )

            self.signature_checks += 1
            # Add signature info to request state for downstream use
            request.state.signature_validated = True
            request.state.signature_algorithm = "HMAC-SHA256"

            # Process request
            response = await call_next(request)

            # Add response signature if configured
            if (
                hasattr(request.state, "sign_response")
                and request.state.sign_response
            ):
                response = await self._sign_response(response, request)

            processing_time = time.time() - start_time
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request signing middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal signature validation error",
                    "code": "SIGNATURE_ERROR",
                },
            )

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from signature validation."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    async def _validate_request_signature(
        self, request: Request
    ) -> Dict[str, Any]:
        """
        Validate HMAC-SHA256 signature for incoming request.
        Returns:
            Dict with 'valid' boolean and 'reason' string
        """
        try:
            # Get signature from headers
            provided_signature = request.headers.get(self.signature_header)
            if not provided_signature:
                return {"valid": False, "reason": "Missing signature header"}

            # Validate timestamp if required
            if self.require_timestamp:
                timestamp_validation = await self._validate_timestamp(request)
                if not timestamp_validation["valid"]:
                    self.timestamp_failures += 1
                    return timestamp_validation

            # Get request body
            body = await self._get_request_body(request)

            # Generate expected signature
            expected_signature = await self._generate_signature(request, body)

            # Verify signature using timing-safe comparison
            if not hmac.compare_digest(provided_signature, expected_signature):
                return {"valid": False, "reason": "Signature mismatch"}

            return {"valid": True, "reason": "Signature valid"}
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}

    async def _validate_timestamp(self, request: Request) -> Dict[str, Any]:
        """Validate request timestamp to prevent replay attacks."""
        timestamp_str = request.headers.get(self.timestamp_header)
        if not timestamp_str:
            return {"valid": False, "reason": "Missing timestamp header"}

        try:
            # Parse timestamp (expecting Unix timestamp)
            request_timestamp = float(timestamp_str)
            current_timestamp = time.time()

            # Check if timestamp is too old
            age_seconds = current_timestamp - request_timestamp
            if age_seconds > self.max_age_seconds:
                return {
                    "valid": False,
                    "reason": f"Request too old: {age_seconds:.1f}s > {self.max_age_seconds}s",
                }

            # Check if timestamp is too far in the future (clock skew protection)
            if age_seconds < -60:  # Allow 1 minute clock skew
                return {
                    "valid": False,
                    "reason": "Request timestamp too far in future",
                }

            return {"valid": True, "reason": "Timestamp valid"}
        except (ValueError, TypeError) as e:
            return {"valid": False, "reason": f"Invalid timestamp format: {e}"}

    async def _get_request_body(self, request: Request) -> bytes:
        """Get request body for signature calculation."""
        # Check if body has already been read
        if hasattr(request.state, "cached_body"):
            return request.state.cached_body

        # Read and cache body
        body = await request.body()
        request.state.cached_body = body
        return body

    async def _generate_signature(self, request: Request, body: bytes) -> str:
        """
        Generate HMAC-SHA256 signature for request.
        Signature includes:
        - HTTP method
        - Request path and query string
        - Timestamp (if provided)
        - Request body
        - Selected headers
        """
        # Build signature payload
        signature_parts = [
            request.method.upper(),
            str(request.url.path),
            str(request.url.query) if request.url.query else "",
        ]

        # Add timestamp if present
        if self.require_timestamp:
            timestamp = request.headers.get(self.timestamp_header, "")
            signature_parts.append(timestamp)

        # Add important headers to signature
        important_headers = ["content-type", "user-agent"]
        for header in important_headers:
            header_value = request.headers.get(header, "")
            signature_parts.append(f"{header}:{header_value}")

        # Add body
        signature_parts.append(body.decode("utf - 8", errors="ignore"))

        # Create signature payload
        payload = "\n".join(signature_parts)

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key, payload.encode("utf - 8"), hashlib.sha256
        ).hexdigest()

        return signature

    async def _sign_response(
        self, response: Response, request: Request
    ) -> Response:
        """Add signature to response headers."""
        try:
            # Get response body if available
            if hasattr(response, "body"):
                body = response.body
            else:
                body = b""

            # Generate response signature
            response_payload = f"{response.status_code}\n{body.decode('utf - 8', errors='ignore')}"
            response_signature = hmac.new(
                self.secret_key,
                response_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Add signature to response headers
            response.headers["X-Response-Signature"] = response_signature
            response.headers["X-Signature-Algorithm"] = "HMAC-SHA256"
        except Exception as e:
            logger.error(f"Response signing error: {e}")

        return response

    async def _log_security_event(
        self, request: Request, event_type: str, details: str
    ) -> None:
        """Log security events for monitoring and alerting."""
        security_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details,
            "request_info": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query) if request.url.query else None,
                "client_ip": (
                    request.client.host if request.client else "unknown"
                ),
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        }

        # Log as warning for failed signature validation
        logger.warning(f"Security event: {json.dumps(security_event)}")
        # In production, this could also send to SIEM/monitoring system

    def get_statistics(self) -> Dict[str, Any]:
        """Get middleware performance and security statistics."""
        total_checks = max(self.signature_checks + self.signature_failures, 1)
        success_rate = (self.signature_checks / total_checks) * 100
        return {
            "signature_checks": self.signature_checks,
            "signature_failures": self.signature_failures,
            "timestamp_failures": self.timestamp_failures,
            "success_rate_percent": round(success_rate, 2),
            "exempt_paths": self.exempt_paths,
            "config": {
                "signature_header": self.signature_header,
                "timestamp_header": self.timestamp_header,
                "max_age_seconds": self.max_age_seconds,
                "require_timestamp": self.require_timestamp,
            },
        }


class RequestSigningHelper:
    """
    Helper class for clients to generate request signatures.
    """

    def __init__(self, secret_key: str) -> None:
        """Initialize with shared secret key."""
        self.secret_key = secret_key.encode("utf-8")

    def sign_request(
        self,
        method: str,
        path: str,
        query_string: str = "",
        body: str = "",
        timestamp: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Generate signature and headers for a request.
        Returns:
            Dict with signature headers to add to request
        """
        if timestamp is None:
            timestamp = time.time()

        headers = headers or {}

        # Build signature payload (must match middleware logic)
        signature_parts = [
            method.upper(),
            path,
            query_string,
            str(timestamp),
        ]

        # Add important headers
        important_headers = ["content-type", "user-agent"]
        for header in important_headers:
            header_value = headers.get(header.lower(), "")
            signature_parts.append(f"{header}:{header_value}")

        signature_parts.append(body)

        # Generate signature
        payload = "\n".join(signature_parts)
        signature = hmac.new(
            self.secret_key, payload.encode("utf - 8"), hashlib.sha256
        ).hexdigest()

        return {
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Signature-Algorithm": "HMAC-SHA256",
        }

    def verify_response_signature(
        self, response_body: str, status_code: int, signature: str
    ) -> bool:
        """Verify response signature from server."""
        response_payload = f"{status_code}\n{response_body}"
        expected_signature = hmac.new(
            self.secret_key, response_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
