# Suno V5 music generation with job polling. $0.09 per generation request;
# one request returns ~2 track variations for a single charge.
# Supports plain-prompt, custom lyrics + style, and instrumental modes.
#   export KUNAVO_API_KEY=sk-kunavo-...
import os
import time

import requests

BASE = "https://api.kunavo.com/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['KUNAVO_API_KEY']}"}

# 1. Submit an async music job
job = requests.post(
    f"{BASE}/audio/music/jobs",
    headers=HEADERS,
    json={
        "model": "suno-v5",
        "prompt": "dreamy synthwave about writing code at 2am, female vocals",
    },
    timeout=60,
).json()
job_id = job["id"]  # "msc_abc..."
status = job["status"]  # "queued"
print(f"job {job_id} submitted, polling...")

# 2. Poll until terminal (recommended cadence: 5s, backing off to 30s)
while status not in ("completed", "failed"):
    time.sleep(10)
    j = requests.get(f"{BASE}/audio/music/jobs/{job_id}", headers=HEADERS, timeout=60).json()
    status = j["status"]
    print(f"  status: {status}")

if status == "failed":
    raise SystemExit(f"generation failed: {j['error']['message']}")
# Suno returns ~2 tracks per request for a single charge.
for track in j["output"]["tracks"]:
    print(track["url"])  # temporary URLs — download and re-host
