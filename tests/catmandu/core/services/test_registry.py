import pathlib

import pytest

from catmandu.core.config import Settings
from catmandu.core.services.registry import CattackleRegistry


@pytest.fixture
def registry(fs):
    # Create cattackles directory if it doesn't exist
    if not fs.exists("cattackles"):
        fs.create_dir("cattackles")
    settings = Settings(cattackles_dir="cattackles", telegram_bot_token="dummy_token")
    return CattackleRegistry(config=settings)


@pytest.fixture
def valid_cattackle_toml_file(fs):
    fs.create_file(
        "cattackles/echo/cattackle.toml",
        contents="""
[cattackle]
name = "echo"
description = "Echoes back the input"
version = "0.1.0"

[cattackle.commands.echo]
description = "Echoes back the payload."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.echo.src.server"]
""",
    )


@pytest.fixture
def invalid_cattackle_toml_file(fs):
    fs.create_file(
        "cattackles/invalid/cattackle.toml",
        contents="""
[cattackle]
name = "invalid"
description = "Invalid cattackle"
version = "0.1.0"
# Missing commands
""",
    )


@pytest.fixture
def another_cattackle_toml_file(fs):
    fs.create_file(
        "cattackles/another/cattackle.toml",
        contents="""
[cattackle]
name = "another"
description = "Another cattackle"
version = "0.1.0"

[cattackle.commands.another]
description = "Another command."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.another.src.server"]
""",
    )


def test_scan_empty_directory(registry):
    """Tests scanning an empty cattackles directory."""
    assert registry.scan() == 0
    assert registry.get_all() == []


def test_scan_valid_cattackle(registry, valid_cattackle_toml_file):
    """Tests scanning a directory with a valid cattackle."""
    assert registry.scan() == 1
    cattackles = registry.get_all()
    assert len(cattackles) == 1
    assert cattackles[0].cattackle.name == "echo"


def test_scan_invalid_cattackle(registry, invalid_cattackle_toml_file):
    """Tests scanning a directory with an invalid cattackle."""
    assert registry.scan() == 0
    assert registry.get_all() == []


def test_scan_multiple_cattackles(registry, valid_cattackle_toml_file, another_cattackle_toml_file):
    """Tests scanning a directory with multiple cattackles."""
    assert registry.scan() == 2
    cattackles = registry.get_all()
    assert len(cattackles) == 2
    assert {c.cattackle.name for c in cattackles} == {"echo", "another"}


def test_scan_non_existent_directory(registry):
    """Tests scanning a non-existent cattackles directory."""
    registry._cattackles_dir = pathlib.Path("nonexistent")
    assert registry.scan() == 0
    assert registry.get_all() == []


def test_get_all_cattackles(registry, valid_cattackle_toml_file):
    """Tests retrieving all registered cattackles."""
    registry.scan()
    all_cattackles = registry.get_all()
    assert isinstance(all_cattackles, list)
    assert len(all_cattackles) == 1
    assert all_cattackles[0].cattackle.name == "echo"


def test_find_by_command(fs, valid_cattackle_toml_file, registry):
    """Tests finding a cattackle by a command it provides."""
    registry.scan()
    config = registry.find_by_command("echo")
    assert config is not None
    assert config.cattackle.name == "echo"


def test_find_by_command_not_found(fs, valid_cattackle_toml_file, registry):
    """Tests finding a non-existent command."""
    config = registry.find_by_command("nonexistent")
    assert config is None
