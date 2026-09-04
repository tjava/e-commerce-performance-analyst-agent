"""Dataset profiling domain package.

Exports the public surface needed by analytics and application layers.
"""

from ecommerce_analyst.domain.profiling.enums import (
    ColumnRole,
    QualityIssueCode,
    QualityIssueSeverity,
)
from ecommerce_analyst.domain.profiling.result import (
    CapabilityAssessment,
    CategoricalStats,
    ColumnProfile,
    DatasetOverview,
    DatasetProfile,
    DateRangeStats,
    NumericStats,
    QualityIssue,
)

__all__ = [
    "CapabilityAssessment",
    "CategoricalStats",
    "ColumnProfile",
    "ColumnRole",
    "DatasetOverview",
    "DatasetProfile",
    "DateRangeStats",
    "NumericStats",
    "QualityIssue",
    "QualityIssueCode",
    "QualityIssueSeverity",
]
