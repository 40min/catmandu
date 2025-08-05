"""Health check handler for the Notion cattackle."""

from starlette.requests import Request
from starlette.responses import JSONResponse


async def handle_health_check(request: Request) -> JSONResponse:
    """
    Handle health check requests.

    Args:
        request: The incoming HTTP request

    Returns:
        JSON response indicating server health
    """
    return JSONResponse(
        {
            "status": "healthy",
            "service": "notion-cattackle",
            "version": "1.0.0",
        }
    )
