from typing import Dict, List

import structlog


class MessageAccumulator:
    """In-memory message accumulator for chat-specific message storage.

    This service stores non-command messages from users on a per-chat basis,
    allowing them to be used as parameters when commands are executed.
    """

    def __init__(self, max_messages_per_chat: int = 100, max_message_length: int = 1000):
        """Initialize the message accumulator.

        Args:
            max_messages_per_chat: Maximum number of messages to store per chat
            max_message_length: Maximum length of individual messages to store
        """
        self._messages: Dict[int, List[str]] = {}
        self._max_messages = max_messages_per_chat
        self._max_message_length = max_message_length
        self.log = structlog.get_logger(self.__class__.__name__)

    def add_message(self, chat_id: int, message: str) -> None:
        """Add a message to the accumulator for a specific chat.

        Args:
            chat_id: The Telegram chat ID
            message: The message text to store
        """
        # Skip empty or whitespace-only messages
        if not message or not message.strip():
            self.log.debug("Skipping empty message", chat_id=chat_id)
            return

        # Truncate message if it exceeds maximum length
        if self._max_message_length > 0 and len(message) > self._max_message_length:
            message = message[: self._max_message_length]
            self.log.debug("Truncated message to max length", chat_id=chat_id, max_length=self._max_message_length)
        elif self._max_message_length == 0:
            # If max length is 0, skip the message entirely
            self.log.debug("Skipping message due to zero max length", chat_id=chat_id)
            return

        # Initialize chat messages list if it doesn't exist
        if chat_id not in self._messages:
            self._messages[chat_id] = []

        # Add the message
        self._messages[chat_id].append(message)

        # Enforce message count limits
        self._enforce_limits(chat_id)

        self.log.debug(
            "Message added to accumulator",
            chat_id=chat_id,
            message_count=len(self._messages[chat_id]),
            message_preview=message[:50] + "..." if len(message) > 50 else message,
        )

    def get_messages(self, chat_id: int) -> List[str]:
        """Get all accumulated messages for a chat.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            List of accumulated messages in order they were added
        """
        return self._messages.get(chat_id, []).copy()

    def get_all_and_clear(self, chat_id: int) -> List[str]:
        """Get all accumulated messages and clear the accumulator for a chat.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            List of accumulated messages in order they were added
        """
        messages = self._messages.get(chat_id, []).copy()
        self.clear_chat(chat_id)

        self.log.debug("Retrieved and cleared messages", chat_id=chat_id, message_count=len(messages))

        return messages

    def clear_chat(self, chat_id: int) -> None:
        """Clear all messages for a specific chat.

        Args:
            chat_id: The Telegram chat ID
        """
        if chat_id in self._messages:
            message_count = len(self._messages[chat_id])
            del self._messages[chat_id]
            self.log.debug("Cleared chat messages", chat_id=chat_id, cleared_count=message_count)

    def get_message_count(self, chat_id: int) -> int:
        """Get count of accumulated messages for a chat.

        Args:
            chat_id: The Telegram chat ID

        Returns:
            Number of accumulated messages
        """
        return len(self._messages.get(chat_id, []))

    def get_total_chats(self) -> int:
        """Get total number of chats with accumulated messages.

        Returns:
            Number of chats with messages
        """
        return len(self._messages)

    def get_all_chat_ids(self) -> List[int]:
        """Get all chat IDs that have accumulated messages.

        Returns:
            List of chat IDs
        """
        return list(self._messages.keys())

    def _enforce_limits(self, chat_id: int) -> None:
        """Enforce memory limits by removing oldest messages if needed.

        Args:
            chat_id: The Telegram chat ID
        """
        if chat_id in self._messages:
            messages = self._messages[chat_id]
            if len(messages) > self._max_messages:
                # Keep only the most recent messages
                removed_count = len(messages) - self._max_messages
                self._messages[chat_id] = messages[-self._max_messages :]
                self.log.debug(
                    "Enforced message limit",
                    chat_id=chat_id,
                    removed_count=removed_count,
                    remaining_count=len(self._messages[chat_id]),
                )
