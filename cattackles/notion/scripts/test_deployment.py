#!/usr/bin/env python3
"""
Deployment validation script for the Notion cattackle.
This script validates the complete deployment configuration.
"""

import subprocess
import sys
import time
from pathlib import Path

import requests
import toml


def test_toml_validation():
    """Test that cattackle.toml is valid and complete."""
    print("🔍 Testing cattackle.toml validation...")

    try:
        with open("cattackle.toml", "r") as f:
            config = toml.load(f)

        # Check required fields
        required_fields = [
            "cattackle.name",
            "cattackle.version",
            "cattackle.description",
            "cattackle.commands",
            "cattackle.mcp.transport.type",
            "cattackle.mcp.transport.url",
        ]

        for field in required_fields:
            keys = field.split(".")
            current = config
            for key in keys:
                if key not in current:
                    raise ValueError(f"Missing required field: {field}")
                current = current[key]

        print("✅ cattackle.toml validation passed")
        return True

    except Exception as e:
        print(f"❌ cattackle.toml validation failed: {e}")
        return False


def test_container_build():
    """Test that the container builds successfully."""
    print("🔍 Testing container build...")

    try:
        result = subprocess.run(
            ["docker", "build", "--target", "production", "-t", "notion-cattackle:test", "."],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            print("✅ Container build successful")
            return True
        else:
            print(f"❌ Container build failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Container build timed out")
        return False
    except Exception as e:
        print(f"❌ Container build error: {e}")
        return False


def test_container_health():
    """Test that the container starts and health check passes."""
    print("🔍 Testing container health...")

    container_id = None
    try:
        # Start container
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                "notion-cattackle-test",
                "-p",
                "8002:8002",
                "notion-cattackle:test",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"❌ Failed to start container: {result.stderr}")
            return False

        container_id = result.stdout.strip()
        print(f"📦 Container started: {container_id[:12]}")

        # Wait for startup
        time.sleep(5)

        # Test health endpoint
        response = requests.get("http://localhost:8002/health", timeout=10)

        if response.status_code == 200:
            health_data = response.json()
            if health_data.get("status") == "healthy":
                print("✅ Container health check passed")
                return True
            else:
                print(f"❌ Health check failed: {health_data}")
                return False
        else:
            print(f"❌ Health endpoint returned {response.status_code}")
            return False

    except requests.RequestException as e:
        print(f"❌ Health check request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Container health test error: {e}")
        return False
    finally:
        # Clean up container
        if container_id:
            subprocess.run(["docker", "stop", container_id], capture_output=True, text=True)


def test_registry_integration():
    """Test that the cattackle can be discovered by the registry."""
    print("🔍 Testing registry integration...")

    try:
        # Add parent directory to path for imports
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root / "src"))

        from catmandu.core.config import Settings
        from catmandu.core.infrastructure.registry import CattackleRegistry

        # Create registry and scan from project root
        cattackles_dir = project_root / "cattackles"
        settings = Settings(cattackles_dir=str(cattackles_dir))
        registry = CattackleRegistry(settings)

        # Check if notion cattackle was found
        notion_config = registry.find_by_command("to_notion")
        if notion_config and notion_config.name == "notion":
            print("✅ Registry integration successful")
            return True
        else:
            print("❌ Notion cattackle not found in registry")
            return False

    except Exception as e:
        print(f"❌ Registry integration failed: {e}")
        return False


def main():
    """Run all deployment validation tests."""
    print("🚀 Starting Notion cattackle deployment validation...\n")

    tests = [test_toml_validation, test_container_build, test_container_health, test_registry_integration]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All deployment validation tests passed!")
        print("✅ Notion cattackle is ready for deployment")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
