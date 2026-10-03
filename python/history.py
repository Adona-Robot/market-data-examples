"""Pull candle history from adona-robot into CSV, and keep it up to date.

Python 3.9+, standard library only. Run it on your server or in a notebook:

    export ADONA_API_KEY=...   # from your account page on adona-robot.com
    python history.py EURUSD M1 2026-09-01

It pages backwards from now to the date you give and writes the bars oldest
first. What it has fetched is kept in a local store, so the next run asks for
about as many bars as can have arrived since, plus any older range the store
does not hold: closed history is paid for once.
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://api.adona-robot.com"
STORE = Path(".adona-store")
PAGE = 5000  # the most bars one page returns
SECONDS = {"S1": 1, "M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400, "D1": 86400}


class Refused(Exception):
    """A refusal to stop on. `code` is the part of `detail` before the first colon."""

    def __init__(self, status, code, detail):
        super().__init__(f"{status} {detail}")
        self.status, self.code = status, code


def call(method, path, *, token, body=None, attempts=6):
    """One call, retried when waiting helps and only then."""
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(attempts):
        request = urllib.request.Request(API + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {token}")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        wait = 2**attempt  # 1, 2, 4... seconds
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            try:
                detail = str(json.loads(error.read()).get("detail", ""))
            except ValueError:
                detail = ""  # not ours: a proxy's page during a deploy
            code = detail.split(":", 1)[0].strip()
            # 429 clears by waiting, except the daily guard, which reopens the next
            # UTC day. 5xx is temporary. Everything else is an answer: stop.
            retryable = (error.code == 429 and code != "CUSTOMER_DAILY_CAP") or error.code >= 500
            if not retryable or attempt == attempts - 1:
                raise Refused(error.code, code, detail or str(error.code)) from None
            header = error.headers.get("Retry-After", "")
            wait = int(header) if header.isdigit() and int(header) > 0 else wait
        except OSError as error:  # the network: refused, reset, timed out (after HTTPError, a subclass)
            if attempt == attempts - 1:
                raise Refused(0, "NETWORK", str(error)) from None
        time.sleep(wait)
    raise AssertionError("unreachable")


def access_token(api_key, end_user_id="history-script"):
    """The key stays here; every other call carries the twelve-hour token."""
    return call("POST", "/v1/tokens", token=api_key, body={"end_user_id": end_user_id})["access_token"]


def page(token, symbol, timeframe, before, limit):
    """Up to `limit` bars older than `before` (newest if None), oldest first, and the next cursor."""
    params = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
    if before:
        params["before"] = before
    result = call("GET", "/v1/candles?" + urllib.parse.urlencode(params), token=token)
    return result["candles"], result["next_before"]


def walk(token, symbol, timeframe, before, stop_at, first=None):
    """Pages back from `before` until a bar at or before `stop_at`, oldest first.

    It also stops at a null cursor: nothing older for this account (the end of the
    archive, or of your plan's history). On S1 a page is one day, so an empty page
    with a cursor is an empty day: keep going.
    """
    bars, limit = [], first or PAGE
    while True:
        candles, before = page(token, symbol, timeframe, before, limit)
        bars = candles + bars  # each page is older than the last
        if before is None or before <= stop_at:
            return bars
        limit = PAGE


def history(token, symbol, timeframe, since):
    """Every bar from `since` (YYYY-MM-DD, or an RFC3339 instant) to now, oldest first."""
    if len(since) == 10:
        since += "T00:00:00Z"  # compared as text with the bars' RFC3339 times
    STORE.mkdir(exist_ok=True)
    path = STORE / f"{symbol}-{timeframe}.json"
    known = json.loads(path.read_text()) if path.exists() else {}

    # The newest bars, back until they meet what the store already holds. Every bar
    # served is paid for, so the first page asks for roughly what can have arrived.
    first = PAGE
    if known:
        elapsed = time.time() - datetime.fromisoformat(max(known).replace("Z", "+00:00")).timestamp()
        first = max(2, min(PAGE, int(elapsed // SECONDS[timeframe]) + 2))
    fresh = walk(token, symbol, timeframe, None, max(known, default=since), first)
    # The newest bar can still be forming: served, never stored as final.
    forming = fresh.pop() if fresh else None

    # Older than the store, if it does not reach back to `since`. Asked again on
    # every such run: a plan with a deeper history (after a trial) answers with
    # more, and an answer with nothing older is an empty page, which costs no slices.
    if known and since < min(known):
        fresh += walk(token, symbol, timeframe, min(known), since)
    for bar in fresh:
        known[bar["time"]] = bar
    path.write_text(json.dumps(known))

    bars = [known[t] for t in sorted(known) if t >= since]
    if forming and forming["time"] >= since:
        bars = [bar for bar in bars if bar["time"] < forming["time"]] + [forming]
    return bars


def main():
    symbol, timeframe, since = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        token = access_token(os.environ["ADONA_API_KEY"])
        bars = history(token, symbol, timeframe, since)
    except Refused as refused:
        sys.exit(f"refused: {refused}")
    out = f"{symbol}-{timeframe}.csv"
    with open(out, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["time", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(bars)  # prices stay strings, exactly as served
    print(f"{len(bars)} bars written to {out}")


if __name__ == "__main__":
    main()
