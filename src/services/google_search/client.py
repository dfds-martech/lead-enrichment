import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from common.config import config
from services.google_search.schemas import GoogleSearchRequest, GoogleSearchResponse

logger = logging.getLogger(__name__)


class GoogleSearchClient:
    def __init__(self):
        self._api_key = config.GOOGLE_SEARCH_API_KEY.get_secret_value()
        self.search_engine_id = config.GOOGLE_SEARCH_ENGINE_ID
        self.service = build("customsearch", "v1", developerKey=self._api_key)

    def search(self, request: GoogleSearchRequest) -> GoogleSearchResponse:
        """
        Send search request to Google Custom Search API.
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

        try:
            logger.info(str(request))
            params = request.to_api_params(self.search_engine_id)
            result = self.service.cse().list(**params).execute()
            logger.info(f"Google Search API returned results: {len(result.get('items', []))}")

            return GoogleSearchResponse.from_dict(result)

        except HttpError as e:
            error_detail = e.error_details if hasattr(e, "error_details") else str(e)
            raise Exception(f"Google Search API failed (status: {e.resp.status}): {error_detail}") from e
        except Exception as e:
            raise Exception(f"Search request failed: {str(e)}") from e
