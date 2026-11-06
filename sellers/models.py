from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import SellerProfile


class Showroom(models.Model):
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="showrooms",
    )
    name = models.CharField(max_length=180)
    address = models.TextField()
    city = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "showrooms"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ShowroomMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"

    showroom = models.ForeignKey(
        Showroom,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="showroom_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "showroom_members"
        constraints = [
            models.UniqueConstraint(
                fields=["showroom", "user"],
                name="unique_showroom_member",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.showroom}"


class Vehicle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        RESERVED = "RESERVED", "Reserved"
        SOLD = "SOLD", "Sold"
        ARCHIVED = "ARCHIVED", "Archived"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        USED = "USED", "Used"

    class Transmission(models.TextChoices):
        AUTOMATIC = "AUTOMATIC", "Automatic"
        MANUAL = "MANUAL", "Manual"
        OTHER = "OTHER", "Other"

    class FuelType(models.TextChoices):
        PETROL = "PETROL", "Petrol"
        DIESEL = "DIESEL", "Diesel"
        HYBRID = "HYBRID", "Hybrid"
        ELECTRIC = "ELECTRIC", "Electric"
        OTHER = "OTHER", "Other"

    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    showroom = models.ForeignKey(
        Showroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicles",
    )
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=120)
    trim = models.CharField(max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1886), MaxValueValidator(2100)],
    )
    price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="MMK")
    mileage_km = models.PositiveIntegerField(default=0)
    condition = models.CharField(
        max_length=8,
        choices=Condition.choices,
        default=Condition.USED,
    )
    transmission = models.CharField(
        max_length=12,
        choices=Transmission.choices,
        default=Transmission.AUTOMATIC,
    )
    fuel_type = models.CharField(
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.PETROL,
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["make", "model", "year"]),
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="vehicles/%Y/%m/")
    alt_text = models.CharField(max_length=180, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "vehicle_images"
        ordering = ["position", "id"]

    def __str__(self):
        return f"Image for {self.vehicle}"


class VehicleFavorite(models.Model):
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_vehicles",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle_favorites"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["buyer", "vehicle"],
                name="unique_buyer_vehicle_favorite",
            ),
        ]

    def __str__(self):
        return f"{self.buyer} likes {self.vehicle}"


class VehicleDocument(models.Model):
    class DocumentType(models.TextChoices):
        REGISTRATION = "REGISTRATION", "Registration"
        OWNERSHIP = "OWNERSHIP", "Ownership"
        INSPECTION = "INSPECTION", "Inspection"
        OTHER = "OTHER", "Other"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=12,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file = models.FileField(upload_to="vehicle-documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle_documents"

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.vehicle}"


class Conversation(models.Model):
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_conversations",
    )
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="buyer_conversations",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation: {self.buyer} / {self.seller}"


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_vehicle_messages",
    )
    body = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender} in {self.conversation_id}"


class CustomerLead(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        CONVERTED = "CONVERTED", "Converted"
        CLOSED = "CLOSED", "Closed"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="customer_leads",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_leads",
    )
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="customer_leads",
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customer_leads"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Lead for {self.vehicle} from {self.buyer}"


class TestDriveBooking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="test_drive_bookings",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="test_drive_bookings",
    )
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="test_drive_bookings",
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "test_drive_bookings"
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"Test drive: {self.vehicle} at {self.scheduled_at}"


class VehicleReservation(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_reservations",
    )
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="vehicle_reservations",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    deposit_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3, default="MMK")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle_reservations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reservation for {self.vehicle} by {self.buyer}"


class SalesTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="sales_transactions",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_purchases",
    )
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="sales_transactions",
    )
    reservation = models.OneToOneField(
        VehicleReservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_transaction",
    )
    sale_price = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default="MMK")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    sold_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sale of {self.vehicle} to {self.buyer}"


class CommissionRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        WAIVED = "WAIVED", "Waived"

    transaction = models.OneToOneField(
        SalesTransaction,
        on_delete=models.PROTECT,
        related_name="commission",
    )
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="commission_records",
    )
    rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default="MMK")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "commission_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commission for {self.transaction}"


class DealerSubscription(models.Model):
    class Status(models.TextChoices):
        TRIAL = "TRIAL", "Trial"
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past due"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.TRIAL,
        db_index=True,
    )
    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3, default="MMK")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dealer_subscriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.plan_name} - {self.seller.store_name}"
