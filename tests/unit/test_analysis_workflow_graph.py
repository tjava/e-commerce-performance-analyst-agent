from __future__ import annotations

from typing import cast

from ecommerce_analyst.agent.graph import (
    build_analysis_graph,
    route_after_profiling,
    route_after_quality,
    route_after_validation,
    run_analysis_workflow,
)
from ecommerce_analyst.agent.nodes import AnalysisWorkflowServices
from ecommerce_analyst.agent.state import (
    AnalysisState,
    DataQualityReport,
    QualitySuitability,
    WorkflowStage,
    WorkflowStatus,
    create_initial_analysis_state,
)
from ecommerce_analyst.application.services.dataset_profiling_service import (
    DatasetProfilingService,
)
from ecommerce_analyst.application.use_cases.profile_dataset import ProfileDatasetUseCase
from ecommerce_analyst.domain.models import IngestedDataset
from ecommerce_analyst.domain.profiling.result import DatasetProfile
from ecommerce_analyst.domain.validation.enums import ValidationDecision
from tests.fixtures.dataset_builders import make_ecommerce_dataset, make_ingested_dataset


def test_valid_ecommerce_dataset_reaches_analysis_preparation() -> None:
    final_state = _run(make_ecommerce_dataset(row_count=8))

    assert final_state["workflow_status"] is WorkflowStatus.COMPLETED
    assert final_state["domain_validation"].decision is ValidationDecision.PASS
    assert "data_profile" in final_state
    assert "quality_report" in final_state
    assert final_state["quality_report"].suitability is QualitySuitability.USABLE
    assert final_state["analysis_preparation"].ready_for_analysis is True
    assert final_state["metadata"].completed_stages == (
        WorkflowStage.DOMAIN_VALIDATION,
        WorkflowStage.DATA_PROFILING,
        WorkflowStage.QUALITY_ASSESSMENT,
        WorkflowStage.ANALYSIS_PREPARATION,
    )


def test_non_ecommerce_dataset_is_rejected_before_profiling() -> None:
    dataset = make_ingested_dataset(
        columns=[
            ("employee_id", "object"),
            ("name", "object"),
            ("department", "object"),
            ("salary", "float64"),
            ("hire_date", "datetime64[ns]"),
        ],
    )

    final_state = _run(dataset)

    assert final_state["workflow_status"] is WorkflowStatus.REJECTED
    assert final_state["domain_validation"].decision is ValidationDecision.REJECT
    assert "data_profile" not in final_state
    assert "quality_report" not in final_state
    assert "analysis_preparation" not in final_state
    assert final_state["metadata"].completed_stages == (WorkflowStage.DOMAIN_VALIDATION,)


def test_ecommerce_dataset_with_warnings_continues_to_preparation() -> None:
    dataset = make_ecommerce_dataset(row_count=5)
    dataset = dataset.model_copy(
        update={
            "metadata": dataset.metadata.model_copy(update={"parsing_warnings": ("csv warning",)})
        }
    )

    final_state = _run(dataset)

    assert final_state["workflow_status"] is WorkflowStatus.COMPLETED
    assert final_state["analysis_preparation"].ready_for_analysis is True
    assert "csv warning" in final_state["warnings"]


def test_unsuitable_dataset_terminates_after_quality_assessment() -> None:
    dataset = make_ecommerce_dataset(
        records=[
            {
                "order_id": 1000 + index,
                "product_id": "PROD-1",
                "price": 10.0 if index == 0 else None,
                "quantity": 1,
                "order_date": "2024-01-01",
                "customer_id": "CUST-1",
                "category": "Electronics",
            }
            for index in range(10)
        ],
    )

    final_state = _run(dataset)

    assert final_state["workflow_status"] is WorkflowStatus.UNSUITABLE
    assert final_state["quality_report"].suitability is QualitySuitability.UNSUITABLE
    assert final_state["quality_report"].blocking_issue_count > 0
    assert "analysis_preparation" not in final_state
    assert final_state["metadata"].completed_stages == (
        WorkflowStage.DOMAIN_VALIDATION,
        WorkflowStage.DATA_PROFILING,
        WorkflowStage.QUALITY_ASSESSMENT,
    )


