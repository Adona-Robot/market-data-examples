"""Candle history in Python: your API key for a token, then pages of candles.

Python 3.9+ and `requests` (pip install requests websockets):

    export ADONA_API_KEY=...   # from your account page on adona-robot.com
    python history.py EURUSD M1 2000

The key stays on your server: it is exchanged at POST /v1/tokens for a
twelve-hour token per end user, and every other call carries that token. Prices
are strings, exactly as served: convert them at the last moment.
"""

import os
import sys

import requests

API = "https://api.adona-robot.com"


class Refused(Exception):
    def __init__(self, status, detail):
        super().__init__(f"{status} {detail}")
        self.status = status
        self.code = str(detail).split(":", 1)[0].strip()  # branch on this


def call(method, path, *, bearer, **kwargs):
    response = requests.request(method, API + path, headers={"Authorization": f"Bearer {bearer}"}, timeout=30, **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", "")
        except ValueError:
            detail = ""  # not ours: a proxy's page during a deploy
        raise Refused(response.status_code, detail)
    return response.json()


def history(token, symbol, timeframe, bars):
    """The latest `bars` bars, oldest first, paging back with the cursor."""
    out, before = [], None
    while len(out) < bars:
        params = {"symbol": symbol, "timeframe": timeframe, "limit": min(5000, bars - len(out))}
        if before:
            params["before"] = before
        page = call("GET", "/v1/candles", bearer=token, params=params)
        out = page["candles"] + out  # each page is older than the last
        before = page["next_before"]
        if not before:
            break  # nothing older for this account
    return out[-bars:]


def main():
    args = sys.argv[1:] + ["EURUSD", "M1", "2000"][len(sys.argv[1:]) :]
    symbol, timeframe, bars = args[:3]
    try:
        token = call("POST", "/v1/tokens", bearer=os.environ["ADONA_API_KEY"], json={"end_user_id": "u-42"})["access_token"]
        candles = history(token, symbol, timeframe, int(bars))
    except Refused as refused:
        sys.exit(f"refused: {refused}")
    if candles:
        print(f"{len(candles)} bars, {candles[0]['time']} to {candles[-1]['time']}")
        print("last:", candles[-1])
    else:
        print("0 bars")


if __name__ == "__main__":
    main()
