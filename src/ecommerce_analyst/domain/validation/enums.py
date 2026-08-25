"""Enums for the e-commerce domain validation result."""

from __future__ import annotations

from enum import StrEnum


class ValidationDecision(StrEnum):
    """The outcome of domain validation for an ingested dataset."""

    PASS = "pass"
    """Dataset clearly belongs to the e-commerce domain and meets the core contract."""

    PASS_LIMITED = "pass_limited"
    """Dataset is valid e-commerce data but lacks optional signals, limiting some analyses."""

    UNCERTAIN = "uncertain"
    """Dataset has insufficient signals to be confidently classified either way."""

    REJECT = "reject"
    """Dataset does not belong to the e-commerce domain or fails the core contract."""


class EcommerceCapability(StrEnum):
    """Analytical capabilities that a dataset may or may not support."""

    REVENUE_ANALYSIS = "revenue_analysis"
    """Aggregate revenue totals, averages, and revenue-by-dimension breakdowns."""

    TREND_ANALYSIS = "trend_analysis"
    """Time-series revenue and order volume trends requiring transaction dates."""

    PRODUCT_ANALYSIS = "product_analysis"
    """Product-level performance, top sellers, and category breakdowns."""

    CUSTOMER_ANALYSIS = "customer_analysis"
    """Customer-level metrics, repeat purchase rate, and customer segmentation."""

    DISCOUNT_ANALYSIS = "discount_analysis"
    """Discount impact analysis and promotional effectiveness."""

    GEOGRAPHIC_ANALYSIS = "geographic_analysis"
    """Regional or country-level sales performance breakdowns."""

    PAYMENT_ANALYSIS = "payment_analysis"
    """Payment method distribution and revenue by payment channel."""


class SignalStrength(StrEnum):
    """How strongly a detected signal contributes to the domain confidence score."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
