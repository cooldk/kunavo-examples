# Kunavo Examples

Runnable examples for [Kunavo](https://kunavo.com) — an independent, OpenAI-compatible AI API gateway: one API key and one pay-as-you-go balance reach Claude, GPT and image, video and audio models, with no per-provider account required.

Maintained by Kunavo's operator. Code and documentation are prepared with AI assistance. The offline examples below document their validation and limitations.

For supported Chat Completions requests, configure the OpenAI SDK with your Kunavo key and base URL:

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],          # sk-kn-...
    base_url="https://api.kunavo.com/v1",          # Kunavo Chat Completions endpoint
)
resp = client.chat.completions.create(
    model="claude-sonnet-5",                    # verify availability in /v1/models
    messages=[{"role": "user", "content": "Hello"}],
)
```

Kunavo is an independent gateway that resells access to these models. Kunavo is not Anthropic, Google or OpenAI, and Kunavo does not train or host the models it serves.

## Setup

1. Create a key at [kunavo.com/app/keys](https://kunavo.com/app/keys) — it is shown once. Pay-as-you-go from a $10 top-up; the balance never expires and there is no monthly fee.
2. `export KUNAVO_API_KEY=sk-kn-...`
3. Run any example below.

## Discover models and current prices

Examples show specific model IDs to make requests concrete. Before using them, check the [live model catalog](https://api.kunavo.com/v1/models) for availability, endpoint, capabilities and limits. Model IDs are exact strings; a sample or an archived study is not a promise that a model is currently available.

Use [live pricing](https://kunavo.com/pricing) or the [machine-readable price catalog](https://kunavo.com/pricing.json) for current rates and billing units. This README does not maintain a separate price table. Media pricing can depend on duration or tier; token pricing can distinguish ordinary input, cache writes, cache reads and output. See [billing](https://kunavo.com/docs/billing) and [prompt caching](https://kunavo.com/docs/caching).

## Start without making a live API call

These examples can be inspected and tested with synthetic data, without an account or API key:

- [`billing-attribution/`](billing-attribution/) reproduces a historical-cost attribution bug when keys move between clients, with a SQLite model and six offline tests.
- [`usage-daily/`](usage-daily/) converts a single key's usage snapshot to daily CSV, preserving decimal costs and UTC boundaries.
- [`agent-cost-audit/`](agent-cost-audit/) compares task costs while separating retries, rejected work and health checks.
- [`music-job-recovery/`](music-job-recovery/) plans recovery after an uncertain submission, with bounded polling and explicit resubmission decisions.

Their offline tests validate local behavior, not live model compatibility, billing correctness or production reliability. Follow each directory's README for commands and limits.

## Examples

| File | What it shows |
|---|---|
| [`python/chat.py`](python/chat.py) | Claude via the OpenAI SDK — the two-line switch |
| [`python/multi_model.py`](python/multi_model.py) | Same code, two providers (Claude, GPT) — model string as config |
| [`python/image.py`](python/image.py) | Text-to-image with Nano Banana (`/v1/images/generations`) |
| [`python/image_edit.py`](python/image_edit.py) | Image-to-image editing (`/v1/images/edits`) |
| [`python/video.py`](python/video.py) | Veo 3 text-to-video with the async task lifecycle (`/v1/videos`) |
| [`python/music.py`](python/music.py) | Suno V5 song generation with job polling (`/v1/audio/music/jobs`) |
| [`music-job-recovery/`](music-job-recovery/) | Offline recovery decisions: lost submit response, known task ID, bounded polling and archive fallback; synthetic scenarios and tests |
| [`node/chat.mjs`](node/chat.mjs) | Node.js — OpenAI SDK against Claude |
| [`node/image.mjs`](node/image.mjs) | Node.js — Nano Banana image generation |
| [`shell/curl.sh`](shell/curl.sh) | Raw curl for every endpoint |
| [`migrate-from-openrouter/`](migrate-from-openrouter/) | Python and Node scripts that map model ids against the live catalog and flag provider-specific request fields |
| [`compat-test/`](compat-test/) | Eight protocol checks for an OpenAI-compatible endpoint; one Node file, no dependencies |
| [`agent-cost-audit/`](agent-cost-audit/) | Offline task-cost calculator: cache writes/reads, retries, rejected work and separate health checks; synthetic fixture and tests |
| [`usage-daily/`](usage-daily/) | Daily per-key usage CSV with UTC date boundaries, decimal costs, missing-day handling and offline tests |
| [`n8n-templates/`](n8n-templates/) | Three importable workflows: validated extraction, FAQ reply drafts and RSS drafts, with human review |
| [`research/task-costs-2026-10/`](research/task-costs-2026-10/) | All 270 task runs, per-request billing and the harness behind a small first-party cost study |
| [`streaming-tool-calls/`](streaming-tool-calls/) | Offline SSE fixtures and diagnostics for streamed function calls; no API key or network |

## Two wire formats, one key

`/v1/chat/completions` and `/v1/responses` expose their respective OpenAI-compatible request formats. `/v1/messages` exposes the Anthropic Messages format. Media endpoints have their own request and asynchronous-task contracts; consult the endpoint documentation instead of assuming every SDK method is supported.

The two conventions disagree about `/v1` on purpose, and getting it backwards is the most common setup failure:

- **OpenAI-style clients** want `https://api.kunavo.com/v1` as the base URL.
- **Anthropic-style clients** append `/v1/messages` themselves, so they want the origin alone: `https://api.kunavo.com`.

## Using it from a tool instead of from code

See the [integration guides](https://kunavo.com/docs/integrations) for client-specific configuration. A custom base URL alone does not establish compatibility: check the client version, endpoint, model ID and required features. The examples here are not a certification of every client listed in those guides.

## For AI agents

- [`kunavo.com/openapi.json`](https://kunavo.com/openapi.json) — machine-readable OpenAPI 3.1 description of every endpoint.
- [`kunavo.com/llms.txt`](https://kunavo.com/llms.txt) — a self-contained plain-text reference: model discovery, billing units and endpoint shapes, written so an agent can integrate without reading documentation pages.

## Why a gateway?

One key and one bill instead of an account per provider; routing and failover across upstreams; per-key spend caps and IP allowlists. The pattern — and when you *don't* need it — is covered in [What is an AI gateway?](https://kunavo.com/guides/ai-gateway) and the honest [OpenRouter alternatives comparison](https://kunavo.com/guides/openrouter-alternatives).

## License

The code and documentation in this repository are MIT-licensed. This does not make the hosted Kunavo service or model weights open source.
