# pip install requests "websockets>=13"
import asyncio
import json
import os

import requests
from websockets.asyncio.client import connect

API = "https://api.adona-robot.com"
STREAM = "wss://api.adona-robot.com/v1/stream"


def post(path, bearer, body=None):
    r = requests.post(API + path, headers={"Authorization": f"Bearer {bearer}"}, json=body, timeout=30)
    if not r.ok:
        raise SystemExit(f"refused: {r.status_code} {r.text}")
    return r.json()


async def main():
    token = post("/v1/tokens", os.environ["ADONA_API_KEY"], {"end_user_id": "u-42"})["access_token"]
    # a ticket for the stream, from the token
    ticket = post("/v1/ws-ticket", token)["ticket"]
    # the stream: live quotes and one-minute bars
    async with connect(STREAM, subprotocols=["adona.data.v1", f"ticket.{ticket}"]) as ws:
        await ws.send(json.dumps({
            "type": "subscribe", "request_id": "sub",
            "payload": {"channels": ["quote:EURUSD", "candle:EURUSD:M1"]},
        }))
        async for message in ws:
            print(json.loads(message))


asyncio.run(main())
