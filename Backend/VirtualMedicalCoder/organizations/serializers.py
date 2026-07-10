from rest_framework import serializers

from .models import APIKeyScope, Organization, OrganizationAPIKey


class OrganizationAPIKeySerializer(serializers.ModelSerializer):
    """Read-only representation -- never exposes key_hash or the raw key."""

    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = OrganizationAPIKey
        fields = [
            "id",
            "organization",
            "organization_name",
            "label",
            "key_prefix",
            "scopes",
            "is_active",
            "created_at",
            "last_used_at",
        ]
        read_only_fields = fields


class OrganizationAPIKeyCreateSerializer(serializers.Serializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(is_active=True)
    )
    label = serializers.CharField(max_length=255, allow_blank=False)
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=APIKeyScope.choices),
        allow_empty=False,
    )

    def validate_scopes(self, value):
        seen = set()
        deduped = []
        for scope in value:
            if scope not in seen:
                seen.add(scope)
                deduped.append(scope)
        return deduped