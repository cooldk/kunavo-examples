import copy
import unittest

from recovery import POLL_BUDGET, next_action, observe, prepare


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = prepare({"model": "suno-v5", "prompt": "piano"}, "demo-key", 1000)

    def test_lost_submit_response_retains_key_and_payload(self):
        first = next_action(self.state, 1000)
        retry = next_action(self.state, 1010)
        self.assertEqual(first, retry)
        self.assertEqual(retry["idempotency_key"], "demo-key")

    def test_known_id_only_polls_even_after_replay_budget(self):
        state = observe(self.state, {"id": "msc_demo", "status": "queued"})
        action = next_action(state, 10000)
        self.assertEqual(action["method"], "GET")
        self.assertEqual(action["path"], "/v1/audio/music/jobs/msc_demo")

    def test_unknown_id_expiry_and_clock_rollback_require_review(self):
        for now in [999, 4600, float("nan")]:
            self.assertEqual(next_action(self.state, now)["action"], "manual_review")

    def test_changed_payload_is_not_replayed(self):
        self.state["payload"]["prompt"] = "different song"
        self.assertEqual(next_action(self.state, 1010)["reason"], "payload_changed")

    def test_failure_does_not_automatically_create_new_generation(self):
        state = observe(self.state, {"id": "msc_demo", "status": "failed"})
        self.assertEqual(next_action(state, 1010)["action"], "inspect_failure")

    def test_completed_archived_and_temporary_outputs_are_distinct(self):
        for archived, action in [(True, "record_manifest"), (False, "archive_outputs")]:
            response = {"id": "msc_demo", "status": "completed", "output": {
                "archived": archived, "tracks": [{"url": "https://example.com/song.mp3"}]}}
            state = observe(self.state, response)
            self.assertEqual(next_action(state, 1010)["action"], action)

    def test_missing_output_never_claims_completion(self):
        for output in [None, {}, {"archived": True, "tracks": []},
                       {"archived": "false", "tracks": [{"url": "https://example.com/song"}]},
                       {"archived": True, "tracks": [{"url": None}]}]:
            state = observe(self.state, {"id": "msc_demo", "status": "completed", "output": output})
            self.assertEqual(next_action(state, 1010)["reason"], "incomplete_output")

    def test_polling_is_bounded_and_does_not_resubmit(self):
        state = observe(self.state, {"id": "msc_demo", "status": "queued"})
        waits = []
        for _ in range(POLL_BUDGET):
            waits.append(next_action(state, 1010)["wait_seconds"])
            state = observe(state, {"id": "msc_demo", "status": "in_progress"})
        self.assertEqual(waits[:4], [5, 10, 20, 30])
        self.assertLessEqual(max(waits), 30)
        self.assertEqual(next_action(state, 1010)["action"], "pause_polling")

    def test_invalid_mismatched_or_regressing_response_is_rejected(self):
        queued = observe(self.state, {"id": "msc_demo", "status": "queued"})
        for response in [{"status": "queued"}, {"id": "msc_other", "status": "queued"},
                         {"id": "msc_demo", "status": "unexpected"}]:
            with self.assertRaises(ValueError):
                observe(queued, response)
        failed_response = {"id": "msc_demo", "status": "failed"}
        failed = observe(queued, failed_response)
        self.assertEqual(observe(failed, failed_response), failed)
        with self.assertRaises(ValueError):
            observe(failed, {"id": "msc_demo", "status": "queued"})

    def test_prepare_copies_payload_and_rejects_invalid_keys(self):
        payload = copy.deepcopy(self.state["payload"])
        prepared = prepare(payload, "key", 1000)
        payload["prompt"] = "changed"
        self.assertEqual(prepared["payload"]["prompt"], "piano")
        for key in ["", " ", "x" * 129, None]:
            with self.assertRaises(ValueError):
                prepare(payload, key, 1000)


if __name__ == "__main__":
    unittest.main()
