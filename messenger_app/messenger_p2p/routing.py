from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/p2p/$', consumers.P2PConsumer.as_asgi()),
]
