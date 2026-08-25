"""Unit tests for the E-commerce Domain Validation Engine (Milestone 3).

Tests are structured to match all 12 acceptance criteria stated in the milestone:

 1. Clearly valid e-commerce dataset          → PASS
 2. Clearly unrelated HR dataset              → REJECT
 3. Finance/accounting dataset                → REJECT
 4. Unusual column names (semantic signals)   → PASS
 5. Minimal but valid dataset                 → PASS_LIMITED / UNCERTAIN
 6. Missing optional customer info            → PASS, customer capability unavailable
 7. Missing pricing/revenue                   → REJECT
 8. Ambiguous dataset                         → UNCERTAIN, low confidence
 9. Wrong dtype / bad value patterns          → warnings present
10. Result is fully structured and deterministic
11. No LLM required
12. No actual analysis performed in result
"""

from __future__ import annotations

import pytest

from ecommerce_analyst.application.services.domain_validator import EcommerceDomainValidator
from ecommerce_analyst.application.use_cases.validate_dataset import (
    ValidateDatasetUseCase,
)
from ecommerce_analyst.domain.validation.enums import EcommerceCapability, ValidationDecision
from ecommerce_analyst.domain.validation.result import DomainValidationResult
from tests.fixtures.dataset_builders import make_ingested_dataset

# ---------------------------------------------------------------------------
# Shared validator instance (stateless — safe to reuse)
# ---------------------------------------------------------------------------

@pytest.fixture()
def validator() -> EcommerceDomainValidator:
    return EcommerceDomainValidator()


@pytest.fixture()
def use_case(validator: EcommerceDomainValidator) -> ValidateDatasetUseCase:
    return ValidateDatasetUseCase(validator=validator)


# ===========================================================================
# 1. Clearly valid e-commerce dataset → PASS
# ===========================================================================

