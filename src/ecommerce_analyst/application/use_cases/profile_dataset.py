"""Application use case for profiling an ingested dataset."""

from __future__ import annotations

from dataclasses import dataclass, field

from ecommerce_analyst.application.services.dataset_profiling_service import (
    DatasetProfilingService,
)
from ecommerce_analyst.domain.models.dataset import IngestedDataset
from ecommerce_analyst.domain.profiling.result import DatasetProfile
from ecommerce_analyst.domain.validation.result import DomainValidationResult


@dataclass(frozen=True, slots=True)
class ProfileDatasetUseCase:
    """Produce a domain-aware profile and quality assessment of an ingested dataset.

    Coordinates between DatasetProfilingService and the analytical domain types.
    """

    service: DatasetProfilingService = field(default_factory=DatasetProfilingService)

    def execute(
        self,
        dataset: IngestedDataset,
        validation_result: DomainValidationResult,
    ) -> DatasetProfile:
        """Profile an ingested dataset and evaluate its quality."""
        return self.service.profile(dataset, validation_result)
