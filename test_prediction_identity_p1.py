from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import uruha_adaptive_person_model as adaptive
import uruha_prediction_identity_p1 as identity
from test_adaptive_person_model_m16 import decision_for
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph


class PredictionIdentityTests(unittest.TestCase):
    def setUp(self):
        # Install only for this test, preserving the caller's complete overlay
        # stack. This suite must not alter frozen tests collected in the process.
        for name in ("_normalise_model", "decide_response", "set_pending_prediction"):
            context = patch.object(adaptive, name, getattr(adaptive, name))
            context.start()
            self.addCleanup(context.stop)
        identity.install_prediction_identity_p1()

    def event(self, model, text="我需要一個現在能做的方法。", turn=1):
        _, decision = decision_for(text, model, turn)
        return adaptive.set_pending_prediction(model, decision, turn), decision

    def test_restart_repeated_input_preserves_completed_event_and_routes_new_feedback(self):
        model, first = self.event(adaptive.empty_model())
        model, _ = adaptive.observe_next_turn(model, "對就是這樣。", 2)
        prior = deepcopy(model["outcome_calibration_ledger_m27"][0])
        self.assertEqual(prior["result_status"], "supported")
        with tempfile.TemporaryDirectory(prefix="uruha-p1-") as directory:
            path = Path(directory) / "adaptive.json"
            adaptive.save_model(path, model)
            loaded, status = adaptive.load_model(path)
            self.assertEqual(status["status"], "loaded")
            restored, second = self.event(loaded)
        self.assertNotEqual(first["prediction_id"], second["prediction_id"])
        self.assertEqual(restored["outcome_calibration_ledger_m27"][0], prior)
        self.assertEqual(len(restored["outcome_calibration_ledger_m27"]), 2)
        final, _ = adaptive.observe_next_turn(restored, "不是要方法，我只是想讓你聽我說。", 2)
        self.assertEqual(final["outcome_calibration_ledger_m27"][0], prior)
        self.assertEqual(final["outcome_calibration_ledger_m27"][1]["result_status"], "contradicted")

    def test_identical_pending_is_idempotent_and_resolved_replay_is_rejected(self):
        model, decision = self.event(adaptive.empty_model())
        retry = adaptive.set_pending_prediction(model, decision, 1)
        self.assertEqual(retry, adaptive._normalise_model(model))
        changed = deepcopy(decision)
        changed["selected"]["policy_id"] = "listen_presence"
        with self.assertRaisesRegex(ValueError, "changed event content"):
            adaptive.set_pending_prediction(model, changed, 1)
        completed, _ = adaptive.observe_next_turn(model, "對就是這樣。", 2)
        with self.assertRaisesRegex(ValueError, "stale prediction"):
            adaptive.set_pending_prediction(completed, decision, 1)

    def test_decision_content_is_unchanged_and_does_not_mutate_input(self):
        model = adaptive.empty_model()
        before_model = deepcopy(model)
        state, wrapped = decision_for("今は方法はいらない。ただ聞いて。", model, 1)
        original = identity._previous_decide(state, model)
        self.assertNotEqual(wrapped.pop("prediction_id"), original.pop("prediction_id"))
        self.assertFalse(wrapped.pop(identity.TRACE)["policy_or_surface_changed"])
        self.assertEqual(wrapped, original)
        self.assertEqual(model, before_model)

    def test_legacy_record_migrates_and_sequence_survives_ledger_eviction(self):
        model = adaptive.empty_model()
        with tempfile.TemporaryDirectory(prefix="uruha-p1-sequence-") as directory:
            path = Path(directory) / "adaptive.json"
            identifiers = set()
            # Shorten retention solely to exercise the real eviction code.
            with patch.object(adaptive, "M27_MAX_LEDGER_ENTRIES", 2):
                for index in range(6):
                    model, decision = self.event(model)
                    identifiers.add(decision["prediction_id"])
                    model, _ = adaptive.observe_next_turn(model, "今天下雨。", 2)
                    adaptive.save_model(path, model)
                    model, _ = adaptive.load_model(path)
                    self.assertEqual(model[identity.SEQUENCE], index + 1)
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("我需要一個現在能做的方法", raw)
            self.assertEqual(len(identifiers), 6)
            self.assertEqual(len(model["outcome_calibration_ledger_m27"]), 2)
            model.pop(identity.SEQUENCE)
            self.assertEqual(adaptive._normalise_model(model)[identity.SEQUENCE], 6)

    def test_unknown_does_not_become_support_and_invalid_sequence_is_rejected(self):
        model, decision = self.event(adaptive.empty_model())
        model, _ = adaptive.observe_next_turn(model, "今日は雨だね。", 2)
        self.assertEqual(model["outcome_calibration_ledger_m27"][0]["result_status"], "uncertain")
        again, _ = self.event(model)
        self.assertEqual(again["outcome_calibration_ledger_m27"][0]["result_status"], "uncertain")
        broken = deepcopy(again)
        broken[identity.SEQUENCE] = -1
        with self.assertRaises(ValueError):
            adaptive._normalise_model(broken)
        skipped = deepcopy(decision)
        skipped["prediction_id"] = "p1-100-0123456789abcdef"
        with self.assertRaisesRegex(ValueError, "skipped"):
            adaptive.set_pending_prediction(adaptive.empty_model(), skipped, 1)

    def test_legacy_completed_entry_is_not_reopened_and_suppressed_action_does_not_commit(self):
        model = adaptive.empty_model()
        state, _ = decision_for("我需要一個現在能做的方法。", model, 1)
        legacy = identity._previous_decide(state, model)
        model = identity._previous_pending(model, legacy, 1)
        model, _ = adaptive.observe_next_turn(model, "對就是這樣。", 2)
        old = deepcopy(model["outcome_calibration_ledger_m27"])
        with self.assertRaisesRegex(ValueError, "stale legacy"):
            adaptive.set_pending_prediction(model, legacy, 1)
        _, fresh = decision_for("我需要一個現在能做的方法。", model, 1)
        suppressed = deepcopy(fresh)
        suppressed["selected"] = None
        skipped = adaptive.set_pending_prediction(model, suppressed, 1)
        self.assertEqual(skipped[identity.SEQUENCE], 0)
        self.assertEqual(skipped["outcome_calibration_ledger_m27"], old)
        committed = adaptive.set_pending_prediction(skipped, fresh, 1)
        self.assertEqual(committed[identity.SEQUENCE], 1)
        self.assertEqual(committed["outcome_calibration_ledger_m27"][0], old[0])

    def test_mock_runtime_restart_uses_product_ids_and_existing_graph(self):
        brain = _IsolatedContractBrain()
        first = brain.run_turn_debug("我從早上就一直坐不住，腦子停不下來。")
        brain.run_turn_debug("不是要方法，我只是想讓你聽我說。")
        stored = deepcopy(brain.runtime.adaptive_person_model)
        prior = deepcopy(stored["outcome_calibration_ledger_m27"])
        restarted = _IsolatedContractBrain()
        restarted.runtime.set_adaptive_person_model(adaptive._normalise_model(stored))
        second = restarted.run_turn_debug("我從早上就一直坐不住，腦子停不下來。")
        rows = restarted.runtime.adaptive_person_model["outcome_calibration_ledger_m27"]
        first_id = first["logic"]["desired_response_decision_m18"]["prediction_id"]
        second_id = second["logic"]["desired_response_decision_m18"]["prediction_id"]
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(rows[0], prior[0])
        graph = collect_cognitive_graph(second)
        serialized = json.dumps(graph, ensure_ascii=False)
        self.assertIn("causal_outcome_calibration_ledger_m27", serialized)
        self.assertRegex(second["reply"], r"[ぁ-んァ-ン]")
        self.assertNotIn("prediction_identity_p1", second["reply"])


if __name__ == "__main__":
    unittest.main()
