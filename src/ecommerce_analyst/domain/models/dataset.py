"""Domain-neutral dataset models produced by ingestion."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from ecommerce_analyst.domain.enums.dataset_file_type import DatasetFileType

type CellValue = str | int | float | bool | date | datetime | None


class ColumnMetadata(BaseModel):
    """Technical metadata for a loaded dataset column."""

    index: int = Field(ge=0)
    name: str = Field(min_length=1)
    inferred_dtype: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class DatasetMetadata(BaseModel):
    """Technical metadata collected during dataset ingestion."""

    filename: str = Field(min_length=1)
    file_type: DatasetFileType
    file_size_bytes: int = Field(ge=0)
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: tuple[ColumnMetadata, ...]
    parsing_warnings: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True)

    @property
    def column_names(self) -> tuple[str, ...]:
        """Return column names in their loaded order."""

        return tuple(column.name for column in self.columns)


class IngestedDataset(BaseModel):
    """Format-independent representation of an uploaded tabular dataset."""

    metadata: DatasetMetadata
    records: list[dict[str, CellValue]]

    model_config = ConfigDict(frozen=True)


class DatasetIngestionLimits(BaseModel):
    """Configurable technical limits for uploaded dataset ingestion."""

    max_file_size_bytes: PositiveInt
    supported_file_types: tuple[DatasetFileType, ...] = (
        DatasetFileType.CSV,
        DatasetFileType.XLSX,
    )

    model_config = ConfigDict(frozen=True)
