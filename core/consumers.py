import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from .models import Chat, Message
from .serializers import MessageSerializer

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']  # "all" or chat_id

        # Extract token from query string
        query_string = self.scope["query_string"].decode()
        token = None
        for part in query_string.split("&"):
            if part.startswith("token="):
                token = part.split("=", 1)[1]

        if not token:
            await self.close(code=4001)  # Missing token
            return

        # Authenticate user
        self.user = await database_sync_to_async(self.authenticate_token)(token)
        if not self.user:
            await self.close(code=4003)  # Invalid token
            return

        # Mode 1: Student (single chat_id)
        if self.chat_id != "all":
            in_chat = await database_sync_to_async(self.user_in_chat)(self.user, self.chat_id)
            if not in_chat:
                await self.close(code=4004)  # Not in chat
                return

            self.room_group_name = f'chat_{self.chat_id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Mode 2: Teacher (subscribe to all their chats)
        else:
            if self.user.role != "teacher":
                await self.close(code=4005)  # Only teachers allowed
                return

            chats = await database_sync_to_async(self.get_user_chats)(self.user)
            self.room_group_names = [f"chat_{c.id}" for c in chats]

            for group in self.room_group_names:
                await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()

    # ------------------ HELPERS ------------------

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

    def get_user_chats(self, user):
        """Return all chats where user is a participant"""
        return list(Chat.objects.filter(participants=user))

    def save_message(self, chat_id, user, content):
        chat = Chat.objects.get(pk=chat_id)
        return Message.objects.create(chat=chat, sender=user, content=content)

    # ------------------ LIFECYCLE ------------------

    async def disconnect(self, close_code):
        if self.chat_id != "all":
            await self.channel_layer.group_discard(f"chat_{self.chat_id}", self.channel_name)
        else:
            for group in getattr(self, "room_group_names", []):
                await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content")
        target_chat_id = data.get("chat_id", None)

        if not content:
            return

        # Case 1: student → chat_id from URL
        if self.chat_id != "all":
            target_chat_id = self.chat_id

        # Case 2: teacher → must include chat_id in payload
        elif not target_chat_id:
            return

        # Save message safely
        msg = await database_sync_to_async(self.save_message)(target_chat_id, self.user, content)
        payload = MessageSerializer(msg).data

        # Broadcast only to target chat group
        await self.channel_layer.group_send(
            f"chat_{target_chat_id}",
            {"type": "chat_message", "payload": payload}
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