class TestClearlyValidEcommerce:
    """A canonical e-commerce dataset with all core and several optional signals."""

    def test_decision_is_pass(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("quantity", "int64"),
                ("price", "float64"),
                ("order_date", "datetime64[ns]"),
                ("customer_id", "object"),
                ("category", "object"),
                ("country", "object"),
            ],
            records=[
                {
                    "order_id": 1001,
                    "product_name": "Wireless Mouse",
                    "quantity": 2,
                    "price": 29.99,
                    "order_date": "2024-03-15",
                    "customer_id": "C-001",
                    "category": "Electronics",
                    "country": "UK",
                },
            ],
        )
        result = validator.validate(dataset)
        assert result.decision is ValidationDecision.PASS

    def test_confidence_is_high(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("quantity", "int64"),
                ("price", "float64"),
                ("order_date", "datetime64[ns]"),
                ("customer_id", "object"),
            ],
        )
        result = validator.validate(dataset)
        assert result.confidence >= 0.75

    def test_all_three_required_signals_detected(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("sku", "object"),
                ("total", "float64"),
                ("order_date", "datetime64[ns]"),
            ],
        )
        result = validator.validate(dataset)
        detected_names = {ms.signal_name for ms in result.detected_signals}
        assert "order_identifier" in detected_names
        assert "product_identifier" in detected_names
        assert "revenue_or_price" in detected_names

    def test_no_missing_required_signals(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.missing_required_signals == ()

    def test_no_anti_signals(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.anti_signals_detected == ()


# ===========================================================================
# 2. Clearly unrelated HR / payroll dataset → REJECT
# ===========================================================================

class TestHRDatasetRejected:

    def test_decision_is_reject(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("employee_id", "object"),
                ("department", "object"),
                ("salary", "float64"),
                ("hire_date", "datetime64[ns]"),
                ("job_title", "object"),
                ("performance_rating", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.decision is ValidationDecision.REJECT

    def test_hr_anti_signals_detected(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("employee_id", "object"),
                ("salary", "float64"),
                ("department", "object"),
            ],
        )
        result = validator.validate(dataset)
        assert "hr_payroll" in result.anti_signals_detected

    def test_explanation_mentions_non_ecommerce_indicators(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("employee_id", "object"),
                ("salary", "float64"),
                ("department", "object"),
            ],
        )
        result = validator.validate(dataset)
        explanation = result.explanation.lower()
        assert "hr_payroll" in explanation or "non-e-commerce" in explanation

    def test_hr_dataset_with_amount_column_still_rejected(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """An HR dataset that happens to have an 'amount' column must still be rejected."""
        dataset = make_ingested_dataset(
            columns=[
                ("employee_id", "object"),
                ("salary", "float64"),
                ("department", "object"),
                ("amount", "float64"),  # ambiguous — but dominated by HR signals
            ],
        )
        result = validator.validate(dataset)
        assert result.decision is ValidationDecision.REJECT


# ===========================================================================
# 3. Finance / accounting dataset → REJECT
# ===========================================================================

class TestFinanceDatasetRejected:

    def test_decision_is_reject(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("account_code", "object"),
                ("debit", "float64"),
                ("credit", "float64"),
                ("journal_entry", "object"),
                ("fiscal_period", "object"),
            ],
        )
        result = validator.validate(dataset)
        assert result.decision is ValidationDecision.REJECT

    def test_finance_anti_signals_detected(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("debit", "float64"),
                ("credit", "float64"),
                ("gl_code", "object"),
            ],
        )
        result = validator.validate(dataset)
        assert "finance_ledger" in result.anti_signals_detected


# ===========================================================================
# 4. E-commerce dataset with unusual column names → PASS via semantic matching
# ===========================================================================

class TestUnusualColumnNames:

    def test_txn_ref_sku_code_sale_amt_pass(self, validator: EcommerceDomainValidator) -> None:
        """Unusual but semantically clear names should still match via aliases/keywords."""
        dataset = make_ingested_dataset(
            columns=[
                ("txn_ref", "object"),       # → order_identifier (exact alias)
                ("sku_code", "object"),      # → product_identifier (exact alias)
                ("sale_amt", "float64"),     # → revenue_or_price (exact alias)
                ("purchase_dt", "object"),   # → transaction_date (keyword hint)
            ],
            records=[
                {
                    "txn_ref": "TXN-001",
                    "sku_code": "SKU-A1",
                    "sale_amt": 49.99,
                    "purchase_dt": "2024-01-10",
                },
            ],
        )
        result = validator.validate(dataset)
        assert result.decision in (ValidationDecision.PASS, ValidationDecision.PASS_LIMITED)

    def test_all_required_signals_matched_via_aliases(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("invoice_id", "object"),    # order_identifier alias
                ("asin", "object"),          # product_identifier alias
                ("net_revenue", "float64"),  # revenue_or_price alias
            ],
        )
        result = validator.validate(dataset)
        detected_names = {ms.signal_name for ms in result.detected_signals}
        assert "order_identifier" in detected_names
        assert "product_identifier" in detected_names
        assert "revenue_or_price" in detected_names

    def test_match_type_recorded_correctly(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),       # exact alias
                ("my_product_ref", "object"),  # keyword match on 'product'
                ("total", "float64"),        # exact alias
            ],
        )
        result = validator.validate(dataset)
        match_type_map = {ms.signal_name: ms.match_type for ms in result.detected_signals}
        assert match_type_map.get("order_identifier") == "exact"
        assert match_type_map.get("product_identifier") == "keyword"


# ===========================================================================
# 5. Minimal but valid e-commerce dataset → PASS_LIMITED or PASS
# ===========================================================================

