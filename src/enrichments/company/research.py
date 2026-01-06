"""
Company research stage.

Uses web search and scraping to find company information:
- Company domain
- National ID / registration number
- Additional company details
"""

from agents import Runner

from common.logging import get_logger
from common.openai_errors import handle_openai_errors
from custom_agents.company_research import CompanyResearchResult, create_company_research_agent
from models.company import CompanyResearchCriteria

logger = get_logger(__name__)


async def research_company(criteria: CompanyResearchCriteria) -> CompanyResearchResult:
    """Research company using web search and scraping."""
    logger.info(f"[Research] Starting for: {criteria.name}")

    try:
        research_agent = create_company_research_agent()
        logger.debug("[Research] Agent created successfully")
    except Exception as e:
        logger.error(f"[Research] Failed to create agent: {type(e).__name__}: {e}")
        raise

    research_input = criteria.to_prompt()
    logger.debug(f"[Research] Input prompt length: {len(research_input)} chars")

    with handle_openai_errors("Research"):
        logger.debug("[Research] Calling Runner.run()...")
        run_result = await Runner.run(research_agent, research_input)
        logger.debug(f"[Research] Runner.run() completed, result type: {type(run_result)}")

    result = run_result.final_output

    if result is None:
        logger.error("[Research] final_output is None")
        raise ValueError("Research agent returned None")

    logger.info(f"[Research] Completed - domain: {result.domain}, national_id: {result.national_id}")
    return result
