from typing import Optional

from echo.clients.gemini_client import GeminiClient
from echo.config import EchoCattackleSettings
from echo.core.cattackle import EchoCattackle


def create_gemini_client(settings: EchoCattackleSettings) -> Optional[GeminiClient]:
    """
    Create a Gemini client if API key is available.

    Args:
        settings: Application settings

    Returns:
        GeminiClient instance or None if API key is not configured
    """
    if not settings.gemini_api_key:
        return None

    return GeminiClient(api_key=settings.gemini_api_key, model_name=settings.gemini_model)


def create_echo_cattackle(settings: EchoCattackleSettings) -> EchoCattackle:
    """
    Create an EchoCattackle instance with dependencies.

    Args:
        settings: Application settings

    Returns:
        Configured EchoCattackle instance
    """
    gemini_client = create_gemini_client(settings)
    return EchoCattackle(gemini_client=gemini_client)
