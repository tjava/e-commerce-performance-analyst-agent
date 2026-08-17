"""Supported uploaded dataset file types."""

from __future__ import annotations

from enum import StrEnum


class DatasetFileType(StrEnum):
    """File formats accepted by the ingestion layer."""

    CSV = "csv"
    XLSX = "xlsx"

    @classmethod
    def from_extension(cls, extension: str) -> DatasetFileType:
        """Resolve a file type from a path extension."""

        normalized = extension.lower().lstrip(".")
        match normalized:
            case "csv":
                return cls.CSV
            case "xlsx":
                return cls.XLSX
            case _:
                raise ValueError(f"Unsupported dataset file extension: .{normalized}")
