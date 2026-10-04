# Adona Robot market data: examples and MCP server

Runnable examples for the [Adona Robot](https://adona-robot.com/en) market-data API, and the
configuration to connect an AI agent to its MCP server.

Adona Robot sells **one-second OHLC candles and a live bid/ask quote stream for 46 FX pairs and
5 spot metals**, over REST and WebSocket. It is priced by capacity: the month's peak of
simultaneous connections and slices of 1000 bars, not per seat. **Redistribution is allowed on
every plan**: show the data in your product, relay it to your own clients, keep what you receive.
A symbol you follow live for more than 80% of its open hours in a month adds CHF 150 to that
month's invoice, on top of the plan.

*Facts as of 2026-10-03. The current ones are always on [adona-robot.com](https://adona-robot.com/en)
and, machine-readable, in [spec.json](https://adona-robot.com/spec.json) and
[symbols.json](https://adona-robot.com/symbols.json).*

| Plan | CHF a month, before VAT | Sized for (simultaneous connections) | Slices of 1000 bars a month |
|---|---|---|---|
| Trial, 7 days, free | 0 | 3 | 2 500 a day |
| Starter | 500 | 30 | 750 000 |
| Growth | 1 200 | 100 | 2 500 000 |
| Scale | 2 400 | 300 | 7 500 000 |
| Enterprise | 5 000 | 1 000 | 25 000 000 |

The trial carries EURUSD and XAUUSD with 7 days of history; every paid plan carries all 51
symbols. A paid plan never refuses a connection: the month's reading sets the next invoice's
plan. Above Enterprise: sales@adona-robot.com.

## 1. Get a key

1. [Open an account](https://adona-robot.com/en/signup) with your company email address (one
   trial per company).
2. Confirm the address, sign in, and create the key on your account page. It is shown once:
   keep it on your server, never in a web page or a repository.
3. Export it for the examples:

   ```sh
   export ADONA_API_KEY=YOUR_API_KEY
   ```

The [quickstart](https://adona-robot.com/en/quickstart) walks through the same steps on the site.

## 2. How a call works

- Your **API key** stays on your server. It is exchanged at `POST /v1/tokens` for a
  **twelve-hour token** per end user of yours (`end_user_id`).
- **History**: `GET /v1/candles?symbol=EURUSD&timeframe=S1`, timeframes `S1`, `M1`, `M5`, `M15`,
  `H1`, `H4`, `D1`, up to 5000 bars a page, oldest first, prices as strings. `next_before` is the
  cursor to the page before (null when there is nothing older). On `S1` a page covers one day,
  so an empty page with a cursor is an empty day (a weekend): continue with the cursor.
- **Live**: `POST /v1/ws-ticket` with the token gives a single-use ticket. Open
  `wss://api.adona-robot.com/v1/stream` offering two subprotocols, `adona.data.v1` and
  `ticket.<ticket>` (never in the URL), then send a `subscribe` frame with channels such as
  `quote:EURUSD` and `candle:EURUSD:M1`.
- A refusal answers `{"detail": "CODE"}`: branch on the code. Every code and what to do about
  it is in the [API reference](https://adona-robot.com/en/reference), and the contract is
  machine-readable at [openapi.json](https://api.adona-robot.com/v1/openapi.json).

## 3. Examples

The Python and JavaScript history examples and the Python stream are the code of the
[quickstart](https://adona-robot.com/en/quickstart)'s tabs, unchanged.

| | History | Live stream |
|---|---|---|
| curl | [`curl/history.sh`](curl/history.sh) | [`curl/stream-ticket.sh`](curl/stream-ticket.sh) (the ticket; a WebSocket client opens the stream) |
| Python 3.9+ | [`python/history.py`](python/history.py) | [`python/stream.py`](python/stream.py) |
| JavaScript | [`javascript/history.mjs`](javascript/history.mjs), Node 18+ | [`javascript/stream.mjs`](javascript/stream.mjs), Node 22+ (global `WebSocket`); the same frames as the quickstart's browser snippet |

The Python examples need two packages, once: `pip install requests websockets`.

```sh
./curl/history.sh                   # the latest 1000 EURUSD one-minute bars
python python/history.py            # the latest 1000 EURUSD one-minute bars
python python/stream.py             # quotes and one-minute bars, until Ctrl-C
node javascript/history.mjs
node javascript/stream.mjs quote:XAUUSD candle:XAUUSD:M1
```

Each one prints `refused:` with the status and the API's answer, and stops, when the API says
no (a wrong key answers `INVALID_CUSTOMER_KEY`). For a browser, keep the key on your server and hand the page a token:
the site publishes a [token server](https://adona-robot.com/examples/token-server.ts) and a
[browser client](https://adona-robot.com/examples/browser.ts) with reconnection, and
[history.py](https://adona-robot.com/examples/history.py) keeps a local store of the bars it
has fetched, so closed history is paid for once.

The [`guides/`](guides) folder holds the code of the guides on the site, the same files:
[one-minute history, paged back](https://adona-robot.com/en/use/forex-1-minute-history-api)
(`guides/history_m1.py`), [the live stream](https://adona-robot.com/en/use/forex-websocket-price-stream)
(`guides/stream.mjs`) and [the MCP server for an agent](https://adona-robot.com/en/use/market-data-mcp-server-ai-agent)
(`guides/mcp.sh`). The [Python guide](https://adona-robot.com/en/use/forex-data-api-python) shows
`python/history.py` and `python/stream.py`.

[`check/run.sh`](check/run.sh) runs every example once against production and prints OK or KO
for each.

## 4. Symbols

46 FX pairs and 5 metals (XAUUSD, XAGUSD, XAUEUR, XPTUSD, XPDUSD). The list, with each symbol's
history dates, is on [adona-robot.com/en/symbols](https://adona-robot.com/en/symbols) and in
[symbols.json](https://adona-robot.com/symbols.json); every symbol has its own page, for example
[EURUSD](https://adona-robot.com/en/symbols/eurusd).

## 5. Connect an AI agent (MCP)

The MCP server is at `https://api.adona-robot.com/mcp` (streamable HTTP, stateless). Four tools:

| Tool | What it answers | Key |
|---|---|---|
| `get_offer` | The plans, prices, limits, trial, continuous feed and links | No |
| `list_symbols` | Every symbol a paid plan carries, with its name and class | No |
| `quote_price_for` | The plan and the CHF total, before VAT, for a month of usage | No |
| `get_candles` | Candle history for one symbol, one page, oldest first | Yes, billed like `GET /v1/candles` |

The key, when you want `get_candles`, travels on every call in the `Authorization: Bearer`
header, or in an `X-API-Key` header for a client or gateway that keeps `Authorization` for
itself (`X-API-Key: YOUR_API_KEY`, no `Bearer`). Send one key: two different keys in the two
headers, or two different `X-API-Key` values, are refused as `CONFLICTING_API_KEYS`. Keep the
key in an environment variable, not in a file you commit.

**Claude Code**: put [`mcp/claude-code.mcp.json`](mcp/claude-code.mcp.json) in your project as
`.mcp.json` (it reads `ADONA_API_KEY` from your environment; unset, the keyless tools still
work), or add it from the command line:

```sh
claude mcp add --transport http adona-robot https://api.adona-robot.com/mcp \
  --header "Authorization: Bearer $ADONA_API_KEY"
```

**Cursor**: put [`mcp/cursor.mcp.json`](mcp/cursor.mcp.json) in `.cursor/mcp.json` (project) or
`~/.cursor/mcp.json` (global); it reads `${env:ADONA_API_KEY}`.

**Claude Desktop and claude.ai**: Customize, then Connectors, then Add custom connector, with
the URL `https://api.adona-robot.com/mcp` and the authentication "No sign-in" (on Team and
Enterprise, an owner adds it under Organization settings, then Connectors). The three keyless
tools work as is. For `get_candles`, add the request header `Authorization` with the value
`Bearer YOUR_API_KEY`, or `X-API-Key` with the value `YOUR_API_KEY`, where your account offers
request headers (a beta, not yet open to every account).

Then ask, for example: "What would 40 simultaneous users cost on Adona Robot?"

Without a client, the server answers plain JSON-RPC: see [`curl/mcp.sh`](curl/mcp.sh).

## Support

support@adona-robot.com, by email on business days. Security reports:
[adona-robot.com/en/security](https://adona-robot.com/en/security).

The code in this repository is under the [MIT License](LICENSE). The data you read with it is
governed by the [terms of service](https://adona-robot.com/en/terms).
