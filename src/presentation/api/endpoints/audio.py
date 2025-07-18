# Standard library imports
from typing import Any, Dict, Optional

# Optional imports

# Third-party imports
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

# Local imports (صحح المسارات حسب مشروعك)
from src.application.services.audio_processing_service import (
    AudioProcessingService,
)
from src.infrastructure.di.container import container
from src.infrastructure.security.real_auth_service import (
    get_current_user,
    UserInfo,
)

router = APIRouter()


@router.post(
    "/transcribe",
    summary="Transcribe audio input and return a child-safe response",
    response_description="A streaming audio response or an error message.",
)
async def transcribe_audio(
    audio_file: UploadFile = File(
        ..., description="The audio file to transcribe (e.g., WAV, MP3)."
    ),
    child_context: Optional[Dict[str, Any]] = None,
    voice_service: AudioProcessingService = Depends(
        container.audio_processing_service
    ),
    current_user: UserInfo = Depends(get_current_user),
) -> StreamingResponse:
    """
    Transcribes an uploaded audio file and processes it to generate a child-safe AI response.
    This endpoint:
    - Handles audio input from devices (like ESP32) or other sources.
    - Transcribes it using the `AudioProcessingService`.
    - Uses the `AIOrchestrationService` to generate an appropriate, moderated response.
    - Streams the response back as audio.

    Security and Safety:
    - Input audio is validated for type and size.
    - All AI interactions are routed through child-safe moderation layers.
    - Requires authentication via JWT.

    Parameters:
    - audio_file: The audio file to be transcribed. Supported formats include WAV, MP3.
    - child_context: Optional JSON object providing additional context about the child for personalization.

    Responses:
    - 200 OK: Returns a StreamingResponse containing the audio of the AI's reply.
    - 400 Bad Request: If the input audio is invalid or child context is malformed.
    - 401 Unauthorized: If authentication credentials are missing or invalid.
    - 415 Unsupported Media Type: If the uploaded file is not a supported audio format.
    - 413 Request Entity Too Large: If the uploaded file exceeds the maximum allowed size.
    - 500 Internal Server Error: If an unexpected error occurs during processing.
    """
    # هنا تكتب منطق المعالجة الخاص بك
    # مثال: استدعاء voice_service لتحويل الصوت إلى نص ثم الرد المناسب
    # return StreamingR
