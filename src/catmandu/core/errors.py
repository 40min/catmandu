class CatmanduError(Exception):
    """Base exception for the application."""


class CommandNotFoundError(CatmanduError):
    """Raised when a command cannot be found in the registry."""


class CattackleExecutionError(CatmanduError):
    """Raised when a cattackle fails to execute."""


class CattackleValidationError(CattackleExecutionError):
    """Raised when cattackle input validation fails - should not be retried."""


class CattackleResponseError(CattackleExecutionError):
    """Raised when cattackle returns invalid response format - should not be retried."""


class ConfigurationError(CatmanduError):
    """Raised when there are configuration validation issues."""


class AudioProcessingConfigurationError(ConfigurationError):
    """Raised when there are audio processing configuration issues."""
