#!/usr/bin/env bash
# Every Kunavo endpoint, raw. export KUNAVO_API_KEY=sk-kunavo-... first.
set -euo pipefail

BASE="https://api.kunavo.com/v1"
AUTH="Authorization: Bearer $KUNAVO_API_KEY"

# --- Discover models (OpenAI-shaped + a "kunavo" object per entry) ---------
curl -s "$BASE/models" -H "$AUTH" | head -40

# --- Chat (Claude / Gemini / GPT — swap the model string) -------------------
curl -s "$BASE/chat/completions" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "model": "claude-sonnet-4-6",
  "messages": [{"role": "user", "content": "Hello, Claude"}]
}'

# --- Image: text-to-image ----------------------------------------------------
curl -s "$BASE/images/generations" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "model": "nano-banana",
  "prompt": "A neon ramen stall in the rain, cinematic",
  "size": "1024x1024"
}'

# --- Image: edit (image-to-image) --------------------------------------------
curl -s "$BASE/images/edits" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "model": "nano-banana-edit",
  "prompt": "make the sky golden hour, keep the subject",
  "image": "https://example.com/source.png"
}'

# --- Video: submit async task, then poll -------------------------------------
curl -s "$BASE/videos" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "model": "veo-3",
  "prompt": "a slow push-in on a neon-lit alley in the rain",
  "duration": 8,
  "aspect_ratio": "16:9"
}'
# curl -s "$BASE/videos/<task_id>" -H "$AUTH"

# --- Music: submit async job, then poll ---------------------------------------
curl -s "$BASE/audio/music/jobs" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "model": "suno-v5",
  "prompt": "dreamy synthwave about writing code at 2am"
}'
# curl -s "$BASE/audio/music/jobs/<job_id>" -H "$AUTH"
