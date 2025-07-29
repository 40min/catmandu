import pytest
from httpx import AsyncClient

from catmandu.api.dependencies import get_cattackle_registry
from catmandu.core.config import Settings
from catmandu.core.infrastructure.registry import CattackleRegistry

pytestmark = pytest.mark.asyncio


@pytest.fixture
def test_registry_empty(fs, app_test):
    """Create a test registry with no cattackles and set up dependency override."""
    # Ensure no cattackles are present in the fake filesystem
    if fs.exists("/nonexistent"):
        fs.remove_object("/nonexistent")

    test_settings = Settings(cattackles_dir="/nonexistent")
    test_registry = CattackleRegistry(config=test_settings)
    test_registry.scan()

    def get_test_registry():
        return test_registry

    app_test.dependency_overrides[get_cattackle_registry] = get_test_registry

    yield test_registry

    # Cleanup
    if get_cattackle_registry in app_test.dependency_overrides:
        del app_test.dependency_overrides[get_cattackle_registry]


@pytest.fixture
def test_registry_with_cattackles(valid_cattackle_toml_file, app_test):
    """Create a test registry with cattackles present and set up dependency override."""
    test_settings = Settings(cattackles_dir="/cattackles")
    test_registry = CattackleRegistry(config=test_settings)
    test_registry.scan()

    def get_test_registry():
        return test_registry

    app_test.dependency_overrides[get_cattackle_registry] = get_test_registry

    yield test_registry

    # Cleanup
    if get_cattackle_registry in app_test.dependency_overrides:
        del app_test.dependency_overrides[get_cattackle_registry]


async def test_list_cattackles_no_cattackles(async_client: AsyncClient, test_registry_empty):
    """Tests the /nonexistent endpoint when no cattackles are present."""
    response = await async_client.get("/cattackles")
    assert response.status_code == 200
    assert response.json() == []


async def test_admin_reload_cattackles(async_client: AsyncClient, test_registry_with_cattackles):
    """Tests the POST /admin/reload endpoint."""
    response = await async_client.post("/admin/reload")
    assert response.status_code == 200
    assert response.json() == {"status": "reloaded", "found": 1}


async def test_list_cattackles_with_cattackles(async_client: AsyncClient, test_registry_with_cattackles):
    """Tests the /cattackles endpoint when cattackles are present."""
    response = await async_client.get("/cattackles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


# TODO: Uncomment when the async client supports calling tools
#
# async def test_call_tool_success(
#     async_client: AsyncClient,
#     test_registry_with_cattackles
# ):
#     """Tests calling a tool successfully."""
#     payload = {"message": "Hello, world!"}
#     response = await async_client.post("/call/echo", json=payload)
#     assert response.status_code == 200
#     assert response.json() == {"data": payload}

# TODO: Uncomment when the async client supports calling tools
#
# async def test_call_tool_not_found(
#     async_client: AsyncClient,
#     test_registry_with_cattackles
# ):
#     """Tests calling a non-existent tool."""
#     response = await async_client.post("/call/nonexistent", json={})
#     assert response.status_code == 404
#     assert response.json() == {"detail": "Tool not found"}

# TODO: Uncomment when the async client supports calling tools
#
# async def test_call_tool_validation_error(
#     async_client: AsyncClient,
#     test_registry_with_cattackles
# ):
#     """Tests calling a tool with invalid input."""
#     response = await async_client.post("/call/echo", json={"invalid_field": "value"})
#     assert response.status_code == 422
#     assert "Input validation error" in response.json()["detail"]
