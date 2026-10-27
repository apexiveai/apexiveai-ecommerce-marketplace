
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from .models import User, SellerProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    store_name = serializers.CharField(
        required=False,
        write_only=True,
        max_length=150,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "role",
            "phone_number",
            "store_name",
        ]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate_role(self, value):
        if value not in [User.Role.BUYER, User.Role.SELLER]:
            raise serializers.ValidationError(
                "Only Buyer or Seller registration is allowed."
            )
        return value

    def validate(self, attrs):
        if attrs.get("role") == User.Role.SELLER:
            store_name = attrs.get("store_name", "").strip()
            if not store_name:
                raise serializers.ValidationError({
                    "store_name": "Store name is required for sellers."
                })
            attrs["store_name"] = store_name
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        store_name = validated_data.pop("store_name", None)
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if user.role == User.Role.SELLER:
            base_slug = slugify(store_name)[:150] or "store"
            store_slug = base_slug
            counter = 2

            while SellerProfile.objects.filter(
                store_slug=store_slug
            ).exists():
                suffix = f"-{counter}"
                store_slug = f"{base_slug[:170-len(suffix)]}{suffix}"
                counter += 1

            SellerProfile.objects.create(
                user=user,
                store_name=store_name,
                store_slug=store_slug,
            )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "phone_number",
            "email_verified",
        ]
        read_only_fields = fields
