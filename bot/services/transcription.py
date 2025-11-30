import openai
from bot.config import Config
from bot.services.llm_logger import LLMLogger, LLMRequestTimer
import logging
import os
from typing import Optional

async def transcribe_audio(audio_file_path: str, supabase_client=None, user_id: Optional[int] = None) -> str:
    """
    Transcribe audio file using OpenAI Whisper API

    Args:
        audio_file_path: Path to the audio file
        supabase_client: Optional SupabaseClient for logging
        user_id: Optional user ID for logging

    Returns:
        Transcribed text or empty string if failed
    """
    llm_logger = LLMLogger(supabase_client) if supabase_client else None

    try:
        if not os.path.exists(audio_file_path):
            logging.error(f"Audio file not found: {audio_file_path}")
            return ""

        # Initialize OpenAI client
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

        # Get file size for metadata
        file_size = os.path.getsize(audio_file_path)

        with LLMRequestTimer() as timer:
            try:
                # Open and transcribe the audio file
                with open(audio_file_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )

                transcribed_text = transcript.strip() if transcript else ""

                # Log successful transcription
                if llm_logger:
                    await llm_logger.log_transcription_request(
                        model="whisper-1",
                        output_text=transcribed_text,
                        user_id=user_id,
                        latency_ms=timer.latency_ms,
                        success=True,
                        input_metadata={'file_size_bytes': file_size}
                    )

                return transcribed_text

            except openai.APIError as e:
                # Log failed transcription
                if llm_logger:
                    await llm_logger.log_transcription_request(
                        model="whisper-1",
                        output_text=None,
                        user_id=user_id,
                        latency_ms=timer.latency_ms,
                        success=False,
                        error_message=str(e),
                        input_metadata={'file_size_bytes': file_size}
                    )
                logging.error(f"OpenAI API error during transcription: {e}")
                return ""

    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return ""

async def transcribe_audio_with_language(audio_file_path: str, language: str = None, supabase_client=None, user_id: Optional[int] = None) -> dict:
    """
    Transcribe audio file with language detection and confidence

    Args:
        audio_file_path: Path to the audio file
        language: Optional language hint (e.g., 'en', 'ru')
        supabase_client: Optional SupabaseClient for logging
        user_id: Optional user ID for logging

    Returns:
        Dict with transcription, language, and other metadata
    """
    llm_logger = LLMLogger(supabase_client) if supabase_client else None

    try:
        if not os.path.exists(audio_file_path):
            logging.error(f"Audio file not found: {audio_file_path}")
            return {"text": "", "language": "unknown", "confidence": 0.0}

        # Initialize OpenAI client
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

        # Get file size for metadata
        file_size = os.path.getsize(audio_file_path)

        # Prepare transcription parameters
        transcription_params = {
            "model": "whisper-1",
            "response_format": "verbose_json"
        }

        if language:
            transcription_params["language"] = language

        with LLMRequestTimer() as timer:
            try:
                # Open and transcribe the audio file
                with open(audio_file_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        file=audio_file,
                        **transcription_params
                    )

                result = {
                    "text": transcript.text.strip() if transcript.text else "",
                    "language": transcript.language or "unknown",
                    "duration": transcript.duration or 0,
                    "segments": transcript.segments if hasattr(transcript, 'segments') else []
                }

                # Log successful transcription
                if llm_logger:
                    await llm_logger.log_transcription_request(
                        model="whisper-1",
                        output_text=result["text"],
                        user_id=user_id,
                        latency_ms=timer.latency_ms,
                        success=True,
                        input_metadata={'file_size_bytes': file_size, 'language_hint': language},
                        output_metadata={'detected_language': result["language"], 'duration': result["duration"]}
                    )

                return result

            except openai.APIError as e:
                # Log failed transcription
                if llm_logger:
                    await llm_logger.log_transcription_request(
                        model="whisper-1",
                        output_text=None,
                        user_id=user_id,
                        latency_ms=timer.latency_ms,
                        success=False,
                        error_message=str(e),
                        input_metadata={'file_size_bytes': file_size, 'language_hint': language}
                    )
                logging.error(f"OpenAI API error during detailed transcription: {e}")
                return {"text": "", "language": "unknown", "confidence": 0.0}

    except Exception as e:
        logging.error(f"Error in detailed transcription: {e}")
        return {"text": "", "language": "unknown", "confidence": 0.0}