# pip install requests
import os

import requests

API = "https://api.adona-robot.com"

# your server exchanges the key for a token
r = requests.post(
    f"{API}/v1/tokens",
    headers={"Authorization": f"Bearer {os.environ['ADONA_API_KEY']}"},
    json={"end_user_id": "u-42"},
    timeout=30,
)
if not r.ok:
    raise SystemExit(f"refused: {r.status_code} {r.text}")
token = r.json()["access_token"]

# the token reads candles
r = requests.get(
    f"{API}/v1/candles",
    headers={"Authorization": f"Bearer {token}"},
    params={"symbol": "EURUSD", "timeframe": "M1", "limit": 1000},
    timeout=30,
)
if not r.ok:
    raise SystemExit(f"refused: {r.status_code} {r.text}")
page = r.json()
print(len(page["candles"]), "bars, newest:", page["candles"][-1] if page["candles"] else None)
