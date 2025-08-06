"""Tests for user configuration management."""

import os
from unittest.mock import patch

from notion.config.user_config import (
    _get_user_configs,
    _parse_user_configs,
    get_user_config,
    is_user_authorized,
    reload_user_configs,
)


class TestParseUserConfigs:
    """Tests for _parse_user_configs function."""

    def test_parse_single_user_complete_config(self):
        """Test parsing a single user with complete configuration."""
        test_env = {
            "NOTION__USER__TESTUSER__TOKEN": "test_token_123",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "test_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            configs = _parse_user_configs()

            assert "testuser" in configs
            assert configs["testuser"]["token"] == "test_token_123"
            assert configs["testuser"]["parent_page_id"] == "test_page_id_456"

    def test_parse_multiple_users(self):
        """Test parsing multiple users with configurations."""
        test_env = {
            "NOTION__USER__USERA__TOKEN": "token1",
            "NOTION__USER__USERA__PARENT_PAGE_ID": "page1",
            "NOTION__USER__USERB__TOKEN": "token2",
            "NOTION__USER__USERB__PARENT_PAGE_ID": "page2",
        }

        with patch.dict(os.environ, test_env, clear=True):
            configs = _parse_user_configs()

            assert len(configs) == 2
            assert "usera" in configs
            assert "userb" in configs
            assert configs["usera"]["token"] == "token1"
            assert configs["userb"]["token"] == "token2"

    def test_parse_incomplete_user_config(self):
        """Test parsing user with incomplete configuration."""
        test_env = {
            "NOTION__USER__INCOMPLETE__TOKEN": "token_only",
            # Missing PARENT_PAGE_ID
        }

        with patch.dict(os.environ, test_env, clear=True):
            configs = _parse_user_configs()

            assert "incomplete" in configs
            assert configs["incomplete"]["token"] == "token_only"
            assert "parent_page_id" not in configs["incomplete"]

    def test_parse_no_matching_env_vars(self):
        """Test parsing when no matching environment variables exist."""
        test_env = {
            "SOME_OTHER_VAR": "value",
            "NOTION_WRONG_FORMAT": "value",
        }

        with patch.dict(os.environ, test_env, clear=True):
            configs = _parse_user_configs()
            assert configs == {}

    def test_parse_strips_whitespace(self):
        """Test that values are stripped of whitespace."""
        test_env = {
            "NOTION__USER__TESTUSER__TOKEN": "  token_with_spaces  ",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "  page_id_with_spaces  ",
        }

        with patch.dict(os.environ, test_env, clear=True):
            configs = _parse_user_configs()

            assert configs["testuser"]["token"] == "token_with_spaces"
            assert configs["testuser"]["parent_page_id"] == "page_id_with_spaces"


class TestGetUserConfig:
    """Tests for get_user_config function."""

    def test_get_existing_user_config(self):
        """Test getting configuration for an existing user."""
        test_env = {
            "NOTION__USER__TESTUSER__TOKEN": "test_token_123",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "test_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Clear cache to force reload
            reload_user_configs()

            config = get_user_config("testuser")

            assert config is not None
            assert config["token"] == "test_token_123"
            assert config["parent_page_id"] == "test_page_id_456"

    def test_get_nonexistent_user_config(self):
        """Test getting configuration for a user that doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            reload_user_configs()
            config = get_user_config("nonexistent_user")
            assert config is None

    def test_get_user_config_case_insensitive(self):
        """Test that username lookup is case-insensitive."""
        test_env = {
            "NOTION__USER__TESTUSER__TOKEN": "test_token_123",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "test_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()

            # All these should return the same config
            config1 = get_user_config("testuser")
            config2 = get_user_config("TESTUSER")
            config3 = get_user_config("TestUser")

            assert config1 == config2 == config3
            assert config1 is not None

    def test_get_user_config_empty_username(self):
        """Test getting configuration with empty username."""
        config = get_user_config("")
        assert config is None

    def test_get_user_config_none_username(self):
        """Test getting configuration with None username."""
        config = get_user_config(None)
        assert config is None

    def test_get_user_config_whitespace_username(self):
        """Test getting configuration with whitespace-only username."""
        config = get_user_config("   ")
        assert config is None


class TestIsUserAuthorized:
    """Tests for is_user_authorized function."""

    def test_authorized_user_with_valid_config(self):
        """Test that user with valid token and parent_page_id is authorized."""
        test_env = {
            "NOTION__USER__VALIDUSER__TOKEN": "valid_token_123",
            "NOTION__USER__VALIDUSER__PARENT_PAGE_ID": "valid_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("validuser") is True

    def test_unauthorized_user_not_in_config(self):
        """Test that user not in configuration is not authorized."""
        with patch.dict(os.environ, {}, clear=True):
            reload_user_configs()
            assert is_user_authorized("unknown_user") is False

    def test_unauthorized_user_missing_token(self):
        """Test that user with missing token is not authorized."""
        test_env = {
            "NOTION__USER__INCOMPLETE__PARENT_PAGE_ID": "valid_page_id_456"
            # Missing token
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("incomplete") is False

    def test_unauthorized_user_missing_parent_page_id(self):
        """Test that user with missing parent_page_id is not authorized."""
        test_env = {
            "NOTION__USER__INCOMPLETE__TOKEN": "valid_token_123"
            # Missing parent_page_id
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("incomplete") is False

    def test_unauthorized_user_empty_token(self):
        """Test that user with empty token is not authorized."""
        test_env = {
            "NOTION__USER__EMPTYTOKEN__TOKEN": "",
            "NOTION__USER__EMPTYTOKEN__PARENT_PAGE_ID": "valid_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("emptytoken") is False

    def test_unauthorized_user_empty_parent_page_id(self):
        """Test that user with empty parent_page_id is not authorized."""
        test_env = {
            "NOTION__USER__EMPTYPAGE__TOKEN": "valid_token_123",
            "NOTION__USER__EMPTYPAGE__PARENT_PAGE_ID": "",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("emptypage") is False

    def test_unauthorized_user_whitespace_token(self):
        """Test that user with whitespace-only token is not authorized."""
        test_env = {
            "NOTION__USER__WHITESPACETOKEN__TOKEN": "   ",
            "NOTION__USER__WHITESPACETOKEN__PARENT_PAGE_ID": "valid_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("whitespacetoken") is False

    def test_unauthorized_user_whitespace_parent_page_id(self):
        """Test that user with whitespace-only parent_page_id is not authorized."""
        test_env = {
            "NOTION__USER__WHITESPACEPAGE__TOKEN": "valid_token_123",
            "NOTION__USER__WHITESPACEPAGE__PARENT_PAGE_ID": "   ",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("whitespacepage") is False

    def test_unauthorized_empty_username(self):
        """Test that empty username is not authorized."""
        assert is_user_authorized("") is False

    def test_unauthorized_none_username(self):
        """Test that None username is not authorized."""
        assert is_user_authorized(None) is False

    def test_multiple_valid_users(self):
        """Test authorization with multiple valid users."""
        test_env = {
            "NOTION__USER__USERA__TOKEN": "token1",
            "NOTION__USER__USERA__PARENT_PAGE_ID": "page_id1",
            "NOTION__USER__USERB__TOKEN": "token2",
            "NOTION__USER__USERB__PARENT_PAGE_ID": "page_id2",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            assert is_user_authorized("usera") is True
            assert is_user_authorized("userb") is True
            assert is_user_authorized("userc") is False


class TestCaching:
    """Tests for configuration caching functionality."""

    def test_config_caching(self):
        """Test that configurations are cached and reused."""
        test_env = {
            "NOTION__USER__TESTUSER__TOKEN": "test_token_123",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "test_page_id_456",
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()

            # First call should parse from environment
            config1 = get_user_config("testuser")

            # Second call should use cached result
            config2 = get_user_config("testuser")

            # Should be the same object (cached)
            assert config1 is config2

    def test_reload_user_configs(self):
        """Test that reload_user_configs clears cache and reloads."""
        test_env1 = {
            "NOTION__USER__TESTUSER__TOKEN": "old_token",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "old_page_id",
        }

        with patch.dict(os.environ, test_env1, clear=True):
            reload_user_configs()
            config1 = get_user_config("testuser")
            assert config1["token"] == "old_token"

        # Change environment and reload
        test_env2 = {
            "NOTION__USER__TESTUSER__TOKEN": "new_token",
            "NOTION__USER__TESTUSER__PARENT_PAGE_ID": "new_page_id",
        }

        with patch.dict(os.environ, test_env2, clear=True):
            reload_user_configs()
            config2 = get_user_config("testuser")
            assert config2["token"] == "new_token"


class TestUserConfigsIntegration:
    """Integration tests for user configuration functionality."""

    def test_config_consistency_between_functions(self):
        """Test that get_user_config and is_user_authorized are consistent."""
        test_env = {
            "NOTION__USER__CONSISTENT__TOKEN": "test_token",
            "NOTION__USER__CONSISTENT__PARENT_PAGE_ID": "test_page_id",
            "NOTION__USER__INCOMPLETE__TOKEN": "test_token",
            # Missing PARENT_PAGE_ID for incomplete user
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()

            # User with complete config should be authorized and return config
            assert is_user_authorized("consistent") is True
            config = get_user_config("consistent")
            assert config is not None
            assert config["token"] == "test_token"
            assert config["parent_page_id"] == "test_page_id"

            # User with incomplete config should not be authorized but still return config
            assert is_user_authorized("incomplete") is False
            config = get_user_config("incomplete")
            assert config is not None
            assert config["token"] == "test_token"
            assert "parent_page_id" not in config

            # Non-existent user should not be authorized and return None
            assert is_user_authorized("nonexistent") is False
            assert get_user_config("nonexistent") is None

    def test_environment_variable_format_validation(self):
        """Test that only properly formatted environment variables are parsed."""
        test_env = {
            # Valid formats (only uppercase letters and underscores allowed)
            "NOTION__USER__VALIDA__TOKEN": "token1",
            "NOTION__USER__VALIDA__PARENT_PAGE_ID": "page1",
            "NOTION__USER__VALID_WITH_UNDERSCORES__TOKEN": "token2",
            "NOTION__USER__VALID_WITH_UNDERSCORES__PARENT_PAGE_ID": "page2",
            # Invalid formats (should be ignored)
            "NOTION_USER_INVALID_TOKEN": "should_be_ignored",  # Wrong separator
            "NOTION__USER__INVALID": "should_be_ignored",  # Missing field
            "NOTION__USER__INVALID1__TOKEN": "should_be_ignored",  # Contains digit
            "NOTION__USER__invalid__TOKEN": "should_be_ignored",  # Contains lowercase
            "NOTION__USER__INVALID__UNKNOWN_FIELD": "should_be_ignored",  # Unknown field
            "OTHER__USER__VALID__TOKEN": "should_be_ignored",  # Wrong prefix
        }

        with patch.dict(os.environ, test_env, clear=True):
            reload_user_configs()
            configs = _get_user_configs()

            # Should only have the valid users
            assert len(configs) == 2
            assert "valida" in configs
            assert "valid_with_underscores" in configs

            # Invalid formats should be ignored
            assert "invalid" not in configs
            assert "invalid1" not in configs
