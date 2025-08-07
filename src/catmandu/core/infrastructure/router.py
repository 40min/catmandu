import structlog

from catmandu.core.audio_processor import AudioProcessingError, AudioProcessor
from catmandu.core.errors import CattackleExecutionError
from catmandu.core.infrastructure.chat_logger import ChatLogger
from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.services.accumulator_manager import AccumulatorManager
from catmandu.core.services.logging_service import LoggingService


class MessageRouter:
    def __init__(
        self,
        mcp_service: McpService,
        cattackle_registry: CattackleRegistry,
        accumulator_manager: AccumulatorManager,
        chat_logger: ChatLogger,
        logging_service: LoggingService,
        audio_processor: AudioProcessor = None,
    ):
        self.log = structlog.get_logger(self.__class__.__name__)
        self._mcp_service = mcp_service
        self._registry = cattackle_registry
        self._accumulator_manager = accumulator_manager
        self._chat_logger = chat_logger
        self._logging_service = logging_service
        self._audio_processor = audio_processor

    async def process_update(self, update: dict) -> tuple[int, str] | None:
        """Process a Telegram update, handling text, command, and audio messages.

        Args:
            update: Telegram update dictionary

        Returns:
            Tuple of (chat_id, response_text) if a response should be sent, None otherwise
        """
        if "message" not in update:
            self.log.warning("Update does not contain a message", update=update)
            return None

        message = update["message"]
        chat_id = message["chat"]["id"]

        # Handle audio messages (voice, audio, video_note)
        if any(key in message for key in ["voice", "audio", "video_note"]):
            return await self._process_audio_message(chat_id, message)

        # Handle text messages
        if "text" not in message:
            self.log.warning("Update does not contain text or audio", update=update)
            return None

        text = message["text"]
        user_info = message.get("from", {})

        if text.startswith("/"):
            return await self._process_command(chat_id, text, user_info)
        else:
            return await self._process_non_command_message(chat_id, text, user_info)

    async def _process_command(self, chat_id: int, text: str, user_info: dict) -> tuple[int, str]:
        """Process command message with accumulated parameters or handle system commands.

        Args:
            chat_id: Telegram chat ID
            text: Command text starting with /
            user_info: User information from Telegram message

        Returns:
            Tuple of (chat_id, response_text)
        """
        parts = text.split(" ", 1)
        full_command = parts[0][1:]  # Remove the '/' prefix
        payload_str = parts[1] if len(parts) > 1 else ""

        # Handle system commands first
        if full_command in ["clear_accumulator", "show_accumulator", "accumulator_status"]:
            response_text = await self._process_system_command(chat_id, full_command)

            # Log system command safely
            self._logging_service.log_chat_interaction_safely(
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

            # Log failed command safely
            self._logging_service.log_chat_interaction_safely(
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

            # Create simplified payload with accumulated parameters and user info
            payload = {
                "text": payload_str,
                "accumulated_params": accumulated_params,
                "username": user_info.get("username", ""),
            }

            response = await self._mcp_service.execute_cattackle(
                cattackle_config=cattackle_config, command=command, payload=payload
            )

            response_text = str(response.data)

            # Log successful command safely
            self._logging_service.log_chat_interaction_safely(
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

            # Log failed command execution safely
            self._logging_service.log_chat_interaction_safely(
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

        # Log the non-command message safely
        self._logging_service.log_chat_interaction_safely(
            chat_id=chat_id, message_type="message", text=text, user_info=user_info
        )

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

    async def _process_audio_message(self, chat_id: int, message: dict) -> tuple[int, str]:
        """Process audio message and convert to text for routing.

        Args:
            chat_id: Telegram chat ID
            message: Telegram message containing audio data

        Returns:
            Tuple of (chat_id, response_text)
        """
        user_info = message.get("from", {})

        # Check if audio processing is available
        if not self._audio_processor:
            self.log.warning("Audio message received but audio processor not available", chat_id=chat_id)
            response_text = "Sorry, audio processing is not available at the moment."

            # Extract basic audio metadata even when processing is unavailable
            audio_metadata = {}
            for audio_type in ["voice", "audio", "video_note"]:
                if audio_type in message:
                    audio_data = message[audio_type]
                    audio_metadata = {
                        "message_type": audio_type,
                        "file_id": audio_data.get("file_id"),
                        "duration": audio_data.get("duration"),
                        "file_size": audio_data.get("file_size"),
                        "mime_type": audio_data.get("mime_type"),
                        "processing_status": "unavailable",
                    }
                    break

            # Log the audio message attempt safely
            self._logging_service.log_chat_interaction_safely(
                chat_id=chat_id,
                message_type="audio",
                text="[Audio message - processing unavailable]",
                user_info=user_info,
                response_length=len(response_text),
                audio_metadata=audio_metadata,
            )

            return chat_id, response_text

        try:
            self.log.info("Processing audio message", chat_id=chat_id)

            # Send typing indicator to show processing is in progress
            await self._audio_processor.telegram_client.send_chat_action(chat_id, "typing")

            # Process the audio message to get transcribed text
            update = {"message": message}
            transcribed_text = await self._audio_processor.process_audio_message(update)

            if not transcribed_text:
                response_text = "Sorry, I couldn't process the audio message. Please try again or send a text message."

                # Extract audio metadata for failed processing
                audio_metadata = {}
                for audio_type in ["voice", "audio", "video_note"]:
                    if audio_type in message:
                        audio_data = message[audio_type]
                        audio_metadata = {
                            "message_type": audio_type,
                            "file_id": audio_data.get("file_id"),
                            "duration": audio_data.get("duration"),
                            "file_size": audio_data.get("file_size"),
                            "mime_type": audio_data.get("mime_type"),
                            "processing_status": "failed",
                        }
                        break

                # Log failed audio processing safely
                self._logging_service.log_chat_interaction_safely(
                    chat_id=chat_id,
                    message_type="audio",
                    text="[Audio message - processing failed]",
                    user_info=user_info,
                    response_length=len(response_text),
                    audio_metadata=audio_metadata,
                )

                return chat_id, response_text

            self.log.info("Audio transcription successful", chat_id=chat_id, text_length=len(transcribed_text))

            # Process the transcribed text as if it were a regular text message
            if transcribed_text.startswith("/"):
                return await self._process_command(chat_id, transcribed_text, user_info)
            else:
                # Process as non-command message for accumulation
                result = await self._process_non_command_message(chat_id, transcribed_text, user_info)

                # If no feedback from accumulator, provide confirmation
                if result is None:
                    response_text = f'I heard: "{transcribed_text}"'

                    # Extract audio metadata for logging
                    audio_metadata = {}
                    for audio_type in ["voice", "audio", "video_note"]:
                        if audio_type in message:
                            audio_data = message[audio_type]
                            audio_metadata = {
                                "message_type": audio_type,
                                "file_id": audio_data.get("file_id"),
                                "duration": audio_data.get("duration"),
                                "file_size": audio_data.get("file_size"),
                                "mime_type": audio_data.get("mime_type"),
                                "transcribed_text_length": len(transcribed_text),
                                "transcribed_word_count": len(transcribed_text.split()),
                            }
                            break

                    # Log the successful audio processing safely
                    self._logging_service.log_chat_interaction_safely(
                        chat_id=chat_id,
                        message_type="audio",
                        text=f"[Audio transcribed]: {transcribed_text}",
                        user_info=user_info,
                        response_length=len(response_text),
                        audio_metadata=audio_metadata,
                    )

                    return chat_id, response_text

                return result

        except AudioProcessingError as e:
            # Log audio processing error
            self.log.error("Audio processing failed", chat_id=chat_id, error=str(e), error_type=type(e).__name__)

            # Provide user-friendly error messages based on error type
            error_message = str(e)
            if "too large" in error_message.lower():
                response_text = "Sorry, the audio file is too large. Please send files smaller than the allowed limit."
            elif "too long" in error_message.lower():
                response_text = "Sorry, the audio file is too long. Please send shorter audio messages."
            elif "unsupported" in error_message.lower():
                response_text = (
                    "Sorry, I can't process this audio format. Please send voice messages or common audio files."
                )
            elif "disabled" in error_message.lower():
                response_text = "Sorry, audio processing is currently disabled."
            elif "api key" in error_message.lower():
                response_text = "Sorry, audio processing is not properly configured. Please contact the administrator."
            else:
                response_text = (
                    "Sorry, I couldn't process the audio message. Please try again later or send a text message."
                )

            # Log audio processing error safely
            self._logging_service.log_chat_interaction_safely(
                chat_id=chat_id,
                message_type="audio",
                text=f"[Audio processing error - {type(e).__name__}]: {error_message}",
                user_info=user_info,
                response_length=len(response_text),
            )

            return chat_id, response_text

        except Exception as e:
            # Log unexpected error
            self.log.error(
                "Unexpected error processing audio message", chat_id=chat_id, error=str(e), error_type=type(e).__name__
            )
            response_text = "Sorry, an unexpected error occurred while processing your audio message. Please try again."

            # Log unexpected audio processing error safely
            self._logging_service.log_chat_interaction_safely(
                chat_id=chat_id,
                message_type="audio",
                text=f"[Audio processing unexpected error - {type(e).__name__}]: {str(e)}",
                user_info=user_info,
                response_length=len(response_text),
            )

            return chat_id, response_text
