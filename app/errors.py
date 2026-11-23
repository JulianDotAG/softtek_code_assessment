class NotFoundError(Exception):
    """The requested resource does not exist (HTTP 404)."""

    def __init__(self, resource: str, identifier: object) -> None:
        self.detail = f"{resource} {identifier} not found"
        super().__init__(self.detail)


class ConflictError(Exception):
    """The request conflicts with an existing resource or a business rule (HTTP 409)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)
