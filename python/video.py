# Veo 3 text-to-video with the async task lifecycle — the production
# pattern. Generation takes minutes: submit to /v1/videos, poll the task.
# From $0.16 per 8s 720p clip (Veo 3 Lite); veo-3 / veo-3-quality for
# higher tiers. Native synchronized audio.
#   export KUNAVO_API_KEY=sk-kunavo-...
import os
import time

import requests

BASE = "https://api.kunavo.com/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['KUNAVO_API_KEY']}"}

# 1. Submit the generation task
task = requests.post(
    f"{BASE}/videos",
    headers=HEADERS,
    json={
        "model": "veo-3",
        "prompt": "a slow push-in on a neon-lit alley in the rain, cinematic",
        "duration": 8,
        "aspect_ratio": "16:9",
    },
    timeout=60,
).json()
task_id = task["id"]  # "vid_abc..."
status = task["status"]  # "queued"
print(f"task {task_id} submitted, polling...")

# 2. Poll until terminal (typically a couple of minutes)
while status not in ("completed", "failed"):
    time.sleep(15)
    v = requests.get(f"{BASE}/videos/{task_id}", headers=HEADERS, timeout=60).json()
    status = v["status"]
    print(f"  status: {status}")

if status == "failed":
    raise SystemExit(f"generation failed: {v['error']['message']}")
print(v["output"]["url"])  # temporary URL — download and re-host
