"""
ingestion/models.py

Replaces / extends your existing raw clinical text model.
Now supports cloud-first file uploads (PDF, image, audio).
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UploadRecord(models.Model):
    """
    Represents one file that a user uploaded to cloud storage.
    The backend receives the file_url after the frontend uploads directly to cloud.
    """

    class FileType(models.TextChoices):
        PDF   = "pdf",   "PDF Document"
        IMAGE = "image", "Image"
        AUDIO = "audio", "Audio",
        RAW_TEXT = "raw_text", "Raw Text"

    class Status(models.TextChoices):
        PENDING    = "pending",    "Pending"         # Just received the URL
        PROCESSING = "processing", "Processing"      # OCR / STT / PDF parse running
        COMPLETED  = "completed",  "Completed"       # Text extracted, codes generated
        FAILED     = "failed",     "Failed"           # Something went wrong

    user       = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="uploads",
        null=True, blank=True,
        help_text="Null when submitted purely via an organization API key with no individual user account.",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="uploads",
        help_text="Which organization this document belongs to. Set from user.organization for browser "
                   "uploads, or from the API key's organization for machine submissions.",
    )
    submitted_by_employee = models.CharField(
        max_length=255, blank=True,
        help_text="Free-text identifier for the person who submitted this document when no full user "
                   "account exists for them (typical for API-key submissions from a partner's staff).",
    )
    review_mode_override = models.CharField(
        max_length=10, blank=True,
        help_text="Optional per-upload override of the organization's default review_mode "
                   "(values match organizations.models.ReviewMode). Empty means 'use the org default'.",
    )
    file_url   = models.URLField(max_length=1000, blank=True, default="")         # Cloud storage URL (S3, Cloudinary, etc.)         # Cloud storage URL (S3, Cloudinary, etc.)
    file_type  = models.CharField(max_length=10, choices=FileType.choices)
    raw_text = models.TextField(blank=True)
    file_name  = models.CharField(max_length=255, blank=True)  # Original filename, for display
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Extracted text from whichever extractor handled this file
    extracted_text = models.TextField(blank=True)

    # Error message if something went wrong during processing
    error_message  = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} | {self.file_type} | {self.status} | {self.created_at:%Y-%m-%d}"
    
    def resolved_review_mode(self):
        """
        Effective review mode for this specific upload: a per-upload override
        if one was set, otherwise the owning organization's default, otherwise
        ASSISTED (the safer default when there's no organization at all).
        """
        from organizations.models import ReviewMode

        if self.review_mode_override:
            return self.review_mode_override
        if self.organization_id:
            return self.organization.review_mode
        return ReviewMode.ASSISTED