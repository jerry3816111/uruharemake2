import os
import re
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_test_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        clean_env["URUHA_SKIP_AUTO_VENV"] = "1"
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_test_python()
os.environ["URUHA_SKIP_AUTO_VENV"] = "1"

from uruha_brain_mac import LeftBrain


def _story_prompt(question, options=None, body=None):
    body = body or "Story: Xiao Hong wants to go out, but another person has a different concern."
    options = options or {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D",
    }
    option_lines = "\n".join(f"{key}. {value}" for key, value in options.items())
    return f"{body}\n\nQuestion: {question}\n{option_lines}"


class TestSocialReasoningProfiles(unittest.TestCase):
    def setUp(self):
        self.left = LeftBrain(client_logic=None)

    def test_persuasion_question_uses_persuasion_focus(self):
        prompt = _story_prompt(
            "How does Xiao Hong persuade her dad?",
            body="Story: Dad thinks the amusement park will be too noisy on weekends.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["focus"], "persuasion_strategy")
        self.assertTrue(profile["prefer_fallback_frame"])
        self.assertEqual(self.left._extract_story_actor_name(prompt), "Xiao Hong")

    def test_hidden_emotion_question_uses_hidden_emotion_focus(self):
        prompt = _story_prompt(
            "What are Xinxin's real feelings?",
            body="Story: Xinxin says her stomach hurts, but she is actually worried about missing a party.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertEqual(profile["focus"], "hidden_emotion")
        self.assertTrue(profile["prefer_fallback_frame"])

    def test_scalar_quantity_question_uses_quantity_focus(self):
        prompt = _story_prompt(
            "Before Laura calls you, how many of these 5 letters do you think contain checks?",
            body="Story: Laura has opened three letters and seen checks in two of them.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertEqual(profile["focus"], "scalar_quantity_inference")
        self.assertTrue(profile["prefer_fallback_frame"])

    def test_short_social_knowledge_prompt_is_not_dropped(self):
        prompt = _story_prompt(
            "Does Xiao Zhang know that Xiao Wang does not want to get married for the time being?",
            body="Story: Xiao Wang has told only a few close friends that she does not want to get married for now.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["focus"], "knowledge_state_social")

    def test_completion_after_action_focus_detected(self):
        prompt = _story_prompt(
            "What does Sara do after she completes the production of the promotional video?",
            body="Story: Sara pauses her own plans to finish a promotional video for the team.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertEqual(profile["focus"], "completion_after_action")
        self.assertTrue(profile["prefer_fallback_frame"])

    def test_fallback_frame_for_quantity_avoids_option_letters(self):
        prompt = _story_prompt(
            "Please ask, after Xiao Ling looks, how many baguettes does she guess?",
            body="Story: Xiao Ling can only see some of the breads and must estimate the rest.",
        )
        frame = self.left._build_social_reasoning_frame(prompt)
        self.assertEqual(frame["focus"], "scalar_quantity_inference")
        self.assertIn("最低限", frame["decision_rule"])
        self.assertNotRegex(frame["best_option_shape"], r"\\b[A-D]\\b")
        self.assertEqual(frame["main_actor"], "Xiao Ling")

    def test_question_line_ignores_option_text_with_question_mark(self):
        prompt = _story_prompt(
            "How does Xiao Hong persuade her dad?",
            body="Story: Dad dislikes noise.",
            options={
                "A": "Use data.",
                "B": "Say it is her special wish.",
                "C": "Go somewhere else.",
                "D": "\"How about we go early?\"",
            },
        )
        self.assertEqual(
            self.left._story_question_line(prompt),
            "Question: How does Xiao Hong persuade her dad?",
        )

    def test_reaction_questions_map_to_emotion(self):
        prompt = _story_prompt(
            "What is Zhang Tingting's reaction to Mr. Zhao's piano concert?",
            body="Story: Zhang Tingting is a music lover and learns the concert is in memory of Mr. Zhao's late wife.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertEqual(profile["focus"], "emotion_attribution")

    def test_attention_action_prompt_is_not_left_as_generic_belief(self):
        prompt = _story_prompt(
            "What does Xiao Ming most likely do?",
            body="Story: Wang Lei returns, sees three toys on a tray, says 'look at that toy', and asks Xiao Ming to pass it to him.",
        )
        profile = self.left._story_reasoning_profile(prompt)
        self.assertEqual(profile["focus"], "attention_reasoning")


if __name__ == "__main__":
    unittest.main()
