#!/usr/bin/env bash
# The MCP server answers plain JSON-RPC over HTTP: no key for the offer, the
# symbols and a price quote.
#
#   ./mcp.sh
set -euo pipefail

MCP="https://api.adona-robot.com/mcp"
call() {
  curl -s --fail-with-body "$MCP" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d "$1"
  echo
}

# The tools it offers.
call '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# What 40 simultaneous connections and 100 000 slices a month would cost.
call '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"quote_price_for","arguments":{"simultaneous_connections":40,"slices_per_month":100000}}}'
