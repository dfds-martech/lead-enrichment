"""Health check and service info endpoints."""

from fastapi import APIRouter

from common.config import config
from common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    return {
        "service": "Lead Enrichment API",
        "version": "0.1.0",
        "status": "running",
        "description": "B2B company enrichment with web research and Orbis database matching",
        "endpoints": {
            "health": "/health",
            "ready": "/health/ready",
            "docs": "/docs",
            "enrich_company": "/api/enrich-company",
        },
        "example_request": {
            "name": "WILDWINE LTD",
            "domain": "wildwine.je",
            "city": "London",
            "country": "United Kingdom",
            "phone": "+447797893894",
        },
    }


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "lead-enrichment"}


@router.get("/health/ready")
async def readiness_check():
    checks = {
        "status": "checking",
        "config": {},
        "dependencies": {},
    }

    # TODO: Check config loads
    try:
        _ = config.openai_model
        _ = config.AZURE_OPENAI_ENDPOINT
        checks["config"]["loaded"] = True
        checks["config"]["model"] = config.openai_model
    except Exception as e:
        checks["config"]["loaded"] = False
        checks["config"]["error"] = f"{type(e).__name__}: {e}"

    # TODO: Check critical dependencies
    try:
        from services.azure_openai_service import AzureOpenAIService

        _ = AzureOpenAIService.get_async_client()
        checks["dependencies"]["azure_openai"] = "available"
    except Exception as e:
        checks["dependencies"]["azure_openai"] = "unavailable"
        checks["dependencies"]["error"] = f"{type(e).__name__}: {e}"

    # Overall readiness
    config_ok = checks["config"].get("loaded", False)
    deps_ok = checks["dependencies"].get("azure_openai") == "available"
    checks["status"] = "ready" if (config_ok and deps_ok) else "not_ready"

    return checks


@router.get("/health/debug")
async def debug_check():
    checks = {
        "status": "checking",
        "config": {},
        "services": {},
    }

    # TODO: Check key config values
    try:
        checks["config"]["openai_model"] = config.openai_model
        checks["config"]["azure_endpoint"] = bool(config.AZURE_OPENAI_ENDPOINT)
        checks["config"]["azure_key_set"] = bool(config.AZURE_OPENAI_API_KEY.get_secret_value())
        checks["config"]["serper_key_set"] = bool(config.SERPER_API_KEY.get_secret_value())
        checks["config"]["orbis_key_set"] = bool(config.ORBIS_API_KEY.get_secret_value())
    except Exception as e:
        checks["config"]["error"] = f"{type(e).__name__}: {e}"

    # Test Azure OpenAI connection
    try:
        from services.azure_openai_service import AzureOpenAIService

        client = AzureOpenAIService.get_async_client()
        checks["services"]["azure_openai"] = {
            "client_created": True,
            "client_type": type(client).__name__,
        }
    except Exception as e:
        checks["services"]["azure_openai"] = {
            "client_created": False,
            "error": f"{type(e).__name__}: {e}",
        }

    # Overall status
    config_ok = checks["config"].get("azure_key_set", False) and not checks["config"].get("error")
    azure_ok = checks["services"].get("azure_openai", {}).get("client_created", False)
    checks["status"] = "healthy" if (config_ok and azure_ok) else "unhealthy"

    logger.info(f"Debug check result: {checks}")
    return checks


@router.get("/health/test-llm")
async def test_llm():
    """Test actual LLM call to Azure OpenAI (without agents SDK)."""
    from services.azure_openai_service import AzureOpenAIService

    result = {
        "status": "testing",
        "client_creation": {},
        "api_call": {},
    }

    # Step 1: Create client
    try:
        client = AzureOpenAIService.get_async_client()
        result["client_creation"] = {"success": True}
    except Exception as e:
        result["client_creation"] = {"success": False, "error": f"{type(e).__name__}: {e!r}"}
        result["status"] = "failed"
        return result

    # Step 2: Make a simple API call (not using agents SDK)
    try:
        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[{"role": "user", "content": "Say 'hello world' and nothing else."}],
            max_tokens=10,
        )
        result["api_call"] = {
            "success": True,
            "response_type": type(response).__name__,
            "content": response.choices[0].message.content if response.choices else None,
        }
        result["status"] = "healthy"
    except Exception as e:
        result["api_call"] = {
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_repr": repr(e),
        }
        result["status"] = "failed"

    logger.info(f"LLM test result: {result}")
    return result
