# Kunavo Examples

Runnable examples for [Kunavo](https://kunavo.com) — an **OpenAI-compatible AI gateway** to frontier text, image, video and music models. One base URL, one `sk-kunavo-` key, one pay-as-you-go balance:

- **Chat**: Claude, Gemini, GPT — via the unmodified OpenAI SDK
- **Image**: Nano Banana (incl. Pro), GPT-Image-2 — generate + edit
- **Video**: Google Veo 3 (text-to-video / image-to-video, native audio)
- **Music**: Suno V5 (full songs from a prompt)

Everything is priced **below the providers' official list** (chat models ~30% under; see [live pricing](https://kunavo.com/pricing) and the [LLM cost calculator](https://kunavo.com/tools/llm-cost-calculator)). If your code can call the OpenAI API, it can call Kunavo by changing only the `base_url`.

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],          # sk-kunavo-...
    base_url="https://api.kunavo.com/v1",           # the only line that changes
)
resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
)
```

## Setup

1. Create a key at [kunavo.com/app/keys](https://kunavo.com/app/keys) (pay-as-you-go from a $5 top-up, balance never expires)
2. `export KUNAVO_API_KEY=sk-kunavo-...`
3. Run any example below

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

## For AI agents

Kunavo publishes a complete, self-contained machine-readable API reference at [`kunavo.com/llms.txt`](https://kunavo.com/llms.txt) — model discovery (`GET /v1/models`), billing units and endpoint shapes, designed so an autonomous agent can integrate without reading docs pages.

## Why a gateway?

One key and one bill instead of N provider accounts; routing and failover across providers; per-key spend caps. The pattern — and when you *don't* need it — is covered in [What is an AI gateway?](https://kunavo.com/guides/ai-gateway) and the honest [OpenRouter alternatives comparison](https://kunavo.com/guides/openrouter-alternatives).

## License

MIT — use these snippets in anything.
