import unittest

from run_rightbrain_4b_guarded_retry_v34_1 import _select_attempt


def _attempt(raw_pass, hits, private=False, hard=False, reason_count=0):
    return {
        "raw_reply": "x",
        "score": {
            "current_gate_raw_pass": raw_pass,
            "semantic_group_hit_count": hits,
            "private_memory_intrusion": private,
            "hard_surface_failure": hard,
            "current_gate_rejection_reasons": ["x"] * reason_count,
        },
    }


class RightBrain4BGuardedRetryV341Test(unittest.TestCase):
    def test_passing_first_attempt_is_never_replaced(self):
        source, selected = _select_attempt(_attempt(True, 2), _attempt(True, 3))
        self.assertEqual(source, "first")
        self.assertEqual(selected["score"]["semantic_group_hit_count"], 2)

    def test_passing_retry_replaces_failed_first_attempt(self):
        source, selected = _select_attempt(_attempt(False, 2, reason_count=1), _attempt(True, 3))
        self.assertEqual(source, "retry")
        self.assertTrue(selected["score"]["current_gate_raw_pass"])

    def test_failed_candidates_use_frozen_semantic_first_order(self):
        source, _ = _select_attempt(
            _attempt(False, 1, reason_count=1),
            _attempt(False, 2, reason_count=2),
        )
        self.assertEqual(source, "retry")


if __name__ == "__main__":
    unittest.main()
