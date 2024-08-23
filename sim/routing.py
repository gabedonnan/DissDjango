from django.urls import re_path

from .websocket_consumers import SimConsumer

websocket_urlpatterns = [
    re_path(r"ws/dutch/(?P<room_name>\w+)/$", SimConsumer.as_asgi()),
    re_path(r"ws/english/(?P<room_name>\w+)/$", SimConsumer.as_asgi()),
    re_path(r"ws/FPSB/(?P<room_name>\w+)/$", SimConsumer.as_asgi()),
    re_path(r"ws/SPSB/(?P<room_name>\w+)/$", SimConsumer.as_asgi()),
    re_path(r"ws/CDA/(?P<room_name>\w+)/$", SimConsumer.as_asgi()),
]