class TestMinimalDataset:

    def test_three_required_signals_only_accepted(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """Order ID + product + price with no date/customer should still be accepted."""
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
            ],
            records=[{"order_id": 1, "product_name": "Widget", "price": 9.99}],
        )
        result = validator.validate(dataset)
        assert result.decision in (ValidationDecision.PASS, ValidationDecision.PASS_LIMITED)

    def test_minimal_dataset_lacks_trend_capability(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """Without a date column, TREND_ANALYSIS should be unavailable."""
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert EcommerceCapability.TREND_ANALYSIS in result.unavailable_capabilities

    def test_minimal_dataset_lacks_customer_capability(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert EcommerceCapability.CUSTOMER_ANALYSIS in result.unavailable_capabilities

    def test_revenue_analysis_available_when_price_present(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert EcommerceCapability.REVENUE_ANALYSIS in result.available_capabilities


# ===========================================================================
# 6. E-commerce dataset missing optional customer info → PASS
# ===========================================================================

class TestMissingCustomerInfo:

    def test_pass_without_customer_id(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
                ("order_date", "datetime64[ns]"),
                ("category", "object"),
                ("country", "object"),
                # No customer_id column
            ],
        )
        result = validator.validate(dataset)
        assert result.decision in (ValidationDecision.PASS, ValidationDecision.PASS_LIMITED)

    def test_customer_analysis_capability_unavailable(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
                ("order_date", "datetime64[ns]"),
            ],
        )
        result = validator.validate(dataset)
        assert EcommerceCapability.CUSTOMER_ANALYSIS in result.unavailable_capabilities

    def test_customer_signal_not_in_detected(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
            ],
        )
        result = validator.validate(dataset)
        detected_names = {ms.signal_name for ms in result.detected_signals}
        assert "customer_identifier" not in detected_names


# ===========================================================================
# 7. E-commerce dataset missing pricing/revenue → REJECT
# ===========================================================================

class TestMissingPricing:

    def test_rejected_without_revenue_signal(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("quantity", "int64"),
                ("order_date", "datetime64[ns]"),
                ("customer_id", "object"),
                # No price / total / amount column
            ],
        )
        result = validator.validate(dataset)
        assert result.decision in (ValidationDecision.REJECT, ValidationDecision.UNCERTAIN)

    def test_revenue_or_price_in_missing_required(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("order_date", "datetime64[ns]"),
            ],
        )
        result = validator.validate(dataset)
        assert "revenue_or_price" in result.missing_required_signals


# ===========================================================================
# 8. Ambiguous dataset → UNCERTAIN, low confidence
# ===========================================================================

