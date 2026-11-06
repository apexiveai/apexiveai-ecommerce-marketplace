
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    BuyerProfile,
    SellerBusiness,
    SellerProfile,
    User,
)


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
    buyer_type = serializers.ChoiceField(
        choices=BuyerProfile.BuyerType.choices,
        required=False,
        default=BuyerProfile.BuyerType.INDIVIDUAL,
        write_only=True,
    )
    company_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=180,
        write_only=True,
    )
    seller_type = serializers.ChoiceField(
        choices=SellerProfile.SellerType.choices,
        required=False,
        default=SellerProfile.SellerType.DEALER,
        write_only=True,
    )
    business_type = serializers.ChoiceField(
        choices=SellerBusiness.BusinessType.choices,
        required=False,
        default=SellerBusiness.BusinessType.CAR_SHOWROOM,
        write_only=True,
    )
    legal_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=180,
        write_only=True,
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
            "buyer_type",
            "company_name",
            "seller_type",
            "business_type",
            "legal_name",
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
        if attrs.get("role") == User.Role.BUYER:
            if (
                attrs.get("buyer_type") == BuyerProfile.BuyerType.CORPORATE
                and not attrs.get("company_name", "").strip()
            ):
                raise serializers.ValidationError({
                    "company_name": "Company name is required for corporate buyers."
                })
        elif attrs.get("role") == User.Role.SELLER:
            seller_type = attrs.get(
                "seller_type",
                SellerProfile.SellerType.DEALER,
            )
            store_name = attrs.get("store_name", "").strip()
            if (
                seller_type == SellerProfile.SellerType.DEALER
                and not store_name
            ):
                raise serializers.ValidationError({
                    "store_name": "Store name is required for dealers."
                })
            attrs["store_name"] = store_name or attrs.get("username", "")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        store_name = validated_data.pop("store_name", "")
        buyer_type = validated_data.pop(
            "buyer_type",
            BuyerProfile.BuyerType.INDIVIDUAL,
        )
        company_name = validated_data.pop("company_name", "")
        seller_type = validated_data.pop(
            "seller_type",
            SellerProfile.SellerType.DEALER,
        )
        business_type = validated_data.pop(
            "business_type",
            SellerBusiness.BusinessType.CAR_SHOWROOM,
        )
        legal_name = validated_data.pop("legal_name", "")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if user.role == User.Role.BUYER:
            BuyerProfile.objects.create(
                user=user,
                buyer_type=buyer_type,
                company_name=company_name.strip(),
            )
        elif user.role == User.Role.SELLER:
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
                seller_type=seller_type,
            )
            if seller_type == SellerProfile.SellerType.DEALER:
                SellerBusiness.objects.create(
                    seller=user.seller_profile,
                    business_type=business_type,
                    legal_name=legal_name.strip(),
                )

        return user


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "phone_number",
            "email_verified",
            "buyer_profile",
            "seller_profile",
        ]
        read_only_fields = fields

    def get_role(self, obj):
        if obj.is_superuser:
            return User.Role.ADMIN
        return obj.role

    buyer_profile = serializers.SerializerMethodField()
    seller_profile = serializers.SerializerMethodField()

    def get_buyer_profile(self, obj):
        try:
            profile = obj.buyer_profile
        except BuyerProfile.DoesNotExist:
            return None
        return {
            "type": profile.buyer_type,
            "company_name": profile.company_name,
        }

    def get_seller_profile(self, obj):
        try:
            profile = obj.seller_profile
        except SellerProfile.DoesNotExist:
            return None
        try:
            business_type = profile.business.business_type
        except SellerBusiness.DoesNotExist:
            business_type = None
        return {
            "type": profile.seller_type,
            "business_type": business_type,
            "store_name": profile.store_name,
            "status": profile.status,
        }


class MarketplaceTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get(User.USERNAME_FIELD, "")
        if "@" in username:
            user = User.objects.filter(email__iexact=username).first()
            if user:
                attrs[User.USERNAME_FIELD] = user.get_username()

        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