def test_profiling_failure_is_captured_and_terminates_cleanly() -> None:
    services = AnalysisWorkflowServices(
        profile_dataset=ProfileDatasetUseCase(
            service=cast(DatasetProfilingService, FailingProfiler())
        )
    )
    graph = build_analysis_graph(services)

    final_state = cast(
        AnalysisState, graph.invoke(create_initial_analysis_state(make_ecommerce_dataset()))
    )

    assert final_state["workflow_status"] is WorkflowStatus.FAILED
    assert final_state["current_stage"] is WorkflowStage.DATA_PROFILING
    assert "data_profile" not in final_state
    assert "quality_report" not in final_state
    assert final_state["errors"][0].stage is WorkflowStage.DATA_PROFILING
    assert final_state["errors"][0].code == "RuntimeError"


def test_state_integrity_preserves_previous_results_across_nodes() -> None:
    final_state = _run(make_ecommerce_dataset(row_count=6))

    assert final_state["domain_validation"].is_accepted
    assert final_state["data_profile"].overview.row_count == 6
    assert final_state["quality_report"].is_usable
    assert final_state["analysis_preparation"].available_capabilities == final_state["capabilities"]


def test_validation_routes_are_deterministic() -> None:
    accepted_state = _run(make_ecommerce_dataset())
    rejected_state = _run(
        make_ingested_dataset(
            columns=[
                ("employee_id", "object"),
                ("department", "object"),
                ("salary", "float64"),
            ],
        )
    )

    assert route_after_validation(accepted_state) == "accept"
    assert route_after_validation(rejected_state) == "reject"
    assert route_after_validation({"workflow_status": WorkflowStatus.FAILED}) == "error"
    assert route_after_validation({}) == "error"


def test_profiling_routes_are_deterministic() -> None:
    profiled_state = _run(make_ecommerce_dataset())

    assert route_after_profiling(profiled_state) == "profiled"
    assert route_after_profiling({"workflow_status": WorkflowStatus.FAILED}) == "error"
    assert route_after_profiling({}) == "error"


def test_quality_routes_are_deterministic() -> None:
    usable_state = _run(make_ecommerce_dataset())
    unsuitable_report = DataQualityReport(
        suitability=QualitySuitability.UNSUITABLE,
        issues=(),
        blocking_issue_count=1,
        warning_issue_count=0,
        available_capabilities=(),
    )

    assert route_after_quality(usable_state) == "usable"
    assert route_after_quality({"quality_report": unsuitable_report}) == "unsuitable"
    assert route_after_quality({"workflow_status": WorkflowStatus.FAILED}) == "error"
    assert route_after_quality({}) == "error"


def test_same_dataset_produces_equivalent_structured_results() -> None:
    dataset = make_ecommerce_dataset(row_count=7)

    first_state = _run(dataset)
    second_state = _run(dataset)

    assert first_state["workflow_status"] == second_state["workflow_status"]
    assert first_state["domain_validation"] == second_state["domain_validation"]
    assert first_state["data_profile"].model_dump(exclude={"profiled_at"}) == second_state[
        "data_profile"
    ].model_dump(exclude={"profiled_at"})
    assert first_state["quality_report"] == second_state["quality_report"]
    assert first_state["analysis_preparation"] == second_state["analysis_preparation"]


class FailingProfiler:
    def profile(
        self,
        dataset: IngestedDataset,
        validation_result: object,
    ) -> DatasetProfile:
        raise RuntimeError("profiling unavailable")


def _run(dataset: IngestedDataset) -> AnalysisState:
    return run_analysis_workflow(dataset)