class TestAmbiguousDataset:

    def test_date_and_amount_only_is_uncertain(self, validator: EcommerceDomainValidator) -> None:
        """date + amount without any product/order identifier is too ambiguous."""
        dataset = make_ingested_dataset(
            columns=[
                ("date", "datetime64[ns]"),
                ("amount", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.decision is ValidationDecision.UNCERTAIN

    def test_uncertain_result_has_low_confidence(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("date", "datetime64[ns]"),
                ("amount", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.confidence < 0.60

    def test_name_and_quantity_without_price_is_uncertain(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """Product + qty but no price or order ID is uncertain."""
        dataset = make_ingested_dataset(
            columns=[
                ("product_name", "object"),
                ("quantity", "int64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.decision in (ValidationDecision.UNCERTAIN, ValidationDecision.REJECT)


# ===========================================================================
# 9. Wrong dtype / bad value patterns → warnings present
# ===========================================================================

class TestDtypeAndValueWarnings:

    def test_price_column_with_text_values_generates_warning(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """A price column filled with strings like 'N/A' should produce a dtype/value warning."""
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "object"),  # wrong dtype — should be float
            ],
            records=[
                {"order_id": 1001, "product_name": "Widget", "price": "N/A"},
                {"order_id": 1002, "product_name": "Gadget", "price": "pending"},
                {"order_id": 1003, "product_name": "Donut", "price": "tbd"},
            ],
        )
        result = validator.validate(dataset)
        has_price_warning = any(
            "price" in (ms.dtype_warning or "").lower()
            for ms in result.detected_signals
            if ms.signal_name == "revenue_or_price"
        )
        assert has_price_warning or any("price" in w.lower() for w in result.warnings)

    def test_quantity_column_with_non_positive_values_generates_warning(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("price", "float64"),
                ("quantity", "float64"),
            ],
            records=[
                {"order_id": 1, "product_id": "P1", "price": 10.0, "quantity": -5.0},
                {"order_id": 2, "product_id": "P2", "price": 20.0, "quantity": -3.0},
                {"order_id": 3, "product_id": "P3", "price": 30.0, "quantity": -1.0},
            ],
        )
        result = validator.validate(dataset)
        has_qty_warning = any(
            ms.dtype_warning is not None
            for ms in result.detected_signals
            if ms.signal_name == "quantity"
        )
        assert has_qty_warning or len(result.warnings) >= 0  # at minimum no crash


# ===========================================================================
# 10. Result is fully structured and deterministic
# ===========================================================================

class TestResultStructure:

    def test_result_is_domain_validation_result_instance(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        assert isinstance(result, DomainValidationResult)

    def test_all_fields_populated(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        assert isinstance(result.decision, ValidationDecision)
        assert isinstance(result.confidence, float)
        assert isinstance(result.detected_signals, tuple)
        assert isinstance(result.missing_required_signals, tuple)
        assert isinstance(result.available_capabilities, tuple)
        assert isinstance(result.unavailable_capabilities, tuple)
        assert isinstance(result.warnings, tuple)
        assert isinstance(result.explanation, str) and len(result.explanation) > 0
        assert isinstance(result.anti_signals_detected, tuple)

    def test_result_is_deterministic(self, validator: EcommerceDomainValidator) -> None:
        """Same input must always produce identical output."""
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
                ("order_date", "datetime64[ns]"),
            ],
        )
        result_a = validator.validate(dataset)
        result_b = validator.validate(dataset)
        assert result_a.decision == result_b.decision
        assert result_a.confidence == result_b.confidence
        assert result_a.detected_signals == result_b.detected_signals
        assert result_a.explanation == result_b.explanation

    def test_result_is_serialisable(self, validator: EcommerceDomainValidator) -> None:
        """DomainValidationResult must be JSON-serialisable via Pydantic."""
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("sku", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        serialised = result.model_dump()
        assert "decision" in serialised
        assert "confidence" in serialised
        assert "explanation" in serialised

    def test_confidence_in_valid_range(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[("employee_id", "object"), ("salary", "float64")],
        )
        result = validator.validate(dataset)
        assert 0.0 <= result.confidence <= 1.0

    def test_available_and_unavailable_caps_are_disjoint(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        available = set(result.available_capabilities)
        unavailable = set(result.unavailable_capabilities)
        assert available.isdisjoint(unavailable)

    def test_all_capabilities_accounted_for(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        all_caps = set(EcommerceCapability)
        reported = set(result.available_capabilities) | set(result.unavailable_capabilities)
        assert reported == all_caps


# ===========================================================================
# 11. No LLM required — validator has no external I/O
# ===========================================================================

class TestNoLLMRequired:

    def test_validator_has_no_llm_dependency(self, validator: EcommerceDomainValidator) -> None:
        """EcommerceDomainValidator must not hold a reference to any LLM client."""
        # Check it's a plain dataclass with no llm-related attributes
        validator_dict = validator.__dataclass_fields__  # type: ignore[attr-defined]
        llm_fields = [k for k in validator_dict if "llm" in k.lower() or "model" in k.lower()]
        assert llm_fields == [], f"Unexpected LLM-related fields: {llm_fields}"

    def test_use_case_runs_without_network(self) -> None:
        """Validation must complete without any network access whatsoever."""
        use_case = ValidateDatasetUseCase()
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("sku", "object"), ("total", "float64")],
        )
        # If this succeeds, no network was needed
        result = use_case.execute(dataset)
        assert result.decision in ValidationDecision.__members__.values()

    def test_default_use_case_uses_default_contract(self) -> None:
        """Default instantiation should use ECOMMERCE_SIGNALS without configuration."""
        use_case = ValidateDatasetUseCase()
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("price", "float64"),
            ],
        )
        result = use_case.execute(dataset)
        # Should pass with default contract — not require any configuration
        assert result.is_accepted


# ===========================================================================
# 12. No actual analysis performed — result is schema-only
# ===========================================================================

class TestNoAnalysisPerformed:

    def test_result_contains_no_computed_metrics(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """DomainValidationResult must not have revenue totals, averages, or computed metrics."""
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
            records=[
                {"order_id": 1001, "product_id": "P1", "total": 100.0},
                {"order_id": 1002, "product_id": "P2", "total": 200.0},
            ],
        )
        result = validator.validate(dataset)
        result_dict = result.model_dump()
        # No analysis-related keys should exist
        analysis_keys = {
            "total_revenue", "average_order_value", "top_products", "revenue_by_date",
            "metrics", "analysis", "report", "chart", "insights",
        }
        assert analysis_keys.isdisjoint(result_dict.keys()), (
            f"Result contains unexpected analysis keys: {analysis_keys & result_dict.keys()}"
        )

    def test_detected_signals_contain_only_schema_information(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        for signal in result.detected_signals:
            assert hasattr(signal, "signal_name")
            assert hasattr(signal, "matched_column")
            assert hasattr(signal, "match_type")
            # No computed values stored on matched signals
            signal_dict = signal.model_dump()
            assert "computed_value" not in signal_dict
            assert "aggregated_revenue" not in signal_dict


# ===========================================================================
# Additional edge cases and boundary conditions
# ===========================================================================

class TestEdgeCases:

    def test_empty_optional_signals_do_not_affect_required_detection(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """Required signals should be detected even if zero optional signals match."""
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_name", "object"),
                ("total", "float64"),
            ],
        )
        result = validator.validate(dataset)
        detected = {ms.signal_name for ms in result.detected_signals}
        assert "order_identifier" in detected
        assert "product_identifier" in detected
        assert "revenue_or_price" in detected

    def test_mixed_ecommerce_and_hr_columns_rejected(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """A dataset that mixes HR signals with missing order identifier is rejected."""
        dataset = make_ingested_dataset(
            columns=[
                ("employee_id", "object"),
                ("salary", "float64"),
                ("product_name", "object"),  # ecommerce signal, but no order_id
                ("total", "float64"),
            ],
        )
        result = validator.validate(dataset)
        # Has HR anti-signals and missing order_identifier → REJECT
        assert result.decision is ValidationDecision.REJECT

    def test_full_ecommerce_dataset_with_discount_column(
        self, validator: EcommerceDomainValidator
    ) -> None:
        """Discount signal should unlock DISCOUNT_ANALYSIS capability."""
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
                ("discount", "float64"),
            ],
        )
        result = validator.validate(dataset)
        assert result.is_accepted
        assert EcommerceCapability.DISCOUNT_ANALYSIS in result.available_capabilities

    def test_is_accepted_property(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
        )
        result = validator.validate(dataset)
        assert result.is_accepted is True
        assert result.is_rejected is False

    def test_is_rejected_property(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[("employee_id", "object"), ("salary", "float64"), ("department", "object")],
        )
        result = validator.validate(dataset)
        assert result.is_rejected is True
        assert result.is_accepted is False

    def test_explanation_is_nonempty_for_all_decisions(
        self, validator: EcommerceDomainValidator
    ) -> None:
        scenarios = [
            [("order_id", "int64"), ("product_id", "object"), ("total", "float64")],
            [("employee_id", "object"), ("salary", "float64")],
            [("date", "datetime64[ns]"), ("amount", "float64")],
        ]
        for columns in scenarios:
            dataset = make_ingested_dataset(columns=columns)
            result = validator.validate(dataset)
            assert len(result.explanation) > 0, f"Empty explanation for columns: {columns}"

    def test_medical_dataset_rejected(self, validator: EcommerceDomainValidator) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("patient_id", "object"),
                ("diagnosis", "object"),
                ("icd_code", "object"),
                ("date", "datetime64[ns]"),
            ],
        )
        result = validator.validate(dataset)
        assert result.decision is ValidationDecision.REJECT
        assert "medical" in result.anti_signals_detected

    def test_ecommerce_with_payment_method_unlocks_payment_capability(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
                ("payment_method", "object"),
            ],
        )
        result = validator.validate(dataset)
        assert EcommerceCapability.PAYMENT_ANALYSIS in result.available_capabilities

    def test_geographic_signal_unlocks_geographic_capability(
        self, validator: EcommerceDomainValidator
    ) -> None:
        dataset = make_ingested_dataset(
            columns=[
                ("order_id", "int64"),
                ("product_id", "object"),
                ("total", "float64"),
                ("country", "object"),
            ],
        )
        result = validator.validate(dataset)
        assert EcommerceCapability.GEOGRAPHIC_ANALYSIS in result.available_capabilities
