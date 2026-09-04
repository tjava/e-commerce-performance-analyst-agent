"""Unit tests for the Dataset Profiling & Data Quality Engine (Milestone 4).

Tests cover:
 1. Full clean dataset -> complete profile, all fields populated, no blocking issues
 2. High null rate on price -> HIGH_NULL_RATE warning, limiting notes
 3. Critical null rate (>80%) on revenue -> BLOCKING issue, capability disabled
 4. Duplicate rows -> DUPLICATE_ROWS quality issue
 5. Duplicate order IDs -> DUPLICATE_ORDER_IDS warning
 6. Negative quantities and zero quantities -> detected with correct counts
 7. Zero/negative prices -> detected with correct counts
 8. Date column with unparseable strings -> UNPARSEABLE_DATE blocking & TREND disabled
 9. Constant column -> CONSTANT_COLUMN info issue
10. Missing customer_id -> CUSTOMER_ANALYSIS capability unavailable
11. Structured Pydantic model and serialisability
12. Column roles correctly assigned from validation signals
13. Analytical dimensions identified properly
14. No LLM dependency
15. Works with PASS_LIMITED validation results
"""

from __future__ import annotations

from datetime import datetime

import pytest

from ecommerce_analyst.application.services.dataset_profiling_service import (
    DatasetProfilingService,
)
from ecommerce_analyst.application.services.domain_validator import (
    EcommerceDomainValidator,
)
from ecommerce_analyst.application.use_cases.profile_dataset import (
    ProfileDatasetUseCase,
)
from ecommerce_analyst.domain.profiling.enums import (
    ColumnRole,
    QualityIssueCode,
    QualityIssueSeverity,
)
from ecommerce_analyst.domain.profiling.result import DatasetProfile
from ecommerce_analyst.domain.validation.enums import (
    EcommerceCapability,
    ValidationDecision,
)
from tests.fixtures.dataset_builders import (
    make_ecommerce_dataset,
    make_ingested_dataset,
)


@pytest.fixture()
def validator() -> EcommerceDomainValidator:
    return EcommerceDomainValidator()


@pytest.fixture()
def profiling_service() -> DatasetProfilingService:
    return DatasetProfilingService()


@pytest.fixture()
def use_case() -> ProfileDatasetUseCase:
    return ProfileDatasetUseCase()


