import httpx
from googleapiclient.discovery import build

from common.config import config
from common.logging import get_logger
from services.google_search.schemas import GoogleSearchRequest, GoogleSearchResponse

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 30.0


class GoogleSearchClient:
    def __init__(self):
        self.search_engine_id = config.GOOGLE_SEARCH_ENGINE_ID
        self._api_key = config.GOOGLE_SEARCH_API_KEY.get_secret_value()
        self.service = build("customsearch", "v1", developerKey=self._api_key)

    async def search(self, request: GoogleSearchRequest) -> GoogleSearchResponse:
        """
        Send async search request to Google Custom Search API.

        Example:
            # Basic
            request = GoogleSearchRequest(query="DFDS Copenhagen")
            result = client.search(request)

            # With langugae and country filters
            request = GoogleSearchRequest(
                query="DFDS",
                language="lang_da",
                country="countryDK",
                num_results=5
            )
            result = client.search(request)
        """
        request.validate_request()
        params = request.to_api_params(self.search_engine_id)
        params["key"] = self._api_key

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                response = await client.get(config.GOOGLE_SEARCH_URL, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Google Search returned {len(data.get('items', []))} results")
                return GoogleSearchResponse.from_dict(data)

            except httpx.HTTPStatusError as e:
                error_body = e.response.text if e.response else "No response body"
                raise Exception(f"Google Search API failed (status: {e.response.status_code}): {error_body}") from e
            except httpx.RequestError as e:
                raise Exception(f"Search request failed: {str(e)}") from e
