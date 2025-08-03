import json
import logging
from typing import List, Optional

from echo.clients.gemini_client import GeminiClient
from echo.clients.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class EchoCattackle:
    """Core echo cattackle functionality."""

    def __init__(self, openai_client: Optional[OpenAIClient] = None, gemini_client: Optional[GeminiClient] = None):
        """
        Initialize the echo cattackle.

        Args:
            openai_client: Optional OpenAI client for joke generation (primary)
            gemini_client: Optional Gemini client for joke generation (fallback)
        """
        self.openai_client = openai_client
        self.gemini_client = gemini_client

    async def echo(self, text: str, accumulated_params: Optional[List[str]] = None) -> str:
        """
        Echoes back the text from the payload, with support for accumulated parameters.
        Returns exactly the same text as entered, joining accumulated messages with semicolon.

        Args:
            text: The text to echo (immediate parameter)
            accumulated_params: List of accumulated messages (optional)

        Returns:
            JSON string with data and error fields
        """
        logger.info(f"Received echo request with text: '{text}', accumulated_params: {accumulated_params}")

        # Handle accumulated parameters vs immediate parameters
        if accumulated_params and len(accumulated_params) > 0:
            # Use accumulated parameters joined with semicolon
            logger.info(f"Using accumulated parameters: {accumulated_params}")
            data = "; ".join(accumulated_params)
        elif text.strip():
            # Use immediate parameter
            logger.info(f"Using immediate parameter: '{text}'")
            data = text
        else:
            # No parameters provided
            data = (
                "Please provide some text to echo. Usage: /echo_echo <your text> or send messages"
                "first then use /echo_echo"
            )

        response = json.dumps({"data": data, "error": None})
        logger.info(f"Sending echo response: {response}")
        return response

    async def ping(self, text: str, accumulated_params: Optional[List[str]] = None) -> str:
        """
        Returns a simple pong response with information about parameters received.

        Args:
            text: Optional text (logged but ignored)
            accumulated_params: List of accumulated messages (logged but ignored)

        Returns:
            JSON string with pong response
        """
        logger.info(f"Received ping request with text: '{text}', accumulated_params: {accumulated_params}")

        # Show parameter information in response for demonstration
        param_info = ""
        if accumulated_params and len(accumulated_params) > 0:
            param_info = f" (received {len(accumulated_params)} accumulated params)"
        elif text.strip():
            param_info = f" (received immediate param: '{text}')"

        response = json.dumps({"data": f"pong{param_info}", "error": None})
        logger.info(f"Sending ping response: {response}")
        return response

    async def joke(self, text: str, accumulated_params: Optional[List[str]] = None) -> str:
        """
        Generates a funny anekdot (short joke) about the provided text using LLM.
        Uses OpenAI as primary model, falls back to Gemini if OpenAI is not available.
        Supports both immediate parameters and accumulated parameters.

        Args:
            text: The topic or text to create a joke about (immediate parameter)
            accumulated_params: List of accumulated messages (optional)

        Returns:
            JSON string with joke or error
        """
        logger.info(f"Received joke request with text: '{text}', accumulated_params: {accumulated_params}")

        # Determine the topic for the joke
        topic = None
        if accumulated_params and len(accumulated_params) > 0:
            # Use first accumulated parameter as topic
            topic = accumulated_params[0].strip()
            logger.info(f"Using accumulated parameter as joke topic: '{topic}'")
        elif text.strip():
            # Use immediate parameter as topic
            topic = text.strip()
            logger.info(f"Using immediate parameter as joke topic: '{topic}'")

        # Check input first
        if not topic:
            return json.dumps(
                {
                    "data": "",
                    "error": (
                        "Please provide some text to create a joke about. "
                        "Usage: /echo_joke <your topic> or send a message first then use /echo_joke"
                    ),
                }
            )

        # Check if any AI client is available
        if not self.openai_client and not self.gemini_client:
            return json.dumps(
                {"data": "", "error": "No AI model configured. Please set OPENAI_API_KEY or GEMINI_API_KEY."}
            )

        try:
            # Create a prompt for generating a short, funny anekdot
            prompt = f"""Create a short, funny anekdot (joke) about: {topic}

The anekdot should be:
- Short (1-3 sentences)
- Funny and witty
- Family-friendly
- In the style of a classic anekdot or dad joke
- Related to the topic: {topic}
- On the same language as a topic

Just return the joke, no additional text."""

            # Try OpenAI first (primary model)
            if self.openai_client:
                try:
                    logger.info(f"Generating joke using OpenAI for topic: {topic}")
                    joke_text = await self.openai_client.generate_content(prompt)
                    response = json.dumps({"data": joke_text, "error": None})
                    logger.info(f"Generated joke successfully using OpenAI for topic: {topic}")
                    return response
                except Exception as e:
                    logger.warning(f"OpenAI failed, trying Gemini fallback: {e}")

            # Fallback to Gemini if OpenAI failed or is not available
            if self.gemini_client:
                try:
                    logger.info(f"Generating joke using Gemini for topic: {topic}")
                    joke_text = await self.gemini_client.generate_content(prompt)
                    response = json.dumps({"data": joke_text, "error": None})
                    logger.info(f"Generated joke successfully using Gemini for topic: {topic}")
                    return response
                except Exception as e:
                    logger.error(f"Gemini also failed: {e}")
                    return json.dumps({"data": "", "error": f"Failed to generate joke with both models: {str(e)}"})

            # This shouldn't happen due to the check above, but just in case
            return json.dumps({"data": "", "error": "No working AI model available"})

        except Exception as e:
            logger.error(f"Unexpected error generating joke: {e}")
            return json.dumps({"data": "", "error": f"Failed to generate joke: {str(e)}"})
