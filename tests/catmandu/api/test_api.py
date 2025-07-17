import pytest
from httpx import AsyncClient

VALID_CATTACKLE_TOML = """
[cattackle]
name = "echo"
version = "0.1.0"
description = "A simple echo cattackle."
[cattackle.commands]
echo = { description = "Echoes back the payload." }
[cattackle.mcp]
transport = "stdio"
"""


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Tests the /health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_cattackles_with_cattackles(client: AsyncClient, fs):
    """Tests the /cattackles endpoint when cattackles are present."""
    fs.create_file("cattackles/echo/cattackle.toml", contents=VALID_CATTACKLE_TOML)
    response = await client.get("/cattackles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cattackle"]["name"] == "echo"


@pytest.mark.asyncio
async def test_list_cattackles_with_no_cattackles_dir(client: AsyncClient, fs):
    """Tests the /cattackles endpoint when the directory is missing."""
    response = await client.get("/cattackles")
    assert response.status_code == 200
    assert response.json() == []
