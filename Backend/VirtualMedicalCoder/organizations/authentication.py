"""
API key authentication for machine clients (partner EHR / insurer systems).

This is deliberately separate from accounts.authentication.JWTCookieAuthentication,
which assumes a browser session. A partner's backend server has no cookie jar,
so it authenticates with:

    Authorization: Bearer vmc_live_<random>

Both authentication classes are registered in REST_FRAMEWORK settings; DRF
tries each in order and uses whichever one recognizes the request's
credentials. A request never needs both -- a browser session uses the
cookie, a partner integration uses the API key.
"""
from rest_framework import authentication, exceptions

from .models import OrganizationAPIKey

    
class OrganizationAPIKeyAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None  # let other authentication classes have a turn

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        raw_key = parts[1]
        if not raw_key.startswith("vmc_live_"):
            # Not one of our keys -- likely a JWT bearer token instead.
            # Let JWTCookieAuthentication / SimpleJWT handle it.
            return None

        api_key = OrganizationAPIKey.get_from_raw_key(raw_key)
        if api_key is None:
            raise exceptions.AuthenticationFailed("Invalid or inactive API key.")

        if not api_key.organization.is_active:
            raise exceptions.AuthenticationFailed("Organization is inactive.")

        api_key.mark_used()

        # request.user stays None (no Django User is involved in a pure
        # API-key call); request.auth carries the key so views/permissions
        # can look up the organization and its scopes.
        return (None, api_key)

    def authenticate_header(self, request):
        return self.keyword