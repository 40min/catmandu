import json
import time

from starlette.types import Receive, Scope, Send


async def handle_health_check(scope: Scope, receive: Receive, send: Send) -> None:
    """Health check endpoint for Docker health checks."""
    if scope["type"] == "http" and scope["method"] == "GET":
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "echo-cattackle",
            "mcp_server": "running",
        }

        response_body = json.dumps(health_data).encode()

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(response_body)).encode()],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response_body,
            }
        )
    else:
        # Method not allowed
        await send(
            {
                "type": "http.response.start",
                "status": 405,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"Method Not Allowed",
            }
        )
