import pytest
from httpx import ASGITransport, AsyncClient

from catmandu.main import create_app


@pytest.fixture
def app_test():
    """Get test app"""
    return create_app()


@pytest.fixture
async def async_client(app_test):  # Depends on clean_db for per-test cleanup
    """Get async test client"""
    async with AsyncClient(
        transport=ASGITransport(app=app_test), base_url="http://test"
    ) as client:
        yield client
