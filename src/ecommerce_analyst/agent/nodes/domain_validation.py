"""LangGraph node for domain validation orchestration."""

from __future__ import annotations

from collections.abc import Callable

from ecommerce_analyst.agent.nodes.dependencies import AnalysisWorkflowServices
from ecommerce_analyst.agent.nodes.helpers import (
    append_completed_stage,
    append_warnings,
    failure_update,
)
from ecommerce_analyst.agent.state import AnalysisState, WorkflowStage, WorkflowStatus


def create_validate_domain_node(
    services: AnalysisWorkflowServices,
) -> Callable[[AnalysisState], AnalysisState]:
    """Create a domain-validation node bound to application use cases."""

    def validate_domain(state: AnalysisState) -> AnalysisState:
        stage = WorkflowStage.DOMAIN_VALIDATION
        try:
            result = services.validate_dataset.execute(state["dataset"])
        except Exception as exc:
            return failure_update(state, stage=stage, exc=exc)

        status = WorkflowStatus.RUNNING if result.is_accepted else WorkflowStatus.REJECTED
        return {
            "domain_validation": result,
            "workflow_status": status,
            "current_stage": stage,
            "warnings": append_warnings(state, result.warnings),
            "metadata": append_completed_stage(state, stage),
        }

    return validate_domain
