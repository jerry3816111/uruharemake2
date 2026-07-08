import json
import os
from datetime import datetime

from project_paths import (
    ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
    ANNOTATION_DRAFT_QUEUE_JSON_PATH,
    COGNITIVE_ARCHITECTURE_REPORT_PATH,
    DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH,
    DOMAIN_EVAL_SUITE_REPORT_PATH,
    FORMAL_BRAIN_BENCHMARKS_REPORT_JSON_PATH,
    FORMAL_TOMBENCH_REFRESH_PATH,
    HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH,
    HUMAN_SPEECH_LAYER_REPORT_JSON_PATH,
    LONG_DIALOGUE_MEMORY_REPORT_PATH,
    MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH,
    MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
    REPLY_DIVERSITY_REPORT_PATH,
    RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH,
    RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH,
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH,
    RUNTIME_DYNAMICS_REPORT_PATH,
    SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH,
    STRESS_EVAL_REPORT_PATH,
    SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH,
    SURFACE_MICROPLANNING_REPORT_JSON_PATH,
    SYSTEM_VS_PROMPT_ONLY_COMPARE_PATH,
    UNIFIED_EVAL_SUMMARY_JSON_PATH,
    UNIFIED_EVAL_SUMMARY_MD_PATH,
    V2_HUMAN_ANSWER_REPORT_PATH,
)

REPORT_PATHS = {
    "architecture": COGNITIVE_ARCHITECTURE_REPORT_PATH,
    "daily_state_self_distress": DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH,
    "self_distress_surface_contract": SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH,
    "support_prefix_contract": SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH,
    "runtime": RUNTIME_DYNAMICS_REPORT_PATH,
    "memory": LONG_DIALOGUE_MEMORY_REPORT_PATH,
    "memory_causal_effect": MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH,
    "memory_speakability_response": MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
    "diversity": REPLY_DIVERSITY_REPORT_PATH,
    "human_answer": V2_HUMAN_ANSWER_REPORT_PATH,
    "formal": FORMAL_BRAIN_BENCHMARKS_REPORT_JSON_PATH,
    "formal_tombench_refresh": FORMAL_TOMBENCH_REFRESH_PATH,
    "domain_suite": DOMAIN_EVAL_SUITE_REPORT_PATH,
    "stress_10k": STRESS_EVAL_REPORT_PATH,
    "system_vs_prompt": SYSTEM_VS_PROMPT_ONLY_COMPARE_PATH,
    "human_blind": HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH,
    "human_feedback_annotation": HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH,
    "annotation_candidate_queue": ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
    "annotation_draft_queue": ANNOTATION_DRAFT_QUEUE_JSON_PATH,
    "human_feedback_regression": HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH,
    "human_feedback_regression_eval": HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    "human_feedback_regression_diff": HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH,
    "human_speech_layer": HUMAN_SPEECH_LAYER_REPORT_JSON_PATH,
    "surface_microplanning": SURFACE_MICROPLANNING_REPORT_JSON_PATH,
    "rightbrain_model_gate": RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH,
    "rightbrain_model_surface_holdout": RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH,
    "rightbrain_runtime_adapter_multiseed": RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH,
}

OUT_JSON = UNIFIED_EVAL_SUMMARY_JSON_PATH
OUT_MD = UNIFIED_EVAL_SUMMARY_MD_PATH


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _compact_domain_suite_summary(report):
    summary = dict((report or {}).get("summary") or {})
    compact_runs = []
    for row in summary.get("task_runs") or []:
        compact_runs.append(
            {
                key: row.get(key)
                for key in (
                    "task",
                    "script",
                    "returncode",
                    "duration_seconds",
                    "report_found",
                    "execution_mode",
                    "refresh_instruction",
                )
                if key in row
            }
        )
    if "task_runs" in summary:
        summary["task_runs"] = compact_runs
    return summary


def _is_newer_or_same(candidate_path, reference_path):
    try:
        if not os.path.exists(candidate_path):
            return False
        if not os.path.exists(reference_path):
            return True
        return os.path.getmtime(candidate_path) >= os.path.getmtime(reference_path)
    except Exception:
        return False


def _safe_float(value, digits=4):
    try:
        return round(float(value), digits)
    except Exception:
        return None


def _rightbrain_model_maturity_evidence(gate_report, holdout_report, multiseed_report=None):
    """Use model-loaded holdout evidence; fall back to the development gate."""
    gate_summary = (gate_report or {}).get("summary") or {}
    holdout_summary = (holdout_report or {}).get("summary") or {}
    promoted_summary = ((multiseed_report or {}).get("aggregate") or {}).get("promoted") or {}
    if (multiseed_report or {}).get("promotion_recommended") and promoted_summary:
        return {
            "raw_candidate_acceptance_rate": _safe_float(promoted_summary.get("raw_candidate_acceptance_rate")),
            "model_selected_case_rate": _safe_float(promoted_summary.get("model_selected_case_rate")),
            "final_contract_pass_rate": _safe_float(promoted_summary.get("final_quality_pass_rate")),
            "adapter_ref": (multiseed_report or {}).get("promoted_adapter"),
            "source": "rightbrain_runtime_adapter_multiseed_report.json",
        }
    if (holdout_report or {}).get("load_model") and holdout_summary.get("model_loaded"):
        return {
            "raw_candidate_acceptance_rate": _safe_float(holdout_summary.get("raw_candidate_acceptance_rate")),
            "model_selected_case_rate": _safe_float(holdout_summary.get("model_selected_case_rate")),
            "final_contract_pass_rate": _safe_float(holdout_summary.get("final_quality_pass_rate")),
            "adapter_ref": (holdout_report or {}).get("adapter_ref"),
            "source": "rightbrain_model_surface_holdout_report.json",
        }
    return {
        "raw_candidate_acceptance_rate": _safe_float(gate_summary.get("raw_candidate_acceptance_rate")),
        "model_selected_case_rate": _safe_float(gate_summary.get("model_selected_case_rate")),
        "final_contract_pass_rate": _safe_float(gate_summary.get("final_contract_pass_rate")),
        "adapter_ref": (gate_report or {}).get("adapter_ref"),
        "source": "rightbrain_model_gate_report.json",
    }


def _flatten_long_dialogue_memory_summary(summary):
    """Expose nested long-dialogue memory metrics for the unified scorecard."""
    summary = summary or {}
    delayed_recall = summary.get("delayed_recall") or {}
    speakability = summary.get("speakability") or {}
    flat = dict(summary)
    flat["delayed_recall"] = delayed_recall
    flat["speakability"] = speakability
    flat["delayed_recall_rate"] = delayed_recall.get("delayed_recall_rate")
    flat["memory_speakability_case_pass_rate"] = speakability.get("case_pass_rate")
    flat["memory_speakability_label_accuracy"] = speakability.get("label_accuracy")
    return flat


def _status_by_threshold(value, target, direction="higher"):
    if value is None:
        return "missing"
    if direction == "higher":
        if value >= target:
            return "good"
        if value >= target * 0.85:
            return "partial"
        return "weak"
    if value <= target:
        return "good"
    if value <= target * 1.25:
        return "partial"
    return "weak"


def _metric(name_zh, key, value, better, source, direction=None, note=""):
    return {
        "key": key,
        "name_zh": name_zh,
        "value": _safe_float(value),
        "better": better,
        "source": source,
        "direction": direction,
        "note": note,
    }


