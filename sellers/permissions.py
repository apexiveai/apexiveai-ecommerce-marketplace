
from rest_framework.permissions import BasePermission


def is_marketplace_admin(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "role", None) == "ADMIN"
        )
    )


def get_approved_seller(user):
    if not user or not user.is_authenticated:
        return None

    try:
        seller = user.seller_profile
    except Exception:
        return None

    if seller.status != "APPROVED":
        return None

    return seller


class IsMarketplaceAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_marketplace_admin(request.user)


class IsApprovedSeller(BasePermission):
    def has_permission(self, request, view):
        return get_approved_seller(request.user) is not None


class IsVehicleOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_marketplace_admin(request.user):
            return True

        seller = get_approved_seller(request.user)

        return bool(
            seller and obj.seller_id == seller.id
        )


class IsShowroomOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_marketplace_admin(request.user):
            return True

        seller = get_approved_seller(request.user)

        return bool(
            seller and obj.seller_id == seller.id
        )
