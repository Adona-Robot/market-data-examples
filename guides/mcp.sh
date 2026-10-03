# The MCP server answers plain JSON-RPC over HTTP; the offer, the symbols and the price of a month need no key.
MCP=https://api.adona-robot.com/mcp

curl -s $MCP -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# what 40 simultaneous connections and 100 000 slices a month would cost
curl -s $MCP -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"quote_price_for","arguments":{"simultaneous_connections":40,"slices_per_month":100000}}}'
