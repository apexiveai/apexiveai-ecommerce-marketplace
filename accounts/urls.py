
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenRefreshView,
)

from .serializers import MarketplaceTokenObtainPairSerializer
from .views import RegisterView, MeView
from rest_framework_simplejwt.views import TokenObtainPairView


class MarketplaceTokenObtainPairView(TokenObtainPairView):
    serializer_class = MarketplaceTokenObtainPairSerializer

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", MarketplaceTokenObtainPairView.as_view(), name="login"),
    path("logout/", TokenBlacklistView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
