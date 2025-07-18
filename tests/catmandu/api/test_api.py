import pytest
from httpx import AsyncClient

from catmandu.api.dependencies import get_cattackle_registry
from catmandu.core.config import Settings
from catmandu.core.services.registry import CattackleRegistry

pytestmark = pytest.mark.asyncio


async def test_list_cattackles_no_cattackles(async_client: AsyncClient, app_test, fs):
    """Tests the /nonexistent endpoint when no cattackles are present."""
    # Ensure no cattackles are present in the fake filesystem
    if fs.exists("/nonexistent"):
        fs.remove_object("/nonexistent")

    test_settings = Settings(cattackles_dir="/nonexistent")
    test_registry = CattackleRegistry(config=test_settings)
    test_registry.scan()

    def get_test_registry():
        return test_registry

    app_test.dependency_overrides[get_cattackle_registry] = get_test_registry
    response = await async_client.get("/cattackles")
    assert response.status_code == 200
    assert response.json() == []
    del app_test.dependency_overrides[get_cattackle_registry]


async def test_list_cattackles_with_cattackles(
    async_client: AsyncClient, app_test, valid_cattackle_toml_file
):
    """Tests the /cattackles endpoint when cattackles are present."""
    test_settings = Settings(cattackles_dir="/cattackles")
    test_registry = CattackleRegistry(config=test_settings)
    test_registry.scan()

    def get_test_registry():
        return test_registry

    app_test.dependency_overrides[get_cattackle_registry] = get_test_registry
    response = await async_client.get("/cattackles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    del app_test.dependency_overrides[get_cattackle_registry]


# TODO: Uncomment when the async client supports calling tools
#
# async def test_call_tool_success(
#     async_client: AsyncClient, app_test, valid_cattackle_toml_file
# ):
#     """Tests calling a tool successfully."""
#     test_settings = Settings(cattackles_dir="/cattackles")
#     test_registry = CattackleRegistry(config=test_settings)
#     test_registry.scan()

#     def get_test_registry():
#         return test_registry

#     app_test.dependency_overrides[get_cattackle_registry] = get_test_registry
#     payload = {"message": "Hello, world!"}
#     response = await async_client.post("/call/echo", json=payload)
#     assert response.status_code == 200
#     assert response.json() == {"data": payload}
#     del app_test.dependency_overrides[get_cattackle_registry]

# TODO: Uncomment when the async client supports calling tools
#
# async def test_call_tool_not_found(
#     async_client: AsyncClient, app_test, valid_cattackle_toml_file
# ):
#     """Tests calling a non-existent tool."""
#     test_settings = Settings(cattackles_dir="/cattackles")
#     test_registry = CattackleRegistry(config=test_settings)
#     test_registry.scan()

#     def get_test_registry():
#         return test_registry

#     app_test.dependency_overrides[get_cattackle_registry] = get_test_registry
#     response = await async_client.post("/call/nonexistent", json={})
#     assert response.status_code == 404
#     assert response.json() == {"detail": "Tool not found"}
#     del app_test.dependency_overrides[get_cattackle_registry]


# TODO: Uncomment when the async client supports calling tools
#
# async def test_call_tool_validation_error(
#     async_client: AsyncClient, app_test, valid_cattackle_toml_file
# ):
#     """Tests calling a tool with invalid input."""
#     test_settings = Settings(cattackles_dir="/cattackles")
#     test_registry = CattackleRegistry(config=test_settings)
#     test_registry.scan()

#     def get_test_registry():
#         return test_registry

#     app_test.dependency_overrides[get_cattackle_registry] = get_test_registry
#     response = await async_client.post("/call/echo", json={"invalid_field": "value"})
#     assert response.status_code == 422
#     assert "Input validation error" in response.json()["detail"]
#     del app_test.dependency_overrides[get_cattackle_registry]
