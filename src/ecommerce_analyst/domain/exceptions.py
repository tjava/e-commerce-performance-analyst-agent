"""Domain-specific exception types."""


class EcommerceAnalystError(Exception):
    """Base exception for project-specific failures."""


class DatasetIngestionError(EcommerceAnalystError):
    """Raised when an uploaded dataset cannot be safely ingested."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
