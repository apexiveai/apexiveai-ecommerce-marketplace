from django.contrib import admin

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    OrderNotification,
)


class OrderItemInline(admin.TabularInline):

    model = OrderItem
    extra = 0
    can_delete = False

    readonly_fields = [
        field.name
        for field in OrderItem._meta.fields
    ]

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):

    model = OrderStatusHistory
    extra = 0
    can_delete = False

    readonly_fields = [
        field.name
        for field in OrderStatusHistory._meta.fields
    ]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_number",
        "buyer",
        "seller",
        "status",
        "payment_status",
        "currency",
        "total_amount",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "currency",
        "created_at",
    )

    search_fields = (
        "order_number",
        "buyer__username",
        "buyer__email",
        "seller__store_name",
        "shipping_full_name",
        "shipping_phone",
        "tracking_number",
    )

    readonly_fields = [
        field.name
        for field in Order._meta.fields
    ]

    inlines = [
        OrderItemInline,
        OrderStatusHistoryInline,
    ]

    date_hierarchy = "created_at"
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "product_name",
        "product_sku",
        "quantity",
        "unit_price",
        "line_total",
    )

    search_fields = (
        "order__order_number",
        "product_name",
        "product_sku",
    )

    readonly_fields = [
        field.name
        for field in OrderItem._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "previous_status",
        "new_status",
        "changed_by",
        "created_at",
    )

    list_filter = (
        "new_status",
        "created_at",
    )

    search_fields = (
        "order__order_number",
        "changed_by__username",
    )

    readonly_fields = [
        field.name
        for field in OrderStatusHistory._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderNotification)
class OrderNotificationAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "order",
        "title",
        "is_read",
        "created_at",
    )

    list_filter = (
        "is_read",
        "created_at",
    )

    search_fields = (
        "user__username",
        "order__order_number",
        "title",
    )

    readonly_fields = (
        "user",
        "order",
        "title",
        "message",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False