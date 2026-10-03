// The live stream in JavaScript: a token, a ticket, then quotes and closed bars.
//
// Node 22+ (global WebSocket), no dependency. The same code runs in a browser,
// where the token comes from your own server instead of the key:
//
//   export ADONA_API_KEY=...   # from your account page on adona-robot.com
//   node stream.mjs quote:EURUSD candle:EURUSD:M1
//
// Channels are `quote:<SYMBOL>` and `candle:<SYMBOL>:<TIMEFRAME>`, up to 64. The
// ticket is offered as a second subprotocol, never in the URL. Stop with Ctrl-C,
// or set STOP_AFTER=N to stop after N seconds.

const API = "https://api.adona-robot.com";
const STREAM = "wss://api.adona-robot.com/v1/stream";

async function post(path, bearer, body) {
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${bearer}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    console.error(`refused: ${response.status} ${json.detail ?? ""}`);
    process.exit(1);
  }
  return json;
}

const channels = process.argv.slice(2).length ? process.argv.slice(2) : ["quote:EURUSD", "candle:EURUSD:M1"];
const key = process.env.ADONA_API_KEY;
if (!key) throw new Error("set ADONA_API_KEY to your API key");

// On your server: the key for a twelve-hour token per end user ("u-42" here).
const { access_token: token } = await post("/v1/tokens", key, { end_user_id: "u-42" });
// Anywhere the token is (a browser too): a single-use ticket.
const { ticket } = await post("/v1/ws-ticket", token);

const ws = new WebSocket(STREAM, ["adona.data.v1", `ticket.${ticket}`]);
ws.onopen = () => ws.send(JSON.stringify({ type: "subscribe", request_id: "sub", payload: { channels } }));
ws.onmessage = (event) => {
  const { type, payload } = JSON.parse(event.data);
  if (type === "subscribed" && payload.rejected?.length) console.log("not in your account's list:", payload.rejected);
  else if (type === "quote.snapshot" || type === "quote.update") console.log(type, payload.symbol, "bid", payload.bid, "ask", payload.ask, payload.as_of);
  else if (type === "candle.snapshot") console.log(type, payload.channel, payload.candles.length, "bars, last", payload.candles.at(-1)?.time);
  // Live bars use short keys: ts, o, h, l, c, v.
  else if (type === "candle.bar") console.log(type, `${payload.symbol} ${payload.tf}`, payload.ts, "close", payload.c);
  else if (type === "error") console.log("error", payload.code);
};
// 1008 with a reason is an answer (revoked, trial ended): do not reconnect in a loop on it.
ws.onclose = (event) => {
  console.log("closed", event.code, event.reason);
  process.exit(event.code === 1000 ? 0 : 1);
};

const seconds = Number(process.env.STOP_AFTER);
if (seconds > 0) setTimeout(() => ws.close(1000), seconds * 1000);
