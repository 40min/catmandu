import pytest

from catmandu.core.config import Settings
from catmandu.core.services.registry import CattackleRegistry


@pytest.fixture
def registry():
    """Fixture to provide a CattackleRegistry instance with configurable settings."""
    settings = Settings(cattackles_dir="/cattackles")
    registry = CattackleRegistry(config=settings)
    registry.scan()

    return registry


@pytest.fixture
def nonexistent_dir_registry():
    """Fixture to provide a CattackleRegistry instance with configurable settings."""
    settings = Settings(cattackles_dir="/nonexistent")
    registry = CattackleRegistry(config=settings)
    registry.scan()

    return registry


def test_scan_successful(
    fs, valid_cattackle_toml_file, valid_cattackle_toml_2_file, registry
):
    """Tests a successful scan of a directory with valid cattackles."""

    all_cattackles = registry.get_all()
    assert len(all_cattackles) == 2
    names = {c.cattackle.name for c in all_cattackles}
    assert names == {"echo", "admin"}


def test_scan_directory_not_found(
    fs, valid_cattackle_toml_file, nonexistent_dir_registry, caplog
):
    """Tests scanning a non-existent directory."""
    nonexistent_dir_registry.scan()
    all_cattackles = nonexistent_dir_registry.get_all()
    assert len(all_cattackles) == 0
    assert "Cattackles directory not found" in caplog.text


def test_scan_with_malformed_toml(fs, invalid_toml_file, registry, caplog):
    """Tests that a malformed TOML file is skipped and an error is logged."""
    registry.scan()
    all_cattackles = registry.get_all()
    assert len(all_cattackles) == 0
    assert "Failed to load cattackle manifest" in caplog.text
    assert "TomlDecodeError" in caplog.text


def test_scan_with_invalid_config(fs, invalid_config_toml_file, registry, caplog):
    """Tests that a config with validation errors is skipped and an error is logged."""
    registry.scan()
    all_cattackles = registry.get_all()
    assert len(all_cattackles) == 0

    assert "Failed to load cattackle manifest" in caplog.text
    assert "Field required" in caplog.text


def test_get_all_returns_list_of_configs(fs, valid_cattackle_toml_file, registry):
    """Tests the get_all method."""
    all_cattackles = registry.get_all()
    assert isinstance(all_cattackles, list)
    assert len(all_cattackles) == 1
    assert all_cattackles[0].cattackle.name == "echo"
