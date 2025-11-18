from django.urls import path

from src.authz.views import LoginView, LogoutView, RegisterView, TokenRefreshCustomView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshCustomView.as_view(), name="token_refresh"),
]
