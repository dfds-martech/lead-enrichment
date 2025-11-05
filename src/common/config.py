import sys

from loguru import logger
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # Orbis
    # TODO: Add Orbis settings

    # Leads
    # TODO: Add leads settings

    # Orbis (company information)
    orbis_base_url: str = ""
    orbis_api_key: SecretStr = SecretStr("")

    # Serper (web search)
    serper_api_key: str = ""

    # Segment (user profiles)
    segment_api_key: str = ""
    segment_space_id: str = ""

    # OpenAI
    azure_git_token: str = ""
    openai_key: str = ""
    openai_endpoint: str = "https://cog-lead-qualification-002.openai.azure.com/"
    openai_model: str = "gpt-4.1-mini"

    # LLM settings
    temperature: float = 0.0
    max_retries: int = 3
    retry_delay: int = 2
    retry_multiplier: int = 2
    retry_max: int = 20

    # Logging
    log_level: str = "INFO"
    log_format: str = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


config = Config()


# Loguru config
logger.remove()
logger.add(sys.stderr, format=config.log_format, level=config.log_level, colorize=True)


def get_logger(name: str | None = None):
    return logger.bind(name=name) if name else logger
