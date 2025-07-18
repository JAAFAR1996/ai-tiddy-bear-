from dataclasses import dataclass, field
from typing import Optional, List

"""
AI Response Data Transfer Objects for AI Teddy Bear
This module defines the data structures used to represent
AI-generated responses throughout the application layer.
These DTOs ensure type safety and data consistency when
transferring AI response data between different layers of
the hexagonal architecture.

Classes:
 AIResponse: Complete AI response with text, audio, and safety metadata

Security Features:
 - Safety score validation
 - Content moderation flags
 - COPPA compliance indicators
"""


@dataclass
class AIResponse:
    """AI Response Data Transfer Object.

    Represents a complete AI-generated response including text content,
    audio data, emotional analysis, and safety validation results.
    Used to transfer AI response data between application services.

    Attributes:
        response_text: The main text content of the AI response
        audio_response: Binary audio data for voice synthesis
        emotion: Detected emotional tone of the response
        sentiment: Numerical sentiment score (-1.0 to 1.0)
        safe: Boolean flag indicating content safety
        conversation_id: Optional identifier for conversation tracking
        safety_score: Detailed safety score (0.0 to 1.0)
        moderation_flags: List of content moderation warnings
        age_appropriate: COPPA compliance flag for age appropriateness

    Security:
        - All responses validated for child safety
        - COPPA compliant age-appropriate content
        - Content moderation integrated
    """

    response_text: str = field(
        metadata={"description": "AI generated text response"}
    )
    audio_response: bytes = field(
        metadata={"description": "Binary audio data"}
    )
    emotion: str = field(
        metadata={
            "description": "Detected emotion (happy, sad, excited, etc.)"
        }
    )
    sentiment: float = field(
        metadata={
            "description": (
                "Sentiment score from -1.0 (negative) " "to 1.0 (positive)"
            )
        }
    )
    safe: bool = field(
        metadata={"description": "Content safety validation result"}
    )
    conversation_id: Optional[str] = field(
        default=None,
        metadata={"description": "Conversation tracking ID"},
    )
    safety_score: float = field(
        default=1.0,
        metadata={"description": "Detailed safety score (0.0-1.0)"},
    )
    moderation_flags: List[str] = field(
        default_factory=list,
        metadata={"description": "Content moderation warnings"},
    )
    age_appropriate: bool = field(
        default=True,
        metadata={"description": "COPPA age appropriateness"},
    )

    def __post_init__(self) -> None:
        """Validate AI response data after initialization.

        Ensures all required safety and quality checks are performed
        on the response data before it can be used by the application.

        Raises:
            ValueError: If response data fails validation
        """
        if (
            not isinstance(self.sentiment, (int, float))
            or not -1.0 <= self.sentiment <= 1.0
        ):
            raise ValueError(
                f"Sentiment must be between -1.0 and 1.0, "
                f"got {self.sentiment}",
            )

        if (
            not isinstance(self.safety_score, (int, float))
            or not 0.0 <= self.safety_score <= 1.0
        ):
            raise ValueError(
                f"Safety score must be between 0.0 and 1.0, "
                f"got {self.safety_score}",
            )

        if not self.response_text.strip():
            raise ValueError("Response text cannot be empty")

        # Mark as unsafe if safety score is too low
        if self.safety_score < 0.8:
            self.safe = False
            if "low_safety_score" not in self.moderation_flags:
                self.moderation_flags.append("low_safety_score")
