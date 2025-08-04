"""Tests for user configuration management."""

from unittest.mock import patch

from notion.config.user_config import USER_CONFIGS, get_user_config, is_user_authorized


class TestGetUserConfig:
    """Tests for get_user_config function."""

    def test_get_existing_user_config(self):
        """Test getting configuration for an existing user."""
        test_configs = {"testuser": {"token": "test_token_123", "path": "test_page_id_456"}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            config = get_user_config("testuser")

            assert config is not None
            assert config["token"] == "test_token_123"
            assert config["path"] == "test_page_id_456"

    def test_get_nonexistent_user_config(self):
        """Test getting configuration for a user that doesn't exist."""
        with patch.dict(USER_CONFIGS, {}, clear=True):
            config = get_user_config("nonexistent_user")
            assert config is None

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
        """Test that user with valid token and path is authorized."""
        test_configs = {"validuser": {"token": "valid_token_123", "path": "valid_page_id_456"}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("validuser") is True

    def test_unauthorized_user_not_in_config(self):
        """Test that user not in configuration is not authorized."""
        with patch.dict(USER_CONFIGS, {}, clear=True):
            assert is_user_authorized("unknown_user") is False

    def test_unauthorized_user_missing_token(self):
        """Test that user with missing token is not authorized."""
        test_configs = {
            "incomplete_user": {
                "path": "valid_page_id_456"
                # Missing token
            }
        }

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("incomplete_user") is False

    def test_unauthorized_user_missing_path(self):
        """Test that user with missing path is not authorized."""
        test_configs = {
            "incomplete_user": {
                "token": "valid_token_123"
                # Missing path
            }
        }

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("incomplete_user") is False

    def test_unauthorized_user_empty_token(self):
        """Test that user with empty token is not authorized."""
        test_configs = {"empty_token_user": {"token": "", "path": "valid_page_id_456"}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("empty_token_user") is False

    def test_unauthorized_user_empty_path(self):
        """Test that user with empty path is not authorized."""
        test_configs = {"empty_path_user": {"token": "valid_token_123", "path": ""}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("empty_path_user") is False

    def test_unauthorized_user_whitespace_token(self):
        """Test that user with whitespace-only token is not authorized."""
        test_configs = {"whitespace_token_user": {"token": "   ", "path": "valid_page_id_456"}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("whitespace_token_user") is False

    def test_unauthorized_user_whitespace_path(self):
        """Test that user with whitespace-only path is not authorized."""
        test_configs = {"whitespace_path_user": {"token": "valid_token_123", "path": "   "}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("whitespace_path_user") is False

    def test_unauthorized_empty_username(self):
        """Test that empty username is not authorized."""
        assert is_user_authorized("") is False

    def test_unauthorized_none_username(self):
        """Test that None username is not authorized."""
        assert is_user_authorized(None) is False

    def test_multiple_valid_users(self):
        """Test authorization with multiple valid users."""
        test_configs = {"user1": {"token": "token1", "path": "path1"}, "user2": {"token": "token2", "path": "path2"}}

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            assert is_user_authorized("user1") is True
            assert is_user_authorized("user2") is True
            assert is_user_authorized("user3") is False


class TestUserConfigsIntegration:
    """Integration tests for user configuration functionality."""

    def test_config_consistency_between_functions(self):
        """Test that get_user_config and is_user_authorized are consistent."""
        test_configs = {
            "consistent_user": {"token": "test_token", "path": "test_path"},
            "incomplete_user": {
                "token": "test_token"
                # Missing path
            },
        }

        with patch.dict(USER_CONFIGS, test_configs, clear=True):
            # User with complete config should be authorized and return config
            assert is_user_authorized("consistent_user") is True
            config = get_user_config("consistent_user")
            assert config is not None
            assert config["token"] == "test_token"
            assert config["path"] == "test_path"

            # User with incomplete config should not be authorized but still return config
            assert is_user_authorized("incomplete_user") is False
            config = get_user_config("incomplete_user")
            assert config is not None
            assert config["token"] == "test_token"
            assert "path" not in config

            # Non-existent user should not be authorized and return None
            assert is_user_authorized("nonexistent") is False
            assert get_user_config("nonexistent") is None
