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
