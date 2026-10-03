#!/usr/bin/env node
// OpenAI-compatible endpoint compatibility test — run it on your own machine,
// with your own key, against any endpoint (Kunavo or not).
//
//   node compat-test.mjs --base-url https://api.kunavo.com/v1 --model claude-sonnet-5
//   KEY comes from --key or the API_KEY / KUNAVO_API_KEY environment variable.
//
// What it checks, in order — each line is PASS, FAIL, WARN or SKIP with the
// evidence next to it:
//   1. base URL      GET {base}/models answers JSON with a data[] list
//   2. auth errors   a wrong key gets a 401 with a JSON error body, not HTML
//   3. chat          a plain completion returns text and a usage block whose
//                    total = prompt + completion
//   4. streaming     SSE chunks arrive, a finish_reason is set, the stream
//                    ends with [DONE]; time to first byte and total are timed
//   5. stream usage  stream_options.include_usage yields a usage chunk
//   6. tools         a forced tool call comes back with JSON-parsable arguments
//   7. json mode     response_format json_object returns parsable JSON
//   8. bad model     an unknown model id gets a 4xx JSON error, not HTML
//
// Your key is sent only to --base-url, only in the Authorization header, and is
// never printed. Requests are small (max_tokens ≤ 64) — a full run costs a few
// thousandths of a dollar on most models. Node 18+ (built-in fetch), no deps.

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => {
    if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : "true"]);
    return acc;
  }, [])
);
// Identifies these requests in the endpoint's own logs (nothing else is sent).
const USER_AGENT = "compat-test/1 (+https://github.com/cooldk/kunavo-examples)";
const BASE = (args["base-url"] || process.env.BASE_URL || "https://api.kunavo.com/v1").replace(/\/+$/, "");
const KEY = args.key || process.env.API_KEY || process.env.KUNAVO_API_KEY || "";
const MODEL = args.model || "claude-sonnet-5";
const JSON_OUT = args.json && args.json !== "true" ? args.json : null;
const TIMEOUT = Number(args.timeout || 60) * 1000;

if (!KEY) {
  console.error("No key. Pass --key or set API_KEY / KUNAVO_API_KEY. It is only sent to --base-url.");
  process.exit(2);
}

const results = [];
const record = (name, status, detail) => {
  results.push({ name, status, detail });
  const mark = { PASS: "✔", FAIL: "✘", WARN: "!", SKIP: "-" }[status];
  console.log(`${mark} ${status.padEnd(4)} ${name.padEnd(13)} ${detail}`);
};

async function call(path, { method = "POST", body, key = KEY, stream = false } = {}) {
  const started = performance.now();
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", Accept: stream ? "text/event-stream" : "application/json", "User-Agent": USER_AGENT },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(TIMEOUT),
  });
  return { res, started };
}

async function readJson(res) {
  const text = await res.text();
  try {
    return { json: JSON.parse(text), text };
  } catch {
    return { json: null, text };
  }
}

const looksHtml = (t) => /^\s*<(!doctype|html)/i.test(t);
/** One line of evidence: HTML bodies are named, not dumped. */
const brief = (t) => (looksHtml(t) ? "(an HTML page)" : t.replace(/\s+/g, " ").trim().slice(0, 140));

async function testModels() {
  try {
    const { res } = await call("/models", { method: "GET" });
    const { json, text } = await readJson(res);
    if (looksHtml(text)) {
      record("base URL", "FAIL", `GET /models returned an HTML page (status ${res.status}) — the base URL is probably missing /v1`);
      return "stop";
    }
    if (json?.error?.code === "missing_v1_prefix") {
      record("base URL", "FAIL", `the endpoint says the base URL is missing /v1: ${brief(json.error.message)}`);
      return "stop";
    }
    if (res.status === 401 || res.status === 403) {
      record("base URL", "FAIL", `your key was rejected (${res.status}): ${brief(text)}`);
      return "stop";
    }
    if (!res.ok) return record("base URL", "FAIL", `GET /models → ${res.status} ${brief(text)}`);
    const ids = Array.isArray(json?.data) ? json.data.map((m) => m.id) : null;
    if (!ids) return record("base URL", "FAIL", "GET /models returned JSON without a data[] list");
    const has = ids.includes(MODEL);
    record("base URL", has ? "PASS" : "WARN", `${ids.length} models listed${has ? `, including ${MODEL}` : ` — ${MODEL} is NOT among them`}`);
  } catch (e) {
    record("base URL", "FAIL", e.message);
  }
}

