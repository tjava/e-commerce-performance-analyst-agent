"""Typed environment configuration for the application."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from ecommerce_analyst.domain.enums.environment import ApplicationEnvironment

_ENV_PREFIX = "ECOMMERCE_ANALYST_"

_ENV_TO_FIELD = {
    "ENV": "app_environment",
    "LOG_LEVEL": "log_level",
    "LLM_PROVIDER": "llm_provider",
    "LLM_MODEL": "llm_model",
    "LLM_API_KEY": "llm_api_key",
    "RAW_DATA_DIR": "raw_data_dir",
    "PROCESSED_DATA_DIR": "processed_data_dir",
    "SAMPLE_DATA_DIR": "sample_data_dir",
}

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    app_environment: ApplicationEnvironment = ApplicationEnvironment.LOCAL
    log_level: str = "INFO"
    llm_provider: str = "none"
    llm_model: str | None = None
    llm_api_key: SecretStr | None = Field(default=None, repr=False)
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    sample_data_dir: Path = Path("data/sample")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Validate and normalize the configured log level."""

        normalized = value.upper()
        if normalized not in _VALID_LOG_LEVELS:
            valid_levels = ", ".join(sorted(_VALID_LOG_LEVELS))
            raise ValueError(f"Invalid log level {value!r}. Expected one of: {valid_levels}.")
        return normalized

    @field_validator("llm_provider")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        """Normalize provider names so configuration comparisons are stable."""

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError(
                "LLM provider cannot be empty. Use 'none' when no provider is configured."
            )
        return normalized

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> Self:
        """Require an API key only when an LLM provider is configured."""

        if self.llm_provider != "none" and self.llm_api_key is None:
            raise ValueError(
                "ECOMMERCE_ANALYST_LLM_API_KEY is required when "
                "ECOMMERCE_ANALYST_LLM_PROVIDER is not 'none'."
            )
        return self


def load_settings(
    *,
    env_file: str | Path | None = ".env",
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load typed settings from a dotenv file and environment variables."""

    source: Mapping[str, str]
    if environ is None:
        if env_file is not None:
            load_dotenv(dotenv_path=env_file, override=False)
        source = os.environ
    else:
        source = environ

    values = _extract_prefixed_settings(source)
    return Settings.model_validate(values)


def _extract_prefixed_settings(source: Mapping[str, str]) -> dict[str, str]:
    """Map known environment variables onto Settings field names."""

    values: dict[str, str] = {}
    for env_name, field_name in _ENV_TO_FIELD.items():
        full_name = f"{_ENV_PREFIX}{env_name}"
        raw_value = source.get(full_name)
        if raw_value is not None and raw_value != "":
            values[field_name] = raw_value
    return values
