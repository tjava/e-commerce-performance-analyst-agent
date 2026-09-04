"""Pydantic result models for the dataset profiling and data quality layer.

All models are frozen and JSON-serialisable so they can be passed between
application layers, stored, or logged without mutation risk.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_analyst.domain.profiling.enums import (
    ColumnRole,
    QualityIssueCode,
    QualityIssueSeverity,
)
from ecommerce_analyst.domain.validation.enums import EcommerceCapability


class QualityIssue(BaseModel):
    """A single detected data quality problem."""

    column: str | None = None
    """Column this issue relates to, or None for dataset-level issues."""

    code: QualityIssueCode
    """Machine-readable issue identifier."""

    severity: QualityIssueSeverity
    """Impact level on downstream analysis."""

    message: str = Field(min_length=1)
    """Human-readable description of the issue and its potential impact."""

    affected_row_count: int = Field(ge=0, default=0)
    """Number of rows affected by this issue (0 if not applicable)."""

    affected_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    """Percentage of rows affected, in range [0.0, 100.0]."""

    model_config = ConfigDict(frozen=True)


class NumericStats(BaseModel):
    """Descriptive statistics for a numeric column."""

    min_value: float
    max_value: float
    mean: float
    median: float
    std: float
    p25: float
    p75: float
    zero_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class DateRangeStats(BaseModel):
    """Statistics for a date/timestamp column."""

    min_date: str | None = None
    """ISO-format earliest date, or None if all values are unparseable."""

    max_date: str | None = None
    """ISO-format latest date, or None if all values are unparseable."""

    date_span_days: int | None = None
    """Calendar days between earliest and latest date."""

    unparseable_count: int = Field(ge=0, default=0)
    """Number of values that could not be parsed as dates."""

    future_date_count: int = Field(ge=0, default=0)
    """Number of dates later than the profiling timestamp."""

    model_config = ConfigDict(frozen=True)


class CategoricalStats(BaseModel):
    """Statistics for a low-to-medium cardinality string column."""

    unique_count: int = Field(ge=0)
    """Number of distinct non-null values."""

    null_count: int = Field(ge=0)
    """Number of null values."""

    top_values: tuple[tuple[str, int], ...]
    """Top N (value, frequency) pairs in descending frequency order."""

    model_config = ConfigDict(frozen=True)


class ColumnProfile(BaseModel):
    """Full profile for a single dataset column."""

    name: str = Field(min_length=1)
    """Original column name as loaded from the dataset."""

    index: int = Field(ge=0)
    """Zero-based column position."""

    inferred_dtype: str = Field(min_length=1)
    """Pandas-inferred dtype string from ingestion."""

    role: ColumnRole
    """Semantic e-commerce role assigned to this column."""

    null_count: int = Field(ge=0)
    """Absolute number of null/NaN values."""

    null_pct: float = Field(ge=0.0, le=100.0)
    """Percentage of null values in [0.0, 100.0]."""

    unique_count: int = Field(ge=0)
    """Number of distinct non-null values."""

    is_constant: bool
    """True when every non-null value is identical."""

    numeric_stats: NumericStats | None = None
    """Populated when the column is numeric."""

    date_stats: DateRangeStats | None = None
    """Populated when the column is or resembles a date column."""

    categorical_stats: CategoricalStats | None = None
    """Populated for string/object columns with manageable cardinality."""

    model_config = ConfigDict(frozen=True)


class DatasetOverview(BaseModel):
    """High-level shape and duplication summary for the dataset."""

    filename: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    duplicate_row_pct: float = Field(ge=0.0, le=100.0)
    file_size_bytes: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class CapabilityAssessment(BaseModel):
    """Refined assessment of a single analytical capability after profiling.

    Extends the signal-based assessment from Milestone 3 with data-quality
    evidence. The ``available`` flag from M3 can only be kept or downgraded
    here — never upgraded.
    """

    capability: EcommerceCapability
    available: bool
    """False if M3 said unavailable, or if quality issues make it unusable."""

    limiting_issues: tuple[QualityIssueCode, ...]
    """Quality issue codes that degrade or block this capability."""

    confidence_note: str
    """Short human-readable note on data quality for this capability."""

    model_config = ConfigDict(frozen=True)


class DatasetProfile(BaseModel):
    """Complete structured profile of an accepted e-commerce dataset.

    Produced by ``DatasetProfilingService`` and consumed by the Analysis Planner
    in Milestone 5.  Contains no computed business metrics — only schema info,
    column statistics, quality issues, and capability assessments.
    """

    overview: DatasetOverview
    """High-level dataset dimensions and duplication summary."""

    column_profiles: tuple[ColumnProfile, ...]
    """One profile entry per column, in load order."""

    quality_issues: tuple[QualityIssue, ...]
    """All detected quality issues, ordered by severity (BLOCKING first)."""

    capability_assessments: tuple[CapabilityAssessment, ...]
    """Refined capability flags incorporating data quality evidence."""

    analytical_dimensions: tuple[str, ...]
    """Column names safe to use as group-by dimensions in analyses."""

    profiling_warnings: tuple[str, ...]
    """Non-issue observations about the profiling run itself."""

    profiled_at: datetime
    """UTC timestamp when this profile was produced."""

    model_config = ConfigDict(frozen=True)

    @property
    def blocking_issues(self) -> tuple[QualityIssue, ...]:
        """Return only BLOCKING quality issues."""
        return tuple(i for i in self.quality_issues if i.severity is QualityIssueSeverity.BLOCKING)

    @property
    def has_blocking_issues(self) -> bool:
        """True when at least one BLOCKING issue was detected."""
        return bool(self.blocking_issues)

    @property
    def available_capabilities(self) -> tuple[EcommerceCapability, ...]:
        """Return capabilities marked available after quality assessment."""
        return tuple(a.capability for a in self.capability_assessments if a.available)

    @property
    def column_roles(self) -> dict[str, ColumnRole]:
        """Return a mapping of column name → assigned role."""
        return {cp.name: cp.role for cp in self.column_profiles}
