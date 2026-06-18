import os
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

from run_formal_brain_benchmarks import _symbolic_social_reasoning_choice


class TestBenchmarkSymbolicSelector(unittest.TestCase):
    def test_family_persuasion_prefers_special_wish(self):
        letter, mode = _symbolic_social_reasoning_choice(
            "Persuasion Story Task",
            "Xiao Hong is a 6-year-old child. Dad thinks the amusement park has a lot of noise.",
            "How does Xiao Hong persuade her dad?",
            {
                "A": "Look up noise-reduction measures.",
                "B": "Tell dad it is a very special wish and she really wants to go.",
                "C": "Go somewhere else.",
                "D": "Go early in the morning when it is quieter.",
            },
            {"focus": "persuasion_strategy"},
        )
        self.assertEqual(letter, "B")
        self.assertEqual(mode, "symbolic_persuasion_family_wish")

    def test_workplace_persuasion_prefers_transition_plan(self):
        letter, mode = _symbolic_social_reasoning_choice(
            "Persuasion Story Task",
            "Li Na wants to transfer from the sales department to the marketing department and must convince her boss.",
            "How does Li Na convince her boss?",
            {
                "A": "Talk about retention.",
                "B": "Propose a detailed plan for a smooth transition without affecting operations.",
                "C": "Explain transferable skills.",
                "D": "Show understanding of marketing trends.",
            },
            {"focus": "persuasion_strategy"},
        )
        self.assertEqual(letter, "B")
        self.assertEqual(mode, "symbolic_persuasion_transition_plan")

    def test_scalar_almost_every_prefers_near_all(self):
        letter, mode = _symbolic_social_reasoning_choice(
            "Scalar Implicature Test",
            "Almost every letter to Laura Company contains a check. Laura receives 5 letters.",
            "Before Laura calls you, how many of these 5 letters do you think contain checks?",
            {
                "A": "0 letters contain checks.",
                "B": "1 letter contains a check.",
                "C": "2 letters contain checks.",
                "D": "4 letters contain checks.",
            },
            {"focus": "scalar_quantity_inference"},
        )
        self.assertEqual(letter, "D")
        self.assertEqual(mode, "symbolic_scalar_almost_every")

    def test_attention_case_prefers_newly_salient_object(self):
        letter, mode = _symbolic_social_reasoning_choice(
            "Knowledge-Attention Links",
            "Wang Lei leaves before colored pencils are played with, comes back, looks at the tray, and says pass it to me.",
            "What does Xiao Ming most likely do?",
            {
                "A": "Give the electric car.",
                "B": "Give the puzzle.",
                "C": "Give the colored pencils.",
                "D": "Give a random toy.",
            },
            {"focus": "attention_reasoning"},
        )
        self.assertEqual(letter, "C")
        self.assertEqual(mode, "symbolic_attention_new_object")


if __name__ == "__main__":
    unittest.main()
