import contextlib
import io
import json
import os
import re
import shutil
import statistics
import sys
import tempfile
from datetime import datetime
from collections import Counter, defaultdict

from project_paths import (
    BASE_DIR,
    HUMAN_FEEDBACK_REGRESSION_DATASET_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_MD_PATH,
)

EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))
DATASET_PATH = HUMAN_FEEDBACK_REGRESSION_DATASET_PATH
REPORT_JSON_PATH = HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH
REPORT_MD_PATH = HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_MD_PATH


def _ensure_project_python():
    if __name__ != "__main__":
        return
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()


FAILURE_TYPES = [
    ("MISREAD_INTENT", "意圖讀錯"),
    ("LOW_DENSITY", "資訊空洞 / 句終結者"),
    ("MISSED_VIBE", "情緒位向錯誤"),
    ("MISSED_JOKE_OR_CULTURE", "梗 / 文化脈絡漏接"),
    ("GENERIC_REPLY", "泛用模板回覆"),
    ("REPEATED_REPLY", "重複句型 / 模式塌陷"),
    ("TOO_ROBOTIC_LOGIC", "過度理性 / 機器人感"),
    ("WRONG_BOUNDARY", "邊界反應錯誤"),
    ("GHOST_MEMORY", "幽靈記憶 / 因果斷裂"),
    ("WRONG_MEMORY_USE", "記憶使用錯誤"),
    ("RIGHTBRAIN_SURFACE_ERROR", "右腦表面化錯誤"),
]
GENERIC_REPLY_SET = {
    "まあそんな感じか",
    "はいはい分かったし",
    "別にいいけど",
    "そうなんだ",
    "分かった",
    "ふーん",
    "あっそ",
}


def normalize_text(text):
    text = str(text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[。．.!！？?,，、~〜…]+", "", text)
    return text


def rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(float(row.get(key, 0.0)) for row in rows) / len(rows), 4)


def safe_mean(values):
    values = [float(value) for value in values if value is not None]
    if not values:
        return 0.0
    return round(statistics.mean(values), 4)


