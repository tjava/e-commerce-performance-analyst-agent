"""Enums for the dataset profiling and data quality layer."""

from __future__ import annotations

from enum import StrEnum


class ColumnRole(StrEnum):
    """Semantic role assigned to a column during domain-aware profiling.

    Roles are derived from the ``DomainValidationResult.detected_signals``
    produced by Milestone 3 and are used by the profiler to apply
    e-commerce-specific quality checks per column.
    """

    ORDER_IDENTIFIER = "order_identifier"
    """Column identifies individual orders/transactions."""

    PRODUCT_IDENTIFIER = "product_identifier"
    """Column identifies products, SKUs, or items."""

    REVENUE = "revenue"
    """Column holds monetary transaction value (price, total, amount)."""

    DATE = "date"
    """Column holds transaction or order dates/timestamps."""

    QUANTITY = "quantity"
    """Column holds units/quantity ordered."""

    CUSTOMER_IDENTIFIER = "customer_identifier"
    """Column identifies customers or buyers."""

    CATEGORY = "category"
    """Column holds product category or segment classification."""

    DISCOUNT = "discount"
    """Column holds discount amount, percentage, or promo code."""

    GEOGRAPHIC = "geographic"
    """Column holds geographic dimension (country, region, city)."""

    PAYMENT_METHOD = "payment_method"
    """Column holds payment channel or method."""

    STATUS = "status"
    """Column holds order or fulfilment status."""

    UNKNOWN = "unknown"
    """Column has no recognised e-commerce semantic role."""


class QualityIssueSeverity(StrEnum):
    """How severely a data quality issue impacts downstream analysis."""

    BLOCKING = "blocking"
    """Issue prevents the associated analysis from running reliably.

    Example: all date values unparseable → TREND_ANALYSIS cannot run.
    """

    WARNING = "warning"
    """Issue reduces confidence but analysis can still execute with caveats.

    Example: 15% missing prices → revenue totals will be understated.
    """

    INFO = "info"
    """Informational observation that does not materially affect analysis.

    Example: a column has only one distinct value.
    """


class QualityIssueCode(StrEnum):
    """Machine-readable codes identifying specific data quality problems."""

    MISSING_VALUES = "missing_values"
    """One or more null/NaN values present in the column."""

    HIGH_NULL_RATE = "high_null_rate"
    """More than 30 % of column values are null."""

    CRITICAL_NULL_RATE = "critical_null_rate"
    """More than 80 % of column values are null — column is effectively empty."""

    DUPLICATE_ROWS = "duplicate_rows"
    """Dataset contains exact row duplicates."""

    DUPLICATE_ORDER_IDS = "duplicate_order_ids"
    """Order identifier column contains non-unique values."""

    NEGATIVE_QUANTITY = "negative_quantity"
    """Quantity column has one or more negative values."""

    ZERO_QUANTITY = "zero_quantity"
    """Quantity column has one or more zero values."""

    NEGATIVE_PRICE = "negative_price"
    """Revenue/price column has one or more negative values."""

    ZERO_PRICE = "zero_price"
    """Revenue/price column has one or more zero values."""

    IMPLAUSIBLE_PRICE = "implausible_price"
    """Revenue/price column has statistical outliers (> mean + 5 * std)."""

    UNPARSEABLE_DATE = "unparseable_date"
    """Date column contains values that cannot be parsed as dates."""

    FUTURE_DATES = "future_dates"
    """Date column contains values later than today."""

    DATE_RANGE_ANOMALY = "date_range_anomaly"
    """Date column spans an implausibly long or short range."""

    SINGLE_CATEGORY_VALUE = "single_category_value"
    """Categorical column has only one distinct non-null value."""

    HIGH_CARDINALITY = "high_cardinality"
    """Categorical column has too many unique values for meaningful grouping."""

    CONSTANT_COLUMN = "constant_column"
    """Every row has the same value — column provides no analytical variance."""

    MIXED_DTYPES = "mixed_dtypes"
    """Object-typed column contains a mix of numeric and string values."""
