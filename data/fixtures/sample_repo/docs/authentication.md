# Authentication Design

## Token lifecycle

Access tokens expire quickly. Refresh tokens last longer, but they are still validated on
every refresh request. The session module stores a token family id so revocation can disable
all descendant tokens.

## Refresh flow

1. Decode the refresh token.
2. Check expiration and revocation.
3. Issue a new access token.
4. Return a support-safe error when the token cannot be refreshed.

## Known edge cases

Older clients may send refresh requests after the refresh token has already expired. The
expected result is `TokenRefreshError` and a forced sign-in, not a server crash.

