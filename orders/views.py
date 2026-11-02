from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Count, Sum
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import SellerProfile
from catalog.models import Product

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    OrderNotification,
)
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    OrderNotificationSerializer,
)


# ============================================================
# PERMISSIONS
# ============================================================

def is_marketplace_admin(user):
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "role", None) == "ADMIN"
        )
    )


def create_order_notification(order, title, message):
    recipients = {
        order.buyer_id,
        order.seller.user_id,
    }

    OrderNotification.objects.bulk_create([
        OrderNotification(
            user_id=user_id,
            order=order,
            title=title,
            message=message,
        )
        for user_id in recipients
    ])


# ============================================================
# ORDER STATUS SERVICES
# These functions must be called inside transaction.atomic().
# ============================================================

def change_order_status(order, new_status, user, note=""):
    old_status = order.status

    if old_status == new_status:
        raise ValidationError(
            "Order already has this status."
        )

    valid_statuses = {
        choice[0] for choice in Order.Status.choices
    }

    if new_status not in valid_statuses:
        raise ValidationError(
            {"status": "Invalid order status."}
        )

    order.status = new_status

    update_fields = [
        "status",
        "updated_at",
    ]

    if new_status == Order.Status.SHIPPED:
        order.shipped_at = timezone.now()
        update_fields.append("shipped_at")

    if new_status == Order.Status.COMPLETED:
        order.completed_at = timezone.now()
        update_fields.append("completed_at")

    order.save(update_fields=update_fields)

    OrderStatusHistory.objects.create(
        order=order,
        previous_status=old_status,
        new_status=new_status,
        changed_by=user,
        note=note,
    )

    create_order_notification(
        order,
        f"Order {order.order_number} updated",
        f"Order status changed to {order.get_status_display()}.",
    )


def cancel_order_locked(order, user, note=""):
    """
    Cancel an unshipped order and restore stock exactly once.

    Caller must hold a database transaction and lock the Order row.
    """

    cancellable_statuses = {
        Order.Status.NEW,
        Order.Status.PROCESSING,
        Order.Status.READY_TO_SHIP,
    }

    if order.status not in cancellable_statuses:
        raise ValidationError(
            "Only unshipped orders can be cancelled."
        )

    items = order.items.all()

    for item in items:
        if item.product_id:
            Product.objects.filter(
                pk=item.product_id
            ).update(
                stock_quantity=F("stock_quantity") + item.quantity
            )

    change_order_status(
        order,
        Order.Status.CANCELLED,
        user,
        note or "Order cancelled. Stock restored.",
    )


# ============================================================
# CHECKOUT
# ============================================================

