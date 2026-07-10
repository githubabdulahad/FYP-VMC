import hashlib
import secrets

from django.db import models
from django.utils import timezone


class ReviewMode(models.TextChoices):
    """
    Controls who is allowed to approve/reject CodingResult rows submitted
    by this organization.

    ASSISTED: only internal coders/admins may review (default -- this is
              the safer starting point for every new partner).
    DIRECT:   the submitting organization's own key/user may review its
              own results directly, without an internal coder in the loop.
    """
    ASSISTED = "assisted", "Assisted (internal coder reviews)"
    DIRECT = "direct", "Direct (partner reviews their own results)"


class Organization(models.Model):
    """
    A tenant. This covers both our own internal team (one row, e.g. "Internal")
    and every partner (hospital, EHR vendor, insurer) that integrates with the
    API. Every User, UploadRecord, and CodingResult is scoped to one of these.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    review_mode = models.CharField(
        max_length=10,
        choices=ReviewMode.choices,
        default=ReviewMode.ASSISTED,
        help_text="Default review mode for uploads submitted by this organization.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class APIKeyScope(models.TextChoices):
    """
    Deliberately coarse-grained to start. Split further only once a real
    partner integration needs the distinction.
    """
    SUBMIT = "submit", "Submit documents"
    READ = "read", "Read results"
    REVIEW = "review", "Review / approve / reject results"


def _generate_raw_key() -> str:
    # vmc_live_<43 url-safe chars> -- long enough to be unguessable,
    # prefixed so a leaked key is recognizable at a glance in logs.
    return f"vmc_live_{secrets.token_urlsafe(32)}"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class OrganizationAPIKey(models.Model):
    """
    Machine-client credential for an Organization. The raw key is shown to
    the user exactly once, at creation time, and is never stored -- only
    its SHA-256 hash is persisted, the same principle as password storage.
    """
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="api_keys"
    )
    label = models.CharField(
        max_length=255,
        help_text="Human-readable label, e.g. 'Acme Claims System - prod'.",
    )
    key_hash = models.CharField(max_length=64, unique=True, editable=False)
    key_prefix = models.CharField(
        max_length=16,
        editable=False,
        help_text="First few characters of the raw key, safe to display for identification.",
    )
    scopes = models.JSONField(
        default=list,
        help_text="List of APIKeyScope values this key is allowed to use.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.organization.name})"

    def has_scope(self, scope: str) -> bool:
        return scope in (self.scopes or [])

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    @classmethod
    def create_for_organization(cls, organization, label, scopes=None):
        """
        Returns (instance, raw_key). raw_key is only available here, at
        creation time -- the caller must show it to the user immediately
        and cannot retrieve it again afterwards.
        """
        raw_key = _generate_raw_key()
        instance = cls.objects.create(
            organization=organization,
            label=label,
            key_hash=_hash_key(raw_key),
            key_prefix=raw_key[:16],
            scopes=scopes or [],
        )
        return instance, raw_key

    @classmethod
    def get_from_raw_key(cls, raw_key: str):
        try:
            return cls.objects.select_related("organization").get(
                key_hash=_hash_key(raw_key), is_active=True
            )
        except cls.DoesNotExist:
            return None