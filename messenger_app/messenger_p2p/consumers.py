import json
from channels.generic.websocket import AsyncWebsocketConsumer

PEERS = {}

class P2PConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        username = getattr(self, 'username', None)
        if username and username in PEERS:
            del PEERS[username]
            # Notify all remaining peers that someone left
            for channel_name in PEERS.values():
                await self.channel_layer.send(channel_name, {
                    'type': 'peer_update',
                    'peers': list(PEERS.keys()),
                })

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data['type'] == 'register':
            self.username = data['username']
            PEERS[self.username] = self.channel_name
            # Send the new peer the current peer list
            await self.send(json.dumps({
                'type': 'peer_list',
                'peers': [p for p in PEERS if p != self.username],
            }))
            # Notify everyone else that a new peer joined
            for username, channel_name in PEERS.items():
                if username != self.username:
                    await self.channel_layer.send(channel_name, {
                        'type': 'peer_update',
                        'peers': [p for p in PEERS if p != username],
                    })

        elif data['type'] == 'message':
            # Blindly forward to the recipient — no routing logic here
            recipient = data['to']
            if recipient in PEERS:
                await self.channel_layer.send(PEERS[recipient], {
                    'type': 'forward_message',
                    'from': self.username,
                    'text': data['text'],
                })

    async def forward_message(self, event):
        await self.send(json.dumps({
            'type': 'message',
            'from': event['from'],
            'text': event['text'],
        }))

    async def peer_update(self, event):
        await self.send(json.dumps({
            'type': 'peer_list',
            'peers': event['peers'],
        }))
