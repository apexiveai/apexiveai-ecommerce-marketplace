from django.test import TestCase
from django.urls import reverse
from rest_framework import serializers
from rest_framework.test import APIClient

from .models import BuyerProfile, SellerBusiness, SellerProfile, User, UserRole
from .serializers import RegisterSerializer


class RegisterSerializerTests(TestCase):
    def register(self, **overrides):
        data = {
            "username": "market-user",
            "email": "market-user@example.com",
            "password": "Qw9!sX4#nT7@vL2",
            "role": User.Role.BUYER,
        }
        data.update(overrides)
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return serializer.save()

    def test_individual_buyer_gets_profile_and_role(self):
        user = self.register()

        self.assertEqual(user.buyer_profile.buyer_type, BuyerProfile.BuyerType.INDIVIDUAL)
        self.assertEqual(user.marketplace_role.role, User.Role.BUYER)

    def test_corporate_buyer_requires_company_name(self):
        serializer = RegisterSerializer(data={
            "username": "corporate-buyer",
            "email": "corporate@example.com",
            "password": "Qw9!sX4#nT7@vL2",
            "role": User.Role.BUYER,
            "buyer_type": BuyerProfile.BuyerType.CORPORATE,
        })

        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_corporate_buyer_profile_keeps_company(self):
        user = self.register(
            username="corporate-buyer",
            email="corporate@example.com",
            buyer_type=BuyerProfile.BuyerType.CORPORATE,
            company_name="Example Motors",
        )

        self.assertEqual(user.buyer_profile.company_name, "Example Motors")

    def test_private_seller_does_not_need_dealer_business(self):
        user = self.register(
            username="private-owner",
            email="owner@example.com",
            role=User.Role.SELLER,
            seller_type=SellerProfile.SellerType.PRIVATE_SELLER,
        )

        self.assertEqual(
            user.seller_profile.seller_type,
            SellerProfile.SellerType.PRIVATE_SELLER,
        )
        self.assertFalse(SellerBusiness.objects.filter(seller=user.seller_profile).exists())
        self.assertEqual(user.marketplace_role.role, User.Role.SELLER)

    def test_dealer_registration_creates_business_profile(self):
        user = self.register(
            username="showroom-owner",
            email="dealer@example.com",
            role=User.Role.SELLER,
            store_name="City Auto",
            business_type=SellerBusiness.BusinessType.AUTHORIZED_DEALER,
        )

        self.assertEqual(
            user.seller_profile.business.business_type,
            SellerBusiness.BusinessType.AUTHORIZED_DEALER,
        )


class AccountAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="buyer-login",
            email="buyer-login@example.com",
            password="Qw9!sX4#nT7@vL2",
        )

    def test_login_accepts_username_and_email(self):
        for credential in (self.user.username, self.user.email):
            response = self.client.post(
                reverse("login"),
                {"username": credential, "password": "Qw9!sX4#nT7@vL2"},
                format="json",
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["user"]["role"], User.Role.BUYER)
            self.assertIn("access", response.data)
            self.assertIn("refresh", response.data)

    def test_seller_login_returns_seller_role(self):
        seller = User.objects.create_user(
            username="seller-login",
            email="seller-login@example.com",
            password="Qw9!sX4#nT7@vL2",
            role=User.Role.SELLER,
        )
        response = self.client.post(
            reverse("login"),
            {"username": seller.username, "password": "Qw9!sX4#nT7@vL2"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], User.Role.SELLER)

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post(
            reverse("login"),
            {
                "username": self.user.username,
                "password": "Qw9!sX4#nT7@vL2",
            },
            format="json",
        )

        response = self.client.post(
            reverse("logout"),
            {"refresh": login.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        refresh_response = self.client.post(
            reverse("token-refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_superuser_is_exposed_as_admin_role(self):
        admin = User.objects.create_superuser(
            username="market-admin",
            email="admin@example.com",
            password="Qw9!sX4#nT7@vL2",
        )
        response = self.client.post(
            reverse("login"),
            {"username": admin.username, "password": "Qw9!sX4#nT7@vL2"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], User.Role.ADMIN)
        self.assertEqual(admin.marketplace_role.role, User.Role.ADMIN)
