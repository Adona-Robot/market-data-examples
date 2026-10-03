// Node 22+: live quotes and closed bars on one WebSocket. ADONA_API_KEY=... node stream.mjs
// In a browser the WebSocket part is the same; the token comes from your server, never the key.
const API = "https://api.adona-robot.com";
const STREAM = "wss://api.adona-robot.com/v1/stream";

async function post(path, bearer, body) {
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${bearer}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`refused: ${response.status} ${await response.text()}`);
  return response.json();
}

// your server exchanges the key for a token
const { access_token: token } = await post("/v1/tokens", process.env.ADONA_API_KEY, { end_user_id: "u-42" });
// a single-use ticket, offered as the second subprotocol, never in the URL
const { ticket } = await post("/v1/ws-ticket", token);

const ws = new WebSocket(STREAM, ["adona.data.v1", `ticket.${ticket}`]);
ws.onopen = () =>
  ws.send(JSON.stringify({ type: "subscribe", request_id: "sub", payload: { channels: ["quote:EURUSD", "candle:EURUSD:M1"] } }));
ws.onmessage = (event) => {
  const { type, payload } = JSON.parse(event.data);
  if (type === "quote.update" || type === "quote.snapshot") console.log(type, payload.symbol, payload.bid, payload.ask);
  else if (type === "candle.snapshot") console.log(type, payload.channel, payload.candles.length, "bars");
  else if (type === "candle.bar") console.log(type, payload.symbol, payload.tf, payload.ts, payload.c); // short keys
  else console.log(type, payload);
};
// 1008 with a reason (revoked, trial ended) is an answer: do not reconnect in a loop on it
ws.onclose = (event) => console.log("closed", event.code, event.reason);
