"""
Company enrichment orchestrator.

Orchestrates the 4-stage company enrichment process:
1. Research - web search and scraping to find company information
2. Match - find the company in Orbis database using enriched data
3. Details - fetch detailed financial/employee data from Orbis
4. Features - extract categorized features from company data
"""

import asyncio
import json
import random
from functools import wraps
from typing import Callable, TypeVar

from agents import Agent, Runner

from common.logging import get_logger
from common.openai_errors import handle_openai_errors
from enrichments.company.features import extract_company_features
from enrichments.company.schemas import CompanyEnrichmentResult
from models.company import CompanyResearchCriteria
from models.lead import Lead
from services.orbis.client import OrbisClient
from services.orbis.schemas import OrbisCompanyDetails

from .agents.company_match import CompanyMatchResult, create_company_match_agent
from .agents.company_research import CompanyResearchResult, create_company_research_agent

logger = get_logger(__name__)

T = TypeVar("T")


# Retry helpers


def _calculate_backoff_delay(attempt: int, base_delay: float = 3.0) -> float:
    """Calculate exponential backoff delay with jitter."""

    delay = base_delay * (2 ** (attempt - 1))  # Exponential: 3s, 6s, 12s
    jitter = delay * 0.2 * (2 * random.random() - 1)  # ±20% (avoid synchronized retries)
    return delay + jitter


def _should_retry_error(error: Exception, current_attempt: int, max_attempts: int) -> tuple[bool, float | None]:
    """Determine if an error should be retried and calculate delay."""

    if current_attempt >= max_attempts:
        return False, None
    
    error_msg = str(error)
    
    # Rate limit errors: exponential backoff with jitter
    if isinstance(error, RuntimeError) and "rate limit" in error_msg.lower():
        return True, _calculate_backoff_delay(current_attempt)
    
    # ModelBehaviorError (invalid JSON from AI): linear backoff
    if "ModelBehaviorError" in error_msg and "Invalid JSON" in error_msg:
        return True, float(current_attempt)  # 1s, 2s, 3s
    
    # Returns "should retry", "delay_seconds"
    return False, None


