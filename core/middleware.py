# core/middleware.py
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from core.models import User

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        scope["user"] = AnonymousUser()

        if token:
            try:
                validated_token = AccessToken(token)
                user_id = validated_token["user_id"]
                scope["user"] = await get_user(user_id)
            except Exception:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
