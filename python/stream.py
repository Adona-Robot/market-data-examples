"""The live stream in Python: a token, a ticket, then quotes and closed bars.

Python 3.9+, `requests` and `websockets` (pip install requests websockets):

    export ADONA_API_KEY=...   # from your account page on adona-robot.com
    python stream.py quote:EURUSD candle:EURUSD:M1

Channels are `quote:<SYMBOL>` and `candle:<SYMBOL>:<TIMEFRAME>`, up to 64. The
ticket is offered as a second subprotocol, never in the URL. On subscribe the
server sends each candle channel's recent bars, then every bar as it closes; a
quote channel sends the current price, then every change. Stop with Ctrl-C, or
pass --seconds N to stop after N seconds.
"""

import asyncio
import json
import os
import sys

import requests
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

API = "https://api.adona-robot.com"
STREAM = "wss://api.adona-robot.com/v1/stream"


def post(path, *, bearer, body=None):
    response = requests.post(API + path, headers={"Authorization": f"Bearer {bearer}"}, json=body, timeout=30)
    if not response.ok:
        # The part of `detail` before the first colon is the code to branch on.
        sys.exit(f"refused: {response.status_code} {response.text}")
    return response.json()


async def stream(channels, seconds=None):
    # On your server: the key for a twelve-hour token per end user ("u-42" here).
    token = post("/v1/tokens", bearer=os.environ["ADONA_API_KEY"], body={"end_user_id": "u-42"})["access_token"]
    # Anywhere the token is (a browser too): a single-use ticket.
    ticket = post("/v1/ws-ticket", bearer=token)["ticket"]

    try:
        ws = await connect(STREAM, subprotocols=["adona.data.v1", f"ticket.{ticket}"])
    except InvalidStatus as refused:  # the upgrade itself was refused
        sys.exit(f"refused: {refused.response.status_code}")
    async with ws:
        await ws.send(json.dumps({"type": "subscribe", "request_id": "sub", "payload": {"channels": channels}}))
        loop = asyncio.get_running_loop()
        deadline = loop.time() + seconds if seconds else None
        try:
            while deadline is None or loop.time() < deadline:
                timeout = None if deadline is None else max(0.0, deadline - loop.time())
                try:
                    frame = json.loads(await asyncio.wait_for(ws.recv(), timeout))
                except asyncio.TimeoutError:
                    break
                kind, payload = frame["type"], frame.get("payload", {})
                if kind == "subscribed" and payload.get("rejected"):
                    print("not in your account's list:", payload["rejected"])
                elif kind in ("quote.snapshot", "quote.update"):
                    print(kind, payload["symbol"], "bid", payload["bid"], "ask", payload["ask"], payload["as_of"])
                elif kind == "candle.snapshot":
                    bars = payload["candles"]
                    print(kind, payload["channel"], len(bars), "bars, last", bars[-1]["time"] if bars else None)
                elif kind == "candle.bar":
                    # Live bars use short keys: ts, o, h, l, c, v.
                    print(kind, f"{payload['symbol']} {payload['tf']}", payload["ts"], "close", payload["c"])
                elif kind == "error":
                    print("error", payload.get("code"))
        except ConnectionClosed as closed:
            # 1008 with a reason is an answer (revoked, trial ended): do not loop on it.
            sys.exit(f"closed: {closed.rcvd.code if closed.rcvd else ''} {closed.rcvd.reason if closed.rcvd else ''}")


def main():
    args = sys.argv[1:]
    seconds = None
    if "--seconds" in args:
        i = args.index("--seconds")
        seconds = float(args[i + 1])
        del args[i : i + 2]
    asyncio.run(stream(args or ["quote:EURUSD", "candle:EURUSD:M1"], seconds))


if __name__ == "__main__":
    main()