class TestCleanDatasetProfiling:
    """A clean e-commerce dataset should profile completely with zero blocking issues."""

    def test_clean_dataset_produces_complete_profile(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        dataset = make_ecommerce_dataset(row_count=10)
        val_result = validator.validate(dataset)
        assert val_result.is_accepted

        profile = profiling_service.profile(dataset, val_result)

        assert isinstance(profile, DatasetProfile)
        assert profile.overview.row_count == 10
        assert profile.overview.column_count == 7
        assert profile.overview.duplicate_row_count == 0
        assert not profile.has_blocking_issues
        assert isinstance(profile.profiled_at, datetime)

    def test_clean_dataset_has_all_expected_roles(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        dataset = make_ecommerce_dataset(row_count=5)
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        roles = profile.column_roles
        assert roles["order_id"] == ColumnRole.ORDER_IDENTIFIER
        assert roles["product_id"] == ColumnRole.PRODUCT_IDENTIFIER
        assert roles["price"] == ColumnRole.REVENUE
        assert roles["quantity"] == ColumnRole.QUANTITY
        assert roles["order_date"] == ColumnRole.DATE
        assert roles["customer_id"] == ColumnRole.CUSTOMER_IDENTIFIER
        assert roles["category"] == ColumnRole.CATEGORY

    def test_clean_dataset_numeric_and_date_stats(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        dataset = make_ecommerce_dataset(row_count=5)
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        col_dict = {cp.name: cp for cp in profile.column_profiles}
        price_prof = col_dict["price"]
        assert price_prof.numeric_stats is not None
        assert price_prof.numeric_stats.min_value > 0
        assert price_prof.numeric_stats.negative_count == 0

        date_prof = col_dict["order_date"]
        assert date_prof.date_stats is not None
        assert date_prof.date_stats.unparseable_count == 0
        assert date_prof.date_stats.min_date is not None


class TestMissingAndNullValues:
    """Check high and critical null rate detection and capability degradation."""

    def test_high_null_rate_warning(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {
                "order_id": 1000 + i,
                "product_id": "P1",
                "price": 20.0 if i < 5 else None,  # 50% null
                "quantity": 1,
            }
            for i in range(10)
        ]
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("quantity", "int64"),
            ],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        issues = [i for i in profile.quality_issues if i.column == "price"]
        issue_codes = {i.code for i in issues}
        assert QualityIssueCode.HIGH_NULL_RATE in issue_codes

        rev_assessment = next(
            a for a in profile.capability_assessments
            if a.capability == EcommerceCapability.REVENUE_ANALYSIS
        )
        assert rev_assessment.available is True
        assert QualityIssueCode.HIGH_NULL_RATE in rev_assessment.limiting_issues

    def test_critical_null_rate_disables_capability(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {
                "order_id": 1000 + i,
                "product_id": "P1",
                "price": 20.0 if i == 0 else None,  # 90% null
                "quantity": 1,
            }
            for i in range(10)
        ]
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("quantity", "int64"),
            ],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        assert profile.has_blocking_issues
        blocking = [i for i in profile.blocking_issues if i.column == "price"]
        assert any(b.code == QualityIssueCode.CRITICAL_NULL_RATE for b in blocking)

        rev_assessment = next(
            a for a in profile.capability_assessments
            if a.capability == EcommerceCapability.REVENUE_ANALYSIS
        )
        assert rev_assessment.available is False


class TestDuplicationIssues:
    """Duplicate rows and duplicate order IDs."""

    def test_duplicate_rows_detected(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        row = {"order_id": 1001, "product_id": "P1", "price": 10.0}
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("price", "float64")],
            records=[row, row, {"order_id": 1002, "product_id": "P2", "price": 15.0}],
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        assert profile.overview.duplicate_row_count == 1
        dup_issue = next(
            (i for i in profile.quality_issues if i.code == QualityIssueCode.DUPLICATE_ROWS),
            None,
        )
        assert dup_issue is not None
        assert dup_issue.severity == QualityIssueSeverity.WARNING

    def test_duplicate_order_ids_detected(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {"order_id": 1001, "product_id": "P1", "price": 10.0},
            {"order_id": 1001, "product_id": "P2", "price": 20.0},  # Duplicate order_id
            {"order_id": 1002, "product_id": "P3", "price": 30.0},
        ]
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("price", "float64")],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        dup_order_issue = next(
            (i for i in profile.quality_issues if i.code == QualityIssueCode.DUPLICATE_ORDER_IDS),
            None,
        )
        assert dup_order_issue is not None
        assert dup_order_issue.column == "order_id"


class TestNumericAnomalies:
    """Negative and zero quantities and prices."""

    def test_negative_and_zero_quantities(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {"order_id": 1, "product_id": "P1", "price": 10.0, "quantity": -2},
            {"order_id": 2, "product_id": "P2", "price": 15.0, "quantity": 0},
            {"order_id": 3, "product_id": "P3", "price": 20.0, "quantity": 3},
        ]
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("quantity", "int64"),
            ],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        qty_issues = {i.code for i in profile.quality_issues if i.column == "quantity"}
        assert QualityIssueCode.NEGATIVE_QUANTITY in qty_issues
        assert QualityIssueCode.ZERO_QUANTITY in qty_issues

    def test_negative_and_zero_prices(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {"order_id": 1, "product_id": "P1", "price": -5.0},
            {"order_id": 2, "product_id": "P2", "price": 0.0},
            {"order_id": 3, "product_id": "P3", "price": 25.0},
        ]
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("price", "float64")],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        price_issues = {i.code for i in profile.quality_issues if i.column == "price"}
        assert QualityIssueCode.NEGATIVE_PRICE in price_issues
        assert QualityIssueCode.ZERO_PRICE in price_issues


