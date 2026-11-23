class DomainError(Exception):
    """A business rule violation, rendered as JSON by a single handler in `app/main.py`.

    Each subclass carries the status code it maps to, so a new error is one class and no
    change to the HTTP layer.
    """

    status_code: int

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(DomainError):
    """The requested resource does not exist (HTTP 404)."""

    status_code = 404

    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(f"{resource} {identifier} not found")


class ConflictError(DomainError):
    """The request conflicts with an existing resource or a business rule (HTTP 409)."""

    status_code = 409
