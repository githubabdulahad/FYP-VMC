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
    OrganizationCreateSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
)


class OrganizationListView(APIView):
    """
    GET  /api/v1/organizations/                        -- list active orgs
    GET  /api/v1/organizations/?include_inactive=true   -- include deactivated
         orgs too (for the admin org-management screen; the API-key
         creation dropdown wants only active ones, so this stays opt-in)
    POST /api/v1/organizations/                         -- create a new
         organization. Only `name` is required; slug is derived
         automatically. Internal admins only.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get(self, request):
        orgs = Organization.objects.all().order_by("name")
        if request.query_params.get("include_inactive") != "true":
            orgs = orgs.filter(is_active=True)
        return Response(OrganizationSerializer(orgs, many=True).data)

    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        org = serializer.save()
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(APIView):
    """
    PATCH  /api/v1/organizations/<id>/  -- update name / review_mode
    DELETE /api/v1/organizations/<id>/  -- deactivate (soft-delete)

    Never hard-deletes: UploadRecord/CodingResult history submitted by this
    organization must survive. Deactivating also blocks every one of the
    organization's API keys immediately (OrganizationAPIKeyAuthentication
    already checks organization.is_active on every request, so this is
    effective the moment it's saved -- we additionally flip is_active on
    the keys themselves so the API Key Management screen doesn't show
    live-looking keys for a deactivated organization).

    The "Internal" organization (your own staff) is protected from both
    operations -- it's not a partner and disabling it would lock out
    every internal admin/coder.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get_object(self, org_id):
        try:
            return Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return None

    def patch(self, request, org_id):
        org = self.get_object(org_id)
        if org is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if org.slug == "internal":
            return Response(
                {"error": "The Internal organization cannot be modified here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrganizationUpdateSerializer(org, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(OrganizationSerializer(org).data)

    def delete(self, request, org_id):
        org = self.get_object(org_id)
        if org is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if org.slug == "internal":
            return Response(
                {"error": "The Internal organization cannot be deactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hard = request.query_params.get("hard") == "true"
        if hard:
            has_uploads = org.uploads.exists()
            has_users = org.users.exists()
            if has_uploads or has_users:
                return Response(
                    {
                        "error": (
                            "This organization has submitted documents or has linked "
                            "user accounts, so it can't be permanently deleted -- that "
                            "would orphan real records. Deactivate it instead."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            org.delete()  # cascades to its (unused) API keys; nothing else references it
            return Response(status=status.HTTP_204_NO_CONTENT)

        org.is_active = False
        org.save(update_fields=["is_active"])
        org.api_keys.filter(is_active=True).update(is_active=False)

        return Response(OrganizationSerializer(org).data)


class OrganizationReactivateView(APIView):
    """
    POST /api/v1/organizations/<id>/reactivate/

    Reverses a deactivation. Deliberately does NOT reactivate the
    organization's API keys -- those stay revoked individually. A partner
    coming back online should get a freshly issued/reactivated key from an
    admin, not have their old one silently start working again.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def post(self, request, org_id):
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if org.is_active:
            return Response(
                {"error": "This organization is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org.is_active = True
        org.save(update_fields=["is_active"])
        return Response(OrganizationSerializer(org).data)


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