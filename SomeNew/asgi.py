"""
ASGI config for SomeNew project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SomeNew.settings')

# IMPORTANT (Vercel deployment ke liye):
# Pehle Django ko initialise karo, uske baad hi channels/homepage.routing import
# karo. Warna app registry ready nahi hoti aur ASGI entrypoint import pe crash
# karta hai (jo Vercel pe build/runtime error deta hai).
from django.core.asgi import get_asgi_application  # noqa: E402

django_asgi_application = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

import homepage.routing  # noqa: E402

application = ProtocolTypeRouter({
    # Django's ASGI application to handle standard HTTP requests
    "http": django_asgi_application,
    # WebSocket chat + notification handler
    "websocket": AuthMiddlewareStack(
        URLRouter(homepage.routing.websocket_urlpatterns)
    ),
})
