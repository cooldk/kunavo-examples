# Claude via the unmodified OpenAI SDK — the two-line switch.
#   pip install openai
#   export KUNAVO_API_KEY=sk-kn-...
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],
    base_url="https://api.kunavo.com/v1",  # the only line that changes
)

resp = client.chat.completions.create(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "Explain quicksort in one paragraph."}],
)
print(resp.choices[0].message.content)
