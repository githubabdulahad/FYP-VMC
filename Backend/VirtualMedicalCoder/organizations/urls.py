from django.urls import path
from .views import (
    OrganizationListView,
    OrganizationDetailView,
    OrganizationReactivateView,
    OrganizationAPIKeyListCreateView,
    OrganizationAPIKeyRevokeView,
)

urlpatterns = [
    path("", OrganizationListView.as_view(), name="organization-list"),
    path("<int:org_id>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("<int:org_id>/reactivate/", OrganizationReactivateView.as_view(), name="organization-reactivate"),
    path("api-keys/", OrganizationAPIKeyListCreateView.as_view(), name="org-api-key-list-create"),
    path("api-keys/<int:key_id>/revoke/", OrganizationAPIKeyRevokeView.as_view(), name="org-api-key-revoke"),
]