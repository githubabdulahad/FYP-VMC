"""
Permission checks for API-key-authenticated requests.

request.auth is an OrganizationAPIKey when OrganizationAPIKeyAuthentication
handled the request, and None otherwise.
"""
from rest_framework.permissions import BasePermission

from .models import OrganizationAPIKey
from rest_framework import permissions


class HasAPIKeyScope(BasePermission):
    """
    For views that are ONLY reachable via an organization API key (no JWT
    fallback), e.g. the Partner API endpoints. Requires a valid, active API
    key with the view's `required_scope`; denies everything else, including
    an unauthenticated request -- there is no other authentication method
    for these views to fall back to.
    """

    def has_permission(self, request, view):
        api_key = request.auth
        if not isinstance(api_key, OrganizationAPIKey):
            return False

        required_scope = getattr(view, "required_scope", None)
        if required_scope is None:
            return True

        return api_key.has_scope(required_scope)


class IsAuthenticatedOrHasAPIKeyScope(BasePermission):
    """
    For views that must accept EITHER a logged-in browser/JWT user OR a
    valid organization API key with the view's required_scope -- e.g. the
    coding review endpoint, which internal coders use via the web app and
    partners (in direct review mode) can use via their API key.
    """

    def has_permission(self, request, view):
        api_key = request.auth
        if isinstance(api_key, OrganizationAPIKey):
            required_scope = getattr(view, "required_scope", None)
            return required_scope is None or api_key.has_scope(required_scope)
        return bool(request.user and request.user.is_authenticated)

class IsInternalAdmin(permissions.BasePermission):
    """
    Allows access only to JWT-authenticated users with role="admin" who
    belong to the "Internal" organization. Used exclusively for the API
    key provisioning endpoints -- partners never log in to the frontend
    at all, so this is deliberately internal-staff-only, JWT-only (not
    reachable via an OrganizationAPIKey).
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "admin"
            and getattr(user, "organization", None) is not None
            and user.organization.slug == "internal"
        )