import inspect
import threading
import time
import unittest
from unittest import mock

import uruha_web_ui as web
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


class _BackgroundBrain:
    def __init__(self):
        self.calls = 0

    def run_background_cycle(self):
        self.calls += 1
        return {"goal": {"kind": "passive_decay"}, "memory_writes": []}


class _BoundedBackgroundBrain:
    def __init__(self):
        self.allow_model_maintenance = None

    def run_background_cycle(self, allow_model_maintenance=True):
        self.allow_model_maintenance = allow_model_maintenance
        return {"goal": {"kind": "three_speed_consolidation"}, "memory_writes": []}


def _manager(brain=None):
    manager = web.RuntimeManager.__new__(web.RuntimeManager)
    manager._brain = brain
    manager._lock = threading.Lock()
    manager._human_gate_lock = threading.Lock()
    manager._human_waiters = 0
    manager._scheduler_trace = {
        "schema": "uruha_human_priority_scheduler_m19",
        "human_waiters": 0,
        "background_status": "not_started",
        "last_decision": "startup",
        "contains_raw_dialogue": False,
    }
    manager._last_activity_at = 0.0
    return manager


class _TurnBrain:
    def run_turn_debug(self, user_text, input_context=None):
        return {
            "reply": "今はちゃんと聞いてる。",
            "logic": {"intent": "chat"},
            "memory_data": {},
            "runtime_trace": {
                "blackboard": [],
                "runtime_latency_m19": {
                    "schema": "uruha_runtime_latency_m19",
                    "target_seconds": 20.0,
                    "cognition_seconds": 0.001,
                },
            },
            "runtime_state": {},
        }


class _TurnRuntime:
    def __init__(self):
        self._brain = _TurnBrain()
        self._lock = threading.Lock()
        self._brain_load_trace = {"status": "ready", "elapsed_seconds": 0.0}

    def mark_activity(self):
        return None

    def get_brain(self):
        return self._brain

    def scheduler_trace(self):
        return {
            "schema": "uruha_human_priority_scheduler_m19",
            "human_waiters": 1,
            "last_decision": "human_admitted",
            "contains_raw_dialogue": False,
        }


class HumanPrioritySchedulerM19Tests(unittest.TestCase):
    def test_human_registration_blocks_new_background_admission(self):
        brain = _BackgroundBrain()
        manager = _manager(brain)

        started = manager.begin_human_turn()
        skipped = manager.run_background_once()

        self.assertGreater(started, 0.0)
        self.assertIsNone(skipped)
        self.assertEqual(brain.calls, 0)
        self.assertEqual(manager.scheduler_trace()["last_decision"], "human_waiting")

        manager.finish_human_turn()
        completed = manager.run_background_once()
        self.assertEqual(completed["goal"]["kind"], "passive_decay")
        self.assertEqual(brain.calls, 1)

    def test_background_and_proactive_poll_never_wait_for_busy_brain(self):
        brain = _BackgroundBrain()
        manager = _manager(brain)
        manager._lock.acquire()
        try:
            started = time.perf_counter()
            result = manager.run_background_once()
            elapsed = time.perf_counter() - started
        finally:
            manager._lock.release()

        self.assertIsNone(result)
        self.assertLess(elapsed, 0.05)
        self.assertEqual(manager.scheduler_trace()["last_decision"], "brain_busy")
        self.assertIn("acquire(blocking=False)", inspect.getsource(web.poll_proactive_turn))

    def test_web_background_uses_bounded_non_model_maintenance(self):
        brain = _BoundedBackgroundBrain()
        manager = _manager(brain)

        result = manager.run_background_once()

        self.assertEqual(result["goal"]["kind"], "three_speed_consolidation")
        self.assertFalse(brain.allow_model_maintenance)

    def test_turn_trace_separates_queue_lock_brain_and_surface(self):
        runtime = _TurnRuntime()
        enqueue_started = time.perf_counter() - 0.05
        handler_started = time.perf_counter() - 0.02
        with mock.patch.object(web, "RUNTIME", runtime):
            result = web._run_turn(
                "聞いてる？",
                False,
                frontend_enqueue_started=enqueue_started,
                handler_started=handler_started,
            )
            surface_started = time.perf_counter() - 0.01
            latency = web._finalize_surface_delivery(
                result,
                enqueue_started,
                handler_started,
                surface_started,
            )

        self.assertEqual(latency["schema"], "uruha_runtime_latency_m19")
        self.assertGreater(latency["frontend_queue_wait_seconds"], 0.0)
        self.assertGreaterEqual(latency["runtime_lock_wait_seconds"], 0.0)
        self.assertGreaterEqual(latency["brain_work_seconds"], 0.0)
        self.assertGreater(latency["surface_stream_seconds"], 0.0)
        self.assertTrue(latency["delivery_complete"])
        labels = [
            row["label"]
            for row in result["cognition_trace"]["runtime_trace"]["blackboard"]
        ]
        self.assertEqual(labels[0], "human_priority_scheduler_m19")
        self.assertIn("runtime_latency_m19", labels)

    def test_graph_and_comparison_card_show_actual_m19_segments(self):
        latency = {
            "schema": "uruha_runtime_latency_m19",
            "frontend_queue_wait_seconds": 0.012,
            "runtime_lock_wait_seconds": 0.003,
            "brain_work_seconds": 1.234,
            "surface_stream_seconds": 0.456,
            "delivery_complete": True,
        }
        result = {
            "user_text": "ねえ",
            "reply": "聞いてるって。",
            "runtime_trace": {
                "runtime_latency_m19": latency,
                "blackboard": [
                    {
                        "stage": "observe",
                        "label": "human_priority_scheduler_m19",
                        "payload": {
                            "schema": "uruha_human_priority_scheduler_m19",
                            "last_decision": "human_admitted",
                            "human_waiters": 1,
                        },
                    },
                    {
                        "stage": "observe",
                        "label": "runtime_latency_m19",
                        "payload": latency,
                    },
                ],
            },
        }

        html = render_memory_observatory(result)
        graph = collect_cognitive_graph(result)

        self.assertIn("HUMAN-PRIORITY COGNITIVE SCHEDULER · M19", html)
        self.assertIn("前端等待 0.012s", html)
        self.assertIn("腦內運算 1.234s", html)
        self.assertTrue(
            any(node["label"] == "human_priority_scheduler_m19" for node in graph["nodes"])
        )
        self.assertTrue(
            any(node["label"] == "runtime_latency_m19" for node in graph["nodes"])
        )

    def test_gradio_wiring_registers_human_before_queue_and_frees_poll(self):
        source = inspect.getsource(web.build_demo)
        main_source = inspect.getsource(web).split('if __name__ == "__main__":', 1)[1]

        self.assertIn("fn=begin_human_submission", source)
        self.assertIn('concurrency_id="human_turn_m19"', source)
        self.assertIn("proactive_poll_timer.tick", source)
        poll_block = source.split("proactive_poll_timer.tick", 1)[1].split(")", 1)[0]
        self.assertIn("queue=False", poll_block)
        self.assertIn("demo.queue(default_concurrency_limit=4)", main_source)


if __name__ == "__main__":
    unittest.main()
