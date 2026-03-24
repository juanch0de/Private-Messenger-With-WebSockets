"""
ASGI config for messenger_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from messenger import routing as messenger_routing
from messenger_p2p import routing as p2p_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messenger_app.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': URLRouter(
        messenger_routing.websocket_urlpatterns +
        p2p_routing.websocket_urlpatterns
        ),
    })
