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

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploads")
    file_url   = models.URLField(max_length=1000, blank=True, default="")         # Cloud storage URL (S3, Cloudinary, etc.)
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