from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "role", "is_active", "date_joined"]
    list_filter = ["role", "is_active", "date_joined"]
    search_fields = ["username", "email"]
    readonly_fields = ["date_joined", "last_login"]
    fieldsets = (
        ("Credentials", {"fields": ("username", "email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name")}),
        ("Role & Permissions", {"fields": ("role", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Status", {"fields": ("is_active", "date_joined", "last_login")}),
    )
