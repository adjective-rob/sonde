class TopicOpsError(Exception):
    """Base exception for TopicOps."""


class ConfigLoadError(TopicOpsError):
    """Raised when a topic config cannot be loaded."""


class TopicNotFoundError(TopicOpsError):
    """Raised when a requested topic does not exist."""
