#!/usr/bin/env bash
# Runs every example once against production and prints OK or KO per example.
#
#   export ADONA_API_KEY=...      # a live key; it is never printed
#   ./check/run.sh                # from the repository root
#
# Needs bash and curl. Python 3.9+ with `requests` and `websockets` and Node 22+ are used when
# present; otherwise, if Docker is available, those examples run in a throwaway
# container (python:3.12-slim, node:22-alpine) that is removed afterwards.
#
# Cost on the account: about a dozen slices of 1000 bars (each stream's snapshot
# is metered too), a handful of tokens and two stream connections of 20 seconds.
# Weekends are fine: every check reads bars that exist while the market is closed. Every example's output goes to a
# temporary directory, filtered so the key can never appear, and only the verdict
# is printed. KEEP=1 keeps that directory and prints its path.
set -uo pipefail

: "${ADONA_API_KEY:?set ADONA_API_KEY to a live API key}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap '[ "${KEEP:-0}" = 1 ] && echo "outputs kept in $WORK" || rm -rf "$WORK"' EXIT
cp -r "$ROOT/curl" "$ROOT/python" "$ROOT/javascript" "$ROOT/guides" "$WORK/"
cd "$WORK" || exit 1

STREAM_SECONDS=20
FAILED=0

# Never let the key reach a file or the screen, whatever an example prints. Read
# from the environment, not passed as an argument: `ps` shows arguments.
redact() {
  awk 'BEGIN { k = ENVIRON["ADONA_API_KEY"] }
       { while (k != "" && (i = index($0, k)) > 0) $0 = substr($0, 1, i - 1) "<redacted>" substr($0, i + length(k)); print }'
}

# --- the runners: local when possible, a throwaway container otherwise -------------
if command -v python3 >/dev/null && python3 -c 'import sys, requests, websockets; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  PY=(python3)
  export PYTHONUNBUFFERED=1  # a stream stopped by `timeout` must have printed what it got
elif command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  PY=(docker run --rm -i --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONUNBUFFERED=1 -e T -e ADONA_API_KEY
      -v "$WORK:/w" -w /w python:3.12-slim
      sh -c 'pip install -q --user -r python/requirements.txt >/dev/null && exec ${T:+timeout $T} python "$@"' python)
else
  PY=()
fi
if command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]; then
  NODE=(node)
elif command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  NODE=(docker run --rm -i --user "$(id -u):$(id -g)" -e ADONA_API_KEY -e STOP_AFTER -v "$WORK:/w" -w /w node:22-alpine node)
else
  NODE=()
fi

# check NAME PATTERN COMMAND...: OK when the command exits 0 and its output matches.
check() {
  local name="$1" pattern="$2"
  shift 2
  local out="$WORK/${name//\//_}.out"
  if [ "$1" = "--skip" ]; then
    printf 'KO    %-34s %s\n' "$name" "$2"
    FAILED=1
    return
  fi
  "$@" 2>&1 | redact >"$out"
  local status=${PIPESTATUS[0]}
  if [ "$status" -eq 0 ] && grep -qE "$pattern" "$out"; then
    printf 'OK    %s\n' "$name"
  else
    printf 'KO    %-34s exit %s: %s\n' "$name" "$status" "$(tail -c 300 "$out" | tr '\n' ' ')"
    FAILED=1
  fi
}

# refused NAME COMMAND...: OK when a wrong key is refused with INVALID_CUSTOMER_KEY.
refused() {
  local name="$1"
  shift
  local out="$WORK/refused_${name//\//_}.out"
  ADONA_API_KEY="not-a-key" "$@" >"$out" 2>&1
  if grep -q "INVALID_CUSTOMER_KEY" "$out"; then
    printf 'OK    %s refuses a wrong key\n' "$name"
  else
    printf 'KO    %-34s a wrong key was not refused as INVALID_CUSTOMER_KEY\n' "$name"
    FAILED=1
  fi
}

mcp_candles() {
  curl -s https://api.adona-robot.com/mcp \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -H @<(printf 'Authorization: Bearer %s\n' "$ADONA_API_KEY") \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_candles","arguments":{"symbol":"EURUSD","timeframe":"M1","limit":5}}}'
}

