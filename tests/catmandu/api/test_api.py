import pytest
from httpx import AsyncClient

VALID_CATTACKLE_TOML = """
[cattackle]
name = "echo"
version = "0.1.0"
description = "A simple cattackle that echoes back the payload."

[cattackle.commands]
echo = { description = "Echoes back the given payload." }

[cattackle.mcp]
transport = "stdio"
"""

pytestmark = pytest.mark.asyncio


async def test_list_cattackles_no_cattackles(async_client: AsyncClient):
    """Tests the /cattackles endpoint when no cattackles are present."""
    response = await async_client.get("/cattackles")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_cattackles_with_cattackles(async_client: AsyncClient):
    """Tests the /cattackles endpoint when cattackles are present."""
    response = await async_client.get("/cattackles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


async def test_call_tool_success(async_client: AsyncClient):
    """Tests calling a tool successfully."""
    payload = {"message": "Hello, world!"}
    response = await async_client.post("/call/echo", json=payload)
    assert response.status_code == 200
    assert response.json() == {"data": payload}


async def test_call_tool_not_found(async_client: AsyncClient):
    """Tests calling a non-existent tool."""
    response = await async_client.post("/call/nonexistent", json={})
    assert response.status_code == 404
    assert response.json() == {"detail": "Tool not found"}


async def test_call_tool_validation_error(async_client: AsyncClient):
    """Tests calling a tool with invalid input."""
    response = await async_client.post("/call/echo", json={"invalid_field": "value"})
    assert response.status_code == 422
    assert "Input validation error" in response.json()["detail"]
