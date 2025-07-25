from typing import List, Optional

import structlog

from catmandu.core.services.accumulator import MessageAccumulator


class AccumulatorManager:
    """Business logic service for managing message accumulation.

    This service wraps MessageAccumulator and provides higher-level business
    logic for processing non-command messages, extracting parameters, and
    managing accumulator state.
    """

    def __init__(self, accumulator: MessageAccumulator, feedback_enabled: bool = True):
        """Initialize the accumulator manager.

        Args:
            accumulator: The MessageAccumulator instance to manage
            feedback_enabled: Whether to provide feedback for non-command messages
        """
        self._accumulator = accumulator
        self._feedback_enabled = feedback_enabled
        self.log = structlog.get_logger(self.__class__.__name__)

    def process_non_command_message(self, chat_id: int, text: str) -> Optional[str]:
        """Process non-command message and return optional feedback.

        Args:
            chat_id: The Telegram chat ID
            text: The message text to process

        Returns:
            Optional feedback message for the user, or None if feedback is disabled
        """
        # Get message count before adding
        count_before = self._accumulator.get_message_count(chat_id)

        # Add message to accumulator
        self._accumulator.add_message(chat_id, text)

        # Get message count after adding
        count_after = self._accumulator.get_message_count(chat_id)

        # Return feedback if enabled and message was actually added
        if self._feedback_enabled and count_after > count_before:
            if count_after == 1:
                return f"📝 Message stored. You now have {count_after} message ready for your next command."
            else:
                return f"📝 Message stored. You now have {count_after} messages ready for your next command."

        return None

    def get_all_parameters_and_clear(self, chat_id: int) -> List[str]:
        """Get all accumulated parameters and clear the accumulator atomically.

        This method is used when a command is executed to extract all
        accumulated messages as parameters and clear the accumulator.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            List of accumulated messages in order they were added
        """
        parameters = self._accumulator.get_all_and_clear(chat_id)

        self.log.info("Extracted parameters for command execution", chat_id=chat_id, parameter_count=len(parameters))

        return parameters

    def get_accumulator_status(self, chat_id: int) -> str:
        """Get human-readable status of accumulator for a chat.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            Human-readable status message
        """
        message_count = self._accumulator.get_message_count(chat_id)

        if message_count == 0:
            return "📭 No messages accumulated. Send some messages and then use a command!"
        elif message_count == 1:
            return "📝 You have 1 message accumulated and ready for your next command."
        else:
            return f"📝 You have {message_count} messages accumulated and ready for your next command."

    def show_accumulated_messages(self, chat_id: int) -> str:
        """Show current accumulated messages for a chat.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            Human-readable display of accumulated messages
        """
        messages = self._accumulator.get_messages(chat_id)

        if not messages:
            return "📭 No messages accumulated."

        # Build response with numbered messages
        response_lines = [f"📝 Your accumulated messages ({len(messages)} total):"]

        for i, message in enumerate(messages, 1):
            # Note: MessageAccumulator already truncates messages to max_message_length
            # We add additional truncation for display purposes if needed
            display_message = message[:100] + "..." if len(message) > 100 else message
            response_lines.append(f"{i}. {display_message}")

        return "\n".join(response_lines)

    def clear_accumulator(self, chat_id: int) -> str:
        """Clear accumulator and return confirmation message.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            Confirmation message about the clearing operation
        """
        message_count = self._accumulator.get_message_count(chat_id)

        if message_count == 0:
            return "📭 No messages to clear - your accumulator is already empty."

        self._accumulator.clear_chat(chat_id)

        self.log.info("Manually cleared accumulator", chat_id=chat_id, cleared_count=message_count)

        if message_count == 1:
            return "🗑️ Cleared 1 accumulated message."
        else:
            return f"🗑️ Cleared {message_count} accumulated messages."

    def get_global_status(self) -> str:
        """Get global accumulator status across all chats.

        Returns:
            Human-readable global status message
        """
        total_chats = self._accumulator.get_total_chats()

        if total_chats == 0:
            return "📊 Global Status: No active chat accumulators."

        chat_ids = self._accumulator.get_all_chat_ids()
        total_messages = sum(self._accumulator.get_message_count(chat_id) for chat_id in chat_ids)

        return f"📊 Global Status: {total_chats} active chat(s) " f"with {total_messages} total accumulated message(s)."