def with_retry(operation_name: str, max_attempts: int = 3):
    """
    Decorator to add retry logic with exponential backoff to async functions.
    
    Automatically retries on:
    - Rate limit errors (429) with exponential backoff + jitter
    - ModelBehaviorError (invalid JSON) with linear backoff
    
    Args:
        operation_name: Name for logging (e.g., "Research", "Match")
        max_attempts: Maximum number of attempts (default 3)
    
    Example:
        @with_retry("Research", max_attempts=3)
        async def _research(self, criteria):
            return await some_api_call(criteria)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, max_attempts + 1):
                try:
                    if attempt > 1:
                        logger.debug(f"[{operation_name}] Attempt {attempt}/{max_attempts}")
                    return await func(*args, **kwargs)
                
                except Exception as e:
                    should_retry, delay = _should_retry_error(e, attempt, max_attempts)
                    
                    if should_retry and delay is not None:
                        error_type = "Rate limit" if "rate limit" in str(e).lower() else "Invalid JSON"
                        logger.warning(
                            f"[{operation_name}] {error_type} error (attempt {attempt}/{max_attempts}). "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    # Not retryable or final attempt - re-raise
                    raise
            
            # Should never reach here, but for type safety
            raise RuntimeError(f"[{operation_name}] Exhausted all {max_attempts} attempts")
        
        return wrapper
    return decorator


class CompanyEnricher:
    """Company enrichment orchestrator with lazy-loaded agents."""

    def __init__(self):
        self._research_agent: Agent[CompanyResearchResult] | None = None
        self._match_agent: Agent[CompanyMatchResult] | None = None
        self._orbis_client: OrbisClient | None = None

    # Lazy-load agents and orbis client

    @property
    def research_agent(self) -> Agent[CompanyResearchResult]:
        if self._research_agent is None:
            self._research_agent = create_company_research_agent()
        return self._research_agent

    @property
    def match_agent(self) -> Agent[CompanyMatchResult]:
        if self._match_agent is None:
            self._match_agent = create_company_match_agent()
        return self._match_agent

    @property
    def orbis_client(self) -> OrbisClient:
        if self._orbis_client is None:
            self._orbis_client = OrbisClient()
        return self._orbis_client

    # Research stage / web search and scraping helpers

    @with_retry("Research", max_attempts=3)
    async def _research(self, criteria: CompanyResearchCriteria) -> CompanyResearchResult:
        """Execute research agent with automatic retry on rate limits and invalid JSON."""
        
        logger.info(f"[Research] Starting for: {criteria.name}")
        research_input = criteria.to_prompt()
        logger.debug(f"[Research] Prompt length: {len(research_input)} chars")

        with handle_openai_errors("Research"):
            logger.debug("[Research] Runner.run()...start")
            run_result = await Runner.run(self.research_agent, research_input)
            logger.debug(f"[Research] Runner.run()...complete, result type: {type(run_result)}")

        result = run_result.final_output
        if result is None:
            logger.error("[Research] final_output is None")
            raise ValueError("Research agent returned None")

        logger.info(f"[Research] Completed - domain: {result.domain}, national_id: {result.national_id}")
        return result
    
    # Match stage / Orbis matching helpers

    @with_retry("Match", max_attempts=3)
    async def _match(
        self, criteria: CompanyResearchCriteria, research_result: CompanyResearchResult | None
    ) -> CompanyMatchResult:
        """Execute match agent with automatic retry on rate limits."""
        logger.info(f"[Match] Starting for: {criteria.name}")

        match_input = {
            "original": criteria.model_dump(exclude_none=True),
            "enriched": research_result.model_dump(exclude_none=True) if research_result else {},
        }
        logger.debug(f"[Match] Input has enriched data: {research_result is not None}")

        with handle_openai_errors("Match"):
            logger.debug("[Match] Calling Runner.run()...")
            run_result = await Runner.run(self.match_agent, json.dumps(match_input))
            logger.debug(f"[Match] Runner.run() completed, result type: {type(run_result)}")

        result = run_result.final_output
        if result is None:
            logger.error("[Match] final_output is None")
            raise ValueError("Match agent returned None")

        logger.info(f"[Match] Completed - Confidence: {result.confidence}")
        return result

    async def _fetch_details(self, bvd_id: str) -> OrbisCompanyDetails | None:
        logger.info(f"[Details] Fetching company details for BvD ID: {bvd_id}")

        try:
            company_details = self.orbis_client.company_lookup_by_bvd(bvd_id)
        except Exception as e:
            logger.error(f"[Details] Failed to fetch company details: {e}", exc_info=True)
            return None

        if not company_details:
            logger.warning(f"[Details] Fetch returned None for BvD ID: {bvd_id}")
            return None

        logger.info(f"[Details] fetched: {company_details.name} (BvD ID: {company_details.bvd_id})")
        return company_details

    # CompanyEnrichment pipeline orchestrator

    async def enrich(self, lead: Lead) -> CompanyEnrichmentResult:
        """Run company enrichment through all stages."""
        criteria = lead.company_research_criteria

        company_research = None
        company_match = None
        company_details = None
        features = None
        errors: list[str] = []

        # Stage 1: Research (best effort)
        try:
            company_research = await self._research(criteria)
        except Exception as e:
            errors.append(f"research: {type(e).__name__}: {e}")
            logger.warning(f"[Enrichment] Research failed: {e!r}")

        # Stage 2: Company Match (best effort)
        try:
            company_match = await self._match(criteria, company_research)
        except Exception as e:
            errors.append(f"match: {type(e).__name__}: {e}")
            logger.warning(f"[Enrichment] Match failed: {e!r}")

        # Stage 3: Company Details (best effort)
        if company_match and company_match.company:
            try:
                company_details = await self._fetch_details(company_match.company.bvd_id)
            except Exception as e:
                errors.append(f"details: {type(e).__name__}: {e}")
                logger.warning(f"[Enrichment] Details fetch failed: {e!r}")

        # Stage 4: Feature Extraction (best effort)
        try:
            features = extract_company_features(company_research, company_match, company_details)
        except Exception as e:
            errors.append(f"features: {type(e).__name__}: {e}")
            logger.warning(f"[Enrichment] Feature extraction failed: {e!r}")

        # Log final status
        if errors:
            logger.warning(f"[Enrichment] Completed with {len(errors)} error(s): {errors}")
        else:
            logger.info("[Enrichment] Completed successfully")

        # TODO: when do we actually fail a company enrichment?
        # We need to make some kind of decision on what to do when we have errors.

        return CompanyEnrichmentResult(
            research=company_research,
            match=company_match,
            details=company_details,
            features=features,
            error="; ".join(errors) if errors else None,
        )
