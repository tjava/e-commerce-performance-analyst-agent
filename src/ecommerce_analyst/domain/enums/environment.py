"""Supported application environments."""

from __future__ import annotations

from enum import StrEnum


class ApplicationEnvironment(StrEnum):
    """Runtime environment names used across the application."""

    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"
