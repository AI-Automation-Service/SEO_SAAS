from dataclasses import dataclass

from integrations.base import (
    IntegrationAuthError,
    IntegrationConfigError,
    IntegrationConnectionError,
    IntegrationError,
)
from integrations.google._auth import build_google_credentials

_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


@dataclass
class PageTraffic:
    path: str
    sessions: int
    users: int
    page_views: int


class AnalyticsAdapter:
    def __init__(
        self,
        property_id: str,
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
        if not property_id:
            raise IntegrationConfigError("GA4 property ID is required.")
        if not credentials_file and not refresh_token:
            raise IntegrationConfigError(
                "Either credentials_file or refresh_token must be provided."
            )

        self._property = f"properties/{property_id}"

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
            from google.api_core.exceptions import GoogleAPIError, PermissionDenied, Unauthenticated
        except ImportError as e:
            raise ImportError(
                "Google Analytics library not installed. "
                "Run: pip install google-analytics-data google-auth"
            ) from e

        self._RunReportRequest = RunReportRequest
        self._Dimension = Dimension
        self._Metric = Metric
        self._DateRange = DateRange
        self._GoogleAPIError = GoogleAPIError
        self._PermissionDenied = PermissionDenied
        self._Unauthenticated = Unauthenticated

        try:
            credentials = build_google_credentials(
                _SCOPES,
                credentials_file=credentials_file,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
            )
            self._client = BetaAnalyticsDataClient(credentials=credentials)
        except (PermissionDenied, Unauthenticated) as e:
            raise IntegrationAuthError(
                f"GA4 credential authentication failed: {e}"
            ) from e
        except IntegrationConfigError:
            raise
        except GoogleAPIError as e:
            raise IntegrationError(f"Failed to initialise GA4 client: {e}") from e

    def _handle_error(self, e: Exception) -> None:
        if isinstance(e, (self._PermissionDenied, self._Unauthenticated)):
            raise IntegrationAuthError(
                f"GA4 authentication failed. Ensure the service account has access "
                f"to property {self._property}: {e}"
            ) from e
        if isinstance(e, self._GoogleAPIError):
            raise IntegrationError(f"GA4 API error: {e}") from e
        raise IntegrationConnectionError(f"GA4 request failed: {e}") from e

    def test_connection(self) -> bool:
        try:
            request = self._RunReportRequest(
                property=self._property,
                dimensions=[self._Dimension(name="pagePath")],
                metrics=[self._Metric(name="sessions")],
                date_ranges=[self._DateRange(start_date="7daysAgo", end_date="today")],
                limit=1,
            )
            self._client.run_report(request)
            return True
        except Exception as e:
            self._handle_error(e)

    def get_top_pages(self, days: int = 28, limit: int = 100) -> list[PageTraffic]:
        try:
            request = self._RunReportRequest(
                property=self._property,
                dimensions=[self._Dimension(name="pagePath")],
                metrics=[
                    self._Metric(name="sessions"),
                    self._Metric(name="totalUsers"),
                    self._Metric(name="screenPageViews"),
                ],
                date_ranges=[self._DateRange(start_date=f"{days}daysAgo", end_date="today")],
                limit=limit,
            )
            response = self._client.run_report(request)
        except Exception as e:
            self._handle_error(e)

        return [
            PageTraffic(
                path=row.dimension_values[0].value,
                sessions=int(row.metric_values[0].value),
                users=int(row.metric_values[1].value),
                page_views=int(row.metric_values[2].value),
            )
            for row in response.rows
        ]
