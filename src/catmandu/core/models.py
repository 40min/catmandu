from typing import Any, Dict, Literal

from pydantic import BaseModel


class McpConfig(BaseModel):
    transport: Literal["stdio", "websocket", "http"]


class CommandsConfig(BaseModel):
    description: str


class CattackleDetails(BaseModel):
    name: str
    version: str
    description: str
    commands: Dict[str, CommandsConfig]
    mcp: McpConfig


class CattackleConfig(BaseModel):
    cattackle: CattackleDetails


class CattackleRequest(BaseModel):
    command: str
    payload: Dict[str, Any]


class CattackleResponse(BaseModel):
    data: Dict[str, Any]
    error: str | None = None
