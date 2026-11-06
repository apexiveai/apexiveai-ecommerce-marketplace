from django.contrib import admin

from .models import (
    ChatMessage,
    CommissionRecord,
    Conversation,
    CustomerLead,
    DealerSubscription,
    SalesTransaction,
    Showroom,
    ShowroomMember,
    TestDriveBooking,
    Vehicle,
    VehicleDocument,
    VehicleFavorite,
    VehicleImage,
    VehicleReservation,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "seller", "vehicle", "updated_at")
    search_fields = ("buyer__username", "buyer__email", "seller__store_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "created_at", "read_at")
    search_fields = ("sender__username", "sender__email", "body")
    readonly_fields = ("created_at",)


@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "city", "is_primary", "created_at")
    list_filter = ("city", "is_primary")
    search_fields = ("name", "seller__store_name", "address")


@admin.register(ShowroomMember)
class ShowroomMemberAdmin(admin.ModelAdmin):
    list_display = ("showroom", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("showroom__name", "user__username", "user__email")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "year", "seller", "price", "status")
    list_filter = ("status", "condition", "make", "year")
    search_fields = ("make", "model", "trim", "seller__store_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "position", "is_primary")
    list_filter = ("is_primary",)


@admin.register(VehicleFavorite)
class VehicleFavoriteAdmin(admin.ModelAdmin):
    list_display = ("buyer", "vehicle", "created_at")
    search_fields = ("buyer__username", "buyer__email", "vehicle__make", "vehicle__model")


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "document_type", "uploaded_at")
    list_filter = ("document_type",)


@admin.register(CustomerLead)
class CustomerLeadAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "buyer", "seller", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("vehicle__make", "vehicle__model", "buyer__email")


@admin.register(TestDriveBooking)
class TestDriveBookingAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "buyer", "seller", "scheduled_at", "status")
    list_filter = ("status",)
    search_fields = ("vehicle__make", "vehicle__model", "buyer__email")


@admin.register(VehicleReservation)
class VehicleReservationAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "buyer", "seller", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("vehicle__make", "vehicle__model", "buyer__email")


@admin.register(SalesTransaction)
class SalesTransactionAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "buyer", "seller", "sale_price", "status")
    list_filter = ("status", "currency")
    search_fields = ("vehicle__make", "vehicle__model", "buyer__email")


@admin.register(CommissionRecord)
class CommissionRecordAdmin(admin.ModelAdmin):
    list_display = ("transaction", "seller", "rate_percent", "amount", "status")
    list_filter = ("status", "currency")
    search_fields = ("seller__store_name",)


@admin.register(DealerSubscription)
class DealerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("seller", "plan_name", "status", "price", "starts_at")
    list_filter = ("status", "plan_name")
    search_fields = ("seller__store_name", "plan_name")
