from app_sample.auth.session import Token, refresh_access_token


def refresh_route(refresh_token: Token) -> dict[str, str]:
    access_token = refresh_access_token(refresh_token)
    return {"access_token": access_token}

