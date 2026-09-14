"""LangGraph node for dataset profiling orchestration."""

from __future__ import annotations

from collections.abc import Callable

from ecommerce_analyst.agent.nodes.dependencies import AnalysisWorkflowServices
from ecommerce_analyst.agent.nodes.helpers import (
    append_completed_stage,
    append_warnings,
    failure_update,
)
from ecommerce_analyst.agent.state import AnalysisState, WorkflowStage, WorkflowStatus


def create_profile_dataset_node(
    services: AnalysisWorkflowServices,
) -> Callable[[AnalysisState], AnalysisState]:
    """Create a profiling node bound to application use cases."""

    def profile_dataset(state: AnalysisState) -> AnalysisState:
        stage = WorkflowStage.DATA_PROFILING
        try:
            profile = services.profile_dataset.execute(
                state["dataset"],
                state["domain_validation"],
            )
        except Exception as exc:
            return failure_update(state, stage=stage, exc=exc)

        return {
            "data_profile": profile,
            "workflow_status": WorkflowStatus.RUNNING,
            "current_stage": stage,
            "warnings": append_warnings(state, profile.profiling_warnings),
            "metadata": append_completed_stage(state, stage),
        }

    return profile_dataset
