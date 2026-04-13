import json
from channels.generic.websocket import AsyncWebsocketConsumer

# PEERS = { username: { 'channel': channel_name, 'public_key': <JWK dict> } }
PEERS = {}

def _peer_list_for(exclude_username):
    """Return [{username, public_key}, ...] for everyone except exclude_username."""
    return [
        {'username': u, 'public_key': info['public_key']}
        for u, info in PEERS.items()
        if u != exclude_username
    ]

class P2PConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        username = getattr(self, 'username', None)
        if username and username in PEERS:
            del PEERS[username]
            # Notify remaining peers — include updated peer list with public keys
            for u, info in PEERS.items():
                await self.channel_layer.send(info['channel'], {
                    'type': 'peer_update',
                    'peers': _peer_list_for(u),
                })

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data['type'] == 'register':
            self.username = data['username']
            # Store channel_name AND the client's ECC public key (JWK)
            PEERS[self.username] = {
                'channel': self.channel_name,
                'public_key': data['public_key'],
            }

            # Send the new peer the current peer list (with public keys)
            await self.send(json.dumps({
                'type': 'peer_list',
                'peers': _peer_list_for(self.username),
            }))

            # Notify everyone else — they need the new peer's public key too
            for u, info in PEERS.items():
                if u != self.username:
                    await self.channel_layer.send(info['channel'], {
                        'type': 'peer_update',
                        'peers': _peer_list_for(u),
                    })

        elif data['type'] == 'message':
            # Blindly relay encrypted payload — server never sees plaintext
            recipient = data['to']
            if recipient in PEERS:
                await self.channel_layer.send(PEERS[recipient]['channel'], {
                    'type': 'forward_message',
                    'from': self.username,
                    'ciphertext': data['ciphertext'],   # base64 AES-GCM ciphertext
                    'iv': data['iv'],                   # base64 IV (12 bytes)
                })

        # ── WebRTC signaling ─────────────────────────────────────────────────
        # The server is a blind relay for all signaling messages.
        # It never inspects SDP or ICE candidates — just forwards them.

        elif data['type'] == 'call_offer':
            recipient = data['to']
            if recipient in PEERS:
                await self.channel_layer.send(PEERS[recipient]['channel'], {
                    'type': 'forward_signal',
                    'signal_type': 'call_offer',
                    'from': self.username,
                    'sdp': data['sdp'],
                })

        elif data['type'] == 'call_answer':
            recipient = data['to']
            if recipient in PEERS:
                await self.channel_layer.send(PEERS[recipient]['channel'], {
                    'type': 'forward_signal',
                    'signal_type': 'call_answer',
                    'from': self.username,
                    'sdp': data['sdp'],
                })

        elif data['type'] == 'ice_candidate':
            recipient = data['to']
            if recipient in PEERS:
                await self.channel_layer.send(PEERS[recipient]['channel'], {
                    'type': 'forward_signal',
                    'signal_type': 'ice_candidate',
                    'from': self.username,
                    'candidate': data['candidate'],
                })

        elif data['type'] in ('call_reject', 'call_end'):
            recipient = data['to']
            if recipient in PEERS:
                await self.channel_layer.send(PEERS[recipient]['channel'], {
                    'type': 'forward_signal',
                    'signal_type': data['type'],
                    'from': self.username,
                })

    async def forward_message(self, event):
        # Deliver encrypted payload as-is to the recipient's WebSocket
        await self.send(json.dumps({
            'type': 'message',
            'from': event['from'],
            'ciphertext': event['ciphertext'],
            'iv': event['iv'],
        }))

    async def forward_signal(self, event):
        # Deliver WebRTC signaling message to the target peer's WebSocket
        payload = {
            'type': event['signal_type'],
            'from': event['from'],
        }
        if 'sdp' in event:
            payload['sdp'] = event['sdp']
        if 'candidate' in event:
            payload['candidate'] = event['candidate']
        await self.send(json.dumps(payload))

    async def peer_update(self, event):
        await self.send(json.dumps({
            'type': 'peer_list',
            'peers': event['peers'],   # [{username, public_key}, ...]
        }))
