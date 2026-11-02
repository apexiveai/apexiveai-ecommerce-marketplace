from rest_framework import serializers

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    OrderNotification,
)


class CheckoutItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class CheckoutSerializer(serializers.Serializer):

    items = CheckoutItemSerializer(many=True)

    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices,
        default=Order.PaymentMethod.CASH_ON_DELIVERY,
    )

    shipping_full_name = serializers.CharField(max_length=150)
    shipping_phone = serializers.CharField(max_length=30)
    shipping_address_line1 = serializers.CharField()
    shipping_address_line2 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    shipping_city = serializers.CharField(max_length=120)
    shipping_region = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    shipping_postal_code = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )
    shipping_country_code = serializers.CharField(
        max_length=2,
        default="MM",
    )
    buyer_note = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError(
                "At least one product is required."
            )

        product_ids = [item["product_id"] for item in items]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Duplicate products are not allowed. Combine quantities."
            )

        return items

    def validate_shipping_country_code(self, value):
        return value.strip().upper()


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "original_unit_price",
            "discount_percent",
            "unit_price",
            "line_total",
            "created_at",
        ]
        read_only_fields = fields


class OrderStatusHistorySerializer(serializers.ModelSerializer):

    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
        default=None,
    )

    class Meta:
        model = OrderStatusHistory
        fields = [
            "id",
            "previous_status",
            "new_status",
            "note",
            "changed_by_username",
            "created_at",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)

    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True,
    )

    buyer_username = serializers.CharField(
        source="buyer.username",
        read_only=True,
    )

    status_history = OrderStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "buyer",
            "buyer_username",
            "seller",
            "seller_name",
            "status",
            "payment_status",
            "payment_method",
            "currency",
            "subtotal",
            "shipping_fee",
            "discount_total",
            "total_amount",
            "shipping_full_name",
            "shipping_phone",
            "shipping_address_line1",
            "shipping_address_line2",
            "shipping_city",
            "shipping_region",
            "shipping_postal_code",
            "shipping_country_code",
            "shipping_carrier",
            "tracking_number",
            "shipped_at",
            "completed_at",
            "buyer_note",
            "seller_note",
            "items",
            "status_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderNotificationSerializer(serializers.ModelSerializer):

    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )

    class Meta:
        model = OrderNotification
        fields = [
            "id",
            "order",
            "order_number",
            "title",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields