"""
OpenAI error handling utilities.

Provides a context manager for consistent error handling across
all OpenAI API operations in the enrichment pipeline.
"""

from collections.abc import Generator
from contextlib import contextmanager

from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

from common.logging import get_logger
from services.azure_openai_service import format_openai_error

logger = get_logger(__name__)

# All OpenAI exceptions that should be handled consistently
OPENAI_EXCEPTIONS = (
    PermissionDeniedError,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APIError,
)


@contextmanager
def handle_openai_errors(operation_name: str) -> Generator[None, None, None]:
    """
    Context manager for handling OpenAI errors consistently.

    Catches OpenAI-specific exceptions, formats them with clear messages,
    logs them, and re-raises as RuntimeError with the formatted message.

    Args:
        operation_name: Name of the operation (e.g., "Research", "Match")
            Used in log messages for context.

    Usage:
        with handle_openai_errors("Research"):
            run_result = await Runner.run(agent, input)

    Raises:
        RuntimeError: If an OpenAI exception occurs, with a formatted error message.
        Exception: Re-raises any other exceptions after logging.
    """
    try:
        yield
    except OPENAI_EXCEPTIONS as e:
        error_msg = format_openai_error(e)
        logger.error(f"[{operation_name}] OpenAI API error: {error_msg}")
        raise RuntimeError(error_msg) from e
    except Exception as e:
        logger.error(f"[{operation_name}] Failed: {type(e).__name__}: {e!r}")
        raise
