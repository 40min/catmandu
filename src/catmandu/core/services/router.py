import structlog

from catmandu.core.errors import CattackleExecutionError
from catmandu.core.services.mcp_client import McpClientManager
from catmandu.core.services.registry import CattackleRegistry


class MessageRouter:
    def __init__(
        self,
        mcp_client_manager: McpClientManager,
        cattackle_registry: CattackleRegistry,
    ):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._mcp_client = mcp_client_manager
        self._registry = cattackle_registry

    async def process_update(self, update: dict) -> tuple[int, str] | None:
        if "message" not in update or "text" not in update["message"]:
            self.log.warning("Update does not contain a message or text", update=update)
            return None

        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message["text"]

        if not text.startswith("/"):
            return None

        parts = text.split(" ", 1)
        command = parts[0][1:]
        payload_str = parts[1] if len(parts) > 1 else ""

        self.log.info("Processing command", command=command, chat_id=chat_id)

        cattackle_config = self._registry.find_by_command(command)
        if not cattackle_config:
            self.log.warning("Command not found", command=command)
            return chat_id, f"Command not found: {command}"

        try:
            payload = {"text": payload_str, "message": message}
            response = await self._mcp_client.call(cattackle_config=cattackle_config, command=command, payload=payload)
            return chat_id, str(response.data)
        except CattackleExecutionError as e:
            self.log.error("Cattackle execution failed", error=e)
            return chat_id, "An error occurred while executing the command."
