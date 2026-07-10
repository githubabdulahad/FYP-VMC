from django.urls import path
from .views import (
    OrganizationListView,
    OrganizationAPIKeyListCreateView,
    OrganizationAPIKeyRevokeView,
)

urlpatterns = [
    path("", OrganizationListView.as_view(), name="organization-list"),
    path("api-keys/", OrganizationAPIKeyListCreateView.as_view(), name="org-api-key-list-create"),
    path("api-keys/<int:key_id>/revoke/", OrganizationAPIKeyRevokeView.as_view(), name="org-api-key-revoke"),
]