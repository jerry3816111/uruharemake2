import inspect
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import uruha_brain_mac as brain_runtime
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


M19_SLOW_INPUT = "Now answer after all those background ticks. Say you are here."


class _SlowCompletion:
    def create(self, **_kwargs):
        time.sleep(0.03)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
        )


class _SlowClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=_SlowCompletion())


class BoundedSlowPathPlannerM21Tests(unittest.TestCase):
    def test_retained_m19_presence_turn_skips_general_planner(self):
        brain = _IsolatedContractBrain()

        result = brain.run_turn_debug(M19_SLOW_INPUT)
        trace = result["logic"]["bounded_slow_path_m21"]

        self.assertEqual(result["reply"], "うん、ここにいるよ。")
        self.assertEqual(brain.left_brain.think_calls, 0)
        self.assertEqual(trace["route"], "bounded_simple_presence")
        self.assertEqual(trace["status"], "completed_without_general_model")
        self.assertEqual(trace["general_llm_planner_calls_saved"], 1)
        self.assertFalse(trace["model_call_attempted"])
        self.assertTrue(trace["budget_met"])
        self.assertLess(trace["stage_seconds"]["cognitive_total"], 1.0)
        labels = {row["label"] for row in result["runtime_trace"]["blackboard"]}
        self.assertIn("bounded_slow_path_planner_m21", labels)

    def test_presence_route_accepts_chinese_and_japanese_but_not_generic_ambiguity(self):
        for text in ("你還在嗎？", "まだいる？"):
            brain = _IsolatedContractBrain()
            result = brain.run_turn_debug(text)
            self.assertEqual(result["reply"], "うん、ここにいるよ。")
            self.assertEqual(
                result["logic"]["bounded_slow_path_m21"]["route"],
                "bounded_simple_presence",
            )
            self.assertEqual(brain.left_brain.think_calls, 0)

        brain = _IsolatedContractBrain()
        result = brain.run_turn_debug("I have several conflicting goals and need to reason through them.")
        self.assertEqual(result["logic"]["bounded_slow_path_m21"]["route"], "full_planner")
        self.assertEqual(brain.left_brain.think_calls, 1)

    def test_full_planner_discards_a_response_that_exceeds_the_budget(self):
        planner = brain_runtime.LeftBrain(_SlowClient())
        memory = {
            "working_memory_summary": "none",
            "procedural_guidance_summary": "none",
            "episodes": "none",
            "wisdom": "none",
            "profile": "none",
            "recent_dialogue": "none",
        }
        with mock.patch.object(planner, "_rule_based_plan", return_value=None), mock.patch.object(
            brain_runtime,
            "LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS",
            0.01,
        ):
            selected = planner.think(
                "A deliberately complex holdout request.",
                memory,
                {"mood": 0, "trust": 50},
                force_general_planner=True,
            )

        trace = selected["bounded_slow_path_m21"]
        self.assertEqual(trace["route"], "full_planner")
        self.assertEqual(trace["status"], "budget_fallback")
        self.assertTrue(trace["model_call_attempted"])
        self.assertFalse(trace["model_call_completed"])
        self.assertTrue(trace["fallback_used"])
        self.assertTrue(trace["forced_general_planner"])
        self.assertGreaterEqual(trace["planner_seconds"], 0.01)
        self.assertIn("捨てたくない", selected["core_message_jp"])

    def test_runtime_uses_no_retry_and_per_call_timeout(self):
        init_source = inspect.getsource(brain_runtime.UruhaBrainV4_Mac.__init__)
        think_source = inspect.getsource(brain_runtime.LeftBrain.think)

        self.assertIn("max_retries=0", init_source)
        self.assertIn("timeout=LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS", think_source)

    def test_graph_shows_route_budget_and_retains_m20_delivery(self):
        trace = {
            "schema": "uruha_bounded_slow_path_planner_m21",
            "route": "bounded_simple_presence",
            "status": "completed_without_general_model",
            "budget_seconds": 8.0,
            "model_call_attempted": False,
            "budget_met": True,
            "stage_seconds": {
                "perception_and_user_model": 0.12,
                "route_and_base_plan": 0.001,
                "post_plan_guards_and_trace": 0.03,
                "cognitive_total": 0.151,
            },
        }
        result = {
            "user_text": M19_SLOW_INPUT,
            "reply": "うん、ここにいるよ。",
            "runtime_trace": {
                "bounded_slow_path_m21": trace,
                "runtime_latency_m19": {
                    "schema": "uruha_runtime_latency_m19",
                    "frontend_queue_wait_seconds": 0.01,
                    "runtime_lock_wait_seconds": 0.0,
                    "brain_work_seconds": 0.4,
                    "surface_stream_seconds": 0.1,
                },
                "surface_delivery_m20": {
                    "schema": "uruha_lightweight_surface_delivery_m20",
                    "stream_chunk_count": 2,
                    "full_payload_update_count": 1,
                },
                "blackboard": [
                    {
                        "stage": "plan",
                        "label": "bounded_slow_path_planner_m21",
                        "payload": trace,
                    }
                ],
            },
        }

        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)

        self.assertIn(
            "bounded_slow_path_planner_m21",
            {node["label"] for node in graph["nodes"]},
        )
        self.assertIn("BOUNDED SLOW-PATH PLANNER · M21", html)
        self.assertIn("M19 保留的真實反例是腦內運算 57.404 秒", html)
        self.assertIn("route bounded_simple_presence", html)
        self.assertIn("general model skipped", html)
        self.assertIn("完整 cognition/graph payload 1 次", html)


if __name__ == "__main__":
    unittest.main()
