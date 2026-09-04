"""Dataset builder helpers for unit and integration tests.

Creates ``IngestedDataset`` objects in-memory without needing real files,
allowing the domain validator and other services to be tested in isolation.
"""

from __future__ import annotations

from typing import Any

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
    """Build an ``IngestedDataset`` from a column spec and optional records."""
    column_metadata = tuple(
        ColumnMetadata(index=i, name=name, inferred_dtype=dtype)
        for i, (name, dtype) in enumerate(columns)
    )

    if records is None:
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


def make_ecommerce_dataset(
    *,
    records: list[dict[str, Any]] | None = None,
    row_count: int = 5,
    filename: str = "orders.csv",
) -> IngestedDataset:
    """Build a standard, clean e-commerce IngestedDataset for testing."""
    columns = [
        ("order_id", "int64"),
        ("product_id", "object"),
        ("price", "float64"),
        ("quantity", "int64"),
        ("order_date", "object"),
        ("customer_id", "object"),
        ("category", "object"),
    ]

    if records is None:
        records = [
            {
                "order_id": 1000 + i,
                "product_id": f"PROD-{i % 3 + 1}",
                "price": round(19.99 + (i * 10.0), 2),
                "quantity": (i % 4) + 1,
                "order_date": f"2024-01-0{i % 8 + 1}",
                "customer_id": f"CUST-{i % 2 + 1}",
                "category": "Electronics" if i % 2 == 0 else "Apparel",
            }
            for i in range(row_count)
        ]

    return make_ingested_dataset(
        columns=columns,
        records=records,
        filename=filename,
    )
