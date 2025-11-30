"""
LLM Request Logger Service

Tracks all LLM API requests (chat, embeddings, transcriptions) to the database
for monitoring, analytics, and cost tracking.
"""

import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging


class LLMLogger:
    """Service for logging LLM API requests to database"""

    def __init__(self, supabase_client):
        """
        Initialize LLM Logger

        Args:
            supabase_client: SupabaseClient instance for database operations
        """
        self.supabase_client = supabase_client
        self.logger = logging.getLogger(__name__)

    async def log_chat_request(
        self,
        model: str,
        input_text: str,
        output_text: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        tokens_total: Optional[int] = None,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        output_metadata: Optional[Dict[str, Any]] = None,
        raw_request: Optional[Dict[str, Any]] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a chat completion request

        Args:
            model: Model name (e.g., 'gpt-4-turbo', 'gpt-3.5-turbo')
            input_text: User's input/prompt
            output_text: Model's response
            user_id: Database user ID
            session_id: Conversation/session identifier
            tokens_prompt: Token count for prompt
            tokens_completion: Token count for completion
            tokens_total: Total token count
            latency_ms: Request latency in milliseconds
            cost_usd: Estimated cost in USD
            success: Whether request succeeded
            error_message: Error message if failed
            input_metadata: Additional input metadata
            output_metadata: Additional output metadata
            raw_request: Raw request data
            raw_response: Raw response data

        Returns:
            bool: True if logged successfully, False otherwise
        """
        return await self._log_request(
            request_type='chat',
            model=model,
            input_text=input_text,
            output_text=output_text,
            user_id=user_id,
            session_id=session_id,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error_message=error_message,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            raw_request=raw_request,
            raw_response=raw_response
        )

    async def log_embedding_request(
        self,
        model: str,
        input_text: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        tokens_total: Optional[int] = None,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        output_metadata: Optional[Dict[str, Any]] = None,
        raw_request: Optional[Dict[str, Any]] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log an embedding request

        Args:
            model: Model name (e.g., 'text-embedding-3-large')
            input_text: Text to embed
            user_id: Database user ID
            session_id: Session identifier
            tokens_total: Total token count
            latency_ms: Request latency in milliseconds
            cost_usd: Estimated cost in USD
            success: Whether request succeeded
            error_message: Error message if failed
            input_metadata: Additional input metadata
            output_metadata: Additional output metadata (e.g., embedding dimensions)
            raw_request: Raw request data
            raw_response: Raw response data

        Returns:
            bool: True if logged successfully, False otherwise
        """
        return await self._log_request(
            request_type='embedding',
            model=model,
            input_text=input_text,
            output_text=None,  # Embeddings don't have text output
            user_id=user_id,
            session_id=session_id,
            tokens_prompt=None,
            tokens_completion=None,
            tokens_total=tokens_total,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error_message=error_message,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            raw_request=raw_request,
            raw_response=raw_response
        )

    async def log_transcription_request(
        self,
        model: str,
        output_text: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        output_metadata: Optional[Dict[str, Any]] = None,
        raw_request: Optional[Dict[str, Any]] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a transcription request (e.g., Whisper)

        Args:
            model: Model name (e.g., 'whisper-1')
            output_text: Transcribed text
            user_id: Database user ID
            session_id: Session identifier
            latency_ms: Request latency in milliseconds
            cost_usd: Estimated cost in USD
            success: Whether request succeeded
            error_message: Error message if failed
            input_metadata: Additional input metadata (e.g., audio duration, format)
            output_metadata: Additional output metadata (e.g., language detected)
            raw_request: Raw request data
            raw_response: Raw response data

        Returns:
            bool: True if logged successfully, False otherwise
        """
        return await self._log_request(
            request_type='transcription',
            model=model,
            input_text=None,  # Audio input, not text
            output_text=output_text,
            user_id=user_id,
            session_id=session_id,
            tokens_prompt=None,
            tokens_completion=None,
            tokens_total=None,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error_message=error_message,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            raw_request=raw_request,
            raw_response=raw_response
        )

    async def _log_request(
        self,
        request_type: str,
        model: str,
        input_text: Optional[str],
        output_text: Optional[str],
        user_id: Optional[int],
        session_id: Optional[str],
        tokens_prompt: Optional[int],
        tokens_completion: Optional[int],
        tokens_total: Optional[int],
        latency_ms: Optional[int],
        cost_usd: Optional[float],
        success: bool,
        error_message: Optional[str],
        input_metadata: Optional[Dict[str, Any]],
        output_metadata: Optional[Dict[str, Any]],
        raw_request: Optional[Dict[str, Any]],
        raw_response: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Internal method to log request to database

        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            self.logger.info(f"🔍 Attempting to log {request_type} request - Model: {model}, User: {user_id}, Latency: {latency_ms}ms")
            await self.supabase_client.log_llm_request(
                request_type=request_type,
                model=model,
                user_id=user_id,
                session_id=session_id,
                input_text=input_text,
                input_metadata=input_metadata or {},
                output_text=output_text,
                output_metadata=output_metadata or {},
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                success=success,
                error_message=error_message,
                raw_request=raw_request,
                raw_response=raw_response
            )
            self.logger.info(f"✅ Successfully logged {request_type} request")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to log LLM request: {e}")
            import traceback
            traceback.print_exc()
            return False


class LLMRequestTimer:
    """Context manager for timing LLM requests"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.latency_ms = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.latency_ms = int((self.end_time - self.start_time) * 1000)
        return False  # Don't suppress exceptions
