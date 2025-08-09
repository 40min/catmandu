import logging
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini API."""

    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        """
        Initialize the Gemini client.

        Args:
            api_key: Google Gemini API key
            model_name: Name of the Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model: Optional[genai.GenerativeModel] = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the Gemini model."""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini API configured successfully with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            raise RuntimeError(f"Failed to configure Gemini API: {e}") from e

    async def generate_content(self, prompt: str) -> str:
        """
        Generate content using the Gemini model.

        Args:
            prompt: The prompt to send to the model

        Returns:
            Generated text content

        Raises:
            RuntimeError: If model is not configured or generation fails
        """
        if not self.model:
            raise RuntimeError("Gemini model not configured")

        try:
            response = self.model.generate_content(prompt)
            content = response.text.strip() if response.text else ""

            if not content:
                return "😴 The joker is sleeping... try again later!"

            return content
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            raise RuntimeError(f"Failed to generate content: {str(e)}") from e
