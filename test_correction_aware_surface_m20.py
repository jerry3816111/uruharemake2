import inspect
import threading
import time
import unittest
from unittest import mock

import uruha_adaptive_person_model as uapm
import uruha_functional_understanding as ufu
import uruha_personhood_loop as upl
import uruha_web_ui as web
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT, decision_for
from test_human_priority_scheduler_m19 import _TurnRuntime
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


EXPLICIT_CORRECTION = (
    "You misunderstood again. I only want you to wait for the result with me."
)
OLD_CLARIFIER = "寝てないのか、考え事で止まんないのか、まずそこだけどっち？"
EXPECTED_REPAIR = "あー、そこ読み違えた。結果来るまでうちも一緒に待っとく。"


def correction_decision():
    model = uapm.empty_model()
    _state, first = decision_for(AMBIGUOUS_INPUT, model, 1)
    model = uapm.set_pending_prediction(model, first, 1)
    model, feedback = uapm.observe_next_turn(model, EXPLICIT_CORRECTION, 2)
    hypothesis = ufu.build_user_mental_state_hypothesis(
        EXPLICIT_CORRECTION,
        actual_signal={"actual_intent": "chat", "actual_valence": 0.0},
        appraisal={},
        attention_frame={},
        turn_index=2,
        calibration_state={},
    )
    pragmatics = upl.build_human_pragmatic_understanding(
        EXPLICIT_CORRECTION,
        hypothesis=hypothesis,
        turn_index=2,
    )
    state = uapm.build_current_state(
        EXPLICIT_CORRECTION,
        pragmatics,
        hypothesis,
        {},
        model,
        turn_index=2,
        adaptive_feedback=feedback,
    )
    return model, feedback, state, uapm.decide_response(state, model)


