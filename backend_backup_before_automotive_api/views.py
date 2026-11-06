from django.shortcuts import render
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import SellerProfile
from .serializers import (
    SellerApplicationSerializer,
    SellerStatusSerializer,
)


# Create your views here.
class IsMarketplaceAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "role", None) == "ADMIN"
            )
        )


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
            SellerApplicationSerializer(
                queryset,
                many=True,
            ).data
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

        return Response(
            SellerApplicationSerializer(seller).data
        )
