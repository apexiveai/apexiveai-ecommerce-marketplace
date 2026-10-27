from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, SellerProfile

# Register your models here.
@admin.register(User)
class MarketplaceUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "email_verified",
    )
    list_filter = ("role", "is_active", "email_verified")
    search_fields = ("username", "email", "phone_number")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Marketplace",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "email_verified",
                )
            },
        ),
    )


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "store_name",
        "user",
        "country_code",
        "status",
        "created_at",
    )
    list_filter = ("status", "country_code")
    search_fields = ("store_name", "user__username", "user__email")
    readonly_fields = ("created_at",)
