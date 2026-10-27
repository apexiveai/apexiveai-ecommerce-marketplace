
from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True,
    )
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    sale_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "seller",
            "seller_name",
            "category",
            "category_name",
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "discount_percent",
            "sale_price",
            "currency",
            "stock_quantity",
            "image",
            "image_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "seller",
            "slug",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

    def validate_currency(self, value):
        value = value.upper()
        if value not in {"MMK", "USD"}:
            raise serializers.ValidationError(
                "Supported currencies for launch are MMK and USD."
            )
        return value

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "This category is not available."
            )
        return value

    def validate(self, attrs):
        discount = attrs.get(
            "discount_percent",
            getattr(self.instance, "discount_percent", 0),
        )
        if discount < 0 or discount > 100:
            raise serializers.ValidationError({
                "discount_percent": "Discount must be between 0 and 100."
            })
        return attrs
