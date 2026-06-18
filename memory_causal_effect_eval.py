import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
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
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__, *sys.argv[1:]], clean_env)


_ensure_project_python()

import uruha_brain_mac as brain_mod
from project_paths import (
    MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH,
    MEMORY_CAUSAL_EFFECT_REPORT_MD_PATH,
)


def build_cases():
    return [
        {
            "id": "zh_dislike_spicy",
            "category": "preference_boundary",
            "language": "zh",
            "seed_turns": ["我討厭吃辣。"],
            "prompt": "那今天要不要吃麻辣鍋？",
            "expected_anchors": ["辛", "辣", "麻辣"],
        },
        {
            "id": "zh_name_recall",
            "category": "identity_recall",
            "language": "zh",
            "seed_turns": ["叫我小傑。"],
            "prompt": "你還記得我叫什麼嗎？",
            "expected_anchors": ["小傑"],
        },
        {
            "id": "zh_bad_ramen",
            "category": "episodic_consequence",
            "language": "zh",
            "seed_turns": ["我上次吃那家拉麵吃到肚子痛。"],
            "prompt": "我今天又要去吃那家拉麵。",
            "expected_anchors": ["腹", "肚", "ラーメン", "拉麵"],
        },
        {
            "id": "en_favorite_drink",
            "category": "preference_recall",
            "language": "en",
            "seed_turns": ["My favorite drink is strawberry milk."],
            "prompt": "Do you remember my favorite drink?",
            "expected_anchors": ["strawberry", "いちご", "milk", "ミルク"],
        },
        {
            "id": "en_dislike_horror",
            "category": "preference_boundary",
            "language": "en",
            "seed_turns": ["I hate horror movies."],
            "prompt": "Should we watch a horror movie tonight?",
            "expected_anchors": ["horror", "ホラー", "嫌"],
        },
        {
            "id": "ja_name_recall",
            "category": "identity_recall",
            "language": "ja",
            "seed_turns": ["ジェリーって呼んで。"],
            "prompt": "うちの名前覚えてる？",
            "expected_anchors": ["ジェリー"],
        },
        {
            "id": "ja_dislike_nattoo",
            "category": "preference_boundary",
            "language": "ja",
            "seed_turns": ["納豆だけは苦手。"],
            "prompt": "朝ごはん納豆でいい？",
            "expected_anchors": ["納豆", "苦手", "嫌"],
        },
        {
            "id": "ja_recent_action",
            "category": "episodic_recall",
            "language": "ja",
            "seed_turns": ["さっきコンビニ行ってくるって言った。"],
            "prompt": "さっき何するって言ってたっけ？",
            "expected_anchors": ["コンビニ"],
        },
    ]


def normalize_text(text):
    text = str(text or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[。．.!！？?,，、~〜…/／]+", "", text)
    return text


def contains_any(text, anchors):
    lowered = str(text or "").lower()
    return any(str(anchor).lower() in lowered for anchor in anchors or [])


def silent_turn(brain, prompt):
    with contextlib.redirect_stdout(io.StringIO()):
        return brain.run_turn_debug(prompt)


def _logic_signature(result):
    logic = result.get("logic") or {}
    return {
        "intent": logic.get("intent"),
        "scene": logic.get("scene"),
        "response_mode": logic.get("response_mode"),
        "surface_act": logic.get("surface_act"),
        "focus_anchor": logic.get("focus_anchor"),
        "reply_obligation": logic.get("reply_obligation"),
    }


def _memory_score(result):
    logic = result.get("logic") or {}
    try:
        return float(logic.get("memory_relevance") or 0.0)
    except Exception:
        return 0.0


def _memory_summary(result):
    memory_data = result.get("memory_data") or {}
    return memory_data.get("working_memory_summary") or ""


def _post_check(result):
    return ((result.get("logic") or {}).get("post_check") or {})


def run_condition(brain, case, with_memory):
    tempdir = tempfile.mkdtemp(prefix="uruha_memory_causal_")
    try:
        brain.reset_session(db_path=tempdir)
        brain.memory.reflect_experience = lambda *_args, **_kwargs: None
        if with_memory:
            for seed in case.get("seed_turns") or []:
                brain.memory.save_episode(
                    seed,
                    "覚えた。",
                    {"mood": 0, "trust": 50},
                    {
                        "intent": "memory_seed",
                        "scene": "memory",
                        "jp_summary": seed,
                        "cognitive_mode": "direct",
                        "premise_check": "accept",
                        "routing_path": "high_road",
                    },
                )
        return silent_turn(brain, case["prompt"])
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def evaluate_case(brain, case):
    control = run_condition(brain, case, with_memory=False)
    memory = run_condition(brain, case, with_memory=True)

    control_reply = control.get("reply") or ""
    memory_reply = memory.get("reply") or ""
    control_sig = _logic_signature(control)
    memory_sig = _logic_signature(memory)
    post_check = _post_check(memory)
    anchors = case.get("expected_anchors") or []

    reply_changed = normalize_text(control_reply) != normalize_text(memory_reply)
    plan_changed = control_sig != memory_sig
    anchor_in_reply = contains_any(memory_reply, anchors)
    anchor_in_working_memory = contains_any(_memory_summary(memory), anchors)
    memory_relevance = _memory_score(memory)
    memory_expected = bool(post_check.get("memory_use_expected"))
    memory_used_explicitly = bool(post_check.get("did_reply_use_memory_explicitly"))

    strong_causal_effect = bool(reply_changed and anchor_in_reply)
    weak_causal_effect = bool(
        (reply_changed or plan_changed)
        and (anchor_in_reply or anchor_in_working_memory or memory_relevance >= 0.45 or memory_expected)
    )

    return {
        **case,
        "control_reply": control_reply,
        "memory_reply": memory_reply,
        "control_logic": control_sig,
        "memory_logic": memory_sig,
        "reply_changed": int(reply_changed),
        "plan_changed": int(plan_changed),
        "anchor_in_reply": int(anchor_in_reply),
        "anchor_in_working_memory": int(anchor_in_working_memory),
        "memory_relevance": memory_relevance,
        "memory_expected": int(memory_expected),
        "memory_used_explicitly": int(memory_used_explicitly),
        "strong_causal_effect": int(strong_causal_effect),
        "weak_causal_effect": int(weak_causal_effect),
        "working_memory_summary": _memory_summary(memory),
    }


def _rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(int(row.get(key) or 0) for row in rows) / len(rows), 4)


