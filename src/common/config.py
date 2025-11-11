from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # Leads
    # TODO: Add leads settings

    GOOGLE_SEARCH_ENGINE_ID: str = ""
    GOOGLE_SEARCH_API_KEY: SecretStr = SecretStr("")

    # Orbis (company information)
    orbis_base_url: str = ""
    orbis_api_key: SecretStr = SecretStr("")

    # Serper (web search)
    serper_base_url: str = "https://google.serper.dev/search"
    serper_api_key: SecretStr = SecretStr("")

    # Segment (user profiles)
    segment_api_key: SecretStr = SecretStr("")
    segment_space_id: SecretStr = SecretStr("")

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
