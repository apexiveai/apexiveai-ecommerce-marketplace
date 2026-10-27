from django.contrib import admin
from django.contrib import admin

from .models import Category, Product

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "seller",
        "category",
        "price",
        "discount_percent",
        "stock_quantity",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency", "category")
    search_fields = ("name", "sku", "seller__store_name")
    readonly_fields = ("created_at", "updated_at")
