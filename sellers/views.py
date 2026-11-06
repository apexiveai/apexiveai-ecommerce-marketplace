
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from rest_framework import generics, permissions, filters, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from accounts.models import SellerProfile
from .models import Showroom, Vehicle, VehicleImage
from .permissions import (
    IsMarketplaceAdmin,
    IsApprovedSeller,
    IsVehicleOwnerOrAdmin,
    get_approved_seller,
    is_marketplace_admin,
)
from .serializers import (
    SellerApplicationSerializer,
    SellerStatusSerializer,
    ShowroomSerializer,
    VehicleListSerializer,
    VehicleDetailSerializer,
    VehicleWriteSerializer,
    VehicleImageSerializer,
    VehicleImageReorderSerializer,
    VehicleModerationSerializer,
)


# --------------------------------------------------
# EXISTING SELLER APPLICATION API
# --------------------------------------------------

class SellerApplicationListView(APIView):
    permission_classes = [IsMarketplaceAdmin]

    def get(self, request):
        queryset = SellerProfile.objects.select_related("user").order_by(
            "created_at"
        )

        selected_status = request.query_params.get("status")
        allowed_statuses = {
            choice for choice, _label in SellerProfile.Status.choices
        }

        if selected_status:
            selected_status = selected_status.upper()

            if selected_status not in allowed_statuses:
                return Response(
                    {"detail": "Invalid seller status."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(status=selected_status)

        return Response(
            SellerApplicationSerializer(queryset, many=True).data
        )


class SellerApplicationStatusView(APIView):
    permission_classes = [IsMarketplaceAdmin]

    def patch(self, request, pk):
        seller = get_object_or_404(
            SellerProfile.objects.select_related("user"),
            pk=pk,
        )

        serializer = SellerStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        seller.status = serializer.validated_data["status"]
        seller.save(update_fields=["status"])

        return Response(SellerApplicationSerializer(seller).data)


# --------------------------------------------------
# SHOWROOM API
# --------------------------------------------------

class ShowroomListCreateView(generics.ListCreateAPIView):
    serializer_class = ShowroomSerializer
    permission_classes = [permissions.IsAuthenticated, IsApprovedSeller]

    def get_queryset(self):
        seller = get_approved_seller(self.request.user)

        return Showroom.objects.filter(
            seller=seller
        ).order_by("name")

    def perform_create(self, serializer):
        seller = get_approved_seller(self.request.user)
        serializer.save(seller=seller)


# --------------------------------------------------
# VEHICLE PUBLIC LIST / DEALER CREATE
# --------------------------------------------------

class VehicleListCreateView(generics.ListCreateAPIView):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "make", "model", "year", "condition",
        "transmission", "fuel_type", "currency",
    ]

    search_fields = [
        "make", "model", "trim", "description",
    ]

    ordering_fields = [
        "created_at", "price", "year", "mileage_km",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return Vehicle.objects.filter(
            status=Vehicle.Status.ACTIVE,
            seller__status=SellerProfile.Status.APPROVED,
        ).select_related(
            "seller", "showroom"
        ).prefetch_related("images")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return VehicleWriteSerializer
        return VehicleListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsApprovedSeller()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        seller = get_approved_seller(self.request.user)

        serializer.save(
            seller=seller,
            status=Vehicle.Status.DRAFT,
        )


# --------------------------------------------------
# DEALER OWN VEHICLE LIST
# --------------------------------------------------

class MyVehicleListView(generics.ListAPIView):
    serializer_class = VehicleDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsApprovedSeller]

    def get_queryset(self):
        seller = get_approved_seller(self.request.user)

        return Vehicle.objects.filter(
            seller=seller
        ).select_related(
            "seller", "showroom"
        ).prefetch_related("images")


# --------------------------------------------------
# VEHICLE DETAIL / UPDATE / DELETE
# --------------------------------------------------

class VehicleDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        queryset = Vehicle.objects.select_related(
            "seller", "showroom"
        ).prefetch_related("images")

        user = self.request.user

        if is_marketplace_admin(user):
            return queryset

        seller = get_approved_seller(user)

        if seller:
            return queryset.filter(
                models.Q(status=Vehicle.Status.ACTIVE)
                | models.Q(seller=seller)
            )

        return queryset.filter(
            status=Vehicle.Status.ACTIVE,
            seller__status=SellerProfile.Status.APPROVED,
        )

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]

        return [
            permissions.IsAuthenticated(),
            IsVehicleOwnerOrAdmin(),
        ]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return VehicleDetailSerializer
        return VehicleWriteSerializer