class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        if is_marketplace_admin(request.user):
            raise PermissionDenied(
                "Marketplace administrators cannot checkout as buyers."
            )

        if getattr(request.user, "role", None) != "BUYER":
            raise PermissionDenied(
                "A buyer account is required to checkout."
            )

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        requested_items = data["items"]

        requested_quantities = {
            item["product_id"]: item["quantity"]
            for item in requested_items
        }

        product_ids = list(requested_quantities.keys())

        with transaction.atomic():

            products = list(
                Product.objects.select_for_update()
                .select_related(
                    "seller",
                    "seller__user",
                    "category",
                )
                .filter(id__in=product_ids)
                .order_by("id")
            )

            if len(products) != len(product_ids):
                raise ValidationError({
                    "items": "One or more products do not exist."
                })

            grouped_products = defaultdict(list)

            for product in products:

                if product.status != Product.Status.ACTIVE:
                    raise ValidationError(
                        f"{product.name} is not available."
                    )

                if (
                    product.seller.status
                    != SellerProfile.Status.APPROVED
                ):
                    raise ValidationError(
                        f"Seller for {product.name} is not approved."
                    )

                if not product.category.is_active:
                    raise ValidationError(
                        f"Category for {product.name} is unavailable."
                    )

                quantity = requested_quantities[product.id]

                if product.stock_quantity < quantity:
                    raise ValidationError(
                        f"Insufficient stock for {product.name}."
                    )

                grouped_products[product.seller_id].append(
                    (product, quantity)
                )

            created_orders = []

            for seller_id, seller_items in grouped_products.items():

                currencies = {
                    product.currency.upper()
                    for product, quantity in seller_items
                }

                if len(currencies) != 1:
                    raise ValidationError(
                        "Products from one seller must use the same currency."
                    )

                currency = currencies.pop()

                subtotal = Decimal("0.00")
                discount_total = Decimal("0.00")

                for product, quantity in seller_items:
                    sale_price = product.sale_price

                    subtotal += sale_price * quantity

                    discount_per_unit = (
                        product.price - sale_price
                    )

                    discount_total += (
                        discount_per_unit * quantity
                    )

                shipping_fee = Decimal("0.00")
                total_amount = subtotal + shipping_fee

                order = Order.objects.create(
                    buyer=request.user,
                    seller_id=seller_id,
                    status=Order.Status.NEW,
                    payment_status=Order.PaymentStatus.UNPAID,
                    payment_method=data["payment_method"],
                    currency=currency,
                    subtotal=subtotal,
                    shipping_fee=shipping_fee,
                    discount_total=discount_total,
                    total_amount=total_amount,
                    shipping_full_name=data["shipping_full_name"],
                    shipping_phone=data["shipping_phone"],
                    shipping_address_line1=data[
                        "shipping_address_line1"
                    ],
                    shipping_address_line2=data.get(
                        "shipping_address_line2", ""
                    ),
                    shipping_city=data["shipping_city"],
                    shipping_region=data.get(
                        "shipping_region", ""
                    ),
                    shipping_postal_code=data.get(
                        "shipping_postal_code", ""
                    ),
                    shipping_country_code=data[
                        "shipping_country_code"
                    ],
                    buyer_note=data.get("buyer_note", ""),
                )

                for product, quantity in seller_items:

                    # Conditional UPDATE is important for SQLite too.
                    # select_for_update() alone does not provide
                    # effective row locking on SQLite.

                    updated = Product.objects.filter(
                        pk=product.pk,
                        stock_quantity__gte=quantity,
                        status=Product.Status.ACTIVE,
                    ).update(
                        stock_quantity=F("stock_quantity") - quantity
                    )

                    if updated != 1:
                        raise ValidationError(
                            f"Stock changed for {product.name}. "
                            "Please try again."
                        )

                    sale_price = product.sale_price

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_sku=product.sku,
                        quantity=quantity,
                        original_unit_price=product.price,
                        discount_percent=product.discount_percent,
                        unit_price=sale_price,
                        line_total=sale_price * quantity,
                    )

                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status="",
                    new_status=Order.Status.NEW,
                    changed_by=request.user,
                    note="Order created by buyer checkout.",
                )

                create_order_notification(
                    order,
                    "New marketplace order",
                    f"New order {order.order_number} requires your review.",
                )

                created_orders.append(order)

        result = OrderSerializer(
            created_orders,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "message": "Checkout completed successfully.",
                "orders_created": len(created_orders),
                "orders": result.data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# ORDER MANAGEMENT
# ============================================================

class OrderViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    filterset_fields = [
        "status",
        "payment_status",
        "payment_method",
        "currency",
    ]

    search_fields = [
        "order_number",
        "buyer__username",
        "buyer__email",
        "shipping_full_name",
        "shipping_phone",
        "items__product_name",
        "items__product_sku",
    ]

    ordering_fields = [
        "created_at",
        "updated_at",
        "total_amount",
        "status",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):

        queryset = Order.objects.select_related(
            "buyer",
            "seller",
            "seller__user",
        ).prefetch_related(
            "items",
            "status_history",
        )

        user = self.request.user

        if is_marketplace_admin(user):
            return queryset

        if getattr(user, "role", None) == "SELLER":
            try:
                seller = user.seller_profile
            except SellerProfile.DoesNotExist:
                return queryset.none()

            return queryset.filter(
                seller=seller
            ).distinct()

        return queryset.filter(
            buyer=user
        ).distinct()

    def _check_seller_or_admin(self, order):

        if is_marketplace_admin(self.request.user):
            return

        try:
            seller = self.request.user.seller_profile
        except SellerProfile.DoesNotExist:
            raise PermissionDenied(
                "Seller account required."
            )

        if order.seller_id != seller.id:
            raise PermissionDenied(
                "You cannot manage another seller's order."
            )

        if seller.status != SellerProfile.Status.APPROVED:
            raise PermissionDenied(
                "Your seller account is not approved."
            )

    def _get_locked_order(self, visible_order):

        return (
            Order.objects.select_for_update()
            .select_related(
                "buyer",
                "seller",
                "seller__user",
            )
            .get(pk=visible_order.pk)
        )

    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

    @action(detail=False, methods=["get"])
    def dashboard(self, request):

        orders = self.get_queryset()

        summary = orders.aggregate(
            total_orders=Count("id"),
            total_sales=Sum("total_amount"),
        )

        counts = {
            item["status"]: item["count"]
            for item in orders.values("status").annotate(
                count=Count("id")
            )
        }

        payment_counts = {
            item["payment_status"]: item["count"]
            for item in orders.values(
                "payment_status"
            ).annotate(
                count=Count("id")
            )
        }

        return Response({
            "total_orders": summary["total_orders"] or 0,
            "total_sales": (
                summary["total_sales"] or Decimal("0.00")
            ),
            "status_counts": counts,
            "payment_counts": payment_counts,
        })

    # --------------------------------------------------------
    # ACCEPT ORDER
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):

        visible_order = self.get_object()

        with transaction.atomic():

            order = self._get_locked_order(visible_order)
            self._check_seller_or_admin(order)

            if order.status != Order.Status.NEW:
                raise ValidationError(
                    "Only new orders can be accepted."
                )

            change_order_status(
                order,
                Order.Status.PROCESSING,
                request.user,
                request.data.get("note", ""),
            )

        return Response(self.get_serializer(order).data)

    # --------------------------------------------------------
    # REJECT ORDER
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):

        visible_order = self.get_object()

        with transaction.atomic():

            order = self._get_locked_order(visible_order)
            self._check_seller_or_admin(order)

            if order.status != Order.Status.NEW:
                raise ValidationError(
                    "Only new orders can be rejected."
                )

            cancel_order_locked(
                order,
                request.user,
                request.data.get(
                    "note",
                    "Rejected by seller.",
                ),
            )

        return Response(self.get_serializer(order).data)

    # --------------------------------------------------------
    # UPDATE STATUS
    # Seller: PROCESSING -> READY_TO_SHIP
    # Admin: controlled transitions
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):

        new_status = request.data.get("status")

        valid_statuses = {
            choice[0] for choice in Order.Status.choices
        }

        if new_status not in valid_statuses:
            raise ValidationError({
                "status": "Invalid order status."
            })

        visible_order = self.get_object()

        with transaction.atomic():

            order = self._get_locked_order(visible_order)
            self._check_seller_or_admin(order)

            if is_marketplace_admin(request.user):

                admin_transitions = {
                    Order.Status.NEW: {
                        Order.Status.PROCESSING,
                        Order.Status.CANCELLED,
                    },
                    Order.Status.PROCESSING: {
                        Order.Status.READY_TO_SHIP,
                        Order.Status.CANCELLED,
                    },
                    Order.Status.READY_TO_SHIP: {
                        Order.Status.CANCELLED,
                    },
                    Order.Status.SHIPPED: {
                        Order.Status.COMPLETED,
                    },
                }

                allowed = admin_transitions.get(
                    order.status,
                    set(),
                )

            else:

                seller_transitions = {
                    Order.Status.PROCESSING: {
                        Order.Status.READY_TO_SHIP,
                    },
                }

                allowed = seller_transitions.get(
                    order.status,
                    set(),
                )

            if new_status not in allowed:
                raise ValidationError(
                    "This status transition is not allowed."
                )

            if new_status == Order.Status.CANCELLED:

                cancel_order_locked(
                    order,
                    request.user,
                    request.data.get("note", ""),
                )

            else:

                change_order_status(
                    order,
                    new_status,
                    request.user,
                    request.data.get("note", ""),
                )

        return Response(self.get_serializer(order).data)

    # --------------------------------------------------------
    # SHIPMENT
    # READY_TO_SHIP -> SHIPPED only
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def shipment(self, request, pk=None):

        carrier = request.data.get(
            "shipping_carrier", ""
        )

        tracking = request.data.get(
            "tracking_number", ""
        )

        if not isinstance(carrier, str):
            raise ValidationError({
                "shipping_carrier": "Invalid carrier."
            })

        if not isinstance(tracking, str):
            raise ValidationError({
                "tracking_number": "Invalid tracking number."
            })

        carrier = carrier.strip()
        tracking = tracking.strip()

        if not carrier or not tracking:
            raise ValidationError({
                "shipping": (
                    "Shipping carrier and tracking number are required."
                )
            })

        if len(carrier) > 120 or len(tracking) > 150:
            raise ValidationError({
                "shipping": "Shipping information is too long."
            })

        visible_order = self.get_object()

        with transaction.atomic():

            order = self._get_locked_order(visible_order)
            self._check_seller_or_admin(order)

            if order.status != Order.Status.READY_TO_SHIP:
                raise ValidationError(
                    "Only READY_TO_SHIP orders can be shipped."
                )

            order.shipping_carrier = carrier
            order.tracking_number = tracking

            order.save(
                update_fields=[
                    "shipping_carrier",
                    "tracking_number",
                    "updated_at",
                ]
            )

            change_order_status(
                order,
                Order.Status.SHIPPED,
                request.user,
                request.data.get(
                    "note",
                    "Shipment information added.",
                ),
            )

        return Response(self.get_serializer(order).data)

    # --------------------------------------------------------
    # BUYER DELIVERY CONFIRMATION
    # SHIPPED -> COMPLETED
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def confirm_delivery(self, request, pk=None):

        if getattr(request.user, "role", None) != "BUYER":
            raise PermissionDenied(
                "Only the buyer can confirm delivery."
            )

        visible_order = self.get_object()

        with transaction.atomic():

            order = self._get_locked_order(visible_order)

            if order.buyer_id != request.user.id:
                raise PermissionDenied(
                    "You cannot confirm another buyer's order."
                )

            if order.status != Order.Status.SHIPPED:
                raise ValidationError(
                    "Only shipped orders can be confirmed."
                )

            change_order_status(
                order,
                Order.Status.COMPLETED,
                request.user,
                request.data.get(
                    "note",
                    "Delivery confirmed by buyer.",
                ),
            )

        return Response(self.get_serializer(order).data)

    # --------------------------------------------------------
    # PAYMENT MANAGEMENT - ADMIN ONLY
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):

        if not is_marketplace_admin(request.user):
            raise PermissionDenied(
                "Only marketplace administrators can verify payments."
            )

        payment_status = request.data.get("payment_status")

        valid_statuses = {
            choice[0]
            for choice in Order.PaymentStatus.choices
        }

        if payment_status not in valid_statuses:
            raise ValidationError({
                "payment_status": "Invalid payment status."
            })

        visible_order = self.get_object()

        with transaction.atomic():

            order = self._get_locked_order(visible_order)

            old_payment_status = order.payment_status

            if old_payment_status == payment_status:
                raise ValidationError(
                    "Payment already has this status."
                )

            order.payment_status = payment_status

            order.save(
                update_fields=[
                    "payment_status",
                    "updated_at",
                ]
            )

            create_order_notification(
                order,
                "Payment status updated",
                (
                    "Payment status changed from "
                    f"{old_payment_status} to {payment_status}."
                ),
            )

        return Response(self.get_serializer(order).data)

    # --------------------------------------------------------
    # INVOICE
    # Returns structured data for frontend printing.
    # Not a generated PDF.
    # --------------------------------------------------------

    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):

        order = self.get_object()

        return Response({
            "document_type": "INVOICE",
            "order": self.get_serializer(order).data,
        })

    # --------------------------------------------------------
    # PACKING SLIP
    # Returns structured data for frontend printing.
    # Not a generated PDF.
    # --------------------------------------------------------

    @action(detail=True, methods=["get"])
    def packing_slip(self, request, pk=None):

        order = self.get_object()

        return Response({
            "document_type": "PACKING_SLIP",
            "order": self.get_serializer(order).data,
        })


# ============================================================
# NOTIFICATIONS
# ============================================================

class OrderNotificationViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = OrderNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        return OrderNotification.objects.filter(
            user=self.request.user
        ).select_related("order")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):

        notification = self.get_object()

        notification.is_read = True

        notification.save(
            update_fields=["is_read"]
        )

        return Response(
            self.get_serializer(notification).data
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):

        self.get_queryset().filter(
            is_read=False
        ).update(
            is_read=True
        )

        return Response({
            "message": "All notifications marked as read."
        })