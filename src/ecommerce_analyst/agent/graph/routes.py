"""Conditional routing functions for the analysis workflow graph."""

from __future__ import annotations

from typing import Literal

from ecommerce_analyst.agent.state import AnalysisState, QualitySuitability, WorkflowStatus

ValidationRoute = Literal["accept", "reject", "error"]
ProfilingRoute = Literal["profiled", "error"]
QualityRoute = Literal["usable", "unsuitable", "error"]


def route_after_validation(state: AnalysisState) -> ValidationRoute:
    """Route after domain validation based on structured validation state."""

    if state.get("workflow_status") is WorkflowStatus.FAILED:
        return "error"

    validation_result = state.get("domain_validation")
    if validation_result is None:
        return "error"
    if validation_result.is_accepted:
        return "accept"
    return "reject"


def route_after_profiling(state: AnalysisState) -> ProfilingRoute:
    """Route after profiling, stopping controlled profiling failures."""

    if state.get("workflow_status") is WorkflowStatus.FAILED:
        return "error"
    if state.get("data_profile") is None:
        return "error"
    return "profiled"


def route_after_quality(state: AnalysisState) -> QualityRoute:
    """Route after quality assessment based on workflow-level suitability."""

    if state.get("workflow_status") is WorkflowStatus.FAILED:
        return "error"

    quality_report = state.get("quality_report")
    if quality_report is None:
        return "error"
    if quality_report.suitability is QualitySuitability.UNSUITABLE:
        return "unsuitable"
    return "usable"
