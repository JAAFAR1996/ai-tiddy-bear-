from typing import Dict
from fastapi import Request
from .header_config import SecurityHeadersConfig

"""Security Headers Builder

This module provides utilities for building security headers
based on configuration and request context.
"""


class SecurityHeadersBuilder:
    """Builder class for constructing security headers"""

    def __init__(self, config: SecurityHeadersConfig) -> None:
        self.config = config

    def build_all_headers(self, request: Request) -> Dict[str, str]:
        """
        Build all security headers for a request
        Args:
            request: FastAPI request object
        Returns:
            Dict of header name -> value pairs
        """
        headers = {}

        # Basic security headers
        headers.update(self._build_basic_headers())

        # Content Security Policy
        headers.update(self._build_csp_headers())

        # HTTP Strict Transport Security
        headers.update(self._build_hsts_headers(request))

        # Permissions Policy
        headers.update(self._build_permissions_headers())

        # Cross-Origin headers
        headers.update(self._build_cors_headers())

        # Child safety headers
        if self.config.child_safety_mode:
            headers.update(self._build_child_safety_headers())

        # Request-specific headers
        headers.update(self._build_dynamic_headers(request))

        return headers

    def _build_basic_headers(self) -> Dict[str, str]:
        """Build basic security headers"""
        return {
            "X-Frame-Options": self.config.x_frame_options,
            "X-Content-Type-Options": self.config.x_content_type_options,
            "X-XSS-Protection": self.config.x_xss_protection,
            "Referrer-Policy": self.config.referrer_policy,
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen",
        }

    def _build_csp_headers(self) -> Dict[str, str]:
        """Build Content Security Policy header"""
        csp = self.config.csp
        directives = [
            f"default-src {csp.default_src}",
            f"script-src {csp.script_src}",
            f"style-src {csp.style_src}",
            f"img-src {csp.img_src}",
            f"connect-src {csp.connect_src}",
            f"font-src {csp.font_src}",
            f"object-src {csp.object_src}",
            f"media-src {csp.media_src}",
            f"frame-src {csp.frame_src}",
            f"child-src {csp.child_src}",
            f"worker-src {csp.worker_src}",
            f"manifest-src {csp.manifest_src}",
            f"base-uri {csp.base_uri}",
            f"form-action {csp.form_action}",
            f"frame-ancestors {csp.frame_ancestors}",
        ]

        if csp.upgrade_insecure_requests:
            directives.append("upgrade-insecure-requests")

        return {"Content-Security-Policy": "; ".join(directives)}

    def _build_hsts_headers(self, request: Request) -> Dict[str, str]:
        """Build HSTS headers for HTTPS requests"""
        headers = {}

        # Only add HSTS for HTTPS requests
        if request.url.scheme == "https" and self.config.hsts_max_age > 0:
            hsts_value = f"max-age={self.config.hsts_max_age}"

            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"

            if self.config.hsts_preload:
                hsts_value += "; preload"

            headers["Strict-Transport-Security"] = hsts_value

        return headers

    def _build_permissions_headers(self) -> Dict[str, str]:
        """Build Permissions Policy header"""
        if not self.config.permissions_policy:
            return {}

        permissions = ", ".join(
            [
                f"{feature}=({value})"
                for feature, value in self.config.permissions_policy.items()
            ]
        )

        return {"Permissions-Policy": permissions}

    def _build_cors_headers(self) -> Dict[str, str]:
        """Build Cross - Origin policy headers"""
        return {
            "Cross-Origin-Embedder-Policy": self.config.cross_origin_embedder_policy,
            "Cross-Origin-Opener-Policy": self.config.cross_origin_opener_policy,
            "Cross-Origin-Resource-Policy": self.config.cross_origin_resource_policy,
        }

    def _build_child_safety_headers(self) -> Dict[str, str]:
        """Build child safety specific headers"""
        headers = self.config.custom_child_headers.copy()

        # Add additional child safety headers
        headers.update(
            {
                "X-DNS-Prefetch-Control": "off",
                "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet, noimageindex",
                "X-Security-Policy": "child-safe-mode",
            }
        )

        return headers

    def _build_dynamic_headers(self, request: Request) -> Dict[str, str]:
        """Build headers that depend on request context"""
        headers = {}

        # Add request ID if available
        if hasattr(request.state, "request_id"):
            headers["X-Request-ID"] = request.state.request_id

        # Add timing information
        if hasattr(request.state, "start_time"):
            import time

            processing_time = int(
                (time.time() - request.state.start_time) * 1000
            )
            headers["X-Response-Time"] = f"{processing_time}ms"

        # User-specific headers
        user = getattr(request.state, "user", None)
        if user:
            headers.update(self._build_user_headers(user))

        return headers

    def _build_user_headers(self, user: dict) -> Dict[str, str]:
        """Build headers specific to user type"""
        headers = {}
        user_role = user.get("role", "guest")

        if user_role == "child":
            headers.update(
                {
                    "X-User-Type": "child",
                    "X-Enhanced-Safety": "enabled",
                    "Cache-Control": "no-store, must-revalidate",
                }
            )
        elif user_role == "parent":
            headers.update(
                {"X-User-Type": "parent", "X-Parental-Controls": "available"}
            )
        elif user_role == "admin":
            headers.update({"X-User-Type": "admin", "X-Admin-Mode": "enabled"})

        return headers


def create_headers_builder(
    environment: str = "production",
) -> SecurityHeadersBuilder:
    """
    Create a headers builder with appropriate configuration
    Args:
        environment: Environment name(production, development, testing)
    Returns:
        Configured SecurityHeadersBuilder instance
    """
    from .header_config import get_production_config, get_development_config

    if environment == "production":
        config = get_production_config()
    else:
        config = get_development_config()

    return SecurityHeadersBuilder(config)
