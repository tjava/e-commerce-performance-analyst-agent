from ecommerce_analyst.domain.enums.environment import ApplicationEnvironment
from ecommerce_analyst.infrastructure.config.settings import Settings
from ecommerce_analyst.main import initialize_application


def test_application_initializes_without_running_workflow() -> None:
    settings = Settings(app_environment=ApplicationEnvironment.TEST, log_level="CRITICAL")

    context = initialize_application(settings)

    assert context.settings is settings
