"""Configuration properties example."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from pythonboot import configuration, configuration_properties


@configuration
@configuration_properties("health")
class HealthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PYTHONBOOT_HEALTH_")
    status: str = "ok"

