from catmandu.core.services.registry import CattackleRegistry

# A valid cattackle.toml content
VALID_CATTACKLE_TOML = """
[cattackle]
name = "echo"
version = "0.1.0"
description = "A simple echo cattackle."
[cattackle.commands]
echo = { description = "Echoes back the payload." }
[cattackle.mcp]
transport = "stdio"
"""

# Another valid cattackle.toml for testing duplicates
VALID_CATTACKLE_TOML_2 = """
[cattackle]
name = "admin"
version = "0.1.0"
description = "An admin cattackle."
[cattackle.commands]
reload = { description = "Reloads cattackles." }
echo = { description = "A duplicate echo command." }
[cattackle.mcp]
transport = "stdio"
"""

# A malformed TOML file
INVALID_TOML = """
[cattackle
name = "bad"
"""

# A TOML with missing required fields (validation error)
INVALID_CONFIG_TOML = """
[cattackle]
name = "invalid"
version = "0.1.0"
"""


def test_scan_successful(fs):
    """Tests a successful scan of a directory with valid cattackles."""
    cattackles_dir = "/cattackles"
    fs.create_file(
        f"{cattackles_dir}/echo/cattackle.toml", contents=VALID_CATTACKLE_TOML
    )
    fs.create_file(
        f"{cattackles_dir}/admin/cattackle.toml", contents=VALID_CATTACKLE_TOML_2
    )
    fs.create_dir(f"{cattackles_dir}/empty_dir")  # A dir without a manifest

    registry = CattackleRegistry(cattackles_dir=cattackles_dir)
    count = registry.scan()

    assert count == 2
    all_cattackles = registry.get_all()
    assert len(all_cattackles) == 2
    names = {c.cattackle.name for c in all_cattackles}
    assert names == {"echo", "admin"}


def test_scan_directory_not_found(fs, caplog, caplog_setup_for_loguru):
    """Tests scanning a non-existent directory."""
    registry = CattackleRegistry(cattackles_dir="/nonexistent")
    count = registry.scan()
    assert count == 0
    assert "Cattackles directory not found" in caplog.text


def test_scan_with_malformed_toml(fs, caplog, caplog_setup_for_loguru):
    """Tests that a malformed TOML file is skipped and an error is logged."""
    cattackles_dir = "/cattackles"
    fs.create_file(f"{cattackles_dir}/bad/cattackle.toml", contents=INVALID_TOML)

    registry = CattackleRegistry(cattackles_dir=cattackles_dir)
    count = registry.scan()

    assert count == 0
    assert "Failed to load cattackle manifest" in caplog.text
    assert "TomlDecodeError" in caplog.text


def test_scan_with_invalid_config(fs, caplog, caplog_setup_for_loguru):
    """Tests that a config with validation errors is skipped and an error is logged."""
    cattackles_dir = "/cattackles"
    fs.create_file(
        f"{cattackles_dir}/invalid/cattackle.toml", contents=INVALID_CONFIG_TOML
    )

    registry = CattackleRegistry(cattackles_dir=cattackles_dir)
    count = registry.scan()

    assert count == 0
    assert "Failed to load cattackle manifest" in caplog.text
    assert "ValidationError" in caplog.text


def test_scan_handles_duplicate_commands(fs, caplog, caplog_setup_for_loguru):
    """Tests that duplicate commands are registered with a warning."""
    cattackles_dir = "/cattackles"
    fs.create_file(
        f"{cattackles_dir}/echo/cattackle.toml", contents=VALID_CATTACKLE_TOML
    )
    fs.create_file(
        f"{cattackles_dir}/admin/cattackle.toml", contents=VALID_CATTACKLE_TOML_2
    )

    registry = CattackleRegistry(cattackles_dir=cattackles_dir)
    registry.scan()

    assert "Duplicate command found, overwriting" in caplog.text
    assert "command=echo" in caplog.text
    assert "new_cattackle=admin" in caplog.text
    assert "old_cattackle=echo" in caplog.text


def test_get_all_returns_list_of_configs(fs):
    """Tests the get_all method."""
    cattackles_dir = "/cattackles"
    fs.create_file(
        f"{cattackles_dir}/echo/cattackle.toml", contents=VALID_CATTACKLE_TOML
    )

    registry = CattackleRegistry(cattackles_dir=cattackles_dir)
    registry.scan()

    all_cattackles = registry.get_all()
    assert isinstance(all_cattackles, list)
    assert len(all_cattackles) == 1
    assert all_cattackles[0].cattackle.name == "echo"
