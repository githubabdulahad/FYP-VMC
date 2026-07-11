from django.utils.text import slugify
from rest_framework import serializers

from .models import APIKeyScope, Organization, OrganizationAPIKey


class OrganizationSerializer(serializers.ModelSerializer):
    """Full read representation -- used by the admin org-management screen."""

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "review_mode", "is_active", "created_at"]
        read_only_fields = fields


class OrganizationCreateSerializer(serializers.Serializer):
    """
    Only `name` is required. The slug is derived from it automatically so
    an admin can't accidentally create a malformed or colliding slug by
    hand -- if the derived slug is taken, we suffix it (acme, acme-2, ...).
    """

    name = serializers.CharField(max_length=255, allow_blank=False)
    review_mode = serializers.ChoiceField(
        choices=["assisted", "direct"], required=False, default="assisted"
    )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def create(self, validated_data):
        base_slug = slugify(validated_data["name"])
        if not base_slug:
            raise serializers.ValidationError({"name": "Name must contain at least one letter or number."})

        slug = base_slug
        suffix = 2
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        return Organization.objects.create(
            name=validated_data["name"],
            slug=slug,
            review_mode=validated_data.get("review_mode", "assisted"),
        )


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Deliberately narrow: name and review_mode only. Slug never changes
    after creation -- it may already be embedded in partner-side config."""

    class Meta:
        model = Organization
        fields = ["name", "review_mode"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value


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