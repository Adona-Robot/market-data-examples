#!/usr/bin/env bash
# The live stream starts with a ticket: one POST with your token, valid once.
#
#   export ADONA_API_KEY=...
#   ./stream-ticket.sh
#
# curl gets the ticket; a WebSocket client then opens
# wss://api.adona-robot.com/v1/stream offering TWO subprotocols, "adona.data.v1"
# and "ticket.<ticket>". The ticket never goes in the URL. See ../python/stream.py
# and ../javascript/stream.mjs for the connection itself.
set -euo pipefail

API="https://api.adona-robot.com"
: "${ADONA_API_KEY:?set ADONA_API_KEY to your API key}"

ANSWER=$(curl -s "$API/v1/tokens" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ADONA_API_KEY" \
  -d '{"end_user_id":"u-42"}')
case "$ANSWER" in
  *'"access_token":"'*) TOKEN=$(printf '%s' "$ANSWER" | sed -E 's/.*"access_token":"([^"]+)".*/\1/') ;;
  *) echo "refused: $ANSWER" >&2; exit 1 ;;  # e.g. {"detail":"INVALID_CUSTOMER_KEY"}
esac

curl -s --fail-with-body -X POST "$API/v1/ws-ticket" -H "Authorization: Bearer $TOKEN"
echo
