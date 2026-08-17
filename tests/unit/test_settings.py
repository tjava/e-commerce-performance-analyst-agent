import pytest
from pydantic import ValidationError

from ecommerce_analyst.domain.enums.environment import ApplicationEnvironment
from ecommerce_analyst.infrastructure.config import load_settings


def test_settings_load_defaults_without_dotenv() -> None:
    settings = load_settings(env_file=None, environ={})

    assert settings.app_environment is ApplicationEnvironment.LOCAL
    assert settings.log_level == "INFO"
    assert settings.llm_provider == "none"
    assert settings.max_upload_size_bytes == 10 * 1024 * 1024


def test_settings_load_from_prefixed_environment() -> None:
    settings = load_settings(
        env_file=None,
        environ={
            "ECOMMERCE_ANALYST_ENV": "test",
            "ECOMMERCE_ANALYST_LOG_LEVEL": "debug",
            "ECOMMERCE_ANALYST_LLM_PROVIDER": "openai",
            "ECOMMERCE_ANALYST_LLM_API_KEY": "test-key",
            "ECOMMERCE_ANALYST_RAW_DATA_DIR": "/tmp/raw",
            "ECOMMERCE_ANALYST_MAX_UPLOAD_SIZE_BYTES": "1024",
        },
    )

    assert settings.app_environment is ApplicationEnvironment.TEST
    assert settings.log_level == "DEBUG"
    assert settings.llm_provider == "openai"
    assert settings.raw_data_dir.as_posix() == "/tmp/raw"
    assert settings.dataset_ingestion_limits().max_file_size_bytes == 1024


def test_settings_require_api_key_when_llm_provider_is_configured() -> None:
    with pytest.raises(ValidationError, match="ECOMMERCE_ANALYST_LLM_API_KEY is required"):
        load_settings(
            env_file=None,
            environ={
                "ECOMMERCE_ANALYST_LLM_PROVIDER": "openai",
            },
        )
