"""
Client layer for external API communication.

This package contains thin wrappers around external APIs and protocols.
Clients should be stateless or have minimal state and focus on transport concerns.
"""

from .mcp import McpClient
from .telegram import TelegramClient

__all__ = ["McpClient", "TelegramClient"]
