from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from ecommerce_analyst.application.use_cases import IngestDatasetUseCase
from ecommerce_analyst.domain.enums import DatasetFileType
from ecommerce_analyst.domain.exceptions import DatasetIngestionError
from ecommerce_analyst.domain.models import DatasetIngestionLimits
from ecommerce_analyst.infrastructure.data import PandasDatasetReader


def test_ingests_valid_csv_dataset(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text(
        "order_id,customer_id,total\n1001,C-1,25.50\n1002,C-2,40.00\n",
        encoding="utf-8",
    )
    use_case = IngestDatasetUseCase(PandasDatasetReader(), _limits())

    dataset = use_case.execute(file_path)

    assert dataset.metadata.filename == "orders.csv"
    assert dataset.metadata.file_type is DatasetFileType.CSV
    assert dataset.metadata.row_count == 2
    assert dataset.metadata.column_count == 3
    assert dataset.metadata.column_names == ("order_id", "customer_id", "total")
    assert dataset.records[0]["order_id"] == 1001
    assert dataset.records[0]["customer_id"] == "C-1"


def test_ingests_valid_xlsx_dataset(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.xlsx"
    _write_xlsx(
        file_path,
        rows=[
            ["order_id", "sku", "quantity"],
            ["1001", "SKU-1", 2],
            ["1002", "SKU-2", 1],
        ],
    )

    dataset = PandasDatasetReader().read(file_path, _limits())

    assert dataset.metadata.file_type is DatasetFileType.XLSX
    assert dataset.metadata.row_count == 2
    assert dataset.metadata.column_names == ("order_id", "sku", "quantity")
    assert dataset.records[1]["sku"] == "SKU-2"


def test_rejects_unsupported_file_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.json"
    file_path.write_text("[]", encoding="utf-8")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "unsupported_file_type"


def test_rejects_malformed_csv_file(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text('order_id,total\n"1001,25.50\n', encoding="utf-8")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "parse_error"


def test_rejects_malformed_xlsx_file(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.xlsx"
    file_path.write_text("not an excel workbook", encoding="utf-8")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "parse_error"


def test_rejects_empty_dataset_with_headers_only(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text("order_id,total\n", encoding="utf-8")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "empty_dataset"


def test_rejects_missing_header(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text("order_id,\n1001,25.50\n", encoding="utf-8")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "missing_header"


def test_rejects_duplicate_column_names(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text("order_id,order_id,total\n1001,duplicate,25.50\n", encoding="utf-8")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "duplicate_columns"


def test_rejects_csv_encoding_errors(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, _limits())

    assert exc_info.value.code == "encoding_error"


def test_rejects_files_over_configured_size_limit(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text("order_id,total\n1001,25.50\n", encoding="utf-8")
    limits = DatasetIngestionLimits(max_file_size_bytes=1)

    with pytest.raises(DatasetIngestionError) as exc_info:
        PandasDatasetReader().read(file_path, limits)

    assert exc_info.value.code == "file_too_large"


def test_preserves_column_names_with_parsing_warning_for_whitespace(tmp_path: Path) -> None:
    file_path = tmp_path / "orders.csv"
    file_path.write_text(" order_id ,total\n1001,25.50\n", encoding="utf-8")

    dataset = PandasDatasetReader().read(file_path, _limits())

    assert dataset.metadata.column_names == (" order_id ", "total")
    assert dataset.records[0][" order_id "] == 1001
    assert dataset.metadata.parsing_warnings == (
        "One or more column names contain leading or trailing whitespace.",
    )


def _limits() -> DatasetIngestionLimits:
    return DatasetIngestionLimits(max_file_size_bytes=1024 * 1024)


def _write_xlsx(file_path: Path, *, rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    workbook.save(file_path)
    workbook.close()
