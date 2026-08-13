"""Application entry point for foundation initialization."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from ecommerce_analyst.infrastructure.config.settings import Settings, load_settings
from ecommerce_analyst.infrastructure.logging.configure import configure_logging


@dataclass(frozen=True, slots=True)
class ApplicationContext:
    """Runtime objects needed by application entry points."""

    settings: Settings


def initialize_application(settings: Settings | None = None) -> ApplicationContext:
    """Initialize configuration and logging without running analytics workflows."""

    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings)

    logger = logging.getLogger(__name__)
    logger.info(
        "Application foundation initialized",
        extra={
            "app_environment": resolved_settings.app_environment.value,
            "llm_provider": resolved_settings.llm_provider,
        },
    )

    return ApplicationContext(settings=resolved_settings)


def main() -> int:
    """Run the minimal application startup check."""

    try:
        initialize_application()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print("E-commerce Performance Analyst foundation initialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
