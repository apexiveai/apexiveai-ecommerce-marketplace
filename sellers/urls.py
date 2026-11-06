
from django.urls import path

from .views import (
    SellerApplicationListView,
    SellerApplicationStatusView,
    ShowroomListCreateView,
    VehicleListCreateView,
    MyVehicleListView,
    VehicleDetailView,
    VehicleImageUploadView,
    VehicleModerationView,
    VehicleImageDeleteView,
    VehicleImagePrimaryView,
    VehicleImageReorderView,
)

urlpatterns = [
    # Seller application
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

    # Showrooms
    path(
        "showrooms/",
        ShowroomListCreateView.as_view(),
        name="showroom-list-create",
    ),

    # Automotive vehicles
    path(
        "vehicles/",
        VehicleListCreateView.as_view(),
        name="vehicle-list-create",
    ),
    path(
        "vehicles/mine/",
        MyVehicleListView.as_view(),
        name="my-vehicles",
    ),
    path(
        "vehicles/<int:pk>/",
        VehicleDetailView.as_view(),
        name="vehicle-detail",
    ),
    path(
        "vehicles/<int:vehicle_id>/images/",
        VehicleImageUploadView.as_view(),
        name="vehicle-image-upload",
    ),
    path(
        "vehicles/<int:pk>/moderation/",
        VehicleModerationView.as_view(),
        name="vehicle-moderation",
    ),
        # Vehicle image management
    path(
        "vehicles/<int:vehicle_id>/images/reorder/",
        VehicleImageReorderView.as_view(),
        name="vehicle-image-reorder",
    ),
    path(
        "vehicles/images/<int:image_id>/",
        VehicleImageDeleteView.as_view(),
        name="vehicle-image-delete",
    ),
    path(
        "vehicles/images/<int:image_id>/primary/",
        VehicleImagePrimaryView.as_view(),
        name="vehicle-image-primary",
    ),
]
