"""from typing import Dict, Any
from fastapi import FastAPI # Added FastAPI import
from starlette.middleware.cors import CORSMiddleware
from src.infrastructure.config.settings import get_settings.
"""

"""CORS middleware configuration for child safety and security.
Implements 2025 security standards for AI Teddy Bear system.
"""


def get_cors_settings() -> Dict[str, Any]:
    """Get CORS settings with child safety and security focus.
    Returns: Dictionary with CORS configuration optimized for child safety.
    """
    settings = get_settings()
    # Base CORS settings for production security
    cors_config = {
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": [
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Child-ID",  # Custom header for child identification
            "X-Device-ID",  # ESP32 device identification
            "X-Session-ID",  # Session tracking for child safety
        ],
    }

    # Environment-specific origin settings
    # Localhost URLs are only used in development mode, not in production
    if settings.application.ENVIRONMENT == "development":
        cors_config["allow_origins"] = settings.application.CORS_ORIGINS or [
            "http://localhost:3000",  # React dev server
            "http://localhost:8080",  # Vue dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://localhost:5173",  # Vite dev server
        ]
    elif settings.application.ENVIRONMENT == "staging":
        cors_config["allow_origins"] = [
            "https://staging-teddy.example.com",
            "https://staging-dashboard.example.com",
        ]
    elif settings.application.ENVIRONMENT == "production":
        # Restrictive CORS for production child safety
        cors_config["allow_origins"] = [
            "https://teddy-dashboard.example.com",
            "https://parent-portal.example.com",
        ]
    else:
        # Fallback - very restrictive
        cors_config["allow_origins"] = []

    return cors_config


def setup_cors_middleware(app: FastAPI) -> None:
    """Legacy function for backwards compatibility."""
    cors_settings = get_cors_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_settings["allow_origins"],
        allow_credentials=cors_settings["allow_credentials"],
        allow_methods=cors_settings["allow_methods"],
        allow_headers=cors_settings["allow_headers"],
    )
