import time

from starlette.requests import Request
from starlette.responses import JSONResponse


async def handle_health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Docker health checks."""
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "echo-cattackle",
        "mcp_server": "running",
    }

    return JSONResponse(health_data)
