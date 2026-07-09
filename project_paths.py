import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
MODELS_DIR = os.path.join(BASE_DIR, "models")
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
RIGHTBRAIN_MODEL_GATE_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_model_gate_development.json",
)
RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_plan_surface_contract_v1_train.json",
)
RIGHTBRAIN_REJECTION_CURRICULUM_V1_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_rejection_curriculum_v1.json",
)
RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_runtime_rejection_curriculum_v13.json",
)
RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_holdout_separated_curriculum_v14.json",
)
RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_candidate_gate_curriculum_v15.json",
)
RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_repair_curriculum_v1.json",
)
RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH = os.path.join(
    DATASETS_DIR,
    "rightbrain_repair_selection_v1.json",
)
RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "rightbrain_repair_selector_v1.json",
)
RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_v10_repair_off_holdout.json",
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
RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_model_gate_report.json",
)
RIGHTBRAIN_MODEL_GATE_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_model_gate_report.md",
)
RIGHTBRAIN_CONTRACT_ALIGNMENT_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_alignment_report.json",
)
RIGHTBRAIN_CONTRACT_ALIGNMENT_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_alignment_report.md",
)
RIGHTBRAIN_AUDITED_MEMORY_BRIEF_EVAL_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_audited_memory_brief_eval_report.json",
)
RIGHTBRAIN_AUDITED_MEMORY_BRIEF_EVAL_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_audited_memory_brief_eval_report.md",
)
RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_audited_memory_surface_eval_report.json",
)
RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_audited_memory_surface_eval_report.md",
)
RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_model_surface_holdout_report.json",
)
RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_model_surface_holdout_report.md",
)
RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_runtime_adapter_multiseed_report.json",
)
RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_runtime_adapter_multiseed_report.md",
)
RIGHTBRAIN_REJECTION_CURRICULUM_V1_SOURCE_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_v9_rejection_source_holdout.json",
)
RIGHTBRAIN_CONTRACT_V1_DATASET_SUMMARY_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_plan_surface_contract_v1_dataset_summary.json",
)
RIGHTBRAIN_CONTRACT_V1_DATASET_SUMMARY_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_plan_surface_contract_v1_dataset_summary.md",
)
RIGHTBRAIN_CONTRACT_V1_TRAINING_RUN_REPORT_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_v1_training_run.json",
)
RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_rejection_curriculum_v1_report.json",
)
RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_rejection_curriculum_v1_report.md",
)
RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_runtime_rejection_curriculum_v13_report.json",
)
RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_runtime_rejection_curriculum_v13_report.md",
)
RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_holdout_separated_curriculum_v14_report.json",
)
RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_holdout_separated_curriculum_v14_report.md",
)
RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_candidate_gate_curriculum_v15_report.json",
)
RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_candidate_gate_curriculum_v15_report.md",
)
RIGHTBRAIN_REPAIR_CURRICULUM_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_curriculum_v1_report.json",
)
RIGHTBRAIN_REPAIR_CURRICULUM_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_curriculum_v1_report.md",
)
RIGHTBRAIN_REPAIR_SELECTION_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selection_v1_report.json",
)
RIGHTBRAIN_REPAIR_SELECTION_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selection_v1_report.md",
)
RIGHTBRAIN_REPAIR_SELECTION_EVAL_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selection_eval_v1_report.json",
)
RIGHTBRAIN_REPAIR_SELECTION_EVAL_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selection_eval_v1_report.md",
)
RIGHTBRAIN_REPAIR_SELECTOR_V1_TRAIN_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selector_v1_train_report.json",
)
RIGHTBRAIN_REPAIR_SELECTOR_V1_TRAIN_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selector_v1_train_report.md",
)
RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selector_v1_eval_report.json",
)
RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_repair_selector_v1_eval_report.md",
)
RIGHTBRAIN_SELECTOR_SHADOW_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_shadow_v1_report.json",
)
RIGHTBRAIN_SELECTOR_SHADOW_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_shadow_v1_report.md",
)
RIGHTBRAIN_SELECTOR_LIVE_EVIDENCE_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_live_evidence_report.json",
)
RIGHTBRAIN_SELECTOR_LIVE_EVIDENCE_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_live_evidence_report.md",
)
RIGHTBRAIN_SELECTOR_LIVE_DISAGREEMENT_QUEUE_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_live_disagreement_queue.json",
)
RIGHTBRAIN_SELECTOR_RUNTIME_SOAK_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_runtime_soak_v1_report.json",
)
RIGHTBRAIN_SELECTOR_RUNTIME_SOAK_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_runtime_soak_v1_report.md",
)
RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_actual_model_soak_v1_report.json",
)
RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_selector_actual_model_soak_v1_report.md",
)
RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_sampling_schedule_ablation_v1_report.json",
)
RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_sampling_schedule_ablation_v1_report.md",
)
RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_sampling_schedule_naturalness_audit_v1.json",
)
RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_sampling_schedule_naturalness_audit_v1.md",
)
RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_casual_register_gate_v2_report.json",
)
RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_casual_register_gate_v2_report.md",
)
RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_projection_v1_report.json",
)
RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_projection_v1_report.md",
)
RIGHTBRAIN_CONTRACT_PROJECTION_V1_AUDIT_JSON_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_projection_v1_naturalness_audit.json",
)
RIGHTBRAIN_CONTRACT_PROJECTION_V1_AUDIT_MD_PATH = os.path.join(
    REPORTS_DIR,
    "rightbrain_contract_projection_v1_naturalness_audit.md",
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
        MODELS_DIR,
        HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR,
        HUMAN_FEEDBACK_INVALID_ANNOTATION_ARCHIVE_DIR,
        CACHE_DIR,
        FORMAL_BENCHMARK_CACHE_DIR,
        WEB_LOG_DIR,
    ):
        os.makedirs(path, exist_ok=True)


ensure_project_dirs()
