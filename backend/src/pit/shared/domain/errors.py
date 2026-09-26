class DomainError(Exception):
    """A business rule was broken. `message` is safe to show to the user."""

    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvariantViolation(DomainError):
    code = "invariant_violation"


class InvalidStateTransition(DomainError):
    code = "invalid_state_transition"


class NotFound(DomainError):
    code = "not_found"


class PermissionDenied(DomainError):
    code = "permission_denied"
