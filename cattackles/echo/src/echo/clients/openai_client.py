import logging
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for interacting with OpenAI API."""

    def __init__(self, api_key: str, model_name: str = None):
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            model_name: Name of the OpenAI model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the OpenAI client."""
        try:
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info(f"OpenAI API configured successfully with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure OpenAI API: {e}")
            raise RuntimeError(f"Failed to configure OpenAI API: {e}") from e

    async def generate_content(self, prompt: str) -> str:
        """
        Generate content using the OpenAI model.

        Args:
            prompt: The prompt to send to the model

        Returns:
            Generated text content

        Raises:
            RuntimeError: If client is not configured or generation fails
        """
        if not self.client:
            raise RuntimeError("OpenAI client not configured")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.8,
            )

            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("OpenAI returned empty content")

            return content.strip()
        except Exception as e:
            logger.error(f"Error generating content with OpenAI: {e}")
            raise RuntimeError(f"Failed to generate content: {str(e)}") from e
