"""LangGraph node for workflow-level quality assessment."""

from __future__ import annotations

from ecommerce_analyst.agent.nodes.helpers import (
    append_completed_stage,
    append_warnings,
    failure_update,
)
from ecommerce_analyst.agent.state import (
    AnalysisState,
    DataQualityReport,
    QualitySuitability,
    WorkflowStage,
    WorkflowStatus,
)


def assess_quality(state: AnalysisState) -> AnalysisState:
    """Derive a workflow quality report from the deterministic dataset profile."""

    stage = WorkflowStage.QUALITY_ASSESSMENT
    try:
        report = DataQualityReport.from_profile(state["data_profile"])
    except Exception as exc:
        return failure_update(state, stage=stage, exc=exc)

    status = (
        WorkflowStatus.UNSUITABLE
        if report.suitability is QualitySuitability.UNSUITABLE
        else WorkflowStatus.RUNNING
    )
    return {
        "quality_report": report,
        "capabilities": report.available_capabilities,
        "workflow_status": status,
        "current_stage": stage,
        "warnings": append_warnings(state, report.warnings),
        "metadata": append_completed_stage(state, stage),
    }
