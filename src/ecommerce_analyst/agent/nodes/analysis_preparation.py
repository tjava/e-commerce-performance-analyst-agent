"""LangGraph node for placeholder analysis preparation."""

from __future__ import annotations

from ecommerce_analyst.agent.nodes.helpers import append_completed_stage, failure_update
from ecommerce_analyst.agent.state import (
    AnalysisPreparationResult,
    AnalysisState,
    WorkflowStage,
    WorkflowStatus,
)


def prepare_analysis(state: AnalysisState) -> AnalysisState:
    """Prepare a structured placeholder for future analysis planning."""

    stage = WorkflowStage.ANALYSIS_PREPARATION
    try:
        validation = state["domain_validation"]
        quality_report = state["quality_report"]
        preparation = AnalysisPreparationResult(
            ready_for_analysis=True,
            available_capabilities=quality_report.available_capabilities,
            unavailable_capabilities=validation.unavailable_capabilities,
            message=(
                "Analysis preparation completed; deterministic analysis is not implemented yet."
            ),
        )
    except Exception as exc:
        return failure_update(state, stage=stage, exc=exc)

    return {
        "analysis_preparation": preparation,
        "capabilities": preparation.available_capabilities,
        "workflow_status": WorkflowStatus.COMPLETED,
        "current_stage": stage,
        "metadata": append_completed_stage(state, stage),
    }
