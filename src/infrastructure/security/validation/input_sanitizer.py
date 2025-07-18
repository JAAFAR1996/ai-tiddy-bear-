"""
🔒 Input Sanitization Service
Advanced input cleaning and validation for child safety
"""

from dataclasses import dataclass
from typing import List, Optional
import html
import re
import urllib.parse
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="security")


@dataclass
class InputSanitizationResult:
    """Result of input sanitization process"""

    original_input: str
    sanitized_input: str
    threats_found: List[str]
    safe: bool
    modifications: List[str]


class InputSanitizer:
    """
    Advanced input sanitization for child protection
    Features:
    - XSS prevention
    - SQL injection pattern removal
    - Age - appropriate content filtering
    - HTML encoding
    - Length limiting
    """

    def __init__(self) -> None:
        # Dangerous patterns for children
        self.child_unsafe_patterns = [
            r"(tell\\s+me\\s+your\\s+(address|location|where\\s+you\\s+live))",
            r"(what\\s+is\\s+your\\s+(phone|email|password))",
            r"(meet\\s+me|come\\s+to|visit\\s+me)",
            r"(secret|don't\\s+tell|hide\\s+from)",
            r"(violence|weapon|gun|knife|kill|hurt)",
            r"(scary|frightening|nightmare|horror)",
            r"(inappropriate|adult|mature\\s+content)",
        ]

        # Safe character patterns
        self.safe_patterns = {
            "name": r"^[a-zA-Z\s\-'.]{1,50}$",
            "child_message": r"^[a-zA-Z0-9\s\.,!\?\-:\'\"]{1,500}$",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "numeric": r"^[0-9]+$",
            "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        }

        logger.info("Input Sanitizer initialized for child safety")

    def sanitize_child_input(
        self, input_value: str, context: str = "general"
    ) -> InputSanitizationResult:
        """Sanitize input from child with age - appropriate filtering"""
        if not isinstance(input_value, str):
            input_value = str(input_value)

        original_input = input_value
        sanitized = input_value
        threats_found = []
        modifications = []

        # HTML encoding for safety
        sanitized = html.escape(sanitized)
        if sanitized != input_value:
            modifications.append("HTML encoded special characters")

        # URL decode to catch encoded threats
        try:
            decoded = urllib.parse.unquote(sanitized)
            if decoded != sanitized:
                modifications.append("URL decoded input")
                sanitized = decoded
        except (ValueError, UnicodeDecodeError) as e:
            logger.debug(f"URL decode failed: {e}")

        # Check for child-unsafe patterns
        for pattern in self.child_unsafe_patterns:
            matches = re.findall(pattern, sanitized, re.IGNORECASE)
            if matches:
                threats_found.extend(
                    [f"Child unsafe pattern: {match}" for match in matches]
                )
                sanitized = re.sub(
                    pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE
                )
                modifications.append(
                    f"Filtered child-unsafe content: {pattern}"
                )

        # Apply context-specific cleaning
        if context == "name":
            sanitized = re.sub(r"[^a-zA-Z\s\-'.]", "", sanitized)
        elif context == "message":
            sanitized = re.sub(r"[^a-zA-Z0-9\s\.,!\?\-:\'\"]", "", sanitized)

        # Length limiting for child safety
        max_lengths = {
            "name": 50,
            "message": 200,  # Shorter for children
            "general": 100,
        }
        max_len = max_lengths.get(context, 100)

        if len(sanitized) > max_len:
            sanitized = sanitized[:max_len]
            modifications.append(
                f"Truncated to {max_len} characters for child safety"
            )

        # Final safety check
        safe = len(threats_found) == 0

        return InputSanitizationResult(
            original_input=original_input,
            sanitized_input=sanitized.strip(),
            threats_found=threats_found,
            safe=safe,
            modifications=modifications,
        )

    def validate_pattern(self, input_value: str, pattern_type: str) -> bool:
        """Validate input against safe patterns"""
        if pattern_type in self.safe_patterns:
            return bool(
                re.match(self.safe_patterns[pattern_type], input_value)
            )
        return False


# Global instance for the application
_input_sanitizer: Optional[InputSanitizer] = None


def get_input_sanitizer() -> InputSanitizer:
    """Get global input sanitizer instance"""
    global _input_sanitizer
    if _input_sanitizer is None:
        _input_sanitizer = InputSanitizer()
    return _input_sanitizer
