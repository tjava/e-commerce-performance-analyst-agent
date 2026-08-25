"""DomainSignal — descriptor for a single e-commerce domain signal."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_analyst.domain.validation.enums import EcommerceCapability, SignalStrength


class DomainSignal(BaseModel):
    """Describes one recognisable signal that contributes to e-commerce domain classification.

    A signal is matched against a dataset's column names (and optionally its values)
    during validation. Each signal is independent and reusable across contract definitions.
    """

    name: str = Field(min_length=1)
    """Canonical programmatic name for this signal (e.g. ``'order_identifier'``)."""

    description: str
    """Human-readable description of what this signal represents."""

    column_aliases: frozenset[str] = Field(default_factory=frozenset)
    """Exact lowercase column names that unambiguously match this signal."""

    keyword_hints: frozenset[str] = Field(default_factory=frozenset)
    """Partial keywords: a column whose normalized name *contains* one of these counts
    as a weaker (keyword) match when no exact alias is found."""

    expected_dtype_patterns: tuple[str, ...] = ()
    """Pandas dtype string prefixes that are acceptable for this column (e.g. ``'int'``,
    ``'float'``, ``'object'``, ``'datetime'``). Empty means any dtype is accepted."""

    value_validator: Callable[[Sequence[Any]], bool] | None = Field(default=None, exclude=True)
    """Optional callable that receives a sample of non-null cell values and returns True
    if they look plausible for this signal. Used for dtype-mismatch warnings only."""

    required: bool = False
    """If True, absence of this signal contributes to a REJECT or UNCERTAIN decision."""

    strength: SignalStrength = SignalStrength.MODERATE
    """How much weight a match contributes to the overall confidence score."""

    capability: EcommerceCapability | None = None
    """Which analytical capability this signal unlocks (if any)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    def matches_column(self, normalized_name: str) -> tuple[bool, bool]:
        """Return ``(is_match, is_exact)`` for a normalised column name.

        ``is_exact`` is True when the name is in ``column_aliases``.
        ``is_exact`` is False when matched only via ``keyword_hints``.
        """
        if normalized_name in self.column_aliases:
            return True, True
        if any(hint in normalized_name for hint in self.keyword_hints):
            return True, False
        return False, False

    def dtype_compatible(self, inferred_dtype: str) -> bool:
        """Return True when the column's inferred dtype is acceptable for this signal."""
        if not self.expected_dtype_patterns:
            return True
        dtype_lower = inferred_dtype.lower()
        return any(dtype_lower.startswith(p) for p in self.expected_dtype_patterns)
