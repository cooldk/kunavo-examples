// Node version of migrate.py — no dependencies (Node 18+). Same behaviour:
// map OpenRouter model ids to Kunavo ids, check them against the live catalog,
// flag OpenRouter-only request fields, optionally send one short request.
//
//   export KUNAVO_API_KEY=sk-kn-...
//   node migrate.mjs anthropic/claude-sonnet-4.6 openai/gpt-5.5
//   node migrate.mjs --request my_request.json --send anthropic/claude-sonnet-4.6
import { readFileSync } from "node:fs";

const BASE_URL = (process.env.KUNAVO_BASE_URL || "https://api.kunavo.com/v1").replace(/\/+$/, "");
const KEY = process.env.KUNAVO_API_KEY;

const OPENROUTER_ONLY_FIELDS = {
  provider: "OpenRouter provider routing preferences",
  models: "OpenRouter's fallback model list",
  route: "OpenRouter's fallback strategy",
  transforms: "OpenRouter prompt transforms (e.g. middle-out)",
  plugins: "OpenRouter plugins (web search, file parsing)",
  usage: "OpenRouter usage-accounting toggle, not a Kunavo parameter",
};

export function kunavoId(openrouterId) {
  const notes = [];
  let id = openrouterId.trim();
  if (id.includes("/")) id = id.slice(id.indexOf("/") + 1);
  if (id.includes(":")) {
    const [base, variant] = id.split(":", 2);
    id = base;
    notes.push(`':${variant}' is an OpenRouter routing variant with no Kunavo equivalent; the base model is used`);
  }
  id = id.replace(/(?<=\d)\.(?=\d)/g, "-");
  return { id, notes };
}

async function api(path, init = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json", "User-Agent": "migrate-from-openrouter/1 (+https://github.com/cooldk/kunavo-examples)", ...(init.headers || {}) },
  });
  const json = await res.json().catch(() => null);
  if (!res.ok) throw new Error(`${path} → ${res.status} ${json?.error?.message ?? ""}`);
  return json;
}

async function main() {
  const argv = process.argv.slice(2);
  const send = argv.includes("--send");
  const reqIdx = argv.indexOf("--request");
  const requestFile = reqIdx >= 0 ? argv[reqIdx + 1] : null;
  if (reqIdx >= 0 && (!requestFile || requestFile.startsWith("--"))) {
    throw new Error("--request requires a JSON file path");
  }
  const models = argv.filter((a, i) => !a.startsWith("--") && !(reqIdx >= 0 && i === reqIdx + 1));
  if (!models.length) throw new Error("Pass at least one OpenRouter model id");
  if (!KEY) {
    console.error("Set KUNAVO_API_KEY (sk-kn-...). It replaces your sk-or- key.");
    process.exit(2);
  }
  const live = (await api("/models", { method: "GET" })).data.map((m) => m.id).sort();
  console.log(`Live catalog at ${BASE_URL}: ${live.length} models\n`);
  const mapped = [];
  for (const orid of models) {
    const { id, notes } = kunavoId(orid);
    if (live.includes(id)) {
      console.log(`  ${orid.padEnd(45)} -> ${id}`);
      mapped.push(id);
    } else {
      const family = id.split("-").slice(0, 2).join("-");
      const near = live.filter((m) => m.startsWith(family)).slice(0, 6);
      console.log(`  ${orid.padEnd(45)} -> ${id}  (NOT in the catalog${near.length ? `; closest: ${near.join(", ")}` : ""})`);
    }
    for (const n of notes) console.log(`      note: ${n}`);
  }
  if (requestFile) {
    const body = JSON.parse(readFileSync(requestFile, "utf8"));
    const found = Object.keys(OPENROUTER_ONLY_FIELDS).filter((k) => k in body);
    console.log("\nRequest body:");
    if (!found.length) console.log("  no OpenRouter-only fields — it can be sent to Kunavo as is (after the model id change)");
    for (const k of found) console.log(`  remove '${k}': ${OPENROUTER_ONLY_FIELDS[k]}`);
    if (typeof body.model === "string" && body.model.includes("/")) console.log(`  model '${body.model}' -> '${kunavoId(body.model).id}'`);
  }
  console.log("\nHeaders: HTTP-Referer, X-Title are OpenRouter attribution headers; they can be dropped.");
  if (send) {
    console.log();
    for (const id of mapped) {
      const r = await api("/chat/completions", {
        method: "POST",
        body: JSON.stringify({ model: id, max_tokens: 16, messages: [{ role: "user", content: "Reply with the single word: pong" }] }),
      });
      console.log(`  ${id}: ${JSON.stringify(r.choices[0].message.content)}  usage ${r.usage?.prompt_tokens}+${r.usage?.completion_tokens}`);
    }
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => {
    console.error(e.message);
    process.exit(1);
  });
}
