// Candle history in JavaScript: your API key for a token, then pages of candles.
//
// Node 18+, no dependency:
//
//   export ADONA_API_KEY=...   # from your account page on adona-robot.com
//   node history.mjs EURUSD M1 2000
//
// The key stays on your server: it is exchanged at POST /v1/tokens for a
// twelve-hour token per end user, and every other call carries that token.
// Prices are strings, exactly as served: convert them at the last moment.

const API = "https://api.adona-robot.com";

class Refused extends Error {
  constructor(status, detail) {
    super(`${status} ${detail}`);
    this.status = status;
    this.code = String(detail).split(":")[0].trim(); // branch on this
  }
}

async function call(path, { bearer, method = "GET", body } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: { Authorization: `Bearer ${bearer}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) throw new Refused(response.status, json.detail ?? "");
  return json;
}

/** The latest `bars` bars, oldest first, paging back with the cursor. */
async function history(token, symbol, timeframe, bars) {
  const out = [];
  let before = null;
  while (out.length < bars) {
    const params = new URLSearchParams({ symbol, timeframe, limit: String(Math.min(5000, bars - out.length)) });
    if (before) params.set("before", before);
    const page = await call(`/v1/candles?${params}`, { bearer: token });
    out.unshift(...page.candles); // each page is older than the last
    before = page.next_before;
    if (!before) break; // nothing older for this account
  }
  return out.slice(-bars);
}

const [symbol = "EURUSD", timeframe = "M1", bars = "2000"] = process.argv.slice(2);
const key = process.env.ADONA_API_KEY;
if (!key) throw new Error("set ADONA_API_KEY to your API key");

try {
  const { access_token: token } = await call("/v1/tokens", { bearer: key, method: "POST", body: { end_user_id: "u-42" } });
  const candles = await history(token, symbol, timeframe, Number(bars));
  console.log(`${candles.length} bars, ${candles[0]?.time} to ${candles.at(-1)?.time}`);
  console.log("last:", candles.at(-1));
} catch (error) {
  console.error(`refused: ${error.message}`);
  process.exit(1);
}