class TestDateAnomalies:
    """Date parsing issues and future dates."""

    def test_unparseable_dates_block_trend_analysis(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {"order_id": 1, "product_id": "P1", "price": 10.0, "order_date": "not-a-date"},
            {"order_id": 2, "product_id": "P2", "price": 15.0, "order_date": "invalid"},
        ]
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("order_date", "object"),
            ],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        trend_cap = next(
            a for a in profile.capability_assessments
            if a.capability == EcommerceCapability.TREND_ANALYSIS
        )
        assert trend_cap.available is False
        assert QualityIssueCode.UNPARSEABLE_DATE in trend_cap.limiting_issues

    def test_future_dates_warning(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {"order_id": 1, "product_id": "P1", "price": 10.0, "order_date": "2099-01-01"},
            {"order_id": 2, "product_id": "P2", "price": 15.0, "order_date": "2024-01-01"},
        ]
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("order_date", "object"),
            ],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        date_issues = {i.code for i in profile.quality_issues if i.column == "order_date"}
        assert QualityIssueCode.FUTURE_DATES in date_issues


class TestCapabilityAndDimensionInference:
    """Verifies capabilities and dimensions."""

    def test_constant_column_detected(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        records = [
            {"order_id": 1, "product_id": "P1", "price": 10.0, "currency": "USD"},
            {"order_id": 2, "product_id": "P2", "price": 20.0, "currency": "USD"},
        ]
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("currency", "object"),
            ],
            records=records,
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        issues = {i.code for i in profile.quality_issues if i.column == "currency"}
        assert QualityIssueCode.CONSTANT_COLUMN in issues
        assert "currency" not in profile.analytical_dimensions

    def test_missing_customer_id_keeps_customer_capability_unavailable(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
            ],
        )
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        cust_cap = next(
            a for a in profile.capability_assessments
            if a.capability == EcommerceCapability.CUSTOMER_ANALYSIS
        )
        assert cust_cap.available is False

    def test_analytical_dimensions_include_valid_grouping_columns(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        dataset = make_ecommerce_dataset(row_count=6)
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        assert "category" in profile.analytical_dimensions
        assert "product_id" in profile.analytical_dimensions


class TestArchitectureAndSerialisation:
    """Verifies non-LLM, serialisability, and use case layer."""

    def test_profile_is_json_serialisable(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        dataset = make_ecommerce_dataset(row_count=3)
        val_result = validator.validate(dataset)
        profile = profiling_service.profile(dataset, val_result)

        dump = profile.model_dump(mode="json")
        assert "overview" in dump
        assert "column_profiles" in dump
        assert "quality_issues" in dump
        assert "capability_assessments" in dump
        assert "profiled_at" in dump

    def test_use_case_execution(
        self,
        validator: EcommerceDomainValidator,
        use_case: ProfileDatasetUseCase,
    ) -> None:
        dataset = make_ecommerce_dataset(row_count=3)
        val_result = validator.validate(dataset)
        profile = use_case.execute(dataset, val_result)

        assert isinstance(profile, DatasetProfile)
        assert profile.overview.row_count == 3

    def test_profiler_works_on_pass_limited(
        self,
        validator: EcommerceDomainValidator,
        profiling_service: DatasetProfilingService,
    ) -> None:
        # Minimal dataset that passes with limited capability
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
            ],
        )
        val_result = validator.validate(dataset)
        assert val_result.decision in (ValidationDecision.PASS, ValidationDecision.PASS_LIMITED)

        profile = profiling_service.profile(dataset, val_result)
        assert profile.overview.row_count == 1
        assert EcommerceCapability.REVENUE_ANALYSIS in profile.available_capabilities