class CorrectionAwareSurfaceM20Tests(unittest.TestCase):
    def test_explicit_correction_revokes_old_clarifier_and_selects_shared_wait(self):
        _model, feedback, state, decision = correction_decision()

        directive = decision["correction_aware_surface_m20"]
        self.assertEqual(feedback["status"], "contradicted")
        self.assertEqual(feedback["previous_policy_id"], "calibrate_need")
        self.assertEqual(feedback["explicit_target_policy"], "share_arousal")
        self.assertEqual(
            state["correction_directive_m20"]["authority"],
            "current_explicit_desired_response",
        )
        self.assertTrue(directive["authoritative"])
        self.assertEqual(directive["revoked_previous_policy"], "calibrate_need")
        self.assertTrue(directive["repeated_clarifier_blocked"])
        self.assertEqual(decision["selected"]["policy_id"], "share_arousal")
        self.assertEqual(decision["selected"]["core_message_jp"], EXPECTED_REPAIR)

    def test_surface_commit_forces_repair_and_forbids_revoked_variants(self):
        _model, _feedback, _state, decision = correction_decision()
        plan, trace = uapm.apply_decision_to_plan(
            {"intent": "chat", "scene": "casual", "core_message_jp": OLD_CLARIFIER},
            decision,
        )
        reply, surface = uapm.ensure_decision_reaches_visible_surface(
            OLD_CLARIFIER,
            plan,
        )

        self.assertTrue(trace["applied"])
        self.assertEqual(plan["response_mode"], "correction_repair")
        self.assertIn(OLD_CLARIFIER, plan["must_avoid"])
        self.assertEqual(reply, EXPECTED_REPAIR)
        self.assertTrue(surface["changed"])
        self.assertTrue(surface["policy_performed"])
        self.assertTrue(
            surface["correction_aware_surface_m20"]["forbidden_repetition_detected"]
        )

    def test_real_runtime_repairs_second_turn_without_another_general_plan(self):
        brain = _IsolatedContractBrain()
        first = brain.run_turn_debug(AMBIGUOUS_INPUT)
        repaired = brain.run_turn_debug(EXPLICIT_CORRECTION)

        self.assertEqual(first["logic"]["desired_response_policy_m18"], "calibrate_need")
        self.assertEqual(repaired["logic"]["desired_response_policy_m18"], "share_arousal")
        self.assertEqual(repaired["reply"], EXPECTED_REPAIR)
        self.assertNotEqual(repaired["reply"], OLD_CLARIFIER)
        self.assertTrue(
            repaired["logic"]["correction_aware_surface_m20"]["authoritative"]
        )
        labels = {row["label"] for row in repaired["runtime_trace"]["blackboard"]}
        self.assertIn("correction_aware_surface_m20", labels)
        self.assertIn("correction_surface_commit_m20", labels)

    def test_streaming_batches_japanese_and_only_full_commits_once(self):
        chunks = list(web._iter_reply_chunks(EXPECTED_REPAIR))
        self.assertGreaterEqual(len(chunks), 2)
        self.assertLessEqual(len(chunks), 5)
        self.assertEqual(chunks[-1], EXPECTED_REPAIR)

        runtime = _TurnRuntime()
        started = time.perf_counter() - 0.02
        with mock.patch.object(web, "RUNTIME", runtime):
            result = web._run_turn(
                "聞いてる？",
                False,
                frontend_enqueue_started=started,
                handler_started=started,
            )
            web._finalize_surface_delivery(
                result,
                started,
                started,
                time.perf_counter() - 0.01,
                stream_chunk_count=3,
                lightweight_payload_update_count=4,
                full_payload_update_count=1,
            )

        delivery = result["cognition_trace"]["runtime_trace"]["surface_delivery_m20"]
        self.assertEqual(delivery["stream_chunk_count"], 3)
        self.assertEqual(delivery["lightweight_payload_update_count"], 4)
        self.assertEqual(delivery["full_payload_update_count"], 1)
        self.assertFalse(delivery["full_cognitive_payload_during_partial_stream"])
        self.assertTrue(delivery["final_graph_commit_once"])

        source = inspect.getsource(web._submit_text_impl)
        partial_block = source.split("for partial in partials:", 1)[1].split(
            "_finalize_surface_delivery", 1
        )[0]
        self.assertIn("gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()", partial_block)
        self.assertNotIn('result["flow_html"]', partial_block)

    def test_graph_compares_stale_clarifier_with_m20_repair_and_delivery(self):
        _model, _feedback, _state, decision = correction_decision()
        directive = decision["correction_aware_surface_m20"]
        result = {
            "user_text": EXPLICIT_CORRECTION,
            "reply": EXPECTED_REPAIR,
            "runtime_trace": {
                "runtime_latency_m19": {
                    "schema": "uruha_runtime_latency_m19",
                    "frontend_queue_wait_seconds": 0.01,
                    "runtime_lock_wait_seconds": 0.0,
                    "brain_work_seconds": 0.9,
                    "surface_stream_seconds": 0.04,
                },
                "surface_delivery_m20": {
                    "schema": "uruha_lightweight_surface_delivery_m20",
                    "stream_chunk_count": 3,
                    "full_payload_update_count": 1,
                },
                "blackboard": [
                    {
                        "stage": "verify",
                        "label": "correction_aware_surface_m20",
                        "payload": directive,
                    },
                    {
                        "stage": "surface",
                        "label": "correction_surface_commit_m20",
                        "payload": directive,
                    },
                    {
                        "stage": "surface",
                        "label": "surface_delivery_m20",
                        "payload": {
                            "schema": "uruha_lightweight_surface_delivery_m20",
                            "stream_chunk_count": 3,
                            "full_payload_update_count": 1,
                        },
                    },
                ],
            },
        }

        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        labels = {node["label"] for node in graph["nodes"]}

        self.assertTrue(
            {
                "correction_aware_surface_m20",
                "correction_surface_commit_m20",
                "surface_delivery_m20",
            }.issubset(labels)
        )
        self.assertIn("CORRECTION-AWARE SURFACE COMMIT · M20", html)
        self.assertIn("撤銷舊假設", html)
        self.assertIn("輕量串流 3 段", html)
        self.assertIn("完整 cognition/graph payload 1 次", html)


if __name__ == "__main__":
    unittest.main()
