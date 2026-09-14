"""LangGraph builder for the initial analysis workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from ecommerce_analyst.agent.graph.routes import (
    route_after_profiling,
    route_after_quality,
    route_after_validation,
)
from ecommerce_analyst.agent.nodes import (
    AnalysisWorkflowServices,
    assess_quality,
    create_profile_dataset_node,
    create_validate_domain_node,
    prepare_analysis,
)
from ecommerce_analyst.agent.state import AnalysisState, create_initial_analysis_state
from ecommerce_analyst.domain.models import IngestedDataset

CompiledAnalysisGraph = Any


def build_analysis_graph(
    services: AnalysisWorkflowServices | None = None,
) -> CompiledAnalysisGraph:
    """Build and compile the initial LangGraph analysis workflow."""

    resolved_services = services or AnalysisWorkflowServices()
    graph = StateGraph(AnalysisState)

    graph.add_node("validate_domain", cast(Any, create_validate_domain_node(resolved_services)))
    graph.add_node("profile_dataset", cast(Any, create_profile_dataset_node(resolved_services)))
    graph.add_node("assess_quality", cast(Any, assess_quality))
    graph.add_node("prepare_analysis", cast(Any, prepare_analysis))

    graph.add_edge(START, "validate_domain")
    graph.add_conditional_edges(
        "validate_domain",
        route_after_validation,
        {
            "accept": "profile_dataset",
            "reject": END,
            "error": END,
        },
    )
    graph.add_conditional_edges(
        "profile_dataset",
        route_after_profiling,
        {
            "profiled": "assess_quality",
            "error": END,
        },
    )
    graph.add_conditional_edges(
        "assess_quality",
        route_after_quality,
        {
            "usable": "prepare_analysis",
            "unsuitable": END,
            "error": END,
        },
    )
    graph.add_edge("prepare_analysis", END)

    return graph.compile()


def run_analysis_workflow(
    dataset: IngestedDataset,
    *,
    graph_factory: Callable[[], CompiledAnalysisGraph] = build_analysis_graph,
) -> AnalysisState:
    """Run the initial analysis workflow for an already ingested dataset."""

    graph = graph_factory()
    result = graph.invoke(create_initial_analysis_state(dataset))
    return cast(AnalysisState, result)
