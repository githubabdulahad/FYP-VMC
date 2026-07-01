import jwt
from datetime import datetime, timezone
from django.conf import settings

def generate_access_token(user):
    config = settings.JWT_AUTH
    now = datetime.now(tz=timezone.utc)

    payload = {
        "user_id" : user.id,
        "exp" : now + config["ACCESS_TOKEN_LIFETIME"],
        "iat" : now , 
        "type" : "access" ,
    }

    return jwt.encode(
        payload,
        config["SIGNING_KEY"],
        algorithm=config["ALGORITHM"]
    )

def generate_refresh_token(user):
    config = settings.JWT_AUTH
    now = datetime.now(tz=timezone.utc)

    payload = {
        "user_id" : user.id,
        "exp" : now + config["REFRESH_TOKEN_LIFETIME"],
        "iat" : now , 
        "type" : "refresh" ,
    }

    return jwt.encode(
        payload,
        config["SIGNING_KEY"],
        algorithm=config["ALGORITHM"]
    )

def set_auth_cookies(response, access_token, refresh_token=None):
    config = settings.JWT_AUTH

    response.set_cookie(
        key = config["AUTH_COOKIE"],
        value = access_token,
        max_age = int(config["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly = config["AUTH_COOKIE_HTTPONLY"],
        secure=config["AUTH_COOKIE_SECURE"],
        samesite=config["AUTH_COOKIE_SAMESITE"],
        path="/",
    )

    if refresh_token:
        response.set_cookie(
            key = config["AUTH_COOKIE_REFRESH"],
            value = refresh_token,
            max_age = int(config["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            httponly = config["AUTH_COOKIE_HTTPONLY"],
            secure=config["AUTH_COOKIE_SECURE"],
            samesite=config["AUTH_COOKIE_SAMESITE"],
            path="/api/auth/refresh/",
        )

         
def delete_auth_cookies(response):
    config = settings.JWT_AUTH
    
    # must match the exact path used in set_cookie
    response.delete_cookie(
        key=config["AUTH_COOKIE"],
        path="/",
        samesite=config["AUTH_COOKIE_SAMESITE"],
    )
    
    response.delete_cookie(
        key=config["AUTH_COOKIE_REFRESH"],
        path="/api/auth/refresh/",  # must match the path it was set with
        samesite=config["AUTH_COOKIE_SAMESITE"],
    )