def load_dataset(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def reply_tokens(text):
    text = str(text or "")
    return re.findall(r"[A-Za-z0-9_']+|[\u3040-\u30ff\u4e00-\u9fff]{1,4}", text)


def seed_case_context(brain, case):
    for turn in case.get("seed_turns") or []:
        user = str(turn.get("user") or "").strip()
        reply = str(turn.get("reply") or "seed").strip() or "seed"
        if not user:
            continue
        logic = {
            "intent": turn.get("intent", "chat"),
            "scene": turn.get("scene", "casual"),
            "jp_summary": user,
            "cognitive_mode": "direct",
            "premise_check": "accept",
            "routing_path": "high_road",
        }
        brain.memory.save_episode(user, reply, {"mood": 0, "trust": 50}, logic)


def silent_turn(brain, prompt):
    with contextlib.redirect_stdout(io.StringIO()):
        return brain.run_turn_debug(prompt)


def derive_proxy_flags(result):
    logic = result.get("logic") or {}
    post_check = logic.get("post_check") or {}
    memory_relevance = float(logic.get("memory_relevance") or 0.0)
    memory_anchor = str(logic.get("memory_anchor") or "").strip()
    memory_speakability = str(logic.get("memory_speakability") or "").strip()
    did_use_memory = bool(post_check.get("did_reply_use_memory_explicitly"))
    return {
        "focus_anchor_miss": not bool(post_check.get("did_reply_cover_focus")),
        "obligation_miss": not bool(post_check.get("did_reply_follow_obligation")),
        "memory_misuse": memory_relevance >= 0.45 and memory_speakability in {"explicit_ok", "latent_ok"} and not did_use_memory,
        "memory_available_but_silent": memory_relevance >= 0.45 and bool(memory_anchor) and not did_use_memory,
    }


def density_ok(reply):
    tokens = reply_tokens(reply)
    unique_tokens = {token.lower() for token in tokens}
    return int(len(tokens) >= 4 and len(unique_tokens) >= 3 and len(str(reply or "").strip()) >= 10)


def generic_reply(reply):
    normalized = normalize_text(reply)
    return int(normalized in GENERIC_REPLY_SET or len(normalized) <= 4)


def colloquial_ok(reply):
    text = str(reply or "")
    formal_markers = ["です", "ます", "でした", "ません"]
    if any(marker in text for marker in formal_markers):
        return 0
    return int(len(reply_tokens(text)) >= 3)


def japanese_surface_ok(reply):
    text = str(reply or "")
    english_words = re.findall(r"[A-Za-z]{3,}", text)
    chinese_surface_markers = [
        "了解你的", "你的需求", "你的想法", "我会", "我會", "我们", "我們", "不用太",
        "擔心", "担心", "一起讨论", "一起討論", "我覺得", "我觉得", "可以一起", "我尊重",
    ]
    chinese_leak = "，" in text or any(marker in text for marker in chinese_surface_markers)
    return int(not english_words and not chinese_leak and colloquial_ok(text) and not generic_reply(text))


def evaluate_human_contract(case, reply):
    contract = case.get("human_contract") or {}
    required_groups = [
        [str(marker) for marker in group if str(marker).strip()]
        for group in (contract.get("required_marker_groups") or [])
        if isinstance(group, list)
    ]
    forbidden_markers = [
        str(marker).strip()
        for marker in (contract.get("forbidden_markers") or [])
        if str(marker).strip()
    ]
    text = str(reply or "")
    group_hits = [int(any(marker in text for marker in group)) for group in required_groups]
    forbidden_hits = [marker for marker in forbidden_markers if marker in text]
    available = bool(required_groups or forbidden_markers)
    return {
        "available": int(available),
        "required_group_count": len(required_groups),
        "required_group_hit_count": sum(group_hits),
        "required_group_hits": group_hits,
        "required_group_hit_rate": round(sum(group_hits) / len(group_hits), 4) if group_hits else None,
        "all_required_groups_hit": int(all(group_hits)) if required_groups else (1 if available else None),
        "forbidden_marker_hits": forbidden_hits,
        "forbidden_markers_ok": int(not forbidden_hits) if available else None,
    }


def evaluate_required_groups(required_groups, reply):
    groups = [
        [str(marker) for marker in group if str(marker).strip()]
        for group in (required_groups or [])
        if group
    ]
    text = str(reply or "")
    hits = [int(any(marker in text for marker in group)) for group in groups]
    return {
        "available": int(bool(groups)),
        "required_group_count": len(groups),
        "required_group_hit_count": sum(hits),
        "required_group_hits": hits,
        "required_group_hit_rate": round(sum(hits) / len(hits), 4) if hits else None,
        "all_required_groups_hit": int(all(hits)) if hits else None,
    }


def vibe_bucket(prompt):
    lowered = str(prompt or "").lower()
    abuse_markers = ["操", "幹", "妈", "媽", "bitch", "fuck", "shut up", "きも", "死ね", "懶覺", "ちんこ"]
    support_markers = ["累", "哭", "難過", "sad", "tired", "cry", "しんど", "つら", "泣", "消えたい", "不想活"]
    nonsense_markers = ["消防車", "魔性日", "歌詞", "平底鍋", "平底锅", "何言って", "意味分か", "lyrics"]
    if any(marker.lower() in lowered for marker in abuse_markers):
        return "abuse"
    if any(marker.lower() in lowered for marker in support_markers):
        return "support"
    if any(marker.lower() in lowered for marker in nonsense_markers):
        return "nonsense"
    return "unknown"


def vibe_ok(prompt, logic):
    bucket = vibe_bucket(prompt)
    scene = str(logic.get("scene") or "")
    intent = str(logic.get("intent") or "")
    surface_act = str(logic.get("surface_act") or "")
    if bucket == "abuse":
        return int(scene not in {"support"} and "support" not in intent)
    if bucket == "support":
        return int(scene in {"support", "casual"} or "support" in intent)
    if bucket == "nonsense":
        return int(
            surface_act in {"nonsense_tease", "announcement_tease", "reference_probe", "lyric_probe"}
            or ("support" not in intent and scene != "support")
        )
    return None


def evaluate_failure_resolution(case, result, actual_proxies, focus_ok=None, obligation_ok=None):
    logic = result.get("logic") or {}
    post_check = logic.get("post_check") or {}
    reply = result.get("reply") or ""
    failure_types = case.get("failure_types") or []
    resolved = {}
    if focus_ok is None:
        focus_ok = int(bool(post_check.get("did_reply_cover_focus")))
    if obligation_ok is None:
        obligation_ok = int(bool(post_check.get("did_reply_follow_obligation")))

    if "LOW_DENSITY" in failure_types:
        resolved["LOW_DENSITY"] = int(
            bool(focus_ok)
            and bool(obligation_ok)
            and density_ok(reply)
            and not generic_reply(reply)
        )

    if "MISREAD_INTENT" in failure_types:
        resolved["MISREAD_INTENT"] = int(
            bool(focus_ok)
            and bool(obligation_ok)
        )

    if "GHOST_MEMORY" in failure_types:
        resolved["GHOST_MEMORY"] = int(
            not actual_proxies.get("memory_misuse")
            and not actual_proxies.get("memory_available_but_silent")
            and bool(post_check.get("did_reply_use_memory_explicitly"))
        )

    if "TOO_ROBOTIC_LOGIC" in failure_types:
        resolved["TOO_ROBOTIC_LOGIC"] = int(
            not generic_reply(reply)
            and colloquial_ok(reply)
        )

    if "GENERIC_REPLY" in failure_types:
        resolved["GENERIC_REPLY"] = int(
            not generic_reply(reply)
            and bool(focus_ok)
            and density_ok(reply)
        )

    if "REPEATED_REPLY" in failure_types:
        observed_reply = case.get("observed_reply")
        resolved["REPEATED_REPLY"] = int(
            normalize_text(reply) != normalize_text(observed_reply)
            and not generic_reply(reply)
        )

    if "MISSED_JOKE_OR_CULTURE" in failure_types:
        resolved["MISSED_JOKE_OR_CULTURE"] = int(
            bool(focus_ok)
            and not generic_reply(reply)
            and density_ok(reply)
        )

    if "WRONG_BOUNDARY" in failure_types:
        vibe = vibe_ok(case.get("prompt"), logic)
        resolved["WRONG_BOUNDARY"] = int(
            bool(obligation_ok)
            and (vibe is None or bool(vibe))
        )

    if "WRONG_MEMORY_USE" in failure_types:
        resolved["WRONG_MEMORY_USE"] = int(not actual_proxies.get("memory_misuse"))

    if "RIGHTBRAIN_SURFACE_ERROR" in failure_types:
        resolved["RIGHTBRAIN_SURFACE_ERROR"] = japanese_surface_ok(reply)

    if "MISSED_VIBE" in failure_types:
        vibe = vibe_ok(case.get("prompt"), logic)
        resolved["MISSED_VIBE"] = vibe

    return resolved


def evaluate_case(brain, case):
    tempdir = tempfile.mkdtemp(prefix="uruha_hf_regression_eval_")
    try:
        brain.reset_session(db_path=tempdir)
        brain.memory.reflect_experience = lambda *_args, **_kwargs: None
        seed_case_context(brain, case)
        result = silent_turn(brain, case.get("prompt", ""))
        logic = result.get("logic") or {}
        route_info = result.get("route_info") or {}
        post_check = logic.get("post_check") or {}
        reply = result.get("reply") or ""
        normalized_reply = normalize_text(reply)
        normalized_observed = normalize_text(case.get("observed_reply"))
        actual_proxies = derive_proxy_flags(result)
        contract_eval = evaluate_human_contract(case, reply)
        planner_groups = brain.right_brain._required_surface_semantic_groups(logic)
        planner_contract_eval = evaluate_required_groups(planner_groups, reply)
        observed_planner_contract_eval = evaluate_required_groups(
            planner_groups,
            case.get("observed_reply"),
        )
        if contract_eval["available"]:
            focus_ok = int(bool(contract_eval["all_required_groups_hit"]))
            obligation_ok = int(bool(contract_eval["forbidden_markers_ok"]))
            focus_source = "human_contract"
        else:
            focus_ok = int(bool(post_check.get("did_reply_cover_focus")))
            obligation_ok = int(bool(post_check.get("did_reply_follow_obligation")))
            focus_source = "runtime_post_check"
        expected_proxies = set(case.get("expected_trace_proxies") or [])
        persisted_expected_proxies = sorted(name for name in expected_proxies if actual_proxies.get(name))
        failure_resolution = evaluate_failure_resolution(
            case,
            result,
            actual_proxies,
            focus_ok=focus_ok,
            obligation_ok=obligation_ok,
        )
        vibe_score = failure_resolution.get("MISSED_VIBE")

        replay = {
            "id": case.get("id"),
            "category": case.get("category"),
            "language": case.get("language"),
            "prompt": case.get("prompt"),
            "observed_reply": case.get("observed_reply"),
            "replayed_reply": reply,
            "route": route_info.get("route"),
            "expected_route": case.get("expected_route"),
            "route_match": int(
                not case.get("expected_route") or route_info.get("route") == case.get("expected_route")
            ),
            "response_mode": logic.get("response_mode"),
            "intent": logic.get("intent"),
            "scene": logic.get("scene"),
            "surface_act": logic.get("surface_act"),
            "focus_anchor": logic.get("focus_anchor"),
            "reply_obligation": logic.get("reply_obligation"),
            "focus_ok": focus_ok,
            "obligation_ok": obligation_ok,
            "focus_source": focus_source,
            "human_contract_eval": contract_eval,
            "planner_contract_eval": planner_contract_eval,
            "observed_planner_contract_eval": observed_planner_contract_eval,
            "memory_expected": int(bool(post_check.get("memory_use_expected"))),
            "memory_ok": int(bool(post_check.get("did_reply_use_memory_explicitly"))),
            "density_ok": density_ok(reply),
            "generic_reply": generic_reply(reply),
            "colloquial_ok": colloquial_ok(reply),
            "vibe_ok": vibe_score,
            "reply_token_count": len(reply_tokens(reply)),
            "same_as_observed_bad_reply": int(bool(normalized_observed) and normalized_reply == normalized_observed),
            "expected_trace_proxies": sorted(expected_proxies),
            "actual_trace_proxies": sorted(name for name, enabled in actual_proxies.items() if enabled),
            "persisted_expected_proxies": persisted_expected_proxies,
            "expected_proxy_persist_rate": round(
                len(persisted_expected_proxies) / max(1, len(expected_proxies)),
                4,
            ),
            "failure_types": case.get("failure_types") or [],
            "failure_resolution": failure_resolution,
            "regression_targets": case.get("regression_targets") or [],
            "seed_turn_count": len(case.get("seed_turns") or []),
            "working_memory_summary": (result.get("memory_data") or {}).get("working_memory_summary"),
            "planner_tick_count": int((result.get("runtime_state") or {}).get("planner_tick_count") or 0),
            "self_correction_applied": int(bool((result.get("runtime_state") or {}).get("self_correction_applied"))),
        }

        eligible_scores = [
            replay["route_match"],
            replay["focus_ok"],
            replay["obligation_ok"],
        ]
        if replay["memory_expected"]:
            eligible_scores.append(replay["memory_ok"])
        for failure_type in replay["failure_types"]:
            value = failure_resolution.get(failure_type)
            if value is not None:
                eligible_scores.append(value)
        eligible_scores.append(1 - replay["generic_reply"])
        replay["overall_auto_pass"] = int(all(bool(score) for score in eligible_scores)) if eligible_scores else 0
        return replay
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def build_markdown(report):
    summary = report.get("summary") or {}
    lines = [
        "# Human Feedback Regression Eval Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- dataset_path: `{report.get('dataset_path')}`",
        "",
        "## Summary",
        "",
        f"- total_cases: {summary.get('total_cases', 0)}",
        f"- route_match_rate: {summary.get('route_match_rate', 0.0)}",
        f"- focus_ok_rate: {summary.get('focus_ok_rate', 0.0)}",
        f"- obligation_ok_rate: {summary.get('obligation_ok_rate', 0.0)}",
        f"- human_contract_required_group_hit_rate: {summary.get('human_contract_required_group_hit_rate', 0.0)}",
        f"- planner_contract_observed_group_hit_rate: {summary.get('planner_contract_observed_group_hit_rate', 0.0)}",
        f"- planner_contract_current_group_hit_rate: {summary.get('planner_contract_current_group_hit_rate', 0.0)}",
        f"- planner_contract_group_hit_delta: {summary.get('planner_contract_group_hit_delta', 0.0)}",
        f"- memory_ok_rate_when_expected: {summary.get('memory_ok_rate_when_expected', 0.0)}",
        f"- density_ok_rate: {summary.get('density_ok_rate', 0.0)}",
        f"- generic_reply_rate: {summary.get('generic_reply_rate', 0.0)}",
        f"- same_as_observed_bad_reply_rate: {summary.get('same_as_observed_bad_reply_rate', 0.0)}",
        f"- avg_expected_proxy_persist_rate: {summary.get('avg_expected_proxy_persist_rate', 0.0)}",
        f"- overall_auto_pass_rate: {summary.get('overall_auto_pass_rate', 0.0)}",
        "- evidence boundary: these are deterministic contract checks; post-patch human naturalness has not been re-rated.",
        "",
        "## Failure Resolution",
        "",
    ]
    for row in report.get("failure_type_summary") or []:
        lines.append(
            f"- {row.get('code')} ({row.get('label_zh')}): eligible={row.get('eligible_count')} "
            f"resolved={row.get('resolved_count')} unresolved={row.get('unresolved_count')} "
            f"unknown={row.get('unknown_count')} resolved_rate={row.get('resolved_rate')}"
        )

    lines.extend(["", "## Worst Cases", ""])
    for row in report.get("worst_cases") or []:
        lines.append(
            f"- id={row.get('id')} failure={row.get('failure_types')} route={row.get('route')} "
            f"focus={row.get('focus_ok')} obligation={row.get('obligation_ok')} "
            f"memory={row.get('memory_ok')} generic={row.get('generic_reply')} "
            f"persisted={row.get('persisted_expected_proxies')} prompt={row.get('prompt')} "
            f"reply={row.get('replayed_reply')}"
        )
    if not (report.get("worst_cases") or []):
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main():
    dataset = load_dataset(DATASET_PATH)

    results = []
    if dataset:
        import uruha_brain_mac as brain_mod

        brain = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)
        brain.memory.reflect_experience = lambda *_args, **_kwargs: None
        for idx, case in enumerate(dataset, 1):
            results.append(evaluate_case(brain, case))
            if idx % 25 == 0:
                print(f"[{idx:04d}/{len(dataset)}] replayed")

    memory_expected_rows = [row for row in results if row.get("memory_expected")]
    vibe_rows = [row for row in results if row.get("vibe_ok") is not None]
    contract_rows = [row for row in results if (row.get("human_contract_eval") or {}).get("available")]
    planner_contract_rows = [row for row in results if (row.get("planner_contract_eval") or {}).get("available")]
    planner_current_group_hit_rate = safe_mean(
        (row.get("planner_contract_eval") or {}).get("required_group_hit_rate")
        for row in planner_contract_rows
    )
    planner_observed_group_hit_rate = safe_mean(
        (row.get("observed_planner_contract_eval") or {}).get("required_group_hit_rate")
        for row in planner_contract_rows
    )

    failure_type_summary = []
    for code, label in FAILURE_TYPES:
        rows = [row for row in results if code in (row.get("failure_types") or [])]
        eligible = [row for row in rows if row.get("failure_resolution", {}).get(code) is not None]
        resolved = [row for row in eligible if row.get("failure_resolution", {}).get(code) == 1]
        unresolved = [row for row in eligible if row.get("failure_resolution", {}).get(code) == 0]
        unknown = [row for row in rows if row.get("failure_resolution", {}).get(code) is None]
        failure_type_summary.append(
            {
                "code": code,
                "label_zh": label,
                "eligible_count": len(eligible),
                "resolved_count": len(resolved),
                "unresolved_count": len(unresolved),
                "unknown_count": len(unknown),
                "resolved_rate": rate(eligible, "failure_resolution_value") if False else (
                    round(len(resolved) / len(eligible), 4) if eligible else 0.0
                ),
            }
        )

    summary = {
        "total_cases": len(results),
        "surface_mode": "right_brain_template_mode_via_run_turn_debug",
        "route_match_rate": rate(results, "route_match"),
        "focus_ok_rate": rate(results, "focus_ok"),
        "obligation_ok_rate": rate(results, "obligation_ok"),
        "human_contract_coverage_rate": round(len(contract_rows) / len(results), 4) if results else 0.0,
        "human_contract_required_group_hit_rate": safe_mean(
            (row.get("human_contract_eval") or {}).get("required_group_hit_rate")
            for row in contract_rows
        ),
        "human_contract_forbidden_marker_ok_rate": safe_mean(
            (row.get("human_contract_eval") or {}).get("forbidden_markers_ok")
            for row in contract_rows
        ),
        "planner_contract_coverage_rate": round(len(planner_contract_rows) / len(results), 4) if results else 0.0,
        "planner_contract_current_group_hit_rate": planner_current_group_hit_rate,
        "planner_contract_observed_group_hit_rate": planner_observed_group_hit_rate,
        "planner_contract_group_hit_delta": round(
            (planner_current_group_hit_rate or 0.0) - (planner_observed_group_hit_rate or 0.0),
            4,
        ),
        "planner_contract_current_all_hit_rate": safe_mean(
            (row.get("planner_contract_eval") or {}).get("all_required_groups_hit")
            for row in planner_contract_rows
        ),
        "planner_contract_observed_all_hit_rate": safe_mean(
            (row.get("observed_planner_contract_eval") or {}).get("all_required_groups_hit")
            for row in planner_contract_rows
        ),
        "memory_ok_rate_when_expected": rate(memory_expected_rows, "memory_ok"),
        "density_ok_rate": rate(results, "density_ok"),
        "generic_reply_rate": rate(results, "generic_reply"),
        "same_as_observed_bad_reply_rate": rate(results, "same_as_observed_bad_reply"),
        "avg_expected_proxy_persist_rate": safe_mean(row.get("expected_proxy_persist_rate") for row in results),
        "overall_auto_pass_rate": rate(results, "overall_auto_pass"),
        "avg_reply_token_count": safe_mean(row.get("reply_token_count") for row in results),
        "avg_planner_tick_count": safe_mean(row.get("planner_tick_count") for row in results),
        "self_correction_rate": rate(results, "self_correction_applied"),
        "vibe_eval_coverage_rate": round(len(vibe_rows) / len(results), 4) if results else 0.0,
        "vibe_ok_rate_on_covered_cases": rate(vibe_rows, "vibe_ok"),
        "language_breakdown": {
            lang: {
                "count": len(rows),
                "overall_auto_pass_rate": rate(rows, "overall_auto_pass"),
                "focus_ok_rate": rate(rows, "focus_ok"),
                "obligation_ok_rate": rate(rows, "obligation_ok"),
                "generic_reply_rate": rate(rows, "generic_reply"),
            }
            for lang, rows in (
                (
                    language,
                    [row for row in results if row.get("language") == language],
                )
                for language in sorted({row.get("language") for row in results})
            )
        },
    }

    worst_cases = sorted(
        results,
        key=lambda row: (
            row.get("overall_auto_pass", 0),
            row.get("focus_ok", 0),
            row.get("obligation_ok", 0),
            1 - row.get("generic_reply", 0),
            row.get("expected_proxy_persist_rate", 0.0),
        ),
    )[:20]

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": DATASET_PATH,
        "summary": summary,
        "evidence_boundary": {
            "post_patch_human_rating_available": False,
            "auto_contract_scores_are_human_naturalness_scores": False,
            "paired_comparison_scope": "The current planner-derived semantic groups are applied to both observed and replayed outputs.",
        },
        "failure_type_summary": failure_type_summary,
        "worst_cases": [
            {
                "id": row.get("id"),
                "language": row.get("language"),
                "failure_types": row.get("failure_types"),
                "prompt": row.get("prompt"),
                "observed_reply": row.get("observed_reply"),
                "replayed_reply": row.get("replayed_reply"),
                "route": row.get("route"),
                "response_mode": row.get("response_mode"),
                "intent": row.get("intent"),
                "focus_ok": row.get("focus_ok"),
                "obligation_ok": row.get("obligation_ok"),
                "memory_ok": row.get("memory_ok"),
                "generic_reply": row.get("generic_reply"),
                "persisted_expected_proxies": row.get("persisted_expected_proxies"),
            }
            for row in worst_cases
        ],
        "results": results,
    }

    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(REPORT_JSON_PATH)
    print(REPORT_MD_PATH)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
