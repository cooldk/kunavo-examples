"""Offline recovery decisions for an async music job. No HTTP calls or credentials."""
import copy
import hashlib
import json
import math

STATUSES = {"queued", "in_progress", "completed", "failed"}
REPLAY_BUDGET_SECONDS = 3600  # Local conservative policy, NOT the server's TTL.
POLL_BUDGET = 12


def fingerprint(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def prepare(payload, key, now):
    """Persist this record BEFORE the first POST; keep it tied to one account."""
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValueError("A nonempty idempotency key of at most 128 characters is required")
    if not isinstance(payload, dict) or not payload.get("model") or not payload.get("prompt"):
        raise ValueError("payload must include model and prompt")
    if not math.isfinite(now):
        raise ValueError("now must be finite")
    payload = copy.deepcopy(payload)
    return {"payload": payload, "payload_sha256": fingerprint(payload),
            "key": key.strip(), "first_attempt_at": now, "task_id": None,
            "response": None, "poll_attempts": 0}


def observe(state, response):
    """Record a successful submit/poll response; transport errors do not erase state."""
    task_id = response.get("id")
    if not isinstance(task_id, str) or not task_id.startswith("msc_") or len(task_id) <= 4:
        raise ValueError("Missing/invalid music task id: reconcile; do not start a new job")
    if state["task_id"] and task_id != state["task_id"]:
        raise ValueError("Response belongs to another task")
    if response.get("status") not in STATUSES:
        raise ValueError("Unknown task status")
    previous = state["response"]
    if previous and previous["status"] in {"completed", "failed"}:
        if response != previous:
            raise ValueError("Conflicting response after terminal state; reconcile")
        return copy.deepcopy(state)
    updated = copy.deepcopy(state)
    updated["poll_attempts"] += int(state["task_id"] is not None)
    updated["task_id"] = task_id
    updated["response"] = copy.deepcopy(response)
    return updated


def next_action(state, now):
    """Return a plan, never execute it. Input is trusted local state, not arbitrary JSON."""
    if fingerprint(state["payload"]) != state["payload_sha256"]:
        return {"action": "manual_review", "reason": "payload_changed"}
    response = state["response"]
    if response and response["status"] == "failed":
        return {"action": "inspect_failure", "task_id": state["task_id"]}
    if response and response["status"] == "completed":
        output = response.get("output") or {}
        tracks = output.get("tracks")
        if not isinstance(tracks, list) or not tracks or any(
            not isinstance(t, dict) or not isinstance(t.get("url"), str)
            or not t["url"].startswith("https://") for t in tracks
        ) or not isinstance(output.get("archived"), bool):
            return {"action": "manual_review", "reason": "incomplete_output"}
        return {"action": "record_manifest" if output["archived"] else "archive_outputs",
                "task_id": state["task_id"], "track_count": len(tracks)}
    if state["task_id"]:
        if state["poll_attempts"] >= POLL_BUDGET:
            return {"action": "pause_polling", "task_id": state["task_id"]}
        return {"action": "poll", "method": "GET",
                "path": "/v1/audio/music/jobs/" + state["task_id"],
                "wait_seconds": min(30, 5 * 2 ** min(state["poll_attempts"], 3))}
    age = now - state["first_attempt_at"]
    if not math.isfinite(age) or age < 0 or age >= REPLAY_BUDGET_SECONDS:
        return {"action": "manual_review", "reason": "unknown_submission_outside_local_budget"}
    return {"action": "submit_or_replay_same_key", "method": "POST",
            "path": "/v1/audio/music/jobs", "idempotency_key": state["key"],
            "payload_sha256": state["payload_sha256"]}


def demo():
    # Synthetic timestamps, task ids and URLs. No customer's music or logs.
    initial = prepare({"model": "suno-v5", "prompt": "gentle instrumental piano"},
                      "demo-song-001", 1000)
    queued = observe(initial, {"id": "msc_demo", "status": "queued"})
    failed = observe(queued, {"id": "msc_demo", "status": "failed",
                              "error": {"message": "synthetic failure"}})
    completed = observe(queued, {"id": "msc_demo", "status": "completed",
                                "output": {"archived": False,
                                           "tracks": [{"url": "https://example.com/demo.mp3"}]}})
    exhausted = copy.deepcopy(queued)
    exhausted["poll_attempts"] = POLL_BUDGET
    cases = [("lost_submit_response", initial, 1010), ("known_task", queued, 1010),
             ("terminal_failure", failed, 1010), ("archive_missing", completed, 1010),
             ("unknown_after_budget", initial, 4600), ("poll_budget_reached", exhausted, 1010)]
    return [{"scenario": name, **next_action(state, now)} for name, state, now in cases]


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
