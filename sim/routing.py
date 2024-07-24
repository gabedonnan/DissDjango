from django.urls import re_path

from .websocket_consumers import SimConsumer

websocket_urlpatterns = [
    re_path(r"ws/dutch/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"ws/english/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"ws/fpsb/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"ws/spsb/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"ws/cda/(?P<room_name>\w+)", SimConsumer.as_asgi()),
]
