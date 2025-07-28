from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cattackles_dir: str = "cattackles"
    telegram_bot_token: str
    update_id_file_path: str = ".data/update_id.txt"

    # Chat logging configuration
    chat_logs_dir: str = "logs/chats"

    # Message accumulator configuration
    max_messages_per_chat: int = 100
    max_message_length: int = 1000
