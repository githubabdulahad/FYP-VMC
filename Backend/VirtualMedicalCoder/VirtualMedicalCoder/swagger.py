"""Shared OpenAPI helpers for drf-yasg decorators."""

from drf_yasg import openapi

AUTH_COOKIE_DESC = (
    "JWT access token is set as HttpOnly cookie `access_token` on login. "
    "Send cookies with `credentials: include` from the frontend."
)

UNAUTHORIZED = openapi.Response(
    "Authentication required or invalid token",
    examples={"application/json": {"detail": "Authentication credentials were not provided."}},
)

NOT_FOUND = openapi.Response(
    "Resource not found",
    examples={"application/json": {"error": "Not found."}},
)

BAD_REQUEST = openapi.Response(
    "Validation error",
    examples={"application/json": {"field_name": ["This field is required."]}},
)
