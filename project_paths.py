import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
WEB_LOG_DIR = os.path.join(BASE_DIR, "web_logs")
HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR = os.path.join(REPORTS_DIR, "human_feedback_regression_eval_snapshots")
HUMAN_FEEDBACK_INVALID_ANNOTATION_ARCHIVE_DIR = os.path.join(ANALYSIS_DIR, "human_feedback_invalid_annotation_archives")
WEB_CONVERSATION_LOG_JSONL_PATH = os.path.join(WEB_LOG_DIR, "uruha_web_conversation_log.jsonl")
WEB_CONVERSATION_LOG_TXT_PATH = os.path.join(WEB_LOG_DIR, "uruha_web_conversation_log.txt")
FORMAL_BENCHMARK_CACHE_DIR = os.path.join(CACHE_DIR, "formal_benchmark_cache")
FAILURE_TAXONOMY_MD_PATH = os.path.join(ANALYSIS_DIR, "failure_taxonomy.md")
FAILURE_TAXONOMY_SCHEMA_PATH = os.path.join(ANALYSIS_DIR, "failure_taxonomy_schema.json")
HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH = os.path.join(ANALYSIS_DIR, "human_feedback_annotations.jsonl")
HUMAN_BLIND_DATA_DIR = os.path.join(DATASETS_DIR, "human_blind")
SURFACE_MICROPLANNING_HOLDOUT_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "surface_microplanning_holdout.json",
)

COGNITIVE_ARCHITECTURE_DATASET_PATH = os.path.join(DATASETS_DIR, "cognitive_architecture_eval_dataset.json")
HUMAN_FEEDBACK_REGRESSION_DATASET_PATH = os.path.join(DATASETS_DIR, "human_feedback_regression_dataset.json")
STRESS_EVAL_DATASET_PATH = os.path.join(DATASETS_DIR, "stress_eval_dataset_10000.json")
V2_HUMAN_ANSWER_DATASET_PATH = os.path.join(DATASETS_DIR, "v2_human_answer_dataset.json")

COGNITIVE_ARCHITECTURE_REPORT_PATH = os.path.join(REPORTS_DIR, "cognitive_architecture_eval_report.json")
DOMAIN_EVAL_SUITE_REPORT_PATH = os.path.join(REPORTS_DIR, "domain_eval_suite_report.json")
FORMAL_BRAIN_BENCHMARKS_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "formal_brain_benchmarks_report.json")
FORMAL_BRAIN_BENCHMARKS_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "formal_brain_benchmarks_report.md")
FORMAL_DAILYDIALOG_INTERPRETER_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "formal_dailydialog_interpreter_report.json")
FORMAL_DAILYDIALOG_INTERPRETER_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "formal_dailydialog_interpreter_report.md")
FORMAL_DAILYDIALOG_HOLDOUT_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "formal_dailydialog_holdout_report.json")
FORMAL_DAILYDIALOG_HOLDOUT_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "formal_dailydialog_holdout_report.md")
FORMAL_TOMBENCH_REFRESH_PATH = os.path.join(REPORTS_DIR, "formal_tombench_refresh.json")
HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_feedback_regression_report.json")
HUMAN_FEEDBACK_REGRESSION_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_feedback_regression_report.md")
HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_feedback_regression_eval_report.json")
HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_feedback_regression_eval_report.md")
HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_feedback_regression_diff_report.json")
HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_feedback_regression_diff_report.md")
HUMAN_SPEECH_LAYER_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_speech_layer_eval_report.json")
HUMAN_SPEECH_LAYER_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_speech_layer_eval_report_zh.md")
DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "daily_state_self_distress_report.json")
DAILY_STATE_SELF_DISTRESS_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "daily_state_self_distress_report.md")
SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "self_distress_surface_contract_report.json")
SELF_DISTRESS_SURFACE_CONTRACT_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "self_distress_surface_contract_report.md")
SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "support_prefix_contract_report.json")
SUPPORT_PREFIX_CONTRACT_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "support_prefix_contract_report.md")
LONG_DIALOGUE_MEMORY_REPORT_PATH = os.path.join(REPORTS_DIR, "long_dialogue_memory_report.json")
MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "memory_causal_effect_report.json")
MEMORY_CAUSAL_EFFECT_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "memory_causal_effect_report.md")
MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "memory_speakability_response_report.json")
MEMORY_SPEAKABILITY_RESPONSE_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "memory_speakability_response_report.md")
MEMORY_CONTRADICTION_CORRECTION_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "memory_contradiction_correction_report.json")
MEMORY_CONTRADICTION_CORRECTION_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "memory_contradiction_correction_report.md")
MEMORY_UPDATE_OVERWRITE_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "memory_update_overwrite_report.json")
MEMORY_UPDATE_OVERWRITE_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "memory_update_overwrite_report.md")
REPLY_DIVERSITY_REPORT_PATH = os.path.join(REPORTS_DIR, "reply_diversity_report.json")
RUNTIME_DYNAMICS_REPORT_PATH = os.path.join(REPORTS_DIR, "runtime_dynamics_report.json")
STRESS_EVAL_REPORT_PATH = os.path.join(REPORTS_DIR, "stress_eval_report_10000.json")
SYSTEM_VS_PROMPT_ONLY_COMPARE_PATH = os.path.join(REPORTS_DIR, "system_vs_prompt_only_compare.json")
UNIFIED_EVAL_SUMMARY_JSON_PATH = os.path.join(REPORTS_DIR, "unified_eval_summary.json")
UNIFIED_EVAL_SUMMARY_MD_PATH = os.path.join(REPORTS_DIR, "unified_eval_summary_zh.md")
V2_HUMAN_ANSWER_REPORT_PATH = os.path.join(REPORTS_DIR, "v2_human_answer_report.json")
HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_feedback_annotation_report.json")
HUMAN_FEEDBACK_ANNOTATION_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_feedback_annotation_report.md")
HUMAN_FEEDBACK_ANNOTATION_CLEANUP_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_feedback_annotation_cleanup_report.json")
HUMAN_FEEDBACK_ANNOTATION_CLEANUP_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_feedback_annotation_cleanup_report.md")
HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "human_blind_evidence_report.json")
HUMAN_BLIND_EVIDENCE_REPORT_MD_PATH = os.path.join(REPORTS_DIR, "human_blind_evidence_report.md")
SURFACE_MICROPLANNING_BASELINE_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "surface_microplanning_baseline_report.json",
)
SURFACE_MICROPLANNING_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "surface_microplanning_report.json",
)
SURFACE_MICROPLANNING_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "surface_microplanning_report.md",
)
ANNOTATION_CANDIDATE_QUEUE_JSON_PATH = os.path.join(REPORTS_DIR, "annotation_candidate_queue.json")
ANNOTATION_CANDIDATE_QUEUE_MD_PATH = os.path.join(REPORTS_DIR, "annotation_candidate_queue.md")
ANNOTATION_DRAFT_QUEUE_JSON_PATH = os.path.join(REPORTS_DIR, "annotation_draft_queue.json")
ANNOTATION_DRAFT_QUEUE_MD_PATH = os.path.join(REPORTS_DIR, "annotation_draft_queue.md")


def ensure_project_dirs():
    for path in (
        ANALYSIS_DIR,
        DATASETS_DIR,
        REPORTS_DIR,
        HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR,
        HUMAN_FEEDBACK_INVALID_ANNOTATION_ARCHIVE_DIR,
        CACHE_DIR,
        FORMAL_BENCHMARK_CACHE_DIR,
        WEB_LOG_DIR,
    ):
        os.makedirs(path, exist_ok=True)


ensure_project_dirs()
