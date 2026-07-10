from rest_framework.throttling import SimpleRateThrottle


class OrgRateThrottle(SimpleRateThrottle):
    """
    Throttles requests per-organization rather than per-user or per-IP.
    Applies to both JWT-authenticated internal users (via their
    organization FK) and API-key-authenticated partners (via
    request.auth.organization), so one partner org can't starve another
    or blow through LLM cost regardless of how many keys/users they use.
    """
    scope = "org"

    def get_cache_key(self, request, view):
        from organizations.models import OrganizationAPIKey

        org = None
        if isinstance(request.auth, OrganizationAPIKey):
            org = request.auth.organization
        elif request.user and request.user.is_authenticated:
            org = getattr(request.user, "organization", None)

        if org is None:
            return None  # no org context -> not throttled by this class

        return self.cache_format % {
            "scope": self.scope,
            "ident": org.id,
        }