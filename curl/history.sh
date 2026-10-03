#!/usr/bin/env bash
# Candle history with curl: your API key for a token, then one page of candles.
#
#   export ADONA_API_KEY=...   # from your account page on adona-robot.com
#   ./history.sh EURUSD S1 1000
#
# The key stays on your server: it is exchanged at POST /v1/tokens for a
# twelve-hour token, and every other call carries that token. Prices are strings,
# exactly as served. A page holds up to 5000 bars, oldest first; `next_before`
# is the cursor to the page before it (null when there is nothing older). On S1 a
# page covers one day, so it is empty on a weekend: use M1 there, or the cursor.
# (The key is passed as an argument here for clarity; on a shared machine, other
# users can see a process's arguments.)
set -euo pipefail

API="https://api.adona-robot.com"
SYMBOL="${1:-EURUSD}"
TIMEFRAME="${2:-S1}"   # S1, M1, M5, M15, H1, H4 or D1
LIMIT="${3:-1000}"     # 1 to 5000; billed in slices of 1000 bars, rounded up
: "${ADONA_API_KEY:?set ADONA_API_KEY to your API key}"

# 1. The key for a token (one per end user of yours; "u-42" here).
ANSWER=$(curl -s "$API/v1/tokens" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ADONA_API_KEY" \
  -d '{"end_user_id":"u-42"}')
case "$ANSWER" in
  *'"access_token":"'*) TOKEN=$(printf '%s' "$ANSWER" | sed -E 's/.*"access_token":"([^"]+)".*/\1/') ;;
  *) echo "refused: $ANSWER" >&2; exit 1 ;;  # e.g. {"detail":"INVALID_CUSTOMER_KEY"}
esac

# 2. The latest bars.
curl -s --fail-with-body "$API/v1/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=$LIMIT" \
  -H "Authorization: Bearer $TOKEN"
echo
