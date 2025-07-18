from dataclasses import dataclass


@dataclass
class EmotionResult:
    primary_emotion: str
    confidence: float
    all_emotions: dict[str, float]


class EmotionAnalyzer:
    def analyze_text(self, text: str) -> EmotionResult:
        if "happy" in text:
            return EmotionResult("happy", 0.9, {"happy": 0.9})
        if "sad" in text:
            return EmotionResult("sad", 0.9, {"sad": 0.9})
        return EmotionResult("calm", 0.5, {"calm": 0.5})

    def analyze_voice(self, audio_features) -> EmotionResult:
        return EmotionResult("happy", 0.8, {"happy": 0.8})
