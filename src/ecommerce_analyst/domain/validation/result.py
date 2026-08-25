"""DomainValidationResult — structured output of the e-commerce domain validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ecommerce_analyst.domain.validation.enums import EcommerceCapability, ValidationDecision


class MatchedSignal(BaseModel):
    """Record of a single domain signal that was detected in the dataset."""

    signal_name: str = Field(min_length=1)
    """Canonical signal name (e.g. ``'order_identifier'``)."""

    matched_column: str = Field(min_length=1)
    """The actual column name in the dataset that matched this signal."""

    match_type: str = Field(min_length=1)
    """How the match was made: ``'exact'`` or ``'keyword'``."""

    dtype_warning: str | None = None
    """Non-empty when the column's dtype or values look suspicious for this signal."""

    model_config = ConfigDict(frozen=True)


class DomainValidationResult(BaseModel):
    """Structured, fully serialisable result of domain validation.

    Produced by ``EcommerceDomainValidator`` and consumed by orchestration layers.
    All fields are populated regardless of the decision so callers can always
    inspect why a decision was made without checking for None.
    """

    decision: ValidationDecision
    """The overall validation outcome."""

    confidence: float = Field(ge=0.0, le=1.0)
    """Normalised confidence score in the range [0.0, 1.0]."""

    detected_signals: tuple[MatchedSignal, ...]
    """Signals that were successfully matched against dataset columns."""

    missing_required_signals: tuple[str, ...]
    """Names of required signals that were not detected (contributes to rejection)."""

    available_capabilities: tuple[EcommerceCapability, ...]
    """Analytical capabilities this dataset can support."""

    unavailable_capabilities: tuple[EcommerceCapability, ...]
    """Analytical capabilities this dataset cannot support (missing signals)."""

    warnings: tuple[str, ...]
    """Non-fatal observations: dtype mismatches, missing optional signals, etc."""

    explanation: str = Field(min_length=1)
    """Human-readable explanation of the decision and its rationale."""

    anti_signals_detected: tuple[str, ...]
    """Domain labels of detected anti-signal groups (e.g. ``'hr_payroll'``)."""

    model_config = ConfigDict(frozen=True)

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        """Clamp and round confidence to two decimal places for stable comparisons."""
        return round(max(0.0, min(1.0, v)), 2)

    @property
    def is_accepted(self) -> bool:
        """Return True when the dataset was accepted (PASS or PASS_LIMITED)."""
        return self.decision in (ValidationDecision.PASS, ValidationDecision.PASS_LIMITED)

    @property
    def is_rejected(self) -> bool:
        """Return True when the dataset was definitively rejected."""
        return self.decision is ValidationDecision.REJECT
