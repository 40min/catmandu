import structlog

from catmandu.core.errors import CattackleExecutionError
from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.services.accumulator_manager import AccumulatorManager
from catmandu.core.services.chat_logger import ChatLogger


class MessageRouter:
    def __init__(
        self,
        mcp_service: McpService,
        cattackle_registry: CattackleRegistry,
        accumulator_manager: AccumulatorManager,
        chat_logger: ChatLogger,
    ):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._mcp_service = mcp_service
        self._registry = cattackle_registry
        self._accumulator_manager = accumulator_manager
        self._chat_logger = chat_logger

    async def process_update(self, update: dict) -> tuple[int, str] | None:
        """Process a Telegram update, handling both command and non-command messages.

        Args:
            update: Telegram update dictionary

        Returns:
            Tuple of (chat_id, response_text) if a response should be sent, None otherwise
        """
        if "message" not in update or "text" not in update["message"]:
            self.log.warning("Update does not contain a message or text", update=update)
            return None

        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message["text"]
        user_info = message.get("from", {})

        if text.startswith("/"):
            return await self._process_command(chat_id, text, message)
        else:
            return await self._process_non_command_message(chat_id, text, user_info)

    async def _process_command(self, chat_id: int, text: str, message: dict) -> tuple[int, str]:
        """Process command message with accumulated parameters or handle system commands.

        Args:
            chat_id: Telegram chat ID
            text: Command text starting with /
            message: Full Telegram message object

        Returns:
            Tuple of (chat_id, response_text)
        """
        parts = text.split(" ", 1)
        full_command = parts[0][1:]  # Remove the '/' prefix
        payload_str = parts[1] if len(parts) > 1 else ""
        user_info = message.get("from", {})

        # Handle system commands first
        if full_command in ["clear_accumulator", "show_accumulator", "accumulator_status"]:
            response_text = await self._process_system_command(chat_id, full_command)

            # Log system command
            self._chat_logger.log_message(
                chat_id=chat_id,
                message_type="command",
                text=text,
                user_info=user_info,
                command=full_command,
                response_length=len(response_text[1]),
            )

            return response_text

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
            response_text = f"Command not found: {full_command}"

            # Log failed command
            self._chat_logger.log_message(
                chat_id=chat_id,
                message_type="command",
                text=text,
                user_info=user_info,
                command=full_command,
                cattackle_name=cattackle_name,
                response_length=len(response_text),
            )

            return chat_id, response_text

        try:
            # Extract accumulated parameters and clear accumulator
            accumulated_params = self._accumulator_manager.get_all_parameters_and_clear(chat_id)

            # Create simplified payload with accumulated parameters
            payload = {
                "text": payload_str,
                "accumulated_params": accumulated_params,
            }

            response = await self._mcp_service.execute_cattackle(
                cattackle_config=cattackle_config, command=command, payload=payload
            )

            response_text = str(response.data)

            # Log successful command
            self._chat_logger.log_message(
                chat_id=chat_id,
                message_type="command",
                text=text,
                user_info=user_info,
                command=command,
                cattackle_name=cattackle_name,
                response_length=len(response_text),
            )

            return chat_id, response_text
        except CattackleExecutionError as e:
            self.log.error("Cattackle execution failed", error=e)
            response_text = "An error occurred while executing the command."

            # Log failed command execution
            self._chat_logger.log_message(
                chat_id=chat_id,
                message_type="command",
                text=text,
                user_info=user_info,
                command=command,
                cattackle_name=cattackle_name,
                response_length=len(response_text),
            )

            return chat_id, response_text

    async def _process_non_command_message(self, chat_id: int, text: str, user_info: dict) -> tuple[int, str] | None:
        """Process non-command message for accumulation.

        Args:
            chat_id: Telegram chat ID
            text: Message text (not starting with /)
            user_info: User information from Telegram message

        Returns:
            Tuple of (chat_id, response_text) if feedback should be sent, None otherwise
        """
        self.log.debug("Processing non-command message for accumulation", chat_id=chat_id, text_length=len(text))

        # Log the non-command message
        self._chat_logger.log_message(chat_id=chat_id, message_type="message", text=text, user_info=user_info)

        feedback = self._accumulator_manager.process_non_command_message(chat_id, text)

        if feedback:
            return chat_id, feedback

        return None

    async def _process_system_command(self, chat_id: int, command: str) -> tuple[int, str]:
        """Process system commands for accumulator management.

        Args:
            chat_id: Telegram chat ID
            command: System command name (without /)

        Returns:
            Tuple of (chat_id, response_text)
        """
        self.log.info("Processing system command", command=command, chat_id=chat_id)

        if command == "clear_accumulator":
            response = self._accumulator_manager.clear_accumulator(chat_id)
        elif command == "show_accumulator":
            response = self._accumulator_manager.show_accumulated_messages(chat_id)
        elif command == "accumulator_status":
            response = self._accumulator_manager.get_accumulator_status(chat_id)
        else:
            response = f"Unknown system command: {command}"

        return chat_id, response
