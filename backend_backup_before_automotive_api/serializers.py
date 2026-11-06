
from rest_framework import serializers

from accounts.models import SellerProfile


class SellerApplicationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SellerProfile
        fields = [
            "id",
            "username",
            "email",
            "store_name",
            "store_slug",
            "description",
            "country_code",
            "business_address",
            "status",
            "created_at",
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
