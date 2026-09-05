# Image-to-image: edit an existing image with a text instruction.
# POST /v1/images/edits takes a prompt + source image (https URL or
# data: base64 URI) and keeps the subject while applying the change.
#   export KUNAVO_API_KEY=sk-kn-...
import os

import requests

resp = requests.post(
    "https://api.kunavo.com/v1/images/edits",
    headers={"Authorization": f"Bearer {os.environ['KUNAVO_API_KEY']}"},
    json={
        "model": "nano-banana-edit",
        "prompt": "make the sky golden hour, keep the subject",
        "image": "https://example.com/source.png",
    },
    timeout=120,
)
resp.raise_for_status()
print(resp.json()["data"][0]["url"])
