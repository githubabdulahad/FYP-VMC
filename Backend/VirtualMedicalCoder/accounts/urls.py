from .views import RegisterView ,LoginView, LogoutView, MeView, TokenRefreshView
from django.urls import path

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/",   LoginView.as_view(),        name="auth-login"),
    path("logout/",  LogoutView.as_view(),        name="auth-logout"),
    path("refresh/", TokenRefreshView.as_view(),  name="auth-refresh"),
    path("me/",      MeView.as_view(),            name="auth-me"),
]