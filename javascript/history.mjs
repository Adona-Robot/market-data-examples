// Node 18+, on your server: ADONA_API_KEY=... node history.mjs
const API = "https://api.adona-robot.com";

async function call(path, bearer, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${bearer}`, "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`refused: ${response.status} ${await response.text()}`);
  return response.json();
}

const key = process.env.ADONA_API_KEY;
if (!key) throw new Error("set ADONA_API_KEY to your API key");

// your server exchanges the key for a token
const { access_token: token, expires_in } = await call("/v1/tokens", key, {
  method: "POST",
  body: JSON.stringify({ end_user_id: "u-42" }),
});

// the token reads candles
const page = await call("/v1/candles?symbol=EURUSD&timeframe=M1&limit=1000", token);
console.log(page.candles.length, "bars, newest:", page.candles.at(-1));
console.log(`token ok, expires in ${expires_in} s`);