def _mean(rows, key):
    values = [float(row.get(key) or 0.0) for row in rows]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def build_summary(results):
    summary = {
        "total_cases": len(results),
        "reply_changed_rate": _rate(results, "reply_changed"),
        "plan_changed_rate": _rate(results, "plan_changed"),
        "anchor_in_reply_rate": _rate(results, "anchor_in_reply"),
        "anchor_in_working_memory_rate": _rate(results, "anchor_in_working_memory"),
        "memory_expected_rate": _rate(results, "memory_expected"),
        "memory_used_explicitly_rate": _rate(results, "memory_used_explicitly"),
        "strong_causal_effect_rate": _rate(results, "strong_causal_effect"),
        "weak_causal_effect_rate": _rate(results, "weak_causal_effect"),
        "avg_memory_relevance": _mean(results, "memory_relevance"),
        "by_category": {},
        "by_language": {},
    }

    for category in sorted({row["category"] for row in results}):
        rows = [row for row in results if row["category"] == category]
        summary["by_category"][category] = {
            "count": len(rows),
            "strong_causal_effect_rate": _rate(rows, "strong_causal_effect"),
            "weak_causal_effect_rate": _rate(rows, "weak_causal_effect"),
            "anchor_in_reply_rate": _rate(rows, "anchor_in_reply"),
            "avg_memory_relevance": _mean(rows, "memory_relevance"),
        }

    for language in sorted({row["language"] for row in results}):
        rows = [row for row in results if row["language"] == language]
        summary["by_language"][language] = {
            "count": len(rows),
            "strong_causal_effect_rate": _rate(rows, "strong_causal_effect"),
            "weak_causal_effect_rate": _rate(rows, "weak_causal_effect"),
            "anchor_in_reply_rate": _rate(rows, "anchor_in_reply"),
        }
    return summary


def build_markdown(report):
    summary = report.get("summary") or {}
    lines = [
        "# Memory Causal Effect Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        "",
        "## Summary",
        "",
        f"- total_cases: {summary.get('total_cases', 0)}",
        f"- reply_changed_rate: {summary.get('reply_changed_rate', 0.0)}",
        f"- plan_changed_rate: {summary.get('plan_changed_rate', 0.0)}",
        f"- anchor_in_reply_rate: {summary.get('anchor_in_reply_rate', 0.0)}",
        f"- anchor_in_working_memory_rate: {summary.get('anchor_in_working_memory_rate', 0.0)}",
        f"- memory_expected_rate: {summary.get('memory_expected_rate', 0.0)}",
        f"- memory_used_explicitly_rate: {summary.get('memory_used_explicitly_rate', 0.0)}",
        f"- strong_causal_effect_rate: {summary.get('strong_causal_effect_rate', 0.0)}",
        f"- weak_causal_effect_rate: {summary.get('weak_causal_effect_rate', 0.0)}",
        f"- avg_memory_relevance: {summary.get('avg_memory_relevance', 0.0)}",
        "",
        "## Cases",
        "",
    ]
    for row in report.get("results") or []:
        lines.append(
            f"- {row.get('id')} lang={row.get('language')} category={row.get('category')} "
            f"strong={row.get('strong_causal_effect')} weak={row.get('weak_causal_effect')} "
            f"anchor_reply={row.get('anchor_in_reply')} mem_rel={row.get('memory_relevance')} "
            f"expected={row.get('memory_expected')} used={row.get('memory_used_explicitly')}"
        )
        lines.append(f"  - prompt: {row.get('prompt')}")
        lines.append(f"  - control: {row.get('control_reply')}")
        lines.append(f"  - memory: {row.get('memory_reply')}")
    return "\n".join(lines) + "\n"


def main():
    cases = build_cases()
    brain = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)
    brain.memory.reflect_experience = lambda *_args, **_kwargs: None
    results = [evaluate_case(brain, case) for case in cases]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "surface_mode": "right_brain_template_mode_via_run_turn_debug",
        "summary": build_summary(results),
        "results": results,
    }
    with open(MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(MEMORY_CAUSAL_EFFECT_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH)
    print(MEMORY_CAUSAL_EFFECT_REPORT_MD_PATH)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
