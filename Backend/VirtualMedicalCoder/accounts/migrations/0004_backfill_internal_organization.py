from django.db import migrations


def create_internal_org_and_backfill(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    User = apps.get_model("accounts", "User")

    internal_org, _ = Organization.objects.get_or_create(
        slug="internal",
        defaults={"name": "Internal", "review_mode": "assisted"},
    )

    # Every existing account (your own coders/admins) gets assigned to the
    # Internal org. Anyone created after this migration should be assigned
    # explicitly at signup/invite time instead of relying on this default.
    User.objects.filter(organization__isnull=True).update(organization=internal_org)


def reverse_noop(apps, schema_editor):
    # Deliberately not reversing the backfill -- unassigning users from
    # their organization on a rollback would be more destructive than
    # useful. The Internal org row itself is harmless to leave behind.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_organization"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_internal_org_and_backfill, reverse_noop),
    ]