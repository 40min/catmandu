from typing import Dict, Optional

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class OpenAIClient:
    """Client for OpenAI API interactions, specifically Whisper and GPT-4o-mini."""

    def __init__(self, api_key: str, timeout: int = 60):
        """Initialize OpenAI client with API key and timeout settings.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
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

        # Prepare multipart form data
        data = aiohttp.FormData()
        data.add_field("file", audio_file, filename=filename, content_type="audio/mpeg")
        data.add_field("model", "whisper-1")
        data.add_field("response_format", "verbose_json")

        url = f"{self.base_url}/audio/transcriptions"

        try:
            logger.info("Sending audio transcription request", filename=filename, size=len(audio_file))

            async with session.post(url, data=data) as response:
                response_data = await response.json()

                if response.status != 200:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    logger.error("Whisper API error", status=response.status, error=error_msg, filename=filename)
                    raise ValueError(f"Whisper API error: {error_msg}")

                logger.info(
                    "Audio transcription completed",
                    filename=filename,
                    language=response_data.get("language"),
                    duration=response_data.get("duration"),
                )

                return response_data

        except aiohttp.ClientError as e:
            logger.error("HTTP error during transcription", error=str(e), filename=filename)
            raise
        except Exception as e:
            logger.error("Unexpected error during transcription", error=str(e), filename=filename)
            raise

    async def improve_text(self, text: str, prompt: str = None) -> Dict:
        """Improve transcription quality using GPT-4o-mini.

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

        # Default prompt for text improvement
        if prompt is None:
            prompt = (
                "Please improve the following transcribed text by fixing any obvious "
                "transcription errors, adding proper punctuation, and making it more "
                "readable while preserving the original meaning and intent. "
                "Do not add any content that wasn't in the original text."
            )

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        url = f"{self.base_url}/chat/completions"

        try:
            logger.info("Sending text improvement request", text_length=len(text))

            async with session.post(url, json=payload) as response:
                response_data = await response.json()

                if response.status != 200:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "GPT-4o-mini API error", status=response.status, error=error_msg, text_length=len(text)
                    )
                    raise ValueError(f"GPT-4o-mini API error: {error_msg}")

                # Extract improved text and usage information
                improved_text = response_data["choices"][0]["message"]["content"]
                usage = response_data.get("usage", {})

                logger.info(
                    "Text improvement completed",
                    original_length=len(text),
                    improved_length=len(improved_text),
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )

                return {"text": improved_text, "usage": usage, "model": "gpt-4o-mini"}

        except aiohttp.ClientError as e:
            logger.error("HTTP error during text improvement", error=str(e), text_length=len(text))
            raise
        except Exception as e:
            logger.error("Unexpected error during text improvement", error=str(e), text_length=len(text))
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
