# Login fails after token expires

Users are logged out when a refresh token expires unexpectedly. The client expected a token
refresh but received an error from the auth flow.

Expected: the session should either refresh the access token or return a clear sign-in action.
Actual: users report a login failure after a long idle session.

