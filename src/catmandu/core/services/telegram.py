import httpx
import structlog


class TelegramService:
    def __init__(self, token: str):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._api_url = f"https://api.telegram.org/bot{token}"
        self._client = httpx.AsyncClient(base_url=self._api_url, timeout=30.0)

    async def get_updates(self, offset: int | None = None) -> list[dict]:
        params = {"timeout": 10}
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

    async def send_message(self, chat_id: int, text: str):
        payload = {"chat_id": chat_id, "text": text}
        try:
            response = await self._client.post("/sendMessage", json=payload)
            response.raise_for_status()
            self.log.info("Message sent successfully", chat_id=chat_id)
        except httpx.HTTPError as e:
            self.log.error("Failed to send message to Telegram", error=e)

    async def close(self):
        if not self._client.is_closed:
            await self._client.aclose()
