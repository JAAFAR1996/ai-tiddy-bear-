from enum import Enum


class SafetyLevel(Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def create_safe_level(cls) -> "SafetyLevel":
        """Create a safe level instance."""
        return cls.NONE

    def is_safe(self) -> bool:
        """Check if the safety level indicates safe content."""
        return self in [SafetyLevel.NONE, SafetyLevel.LOW]

    @property
    def level(self) -> int:
        """Get numeric level for comparison."""
        level_map = {
            SafetyLevel.NONE: 0,
            SafetyLevel.LOW: 1,
            SafetyLevel.MODERATE: 2,
            SafetyLevel.HIGH: 3,
            SafetyLevel.CRITICAL: 4,
        }
        return level_map.get(self, 0)
