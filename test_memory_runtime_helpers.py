import unittest
import datetime
import uruha_memory_runtime as umr

class TestMemoryRuntimeHelpers(unittest.TestCase):
    def test_memory_tokens(self):
        text = "Hello world! 這是測試 Uruha_Memory."
        tokens = umr.memory_tokens(text)
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("這是測試", tokens)
        self.assertIn("uruha_memory", tokens)

    def test_clean_fact_value(self):
        val = " :： , 測試內容 .!? "
        cleaned = umr.clean_fact_value(val)
        self.assertEqual(cleaned, "測試內容")

    def test_profile_snapshot(self):
        profile = {
            "name": "Jerry",
            "likes": ["apple", "banana"],
            "dislikes": ["onion"],
            "favorites": ["programming"]
        }
        snapshot = umr.profile_snapshot(profile)
        self.assertEqual(snapshot["name"], "Jerry")
        self.assertEqual(snapshot["likes"], ["apple", "banana"])
        self.assertEqual(snapshot["dislikes"], ["onion"])
        self.assertEqual(snapshot["favorites"], ["programming"])

    def test_profile_summary(self):
        profile = {
            "name": "Jerry",
            "likes": ["apple"],
            "favorites": ["coding"]
        }
        summary = umr.profile_summary(profile)
        self.assertIn("Name=Jerry", summary)
        self.assertIn("Likes=apple", summary)
        self.assertIn("Favorites=coding", summary)

    def test_recent_dialogue_summary(self):
        turns = [
            {"user": "hi", "reply": "hello"},
            {"user": "how are you", "reply": "fine"}
        ]
        summary = umr.recent_dialogue_summary(turns)
        self.assertIn("User:hi -> Uruha:hello", summary)
        self.assertIn("User:how are you -> Uruha:fine", summary)

    def test_short_term_summary(self):
        buffer = [
            {"text": "Fact A", "strength": 0.5},
            {"text": "Fact B", "strength": 0.8}
        ]
        summary = umr.short_term_summary(buffer)
        self.assertIn("0.50:Fact A", summary)
        self.assertIn("0.80:Fact B", summary)

    def test_salience_score_basic(self):
        now = datetime.datetime.now()
        candidate = {
            "source": "short_term",
            "text": "test memory",
            "distance": 0.1,
            "metadata": {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S")}
        }
        query_tokens = ["test"]
        score = umr.salience_score(candidate, query_tokens, now)
        self.assertGreater(score, 0)

    def test_v2_distance_remains_monotonic_beyond_one(self):
        self.assertGreater(
            umr.distance_similarity(1.1, scoring_profile="v2"),
            umr.distance_similarity(1.8, scoring_profile="v2"),
        )
        self.assertGreater(umr.distance_similarity(1.8, scoring_profile="v2"), 0.0)
        self.assertEqual(umr.distance_similarity(1.1, scoring_profile="legacy"), 0.0)

    def test_v2_lexical_overlap_is_length_normalized(self):
        long_memory = "tea " + " ".join(f"noise{index}" for index in range(80))

        bonus = umr.lexical_overlap_bonus(
            ["tea", "favorite"],
            long_memory,
            scoring_profile="v2",
        )

        self.assertGreater(bonus, 0.0)
        self.assertLess(bonus, 0.45)

    def test_v2_self_relevance_requires_explicit_metadata(self):
        generic = {
            "source": "episode",
            "text": "User: remember my name",
            "metadata": {},
        }
        explicit = {
            "source": "episode",
            "text": "ordinary memory",
            "metadata": {"self_relevance": True},
        }

        self.assertEqual(umr.explicit_self_relevance_bonus(generic), 0.0)
        self.assertEqual(umr.explicit_self_relevance_bonus(explicit), 0.16)

    def test_legacy_profile_preserves_frozen_surface_word_heuristic(self):
        now = datetime.datetime(2024, 1, 2, 9, 0, 0)
        candidate = {
            "source": "episode",
            "text": "User: remember my name",
            "distance": 1.2,
            "metadata": {"timestamp": "2024-01-01 09:00:00"},
        }

        legacy = umr.attention_factors(
            candidate,
            ["remember", "name"],
            now,
            scoring_profile="legacy",
        )
        current = umr.attention_factors(
            candidate,
            ["remember", "name"],
            now,
            scoring_profile="v2",
        )

        self.assertEqual(legacy["self_relevance"], 0.16)
        self.assertEqual(current["self_relevance"], 0.0)
        self.assertEqual(legacy["similarity"], 0.0)
        self.assertGreater(current["similarity"], 0.0)
        
    def test_build_working_memory_top_k(self):
        candidates = [
            {"source": "wisdom", "text": "high score", "distance": 0.01},
            {"source": "knowledge", "text": "low score", "distance": 0.99},
            {"source": "short_term", "text": "mid score", "distance": 0.5}
        ]
        # wisdom source bias is 0.05, short_term is 0.28, knowledge is 0.0
        # Score calculation: (1.0 - distance) + source_bias + ...
        # wisdom: 0.99 + 0.05 = 1.04
        # knowledge: 0.01 + 0.0 = 0.01
        # short_term: 0.5 + 0.28 = 0.78
        
        # Note: salience_score also adds recency_bonus 0.4 for short_term if no timestamp
        # short_term: 0.5 + 0.28 + 0.4 = 1.18
        # wisdom: 0.99 + 0.05 = 1.04
        # knowledge: 0.01 + 0.0 = 0.01
        
        working_memory = umr.build_working_memory("test", candidates, working_memory_limit=2)
        self.assertEqual(len(working_memory), 2)
        self.assertEqual(working_memory[0]["text"], "mid score") # higher due to short_term bias + recency
        self.assertEqual(working_memory[1]["text"], "high score")

    def test_memory_speakability_allows_direct_recall(self):
        anchor = {
            "kind": "name",
            "value": "Jerry",
            "jp_anchor": "Jerry",
            "source_text": "Name=Jerry",
            "relevance": 0.5,
            "expected": True,
        }
        result = umr.assess_memory_speakability(anchor, user_input="你還記得我叫什麼嗎？", trust=50)
        self.assertEqual(result["label"], "explicit_ok")
        self.assertTrue(result["should_use_explicitly"])
        self.assertTrue(result["can_quote"])

    def test_memory_speakability_suppresses_sensitive_memory(self):
        anchor = {
            "kind": "context",
            "value": "password is 1234",
            "jp_anchor": "password",
            "source_text": "User told a password is 1234",
            "relevance": 0.9,
            "expected": True,
        }
        result = umr.assess_memory_speakability(anchor, user_input="你記得那件事嗎？", trust=80)
        self.assertEqual(result["label"], "suppressed_sensitive")
        self.assertFalse(result["should_use_explicitly"])
        self.assertFalse(result["can_quote"])

    def test_memory_speakability_keeps_contextual_memory_background_only(self):
        anchor = {
            "kind": "context",
            "value": "ramen",
            "jp_anchor": "ラーメン",
            "source_text": "User once had stomach pain after ramen",
            "relevance": 0.55,
            "expected": False,
        }
        result = umr.assess_memory_speakability(anchor, user_input="今日は何食べようかな", trust=50)
        self.assertEqual(result["label"], "background_only")
        self.assertFalse(result["should_use_explicitly"])
        self.assertLess(result["gravity_multiplier"], 1.0)

if __name__ == "__main__":
    unittest.main()
