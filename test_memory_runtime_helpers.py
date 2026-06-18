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
