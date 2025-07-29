"""
Tests for the HTTP transport functionality of the echo cattackle.
These tests verify that the HTTP MCP server works correctly.
"""

import json
import subprocess
import time
from typing import Any, Dict

import pytest
import requests


class TestHttpTransport:
    """Test class for HTTP transport functionality."""

    @pytest.fixture(scope="class")
    def http_server(self):
        """Start the HTTP MCP server for testing (shared across all tests)."""
        import os

        # Determine the correct working directory and script path
        current_dir = os.getcwd()
        if current_dir.endswith("cattackles/echo"):
            # Running from cattackles/echo directory
            script_path = "src/server.py"
            cwd = None
        else:
            # Running from root directory
            script_path = "cattackles/echo/src/server.py"
            cwd = None

        proc = subprocess.Popen(
            ["python", script_path, "--port", "8001", "--log-level", "ERROR"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )

        try:
            # Wait for server to be ready with health check
            self._wait_for_server_ready("http://127.0.0.1:8001")
            yield proc
        except Exception as e:
            # If server startup fails, capture output for debugging
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=5)
            error_msg = f"Server startup failed: {e}"
            if stderr:
                error_msg += f"\nStderr: {stderr.decode()}"
            if stdout:
                error_msg += f"\nStdout: {stdout.decode()}"
            raise RuntimeError(error_msg)
        finally:
            # Cleanup
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)

    def _wait_for_server_ready(self, base_url: str, timeout: int = 10) -> None:
        """Wait for server to be ready with exponential backoff."""
        start_time = time.time()
        delay = 0.05  # Start with shorter delay

        while time.time() - start_time < timeout:
            try:
                response = requests.post(
                    f"{base_url}/mcp",
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                    timeout=2,  # Slightly longer timeout for individual requests
                )
                if response.status_code == 200:
                    return
            except requests.exceptions.RequestException:
                pass

            time.sleep(delay)
            delay = min(delay * 1.4, 0.3)  # Exponential backoff, max 0.3s

        raise TimeoutError(f"Server at {base_url} did not become ready within {timeout}s")

    def _make_mcp_request(self, method: str, params: Dict[Any, Any] = None, request_id: int = 1) -> Dict[Any, Any]:
        """Helper to make MCP requests and parse SSE responses."""
        response = requests.post(
            "http://127.0.0.1:8001/mcp",
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200

        # Parse SSE response efficiently
        data_line = next((line for line in response.text.split("\n") if line.startswith("data: ")), None)
        assert data_line is not None, "No data line found in SSE response"

        return json.loads(data_line[6:])  # Remove 'data: ' prefix

    def test_http_server_starts(self, http_server):
        """Test that the HTTP server starts successfully."""
        # Check if process is still running
        assert http_server.poll() is None, "HTTP server should be running"

    def test_tools_list_endpoint(self, http_server):
        """Test the tools/list endpoint returns all available tools."""
        data = self._make_mcp_request("tools/list")

        tools = data["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]

        assert "echo" in tool_names
        assert "ping" in tool_names
        assert "joke" in tool_names
        assert len(tools) == 3

    def test_echo_tool_http_call(self, http_server):
        """Test calling the echo tool via HTTP."""
        data = self._make_mcp_request(
            "tools/call", {"name": "echo", "arguments": {"text": "HTTP echo test"}}, request_id=2
        )

        result_text = data["result"]["content"][0]["text"]
        result = json.loads(result_text)

        assert result["data"] == "HTTP echo test"
        assert result["error"] is None

    def test_echo_tool_with_accumulated_params_http(self, http_server):
        """Test calling the echo tool with accumulated parameters via HTTP."""
        data = self._make_mcp_request(
            "tools/call",
            {"name": "echo", "arguments": {"text": "", "accumulated_params": ["param1", "param2", "param3"]}},
            request_id=3,
        )

        result_text = data["result"]["content"][0]["text"]
        result = json.loads(result_text)

        assert result["data"] == "param1; param2; param3"
        assert result["error"] is None

    def test_ping_tool_http_call(self, http_server):
        """Test calling the ping tool via HTTP."""
        data = self._make_mcp_request(
            "tools/call", {"name": "ping", "arguments": {"text": "HTTP ping test"}}, request_id=4
        )

        result_text = data["result"]["content"][0]["text"]
        result = json.loads(result_text)

        assert "pong" in result["data"]
        assert "HTTP ping test" in result["data"]
        assert result["error"] is None

    def test_joke_tool_http_call_no_api_key(self, http_server):
        """Test calling the joke tool via HTTP without API key."""
        data = self._make_mcp_request("tools/call", {"name": "joke", "arguments": {"text": "cats"}}, request_id=5)

        result_text = data["result"]["content"][0]["text"]
        result = json.loads(result_text)

        # Should either work (if API key is set) or show error message
        if result["error"]:
            assert "not available" in result["error"] or "configure GEMINI_API_KEY" in result["error"]
        else:
            # If it works, should have some joke content
            assert len(result["data"]) > 0

    def test_json_response_mode(self):
        """Test the server with JSON response mode instead of SSE."""
        import os

        # Determine the correct script path
        current_dir = os.getcwd()
        if current_dir.endswith("cattackles/echo"):
            script_path = "src/server.py"
        else:
            script_path = "cattackles/echo/src/server.py"

        proc = subprocess.Popen(
            ["python", script_path, "--port", "8002", "--json-response", "--log-level", "ERROR"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait for server to be ready
            self._wait_for_server_ready("http://127.0.0.1:8002")

            response = requests.post(
                "http://127.0.0.1:8002/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "echo", "arguments": {"text": "JSON mode test"}},
                },
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            )

            assert response.status_code == 200

            # In JSON mode, response should be direct JSON, not SSE
            data = response.json()
            result_text = data["result"]["content"][0]["text"]
            result = json.loads(result_text)

            assert result["data"] == "JSON mode test"
            assert result["error"] is None

        except Exception as e:
            # Capture output for debugging if test fails
            stdout, stderr = proc.communicate(timeout=2)
            error_msg = f"JSON response mode test failed: {e}"
            if stderr:
                error_msg += f"\nStderr: {stderr.decode()}"
            raise RuntimeError(error_msg)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)

    def test_invalid_tool_name(self, http_server):
        """Test calling a non-existent tool returns an error."""
        data = self._make_mcp_request(
            "tools/call", {"name": "nonexistent", "arguments": {"text": "test"}}, request_id=6
        )

        # Should contain an error in the result
        assert data["result"]["isError"] is True
        assert "Unknown tool" in data["result"]["content"][0]["text"]

    def test_malformed_request(self, http_server):
        """Test that malformed requests are handled gracefully."""
        response = requests.post(
            "http://127.0.0.1:8001/mcp",
            json={"invalid": "request"},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        )

        # Should return a 400 Bad Request for malformed JSON-RPC
        assert response.status_code == 400

    def test_missing_accept_header(self, http_server):
        """Test that requests without proper Accept header are rejected."""
        response = requests.post(
            "http://127.0.0.1:8001/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Content-Type": "application/json", "Accept": "application/json"},  # Missing text/event-stream
        )

        # Should return 406 Not Acceptable
        assert response.status_code == 406
        assert "Not Acceptable" in response.text