skip_py=(--skip "no Python 3.9+ with requests and websockets, and no usable Docker")
skip_node=(--skip "no Node 22+, and no usable Docker")
# py runs Python; with T=N in its environment, for N seconds at most (the quickstart's
# stream.py runs until stopped, so `timeout`'s 124 is its success).
py() {
  [ ${#PY[@]} -gt 0 ] || return 127
  if [ "${PY[0]}" = docker ] || [ -z "${T:-}" ]; then "${PY[@]}" "$@"; else timeout "$T" "${PY[@]}" "$@"; fi
}
stopped_ok() { "$@"; local s=$?; [ "$s" -eq 124 ] && return 0; return "$s"; }
py_stream() { T="$STREAM_SECONDS" stopped_ok py python/stream.py; }
# A Node script that runs until stopped: `timeout` around it, 124 is success.
node_stream() {
  [ ${#NODE[@]} -gt 0 ] || return 127
  if [ "${NODE[0]}" = docker ]; then
    stopped_ok "${NODE[@]:0:${#NODE[@]}-1}" timeout "$STREAM_SECONDS" node "$@"
  else
    stopped_ok timeout "$STREAM_SECONDS" "${NODE[@]}" "$@"
  fi
}
nd() { if [ ${#NODE[@]} -gt 0 ]; then "${NODE[@]}" "$@"; else return 127; fi; }

echo "adona-robot examples, against production, $(date -u +%Y-%m-%dT%H:%MZ)"

# Keyless.
check "curl/mcp.sh" '"total_chf_per_month_excluding_vat"' bash curl/mcp.sh

# With the key.
# M1, not S1: an S1 page covers one day, so it is empty a day after the weekend's close.
check "curl/history.sh" '"candles":\[\{"time"' bash curl/history.sh EURUSD M1 1000
check "curl/stream-ticket.sh" '"ticket":"' bash curl/stream-ticket.sh
check "mcp get_candles" '"isError":false' mcp_candles
if [ ${#PY[@]} -gt 0 ]; then
  check "python/history.py" '^[1-9][0-9]* bars, newest:' py python/history.py
  check "python/stream.py" "candle\.snapshot.*'channel': 'candle:EURUSD:M1'.*'candles': \[\{" py_stream
else
  check "python/history.py" '' "${skip_py[@]}"
  check "python/stream.py" '' "${skip_py[@]}"
fi
if [ ${#NODE[@]} -gt 0 ]; then
  check "javascript/history.mjs" '^[1-9][0-9]* bars, newest:' nd javascript/history.mjs
  check "javascript/stream.mjs" 'candle.snapshot candle:EURUSD:M1 [1-9]' env STOP_AFTER="$STREAM_SECONDS" "${NODE[@]}" javascript/stream.mjs
else
  check "javascript/history.mjs" '' "${skip_node[@]}"
  check "javascript/stream.mjs" '' "${skip_node[@]}"
fi

# The guides' code (adona-robot.com/en/use/...), the same files the site serves.
check "guides/mcp.sh" '"total_chf_per_month_excluding_vat"' bash guides/mcp.sh
if [ ${#PY[@]} -gt 0 ]; then
  check "guides/history_m1.py" '^[1-9][0-9]* bars from 20' py guides/history_m1.py EURUSD 3
else
  check "guides/history_m1.py" '' "${skip_py[@]}"
fi
if [ ${#NODE[@]} -gt 0 ]; then
  check "guides/stream.mjs" 'candle.snapshot candle:EURUSD:M1 [1-9]' node_stream guides/stream.mjs
else
  check "guides/stream.mjs" '' "${skip_node[@]}"
fi

# A wrong key is an answer, not a crash.
refused "curl/history.sh" bash curl/history.sh
[ ${#PY[@]} -gt 0 ] && refused "python/history.py" py python/history.py
[ ${#PY[@]} -gt 0 ] && T=10 refused "python/stream.py" py python/stream.py
[ ${#NODE[@]} -gt 0 ] && refused "javascript/history.mjs" nd javascript/history.mjs
[ ${#PY[@]} -gt 0 ] && refused "guides/history_m1.py" py guides/history_m1.py

if [ "$FAILED" -eq 0 ]; then echo "ALL OK"; else echo "SOME KO"; fi
exit "$FAILED"
