from catmandu.core.config import Settings
from catmandu.core.services.registry import CattackleRegistry


def test_scan_successful(fs, valid_cattackle_toml_file, valid_cattackle_toml_2_file):
    """Tests a successful scan of a directory with valid cattackles."""
    cattackles_dir = "/cattackles"
    fs.create_dir(f"{cattackles_dir}/empty_dir")  # A dir without a manifest

    settings = Settings(cattackles_dir=cattackles_dir)
    registry = CattackleRegistry(config=settings)
    count = registry.scan()

    assert count == 2
    all_cattackles = registry.get_all()
    assert len(all_cattackles) == 2
    names = {c.cattackle.name for c in all_cattackles}
    assert names == {"echo", "admin"}


def test_scan_directory_not_found(fs, caplog):
    """Tests scanning a non-existent directory."""
    settings = Settings(cattackles_dir="/nonexistent")
    registry = CattackleRegistry(config=settings)
    count = registry.scan()
    assert count == 0
    assert "Cattackles directory not found" in caplog.text


def test_scan_with_malformed_toml(fs, caplog, invalid_toml_file):
    """Tests that a malformed TOML file is skipped and an error is logged."""
    cattackles_dir = "/cattackles"

    settings = Settings(cattackles_dir=cattackles_dir)
    registry = CattackleRegistry(config=settings)
    count = registry.scan()

    assert count == 0
    assert "Failed to load cattackle manifest" in caplog.text
    assert "TomlDecodeError" in caplog.text


def test_scan_with_invalid_config(fs, caplog, invalid_config_toml_file):
    """Tests that a config with validation errors is skipped and an error is logged."""
    cattackles_dir = "/cattackles"

    settings = Settings(cattackles_dir=cattackles_dir)
    registry = CattackleRegistry(config=settings)
    count = registry.scan()

    assert count == 0
    assert "Failed to load cattackle manifest" in caplog.text
    assert "Field required" in caplog.text


def test_get_all_returns_list_of_configs(fs, valid_cattackle_toml_file):
    """Tests the get_all method."""
    cattackles_dir = "/cattackles"

    settings = Settings(cattackles_dir=cattackles_dir)
    registry = CattackleRegistry(config=settings)
    registry.scan()

    all_cattackles = registry.get_all()
    assert isinstance(all_cattackles, list)
    assert len(all_cattackles) == 1
    assert all_cattackles[0].cattackle.name == "echo"
