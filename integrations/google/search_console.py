from dataclasses import dataclass
from datetime import date, timedelta

from integrations.base import (
    IntegrationAuthError,
    IntegrationConfigError,
    IntegrationConnectionError,
    IntegrationError,
    IntegrationRateLimitError,
)
from integrations.google._auth import build_google_credentials

_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


@dataclass
class SearchQuery:
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


@dataclass
class PagePerformance:
    url: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class SearchConsoleAdapter:
    def __init__(
        self,
        site_url: str,
        *,
        credentials_file: str | None = None,
        refresh_token: str | None = None,
        client_id: str = "",
        client_secret: str = "",
    ):
        """
        Accepts either a service-account file (legacy) or an OAuth refresh token (Phase 3).
        Exactly one of credentials_file / refresh_token must be provided.
        """
        if not site_url:
            raise IntegrationConfigError("GSC site URL is required.")
        if not credentials_file and not refresh_token:
            raise IntegrationConfigError(
                "Either credentials_file or refresh_token must be provided."
            )

        self._site_url = site_url

        try:
            from googleapiclient.discovery import build as _build
            from googleapiclient.errors import HttpError
        except ImportError as e:
            raise ImportError(
                "Google API libraries not installed. "
                "Run: pip install google-api-python-client google-auth"
            ) from e

        self._HttpError = HttpError

        try:
            credentials = build_google_credentials(
                _SCOPES,
                credentials_file=credentials_file,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
            )
            self._service = _build(
                "searchconsole", "v1", credentials=credentials, cache_discovery=False
            )
        except HttpError as e:
            raise IntegrationAuthError(
                f"GSC credential authentication failed (HTTP {e.resp.status}): {e.reason}"
            ) from e
        except IntegrationConfigError:
            raise
        except Exception as e:
            raise IntegrationError(f"Failed to initialise GSC client: {e}") from e

    def _handle_http_error(self, e: Exception) -> None:
        if not isinstance(e, self._HttpError):
            raise IntegrationConnectionError(
                f"Cannot reach Google Search Console: {e}"
            ) from e
        code = e.resp.status
        if code in (401, 403):
            raise IntegrationAuthError(
                f"GSC authentication failed (HTTP {code}). "
                "Ensure the service account has access to the GSC property."
            ) from e
        if code == 429:
            raise IntegrationRateLimitError("GSC rate limit reached. Retry later.") from e
        raise IntegrationError(f"GSC API error {code}: {e.reason}") from e

    def _fetch_rows(self, dimension: str, days: int, row_limit: int) -> list[dict]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        request_body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": [dimension],
            "rowLimit": row_limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        }
        try:
            response = (
                self._service.searchanalytics()
                .query(siteUrl=self._site_url, body=request_body)
                .execute()
            )
        except Exception as e:
            self._handle_http_error(e)
        return response.get("rows", [])

    def test_connection(self) -> bool:
        try:
            self._service.sites().get(siteUrl=self._site_url).execute()
            return True
        except Exception as e:
            self._handle_http_error(e)

    def get_top_queries(self, days: int = 28, row_limit: int = 100) -> list[SearchQuery]:
        return [
            SearchQuery(
                query=row["keys"][0],
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=round(float(row.get("ctr", 0.0)), 4),
                position=round(float(row.get("position", 0.0)), 1),
            )
            for row in self._fetch_rows("query", days, row_limit)
        ]

    def get_keyword_pages(self, days: int = 90, row_limit: int = 500) -> list[dict]:
        """Return rows with {query, page, clicks, impressions, ctr, position}."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        request_body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["query", "page"],
            "rowLimit": row_limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        }
        try:
            response = (
                self._service.searchanalytics()
                .query(siteUrl=self._site_url, body=request_body)
                .execute()
            )
        except Exception as e:
            self._handle_http_error(e)
        return [
            {
                "query": row["keys"][0],
                "page": row["keys"][1],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(float(row.get("ctr", 0.0)), 4),
                "position": round(float(row.get("position", 0.0)), 1),
            }
            for row in response.get("rows", [])
        ]

    def get_page_performance(self, days: int = 28, row_limit: int = 100) -> list[PagePerformance]:
        return [
            PagePerformance(
                url=row["keys"][0],
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=round(float(row.get("ctr", 0.0)), 4),
                position=round(float(row.get("position", 0.0)), 1),
            )
            for row in self._fetch_rows("page", days, row_limit)
        ]
