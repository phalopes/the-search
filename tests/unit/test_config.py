import pytest

from surfscout.config import Environment, Settings

pytestmark = pytest.mark.unit


def test_settings_default_environment_is_dev() -> None:
    settings = Settings(_env_file=None)

    assert settings.env == Environment.DEV
    assert settings.telegram_bot_token is None
