from django.urls import re_path

from .websocket_consumers import SimConsumer

websocket_urlpatterns = [
    re_path(r"ws/rooms/(?P<room_name>\w+)", SimConsumer.as_asgi())
]
