"""E-commerce domain signal contract and anti-signal definitions.

This module is the single authoritative source of truth for what constitutes an
e-commerce dataset in this application. Change signal definitions here to adjust
validation behaviour — the validator reads from these constants.

Naming convention:
- ``ECOMMERCE_SIGNALS`` — ordered tuple of DomainSignal objects (required first).
- ``ANTI_SIGNALS`` — column-level patterns that suggest a non-e-commerce domain.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ecommerce_analyst.domain.validation.enums import (
    EcommerceCapability,
    SignalStrength,
)
from ecommerce_analyst.domain.validation.signals import DomainSignal

# ---------------------------------------------------------------------------
# Value validators (pure functions, no external deps)
# ---------------------------------------------------------------------------


def _is_numeric_positive(values: Sequence[Any]) -> bool:
    """Return True if the majority of non-null values are positive numbers."""
    numeric_count = 0
    total = 0
    for v in values:
        if v is None:
            continue
        total += 1
        try:
            if float(v) > 0:
                numeric_count += 1
        except (TypeError, ValueError):
            pass
    if total == 0:
        return True  # cannot determine — don't warn
    return numeric_count / total >= 0.7


def _is_positive_integer(values: Sequence[Any]) -> bool:
    """Return True if the majority of non-null values are positive whole numbers."""
    int_count = 0
    total = 0
    for v in values:
        if v is None:
            continue
        total += 1
        try:
            f = float(v)
            if f > 0 and f == int(f):
                int_count += 1
        except (TypeError, ValueError):
            pass
    if total == 0:
        return True
    return int_count / total >= 0.7


# ---------------------------------------------------------------------------
# Core required signals — absence → REJECT or UNCERTAIN
# ---------------------------------------------------------------------------

_ORDER_IDENTIFIER = DomainSignal(
    name="order_identifier",
    description="Unique identifier for each transaction or order.",
    column_aliases=frozenset(
        {
            "order_id",
            "order_number",
            "order_no",
            "order_ref",
            "transaction_id",
            "transaction_no",
            "txn_id",
            "txn_ref",
            "invoice_id",
            "invoice_number",
            "invoice_no",
            "sale_id",
            "sale_ref",
            "receipt_id",
            "purchase_id",
            "booking_id",
        }
    ),
    keyword_hints=frozenset({"order_id", "transaction_id", "invoice_id", "txn_id", "sale_id"}),
    required=True,
    strength=SignalStrength.STRONG,
    capability=None,
)

_PRODUCT_IDENTIFIER = DomainSignal(
    name="product_identifier",
    description="Identifier or name for the product or item being transacted.",
    column_aliases=frozenset(
        {
            "product_id",
            "product_name",
            "product_code",
            "product",
            "item_id",
            "item_name",
            "item_code",
            "item",
            "sku",
            "sku_code",
            "sku_id",
            "asin",
            "upc",
            "barcode",
            "article_id",
            "article_no",
        }
    ),
    keyword_hints=frozenset({"product", "item", "sku", "article"}),
    required=True,
    strength=SignalStrength.STRONG,
    capability=EcommerceCapability.PRODUCT_ANALYSIS,
)

_REVENUE_OR_PRICE = DomainSignal(
    name="revenue_or_price",
    description="Monetary value of the transaction or line item.",
    column_aliases=frozenset(
        {
            "price",
            "unit_price",
            "sale_price",
            "selling_price",
            "total",
            "total_price",
            "total_amount",
            "order_total",
            "subtotal",
            "sub_total",
            "amount",
            "sale_amount",
            "sale_amt",
            "revenue",
            "gross",
            "gross_revenue",
            "net",
            "net_revenue",
            "line_total",
            "line_amount",
            "extended_price",
            "cost",
            "charge",
            "value",
        }
    ),
    keyword_hints=frozenset({"price", "total", "revenue", "amount", "sale_amt"}),
    expected_dtype_patterns=("int", "float", "object"),
    value_validator=_is_numeric_positive,
    required=True,
    strength=SignalStrength.STRONG,
    capability=EcommerceCapability.REVENUE_ANALYSIS,
)


# ---------------------------------------------------------------------------
# Core-optional signals — presence boosts confidence, absence is allowed
# ---------------------------------------------------------------------------

_TRANSACTION_DATE = DomainSignal(
    name="transaction_date",
    description="Date or timestamp when the transaction occurred.",
    column_aliases=frozenset(
        {
            "date",
            "order_date",
            "purchase_date",
            "transaction_date",
            "sale_date",
            "created_at",
            "created_date",
            "order_timestamp",
            "order_datetime",
            "purchase_timestamp",
            "invoice_date",
            "shipped_date",
            "delivery_date",
            "dt",
            "purchase_dt",
            "order_dt",
        }
    ),
    keyword_hints=frozenset({"date", "timestamp", "_dt", "_at"}),
    expected_dtype_patterns=("datetime", "object"),
    required=False,
    strength=SignalStrength.STRONG,
    capability=EcommerceCapability.TREND_ANALYSIS,
)

_QUANTITY = DomainSignal(
    name="quantity",
    description="Number of units of the product purchased.",
    column_aliases=frozenset(
        {
            "quantity",
            "qty",
            "units",
            "quantity_ordered",
            "order_qty",
            "num_items",
            "items",
            "count",
            "pieces",
            "units_sold",
        }
    ),
    keyword_hints=frozenset({"qty", "quantity", "units"}),
    expected_dtype_patterns=("int", "float"),
    value_validator=_is_positive_integer,
    required=False,
    strength=SignalStrength.MODERATE,
    capability=EcommerceCapability.PRODUCT_ANALYSIS,
)

_CUSTOMER_IDENTIFIER = DomainSignal(
    name="customer_identifier",
    description="Identifier linking the transaction to a customer.",
    column_aliases=frozenset(
        {
            "customer_id",
            "customer_no",
            "client_id",
            "user_id",
            "buyer_id",
            "account_id",
            "shopper_id",
            "member_id",
            "consumer_id",
            "contact_id",
        }
    ),
    keyword_hints=frozenset({"customer", "client", "buyer", "shopper", "member"}),
    required=False,
    strength=SignalStrength.MODERATE,
    capability=EcommerceCapability.CUSTOMER_ANALYSIS,
)

_PRODUCT_CATEGORY = DomainSignal(
    name="product_category",
    description="Category, type, or classification of the product.",
    column_aliases=frozenset(
        {
            "category",
            "product_category",
            "item_category",
            "category_name",
            "product_type",
            "item_type",
            "sub_category",
            "subcategory",
            "product_group",
            "segment",
            "class",
            "genre",
        }
    ),
    keyword_hints=frozenset({"category", "segment", "genre"}),
    required=False,
    strength=SignalStrength.MODERATE,
    capability=EcommerceCapability.PRODUCT_ANALYSIS,
)

_DISCOUNT_OR_PROMO = DomainSignal(
    name="discount_or_promo",
    description="Discount amount, percentage, or promotional code applied.",
    column_aliases=frozenset(
        {
            "discount",
            "discount_amount",
            "discount_pct",
            "discount_percent",
            "promo_code",
            "coupon_code",
            "voucher_code",
            "coupon",
            "promotion",
            "promo",
            "rebate",
            "markdown",
        }
    ),
    keyword_hints=frozenset({"discount", "promo", "coupon", "voucher", "rebate"}),
    required=False,
    strength=SignalStrength.WEAK,
    capability=EcommerceCapability.DISCOUNT_ANALYSIS,
)

_GEOGRAPHIC = DomainSignal(
    name="geographic",
    description="Geographic dimension such as country, region, or city.",
    column_aliases=frozenset(
        {
            "country",
            "country_code",
            "region",
            "state",
            "city",
            "market",
            "territory",
            "shipping_country",
            "delivery_country",
            "ship_to_country",
            "billing_country",
            "location",
            "geography",
            "geo",
        }
    ),
    keyword_hints=frozenset({"country", "region", "city", "market", "territory", "geo"}),
    required=False,
    strength=SignalStrength.WEAK,
    capability=EcommerceCapability.GEOGRAPHIC_ANALYSIS,
)

_PAYMENT_METHOD = DomainSignal(
    name="payment_method",
    description="Payment channel or method used for the transaction.",
    column_aliases=frozenset(
        {
            "payment_method",
            "payment_type",
            "pay_method",
            "payment_channel",
            "payment_mode",
            "pay_type",
        }
    ),
    keyword_hints=frozenset({"payment", "pay_method", "pay_type"}),
    required=False,
    strength=SignalStrength.WEAK,
    capability=EcommerceCapability.PAYMENT_ANALYSIS,
)

_ORDER_STATUS = DomainSignal(
    name="order_status",
    description="Fulfilment or delivery status of the order.",
    column_aliases=frozenset(
        {
            "status",
            "order_status",
            "fulfillment_status",
            "fulfilment_status",
            "delivery_status",
            "shipment_status",
            "shipping_status",
        }
    ),
    keyword_hints=frozenset({"status", "fulfil", "shipment"}),
    required=False,
    strength=SignalStrength.WEAK,
    capability=None,
)


# ---------------------------------------------------------------------------
# Public contract
# ---------------------------------------------------------------------------

ECOMMERCE_SIGNALS: tuple[DomainSignal, ...] = (
    # Required first — easier to iterate by priority
    _ORDER_IDENTIFIER,
    _PRODUCT_IDENTIFIER,
    _REVENUE_OR_PRICE,
    # Optional / capability-bearing
    _TRANSACTION_DATE,
    _QUANTITY,
    _CUSTOMER_IDENTIFIER,
    _PRODUCT_CATEGORY,
    _DISCOUNT_OR_PROMO,
    _GEOGRAPHIC,
    _PAYMENT_METHOD,
    _ORDER_STATUS,
)

# ---------------------------------------------------------------------------
# Anti-signals: column name sets that strongly suggest a non-e-commerce domain.
# Keyed by domain label for use in explanations.
# ---------------------------------------------------------------------------

ANTI_SIGNAL_GROUPS: dict[str, frozenset[str]] = {
    "hr_payroll": frozenset(
        {
            "employee_id",
            "employee_no",
            "staff_id",
            "personnel_id",
            "salary",
            "wage",
            "payroll",
            "headcount",
            "hire_date",
            "termination_date",
            "department",
            "job_title",
            "position",
            "performance_rating",
            "leave_balance",
            "tax_withheld",
            "gross_pay",
            "net_pay",
            "payslip",
            "reimbursement",
        }
    ),
    "finance_ledger": frozenset(
        {
            "debit",
            "credit",
            "account_code",
            "account_number",
            "ledger",
            "journal_entry",
            "gl_code",
            "chart_of_accounts",
            "fiscal_period",
            "trial_balance",
            "balance_sheet",
            "profit_loss",
            "depreciation",
            "amortization",
            "accrual",
            "prepayment",
        }
    ),
    "medical": frozenset(
        {
            "patient_id",
            "patient_name",
            "diagnosis",
            "icd_code",
            "icd10",
            "procedure_code",
            "cpt_code",
            "medication",
            "prescription",
            "clinical_note",
            "nhs_number",
            "mrn",
        }
    ),
    "iot_telemetry": frozenset(
        {
            "sensor_id",
            "device_id",
            "reading",
            "telemetry",
            "firmware_version",
            "signal_strength",
            "latitude",
            "longitude",
            "altitude",
            "rpm",
            "voltage",
            "amperage",
        }
    ),
}

# Anti-signal keyword hints for partial-name matching
ANTI_SIGNAL_KEYWORDS: dict[str, frozenset[str]] = {
    "hr_payroll": frozenset({"employee", "payroll", "salary", "headcount", "hr_"}),
    "finance_ledger": frozenset({"ledger", "journal", "gl_code", "account_code"}),
    "medical": frozenset({"patient", "diagnosis", "icd_", "clinical"}),
    "iot_telemetry": frozenset({"sensor_", "telemetry", "firmware"}),
}
