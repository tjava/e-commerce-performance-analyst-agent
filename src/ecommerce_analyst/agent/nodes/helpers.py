"""Shared helpers for thin LangGraph nodes."""

from __future__ import annotations

from collections.abc import Iterable

from ecommerce_analyst.agent.state import (
    AnalysisState,
    WorkflowError,
    WorkflowMetadata,
    WorkflowStage,
    WorkflowStatus,
)


def append_completed_stage(state: AnalysisState, stage: WorkflowStage) -> WorkflowMetadata:
    """Return workflow metadata with an appended completed stage."""

    metadata = state.get("metadata", WorkflowMetadata())
    return metadata.model_copy(update={"completed_stages": (*metadata.completed_stages, stage)})


def append_error(
    state: AnalysisState,
    *,
    stage: WorkflowStage,
    message: str,
    code: str,
) -> tuple[WorkflowError, ...]:
    """Return existing workflow errors plus a controlled error."""

    return (
        *state.get("errors", ()),
        WorkflowError(stage=stage, message=message, code=code),
    )


def append_warnings(state: AnalysisState, warnings: Iterable[str]) -> tuple[str, ...]:
    """Return existing workflow warnings plus new warnings."""

    return (*state.get("warnings", ()), *tuple(warnings))


def failure_update(state: AnalysisState, *, stage: WorkflowStage, exc: Exception) -> AnalysisState:
    """Build a controlled failure state update from an unexpected exception."""

    return {
        "workflow_status": WorkflowStatus.FAILED,
        "current_stage": stage,
        "errors": append_error(
            state,
            stage=stage,
            message=str(exc) or exc.__class__.__name__,
            code=exc.__class__.__name__,
        ),
        "metadata": append_completed_stage(state, stage),
    }