async function testAuth() {
  try {
    const { res } = await call("/models", { method: "GET", key: "sk-compat-test-invalid" });
    const { json, text } = await readJson(res);
    if (res.status === 401 && json?.error) return record("auth errors", "PASS", `401 with JSON error (${json.error.type ?? json.error.code ?? "no type"})`);
    if (looksHtml(text)) return record("auth errors", "FAIL", `status ${res.status} with an HTML body`);
    record("auth errors", "WARN", `status ${res.status}${json ? " (JSON)" : " (not JSON)"} — clients expect 401`);
  } catch (e) {
    record("auth errors", "FAIL", e.message);
  }
}

async function testChat() {
  try {
    const { res } = await call("/chat/completions", {
      body: { model: MODEL, max_tokens: 32, messages: [{ role: "user", content: "Reply with the single word: pong" }] },
    });
    const { json, text } = await readJson(res);
    if (!res.ok) return record("chat", "FAIL", `${res.status} ${brief(text)}`);
    const content = json?.choices?.[0]?.message?.content;
    const u = json?.usage;
    if (typeof content !== "string" || !content.trim()) return record("chat", "FAIL", "no message content in choices[0]");
    if (!u) return record("chat", "WARN", `reply "${content.trim().slice(0, 30)}" but no usage block`);
    const sumOk = u.total_tokens === u.prompt_tokens + u.completion_tokens;
    record("chat", sumOk ? "PASS" : "WARN", `reply "${content.trim().slice(0, 30)}", usage ${u.prompt_tokens}+${u.completion_tokens}=${u.total_tokens}${sumOk ? "" : " (total ≠ prompt + completion)"}`);
  } catch (e) {
    record("chat", "FAIL", e.message);
  }
}

async function readSse(res, started) {
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "", ttfb = null, chunks = 0, text = "", finish = null, done = false, usage = null;
  for (;;) {
    const { value, done: end } = await reader.read();
    if (end) break;
    if (ttfb == null) ttfb = performance.now() - started;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 1);
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (data === "[DONE]") { done = true; continue; }
      try {
        const j = JSON.parse(data);
        chunks++;
        const c = j.choices?.[0];
        if (c?.delta?.content) text += c.delta.content;
        if (c?.finish_reason) finish = c.finish_reason;
        if (j.usage) usage = j.usage;
      } catch { /* keep-alive or comment */ }
    }
  }
  return { ttfb, total: performance.now() - started, chunks, text, finish, done, usage };
}

async function testStream() {
  try {
    const { res, started } = await call("/chat/completions", {
      stream: true,
      body: { model: MODEL, max_tokens: 64, stream: true, messages: [{ role: "user", content: "Count from 1 to 10, separated by spaces." }] },
    });
    if (!res.ok) return record("streaming", "FAIL", `${res.status} ${brief(await res.text())}`);
    const s = await readSse(res, started);
    const problems = [];
    if (!s.text) problems.push("no delta content");
    if (!s.finish) problems.push("no finish_reason");
    if (!s.done) problems.push("no [DONE]");
    record("streaming", problems.length ? "FAIL" : "PASS", `${s.chunks} chunks, TTFB ${Math.round(s.ttfb)} ms, total ${Math.round(s.total)} ms, finish=${s.finish ?? "none"}${problems.length ? ` — ${problems.join(", ")}` : ""}`);
  } catch (e) {
    record("streaming", "FAIL", e.message);
  }
}

async function testStreamUsage() {
  try {
    const { res, started } = await call("/chat/completions", {
      stream: true,
      body: { model: MODEL, max_tokens: 16, stream: true, stream_options: { include_usage: true }, messages: [{ role: "user", content: "Say hi." }] },
    });
    if (!res.ok) return record("stream usage", "WARN", `${res.status} — stream_options may not be accepted`);
    const s = await readSse(res, started);
    record("stream usage", s.usage ? "PASS" : "WARN", s.usage ? `usage chunk ${s.usage.prompt_tokens}+${s.usage.completion_tokens}` : "no usage chunk — clients that bill from the stream will show 0");
  } catch (e) {
    record("stream usage", "FAIL", e.message);
  }
}