# --------------------------------------------------
# VEHICLE IMAGE UPLOAD
# --------------------------------------------------

class VehicleImageUploadView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsApprovedSeller,
    ]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, vehicle_id):
        seller = get_approved_seller(request.user)

        with transaction.atomic():
            vehicle = get_object_or_404(
                Vehicle.objects.select_for_update(),
                pk=vehicle_id,
                seller=seller,
            )

            serializer = VehicleImageSerializer(
                data=request.data,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)

            make_primary = serializer.validated_data.get(
                "is_primary", False
            )

            has_primary = vehicle.images.filter(
                is_primary=True
            ).exists()

            should_be_primary = make_primary or not has_primary

            image = serializer.save(
                vehicle=vehicle,
                is_primary=should_be_primary,
            )

            if should_be_primary:
                vehicle.images.exclude(
                    pk=image.pk
                ).update(is_primary=False)

        return Response(
            VehicleImageSerializer(
                image,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

class VehicleImageDeleteView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsApprovedSeller,
    ]

    def delete(self, request, image_id):
        seller = get_approved_seller(request.user)

        with transaction.atomic():
            image = get_object_or_404(
                VehicleImage.objects.select_related("vehicle"),
                pk=image_id,
                vehicle__seller=seller,
            )

            vehicle = get_object_or_404(
                Vehicle.objects.select_for_update(),
                pk=image.vehicle_id,
                seller=seller,
            )

            file_name = image.image.name
            storage = image.image.storage

            if image.is_primary:
                replacement = (
                    vehicle.images
                    .exclude(pk=image.pk)
                    .order_by("position", "id")
                    .first()
                )

                if replacement:
                    vehicle.images.exclude(
                        pk=replacement.pk
                    ).update(is_primary=False)

                    replacement.is_primary = True
                    replacement.save(
                        update_fields=["is_primary"]
                    )

            image.delete()

            if file_name:
                transaction.on_commit(
                    lambda: storage.delete(file_name)
                )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

class VehicleImagePrimaryView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsApprovedSeller,
    ]

    def patch(self, request, image_id):
        seller = get_approved_seller(request.user)

        with transaction.atomic():
            image = get_object_or_404(
                VehicleImage.objects.select_related("vehicle"),
                pk=image_id,
                vehicle__seller=seller,
            )

            vehicle = get_object_or_404(
                Vehicle.objects.select_for_update(),
                pk=image.vehicle_id,
                seller=seller,
            )

            vehicle.images.exclude(
                pk=image.pk
            ).update(is_primary=False)

            image.is_primary = True
            image.save(update_fields=["is_primary"])

        return Response(
            VehicleImageSerializer(
                image,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

class VehicleImageReorderView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsApprovedSeller,
    ]

    def patch(self, request, vehicle_id):
        seller = get_approved_seller(request.user)

        serializer = VehicleImageReorderSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        requested_ids = serializer.validated_data["image_ids"]

        with transaction.atomic():
            vehicle = get_object_or_404(
                Vehicle.objects.select_for_update(),
                pk=vehicle_id,
                seller=seller,
            )

            images = list(
                vehicle.images.select_for_update().order_by(
                    "position", "id"
                )
            )

            existing_ids = {
                image.id for image in images
            }

            if (
                len(requested_ids) != len(images)
                or set(requested_ids) != existing_ids
            ):
                return Response(
                    {
                        "detail": (
                            "You must provide every image ID "
                            "belonging to this vehicle exactly once."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            image_map = {
                image.id: image for image in images
            }

            reordered_images = []

            for position, image_id in enumerate(requested_ids):
                image = image_map[image_id]
                image.position = position
                reordered_images.append(image)

            VehicleImage.objects.bulk_update(
                reordered_images,
                ["position"],
            )

        return Response(
            VehicleImageSerializer(
                reordered_images,
                many=True,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )
# --------------------------------------------------
# ADMIN VEHICLE MODERATION
# --------------------------------------------------

class VehicleModerationView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsMarketplaceAdmin,
    ]

    def patch(self, request, pk):
        vehicle = get_object_or_404(
            Vehicle.objects.select_related("seller"),
            pk=pk,
        )

        serializer = VehicleModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vehicle.status = serializer.validated_data["status"]
        vehicle.save(update_fields=["status", "updated_at"])

        return Response({
            "detail": "Vehicle status updated.",
            "vehicle_id": vehicle.id,
            "status": vehicle.status,
        })
