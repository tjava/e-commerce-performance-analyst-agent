"""Provider-neutral LLM interface definitions."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Minimal interface for future LLM-backed reasoning services."""

    def provider_name(self) -> str:
        """Return the configured provider name without exposing secrets."""
