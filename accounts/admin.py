from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    BuyerProfile,
    SellerBusiness,
    SellerProfile,
    User,
    UserRole,
)

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


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at",)


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "buyer_type", "company_name", "created_at")
    list_filter = ("buyer_type",)
    search_fields = ("user__username", "user__email", "company_name")
    readonly_fields = ("created_at",)


@admin.register(SellerBusiness)
class SellerBusinessAdmin(admin.ModelAdmin):
    list_display = ("seller", "business_type", "legal_name", "created_at")
    list_filter = ("business_type",)
    search_fields = ("seller__store_name", "legal_name", "registration_number")
    readonly_fields = ("created_at",)
