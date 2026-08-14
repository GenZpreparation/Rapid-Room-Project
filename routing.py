from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # This regex matches the URL for our notification WebSocket.
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]