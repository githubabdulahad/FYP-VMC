from django.db import models
from django.contrib.auth.models import AbstractUser
class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("coder", "Coder"),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="coder")
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    can_review_partner_submissions = models.BooleanField(
        default=False,
        help_text="If true, this user can see and review ASSISTED-mode results submitted by partner organizations, not just their own uploads.",
    )

    REQUIRED_FIELDS = ["email"]