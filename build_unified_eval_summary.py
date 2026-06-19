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
    HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH,
    HUMAN_SPEECH_LAYER_REPORT_JSON_PATH,
    LONG_DIALOGUE_MEMORY_REPORT_PATH,
    MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH,
    MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
    REPLY_DIVERSITY_REPORT_PATH,
    RUNTIME_DYNAMICS_REPORT_PATH,
    STRESS_EVAL_REPORT_PATH,
    SYSTEM_VS_PROMPT_ONLY_COMPARE_PATH,
    UNIFIED_EVAL_SUMMARY_JSON_PATH,
    UNIFIED_EVAL_SUMMARY_MD_PATH,
    V2_HUMAN_ANSWER_REPORT_PATH,
)

REPORT_PATHS = {
    "architecture": COGNITIVE_ARCHITECTURE_REPORT_PATH,
    "daily_state_self_distress": DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH,
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
    "human_feedback_annotation": HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH,
    "annotation_candidate_queue": ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
    "annotation_draft_queue": ANNOTATION_DRAFT_QUEUE_JSON_PATH,
    "human_feedback_regression": HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH,
    "human_feedback_regression_eval": HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    "human_feedback_regression_diff": HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH,
    "human_speech_layer": HUMAN_SPEECH_LAYER_REPORT_JSON_PATH,
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
            "detail": "人工標記與 taxonomy 已接上；若 annotation_count 仍是 0，代表流程就緒但尚未累積真實資料。",
        },
        "human_feedback_regression_loop": {
            "status": "implemented" if (regression_eval or {}).get("total_cases", 0) > 0 else "partial",
            "metric": {
                "regression_case_count": _safe_float((regression or {}).get("regression_case_count"), digits=0),
                "overall_auto_pass_rate": _safe_float((regression_eval or {}).get("overall_auto_pass_rate")),
                "generic_reply_rate": _safe_float((regression_eval or {}).get("generic_reply_rate")),
            },
            "detail": "從人工標記抽 regression case、重播回腦、再做自動檢查的閉環已成形；若 case 數仍是 0，表示還缺真實標記餵入。",
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
    formal_report = _load_json(REPORT_PATHS["formal"])
    formal_tombench_refresh = _load_json(REPORT_PATHS["formal_tombench_refresh"])
    domain_suite = _load_json(REPORT_PATHS["domain_suite"])
    stress_report = _load_json(REPORT_PATHS["stress_10k"])
    compare_report = _load_json(REPORT_PATHS["system_vs_prompt"])
    annotation_report = _load_json(REPORT_PATHS["human_feedback_annotation"])
    annotation_candidate_report = _load_json(REPORT_PATHS["annotation_candidate_queue"])
    annotation_draft_report = _load_json(REPORT_PATHS["annotation_draft_queue"])
    regression_report = _load_json(REPORT_PATHS["human_feedback_regression"])
    regression_eval_report = _load_json(REPORT_PATHS["human_feedback_regression_eval"])
    regression_diff_report = _load_json(REPORT_PATHS["human_feedback_regression_diff"])
    speech_layer_report = _load_json(REPORT_PATHS["human_speech_layer"])

    arch = arch_report.get("summary", {})
    runtime = runtime_report.get("summary", {})
    memory = memory_report.get("summary", {})
    memory_causal = memory_causal_report.get("summary", {})
    memory_speakability_response = memory_speakability_response_report.get("summary", {})
    diversity = diversity_report.get("summary", {})
    human = human_report.get("summary", {})
    daily_state_self_distress = daily_state_self_distress_report.get("summary", {})
    formal = formal_report.get("summaries", {})
    if (formal_tombench_refresh or {}).get("summary") and _is_newer_or_same(
        REPORT_PATHS["formal_tombench_refresh"],
        REPORT_PATHS["formal"],
    ):
        formal = dict(formal)
        formal["tombench"] = formal_tombench_refresh["summary"]
    stress = stress_report.get("summary", {})
    compare = compare_report.get("overall_compare", {})
    annotation = annotation_report.get("summary", {})
    annotation_queue = annotation_candidate_report.get("summary", {})
    annotation_draft = annotation_draft_report.get("summary", {})
    regression = regression_report.get("summary", {})
    regression_eval = regression_eval_report.get("summary", {})
    regression_diff = regression_diff_report.get("summary", {})
    speech_layer = speech_layer_report.get("metrics", {})
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
            "記憶因果影響率",
            "memory_causal_strong_effect_rate",
            memory_causal.get("strong_causal_effect_rate"),
            "越高越好",
            "memory_causal_effect_report.json",
            "higher",
            "代表同一題在有記憶與無記憶條件下，回答是否會因相關記憶而改變且明確帶入記憶錨點。",
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
                memory_causal.get("strong_causal_effect_rate"),
                memory_speakability_response.get("case_pass_rate"),
            ),
            0.9,
            "這項高表示不是把所有記憶亂塞進左腦，而是能抓住真正相關的少量資訊，讓記憶實際改變回答，且最後一句知道何時該說、何時不該說。",
            [
                "cognitive_architecture_eval_report.json.summary.working_memory_relevance_rate",
                "long_dialogue_memory_report.json.summary.delayed_recall_rate",
                "memory_causal_effect_report.json.summary.strong_causal_effect_rate",
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
            "像人類地修補真實失敗案例",
            regression_eval.get("overall_auto_pass_rate") if (regression_eval.get("total_cases") or 0) > 0 else None,
            0.75,
            "這項高表示不是只在人工設計 benchmark 上過關，而是連真實人工標過的 fail case 回放時也能修正到位。",
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
    ]

    weak_points = [
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
            "人工標記 -> regression dataset -> replay eval -> diff report 的修補閉環已經接通，後面可以開始做真實 fail case 的 patch 驗證。",
            "Web 對話 log 已可自動抽出 annotation candidate queue，後續不必手動翻完整 log 才知道先標哪幾題。",
            "annotation draft queue 已可把候選整理成可直接載入標註表單的草稿，縮短人工標記時間。",
            "日常狀態/自我痛苦分流評測已接上，用來檢查疲累、羞恥、空洞、撐不住與危機句是否被分到不同支援策略。",
        ],
        "gaps": [
            "正式社會推理 / ToM 仍不足，與你要的『更像人類會揣摩對方』還有差距。",
            "大量題目下表面回覆仍太集中，說話雖正確，但偶爾還像模板。",
            "少數日常狀態句、自我羞愧句、短碎片句仍可能走錯分支。",
            "人工標記與 regression cases 目前仍接近 0，表示閉環已建好，但資料還沒有餵進來。",
            "annotation candidate queue 目前仍是 heuristic 挖掘，功能是縮小人工檢查範圍，不是最終真值標籤。",
            "annotation draft 目前只是建議 verdict / severity / failure types，還不能替代人工判斷。",
        ],
        "prompt_baseline_snapshot": prompt_compare_focus,
        "raw_rollup": {
            "architecture": arch,
            "runtime": runtime,
            "memory": memory,
            "diversity": diversity,
            "human_answer": human,
            "daily_state_self_distress": daily_state_self_distress,
            "formal": formal,
            "memory_causal_effect": memory_causal,
            "memory_speakability_response": memory_speakability_response,
            "stress_10k": stress,
            "human_feedback_annotation": annotation,
            "annotation_candidate_queue": annotation_queue,
            "annotation_draft_queue": annotation_draft,
            "human_feedback_regression": regression,
            "human_feedback_regression_eval": regression_eval,
            "human_feedback_regression_diff": regression_diff,
            "human_speech_layer": speech_layer,
            "domain_suite": domain_suite.get("summary", {}),
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
