from django.urls import path, include, re_path
from django.contrib.auth.views import LoginView, LogoutView
from .views import simulation_page, main_page

urlpatterns = [
    path("", main_page, name="main_page"),

    re_path(r"rooms/(?P<room_name>\w+)", simulation_page, name="simulation_page"),  # Sim room path

    # Login Path
    path(
        "auth/login/",
        LoginView.as_view(template_name="sim/login_page.html"),
        name="login_user"
    ),

    # Logout Path
    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="logout_user"
    ),
]

