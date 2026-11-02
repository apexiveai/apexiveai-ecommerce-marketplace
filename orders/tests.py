from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User, SellerProfile
from catalog.models import Category, Product
from orders.models import Order, OrderNotification


class MarketplaceOrderTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.buyer = User.objects.create_user(
            username="buyer_test",
            email="buyer@example.com",
            password="TestPassword123!",
            role="BUYER",
        )

        self.seller_user = User.objects.create_user(
            username="seller_test",
            email="seller@example.com",
            password="TestPassword123!",
            role="SELLER",
        )

        self.other_seller_user = User.objects.create_user(
            username="seller_other",
            email="other@example.com",
            password="TestPassword123!",
            role="SELLER",
        )

        self.admin_user = User.objects.create_user(
            username="marketplace_admin",
            email="admin@example.com",
            password="AdminPassword123!",
            role="ADMIN",
        )

        self.seller = SellerProfile.objects.create(
            user=self.seller_user,
            store_name="Test Store",
            store_slug="test-store",
            status=SellerProfile.Status.APPROVED,
        )

        self.other_seller = SellerProfile.objects.create(
            user=self.other_seller_user,
            store_name="Other Store",
            store_slug="other-store",
            status=SellerProfile.Status.APPROVED,
        )

        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics",
            is_active=True,
        )

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Test Product",
            slug="test-product",
            sku="TEST-001",
            description="Test product",
            price=Decimal("10000.00"),
            discount_percent=Decimal("10.00"),
            currency="MMK",
            stock_quantity=10,
            status=Product.Status.ACTIVE,
        )

        self.other_product = Product.objects.create(
            seller=self.other_seller,
            category=self.category,
            name="Other Product",
            slug="other-product",
            sku="TEST-002",
            description="Other product",
            price=Decimal("20000.00"),
            discount_percent=Decimal("0.00"),
            currency="MMK",
            stock_quantity=5,
            status=Product.Status.ACTIVE,
        )

        self.checkout_payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2,
                },
                {
                    "product_id": self.other_product.id,
                    "quantity": 1,
                },
            ],
            "payment_method": "COD",
            "shipping_full_name": "Test Buyer",
            "shipping_phone": "09123456789",
            "shipping_address_line1": "Test Street",
            "shipping_city": "Yangon",
            "shipping_country_code": "MM",
        }

    def create_checkout_orders(self):

        self.client.force_authenticate(
            user=self.buyer
        )

        response = self.client.post(
            "/api/v1/checkout/",
            self.checkout_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        return response

    def create_seller_order(self):

        self.create_checkout_orders()

        return Order.objects.get(
            seller=self.seller
        )

    def test_multi_seller_checkout_creates_separate_orders(self):

        response = self.create_checkout_orders()

        self.assertEqual(response.data["orders_created"], 2)
        self.assertEqual(Order.objects.count(), 2)

    def test_checkout_decreases_product_stock(self):

        self.create_checkout_orders()

        self.product.refresh_from_db()
        self.other_product.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, 8)
        self.assertEqual(self.other_product.stock_quantity, 4)

    def test_seller_cannot_view_other_sellers_orders(self):

        self.create_checkout_orders()

        self.client.force_authenticate(
            user=self.seller_user
        )

        response = self.client.get(
            "/api/v1/orders/"
        )

        self.assertEqual(response.status_code, 200)

        results = response.data.get(
            "results",
            response.data,
        )

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0]["seller"],
            self.seller.id,
        )

    def test_buyer_can_only_view_own_orders(self):

        self.create_checkout_orders()

        response = self.client.get(
            "/api/v1/orders/"
        )

        self.assertEqual(response.status_code, 200)

        results = response.data.get(
            "results",
            response.data,
        )

        self.assertEqual(len(results), 2)

    def test_checkout_rejects_insufficient_stock(self):

        self.client.force_authenticate(
            user=self.buyer
        )

        payload = {
            **self.checkout_payload,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 100,
                }
            ],
        }

        response = self.client.post(
            "/api/v1/checkout/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_rejects_unapproved_seller(self):

        self.seller.status = SellerProfile.Status.SUSPENDED
        self.seller.save(update_fields=["status"])

        self.client.force_authenticate(
            user=self.buyer
        )

        payload = {
            **self.checkout_payload,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 1,
                }
            ],
        }

        response = self.client.post(
            "/api/v1/checkout/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_seller_cannot_bypass_shipment_action(self):

        order = self.create_seller_order()

        self.client.force_authenticate(
            user=self.seller_user
        )

        accept_response = self.client.post(
            f"/api/v1/orders/{order.id}/accept/",
            {},
            format="json",
        )

        self.assertEqual(accept_response.status_code, 200)

        ready_response = self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {"status": "READY_TO_SHIP"},
            format="json",
        )

        self.assertEqual(ready_response.status_code, 200)

        bypass_response = self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {"status": "SHIPPED"},
            format="json",
        )

        self.assertEqual(bypass_response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.READY_TO_SHIP,
        )

    def test_shipment_requires_carrier_and_tracking(self):

        order = self.create_seller_order()

        self.client.force_authenticate(
            user=self.seller_user
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/accept/",
            {},
            format="json",
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {"status": "READY_TO_SHIP"},
            format="json",
        )

        response = self.client.post(
            f"/api/v1/orders/{order.id}/shipment/",
            {"shipping_carrier": "Test Carrier"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.READY_TO_SHIP,
        )

    def test_seller_cannot_mark_order_completed(self):

        order = self.create_seller_order()

        self.client.force_authenticate(
            user=self.seller_user
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/accept/",
            {},
            format="json",
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {"status": "READY_TO_SHIP"},
            format="json",
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/shipment/",
            {
                "shipping_carrier": "Test Carrier",
                "tracking_number": "TRACK-001",
            },
            format="json",
        )

        response = self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {"status": "COMPLETED"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.SHIPPED,
        )

    def test_buyer_can_confirm_delivery(self):

        order = self.create_seller_order()

        self.client.force_authenticate(
            user=self.seller_user
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/accept/",
            {},
            format="json",
        )

        self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {"status": "READY_TO_SHIP"},
            format="json",
        )

        shipment_response = self.client.post(
            f"/api/v1/orders/{order.id}/shipment/",
            {
                "shipping_carrier": "Test Carrier",
                "tracking_number": "TRACK-001",
            },
            format="json",
        )

        self.assertEqual(shipment_response.status_code, 200)

        self.client.force_authenticate(
            user=self.buyer
        )

        response = self.client.post(
            f"/api/v1/orders/{order.id}/confirm_delivery/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.COMPLETED,
        )

        self.assertIsNotNone(order.completed_at)

    def test_seller_rejection_restores_stock(self):

        order = self.create_seller_order()

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

        self.client.force_authenticate(
            user=self.seller_user
        )

        response = self.client.post(
            f"/api/v1/orders/{order.id}/reject/",
            {"note": "Unable to fulfill."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self.product.stock_quantity,
            10,
        )

    def test_admin_cancellation_restores_stock(self):

        order = self.create_seller_order()

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

        self.client.force_authenticate(
            user=self.admin_user
        )

        response = self.client.post(
            f"/api/v1/orders/{order.id}/update_status/",
            {
                "status": "CANCELLED",
                "note": "Admin cancellation.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self.product.stock_quantity,
            10,
        )

    def test_non_admin_cannot_update_payment_status(self):

        order = self.create_seller_order()

        self.client.force_authenticate(
            user=self.seller_user
        )

        response = self.client.post(
            f"/api/v1/orders/{order.id}/payment/",
            {"payment_status": "PAID"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        order.refresh_from_db()

        self.assertEqual(
            order.payment_status,
            Order.PaymentStatus.UNPAID,
        )

    def test_notifications_are_isolated_by_user(self):

        order = self.create_seller_order()

        self.client.force_authenticate(
            user=self.buyer
        )

        buyer_response = self.client.get(
            "/api/v1/order-notifications/"
        )

        self.assertEqual(buyer_response.status_code, 200)

        buyer_results = buyer_response.data.get(
            "results",
            buyer_response.data,
        )

        self.assertTrue(
            all(
                item["order"] == order.id
                for item in buyer_results
            )
        )

        self.client.force_authenticate(
            user=self.seller_user
        )

        seller_response = self.client.get(
            "/api/v1/order-notifications/"
        )

        self.assertEqual(seller_response.status_code, 200)

        seller_results = seller_response.data.get(
            "results",
            seller_response.data,
        )

        self.assertTrue(
            all(
                item["order"] == order.id
                for item in seller_results
            )
        )