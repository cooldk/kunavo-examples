# Text-to-image with Nano Banana (Google's image family) on the
# OpenAI-compatible images endpoint. ~$0.027/image; nano-banana-pro for
# top fidelity and text-in-image.
#   export KUNAVO_API_KEY=sk-kunavo-...
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KUNAVO_API_KEY"],
    base_url="https://api.kunavo.com/v1",
)

img = client.images.generate(
    model="nano-banana",  # or nano-banana-2 / nano-banana-pro / gpt-image-2
    prompt="A neon ramen stall in the rain, cinematic, 35mm",
    size="1024x1024",
)
# Returned URLs are temporary (~24h) — download and re-host.
print(img.data[0].url)
