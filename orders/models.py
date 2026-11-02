import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_order_number():
    return f"APX-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


class Order(models.Model):

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        PROCESSING = "PROCESSING", "Processing"
        READY_TO_SHIP = "READY_TO_SHIP", "Ready to ship"
        SHIPPED = "SHIPPED", "Shipped"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        RETURN_REQUESTED = "RETURN_REQUESTED", "Return requested"
        RETURNED = "RETURNED", "Returned"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"
        REFUNDED = "REFUNDED", "Refunded"

    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = "COD", "Cash on delivery"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
        ONLINE = "ONLINE", "Online payment"

    order_number = models.CharField(
        max_length=40,
        unique=True,
        default=generate_order_number,
        editable=False,
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="marketplace_orders",
    )

    seller = models.ForeignKey(
        "accounts.SellerProfile",
        on_delete=models.PROTECT,
        related_name="marketplace_orders",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )

    payment_status = models.CharField(
        max_length=25,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH_ON_DELIVERY,
    )

    currency = models.CharField(max_length=3, default="MMK")

    subtotal = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    shipping_fee = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    discount_total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    # Shipping address snapshot
    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=30)
    shipping_address_line1 = models.TextField()
    shipping_address_line2 = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=120)
    shipping_region = models.CharField(max_length=120, blank=True)
    shipping_postal_code = models.CharField(max_length=30, blank=True)
    shipping_country_code = models.CharField(max_length=2, default="MM")

    # Shipping information
    shipping_carrier = models.CharField(max_length=120, blank=True)
    tracking_number = models.CharField(max_length=150, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    buyer_note = models.TextField(blank=True)
    seller_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["seller", "status", "created_at"]),
            models.Index(fields=["buyer", "created_at"]),
            models.Index(fields=["payment_status", "created_at"]),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )

    # Product information snapshot
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField()

    original_unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    line_total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusHistory(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    previous_status = models.CharField(
        max_length=20,
        choices=Order.Status.choices,
        blank=True,
    )

    new_status = models.CharField(
        max_length=20,
        choices=Order.Status.choices,
    )

    note = models.TextField(blank=True)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketplace_order_changes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.new_status}"


class OrderNotification(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_notifications",
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    is_read = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title