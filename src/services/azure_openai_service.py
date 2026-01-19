"""
Simple AzureOpenAI service

Example:
  from services.azure_openai_service import AzureOpenAIService

  # Sync client (for regular OpenAI API calls)
  client = AzureOpenAIService.get_client()
  client = AzureOpenAIService.get_client(model="gpt-4.1-mini")

  # Async client (for agents SDK and async operations)
  async_client = AzureOpenAIService.get_async_client()
  async_client = AzureOpenAIService.get_async_client(model="gpt-4.1-mini")
"""

from openai import (
    APIConnectionError,
    APIError,
    AsyncAzureOpenAI,
    AuthenticationError,
    AzureOpenAI,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from common.config import config
from common.logging import get_logger

logger = get_logger(__name__)

# private_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AzureOpenAIService:
    MODELS_API_VERSIONS: dict[str, str] = {
        "gpt-4o-mini": "2025-03-01-preview",  # "2024-12-01-preview",  # 2024-12-01-preview
        "gpt-4.1-mini": "2025-03-01-preview",  # "2025-01-01-preview",
    }

    DEFAULT_MODEL = "gpt-4.1-mini"

    _clients: dict[str, AzureOpenAI] = {}
    _async_clients: dict[str, AsyncAzureOpenAI] = {}

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
        api_key = config.AZURE_OPENAI_API_KEY.get_secret_value()
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")

        if model not in cls.MODELS_API_VERSIONS:
            available = ", ".join(cls.MODELS_API_VERSIONS.keys())
            raise ValueError(f"Unknown model '{model}'. Available models: {available}")

        return AzureOpenAI(
            api_key=api_key,
            api_version=cls.MODELS_API_VERSIONS[model],
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        )

    @classmethod
    def _create_async_client(cls, model: str) -> AsyncAzureOpenAI:
        api_key = config.AZURE_OPENAI_API_KEY.get_secret_value()
        if not api_key:
            logger.error("[AzureOpenAI] AZURE_OPENAI_API_KEY is missing or empty")
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")

        if model not in cls.MODELS_API_VERSIONS:
            available = ", ".join(cls.MODELS_API_VERSIONS.keys())
            logger.error(f"[AzureOpenAI] Unknown model '{model}'. Available: {available}")
            raise ValueError(f"Unknown model '{model}'. Available models: {available}")

        endpoint = config.AZURE_OPENAI_ENDPOINT
        api_version = cls.MODELS_API_VERSIONS[model]
        logger.info(
            f"[AzureOpenAI] Creating async client - model: {model}, endpoint: {endpoint}, api_version: {api_version}"
        )

        return AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )

    @classmethod
    def get_async_client(cls, model: str = DEFAULT_MODEL) -> AsyncAzureOpenAI:
        """
        Get async Azure OpenAI client for specified model (cached)
        Use this for agents SDK and async operations.
        """
        logger.info(f"Getting async client for model: {model}")

        if model not in cls._async_clients:
            cls._async_clients[model] = cls._create_async_client(model)

        return cls._async_clients[model]

    @classmethod
    def get_available_models(cls) -> list[str]:
        return list(cls.MODELS_API_VERSIONS.keys())

    @classmethod
    def clear_cache(cls) -> None:
        """Clear both sync and async client caches."""
        cls._clients.clear()
        cls._async_clients.clear()


def format_openai_error(e: Exception) -> str:
    """Extract a clean error message from OpenAI SDK exceptions."""
    error_type = type(e).__name__

    # Handle OpenAI-specific errors with better messages
    if isinstance(e, PermissionDeniedError):
        return f"Azure OpenAI access denied: {e.message}"
    elif isinstance(e, AuthenticationError):
        return f"Azure OpenAI authentication failed: {e.message}"
    elif isinstance(e, RateLimitError):
        return f"Azure OpenAI rate limit exceeded: {e.message}"
    elif isinstance(e, APIConnectionError):
        return f"Cannot connect to Azure OpenAI: {e.message}"
    elif isinstance(e, APIError):
        return f"Azure OpenAI API error ({e.status_code}): {e.message}"

    # For other exceptions, return type and message
    return f"{error_type}: {e}"
