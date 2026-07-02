# Same request, three providers — the model string is just config.
# This is the point of an OpenAI-compatible gateway: no per-provider SDKs.
#   export KUNAVO_API_KEY=sk-kunavo-...
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],
    base_url="https://api.kunavo.com/v1",
)

PROMPT = "In one sentence: what makes a good API?"

for model in ["claude-sonnet-4-6", "gemini-2-5-flash", "gpt-5-4-mini"]:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
    )
    print(f"{model}:\n  {resp.choices[0].message.content}\n")
