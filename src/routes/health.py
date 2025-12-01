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

    # Overall status
    all_env_set = all(v == "set" for v in checks["env_vars"].values())
    azure_ok = checks["azure_openai"].get("client_created", False)
    checks["status"] = "healthy" if (all_env_set and azure_ok) else "unhealthy"

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
            messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
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


@router.get("/health/test-agent")
async def test_agent():
    """Test the agents SDK with a minimal agent."""
    from agents import Agent, OpenAIChatCompletionsModel, Runner

    from services.azure_openai_service import AzureOpenAIService

    result = {
        "status": "testing",
        "client_creation": {},
        "agent_creation": {},
        "agent_run": {},
    }

    # Step 1: Create client
    try:
        client = AzureOpenAIService.get_async_client()
        result["client_creation"] = {"success": True}
    except Exception as e:
        result["client_creation"] = {"success": False, "error": f"{type(e).__name__}: {e!r}"}
        result["status"] = "failed"
        return result

    # Step 2: Create model and agent
    try:
        model = OpenAIChatCompletionsModel(model=config.openai_model, openai_client=client)
        agent = Agent(name="test-agent", instructions="Reply with exactly: OK", model=model)
        result["agent_creation"] = {"success": True}
    except Exception as e:
        result["agent_creation"] = {"success": False, "error": f"{type(e).__name__}: {e!r}"}
        result["status"] = "failed"
        return result

    # Step 3: Run agent
    try:
        logger.info("[test-agent] Running agent...")
        run_result = await Runner.run(agent, "test")
        logger.info(f"[test-agent] Run completed, result type: {type(run_result)}")
        result["agent_run"] = {
            "success": True,
            "result_type": type(run_result).__name__,
            "final_output_type": type(run_result.final_output).__name__,
            "final_output": str(run_result.final_output)[:100],
        }
        result["status"] = "healthy"
    except Exception as e:
        logger.error(f"[test-agent] Run failed: {type(e).__name__}: {e!r}")
        result["agent_run"] = {
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_repr": repr(e),
        }
        result["status"] = "failed"

    logger.info(f"Agent test result: {result}")
    return result
