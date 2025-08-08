import time
from typing import Dict, Optional

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class OpenAIClient:
    """Client for OpenAI API interactions, specifically Whisper and configured OpenAI model."""

    def __init__(self, api_key: str, model_name: str = "gpt-5-nano", timeout: int = 60):
        """Initialize OpenAI client with API key and timeout settings.

        Args:
            api_key: OpenAI API key
            model_name: OpenAI model name to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.base_url = "https://api.openai.com/v1"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with proper headers."""
        if self._session is None or self._session.closed:
            headers = {"Authorization": f"Bearer {self.api_key}", "User-Agent": "Catmandu-Bot/1.0"}
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def transcribe_audio(self, audio_file: bytes, filename: str) -> Dict:
        """Transcribe audio using OpenAI Whisper API.

        Args:
            audio_file: Audio file content as bytes
            filename: Original filename for format detection

        Returns:
            Dict containing transcription result with text, language, and metadata

        Raises:
            aiohttp.ClientError: For HTTP-related errors
            ValueError: For invalid responses or parameters
        """
        session = await self._get_session()
        request_start_time = time.time()

        # Prepare multipart form data
        data = aiohttp.FormData()
        data.add_field("file", audio_file, filename=filename, content_type="audio/mpeg")
        data.add_field("model", "whisper-1")
        data.add_field("response_format", "verbose_json")

        url = f"{self.base_url}/audio/transcriptions"

        # Enhanced request logging
        logger.info(
            "Sending Whisper API transcription request",
            url=url,
            filename=filename,
            file_size_bytes=len(audio_file),
            file_size_mb=round(len(audio_file) / (1024 * 1024), 2),
            model="whisper-1",
            response_format="verbose_json",
            timeout_seconds=self.timeout,
        )

        try:
            async with session.post(url, data=data) as response:
                request_time = time.time() - request_start_time
                response_data = await response.json()

                # Log response details
                logger.info(
                    "Whisper API response received",
                    filename=filename,
                    status_code=response.status,
                    request_time_seconds=round(request_time, 2),
                    response_size_bytes=len(str(response_data)),
                    response_headers_content_type=response.headers.get("content-type"),
                    response_headers_content_length=response.headers.get("content-length"),
                )

                if response.status != 200:
                    error_info = response_data.get("error", {})
                    error_msg = error_info.get("message", "Unknown error")
                    error_type = error_info.get("type", "unknown")
                    error_code = error_info.get("code", "unknown")

                    logger.error(
                        "Whisper API error response",
                        filename=filename,
                        status_code=response.status,
                        error_message=error_msg,
                        error_type=error_type,
                        error_code=error_code,
                        request_time_seconds=round(request_time, 2),
                        full_error_response=error_info,
                    )
                    raise ValueError(f"Whisper API error: {error_msg}")

                # Enhanced success logging with API response details
                logger.info(
                    "Whisper API transcription completed successfully",
                    filename=filename,
                    request_time_seconds=round(request_time, 2),
                    detected_language=response_data.get("language"),
                    audio_duration_seconds=response_data.get("duration"),
                    text_length_chars=len(response_data.get("text", "")),
                    text_length_words=len(response_data.get("text", "").split()),
                    segments_count=len(response_data.get("segments", [])),
                    processing_speed_ratio=(
                        round(response_data.get("duration", 0) / request_time, 2)
                        if request_time > 0 and response_data.get("duration")
                        else None
                    ),
                    text_preview=(
                        response_data.get("text", "")[:100] + "..."
                        if len(response_data.get("text", "")) > 100
                        else response_data.get("text", "")
                    ),
                )

                return response_data

        except aiohttp.ClientError as e:
            request_time = time.time() - request_start_time
            logger.error(
                "HTTP error during Whisper API transcription",
                filename=filename,
                url=url,
                request_time_seconds=round(request_time, 2),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
        except Exception as e:
            request_time = time.time() - request_start_time
            logger.error(
                "Unexpected error during Whisper API transcription",
                filename=filename,
                url=url,
                request_time_seconds=round(request_time, 2),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    async def improve_text(self, text: str, prompt: str = None) -> Dict:
        """Improve transcription quality using OPENAI_MODEL.

        Args:
            text: Original transcribed text to improve
            prompt: Optional custom prompt for text improvement

        Returns:
            Dict containing improved text and token usage information

        Raises:
            aiohttp.ClientError: For HTTP-related errors
            ValueError: For invalid responses or parameters
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        session = await self._get_session()
        request_start_time = time.time()

        # Default prompt for text improvement
        if prompt is None:
            prompt = (
                "Please improve the following transcribed text by fixing any obvious "
                "transcription errors, adding proper punctuation, and making it more "
                "readable while preserving the original meaning and intent. "
                "Do not add any content that wasn't in the original text."
            )

        payload = {
            "model": self.model_name,
            "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        url = f"{self.base_url}/chat/completions"

        # Enhanced request logging
        logger.info(
            "Sending OpenAI text improvement request",
            url=url,
            model=self.model_name,
            original_text_length=len(text),
            original_word_count=len(text.split()),
            system_prompt_length=len(prompt),
            max_completion_tokens=2000,
            timeout_seconds=self.timeout,
            text_preview=text[:100] + "..." if len(text) > 100 else text,
        )

        try:
            async with session.post(url, json=payload) as response:
                request_time = time.time() - request_start_time
                response_data = await response.json()

                # Log response details
                logger.info(
                    "OpenAI API response received",
                    status_code=response.status,
                    request_time_seconds=round(request_time, 2),
                    response_size_bytes=len(str(response_data)),
                    response_headers_content_type=response.headers.get("content-type"),
                    response_headers_content_length=response.headers.get("content-length"),
                )

                if response.status != 200:
                    error_info = response_data.get("error", {})
                    error_msg = error_info.get("message", "Unknown error")
                    error_type = error_info.get("type", "unknown")
                    error_code = error_info.get("code", "unknown")

                    logger.error(
                        "OpenAI API error response",
                        status_code=response.status,
                        error_message=error_msg,
                        error_type=error_type,
                        error_code=error_code,
                        request_time_seconds=round(request_time, 2),
                        original_text_length=len(text),
                        full_error_response=error_info,
                    )
                    raise ValueError(f"OpenAI API error: {error_msg}")

                # Extract improved text and usage information
                improved_text = response_data["choices"][0]["message"]["content"]
                usage = response_data.get("usage", {})
                model_used = response_data.get("model", self.model_name)
                finish_reason = response_data["choices"][0].get("finish_reason")

                # Enhanced success logging with comprehensive API response details
                logger.info(
                    "OpenAI text improvement completed successfully",
                    model_used=model_used,
                    request_time_seconds=round(request_time, 2),
                    finish_reason=finish_reason,
                    original_text_length=len(text),
                    original_word_count=len(text.split()),
                    improved_text_length=len(improved_text),
                    improved_word_count=len(improved_text.split()),
                    text_length_change=len(improved_text) - len(text),
                    word_count_change=len(improved_text.split()) - len(text.split()),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    tokens_per_second=(
                        round(usage.get("total_tokens", 0) / request_time, 2) if request_time > 0 else None
                    ),
                    improved_text_preview=improved_text[:100] + "..." if len(improved_text) > 100 else improved_text,
                )

                return {"text": improved_text, "usage": usage, "model": model_used}

        except aiohttp.ClientError as e:
            request_time = time.time() - request_start_time
            logger.error(
                "HTTP error during OpenAI text improvement",
                url=url,
                request_time_seconds=round(request_time, 2),
                original_text_length=len(text),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
        except Exception as e:
            request_time = time.time() - request_start_time
            logger.error(
                "Unexpected error during OpenAI text improvement",
                url=url,
                request_time_seconds=round(request_time, 2),
                original_text_length=len(text),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    async def close(self):
        """Close HTTP client connections."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("OpenAI client session closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
