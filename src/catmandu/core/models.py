from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StdioTransportConfig(BaseModel):
    type: Literal["stdio"] = "stdio"
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None


class WebSocketTransportConfig(BaseModel):
    type: Literal["websocket"] = "websocket"
    url: str
    headers: Optional[Dict[str, str]] = None


class HttpTransportConfig(BaseModel):
    type: Literal["http"] = "http"
    url: str
    headers: Optional[Dict[str, str]] = None


class McpConfig(BaseModel):
    transport: StdioTransportConfig | WebSocketTransportConfig | HttpTransportConfig = Field(discriminator="type")
    timeout: Optional[float] = 30.0
    max_retries: Optional[int] = 3


class CommandsConfig(BaseModel):
    description: str


class CattackleConfig(BaseModel):
    name: str
    version: str
    description: str
    commands: Dict[str, CommandsConfig]
    mcp: McpConfig


class CattackleRequest(BaseModel):
    command: str
    payload: Dict[str, Any]


class CattackleResponse(BaseModel):
    data: str
    error: Optional[str] = None


class AudioFileInfo(BaseModel):
    """Information about an audio file from Telegram."""

    file_id: str
    file_unique_id: str
    duration: Optional[int] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class TranscriptionResult(BaseModel):
    """Result of audio transcription processing."""

    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: float


class CostLogEntry(BaseModel):
    """Cost tracking entry for audio processing operations."""

    timestamp: datetime
    chat_id: int
    user_info: Dict[str, Any]
    audio_duration: float  # in minutes
    whisper_cost: float  # in USD
    gpt_tokens_input: int
    gpt_tokens_output: int
    gpt_cost: float  # in USD
    total_cost: float  # in USD
    file_size: int  # in bytes
    processing_time: float  # in seconds
