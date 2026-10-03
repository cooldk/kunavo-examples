# Moving from OpenRouter to Kunavo

Both speak the OpenAI chat-completions protocol, so most code moves with three changes. These scripts do the part that is easy to get wrong — the model ids — against the live catalog, and point out what in your request has no equivalent.

```bash
export KUNAVO_API_KEY=sk-kn-...          # replaces your sk-or- key
pip install openai && python migrate.py anthropic/claude-sonnet-4.6 openai/gpt-5.5
# or, no dependencies:
node migrate.mjs anthropic/claude-sonnet-4.6 openai/gpt-5.5
# check a request body you send today, and try each mapped model once:
python migrate.py --request my_request.json --send anthropic/claude-sonnet-4.6
```

## What changes

| | OpenRouter | Kunavo |
|---|---|---|
| Base URL | `https://openrouter.ai/api/v1` | `https://api.kunavo.com/v1` (Anthropic SDKs: `https://api.kunavo.com`) |
| Key | `sk-or-...` | `sk-kn-...` from [kunavo.com/app/keys](https://kunavo.com/app/keys) |
| Model ids | `vendor/model` with optional `:variant` | bare id, version dots as hyphens: `anthropic/claude-sonnet-4.6` → `claude-sonnet-4-6` |
| Routing fields | `provider`, `models`, `route`, `transforms`, `plugins` | none — remove them; Kunavo fails over between its own upstream channels |
| Attribution headers | `HTTP-Referer`, `X-Title` | not used; safe to drop |

## What does not carry over

- Routing variants (`:free`, `:nitro`, `:floor`, `:online`, `:thinking`): there is one way to call each model.
- Models Kunavo does not list. The script prints the closest ids in the same family; it never guesses one silently.
- Free models and bring-your-own-key: Kunavo has neither.
- Batch pricing: there is no batch endpoint.

The side-by-side comparison, including when to stay on OpenRouter, is at [kunavo.com/compare/openrouter](https://kunavo.com/compare/openrouter).
