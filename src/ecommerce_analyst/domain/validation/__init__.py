"""E-commerce domain validation package.

Exports the public surface needed by the application layer.
"""

from ecommerce_analyst.domain.validation.enums import (
    EcommerceCapability,
    SignalStrength,
    ValidationDecision,
)
from ecommerce_analyst.domain.validation.result import DomainValidationResult, MatchedSignal
from ecommerce_analyst.domain.validation.signals import DomainSignal

__all__ = [
    "DomainSignal",
    "DomainValidationResult",
    "EcommerceCapability",
    "MatchedSignal",
    "SignalStrength",
    "ValidationDecision",
]
