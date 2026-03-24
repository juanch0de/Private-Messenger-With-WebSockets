import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Routing table: username → channel_name (not the socket object directly)
CLIENTS = {}

class MessengerConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Accept the connection but wait for a register message
        await self.accept()

    async def disconnect(self, close_code):
        # Remove this user from the routing table on disconnect
        username = getattr(self, 'username', None)
        if username and username in CLIENTS:
            del CLIENTS[username]
            print(f"[-] '{username}' disconnected.")

    async def receive(self, text_data):
        data = json.loads(text_data)

        # First message: register with a username
        if data.get('type') == 'register':
            username = data['username']

            if username in CLIENTS:
                await self.send(json.dumps({
                    'type': 'error',
                    'text': f"Username '{username}' is already taken."
                }))
                await self.close()
                return

            self.username = username
            CLIENTS[username] = self.channel_name  # store channel_name, not self
            print(f"[+] '{username}' connected. Online: {list(CLIENTS.keys())}")

            await self.send(json.dumps({
                'type': 'system',
                'text': f"Welcome! Online: {[u for u in CLIENTS if u != username]}"
            }))

        # Subsequent messages: private message to a recipient
        elif data.get('type') == 'message':
            recipient = data['to']
            text = data['text']

            if recipient not in CLIENTS:
                await self.send(json.dumps({
                    'type': 'error',
                    'text': f"'{recipient}' is not online."
                }))
            else:
                # Send to recipient via their channel name
                await self.channel_layer.send(CLIENTS[recipient], {
                    'type': 'forward_message',
                    'from': self.username,
                    'text': text,
                })
                # Echo back to sender
                await self.send(json.dumps({
                    'type': 'message',
                    'from': f'you → {recipient}',
                    'text': text,
                }))

    # Called by channel_layer.send() on the recipient's consumer instance
    async def forward_message(self, event):
        await self.send(json.dumps({
            'type': 'message',
            'from': event['from'],
            'text': event['text'],
        }))
