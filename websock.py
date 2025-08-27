import asyncio
import websockets
import json
from collections import defaultdict
import os  # to access env vars

channels = defaultdict(set)
joined = defaultdict(list)
user_channels = {}
usernames = {}

async def handler(websocket):
    user_channel = None
    username = None

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "join":
                user_channel = data["channel"]
                username = data["name"]
                channels[user_channel].add(websocket)
                user_channels[websocket] = user_channel
                usernames[websocket] = username

                if username not in joined[user_channel]:
                    joined[user_channel].append(username)

                join_message = json.dumps({
                    "type": "joined",
                    "user": joined[user_channel]
                })

                for conn in list(channels[user_channel]):
                    try:
                        await conn.send(join_message)
                    except websockets.exceptions.ConnectionClosed:
                        channels[user_channel].remove(conn)

                print(f"{username} joined channel: {user_channel}")

            elif data["type"] == "leave":
                if username in joined[user_channel]:
                    joined[user_channel].remove(username)

                leave_message = json.dumps({
                    "type": "left",
                    "user": joined[user_channel]
                })

                for conn in list(channels[user_channel]):
                    try:
                        await conn.send(leave_message)
                    except websockets.exceptions.ConnectionClosed:
                        channels[user_channel].remove(conn)

                print(f"{username} left channel: {user_channel}")

            elif data['type'] in ['offer', 'answer', 'candidate']:
                channel = user_channels.get(websocket)
                sender = usernames.get(websocket)
                data["name"] = sender

                for ws in list(channels[channel]):
                    if ws != websocket:
                        try:
                            await ws.send(json.dumps(data))
                        except websockets.exceptions.ConnectionClosed:
                            channels[channel].remove(ws)

    except Exception as e:
        print(f"[-] Client disconnected. Error: {e}")
        if user_channel and username in joined[user_channel]:
            joined[user_channel].remove(username)

    finally:
        if user_channel:
            channels[user_channel].discard(websocket)

            if username in joined[user_channel]:
                joined[user_channel].remove(username)

                leave_message = json.dumps({
                    "type": "left",
                    "user": joined[user_channel]
                })

                for conn in list(channels[user_channel]):
                    try:
                        await conn.send(leave_message)
                    except websockets.exceptions.ConnectionClosed:
                        channels[user_channel].remove(conn)

            if not channels[user_channel]:
                del channels[user_channel]
                del joined[user_channel]

async def main():
    port = int(os.environ.get("PORT", 8765))  # Use Railway's port or default locally
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"✅ WebSocket Server running at ws://0.0.0.0:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
