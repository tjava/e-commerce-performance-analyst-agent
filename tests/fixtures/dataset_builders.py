"""Dataset builder helpers for unit and integration tests.

Creates ``IngestedDataset`` objects in-memory without needing real files,
allowing the domain validator and other services to be tested in isolation.
"""

from __future__ import annotations

from ecommerce_analyst.domain.enums.dataset_file_type import DatasetFileType
from ecommerce_analyst.domain.models.dataset import (
    CellValue,
    ColumnMetadata,
    DatasetMetadata,
    IngestedDataset,
)


def make_ingested_dataset(
    *,
    columns: list[tuple[str, str]],
    records: list[dict[str, CellValue]] | None = None,
    filename: str = "test_dataset.csv",
    file_type: DatasetFileType = DatasetFileType.CSV,
    file_size_bytes: int = 1024,
    parsing_warnings: tuple[str, ...] = (),
) -> IngestedDataset:
    """Build an ``IngestedDataset`` from a column spec and optional records.

    Parameters
    ----------
    columns:
        List of ``(name, inferred_dtype)`` tuples defining the schema.
    records:
        Optional list of record dicts.  Defaults to a single dummy row.
    filename:
        Filename stored in metadata (does not need to exist on disk).
    file_type:
        ``DatasetFileType`` enum value (defaults to CSV).
    file_size_bytes:
        Reported file size (defaults to 1024).
    parsing_warnings:
        Any parsing warnings to include in metadata.

    Returns
    -------
    IngestedDataset
        A fully valid, frozen dataset representation.
    """
    column_metadata = tuple(
        ColumnMetadata(index=i, name=name, inferred_dtype=dtype)
        for i, (name, dtype) in enumerate(columns)
    )

    if records is None:
        # Build one synthetic row with a sensible default per dtype
        default_row: dict[str, CellValue] = {}
        for name, dtype in columns:
            if dtype.startswith("int"):
                default_row[name] = 1
            elif dtype.startswith("float"):
                default_row[name] = 1.0
            elif dtype.startswith("datetime"):
                default_row[name] = "2024-01-01"
            else:
                default_row[name] = "value"
        records = [default_row]

    metadata = DatasetMetadata(
        filename=filename,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        row_count=len(records),
        column_count=len(columns),
        columns=column_metadata,
        parsing_warnings=parsing_warnings,
    )

    return IngestedDataset(metadata=metadata, records=records)
