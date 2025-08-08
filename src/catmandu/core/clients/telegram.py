"""
Telegram Bot API client.

Provides a thin wrapper around the Telegram Bot HTTP API.
Focuses on transport and protocol concerns only.
"""

from typing import Any, Dict, Optional

import httpx
import structlog


class TelegramClient:
    """
    HTTP client for Telegram Bot API.

    This is a stateless wrapper around the Telegram Bot API that handles
    HTTP communication and basic error handling. Business logic should
    be implemented in services that use this client.
    """

    def __init__(self, token: str):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._api_url = f"https://api.telegram.org/bot{token}"
        self._client = httpx.AsyncClient(base_url=self._api_url, timeout=30.0)

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 10) -> list[dict]:
        """
        Get updates from Telegram Bot API.

        Args:
            offset: Identifier of the first update to be returned
            timeout: Timeout in seconds for long polling

        Returns:
            List of update objects from Telegram API
        """
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset

        try:
            response = await self._client.get("/getUpdates", params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                return data["result"]

            self.log.error("Telegram API error", response=data)
            return []

        except httpx.HTTPError as e:
            self.log.error("Failed to get updates from Telegram", error=e)
            return []

    async def send_message(self, chat_id: int, text: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Send a message via Telegram Bot API.

        Args:
            chat_id: Unique identifier for the target chat
            text: Text of the message to be sent
            **kwargs: Additional parameters for sendMessage API

        Returns:
            Message object from Telegram API if successful, None otherwise
        """
        payload = {"chat_id": chat_id, "text": text, **kwargs}

        try:
            response = await self._client.post("/sendMessage", json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                self.log.debug("Message sent successfully", chat_id=chat_id)
                return data["result"]

            self.log.error("Telegram API error sending message", response=data)
            return None

        except httpx.HTTPError as e:
            self.log.error("Failed to send message to Telegram", error=e, chat_id=chat_id, message=text)
            return None

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from Telegram API.

        Args:
            file_id: Unique identifier for the file

        Returns:
            File object from Telegram API if successful, None otherwise
        """
        payload = {"file_id": file_id}

        try:
            response = await self._client.post("/getFile", json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                self.log.debug("File info retrieved successfully", file_id=file_id)
                return data["result"]

            self.log.error("Telegram API error getting file info", response=data, file_id=file_id)
            return None

        except httpx.HTTPError as e:
            self.log.error("Failed to get file info from Telegram", error=e, file_id=file_id)
            return None

    async def download_file(self, file_path: str) -> Optional[bytes]:
        """Download file content from Telegram servers.

        Args:
            file_path: File path returned by getFile API

        Returns:
            File content as bytes if successful, None otherwise
        """
        # Telegram file download URL uses a different base URL
        download_url = f"https://api.telegram.org/file/bot{self._api_url.split('bot')[1]}/{file_path}"

        try:
            response = await self._client.get(download_url)
            response.raise_for_status()

            self.log.debug("File downloaded successfully", file_path=file_path, size=len(response.content))
            return response.content

        except httpx.HTTPError as e:
            self.log.error("Failed to download file from Telegram", error=e, file_path=file_path)
            return None

    async def send_chat_action(self, chat_id: int, action: str) -> bool:
        """Send chat action (typing, upload_voice, etc.).

        Args:
            chat_id: Unique identifier for the target chat
            action: Type of action to broadcast

        Returns:
            True if successful, False otherwise
        """
        payload = {"chat_id": chat_id, "action": action}

        try:
            response = await self._client.post("/sendChatAction", json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                self.log.debug("Chat action sent successfully", chat_id=chat_id, action=action)
                return True

            self.log.error("Telegram API error sending chat action", response=data, chat_id=chat_id, action=action)
            return False

        except httpx.HTTPError as e:
            self.log.error("Failed to send chat action to Telegram", error=e, chat_id=chat_id, action=action)
            return False

    async def close(self):
        """Close the HTTP client connection."""
        if not self._client.is_closed:
            await self._client.aclose()
