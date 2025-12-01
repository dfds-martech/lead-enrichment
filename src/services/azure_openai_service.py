"""
Simple AzureOpenAI service

Example:
  from services.azure_openai_service import AzureOpenAIService

  # Default client (gpt-4o-mini)
  client = AzureOpenAIService.get_client()

  # Specific model
  client = AzureOpenAIService.get_client(model="gpt-4.1-mini")

  # Custom client for testing
  test_client = AzureOpenAIService.create_custom_client(api_key="test_key")
"""

from openai import AzureOpenAI, OpenAI

from common.config import config
from common.logging import get_logger

logger = get_logger(__name__)

# private_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AzureOpenAIService:
    MODELS_API_VERSIONS: dict[str, str] = {
        "gpt-4o-mini": "2024-12-01-preview",  # 2024-12-01-preview
        "gpt-4.1-mini": "2025-01-01-preview",
    }

    DEFAULT_MODEL = "gpt-4.1-mini"
    # AZURE_ENDPOINT = "https://cog-lead-qualification-002.openai.azure.com/"
    AZURE_ENDPOINT = "https://cog-dev-pace-llm.openai.azure.com/"

    _clients: dict[str, AzureOpenAI] = {}

    @classmethod
    def get_client(cls, model: str = DEFAULT_MODEL) -> AzureOpenAI | OpenAI:
        """Get Azure OpenAI client for specified model (cached)"""

        # return private_client

        model = model
        logger.info(f"Getting client for model: {model}")

        if model not in cls._clients:
            cls._clients[model] = cls._create_client(model)

        return cls._clients[model]

    @classmethod
    def _create_client(cls, model: str) -> AzureOpenAI:
        api_key = config.openai_key
        if not api_key:
            raise ValueError("OPENAI_KEY environment variable is required")

        if model not in cls.MODELS_API_VERSIONS:
            available = ", ".join(cls.MODELS_API_VERSIONS.keys())
            raise ValueError(f"Unknown model '{model}'. Available models: {available}")

        return AzureOpenAI(
            api_key=api_key,
            api_version=cls.MODELS_API_VERSIONS[model],
            azure_endpoint=cls.AZURE_ENDPOINT,
        )

    @classmethod
    def get_available_models(cls) -> list[str]:
        return list(cls.MODELS_API_VERSIONS.keys())

    @classmethod
    def clear_cache(cls) -> None:
        cls._clients.clear()
