# Sample Repo

Sample Repo is a small authentication service used by RepoOps tests.

## Authentication

The authentication module issues short-lived access tokens and long-lived refresh tokens.
When an access token expires, `src/auth/session.py` calls `refresh_access_token` to validate
the refresh token and mint a new access token. If the refresh token is expired or revoked,
the user must sign in again.

## API

The HTTP layer lives in `src/api/routes.py`. Login and token refresh responses are shaped
by the auth session module.

## Troubleshooting

Most login failures are caused by expired refresh tokens, clock skew, or missing token
metadata. Check auth logs before changing API routes.

