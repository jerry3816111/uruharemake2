import unittest

from uruha_memory_observatory import (
    MEMORY_OBSERVATORY_CSS,
    collect_memory_nodes,
    render_memory_observatory,
)


class TeacherMemoryObservatoryV215Tests(unittest.TestCase):
    def _fixture(self):
        return {
            "memory_data": {
                "working_memory_items": [
                    {
                        "trace_id": "stored:profile:tea",
                        "source": "profile",
                        "text": "使用者喜歡草莓牛奶",
                        "score": 0.92,
                    }
                ],
                "memory_provenance": {
                    "retrieved_candidate_count": 3,
                    "candidate_count": 2,
                    "candidate_pool": [
                        {
                            "trace_id": "stored:profile:tea",
                            "source": "profile",
                            "text": "使用者喜歡草莓牛奶",
                            "score": 0.92,
                            "rank": 1,
                            "selected": True,
                        },
                        {
                            "trace_id": "stored:episode:old",
                            "source": "episode",
                            "text": "<script>alert('no')</script>",
                            "score": 0.31,
                            "rank": 2,
                            "selected": False,
                        },
                    ],
                    "selected_working_memory_trace_ids": ["stored:profile:tea"],
                    "passed_to_leftbrain_trace_ids": [
                        "stored:profile:tea",
                        "derived:procedural:support",
                    ],
                    "passed_to_leftbrain": [
                        {
                            "trace_id": "derived:procedural:support",
                            "source": "procedural",
                            "text": "先確認對方的情緒，再提出一個具體步驟",
                            "channel": "direct_procedural",
                            "score": 0.66,
                        }
                    ],
                },
            },
            "runtime_trace": {
                "memory_writes": [
                    {
                        "layer": "episodic_memory",
                        "kind": "turn_episode",
                        "summary": "記住這次飲料偏好回想",
                    }
                ]
            },
        }

    def test_renders_live_pipeline_constellation_and_writeback(self):
        html = render_memory_observatory(self._fixture())
        self.assertIn("Memory Observatory", html)
        self.assertIn("記憶星圖", html)
        self.assertIn("使用者喜歡草莓牛奶", html)
        self.assertIn("is-selected", html)
        self.assertIn("is-passed", html)
        self.assertIn("episodic_memory", html)
        self.assertIn("記住這次飲料偏好回想", html)

    def test_direct_passed_memory_is_not_lost_when_absent_from_candidate_pool(self):
        nodes = collect_memory_nodes(self._fixture())
        by_id = {row["trace_id"]: row for row in nodes}
        self.assertIn("derived:procedural:support", by_id)
        self.assertTrue(by_id["derived:procedural:support"]["passed"])
        self.assertEqual(by_id["derived:procedural:support"]["source_key"], "procedural")

    def test_runtime_memory_text_is_html_escaped(self):
        html = render_memory_observatory(self._fixture())
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_source_cannot_inject_css_class(self):
        fixture = self._fixture()
        fixture["memory_data"]["memory_provenance"]["candidate_pool"][1]["source"] = 'x\" onmouseover="bad'
        nodes = collect_memory_nodes(fixture)
        by_id = {row["trace_id"]: row for row in nodes}
        self.assertEqual(by_id["stored:episode:old"]["source_key"], "unknown")

    def test_empty_state_and_reduced_motion_are_available(self):
        html = render_memory_observatory({})
        self.assertIn("尚無記憶節點", html)
        self.assertIn("prefers-reduced-motion", MEMORY_OBSERVATORY_CSS)


if __name__ == "__main__":
    unittest.main()
