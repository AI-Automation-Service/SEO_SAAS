import os

from integrations.base import IntegrationConfigError

_TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_google_credentials(
    scopes: list[str],
    *,
    credentials_file: str | None = None,
    refresh_token: str | None = None,
    client_id: str = "",
    client_secret: str = "",
):
    """Build a google-auth Credentials object from a service-account file or OAuth refresh token."""
    if refresh_token:
        from google.oauth2.credentials import Credentials
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=_TOKEN_URI,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
    if not credentials_file or not os.path.exists(credentials_file):
        raise IntegrationConfigError(
            f"Google credentials file not found: {credentials_file}"
        )
    from google.oauth2 import service_account as _sa
    return _sa.Credentials.from_service_account_file(credentials_file, scopes=scopes)
