"""E-commerce domain validator service.

Consumes an ``IngestedDataset`` produced by Milestone 2 and returns a fully
structured ``DomainValidationResult``.  No LLM is used here — the validator
is entirely deterministic and testable.

Architecture note: this module lives in ``application/services`` because it
coordinates between domain models (signals, contract) and domain result objects.
It has no infrastructure dependencies and can be tested in isolation.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from ecommerce_analyst.domain.models.dataset import IngestedDataset
from ecommerce_analyst.domain.validation.contracts import (
    ANTI_SIGNAL_GROUPS,
    ANTI_SIGNAL_KEYWORDS,
    ECOMMERCE_SIGNALS,
)
from ecommerce_analyst.domain.validation.enums import (
    EcommerceCapability,
    SignalStrength,
    ValidationDecision,
)
from ecommerce_analyst.domain.validation.result import DomainValidationResult, MatchedSignal
from ecommerce_analyst.domain.validation.signals import DomainSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights — tuned so 3 strong signals yield ~0.75 confidence
# ---------------------------------------------------------------------------
_STRENGTH_WEIGHT: dict[SignalStrength, float] = {
    SignalStrength.STRONG: 0.25,
    SignalStrength.MODERATE: 0.12,
    SignalStrength.WEAK: 0.05,
}

# Keyword match is worth 70 % of an exact match
_KEYWORD_MATCH_FACTOR = 0.7

# Anti-signal penalty applied per detected anti-signal group
_ANTI_SIGNAL_PENALTY = 0.20

# Decision thresholds
_PASS_THRESHOLD = 0.75
_UNCERTAIN_THRESHOLD = 0.40

# Sample size for value-level validation
_VALUE_SAMPLE_SIZE = 50


@dataclass(frozen=True, slots=True)
class EcommerceDomainValidator:
    """Determine whether an ingested dataset belongs to the e-commerce domain.

    The validator is stateless and reusable.  Inject a custom ``signals``
    tuple to replace the default e-commerce contract in tests or alternative
    domain configurations.
    """

    signals: tuple[DomainSignal, ...] = field(default_factory=lambda: ECOMMERCE_SIGNALS)

    def validate(self, dataset: IngestedDataset) -> DomainValidationResult:
        """Run domain validation and return a structured result.

        Parameters
        ----------
        dataset:
            A technically valid ``IngestedDataset`` produced by the ingestion layer.

        Returns
        -------
        DomainValidationResult
            A fully populated, frozen Pydantic model.  Never raises for normal
            rejection cases — those are encoded in the ``decision`` field.
        """
        logger.debug(
            "Running domain validation",
            extra={"filename": dataset.metadata.filename},
        )

        normalized_columns = _normalize_columns(dataset)
        column_dtype_map = _column_dtype_map(dataset)

        # ── 1. Match signals ─────────────────────────────────────────────────
        matched: list[MatchedSignal] = []
        matched_signal_names: set[str] = set()

        for signal in self.signals:
            match_result = _match_signal(
                signal,
                normalized_columns,
                column_dtype_map,
                dataset.records,
            )
            if match_result is not None:
                matched.append(match_result)
                matched_signal_names.add(signal.name)

        # ── 2. Detect anti-signals ────────────────────────────────────────────
        anti_signals_detected = _detect_anti_signals(normalized_columns)

        # ── 3. Identify missing required signals ─────────────────────────────
        missing_required = [
            s.name for s in self.signals if s.required and s.name not in matched_signal_names
        ]

        # ── 4. Compute confidence score ───────────────────────────────────────
        raw_score = _compute_score(matched, self.signals, anti_signals_detected)
        confidence = round(max(0.0, min(1.0, raw_score)), 2)

        # ── 5. Assess capabilities ────────────────────────────────────────────
        available_caps, unavailable_caps = _assess_capabilities(matched_signal_names, self.signals)

        # ── 6. Collect warnings ───────────────────────────────────────────────
        warnings = _collect_warnings(matched, missing_required, anti_signals_detected)

        # ── 7. Make decision ──────────────────────────────────────────────────
        decision = _make_decision(
            missing_required=missing_required,
            anti_signals=anti_signals_detected,
            confidence=confidence,
            matched_names=matched_signal_names,
        )

        # ── 8. Build explanation ──────────────────────────────────────────────
        explanation = _build_explanation(
            decision=decision,
            matched=matched,
            missing_required=missing_required,
            anti_signals=anti_signals_detected,
            available_caps=available_caps,
            unavailable_caps=unavailable_caps,
            confidence=confidence,
        )

        logger.info(
            "Domain validation complete",
            extra={
                "filename": dataset.metadata.filename,
                "decision": decision.value,
                "confidence": confidence,
            },
        )

        return DomainValidationResult(
            decision=decision,
            confidence=confidence,
            detected_signals=tuple(matched),
            missing_required_signals=tuple(missing_required),
            available_capabilities=tuple(available_caps),
            unavailable_capabilities=tuple(unavailable_caps),
            warnings=tuple(warnings),
            explanation=explanation,
            anti_signals_detected=tuple(anti_signals_detected),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_columns(dataset: IngestedDataset) -> dict[str, str]:
    """Return {normalized_name: original_name} for every column."""
    return {
        col.name.strip().lower().replace(" ", "_"): col.name for col in dataset.metadata.columns
    }


def _column_dtype_map(dataset: IngestedDataset) -> dict[str, str]:
    """Return {normalized_name: inferred_dtype} for every column."""
    result: dict[str, str] = {}
    for col in dataset.metadata.columns:
        normalized = col.name.strip().lower().replace(" ", "_")
        result[normalized] = col.inferred_dtype
    return result


def _match_signal(
    signal: DomainSignal,
    normalized_columns: dict[str, str],
    column_dtype_map: dict[str, str],
    records: list[dict[str, Any]],
) -> MatchedSignal | None:
    """Attempt to match a single DomainSignal against the dataset columns.

    Returns a ``MatchedSignal`` if matched, or ``None`` if no column qualifies.
    """
    best_match: tuple[str, str, bool] | None = None  # (normalized_name, original_name, is_exact)

    for norm_name, orig_name in normalized_columns.items():
        is_match, is_exact = signal.matches_column(norm_name)
        if not is_match:
            continue
        # Prefer exact over keyword; take first exact found, or first keyword if no exact
        if best_match is None or (is_exact and not best_match[2]):
            best_match = (norm_name, orig_name, is_exact)

    if best_match is None:
        return None

    norm_name, orig_name, is_exact = best_match
    match_type = "exact" if is_exact else "keyword"

    # Dtype compatibility check
    dtype_warning: str | None = None
    inferred_dtype = column_dtype_map.get(norm_name, "")
    if not signal.dtype_compatible(inferred_dtype):
        dtype_warning = (
            f"Column '{orig_name}' matched signal '{signal.name}' "
            f"but has dtype '{inferred_dtype}', which may not be appropriate."
        )

    # Value-level pattern check (if dtype looks right and validator provided)
    if dtype_warning is None and signal.value_validator is not None:
        sample = _sample_values(orig_name, records)
        if sample and not signal.value_validator(sample):
            dtype_warning = (
                f"Column '{orig_name}' matched signal '{signal.name}' "
                f"but sampled values do not match expected pattern."
            )

    return MatchedSignal(
        signal_name=signal.name,
        matched_column=orig_name,
        match_type=match_type,
        dtype_warning=dtype_warning,
    )


def _sample_values(column: str, records: list[dict[str, Any]]) -> list[Any]:
    """Extract up to _VALUE_SAMPLE_SIZE non-null values from a column."""
    values: list[Any] = []
    for record in records:
        val = record.get(column)
        if val is not None:
            values.append(val)
        if len(values) >= _VALUE_SAMPLE_SIZE:
            break
    return values


def _detect_anti_signals(normalized_columns: dict[str, str]) -> list[str]:
    """Return domain labels for each anti-signal group that has a column hit."""
    detected: list[str] = []
    col_names = set(normalized_columns.keys())

    for domain_label, exact_set in ANTI_SIGNAL_GROUPS.items():
        if col_names & exact_set:
            detected.append(domain_label)
            continue
        # Keyword partial match
        keywords = ANTI_SIGNAL_KEYWORDS.get(domain_label, frozenset())
        if any(kw in col_name for col_name in col_names for kw in keywords):
            detected.append(domain_label)

    return detected


def _compute_score(
    matched: list[MatchedSignal],
    signals: Sequence[DomainSignal],
    anti_signals: list[str],
) -> float:
    """Compute a raw confidence score in [0, 1]."""
    signal_map = {s.name: s for s in signals}
    score = 0.0

    for ms in matched:
        signal = signal_map.get(ms.signal_name)
        if signal is None:
            continue
        weight = _STRENGTH_WEIGHT.get(signal.strength, 0.0)
        if ms.match_type == "keyword":
            weight *= _KEYWORD_MATCH_FACTOR
        score += weight

    # Penalise anti-signals
    score -= len(anti_signals) * _ANTI_SIGNAL_PENALTY

    return score


def _assess_capabilities(
    matched_names: set[str],
    signals: Sequence[DomainSignal],
) -> tuple[list[EcommerceCapability], list[EcommerceCapability]]:
    """Determine which capabilities are available vs. unavailable."""
    all_caps = list(EcommerceCapability)
    available: set[EcommerceCapability] = set()

    for signal in signals:
        if signal.capability and signal.name in matched_names:
            available.add(signal.capability)

    unavailable = [cap for cap in all_caps if cap not in available]
    return sorted(available, key=lambda c: c.value), sorted(unavailable, key=lambda c: c.value)


def _make_decision(
    *,
    missing_required: list[str],
    anti_signals: list[str],
    confidence: float,
    matched_names: set[str],
) -> ValidationDecision:
    """Apply decision rules to produce a ValidationDecision."""
    # Anti-signals dominant without any e-commerce order signal → reject
    if anti_signals and "order_identifier" not in matched_names:
        return ValidationDecision.REJECT

    # Missing required signals
    if missing_required:
        # Anti-signals present alongside missing required → reject
        if anti_signals:
            return ValidationDecision.REJECT
        # No anti-signals but required signals absent → uncertain
        return ValidationDecision.UNCERTAIN

    # All required signals present — score decides pass vs. limited
    if confidence >= _PASS_THRESHOLD:
        return ValidationDecision.PASS
    if confidence >= _UNCERTAIN_THRESHOLD:
        return ValidationDecision.PASS_LIMITED
    return ValidationDecision.UNCERTAIN


def _collect_warnings(
    matched: list[MatchedSignal],
    missing_required: list[str],
    anti_signals: list[str],
) -> list[str]:
    """Collect all non-fatal warning strings."""
    warnings: list[str] = []

    for ms in matched:
        if ms.dtype_warning:
            warnings.append(ms.dtype_warning)

    if anti_signals:
        labels = ", ".join(anti_signals)
        warnings.append(
            f"Dataset contains column names associated with non-e-commerce domains: {labels}."
        )

    return warnings


def _build_explanation(
    *,
    decision: ValidationDecision,
    matched: list[MatchedSignal],
    missing_required: list[str],
    anti_signals: list[str],
    available_caps: list[EcommerceCapability],
    unavailable_caps: list[EcommerceCapability],
    confidence: float,
) -> str:
    """Build a human-readable explanation of the validation outcome."""
    parts: list[str] = []

    # Decision summary
    match decision:
        case ValidationDecision.PASS:
            parts.append(
                f"Dataset accepted as e-commerce transaction data "
                f"(confidence: {confidence:.0%})."
            )
        case ValidationDecision.PASS_LIMITED:
            parts.append(
                f"Dataset accepted as e-commerce data with limited capabilities "
                f"(confidence: {confidence:.0%})."
            )
        case ValidationDecision.UNCERTAIN:
            parts.append(
                f"Dataset could not be confidently classified as e-commerce data "
                f"(confidence: {confidence:.0%})."
            )
        case ValidationDecision.REJECT:
            parts.append(
                f"Dataset rejected: does not meet the e-commerce domain contract "
                f"(confidence: {confidence:.0%})."
            )

    # Detected signals
    if matched:
        signal_list = ", ".join(ms.signal_name for ms in matched)
        parts.append(f"Detected signals: {signal_list}.")

    # Missing required
    if missing_required:
        missing_list = ", ".join(missing_required)
        parts.append(
            f"Missing required signals: {missing_list}. "
            "These are necessary to classify the dataset as e-commerce transaction data."
        )

    # Anti-signals
    if anti_signals:
        anti_list = ", ".join(anti_signals)
        parts.append(
            f"Non-e-commerce domain indicators detected: {anti_list}. "
            "These columns suggest the dataset may belong to a different domain."
        )

    # Capabilities
    if available_caps:
        caps_list = ", ".join(c.value for c in available_caps)
        parts.append(f"Available analytical capabilities: {caps_list}.")
    if unavailable_caps:
        unavail_list = ", ".join(c.value for c in unavailable_caps)
        parts.append(
            f"Unavailable capabilities (missing optional signals): {unavail_list}."
        )

    return " ".join(parts)
