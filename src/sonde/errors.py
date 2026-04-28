class SondeError(Exception):
    """Base exception for Sonde."""


class ConfigLoadError(SondeError):
    """Raised when a topic config cannot be loaded."""


class TopicNotFoundError(SondeError):
    """Raised when a requested topic does not exist."""
