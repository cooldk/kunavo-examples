# Kunavo Examples

Runnable examples for [Kunavo](https://kunavo.com) — an independent, OpenAI-compatible AI API gateway: one API key and one pay-as-you-go balance reach Claude, Gemini, GPT and image, video and audio models, with no per-provider account required.

If your code can call the OpenAI API, it can call Kunavo by changing one line:

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],          # sk-kn-...
    base_url="https://api.kunavo.com/v1",          # the only line that changes
)
resp = client.chat.completions.create(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Kunavo is an independent gateway that resells access to these models. Kunavo is not Anthropic, Google or OpenAI, and Kunavo does not train or host the models it serves.

## Setup

1. Create a key at [kunavo.com/app/keys](https://kunavo.com/app/keys) — it is shown once. Pay-as-you-go from a $10 top-up; the balance never expires and there is no monthly fee.
2. `export KUNAVO_API_KEY=sk-kn-...`
3. Run any example below.

## What you can call with that one key

Rates below are Kunavo's, in USD, and were taken from the catalog on 2026-09-06. [Live pricing](https://kunavo.com/pricing) is authoritative; `GET /v1/models` is the live catalog.

**Chat** — per 1M tokens, input / output:

| Model id | In / out | Notes |
|---|---|---|
| `claude-sonnet-5` | $2.00 / $10.00 | the general default |
| `claude-opus-5` | $2.00 / $10.00 | planning, architecture, hard reasoning |
| `claude-haiku-4-5` | $0.40 / $2.00 | high-volume work; cheapest Claude |
| `gpt-5-6-sol` | $2.00 / $12.00 | also reachable on `/v1/responses` (Codex CLI) |
| `gpt-5-4-mini` | $0.225 / $1.35 | cheapest GPT |
| `gemini-3-1-pro` | $0.70 / $4.20 | long context |
| `gemini-2-5-flash` | $0.09 / $0.75 | cheapest model in the catalog |

**Image** (per image) — `nano-banana` $0.0273, `nano-banana-2`, `nano-banana-2-lite`, `nano-banana-pro` from $0.067, `gpt-image-2` $0.0633, plus `nano-banana-edit` and `gpt-image-2-edit` for editing.

**Video** (per clip, cheapest tier) — `veo-3-lite` from $0.18, `veo-3` from $0.36, `veo-3-quality`, `seedance-2` / `-fast` / `-2-5` / `-mini` from $0.0526, `wan-2-7` from $0.096.

**Music** (per track) — `suno-v5` $0.09, `suno-v5-5`.

Prompt caching is billed at the cache-read rate on every model that supports it, which on a repeated-context workload moves the bill more than the model choice does — see [caching](https://kunavo.com/docs/caching).

## Examples

| File | What it shows |
|---|---|
| [`python/chat.py`](python/chat.py) | Claude via the OpenAI SDK — the two-line switch |
| [`python/multi_model.py`](python/multi_model.py) | Same code, three providers (Claude, Gemini, GPT) — model string as config |
| [`python/image.py`](python/image.py) | Text-to-image with Nano Banana (`/v1/images/generations`) |
| [`python/image_edit.py`](python/image_edit.py) | Image-to-image editing (`/v1/images/edits`) |
| [`python/video.py`](python/video.py) | Veo 3 text-to-video with the async task lifecycle (`/v1/videos`) |
| [`python/music.py`](python/music.py) | Suno V5 song generation with job polling (`/v1/audio/music/jobs`) |
| [`node/chat.mjs`](node/chat.mjs) | Node.js — OpenAI SDK against Claude |
| [`node/image.mjs`](node/image.mjs) | Node.js — Nano Banana image generation |
| [`shell/curl.sh`](shell/curl.sh) | Raw curl for every endpoint |

## Two wire formats, one key

`/v1/chat/completions`, `/v1/responses` and the media routes speak the OpenAI formats. `/v1/messages` speaks the Anthropic Messages format, so an Anthropic SDK works unmodified.

The two conventions disagree about `/v1` on purpose, and getting it backwards is the most common setup failure:

- **OpenAI-style clients** want `https://api.kunavo.com/v1` as the base URL.
- **Anthropic-style clients** append `/v1/messages` themselves, so they want the origin alone: `https://api.kunavo.com`.

## Using it from a tool instead of from code

Anything with a base-URL field works, and [kunavo.com/docs/integrations](https://kunavo.com/docs/integrations) has the exact fields per client — Claude Code, Kilo Code, Roo Code, Cline, Codex CLI, opencode, Zed, Continue, Aider, Claude Code Router, Open WebUI, Cherry Studio, Chatbox, LobeChat, SillyTavern, Janitor AI. Each page names the client's own documentation and the date the configuration was last checked against it.

## For AI agents

- [`kunavo.com/openapi.json`](https://kunavo.com/openapi.json) — machine-readable OpenAPI 3.1 description of every endpoint.
- [`kunavo.com/llms.txt`](https://kunavo.com/llms.txt) — a self-contained plain-text reference: model discovery, billing units and endpoint shapes, written so an agent can integrate without reading documentation pages.

## Why a gateway?

One key and one bill instead of an account per provider; routing and failover across upstreams; per-key spend caps and IP allowlists. The pattern — and when you *don't* need it — is covered in [What is an AI gateway?](https://kunavo.com/guides/ai-gateway) and the honest [OpenRouter alternatives comparison](https://kunavo.com/guides/openrouter-alternatives).

## License

MIT — use these snippets in anything.
