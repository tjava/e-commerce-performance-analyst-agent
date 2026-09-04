"""Dataset profiling application service.

Coordinates the profiling of an ingested, validated dataset using the analytics
profiler engine and returns a structured DatasetProfile.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ecommerce_analyst.analytics.engines.dataset_profiler import DatasetProfiler
from ecommerce_analyst.domain.models.dataset import IngestedDataset
from ecommerce_analyst.domain.profiling.result import DatasetProfile
from ecommerce_analyst.domain.validation.result import DomainValidationResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DatasetProfilingService:
    """Application service for profiling datasets and evaluating data quality."""

    profiler: DatasetProfiler = field(default_factory=DatasetProfiler)

    def profile(
        self,
        dataset: IngestedDataset,
        validation_result: DomainValidationResult,
    ) -> DatasetProfile:
        """Profile an ingested dataset given its domain validation result."""
        logger.debug(
            "Profiling dataset",
            extra={"filename": dataset.metadata.filename},
        )
        return self.profiler.profile(dataset, validation_result)
