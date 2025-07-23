import asyncio
import pathlib

import structlog

from catmandu.core.clients import TelegramClient
from catmandu.core.config import Settings
from catmandu.core.services.router import MessageRouter


class TelegramPoller:
    def __init__(
        self,
        router: MessageRouter,
        telegram_client: TelegramClient,
        settings: Settings,
    ):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._router = router
        self._telegram = telegram_client
        self._offset_file = pathlib.Path(settings.update_id_file_path)
        self._offset: int | None = None
        self._should_stop = asyncio.Event()

    def _load_offset(self):
        try:
            if self._offset_file.exists():
                self._offset = int(self._offset_file.read_text().strip())
                self.log.info("Loaded update_id offset", offset=self._offset)
        except (IOError, ValueError) as e:
            self.log.error("Failed to load offset, starting from scratch", error=e)
            self._offset = None

    def _save_offset(self, offset: int):
        try:
            self._offset_file.parent.mkdir(parents=True, exist_ok=True)
            self._offset_file.write_text(str(offset))
        except IOError as e:
            self.log.error("Failed to save offset", offset=offset, error=e)

    async def _run_single_loop(self):
        updates = await self._telegram.get_updates(offset=self._offset)
        for update in updates:
            update_id = update["update_id"]
            self.log.debug("Processing update", update_id=update_id)
            response = await self._router.process_update(update)
            if response:
                chat_id, text = response
                await self._telegram.send_message(chat_id, text)

            self._offset = update_id + 1

        if updates and self._offset:
            self._save_offset(self._offset)

    async def run(self):
        self._load_offset()
        self.log.info("Telegram poller started")
        while not self._should_stop.is_set():
            await self._run_single_loop()
        self.log.info("Telegram poller stopped")

    async def stop(self):
        self.log.info("Stopping telegram poller...")
        self._should_stop.set()
