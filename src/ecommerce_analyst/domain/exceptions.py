"""Domain-specific exception types."""


class EcommerceAnalystError(Exception):
    """Base exception for project-specific failures."""


class DatasetIngestionError(EcommerceAnalystError):
    """Raised when an uploaded dataset cannot be safely ingested."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class DomainValidationError(EcommerceAnalystError):
    """Raised when domain validation cannot be performed due to invalid input.

    This is not raised for normal rejection outcomes — those are returned as
    a structured DomainValidationResult. This is only raised when the validator
    receives an input that prevents it from running at all (e.g. null dataset).
    """

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
