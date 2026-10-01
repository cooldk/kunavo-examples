# Same request, two providers — the model string is just config.
# This is the point of an OpenAI-compatible gateway: no per-provider SDKs.
#   export KUNAVO_API_KEY=sk-kn-...
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],
    base_url="https://api.kunavo.com/v1",
)

PROMPT = "In one sentence: what makes a good API?"

for model in ["claude-sonnet-5", "claude-haiku-4-5", "gpt-6-sol"]:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
    )
    print(f"{model}:\n  {resp.choices[0].message.content}\n")
