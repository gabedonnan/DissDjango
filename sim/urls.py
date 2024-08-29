from django.urls import path, include, re_path
from django.contrib.auth.views import LoginView, LogoutView
from .views import (
    main_page,
    simulation_page_dutch,
    simulation_page_english,
    simulation_page_fpsb,
    simulation_page_spsb,
    simulation_page_cda,
    join_page
)

urlpatterns = [
    path("", main_page, name="main_page"),
    path("join", join_page, name="join_page"),
    re_path(
        r"dutch/(?P<room_name>\w+)", simulation_page_dutch, name="simulation_page_dutch"
    ),  # Dutch room path
    re_path(
        r"english/(?P<room_name>\w+)",
        simulation_page_english,
        name="simulation_page_english",
    ),  # English room path
    re_path(
        r"FPSB/(?P<room_name>\w+)", simulation_page_fpsb, name="simulation_page_fpsb"
    ),  # First price sealed bid room path
    re_path(
        r"SPSB/(?P<room_name>\w+)", simulation_page_spsb, name="simulation_page_spsb"
    ),  # Second price sealed bid room path
    re_path(
        r"CDA/(?P<room_name>\w+)", simulation_page_cda, name="simulation_page_cda"
    ),  # Continuous double auction room path
    # Login Path
    path(
        "auth/login/",
        LoginView.as_view(template_name="sim/login_page.html"),
        name="login_user",
    ),
    # Logout Path
    path("auth/logout/", LogoutView.as_view(), name="logout_user"),
]
