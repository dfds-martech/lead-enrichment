from agents import function_tool

from common.logging import get_logger
from services.serper_search.client import WebSearchService
from services.serper_search.schemas import SearchResult

logger = get_logger(__name__)


@function_tool
async def search_web(query: str, max_results: int = 8) -> SearchResult:
    """
    Search the web using Serper.dev API and return structured results.

    Args:
        query (str): The search query to execute.
        max_results (int, optional): Max number of results to return.

    Returns:
        SearchResult: Structured search result with hits and metadata.
    """
    logger.info(f"Serper search tool called with query: {query}")
    try:
        ws = WebSearchService()
        response = await ws.search(query, max_results)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception in search_web: {e}", exc_info=True)
        return SearchResult(
            success=False,
            query=query,
            hits=[],
            engine=None,
            credits_used=None,
            error=str(e),
        )
