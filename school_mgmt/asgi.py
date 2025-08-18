from channels.routing import ProtocolTypeRouter, URLRouter
from core.middleware import JWTAuthMiddleware
from core.routing import websocket_urlpatterns
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
