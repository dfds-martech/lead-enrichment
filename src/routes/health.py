"""Health check and service info endpoints."""

import os

from fastapi import APIRouter

from common.config import config
from common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "Lead Enrichment API",
        "version": "0.1.0",
        "status": "running",
        "description": "B2B company enrichment with web research and Orbis database matching",
        "endpoints": {
            "health": "/health",
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
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "service": "lead-enrichment"}


@router.get("/health/debug")
async def debug_check():
    """Debug endpoint to verify configuration and connections."""
    checks = {
        "status": "checking",
        "config": {},
        "azure_openai": {},
        "env_vars": {},
    }

    # Check critical env vars (don't expose values, just presence)
    env_checks = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "SERPER_API_KEY",
        "ORBIS_API_KEY",
    ]
    for var in env_checks:
        value = os.environ.get(var)
        checks["env_vars"][var] = "set" if value else "MISSING"

    # Check config
    checks["config"]["openai_model"] = config.openai_model
    checks["config"]["azure_endpoint_set"] = bool(config.azure_openai_endpoint)
    checks["config"]["azure_key_set"] = bool(config.azure_openai_api_key.get_secret_value())

    # Test Azure OpenAI connection
    try:
        from services.azure_openai_service import AzureOpenAIService

        client = AzureOpenAIService.get_async_client()
        checks["azure_openai"]["client_created"] = True
        checks["azure_openai"]["client_type"] = type(client).__name__
    except Exception as e:
        checks["azure_openai"]["client_created"] = False
        checks["azure_openai"]["error"] = f"{type(e).__name__}: {e}"

    # try:
    #     from agents import Agent, Runner
    #     test_agent = Agent(name="test", instructions="Say hello")
    #     result = await Runner.run(test_agent, "test")
    #     checks["agent_test"] = {"success": True, "output_type": type(result.final_output).__name__}
    # except Exception as e:
    #     checks["agent_test"] = {"success": False, "error": f"{type(e).__name__}: {e}"}

    # Overall status
    all_env_set = all(v == "set" for v in checks["env_vars"].values())
    azure_ok = checks["azure_openai"].get("client_created", False)
    checks["status"] = "healthy" if (all_env_set and azure_ok) else "unhealthy"

    logger.info(f"Debug check result: {checks}")
    return checks
