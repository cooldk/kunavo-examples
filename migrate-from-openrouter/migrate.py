"""Move an OpenRouter integration to Kunavo: map the model ids, check them
against the live catalog, list what in your request has no equivalent, and
(optionally) send one short request through each mapped model.

    pip install openai
    export KUNAVO_API_KEY=sk-kn-...
    python migrate.py anthropic/claude-sonnet-4.6 openai/gpt-5.5 meta-llama/llama-4:free
    python migrate.py --request my_request.json --send anthropic/claude-sonnet-4.6

Nothing here talks to OpenRouter. The key is sent only to KUNAVO_BASE_URL
(default https://api.kunavo.com/v1).
"""
import argparse
import json
import os
import re
import sys

from openai import OpenAI

BASE_URL = os.environ.get("KUNAVO_BASE_URL", "https://api.kunavo.com/v1")

# Request fields that exist only on OpenRouter. Kunavo does its own channel
# failover, so there is nothing to translate them into — remove them.
OPENROUTER_ONLY_FIELDS = {
    "provider": "OpenRouter provider routing preferences",
    "models": "OpenRouter's fallback model list",
    "route": "OpenRouter's fallback strategy",
    "transforms": "OpenRouter prompt transforms (e.g. middle-out)",
    "plugins": "OpenRouter plugins (web search, file parsing)",
    "usage": "OpenRouter usage-accounting toggle, not a Kunavo parameter",
}
OPENROUTER_ONLY_HEADERS = ("HTTP-Referer", "X-Title")


def kunavo_id(openrouter_id: str):
    """anthropic/claude-sonnet-4.6:nitro -> ('claude-sonnet-4-6', [notes])."""
    notes = []
    mid = openrouter_id.strip()
    if "/" in mid:
        mid = mid.split("/", 1)[1]  # Kunavo ids carry no vendor/ prefix
    if ":" in mid:
        mid, variant = mid.split(":", 1)
        notes.append(f"':{variant}' is an OpenRouter routing variant with no Kunavo equivalent; the base model is used")
    # Version dots become hyphens: 4.6 -> 4-6, 5.5 -> 5-5.
    mid = re.sub(r"(?<=\d)\.(?=\d)", "-", mid)
    return mid, notes


def closest(candidate: str, live: list[str]) -> list[str]:
    """Live ids that share the candidate's family prefix, e.g. claude-sonnet-*."""
    family = "-".join(candidate.split("-")[:2])
    return sorted(i for i in live if i.startswith(family))[:6]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="+", help="OpenRouter model ids, e.g. anthropic/claude-sonnet-4.6")
    ap.add_argument("--request", help="a JSON request body you send to OpenRouter today, to check for OpenRouter-only fields")
    ap.add_argument("--send", action="store_true", help="send one short request through each mapped model (costs a fraction of a cent)")
    args = ap.parse_args()

    key = os.environ.get("KUNAVO_API_KEY")
    if not key:
        print("Set KUNAVO_API_KEY (sk-kn-...). It replaces your sk-or- key.", file=sys.stderr)
        return 2
    client = OpenAI(api_key=key, base_url=BASE_URL, default_headers={"User-Agent": "migrate-from-openrouter/1 (+https://github.com/cooldk/kunavo-examples)"})
    live = sorted(m.id for m in client.models.list())

    print(f"Live catalog at {BASE_URL}: {len(live)} models\n")
    mapped = []
    for orid in args.models:
        kid, notes = kunavo_id(orid)
        if kid in live:
            print(f"  {orid:45s} -> {kid}")
            mapped.append(kid)
        else:
            near = closest(kid, live)
            print(f"  {orid:45s} -> {kid}  (NOT in the catalog{'; closest: ' + ', '.join(near) if near else ''})")
        for n in notes:
            print(f"      note: {n}")

    if args.request:
        with open(args.request, encoding="utf-8") as f:
            body = json.load(f)
        found = [k for k in OPENROUTER_ONLY_FIELDS if k in body]
        print("\nRequest body:")
        if not found:
            print("  no OpenRouter-only fields — it can be sent to Kunavo as is (after the model id change)")
        for k in found:
            print(f"  remove '{k}': {OPENROUTER_ONLY_FIELDS[k]}")
        if isinstance(body.get("model"), str) and "/" in body["model"]:
            print(f"  model '{body['model']}' -> '{kunavo_id(body['model'])[0]}'")
    print(f"\nHeaders: {', '.join(OPENROUTER_ONLY_HEADERS)} are OpenRouter attribution headers; they can be dropped.")

    if args.send:
        print()
        for kid in mapped:
            resp = client.chat.completions.create(
                model=kid, max_tokens=16, messages=[{"role": "user", "content": "Reply with the single word: pong"}]
            )
            u = resp.usage
            print(f"  {kid}: {resp.choices[0].message.content!r}  usage {u.prompt_tokens}+{u.completion_tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
