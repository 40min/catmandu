import pathlib

import pytest

from catmandu.core.config import Settings
from catmandu.core.infrastructure.registry import CattackleRegistry


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
    assert cattackles[0].name == "echo"


def test_scan_invalid_cattackle(registry, invalid_cattackle_toml_file):
    """Tests scanning a directory with an invalid cattackle."""
    assert registry.scan() == 0
    assert registry.get_all() == []


def test_scan_multiple_cattackles(registry, valid_cattackle_toml_file, another_cattackle_toml_file):
    """Tests scanning a directory with multiple cattackles."""
    assert registry.scan() == 2
    cattackles = registry.get_all()
    assert len(cattackles) == 2
    assert {c.name for c in cattackles} == {"echo", "another"}


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
    assert all_cattackles[0].name == "echo"


def test_find_by_command(fs, valid_cattackle_toml_file, registry):
    """Tests finding a cattackle by a command it provides."""
    registry.scan()
    config = registry.find_by_command("echo")
    assert config is not None
    assert config.name == "echo"


def test_find_by_command_not_found(fs, valid_cattackle_toml_file, registry):
    """Tests finding a non-existent command."""
    config = registry.find_by_command("nonexistent")
    assert config is None


def test_find_by_cattackle_and_command(registry, valid_cattackle_toml_file):
    """Tests finding a cattackle by specific name and command."""
    registry.scan()
    config = registry.find_by_cattackle_and_command("echo", "echo")
    assert config is not None
    assert config.name == "echo"

    # Test non-existent cattackle
    config = registry.find_by_cattackle_and_command("nonexistent", "echo")
    assert config is None

    # Test non-existent command for existing cattackle
    config = registry.find_by_cattackle_and_command("echo", "nonexistent")
    assert config is None


def test_get_commands_for_cattackle(registry, valid_cattackle_toml_file):
    """Tests getting all commands for a specific cattackle."""
    registry.scan()
    commands = registry.get_commands_for_cattackle("echo")
    assert commands == ["echo"]

    # Test non-existent cattackle
    commands = registry.get_commands_for_cattackle("nonexistent")
    assert commands == []


def test_get_all_commands(registry, valid_cattackle_toml_file, another_cattackle_toml_file):
    """Tests getting all commands grouped by cattackle."""
    registry.scan()
    all_commands = registry.get_all_commands()
    assert all_commands == {"echo": ["echo"], "another": ["another"]}


@pytest.fixture
def cattackle_with_multiple_commands(fs):
    fs.create_file(
        "cattackles/multi/cattackle.toml",
        contents="""
[cattackle]
name = "multi"
description = "Cattackle with multiple commands"
version = "0.1.0"

[cattackle.commands.cmd1]
description = "First command."

[cattackle.commands.cmd2]
description = "Second command."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.multi.src.server"]
""",
    )


def test_cattackle_with_multiple_commands(registry, cattackle_with_multiple_commands):
    """Tests a cattackle that provides multiple commands."""
    registry.scan()

    # Both commands should be findable
    config1 = registry.find_by_command("cmd1")
    config2 = registry.find_by_command("cmd2")
    assert config1 is not None
    assert config2 is not None
    assert config1.name == "multi"
    assert config2.name == "multi"

    # Commands should be listed for the cattackle
    commands = registry.get_commands_for_cattackle("multi")
    assert set(commands) == {"cmd1", "cmd2"}


@pytest.fixture
def cattackles_with_same_command_name(fs):
    """Creates two cattackles that have commands with the same name."""
    fs.create_file(
        "cattackles/first/cattackle.toml",
        contents="""
[cattackle]
name = "first"
description = "First cattackle"
version = "0.1.0"

[cattackle.commands.shared]
description = "Shared command name in first cattackle."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.first.src.server"]
""",
    )

    fs.create_file(
        "cattackles/second/cattackle.toml",
        contents="""
[cattackle]
name = "second"
description = "Second cattackle"
version = "0.1.0"

[cattackle.commands.shared]
description = "Shared command name in second cattackle."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.second.src.server"]
""",
    )


def test_cattackles_with_same_command_name(registry, cattackles_with_same_command_name):
    """Tests handling of cattackles that have commands with the same name."""
    registry.scan()

    # find_by_command should return one of them (first found)
    config = registry.find_by_command("shared")
    assert config is not None
    assert config.name in ["first", "second"]

    # But we should be able to find specific ones by cattackle name
    first_config = registry.find_by_cattackle_and_command("first", "shared")
    second_config = registry.find_by_cattackle_and_command("second", "shared")

    assert first_config is not None
    assert second_config is not None
    assert first_config.name == "first"
    assert second_config.name == "second"

    # All commands should be listed correctly
    all_commands = registry.get_all_commands()
    assert all_commands == {"first": ["shared"], "second": ["shared"]}
