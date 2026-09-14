"""Dependencies used by LangGraph workflow nodes."""

from __future__ import annotations

from dataclasses import dataclass, field

from ecommerce_analyst.application.use_cases.profile_dataset import ProfileDatasetUseCase
from ecommerce_analyst.application.use_cases.validate_dataset import ValidateDatasetUseCase


@dataclass(frozen=True, slots=True)
class AnalysisWorkflowServices:
    """Application use cases available to workflow nodes."""

    validate_dataset: ValidateDatasetUseCase = field(default_factory=ValidateDatasetUseCase)
    profile_dataset: ProfileDatasetUseCase = field(default_factory=ProfileDatasetUseCase)
