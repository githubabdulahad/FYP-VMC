from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import JWTCookieAuthentication
from .models import Organization, OrganizationAPIKey
from .permissions import IsInternalAdmin
from .serializers import (
    OrganizationAPIKeyCreateSerializer,
    OrganizationAPIKeySerializer,
)


class OrganizationListView(APIView):
    """
    GET /api/v1/organizations/
    Lightweight list for populating the "target organization" dropdown
    when provisioning a key. Internal admins only.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get(self, request):
        orgs = Organization.objects.filter(is_active=True).order_by("name")
        return Response(
            [{"id": o.id, "name": o.name, "slug": o.slug, "review_mode": o.review_mode} for o in orgs]
        )


class OrganizationAPIKeyListCreateView(APIView):
    """
    GET  /api/v1/organizations/api-keys/                 -- list ALL orgs' keys
    GET  /api/v1/organizations/api-keys/?organization=<id> -- filter to one org
    POST /api/v1/organizations/api-keys/                 -- create a key for
         whichever organization is passed in the request body
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get(self, request):
        keys = OrganizationAPIKey.objects.select_related("organization").order_by("-created_at")
        org_id = request.query_params.get("organization")
        if org_id:
            keys = keys.filter(organization_id=org_id)
        return Response(OrganizationAPIKeySerializer(keys, many=True).data)

    def post(self, request):
        serializer = OrganizationAPIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        instance, raw_key = OrganizationAPIKey.create_for_organization(
            organization=serializer.validated_data["organization"],
            label=serializer.validated_data["label"],
            scopes=serializer.validated_data["scopes"],
        )

        data = OrganizationAPIKeySerializer(instance).data
        data["raw_key"] = raw_key  # only ever present in this one response
        return Response(data, status=status.HTTP_201_CREATED)


class OrganizationAPIKeyRevokeView(APIView):
    """
    POST /api/v1/organizations/api-keys/<id>/revoke/
    Soft-revoke only -- sets is_active=False, never deletes the row.
    No organization filter needed here: an internal admin is trusted to
    revoke any org's key, that's the entire point of this being
    internal-only provisioning.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def post(self, request, key_id):
        try:
            key = OrganizationAPIKey.objects.select_related("organization").get(id=key_id)
        except OrganizationAPIKey.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        key.is_active = False
        key.save(update_fields=["is_active"])
        return Response(OrganizationAPIKeySerializer(key).data)