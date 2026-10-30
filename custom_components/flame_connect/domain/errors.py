"""Public errors never include upstream payloads or credentials."""


class FlameError(Exception):
    """Base API error."""


class AuthenticationError(FlameError):
    """The user must link their account again."""


class ConnectionError(FlameError):
    """Temporary failure reaching the service."""


class ProtocolError(FlameError):
    """The service returned an invalid payload."""


class CommandError(FlameError):
    """A command failed or its outcome is unknown."""


class DeviceUnavailable(FlameError):
    """A particular fireplace is unavailable."""


class AccessDenied(FlameError):
    """The account cannot access this fireplace."""
