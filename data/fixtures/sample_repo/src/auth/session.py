from dataclasses import dataclass
from datetime import UTC, datetime


class TokenRefreshError(Exception):
    """Raised when a refresh token cannot produce a new access token."""


@dataclass
class Token:
    subject: str
    expires_at: datetime
    revoked: bool = False


def is_expired(token: Token, now: datetime | None = None) -> bool:
    current_time = now or datetime.now(UTC)
    return token.expires_at <= current_time


def refresh_access_token(refresh_token: Token, now: datetime | None = None) -> str:
    if refresh_token.revoked:
        raise TokenRefreshError("refresh token has been revoked")
    if is_expired(refresh_token, now):
        raise TokenRefreshError("refresh token has expired")
    return f"access-token-for:{refresh_token.subject}"

