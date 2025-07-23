import structlog

from catmandu.core.errors import CattackleExecutionError
from catmandu.core.services.mcp_service import McpService
from catmandu.core.services.registry import CattackleRegistry


class MessageRouter:
    def __init__(
        self,
        mcp_service: McpService,
        cattackle_registry: CattackleRegistry,
    ):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._mcp_service = mcp_service
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
        full_command = parts[0][1:]  # Remove the '/' prefix
        payload_str = parts[1] if len(parts) > 1 else ""

        # Parse cattackle_command format
        if "_" in full_command:
            cattackle_name, command = full_command.split("_", 1)
        else:
            # Fallback to old behavior for backward compatibility
            cattackle_name = None
            command = full_command

        self.log.info(
            "Processing command",
            full_command=full_command,
            cattackle_name=cattackle_name,
            command=command,
            chat_id=chat_id,
        )

        # Use the new method to find by cattackle and command
        if cattackle_name:
            cattackle_config = self._registry.find_by_cattackle_and_command(cattackle_name, command)
        else:
            # Fallback to find by command only
            cattackle_config = self._registry.find_by_command(command)

        if not cattackle_config:
            self.log.warning(
                "Command not found", full_command=full_command, cattackle_name=cattackle_name, command=command
            )
            return chat_id, f"Command not found: {full_command}"

        try:
            payload = {"text": payload_str, "message": message}
            response = await self._mcp_service.execute_cattackle(
                cattackle_config=cattackle_config, command=command, payload=payload
            )

            return chat_id, str(response.data)
        except CattackleExecutionError as e:
            self.log.error("Cattackle execution failed", error=e)
            return chat_id, "An error occurred while executing the command."
