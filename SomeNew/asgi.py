"""
ASGI config for SomeNew project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import homepage.routing 


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SomeNew.settings')

application = ProtocolTypeRouter({
  # Django's ASGI application to handle standard HTTP requests
  "http": get_asgi_application(),
  # WebSocket chat handler
  "websocket": AuthMiddlewareStack(
        URLRouter(homepage.routing.websocket_urlpatterns)
    ),
})
