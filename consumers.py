import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Conversation, Message, user


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # A user is only authenticated if they are logged in.
        if self.scope["user"].is_authenticated:
            # Each user gets their own private notification group.
            # The group name is based on their user ID.
            self.group_name = f'user_notifications_{self.scope["user"].id}'

            # Join the user's group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            await self.accept()
        else:
            # Reject the connection if the user is not authenticated.
            await self.close()

    async def disconnect(self, close_code):
        # Leave the user's group when they disconnect
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_remove(self.group_name, self.channel_name)

    # This method is called when a message is sent to the group.
    async def send_notification(self, event):
        # Send the message data to the WebSocket.
        await self.send(text_data=json.dumps(event["message"]))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        if self.user.is_authenticated:
            is_participant = await self.is_user_participant(self.user, self.conversation_id)
            if is_participant:
                # Join room group
                await self.channel_layer.group_add(
                    self.conversation_group_name,
                    self.channel_name
                )
                await self.accept()
            else:
                await self.close()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_remove(
            self.conversation_group_name,
            self.channel_name
        )

    # This method is called by the view when a new message is saved
    async def new_message(self, event): # Renamed to match the 'type' sent from the view
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            # We reconstruct the payload here to ensure consistency
            # and only send what the client needs.
            'text': event['text'],       # Access directly from event
            'sender_id': event['sender_id'], # Access directly from event
        }))

    # This method is for receiving messages from the WebSocket (e.g., typing indicators)
    # We are not using it for sending messages from client to server in this setup.
    async def receive(self, text_data):
        pass

    @sync_to_async
    def is_user_participant(self, user, conversation_id):
        """
        Checks if a user is a participant in a given conversation.
        """
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
            return user in conversation.participants.all()
        except Conversation.DoesNotExist:
            return False