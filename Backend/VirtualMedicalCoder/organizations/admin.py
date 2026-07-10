from django.contrib import admin, messages

from .models import Organization, OrganizationAPIKey, APIKeyScope


@admin.action(description="Generate a new API key for selected organization(s)")
def generate_api_key(modeladmin, request, queryset):
    """
    Admin action (not the plain 'Add' button): the raw key can only be
    produced through OrganizationAPIKey.create_for_organization(), since it
    needs to be generated and hashed together. This runs that for every
    selected organization and shows each raw key once, in a flash message --
    exactly like it would be shown to a real partner at creation time.
    """
    for org in queryset:
        existing_count = org.api_keys.count()
        key_obj, raw_key = OrganizationAPIKey.create_for_organization(
            org,
            label=f"Admin-generated key #{existing_count + 1}",
            scopes=[APIKeyScope.SUBMIT, APIKeyScope.READ, APIKeyScope.REVIEW],
        )
        messages.success(
            request,
            f"New key for '{org.name}': {raw_key}  "
            f"(copy this now -- it will never be shown again)",
        )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "review_mode", "is_active", "created_at")
    list_filter = ("review_mode", "is_active")
    search_fields = ("name", "slug")
    actions = [generate_api_key]


@admin.register(OrganizationAPIKey)
class OrganizationAPIKeyAdmin(admin.ModelAdmin):
    # key_hash is intentionally never shown -- only the prefix, enough to
    # identify a key without exposing anything usable. Raw keys are only
    # ever shown once, via the "Generate a new API key" action on the
    # Organization admin page above -- not here, and not through the plain
    # "Add" button, which cannot produce a valid key on its own.
    list_display = ("label", "organization", "key_prefix", "scopes", "is_active", "last_used_at", "created_at")
    list_filter = ("is_active", "organization")
    readonly_fields = ("key_hash", "key_prefix", "created_at", "last_used_at")