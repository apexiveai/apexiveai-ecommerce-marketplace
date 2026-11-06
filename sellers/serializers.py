from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from accounts.models import SellerProfile
from .models import Showroom, Vehicle, VehicleImage


class SellerApplicationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SellerProfile
        fields = [
            "id", "username", "email", "store_name", "store_slug",
            "description", "country_code", "business_address",
            "status", "created_at",
        ]
        read_only_fields = fields


class SellerStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            SellerProfile.Status.APPROVED,
            SellerProfile.Status.REJECTED,
            SellerProfile.Status.SUSPENDED,
        ]
    )


class ShowroomSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True,
    )

    class Meta:
        model = Showroom
        fields = [
            "id", "seller_name", "name", "address", "city",
            "phone_number", "is_primary", "created_at",
        ]
        read_only_fields = ["id", "seller_name", "created_at"]

    def validate(self, attrs):
        request = self.context["request"]
        seller = request.user.seller_profile

        if self.instance and self.instance.seller_id != seller.id:
            raise serializers.ValidationError(
                "You cannot modify another seller's showroom."
            )

        return attrs


class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = [
            "id", "image", "alt_text", "position", "is_primary",
        ]
        read_only_fields = ["id"]


class VehicleListSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True,
    )
    showroom_name = serializers.CharField(
        source="showroom.name",
        read_only=True,
        allow_null=True,
    )
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id", "seller_name", "showroom_name", "make", "model",
            "trim", "year", "price", "currency", "mileage_km",
            "condition", "transmission", "fuel_type", "status",
            "primary_image", "created_at",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first()
        if not image:
            image = obj.images.first()

        if not image or not image.image:
            return None

        request = self.context.get("request")
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class VehicleDetailSerializer(VehicleListSerializer):
    images = VehicleImageSerializer(many=True, read_only=True)

    class Meta(VehicleListSerializer.Meta):
        fields = VehicleListSerializer.Meta.fields + [
            "description", "updated_at", "images",
        ]


class VehicleWriteSerializer(serializers.ModelSerializer):
    showroom = serializers.PrimaryKeyRelatedField(
        queryset=Showroom.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Vehicle
        fields = [
            "showroom", "make", "model", "trim", "year", "price",
            "currency", "mileage_km", "condition", "transmission",
            "fuel_type", "description",
        ]

    def validate_showroom(self, showroom):
        if showroom is None:
            return showroom

        seller = self.context["request"].user.seller_profile

        if showroom.seller_id != seller.id:
            raise serializers.ValidationError(
                "You can only select your own showroom."
            )

        return showroom


class VehicleModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Vehicle.Status.ACTIVE,
            Vehicle.Status.DRAFT,
            Vehicle.Status.ARCHIVED,
        ]
    )

class VehicleImageReorderSerializer(serializers.Serializer):
    image_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_image_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate image IDs are not allowed."
            )

        return value