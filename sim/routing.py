from django.urls import re_path

from .websocket_consumers import SimConsumer

websocket_urlpatterns = [
    re_path(r"(?P<domain_prefix>\w+)/ws/dutch/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"(?P<domain_prefix>\w+)/ws/english/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"(?P<domain_prefix>\w+)/ws/fpsb/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"(?P<domain_prefix>\w+)/ws/spsb/(?P<room_name>\w+)", SimConsumer.as_asgi()),
    re_path(r"(?P<domain_prefix>\w+)/ws/cda/(?P<room_name>\w+)", SimConsumer.as_asgi()),
]
