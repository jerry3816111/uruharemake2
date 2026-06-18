import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_project_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        clean_env["URUHA_SKIP_AUTO_VENV"] = "1"
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()
os.environ["URUHA_SKIP_AUTO_VENV"] = "1"

from uruha_brain_mac import LeftBrain


def _story_prompt(story, question, options=None):
    options = options or {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D",
    }
    option_lines = "\n".join(f"{key}. {value}" for key, value in options.items())
    return f"Story: {story}\n\nQuestion: {question}\n{option_lines}"


CASES = [
    {
        "id": "persuasion_strategy_dad",
        "task": "Persuasion Story Task",
        "prompt": _story_prompt(
            "Dad thinks the amusement park will be too noisy on weekends, and Xiao Hong wants to persuade him.",
            "How does Xiao Hong persuade her dad?",
        ),
        "expected_focus": "persuasion_strategy",
        "expected_frame_terms": ["懸念", "具体策"],
    },
    {
        "id": "persuasion_strategy_boss",
        "task": "Persuasion Story Task",
        "prompt": _story_prompt(
            "Li Na wants to change departments and needs to present a concrete plan to her boss.",
            "How does Li Na convince her boss?",
        ),
        "expected_focus": "persuasion_strategy",
        "expected_frame_terms": ["懸念", "具体策"],
    },
    {
        "id": "hidden_emotion_party",
        "task": "Hidden Emotions",
        "prompt": _story_prompt(
            "Xinxin says her stomach hurts, but she is actually worried about missing a party she wants to attend.",
            "What are Xinxin's real feelings?",
        ),
        "expected_focus": "hidden_emotion",
        "expected_frame_terms": ["本音", "言い訳"],
    },
    {
        "id": "scalar_letters",
        "task": "Scalar Implicature Test",
        "prompt": _story_prompt(
            "Laura has opened three of five letters and seen checks in two of them. She has not seen the other two.",
            "Before Laura calls you, how many of these 5 letters do you think contain checks?",
        ),
        "expected_focus": "scalar_quantity_inference",
        "expected_frame_terms": ["最低限", "未観測"],
    },
    {
        "id": "scalar_baguettes",
        "task": "Scalar Implicature Test",
        "prompt": _story_prompt(
            "Xiao Ling can see only some of the breads and must guess how many baguettes there are in total.",
            "Please ask, after Xiao Ling looks, how many baguettes does she guess?",
        ),
        "expected_focus": "scalar_quantity_inference",
        "expected_frame_terms": ["最低限", "未観測"],
    },
    {
        "id": "social_knowledge_marriage",
        "task": "Faux-pas Recognition Test",
        "prompt": _story_prompt(
            "Xiao Wang has told only a few close friends that she does not want to get married for now.",
            "Does Xiao Zhang know that Xiao Wang does not want to get married for the time being?",
        ),
        "expected_focus": "knowledge_state_social",
        "expected_frame_terms": ["知っている", "知らない"],
    },
    {
        "id": "completion_after_video",
        "task": "Multiple Desires",
        "prompt": _story_prompt(
            "Sara paused her own plans to finish a promotional video for the team and is now done.",
            "What does Sara do after she completes the production of the promotional video?",
        ),
        "expected_focus": "completion_after_action",
        "expected_frame_terms": ["保留", "戻"],
    },
    {
        "id": "completion_after_cooking",
        "task": "Completion of Failed Actions",
        "prompt": _story_prompt(
            "Xiao Hua wanted to watch a movie with Xiao Li, but had to finish cooking dinner first.",
            "What does Xiao Hua do next after hearing Xiao Li's invitation?",
        ),
        "expected_focus": "action_prediction",
        "expected_frame_terms": ["最後", "障害"],
    },
]


def main():
    left = LeftBrain(client_logic=None)
    rows = []
    for case in CASES:
        profile = left._story_reasoning_profile(case["prompt"]) or {}
        frame = left._build_social_reasoning_frame(case["prompt"]) or {}
        frame_blob = " ".join(str(frame.get(key, "")) for key in frame.keys())
        focus_hit = profile.get("focus") == case["expected_focus"] and frame.get("focus") == case["expected_focus"]
        term_hit = all(term in frame_blob for term in case["expected_frame_terms"])
        rows.append(
            {
                "id": case["id"],
                "task": case["task"],
                "expected_focus": case["expected_focus"],
                "profile_focus": profile.get("focus"),
                "frame_focus": frame.get("focus"),
                "focus_hit": int(focus_hit),
                "frame_terms_hit": int(term_hit),
                "frame": frame,
            }
        )

    pass_rate = round(sum(1 for row in rows if row["focus_hit"] and row["frame_terms_hit"]) / len(rows), 4) if rows else 0.0
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "research_social_reasoning_audit_v1",
        "summary": {
            "total_cases": len(rows),
            "passed_cases": sum(1 for row in rows if row["focus_hit"] and row["frame_terms_hit"]),
            "pass_rate": pass_rate,
        },
        "results": rows,
    }
    os.makedirs("reports", exist_ok=True)
    out_path = os.path.join("reports", "research_social_reasoning_audit_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
