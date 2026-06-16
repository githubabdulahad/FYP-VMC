import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
 
User = get_user_model()
 
 
class JWTCookieAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # 1. Try to get the access token from the cookie
        access_token = request.COOKIES.get(settings.JWT_AUTH["AUTH_COOKIE"])
 
        if not access_token:
            # No cookie present — let DRF fall through to the next auth class
            return None
 
        # 2. Decode and verify the token
        try:
            payload = jwt.decode(
                access_token,
                settings.JWT_AUTH["SIGNING_KEY"],
                algorithms=[settings.JWT_AUTH["ALGORITHM"]],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please refresh.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token.")
 
        # 3. Fetch the user from the DB using the user_id in the payload
        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found.")
 
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")
 
        # DRF expects a (user, token) tuple — second value is the auth token
        # which can be None if you don't need it downstream
        return (user, access_token)
 
    def authenticate_header(self, request):
        # This string is returned in the WWW-Authenticate header on 401 responses
        return "Cookie"
 