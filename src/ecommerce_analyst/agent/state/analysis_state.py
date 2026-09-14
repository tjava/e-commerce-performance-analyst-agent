"""Typed LangGraph state for the analysis workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TypedDict
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_analyst.domain.models import IngestedDataset
from ecommerce_analyst.domain.profiling.enums import QualityIssueSeverity
from ecommerce_analyst.domain.profiling.result import DatasetProfile, QualityIssue
from ecommerce_analyst.domain.validation.enums import EcommerceCapability
from ecommerce_analyst.domain.validation.result import DomainValidationResult


class WorkflowStatus(StrEnum):
    """Top-level status for the analysis workflow."""

    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    REJECTED = "rejected"
    UNSUITABLE = "unsuitable"
    FAILED = "failed"


class WorkflowStage(StrEnum):
    """Workflow stages executed by the initial LangGraph graph."""

    INITIALIZED = "initialized"
    DOMAIN_VALIDATION = "domain_validation"
    DATA_PROFILING = "data_profiling"
    QUALITY_ASSESSMENT = "quality_assessment"
    ANALYSIS_PREPARATION = "analysis_preparation"
    END = "end"


class QualitySuitability(StrEnum):
    """Workflow-level quality decision derived from a dataset profile."""

    USABLE = "usable"
    UNSUITABLE = "unsuitable"


class WorkflowError(BaseModel):
    """Controlled workflow error captured in state."""

    stage: WorkflowStage
    message: str = Field(min_length=1)
    code: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class WorkflowMetadata(BaseModel):
    """Execution metadata that is separate from domain results."""

    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_stages: tuple[WorkflowStage, ...] = ()

    model_config = ConfigDict(frozen=True)


class DataQualityReport(BaseModel):
    """Workflow-level quality summary derived from DatasetProfile."""

    suitability: QualitySuitability
    issues: tuple[QualityIssue, ...]
    blocking_issue_count: int = Field(ge=0)
    warning_issue_count: int = Field(ge=0)
    available_capabilities: tuple[EcommerceCapability, ...]
    warnings: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True)

    @property
    def is_usable(self) -> bool:
        """Return True when no blocking quality issue terminates the workflow."""

        return self.suitability is QualitySuitability.USABLE

    @classmethod
    def from_profile(cls, profile: DatasetProfile) -> DataQualityReport:
        """Build a workflow quality report from a deterministic dataset profile."""

        blocking_count = sum(
            1 for issue in profile.quality_issues if issue.severity is QualityIssueSeverity.BLOCKING
        )
        warning_count = sum(
            1 for issue in profile.quality_issues if issue.severity is QualityIssueSeverity.WARNING
        )
        suitability = (
            QualitySuitability.UNSUITABLE if blocking_count > 0 else QualitySuitability.USABLE
        )
        return cls(
            suitability=suitability,
            issues=profile.quality_issues,
            blocking_issue_count=blocking_count,
            warning_issue_count=warning_count,
            available_capabilities=profile.available_capabilities,
            warnings=profile.profiling_warnings,
        )


class AnalysisPreparationResult(BaseModel):
    """Placeholder result for future analysis planning milestones."""

    ready_for_analysis: bool
    available_capabilities: tuple[EcommerceCapability, ...]
    unavailable_capabilities: tuple[EcommerceCapability, ...]
    message: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class AnalysisState(TypedDict, total=False):
    """State shape carried through the LangGraph workflow."""

    dataset: IngestedDataset
    domain_validation: DomainValidationResult
    data_profile: DatasetProfile
    quality_report: DataQualityReport
    capabilities: tuple[EcommerceCapability, ...]
    analysis_preparation: AnalysisPreparationResult
    workflow_status: WorkflowStatus
    current_stage: WorkflowStage
    errors: tuple[WorkflowError, ...]
    warnings: tuple[str, ...]
    metadata: WorkflowMetadata


def create_initial_analysis_state(dataset: IngestedDataset) -> AnalysisState:
    """Create initial workflow state for a newly ingested dataset."""

    return {
        "dataset": dataset,
        "workflow_status": WorkflowStatus.INITIALIZED,
        "current_stage": WorkflowStage.INITIALIZED,
        "errors": (),
        "warnings": dataset.metadata.parsing_warnings,
        "metadata": WorkflowMetadata(),
    }