def _goal_item(name_zh, score, target, rationale, source_keys):
    return {
        "name_zh": name_zh,
        "score": _safe_float(score),
        "target": target,
        "status": _status_by_threshold(_safe_float(score), target, "higher"),
        "rationale": rationale,
        "source_keys": source_keys,
    }


def _required_min(*values):
    normalized = [_safe_float(value) for value in values]
    if any(value is None for value in normalized):
        return None
    return min(normalized)


def _diversity_acceptance_score(stress_summary):
    unique_ratio = _safe_float((stress_summary or {}).get("unique_reply_ratio")) or 0.0
    top20 = _safe_float((stress_summary or {}).get("top_20_reply_concentration"))
    if top20 is None:
        top20 = 1.0
    unique_score = min(1.0, unique_ratio / 0.08) if unique_ratio >= 0 else 0.0
    concentration_score = min(1.0, 0.35 / max(top20, 1e-9))
    return max(0.0, min(unique_score, concentration_score))


def _build_alignment_snapshot(
    arch,
    human,
    formal,
    stress,
    annotation,
    regression,
    regression_eval,
    regression_diff,
    speech_layer,
    memory_speakability_response,
    human_blind,
):
    tombench = ((formal or {}).get("summaries") or {}).get("tombench") or {}
    return {
        "working_memory_buffer": {
            "status": "implemented" if arch.get("working_memory_budget_adherence") == 1.0 else "partial",
            "metric": {
                "budget_adherence": _safe_float(arch.get("working_memory_budget_adherence")),
                "relevance_rate": _safe_float(arch.get("working_memory_relevance_rate")),
            },
            "detail": "長期記憶已先經過工作記憶過濾，再交給左腦規劃。",
        },
        "high_low_road_router": {
            "status": "implemented"
            if arch.get("high_road_precision") == 1.0 and arch.get("low_road_precision") == 1.0
            else "partial",
            "metric": {
                "high_road_precision": _safe_float(arch.get("high_road_precision")),
                "low_road_precision": _safe_float(arch.get("low_road_precision")),
            },
            "detail": "高低軌已實作，辱罵/危機可 bypass 深思考，正常對話仍走 deliberative 路徑。",
        },
        "bayesian_multi_plan": {
            "status": "implemented"
            if arch.get("bayesian_candidate_coverage") == 1.0 and arch.get("bayesian_probability_valid_rate") == 1.0
            else "partial",
            "metric": {
                "candidate_coverage": _safe_float(arch.get("bayesian_candidate_coverage")),
                "probability_valid_rate": _safe_float(arch.get("bayesian_probability_valid_rate")),
                "avg_planner_tick_count": _safe_float(arch.get("avg_planner_tick_count")),
            },
            "detail": "左腦會產生多候選計畫並重排序，不再是單一路徑輸出。",
        },
        "theory_of_mind_scratchpad": {
            "status": "implemented"
            if arch.get("scratchpad_presence_rate") == 1.0 and tombench.get("accuracy", 0) >= 0.65
            else "partial",
            "metric": {
                "scratchpad_presence_rate": _safe_float(arch.get("scratchpad_presence_rate")),
                "tom_subtext_proxy_rate": _safe_float(arch.get("tom_subtext_proxy_rate")),
                "formal_tombench_accuracy": _safe_float(tombench.get("accuracy")),
            },
            "detail": "Scratchpad 已每輪存在，但正式社會推理分數仍是主要瓶頸。",
        },
        "idle_memory_consolidation": {
            "status": "implemented" if arch.get("idle_consolidation_success") == 1.0 else "partial",
            "metric": {
                "idle_consolidation_success": _safe_float(arch.get("idle_consolidation_success")),
                "idle_rule_rate": _safe_float(arch.get("idle_consolidation_rule_rate")),
                "idle_procedural_rate": _safe_float(arch.get("idle_consolidation_procedural_rate")),
            },
            "detail": "背景鞏固與程序化寫入已接上，但還不是完整三速衰減模型。",
        },
        "direct_answer_humanness": {
            "status": "implemented"
            if human.get("direct_answer_rate_on_simple_queries", 0) >= 0.95 and human.get("over_reframe_rate", 1.0) <= 0.03
            else "partial",
            "metric": {
                "direct_answer_rate_on_simple_queries": _safe_float(human.get("direct_answer_rate_on_simple_queries")),
                "over_reframe_rate": _safe_float(human.get("over_reframe_rate")),
                "avg_role_similarity_1_to_5": _safe_float(human.get("avg_role_similarity_1_to_5")),
            },
            "detail": "簡單問題大多能直接答，不會像舊版那樣逢題拆解。",
        },
        "mass_scale_diversity": {
            "status": "partial"
            if stress.get("unique_reply_ratio", 0) < 0.08 or stress.get("top_20_reply_concentration", 1.0) > 0.35
            else "implemented",
            "metric": {
                "unique_reply_ratio": _safe_float(stress.get("unique_reply_ratio")),
                "top_20_reply_concentration": _safe_float(stress.get("top_20_reply_concentration")),
            },
            "detail": "10k 壓測下規劃穩定，但表面回覆仍有模板集中問題。",
        },
        "human_feedback_annotation_loop": {
            "status": "implemented" if (annotation or {}).get("annotation_count", 0) > 0 else "partial",
            "metric": {
                "annotation_count": _safe_float((annotation or {}).get("annotation_count"), digits=0),
                "fail_like_rate": _safe_float((annotation or {}).get("fail_like_rate")),
                "memory_related_rate": _safe_float((annotation or {}).get("memory_related_rate")),
            },
            "detail": "人工標記與 taxonomy 已接上，annotation_count 只計入可追溯的人類標記，不把自動評分冒充成人工真值。",
        },
        "human_blind_validation": {
            "status": "implemented"
            if (human_blind or {}).get("s0_annotation_count", 0) >= 30
            and (human_blind or {}).get("s0_chat_ready_yes_rate", 0) >= 0.75
            else "partial",
            "metric": {
                "s0_annotation_count": _safe_float((human_blind or {}).get("s0_annotation_count"), digits=0),
                "s0_normalized_mean_score": _safe_float((human_blind or {}).get("s0_normalized_mean_score")),
                "s0_chat_ready_yes_rate": _safe_float((human_blind or {}).get("s0_chat_ready_yes_rate")),
                "s0_chat_ready_acceptable_rate": _safe_float((human_blind or {}).get("s0_chat_ready_acceptable_rate")),
            },
            "detail": "盲評已接入正式證據鏈；目前樣本仍小，嚴格可聊天率未達研究目標，因此只列 partial。",
        },
        "human_feedback_regression_loop": {
            "status": "implemented" if (regression_eval or {}).get("total_cases", 0) > 0 else "partial",
            "metric": {
                "regression_case_count": _safe_float((regression or {}).get("regression_case_count"), digits=0),
                "overall_auto_pass_rate": _safe_float((regression_eval or {}).get("overall_auto_pass_rate")),
                "generic_reply_rate": _safe_float((regression_eval or {}).get("generic_reply_rate")),
            },
            "detail": "從人工標記抽 regression case、重播回腦、再做自動檢查的閉環已成形；通過率只代表已收錄案例，不外推到所有對話。",
        },
        "patch_diff_regression": {
            "status": "implemented" if (regression_diff or {}).get("metric_count", 0) > 0 else "partial",
            "metric": {
                "improved_metric_count": _safe_float((regression_diff or {}).get("improved_metric_count"), digits=0),
                "regressed_metric_count": _safe_float((regression_diff or {}).get("regressed_metric_count"), digits=0),
                "unchanged_metric_count": _safe_float((regression_diff or {}).get("unchanged_metric_count"), digits=0),
            },
            "detail": "Patch 前後 diff report 已可建立；真正有辨識力要等 regression cases 進來後，才能看到哪些 fail case 被修掉。",
        },
        "human_speech_realization_layer": {
            "status": "implemented"
            if (speech_layer or {}).get("pass_rate", 0) >= 0.9
            else "partial",
            "metric": {
                "pass_rate": _safe_float((speech_layer or {}).get("pass_rate")),
                "speech_plan_presence_rate": _safe_float((speech_layer or {}).get("speech_plan_presence_rate")),
                "dialogue_act_match_rate": _safe_float((speech_layer or {}).get("dialogue_act_match_rate")),
                "semantic_anchor_hit_rate": _safe_float((speech_layer or {}).get("semantic_anchor_hit_rate")),
                "english_leak_rate": _safe_float((speech_layer or {}).get("english_leak_rate")),
            },
            "detail": "右腦前新增語用功能、語意單元、風格算子與自檢，用來把『回答』轉成更像人類的口語行為。",
        },
        "memory_speakability_response_layer": {
            "status": "implemented"
            if (memory_speakability_response or {}).get("case_pass_rate", 0) >= 0.9
            else "partial",
            "metric": {
                "case_pass_rate": _safe_float((memory_speakability_response or {}).get("case_pass_rate")),
                "speakability_accuracy": _safe_float((memory_speakability_response or {}).get("speakability_accuracy")),
                "explicit_contract_accuracy": _safe_float((memory_speakability_response or {}).get("explicit_contract_accuracy")),
                "forbidden_intrusion_rate": _safe_float((memory_speakability_response or {}).get("forbidden_intrusion_rate")),
                "plan_leak_rate": _safe_float((memory_speakability_response or {}).get("plan_leak_rate")),
            },
            "detail": "記憶不只要被找回，還要決定最後一句是否該明講、只當背景、或因敏感/第三方資訊而不說出口。",
        },
    }


