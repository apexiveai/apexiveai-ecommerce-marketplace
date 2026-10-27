from django.shortcuts import render

from django.db.models import Q

from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from accounts.models import SellerProfile
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

# Create your views here.
def is_marketplace_admin(user):
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "role", None) == "ADMIN"
        )
    )


class IsProductOwnerOrMarketplaceAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if is_marketplace_admin(request.user):
            return True

        return (
            obj.seller.user_id == request.user.id
            and obj.seller.status == SellerProfile.Status.APPROVED
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    queryset = Category.objects.filter(is_active=True)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsProductOwnerOrMarketplaceAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ["category", "currency", "status"]
    search_fields = ["name", "description", "sku", "category__name"]
    ordering_fields = ["created_at", "price", "name", "stock_quantity"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Product.objects.select_related(
            "seller",
            "seller__user",
            "category",
        )

        user = self.request.user

        if is_marketplace_admin(user):
            return queryset

        public_products = Q(
            status=Product.Status.ACTIVE,
            seller__status=SellerProfile.Status.APPROVED,
            category__is_active=True,
        )

        if user.is_authenticated:
            own_products = Q(seller__user=user)
            return queryset.filter(public_products | own_products).distinct()

        return queryset.filter(public_products)

    def perform_create(self, serializer):
        user = self.request.user

        if is_marketplace_admin(user):
            raise PermissionDenied(
                "Create products using an approved seller account."
            )

        try:
            seller = user.seller_profile
        except SellerProfile.DoesNotExist:
            raise PermissionDenied(
                "A seller account is required to create products."
            )

        if seller.status != SellerProfile.Status.APPROVED:
            raise PermissionDenied(
                "Your seller account must be approved first."
            )

        serializer.save(seller=seller)

    def perform_update(self, serializer):
        user = self.request.user

        if is_marketplace_admin(user):
            serializer.save()
            return

        try:
            seller = user.seller_profile
        except SellerProfile.DoesNotExist:
            raise PermissionDenied("A seller account is required.")

        if seller.status != SellerProfile.Status.APPROVED:
            raise PermissionDenied(
                "Your seller account is not approved."
            )

        if serializer.instance.seller_id != seller.id:
            raise PermissionDenied(
                "You can only update your own products."
            )

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if is_marketplace_admin(user):
            instance.delete()
            return

        try:
            seller = user.seller_profile
        except SellerProfile.DoesNotExist:
            raise PermissionDenied("A seller account is required.")

        if (
            seller.status != SellerProfile.Status.APPROVED
            or instance.seller_id != seller.id
        ):
            raise PermissionDenied(
                "You can only delete your own products as an approved seller."
            )

        instance.delete()
