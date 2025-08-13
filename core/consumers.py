import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from .models import Chat, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        
        # Extract token from query string
        query_string = self.scope["query_string"].decode()
        token = None
        for part in query_string.split("&"):
            if part.startswith("token="):
                token = part.split("=", 1)[1]

        if not token:
            await self.close(code=4001)
            return

        # Authenticate user
        self.user = await database_sync_to_async(self.authenticate_token)(token)
        if not self.user:
            await self.close(code=4003)
            return

        # Check if user is in the chat
        if not await database_sync_to_async(self.user_in_chat)(self.user, self.chat_id):
            await self.close(code=4004)
            return

        self.room_group_name = f'chat_{self.chat_id}'

        # Join group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    def authenticate_token(self, token):
        try:
            jwt_auth = JWTAuthentication()
            validated = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated)
        except Exception:
            return None

    def user_in_chat(self, user, chat_id):
        try:
            chat = Chat.objects.get(pk=chat_id)
            return chat.participants.filter(pk=user.pk).exists()
        except Chat.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content")
        if not content:
            return

        # Save the message
        msg = await database_sync_to_async(self.save_message)(self.chat_id, self.user, content)

        payload = {
            "id": msg.id,
            "sender": self.user.username,
            "sender_id": self.user.id,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        }

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "payload": payload}
        )

    def save_message(self, chat_id, user, content):
        chat = Chat.objects.get(pk=chat_id)
        return Message.objects.create(chat=chat, sender=user, content=content)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
