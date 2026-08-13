"""Centralized logging configuration."""

from __future__ import annotations

import logging

from ecommerce_analyst.infrastructure.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure application logging with consistent formatting."""

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )
