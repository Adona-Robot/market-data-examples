# pip install requests
# One-minute history, paged back with the cursor: ADONA_API_KEY=... python history_m1.py EURUSD 3
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

API = "https://api.adona-robot.com"
symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
days = int(sys.argv[2]) if len(sys.argv) > 2 else 3


def get(path, bearer, **kwargs):
    r = requests.request(kwargs.pop("method", "GET"), API + path, headers={"Authorization": f"Bearer {bearer}"}, timeout=30, **kwargs)
    if not r.ok:
        raise SystemExit(f"refused: {r.status_code} {r.text}")
    return r.json()


# your server exchanges the key for a token
token = get("/v1/tokens", os.environ["ADONA_API_KEY"], method="POST", json={"end_user_id": "u-42"})["access_token"]

# pages of up to 5000 bars, newest first; next_before is the page before
since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
bars, before = [], None
while True:
    params = {"symbol": symbol, "timeframe": "M1", "limit": 5000}
    if before:
        params["before"] = before
    page = get("/v1/candles", token, params=params)
    bars = page["candles"] + bars
    before = page["next_before"]
    if before is None or before <= since:  # nothing older, or far enough back
        break

bars = [b for b in bars if b["time"] >= since]
print(len(bars), "bars from", bars[0]["time"] if bars else None, "to", bars[-1]["time"] if bars else None)