async function testTools() {
  try {
    const { res } = await call("/chat/completions", {
      body: {
        model: MODEL,
        max_tokens: 64,
        messages: [{ role: "user", content: "What is the weather in Paris? Use the tool." }],
        tools: [{ type: "function", function: { name: "get_weather", description: "Weather for a city", parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] } } }],
        tool_choice: { type: "function", function: { name: "get_weather" } },
      },
    });
    const { json, text } = await readJson(res);
    if (!res.ok) return record("tools", "FAIL", `${res.status} ${brief(text)}`);
    const tc = json?.choices?.[0]?.message?.tool_calls?.[0];
    if (!tc) return record("tools", "FAIL", "no tool_calls in the response");
    let argsOk = false;
    try { argsOk = typeof JSON.parse(tc.function.arguments) === "object"; } catch { /* */ }
    record("tools", argsOk ? "PASS" : "FAIL", `${tc.function?.name}(${String(tc.function?.arguments).slice(0, 60)})${argsOk ? "" : " — arguments are not JSON"}`);
  } catch (e) {
    record("tools", "FAIL", e.message);
  }
}

async function testJsonMode() {
  try {
    const { res } = await call("/chat/completions", {
      body: { model: MODEL, max_tokens: 48, response_format: { type: "json_object" }, messages: [{ role: "user", content: 'Return a JSON object {"ok": true} and nothing else.' }] },
    });
    const { json, text } = await readJson(res);
    if (!res.ok) return record("json mode", "WARN", `${res.status} — response_format json_object not accepted: ${brief(text)}`);
    const content = json?.choices?.[0]?.message?.content ?? "";
    let ok = false;
    try { JSON.parse(content.replace(/^```(json)?\s*|\s*```$/g, "")); ok = true; } catch { /* */ }
    record("json mode", ok ? "PASS" : "WARN", ok ? "content parses as JSON" : `content is not bare JSON: ${content.slice(0, 60)}`);
  } catch (e) {
    record("json mode", "FAIL", e.message);
  }
}

async function testBadModel() {
  try {
    const { res } = await call("/chat/completions", { body: { model: "no-such-model-compat-test", max_tokens: 8, messages: [{ role: "user", content: "hi" }] } });
    const { json, text } = await readJson(res);
    if (res.status >= 400 && res.status < 500 && json?.error) return record("bad model", "PASS", `${res.status} with JSON error`);
    if (looksHtml(text)) return record("bad model", "FAIL", `${res.status} with an HTML body`);
    record("bad model", "WARN", `status ${res.status}${json ? "" : " (not JSON)"}`);
  } catch (e) {
    record("bad model", "FAIL", e.message);
  }
}

console.log(`Endpoint ${BASE} · model ${MODEL}\n`);
const tests = [
  ["base URL", testModels], ["auth errors", testAuth], ["chat", testChat], ["streaming", testStream],
  ["stream usage", testStreamUsage], ["tools", testTools], ["json mode", testJsonMode], ["bad model", testBadModel],
];
for (let i = 0; i < tests.length; i++) {
  if ((await tests[i][1]()) === "stop") {
    for (const [name] of tests.slice(i + 1)) record(name, "SKIP", "skipped — fix the base URL or key first");
    break;
  }
}

const count = (s) => results.filter((r) => r.status === s).length;
console.log(`\n${count("PASS")} passed, ${count("WARN")} warnings, ${count("FAIL")} failed`);
if (JSON_OUT) {
  const { writeFileSync } = await import("node:fs");
  writeFileSync(JSON_OUT, JSON.stringify({ base_url: BASE, model: MODEL, ran_at: new Date().toISOString(), results }, null, 2) + "\n");
  console.log(`Report written to ${JSON_OUT} (no key inside).`);
}
process.exit(count("FAIL") ? 1 : 0);
