from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CheckoutView,
    OrderViewSet,
    OrderNotificationViewSet,
)

router = DefaultRouter()

router.register(
    "orders",
    OrderViewSet,
    basename="marketplace-order",
)

router.register(
    "notifications",
    OrderNotificationViewSet,
    basename="marketplace-notification",
)

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("", include(router.urls)),
]