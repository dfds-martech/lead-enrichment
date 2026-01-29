from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    ENVIRONMENT: str = Field(default="development")

    # Leads
    # TODO: Add leads settings

    # Google Search (web search)
    GOOGLE_SEARCH_URL: str = "https://www.googleapis.com/customsearch/v1"
    GOOGLE_SEARCH_ENGINE_ID: str = ""
    GOOGLE_SEARCH_API_KEY: SecretStr = SecretStr("")

    # Orbis (company information)
    ORBIS_BASE_URL: str = ""
    ORBIS_API_KEY: SecretStr = SecretStr("")

    # Serper (web search)
    SERPER_BASE_URL: str = "https://google.serper.dev/search"
    SERPER_API_KEY: SecretStr = SecretStr("")

    # Segment (user profiles)
    SEGMENT_WRITE_KEY_ID: str = ""
    SEGMENT_API_KEY: SecretStr = SecretStr("")
    SEGMENT_SPACE_ID: SecretStr = SecretStr("")

    # Service Bus
    SERVICE_BUS_ENABLED: bool = True
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: SecretStr = SecretStr("")
    SERVICE_BUS_NAMESPACE: str = ""
    SERVICE_BUS_TOPIC_NAME: str = ""
    SERVICE_BUS_SUBSCRIPTION_NAME: str = ""
    SERVICE_BUS_USE_WEBSOCKET: bool = Field(
        default=False,
        description="Use WebSocket transport for VPN compatibility (slower, port 443 vs standard AMQP port 5671)",
    )

    # GCP & BigQuery
    GCPPROJECTID: str = ""  # Used for Secret Manager project path
    BQPROJECTID: str = ""
    BQDATASETID: str = ""
    BQTABLEID: str = ""

    # OpenAI
    AZURE_GIT_TOKEN: str = ""
    AZURE_OPENAI_API_KEY: SecretStr = SecretStr("")
    AZURE_OPENAI_ENDPOINT: str = ""

    # LLM settings
    openai_model: str = "gpt-4.1-mini"
    temperature: float = 0.0
    max_retries: int = 3
    retry_delay: int = 2
    retry_multiplier: int = 2
    retry_max: int = 20

    # Logging
    log_level: str = "INFO"
    log_format: str = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), case_sensitive=False, extra="ignore")


config = Config()