def main():
    arch_report = _load_json(REPORT_PATHS["architecture"])
    runtime_report = _load_json(REPORT_PATHS["runtime"])
    memory_report = _load_json(REPORT_PATHS["memory"])
    memory_causal_report = _load_json(REPORT_PATHS["memory_causal_effect"])
    memory_speakability_response_report = _load_json(REPORT_PATHS["memory_speakability_response"])
    diversity_report = _load_json(REPORT_PATHS["diversity"])
    human_report = _load_json(REPORT_PATHS["human_answer"])
    daily_state_self_distress_report = _load_json(REPORT_PATHS["daily_state_self_distress"])
    self_distress_surface_contract_report = _load_json(REPORT_PATHS["self_distress_surface_contract"])
    support_prefix_contract_report = _load_json(REPORT_PATHS["support_prefix_contract"])
    formal_report = _load_json(REPORT_PATHS["formal"])
    formal_tombench_refresh = _load_json(REPORT_PATHS["formal_tombench_refresh"])
    domain_suite = _load_json(REPORT_PATHS["domain_suite"])
    compact_domain_suite = _compact_domain_suite_summary(domain_suite)
    stress_report = _load_json(REPORT_PATHS["stress_10k"])
    compare_report = _load_json(REPORT_PATHS["system_vs_prompt"])
    human_blind_report = _load_json(REPORT_PATHS["human_blind"])
    annotation_report = _load_json(REPORT_PATHS["human_feedback_annotation"])
    annotation_candidate_report = _load_json(REPORT_PATHS["annotation_candidate_queue"])
    annotation_draft_report = _load_json(REPORT_PATHS["annotation_draft_queue"])
    regression_report = _load_json(REPORT_PATHS["human_feedback_regression"])
    regression_eval_report = _load_json(REPORT_PATHS["human_feedback_regression_eval"])
    regression_diff_report = _load_json(REPORT_PATHS["human_feedback_regression_diff"])
    speech_layer_report = _load_json(REPORT_PATHS["human_speech_layer"])
    surface_microplanning_report = _load_json(REPORT_PATHS["surface_microplanning"])
    rightbrain_model_gate_report = _load_json(REPORT_PATHS["rightbrain_model_gate"])
    rightbrain_model_surface_holdout_report = _load_json(REPORT_PATHS["rightbrain_model_surface_holdout"])
    rightbrain_runtime_adapter_multiseed_report = _load_json(
        REPORT_PATHS["rightbrain_runtime_adapter_multiseed"]
    )

    arch = arch_report.get("summary", {})
    runtime = runtime_report.get("summary", {})
    memory = _flatten_long_dialogue_memory_summary(memory_report.get("summary", {}))
    memory_causal = memory_causal_report.get("summary", {})
    memory_speakability_response = memory_speakability_response_report.get("summary", {})
    memory_causal_alignment_rate = memory_causal.get("appropriate_memory_effect_rate")
    if memory_causal_alignment_rate is None:
        memory_causal_alignment_rate = memory_causal.get("strong_causal_effect_rate")
    diversity = diversity_report.get("summary", {})
    human = human_report.get("summary", {})
    daily_state_self_distress = daily_state_self_distress_report.get("summary", {})
    self_distress_surface_contract = self_distress_surface_contract_report.get("summary", {})
    support_prefix_contract = support_prefix_contract_report.get("summary", {})
    formal = formal_report.get("summaries", {})
    if (formal_tombench_refresh or {}).get("summary") and _is_newer_or_same(
        REPORT_PATHS["formal_tombench_refresh"],
        REPORT_PATHS["formal"],
    ):
        formal = dict(formal)
        formal["tombench"] = formal_tombench_refresh["summary"]
    stress = stress_report.get("summary", {})
    compare = compare_report.get("overall_compare", {})
    human_blind = human_blind_report.get("summary", {})
    human_blind_pairs = {
        item.get("control_system_id"): item
        for item in human_blind_report.get("pairwise_s0_vs_controls", [])
    }
    annotation = annotation_report.get("summary", {})
    annotation_queue = annotation_candidate_report.get("summary", {})
    annotation_draft = annotation_draft_report.get("summary", {})
    regression = regression_report.get("summary", {})
    regression_eval = regression_eval_report.get("summary", {})
    regression_diff = regression_diff_report.get("summary", {})
    speech_layer = speech_layer_report.get("metrics", {})
    surface_microplanning = surface_microplanning_report.get("summary", {})
    rightbrain_model_gate = rightbrain_model_gate_report.get("summary", {})
    rightbrain_model_maturity = _rightbrain_model_maturity_evidence(
        rightbrain_model_gate_report,
        rightbrain_model_surface_holdout_report,
        rightbrain_runtime_adapter_multiseed_report,
    )
    speech_english_leak = _safe_float(speech_layer.get("english_leak_rate"))
    speech_english_safe = 1.0 - (speech_english_leak if speech_english_leak is not None else 1.0)

    # Use standalone reports as source-of-truth to avoid stale nested snapshots in domain_eval_suite_report.json.
    latest_metrics = [
        _metric(
            "高低軌路由命中率",
            "route_match_rate",
            arch.get("route_match_rate"),
            "越高越好",
            "cognitive_architecture_eval_report.json",
            "higher",
            "代表高低軌路由是否有按設計觸發。",
        ),
        _metric(
            "工作記憶相關率",
            "working_memory_relevance_rate",
            arch.get("working_memory_relevance_rate"),
            "越高越好",
            "cognitive_architecture_eval_report.json",
            "higher",
            "代表送進左腦的工作記憶是否真的和當輪問題有關。",
        ),
        _metric(
            "簡單問題直接回答率",
            "direct_answer_rate_on_simple_queries",
            human.get("direct_answer_rate_on_simple_queries"),
            "越高越好",
            "v2_human_answer_report.json",
            "higher",
            "代表像『你在幹嘛』『要不要吃蘋果派』這類問題，模型有沒有直接回答。",
        ),
        _metric(
            "日常狀態/自我痛苦細分通過率",
            "daily_state_self_distress_case_pass_rate",
            daily_state_self_distress.get("case_pass_rate"),
            "越高越好",
            "daily_state_self_distress_report.json",
            "higher",
            "代表系統能否把疲累、羞恥、空洞、撐不住、危機句、直接辱罵分到不同支援行為，而不是全部當成泛用疲累。",
        ),
        _metric(
            "自我痛苦最終回覆契約通過率",
            "self_distress_surface_contract_case_pass_rate",
            self_distress_surface_contract.get("case_pass_rate"),
            "越高越好",
            "self_distress_surface_contract_report.json",
            "higher",
            "代表左腦分出的羞恥、空洞、撐不住、危機與直接辱罵，是否真的在右腦最後一句保留下來，而不是退回疲累模板。",
        ),
        _metric(
            "支援回覆固定前綴率",
            "support_fixed_prefix_rate",
            support_prefix_contract.get("fixed_prefix_rate"),
            "越低越好",
            "support_prefix_contract_report.json",
            "lower",
            "代表支援類最後一句是否避免固定開頭，例如『普通に、』『てか、』『はいはい、』。",
        ),
        _metric(
            "過度拆題率",
            "over_reframe_rate",
            human.get("over_reframe_rate"),
            "越低越好",
            "v2_human_answer_report.json",
            "lower",
            "代表本來該直接回的題目，被錯誤改寫成追問/重構的比例。",
        ),
        _metric(
            "正式心智理論分數",
            "formal_tombench_accuracy",
            (formal.get("tombench") or {}).get("accuracy"),
            "越高越好",
            "formal_brain_benchmarks_report.json",
            "higher",
            "代表對故事人物的想法、情緒、信念與隱含意圖的推理能力。",
        ),
        _metric(
            "長對話延遲回憶率",
            "delayed_recall_rate",
            memory.get("delayed_recall_rate"),
            "越高越好",
            "long_dialogue_memory_report.json",
            "higher",
            "代表隔幾輪後還能不能記得前面講過的偏好與資訊。",
        ),
        _metric(
            "記憶適切因果效果率",
            "memory_causal_appropriate_effect_rate",
            memory_causal_alignment_rate,
            "越高越好",
            "memory_causal_effect_report.json",
            "higher",
            "代表該用記憶時回答會受記憶影響，不該用時則不會把無關、敏感或第三方記憶硬塞進回覆。",
        ),
        _metric(
            "不當記憶侵入率",
            "unwanted_memory_intrusion_rate",
            memory_causal.get("unwanted_memory_intrusion_rate"),
            "越低越好",
            "memory_causal_effect_report.json",
            "lower",
            "代表無關、敏感或第三方記憶在不該出現的回覆中被明講或被判定應顯性使用的比例。",
        ),
        _metric(
            "記憶顯性使用率",
            "memory_used_explicitly_rate",
            memory_causal.get("memory_used_explicitly_rate"),
            "越高越好",
            "memory_causal_effect_report.json",
            "higher",
            "代表系統判定應使用記憶時，最終日文回答是否真的顯性使用那條記憶。",
        ),
        _metric(
            "記憶輸出契約通過率",
            "memory_speakability_response_case_pass_rate",
            memory_speakability_response.get("case_pass_rate"),
            "越高越好",
            "memory_speakability_response_report.json",
            "higher",
            "代表最後一句話是否正確處理記憶：直接問才明講，相關但未被問到只當背景，敏感或第三方資訊不亂說。",
        ),
        _metric(
            "小樣本回覆獨特率",
            "overall_unique_ratio",
            diversity.get("overall_unique_ratio"),
            "越高越好",
            "reply_diversity_report.json",
            "higher",
            "代表同類問題下是否會一直回幾乎一樣的句子。",
        ),
        _metric(
            "10k 回覆獨特率",
            "stress_unique_reply_ratio",
            stress.get("unique_reply_ratio"),
            "越高越好",
            "stress_eval_report_10000.json",
            "higher",
            "代表大量壓測下的表面回覆是否仍有變化。",
        ),
        _metric(
            "10k 前 20 回覆集中率",
            "stress_top_20_reply_concentration",
            stress.get("top_20_reply_concentration"),
            "越低越好",
            "stress_eval_report_10000.json",
            "lower",
            "代表是不是太多題都被少數固定句型吃掉。",
        ),
        _metric(
            "10k 壓測整體通過率",
            "overall_pass_rate",
            stress.get("overall_pass_rate"),
            "越高越好",
            "stress_eval_report_10000.json",
            "higher",
            "代表控制器層級的規劃、邊界與必要標記是否穩定。",
        ),
        _metric(
            "待標註候選數",
            "annotation_candidate_count",
            annotation_queue.get("candidate_count"),
            "越高越好",
            "annotation_candidate_queue.json",
            "higher",
            "代表從真實 Web 對話 log 中自動挖出的疑似失敗案例數量。",
        ),
        _metric(
            "高優先待標註候選數",
            "annotation_high_priority_count",
            annotation_queue.get("high_priority_count"),
            "越高越好",
            "annotation_candidate_queue.json",
            "higher",
            "代表最值得先看、先標的高風險對話有多少。",
        ),
        _metric(
            "待確認 annotation draft 數",
            "annotation_draft_count",
            annotation_draft.get("draft_count"),
            "越高越好",
            "annotation_draft_queue.json",
            "higher",
            "代表已經被整理成可直接載入 Human Annotation 表單的候選草稿數量。",
        ),
        _metric(
            "高優先 annotation draft 數",
            "annotation_high_priority_draft_count",
            annotation_draft.get("high_priority_draft_count"),
            "越高越好",
            "annotation_draft_queue.json",
            "higher",
            "代表可直接優先人工確認的高風險草稿數量。",
        ),
        _metric(
            "人類盲評正規化平均分",
            "human_blind_s0_normalized_mean_score",
            human_blind.get("s0_normalized_mean_score"),
            "越高越好",
            "human_blind_evidence_report.json",
            "higher",
            "代表真人在不知道系統身分時，對完整 Uruha 右腦候選給出的平均品質；1.0 等於五分制滿分。",
        ),
        _metric(
            "人類盲評嚴格可聊天率",
            "human_blind_s0_chat_ready_yes_rate",
            human_blind.get("s0_chat_ready_yes_rate"),
            "越高越好",
            "human_blind_evidence_report.json",
            "higher",
            "只計算明確選 yes 的比例；borderline 不算成功，因此比一般可接受率嚴格。",
        ),
        _metric(
            "人類盲評對通用改寫勝率",
            "human_blind_s0_vs_generic_win_rate",
            (human_blind_pairs.get("C1_GENERIC_PARAPHRASE_PROXY") or {}).get("s0_win_rate_excluding_ties"),
            "越高越好",
            "human_blind_evidence_report.json",
            "higher",
            "同一題配對比較完整 Uruha 與通用 LLM 改寫，平手不計入分母。",
        ),
        _metric(
            "人工標記回歸整體通過率",
            "human_feedback_regression_overall_auto_pass_rate",
            regression_eval.get("overall_auto_pass_rate"),
            "越高越好",
            "human_feedback_regression_eval_report.json",
            "higher",
            "代表真實人工 fail case 被重播時，系統能否在 focus / obligation / memory / generic-reply 等條件下過關。",
        ),
        _metric(
            "人工標記回歸通用空話率",
            "human_feedback_regression_generic_reply_rate",
            regression_eval.get("generic_reply_rate"),
            "越低越好",
            "human_feedback_regression_eval_report.json",
            "lower",
            "代表回放真實壞案例時，是否仍大量掉回『別にいいけど』『そうなんだ』這類空泛句型。",
        ),
        _metric(
            "Planner 語意契約新舊輸出命中差",
            "planner_contract_group_hit_delta",
            regression_eval.get("planner_contract_group_hit_delta"),
            "越高越好",
            "human_feedback_regression_eval_report.json",
            "higher",
            "同一份目前 planner 語意群套用到舊輸出與新回放的配對差；只衡量具體語意保留，不等於真人自然度。",
        ),
        _metric(
            "Patch Diff 改善指標數",
            "human_feedback_regression_diff_improved_metric_count",
            regression_diff.get("improved_metric_count"),
            "越高越好",
            "human_feedback_regression_diff_report.json",
            "higher",
            "代表和 baseline 相比，有多少 regression 指標真的往對的方向移動。",
        ),
        _metric(
            "Patch Diff 退步指標數",
            "human_feedback_regression_diff_regressed_metric_count",
            regression_diff.get("regressed_metric_count"),
            "越低越好",
            "human_feedback_regression_diff_report.json",
            "lower",
            "代表 patch 後是否引入新的 regression。",
        ),
        _metric(
            "人類說話層整體通過率",
            "human_speech_layer_pass_rate",
            speech_layer.get("pass_rate"),
            "越高越好",
            "human_speech_layer_eval_report.json",
            "higher",
            "代表右腦輸出前的語用功能、內容密度、語意錨點與禁用重複約束是否正常。",
        ),
        _metric(
            "人類說話層語用功能命中率",
            "human_speech_layer_dialogue_act_match_rate",
            speech_layer.get("dialogue_act_match_rate"),
            "越高越好",
            "human_speech_layer_eval_report.json",
            "higher",
            "代表系統是否把一句話先轉成社交行為，例如安撫、吐槽、邊界回應、記憶說明，而不是只做問答。",
        ),
        _metric(
            "表面微規劃技術契約通過率",
            "surface_microplanning_case_pass_rate",
            surface_microplanning.get("case_pass_rate"),
            "越高越好",
            "surface_microplanning_report.json",
            "higher",
            "只驗證未載入 runtime 的技術集合中，語境、風險、言語動作與禁止過度反應是否成立；不等同真人自然度。",
        ),
        _metric(
            "正常日常操作危機誤報率",
            "surface_microplanning_benign_false_alarm_rate",
            surface_microplanning.get("benign_false_alarm_rate"),
            "越低越好",
            "surface_microplanning_report.json",
            "lower",
            "檢查專心、容量整理、通知省電、暫時離群等正常操作是否被錯當成社交撤退。",
        ),
        _metric(
            "真實右腦模型 raw 候選契約接受率",
            "rightbrain_model_raw_candidate_acceptance_rate",
            rightbrain_model_maturity.get("raw_candidate_acceptance_rate"),
            "越高越好",
            rightbrain_model_maturity.get("source"),
            "higher",
            "只計算 Qwen + LoRA 原始候選能否通過語意、語言、風險與口吻 gate；不把 deterministic 救援算成模型能力。",
        ),
        _metric(
            "右腦模型接入後最終契約通過率",
            "rightbrain_model_final_contract_pass_rate",
            rightbrain_model_gate.get("final_contract_pass_rate"),
            "越高越好",
            "rightbrain_model_gate_report.json",
            "higher",
            "模型候選不合格時必須退回 deterministic，確保最終輸出不因模型接入而漏掉左腦語意。",
        ),
    ]

    goal_attainment = [
        _goal_item(
            "像人類地直接回答",
            _required_min(
                human.get("direct_answer_rate_on_simple_queries"),
                (1.0 - _safe_float(human.get("over_reframe_rate")))
                if _safe_float(human.get("over_reframe_rate")) is not None
                else None,
            ),
            0.95,
            "這項高表示模型不會逢題拆題，簡單對話能直接回應。",
            ["v2_human_answer_report.json.summary.direct_answer_rate_on_simple_queries", "v2_human_answer_report.json.summary.over_reframe_rate"],
        ),
        _goal_item(
            "像人類地維持工作記憶",
            _required_min(
                arch.get("working_memory_relevance_rate"),
                memory.get("delayed_recall_rate"),
                memory_causal_alignment_rate,
                memory_speakability_response.get("case_pass_rate"),
            ),
            0.9,
            "這項高表示不是把所有記憶亂塞進左腦，而是能抓住真正相關的少量資訊，讓記憶實際改變回答，且最後一句知道何時該說、何時不該說。",
            [
                "cognitive_architecture_eval_report.json.summary.working_memory_relevance_rate",
                "long_dialogue_memory_report.json.summary.delayed_recall.delayed_recall_rate",
                "memory_causal_effect_report.json.summary.appropriate_memory_effect_rate",
                "memory_speakability_response_report.json.summary.case_pass_rate",
            ],
        ),
        _goal_item(
            "像人類地做多路徑思考",
            _required_min(
                arch.get("bayesian_candidate_coverage"),
                arch.get("scratchpad_presence_rate"),
            ),
            1.0,
            "這項高表示左腦不是單一路徑，而是有候選計畫、scratchpad 與 rerank。",
            ["cognitive_architecture_eval_report.json.summary.bayesian_candidate_coverage", "cognitive_architecture_eval_report.json.summary.scratchpad_presence_rate"],
        ),
        _goal_item(
            "像人類地推測別人心思",
            (formal.get("tombench") or {}).get("accuracy"),
            0.65,
            "這項高表示模型不只會回話，還能在故事任務裡推測他人信念、情緒與隱含意圖。",
            ["formal_brain_benchmarks_report.json.summaries.tombench.accuracy"],
        ),
        _goal_item(
            "像人類地避免模板化",
            _diversity_acceptance_score(stress),
            0.65,
            "這項高表示同類題目不會一直掉進同一句模板。",
            ["stress_eval_report_10000.json.summary.unique_reply_ratio", "stress_eval_report_10000.json.summary.top_20_reply_concentration"],
        ),
        _goal_item(
            "像人類地延續真正未完成的話題",
            _required_min(
                runtime.get("autonomous_open_loop_detection_accuracy"),
                runtime.get("autonomous_open_loop_key_accuracy"),
                runtime.get("autonomous_open_loop_followup_rate"),
                runtime.get("autonomous_proactive_semantic_match_rate"),
                runtime.get("autonomous_proactive_delivery_rate"),
                runtime.get("autonomous_proactive_memory_record_rate"),
                runtime.get("autonomous_duplicate_suppression_rate"),
            )
            if (runtime.get("autonomous_open_loop_eligible_count") or 0) > 0
            else None,
            0.9,
            (
                "這項高表示系統只在話題確實缺少資訊時，沉默後主動追問一次並真正交付；"
                f"目前可歸因樣本數為 {int(runtime.get('autonomous_open_loop_eligible_count') or 0)}，仍需擴大情境。"
            ),
            [
                "runtime_dynamics_report.json.summary.autonomous_open_loop_detection_accuracy",
                "runtime_dynamics_report.json.summary.autonomous_open_loop_key_accuracy",
                "runtime_dynamics_report.json.summary.autonomous_open_loop_followup_rate",
                "runtime_dynamics_report.json.summary.autonomous_proactive_semantic_match_rate",
                "runtime_dynamics_report.json.summary.autonomous_proactive_delivery_rate",
                "runtime_dynamics_report.json.summary.autonomous_proactive_memory_record_rate",
                "runtime_dynamics_report.json.summary.autonomous_duplicate_suppression_rate",
            ],
        ),
        _goal_item(
            "在人類盲評中自然且可直接聊天",
            min(
                _safe_float(human_blind.get("s0_normalized_mean_score")) or 0.0,
                _safe_float(human_blind.get("s0_chat_ready_yes_rate")) or 0.0,
            )
            if (human_blind.get("s0_annotation_count") or 0) > 0
            else None,
            0.75,
            (
                "這項同時受真人平均品質與嚴格 yes 率限制，避免只靠內部規則測試宣稱像人；"
                f"目前有效 S0 標記為 {int(human_blind.get('s0_annotation_count') or 0)} 筆。"
            ),
            [
                "human_blind_evidence_report.json.summary.s0_normalized_mean_score",
                "human_blind_evidence_report.json.summary.s0_chat_ready_yes_rate",
            ],
        ),
        _goal_item(
            "在技術契約下重播人工失敗案例",
            regression_eval.get("overall_auto_pass_rate") if (regression_eval.get("total_cases") or 0) > 0 else None,
            0.75,
            "這項高只表示人工 fail case 的必要語意、禁止語句與表面規則可重播通過；它不能代替 patch 後的人類自然度盲評。",
            ["human_feedback_regression_eval_report.json.summary.overall_auto_pass_rate"],
        ),
        _goal_item(
            "像人類地把意圖變成口語行為",
            min(
                _safe_float(speech_layer.get("speech_plan_presence_rate")) or 0.0,
                _safe_float(speech_layer.get("dialogue_act_match_rate")) or 0.0,
                _safe_float(speech_layer.get("semantic_anchor_hit_rate")) or 0.0,
                speech_english_safe,
            ),
            0.9,
            "這項高表示右腦不是只把左腦結論念出來，而是先經過語用功能、語意單元與風格算子的表面化流程。",
            ["human_speech_layer_eval_report.json.metrics"],
        ),
        _goal_item(
            "依語境與風險組織支援回覆",
            _required_min(
                surface_microplanning.get("routing_contract_rate"),
                surface_microplanning.get("risk_calibration_rate"),
                surface_microplanning.get("context_specificity_rate"),
                surface_microplanning.get("speech_move_contract_rate"),
                (1.0 - _safe_float(surface_microplanning.get("benign_false_alarm_rate")))
                if _safe_float(surface_microplanning.get("benign_false_alarm_rate")) is not None
                else None,
            ),
            0.9,
            "這項高表示支援回覆會先保留具體情境與使用者選擇，再按風險加入界線和下一步；它仍是技術契約，不取代真人盲評。",
            ["surface_microplanning_report.json.summary"],
        ),
        _goal_item(
            "安全地接入真實右腦模型候選",
            _required_min(
                rightbrain_model_gate.get("policy_match_rate"),
                rightbrain_model_gate.get("final_contract_pass_rate"),
                rightbrain_model_gate.get("final_language_clean_rate"),
                rightbrain_model_gate.get("fallback_protection_rate"),
            ),
            0.95,
            "這項高只證明模型候選接入不會破壞最終回答；raw 模型是否成熟需另外看候選接受率與實際接管率。",
            ["rightbrain_model_gate_report.json.summary"],
        ),
    ]

    weak_points = [
        {
            "id": "raw_rightbrain_model_maturity",
            "name_zh": "真實右腦模型本體仍無法穩定實現 speech plan",
            "current": {
                "raw_candidate_acceptance_rate": rightbrain_model_maturity.get("raw_candidate_acceptance_rate"),
                "model_selected_case_rate": rightbrain_model_maturity.get("model_selected_case_rate"),
                "final_contract_pass_rate": rightbrain_model_maturity.get("final_contract_pass_rate"),
                "adapter_ref": rightbrain_model_maturity.get("adapter_ref"),
            },
            "target": {
                "raw_candidate_acceptance_rate": 0.6,
                "model_selected_case_rate": 0.2,
                "final_contract_pass_rate": 0.99,
            },
            "better": "前兩者越高越好，最終契約必須維持接近 1",
            "why_it_matters": "目前自然度主要仍由 deterministic 候選提供；如果 raw LoRA 長期進不了 gate，就不能說模型本體已學會把思考轉成自然說話。",
            "acceptance": "開發集 raw 接受率 >= 0.6、至少部分情境由模型勝出，且最終契約 >= 0.99。",
            "planned_fix": "以 rejection trace 建立 speech-plan slot 訓練資料，優先修正槽位遺失、英文字串污染、過長與敬語漂移，而不是放寬 gate。",
            "source": rightbrain_model_maturity.get("source"),
        },
        {
            "id": "formal_tom_reasoning",
            "name_zh": "正式 ToM / 社會推理仍弱",
            "current": _safe_float((formal.get("tombench") or {}).get("accuracy")),
            "target": 0.65,
            "better": "越高越好",
            "why_it_matters": "這項低時，系統雖然能表面聊天，但對故事中的『誰知道什麼、誰想表達什麼、誰其實在暗示什麼』仍不夠像人。",
            "acceptance": "ToMBench accuracy >= 0.65，且低分 task 不再大量出現 0 分子項。",
            "planned_fix": "補強左腦的 hidden-intent 與 scratchpad，讓 benchmark 類題目明確區分 belief / desire / emotion / communicative intent / action prediction。",
            "source": "formal_brain_benchmarks_report.json",
        },
        {
            "id": "mass_scale_reply_diversity",
            "name_zh": "10k 壓測下表面回覆仍太集中",
            "current": {
                "unique_reply_ratio": _safe_float(stress.get("unique_reply_ratio")),
                "top_20_reply_concentration": _safe_float(stress.get("top_20_reply_concentration")),
            },
            "target": {
                "unique_reply_ratio": 0.08,
                "top_20_reply_concentration": 0.35,
            },
            "better": "前者越高越好，後者越低越好",
            "why_it_matters": "這項差時，系統會出現『控制器很穩，但說出來像模板』的問題。",
            "acceptance": "10k unique_reply_ratio >= 0.08 且 top_20_reply_concentration <= 0.35。",
            "planned_fix": "擴大表面回覆變體池、強化公式化句子懲罰、讓特定地面詞與情境詞更常被帶入最終句子。",
            "source": "stress_eval_report_10000.json",
        },
        {
            "id": "daily_state_and_self_distress_handoff",
            "name_zh": "日常狀態句與自我痛苦句仍有誤判空間",
            "current": {
                "direct_daily_state_mode_match_rate": _safe_float(((human.get("category_breakdown") or {}).get("direct_daily_state") or {}).get("mode_match_rate")),
                "direct_daily_state_over_reframe_rate": _safe_float(((human.get("category_breakdown") or {}).get("direct_daily_state") or {}).get("over_reframe_rate")),
            },
            "target": {
                "direct_daily_state_mode_match_rate": 0.98,
                "direct_daily_state_over_reframe_rate": 0.02,
            },
            "better": "前者越高越好，後者越低越好",
            "why_it_matters": "這項差時，像『我今天很累』『我很丟臉』『我快撐不住了』這類句子可能被誤分到歌詞/辱罵/冷處理，情緒承接就會斷掉。",
            "acceptance": "direct_daily_state mode_match_rate >= 0.98，且相關 worst cases 明顯減少。",
            "planned_fix": "補強 self-distress guard 與 daily-state 判斷，避免 lyric_probe 或 boundary 路由吃掉真正的求助/狀態報告。",
            "source": "v2_human_answer_report.json",
        },
        {
            "id": "human_blind_chat_readiness",
            "name_zh": "真人盲評的嚴格可聊天率仍不足",
            "current": {
                "s0_annotation_count": _safe_float(human_blind.get("s0_annotation_count"), digits=0),
                "s0_normalized_mean_score": _safe_float(human_blind.get("s0_normalized_mean_score")),
                "s0_chat_ready_yes_rate": _safe_float(human_blind.get("s0_chat_ready_yes_rate")),
                "s0_chat_ready_acceptable_rate": _safe_float(human_blind.get("s0_chat_ready_acceptable_rate")),
            },
            "target": {
                "s0_annotation_count": 30,
                "s0_normalized_mean_score": 0.8,
                "s0_chat_ready_yes_rate": 0.75,
            },
            "better": "越高越好",
            "why_it_matters": "自動測試能證明契約沒有消失，但只有真人盲評能判斷回覆是否真的自然、願意繼續聊。",
            "acceptance": "至少 30 筆有效 S0 盲評，正規化均分 >= 0.8，嚴格 yes 率 >= 0.75。",
            "planned_fix": "優先修正盲評中重複出現的語意流失、公式化與意圖誤讀，再用新 holdout 盲評驗證泛化。",
            "source": "human_blind_evidence_report.json",
        },
        {
            "id": "human_feedback_regression_population",
            "name_zh": "人工標記回歸集尚未累積到可用規模",
            "current": {
                "annotation_count": _safe_float(annotation.get("annotation_count"), digits=0),
                "regression_case_count": _safe_float(regression.get("regression_case_count"), digits=0),
            },
            "target": {
                "annotation_count": 50,
                "regression_case_count": 30,
            },
            "better": "越高越好",
            "why_it_matters": "如果沒有足夠多的真實 fail case，patch 前後 diff 只能驗證流程，不能真正代表『你在修什麼』。",
            "acceptance": "至少累積 50 筆人工標記，並轉出 30 筆以上可回放的 regression cases。",
            "planned_fix": "持續用 Web UI 標記真實錯誤，尤其是 LOW_DENSITY / MISSED_VIBE / GHOST_MEMORY 類型，讓 regression loop 開始有資料密度。",
            "source": "human_feedback_annotation_report.json + human_feedback_regression_report.json",
        },
    ]
    weak_points = [
        item
        for item in weak_points
        if not (
            item["id"] == "raw_rightbrain_model_maturity"
            and (rightbrain_model_maturity.get("raw_candidate_acceptance_rate") or 0.0) >= 0.6
            and (rightbrain_model_maturity.get("model_selected_case_rate") or 0.0) >= 0.2
            and (rightbrain_model_maturity.get("final_contract_pass_rate") or 0.0) >= 0.99
        )
        and not (
            item["id"] == "formal_tom_reasoning"
            and (_safe_float((formal.get("tombench") or {}).get("accuracy")) or 0.0) >= 0.65
        )
        and not (
            item["id"] == "daily_state_and_self_distress_handoff"
            and (_safe_float(((human.get("category_breakdown") or {}).get("direct_daily_state") or {}).get("mode_match_rate")) or 0.0) >= 0.98
            and _safe_float(((human.get("category_breakdown") or {}).get("direct_daily_state") or {}).get("over_reframe_rate")) is not None
            and _safe_float(((human.get("category_breakdown") or {}).get("direct_daily_state") or {}).get("over_reframe_rate")) <= 0.02
        )
        and not (
            item["id"] == "mass_scale_reply_diversity"
            and (_safe_float(stress.get("unique_reply_ratio")) or 0.0) >= 0.08
            and (_safe_float(stress.get("top_20_reply_concentration")) or 1.0) <= 0.35
        )
        and not (
            item["id"] == "human_blind_chat_readiness"
            and (_safe_float(human_blind.get("s0_annotation_count")) or 0.0) >= 30
            and (_safe_float(human_blind.get("s0_normalized_mean_score")) or 0.0) >= 0.8
            and (_safe_float(human_blind.get("s0_chat_ready_yes_rate")) or 0.0) >= 0.75
        )
    ]

    prompt_compare_focus = {
        "avg_score": compare.get("avg_score"),
        "emotional_understanding": compare.get("emotional_understanding"),
        "decision_making_moral_alignment": compare.get("decision_making_moral_alignment"),
        "in_character_consistency": compare.get("in_character_consistency"),
        "boundary_queries": compare.get("boundary_queries"),
        "know_hallucination_safe_rate": compare.get("know_hallucination_safe_rate"),
    }

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources": REPORT_PATHS,
        "source_of_truth_note": "統一摘要優先採用各獨立報告，不採 domain_eval_suite_report.json 內可能過時的巢狀快照。",
        "refresh_note": "formal_tombench_refresh.json 只有在檔案時間不早於 formal_brain_benchmarks_report.json 時才覆蓋，避免舊 refresh 汙染統一摘要。",
        "latest_metrics": latest_metrics,
        "goal_attainment": goal_attainment,
        "weak_points": weak_points,
        "strengths": [
            "高低軌路由、工作記憶預算、多候選 Bayesian rerank 都已落地，控制器骨幹穩定。",
            "簡單問題直接回答率很高，已經明顯脫離『每題都拆』的舊問題。",
            "長對話記憶與延遲回憶能力已可用，代表工作記憶 + 三循環記憶接法有效。",
            "記憶因果評測已接上，能區分『有取出記憶』與『記憶真的改變回答』。",
            "記憶輸出契約評測已接上，能檢查記憶最後是否被明講、當背景使用，或被正確壓住不說。",
            "10k 壓測下規劃與邊界穩定度很高，表示系統架構比純 prompt 基線可靠。",
            "人工標記 -> regression dataset -> replay eval -> diff report 的技術閉環已接通，可驗證語意契約，但真人自然度仍需獨立盲評。",
            "19 筆真人 S0 盲評與 76 筆候選評分已納入證據鏈，完整右腦在配對比較中勝過三種對照，但嚴格可聊天率仍需提升。",
            "Web 對話 log 已可自動抽出 annotation candidate queue，後續不必手動翻完整 log 才知道先標哪幾題。",
            "annotation draft queue 已可把候選整理成可直接載入標註表單的草稿，縮短人工標記時間。",
            "日常狀態/自我痛苦分流評測已接上，用來檢查疲累、羞恥、空洞、撐不住與危機句是否被分到不同支援策略。",
            "自我痛苦最終回覆契約已接上，用來檢查右腦最後一句是否保留左腦的心理狀態細分，而不是退回泛用疲累模板。",
            "支援回覆固定前綴評測已接上，用來檢查右腦最後一句是否保留人類口語感，而不是每句都套『普通に、』『てか、』等固定開頭。",
            "真實 Qwen + LoRA 候選已接上嚴格語意 gate；目前即使 raw 候選失敗，最終語意與語言契約仍能維持。",
        ],
        "gaps": [
            "正式社會推理 / ToM 仍不足，與你要的『更像人類會揣摩對方』還有差距。",
            "大量題目下表面回覆仍太集中，說話雖正確，但偶爾還像模板。",
            "少數日常狀態句、自我羞愧句、短碎片句仍可能走錯分支。",
            "目前只有 19 筆有效 S0 人類盲評與 10 筆 fail-like 回放，足以找問題但不足以代表所有對話情境。",
            "真人盲評嚴格 yes 率仍低於目標；既有失敗回放全過不等於新情境也會自然。",
            "annotation candidate queue 目前仍是 heuristic 挖掘，功能是縮小人工檢查範圍，不是最終真值標籤。",
            "annotation draft 目前只是建議 verdict / severity / failure types，還不能替代人工判斷。",
            "raw 右腦模型候選接受率仍低，現階段主要價值是被安全攔截與留下訓練診斷，尚未穩定提升真人自然度。",
        ],
        "prompt_baseline_snapshot": prompt_compare_focus,
        "raw_rollup": {
            "architecture": arch,
            "runtime": runtime,
            "memory": memory,
            "diversity": diversity,
            "human_answer": human,
            "daily_state_self_distress": daily_state_self_distress,
            "self_distress_surface_contract": self_distress_surface_contract,
            "support_prefix_contract": support_prefix_contract,
            "formal": formal,
            "memory_causal_effect": memory_causal,
            "memory_speakability_response": memory_speakability_response,
            "stress_10k": stress,
            "human_blind": human_blind,
            "human_feedback_annotation": annotation,
            "annotation_candidate_queue": annotation_queue,
            "annotation_draft_queue": annotation_draft,
            "human_feedback_regression": regression,
            "human_feedback_regression_eval": regression_eval,
            "human_feedback_regression_diff": regression_diff,
            "human_speech_layer": speech_layer,
            "surface_microplanning": surface_microplanning,
            "rightbrain_model_gate": rightbrain_model_gate,
            "domain_suite": compact_domain_suite,
        },
    }
    report["alignment_snapshot"] = _build_alignment_snapshot(
        arch,
        human,
        formal_report,
        stress,
        annotation,
        regression,
        regression_eval,
        regression_diff,
        speech_layer,
        memory_speakability_response,
        human_blind,
    )

    lines = [
        "# 統一評測摘要",
        "",
        f"- 生成時間：`{report['generated_at']}`",
        "- 說明：本摘要優先使用各獨立報告作為最新真值，避免巢狀總表混入舊快照。",
        "",
        "## 現在做得好的地方",
    ]
    for item in report["strengths"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
        "## 目前最主要的三個瓶頸",
        ]
    )
    for item in weak_points:
        lines.append(
            f"- `{item['name_zh']}`：現在值={json.dumps(item['current'], ensure_ascii=False)}；目標={json.dumps(item['target'], ensure_ascii=False)}；"
            f"標準={item['acceptance']}"
        )

    lines.extend(
        [
            "",
            "## 人工標記 / Regression 現況",
            f"- `人工標記數`：{annotation.get('annotation_count', 0)}",
            f"- `Regression Case 數`：{regression.get('regression_case_count', 0)}",
            f"- `Regression 自動通過率`：{regression_eval.get('overall_auto_pass_rate', 0.0)}",
            f"- `Regression 通用空話率`：{regression_eval.get('generic_reply_rate', 0.0)}",
            f"- `Patch Diff 改善指標數 / 退步指標數`：{regression_diff.get('improved_metric_count', 0)} / {regression_diff.get('regressed_metric_count', 0)}",
            "",
            "## 指標中文說明",
            "- `簡單問題直接回答率`：越高越好。例：使用者說「你在幹嘛」，理想是直接回答，不是反問或拆題。",
            "- `日常狀態/自我痛苦細分通過率`：越高越好。例：『我很累』要休息建議，『我好丟臉』要自責承接，『我撐不住』要先停下來，不該全部套同一句疲累模板。",
            "- `自我痛苦最終回覆契約通過率`：越高越好。例：左腦判斷『我好丟臉』是自責羞恥，右腦最後一句也要說到『別責めすぎるな／少し吐け』，不能變成『疲れてるなら休め』。",
            "- `支援回覆固定前綴率`：越低越好。例：支援句不應每次都用『普通に、』『てか、』『はいはい、』開頭，否則會像模板。",
            "- `過度拆題率`：越低越好。例：使用者只說「我今天很累」，不應被誤當成要先重構問題。",
            "- `工作記憶相關率`：越高越好。代表送進左腦的記憶真的跟當輪有關，不是亂塞背景。",
            "- `記憶輸出契約通過率`：越高越好。代表最後一句話知道記憶該明講、只當背景，還是因敏感/第三方資訊而不說。",
            "- `正式心智理論分數`：越高越好。例：故事裡 A 在暗示 B，系統要能看出來不是只讀字面。",
            "- `回覆獨特率`：越高越好。代表同類題目不會一直回同一句。",
            "- `前 20 回覆集中率`：越低越好。這個太高就表示模板化嚴重。",
            "- `人工標記回歸整體通過率`：越高越好。代表真實被你標成 fail 的案例，回放時有沒有真的修掉。",
            "- `人工標記回歸通用空話率`：越低越好。代表修 fail case 時，是否還是在用空泛模板句敷衍。",
            "- `Patch Diff 改善/退步指標數`：前者越高越好，後者越低越好。這是專門看 patch 前後到底有沒有進步。",
            "",
            "## 目標達成度",
        ]
    )
    for item in goal_attainment:
        lines.append(
            f"- `{item['name_zh']}`：score={item['score']} / target={item['target']} / status={item['status']} — {item['rationale']}"
        )

    if prompt_compare_focus:
        lines.extend(
            [
                "",
                "## 與 Prompt-only 基線的歷史對照快照",
                f"- `Avg Score`：{json.dumps(prompt_compare_focus.get('avg_score'), ensure_ascii=False)}",
                f"- `Emotional Understanding`：{json.dumps(prompt_compare_focus.get('emotional_understanding'), ensure_ascii=False)}",
                f"- `Decision-Making/Moral Alignment`：{json.dumps(prompt_compare_focus.get('decision_making_moral_alignment'), ensure_ascii=False)}",
                f"- `In-Character Consistency`：{json.dumps(prompt_compare_focus.get('in_character_consistency'), ensure_ascii=False)}",
                f"- `Boundary Queries`：{json.dumps(prompt_compare_focus.get('boundary_queries'), ensure_ascii=False)}",
                f"- `Know-Hallucination Safe Rate`：{json.dumps(prompt_compare_focus.get('know_hallucination_safe_rate'), ensure_ascii=False)}",
            ]
        )

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(OUT_JSON)
    print(OUT_MD)
    print(json.dumps({"weak_points": weak_points, "goal_attainment": goal_attainment}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
