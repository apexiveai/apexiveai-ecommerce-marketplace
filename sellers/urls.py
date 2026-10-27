
from django.urls import path

from .views import (
    SellerApplicationListView,
    SellerApplicationStatusView,
)

urlpatterns = [
    path(
        "applications/",
        SellerApplicationListView.as_view(),
        name="seller-applications",
    ),
    path(
        "applications/<int:pk>/status/",
        SellerApplicationStatusView.as_view(),
        name="seller-application-status",
    ),
]
