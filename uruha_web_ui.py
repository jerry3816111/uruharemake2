import json
import inspect
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from html import escape
from pathlib import Path
from uuid import uuid4

from project_paths import (
    ANNOTATION_DRAFT_QUEUE_JSON_PATH,
    ANNOTATION_DRAFT_QUEUE_MD_PATH,
    ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
    ANNOTATION_CANDIDATE_QUEUE_MD_PATH,
    FAILURE_TAXONOMY_MD_PATH,
    FAILURE_TAXONOMY_SCHEMA_PATH,
    HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_ANNOTATION_REPORT_MD_PATH,
    HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
    HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_MD_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_MD_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR,
    BASE_DIR,
    COGNITIVE_ARCHITECTURE_REPORT_PATH,
    UNIFIED_EVAL_SUMMARY_JSON_PATH,
    UNIFIED_EVAL_SUMMARY_MD_PATH,
    V2_HUMAN_ANSWER_REPORT_PATH,
    WEB_LOG_DIR,
    WEB_CONVERSATION_LOG_JSONL_PATH,
    WEB_CONVERSATION_LOG_TXT_PATH,
)

EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_project_python():
    if __name__ != "__main__":
        return
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        print(f"⚠️ 偵測到目前 Python 不是專案 venv：{sys.executable}")
        print(f"↪️ 自動切換到：{EXPECTED_PYTHON}")
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__, *sys.argv[1:]], clean_env)


_ensure_project_python()

import gradio as gr
from colorama import Fore, init

from human_feedback_validation import (
    invalid_annotation_reason,
    invalid_turn_source_reason,
    is_valid_annotation_record,
    normalize_failure_types,
)
from uruha_brain_mac import UruhaBrainV4_Mac
from uruha_memory_observatory import MEMORY_OBSERVATORY_CSS
from uruha_m38_memory_observatory import (
    render_memory_observatory_m38 as render_memory_observatory,
)
from uruha_equation_lab import (
    DEFAULT_CASE_ID as DEFAULT_EQUATION_CASE_ID,
    EQUATION_LAB_CSS,
    case_choices as equation_case_choices,
    phase_choices as equation_phase_choices,
    render_equation_lab,
    show_feedback_correction,
)
from uruha_long_dialogue_memory_lab import (
    DEFAULT_CHECKPOINT as DEFAULT_LONG_MEMORY_CHECKPOINT,
    LONG_DIALOGUE_LAB_CSS,
    checkpoint_choices as long_memory_checkpoint_choices,
    render_long_dialogue_lab,
)
from uruha_fifty_turn_comparison_lab import (
    DEFAULT_CHECKPOINT as DEFAULT_FIFTY_COMPARISON_CHECKPOINT,
    FIFTY_COMPARISON_CSS,
    checkpoint_choices as fifty_comparison_checkpoint_choices,
    render_fifty_turn_comparison,
)
from uruha_memory_repair_lab import (
    DEFAULT_CHECKPOINT as DEFAULT_MEMORY_REPAIR_CHECKPOINT,
    MEMORY_REPAIR_LAB_CSS,
    checkpoint_choices as memory_repair_checkpoint_choices,
    render_memory_repair_lab,
)
from uruha_temporal_prediction_lab import (
    DEFAULT_SAMPLE_ID as DEFAULT_TEMPORAL_SAMPLE_ID,
    TEMPORAL_PREDICTION_LAB_CSS,
    render_temporal_prediction_lab,
    sample_choices as temporal_sample_choices,
)
from uruha_structured_memory_lab import (
    DEFAULT_QUERY_ID as DEFAULT_STRUCTURED_MEMORY_QUERY_ID,
    STRUCTURED_MEMORY_LAB_CSS,
    query_choices as structured_memory_query_choices,
    render_structured_memory_lab,
)
from uruha_human_state_lab import (
    DEFAULT_STATE_ID as DEFAULT_HUMAN_STATE_ID,
    HUMAN_STATE_LAB_CSS,
    render_human_state_lab,
    state_choices as human_state_choices,
)
from uruha_transition_lab import (
    DEFAULT_TRANSITION_ID,
    TRANSITION_LAB_CSS,
    render_transition_lab,
    transition_choices,
)
from uruha_behavior_predictor_lab import (
    BEHAVIOR_PREDICTOR_LAB_CSS,
    DEFAULT_BEHAVIOR_SAMPLE_ID,
    behavior_sample_choices,
    render_behavior_predictor_lab,
)
from uruha_ablation_lab import (
    ABLATION_LAB_CSS,
    DEFAULT_ABLATION_COMPONENT,
    ablation_component_choices,
    render_ablation_lab,
)
from uruha_robustness_lab import (
    DEFAULT_ROLLING_CUTOFF,
    ROBUSTNESS_LAB_CSS,
    render_robustness_lab,
    rolling_cutoff_choices,
)
from uruha_transfer_lab import (
    DEFAULT_TRANSFER_CUTOFF,
    TRANSFER_LAB_CSS,
    render_transfer_lab,
    transfer_cutoff_choices,
)
from uruha_language_lab import (
    DEFAULT_LANGUAGE_SAMPLE_ID,
    LANGUAGE_LAB_CSS,
    language_case_choices,
    render_language_lab,
)
from uruha_register_lab import (
    DEFAULT_REGISTER_CASE_ID,
    REGISTER_LAB_CSS,
    register_case_choices,
    render_register_lab,
)
from uruha_register_rating_lab import (
    DEFAULT_BLIND_ITEM_ID,
    RATING_LAB_CSS,
    blind_item_choices,
    render_blind_rating_item,
    render_rater_progress,
    save_blind_rating,
)
from uruha_research_closure_lab import (
    DEFAULT_CLOSURE_STAGE,
    RESEARCH_CLOSURE_CSS,
    closure_stage_choices,
    render_research_closure,
)
from uruha_senses import UruhaEars, UruhaMouth
from uruha_teacher_demo import (
    DEFAULT_SCENARIO_ID,
    TEACHER_DEMO_CSS,
    advance_teacher_demo,
    render_teacher_demo,
    scenario_choices,
    step_choices,
)

init(autoreset=True)

WEB_WHISPER_MODEL = os.getenv("URUHA_WEB_WHISPER_MODEL", "large-v3")
WEB_WHISPER_DEVICE = os.getenv("URUHA_WEB_WHISPER_DEVICE", "cpu")
WEB_TTS_BASE_URL = os.getenv("URUHA_TTS_BASE_URL", "http://127.0.0.1:5001")
WEB_SERVER_NAME = os.getenv("URUHA_WEB_HOST", "127.0.0.1")
WEB_SERVER_PORT = int(os.getenv("URUHA_WEB_PORT", "7860"))
WEB_PREWARM_BRAIN = str(os.getenv("URUHA_WEB_PREWARM_BRAIN", "1")).strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
WEB_CSS = """
.wrap {max-width: 1560px; margin: 0 auto;}
.trace-board {display: flex; gap: 12px; overflow-x: auto; padding: 8px 2px 12px;}
.trace-card {min-width: 230px; max-width: 280px; border: 1px solid #2f3541; border-radius: 12px; padding: 12px; background: #111827; color: #f9fafb; box-shadow: 0 8px 24px rgba(0,0,0,0.16);}
.trace-arrow {align-self: center; color: #6b7280; font-size: 18px; padding: 0 2px;}
.trace-stage {font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #93c5fd; margin-bottom: 6px;}
.trace-label {font-size: 15px; font-weight: 700; margin-bottom: 8px; color: #ffffff;}
.trace-meta {font-size: 11px; color: #9ca3af; margin-bottom: 8px;}
.trace-pre {white-space: pre-wrap; font-size: 12px; line-height: 1.45; color: #e5e7eb; margin: 0;}
.trace-empty {border: 1px dashed #374151; border-radius: 12px; padding: 16px; color: #9ca3af; background: rgba(17,24,39,0.55);}
.state-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px;}
.state-card {border: 1px solid #d1d5db; border-radius: 12px; padding: 14px; background: #ffffff;}
.state-card h4 {margin: 0 0 8px 0; font-size: 14px;}
.state-list {margin: 0; padding-left: 18px; font-size: 12px; line-height: 1.5;}
.trace-chip {display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; background: #e5e7eb; color: #111827; margin: 0 6px 6px 0;}
.muted {color: #6b7280;}
""" + RESEARCH_CLOSURE_CSS + RATING_LAB_CSS + REGISTER_LAB_CSS + LANGUAGE_LAB_CSS + TRANSFER_LAB_CSS + ROBUSTNESS_LAB_CSS + ABLATION_LAB_CSS + BEHAVIOR_PREDICTOR_LAB_CSS + TRANSITION_LAB_CSS + HUMAN_STATE_LAB_CSS + STRUCTURED_MEMORY_LAB_CSS + TEMPORAL_PREDICTION_LAB_CSS + MEMORY_OBSERVATORY_CSS + TEACHER_DEMO_CSS + EQUATION_LAB_CSS + LONG_DIALOGUE_LAB_CSS + FIFTY_COMPARISON_CSS + MEMORY_REPAIR_LAB_CSS
ARCH_DATASET_SCRIPT = os.path.join(BASE_DIR, "build_cognitive_architecture_eval_dataset.py")
ARCH_EVAL_SCRIPT = os.path.join(BASE_DIR, "cognitive_architecture_eval.py")
ANNOTATION_QUEUE_SCRIPT = os.path.join(BASE_DIR, "build_annotation_candidate_queue.py")
ANNOTATION_DRAFT_SCRIPT = os.path.join(BASE_DIR, "build_annotation_draft_queue.py")
ANNOTATION_REPORT_SCRIPT = os.path.join(BASE_DIR, "build_human_feedback_annotation_report.py")
REGRESSION_DATASET_SCRIPT = os.path.join(BASE_DIR, "build_human_feedback_regression_dataset.py")
REGRESSION_EVAL_SCRIPT = os.path.join(BASE_DIR, "eval_human_feedback_regression.py")
REGRESSION_DIFF_SCRIPT = os.path.join(BASE_DIR, "build_human_feedback_regression_diff_report.py")
ARCH_REPORT_PATH = COGNITIVE_ARCHITECTURE_REPORT_PATH
V2_REPORT_PATH = V2_HUMAN_ANSWER_REPORT_PATH
UNIFIED_SUMMARY_SCRIPT = os.path.join(BASE_DIR, "build_unified_eval_summary.py")
WEB_LOG_JSONL = os.path.abspath(
    os.getenv("URUHA_WEB_LOG_JSONL_PATH", WEB_CONVERSATION_LOG_JSONL_PATH)
)
WEB_LOG_TXT = os.path.abspath(
    os.getenv("URUHA_WEB_LOG_TXT_PATH", WEB_CONVERSATION_LOG_TXT_PATH)
)
WEB_HEAD = """
<script>
(() => {
  const ORT_SRC = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.14.0/dist/ort.js";
  const VAD_SRC = "https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.7/dist/bundle.min.js";

  const loadScript = (src) => new Promise((resolve, reject) => {
    if ([...document.scripts].some((s) => s.src === src)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });

  const getVoiceModeEnabled = () => {
    const input = document.querySelector("#voice-chat-mode input[type='checkbox']");
    return input ? input.checked : true;
  };

  const assistantIsPlaying = () => {
    const player = document.querySelector("#uruha-tts audio");
    return !!(player && !player.paused && !player.ended);
  };

  const findRecordButton = () => document.querySelector("#uruha-mic .record-button");
  const findStopButton = () => document.querySelector("#uruha-mic .stop-button");
  const findAudioPlayer = () => document.querySelector("#uruha-tts audio");

  window.__uruhaAwaitingSpeech = true;

  const setRecordLabel = () => {
    const record = findRecordButton();
    if (record && window.__uruhaVadAttached && record.textContent !== "Just Start Talking") {
      record.textContent = "Just Start Talking";
    }
  };

  const armVoiceWait = () => {
    if (!getVoiceModeEnabled()) return;
    window.__uruhaAwaitingSpeech = true;
    setRecordLabel();
  };

  const attachPlayerWatcher = () => {
    const player = findAudioPlayer();
    if (!player || player === window.__uruhaBoundPlayer) return;
    if (window.__uruhaBoundPlayer && window.__uruhaOnEnded) {
      window.__uruhaBoundPlayer.removeEventListener("ended", window.__uruhaOnEnded);
      window.__uruhaBoundPlayer.removeEventListener("play", window.__uruhaOnPlay);
    }
    window.__uruhaOnPlay = () => {
      window.__uruhaAwaitingSpeech = false;
    };
    window.__uruhaOnEnded = () => {
      window.setTimeout(() => {
        armVoiceWait();
      }, 150);
    };
    player.addEventListener("play", window.__uruhaOnPlay);
    player.addEventListener("ended", window.__uruhaOnEnded);
    window.__uruhaBoundPlayer = player;
  };

  const attachVad = async () => {
    if (window.__uruhaVadAttached) return;
    await loadScript(ORT_SRC);
    await loadScript(VAD_SRC);
    const poll = window.setInterval(async () => {
      const record = findRecordButton();
      if (!record || !window.vad?.MicVAD) return;
      window.clearInterval(poll);
      setRecordLabel();
      try {
        const micVad = await window.vad.MicVAD.new({
          onSpeechStart: () => {
            if (!getVoiceModeEnabled() || assistantIsPlaying() || !window.__uruhaAwaitingSpeech) return;
            const recordButton = findRecordButton();
            const stopButton = findStopButton();
            if (recordButton && !stopButton) {
              window.__uruhaAwaitingSpeech = false;
              recordButton.click();
            }
          },
          onSpeechEnd: () => {
            if (!getVoiceModeEnabled()) return;
            const stopButton = findStopButton();
            if (stopButton) {
              stopButton.click();
            }
          },
        });
        micVad.start();
        window.__uruhaVadAttached = true;
        window.__uruhaVad = micVad;
        setRecordLabel();
      } catch (error) {
        console.error("Uruha VAD init failed:", error);
      }
    }, 500);
  };

  const attachVoiceModeToggle = () => {
    const input = document.querySelector("#voice-chat-mode input[type='checkbox']");
    if (!input || input === window.__uruhaVoiceModeInput) return;
    const enableHandsFree = () => {
      if (input.checked) attachVad();
    };
    input.addEventListener("change", enableHandsFree);
    window.__uruhaVoiceModeInput = input;
  };

  const watchDom = () => {
    attachPlayerWatcher();
    attachVoiceModeToggle();
    setRecordLabel();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      watchDom();
      new MutationObserver(watchDom).observe(document.body, { childList: true, subtree: true });
    }, { once: true });
  } else {
    watchDom();
    new MutationObserver(watchDom).observe(document.body, { childList: true, subtree: true });
  }
})();
</script>
"""
os.makedirs(WEB_LOG_DIR, exist_ok=True)
for _web_log_path in {WEB_LOG_JSONL, WEB_LOG_TXT}:
    os.makedirs(os.path.dirname(_web_log_path), exist_ok=True)


def _default_taxonomy_catalog():
    return {
        "version": "fallback-v1",
        "verdict_options": [
            {"value": "pass", "label_zh": "通過 / 像人"},
            {"value": "mixed", "label_zh": "部分失敗 / 需要看洞"},
            {"value": "fail", "label_zh": "失敗 / 明顯不對"},
        ],
        "severity_options": [
            {"value": "low", "label_zh": "低"},
            {"value": "medium", "label_zh": "中"},
            {"value": "high", "label_zh": "高"},
        ],
        "failure_types": [
            {"code": "MISREAD_INTENT", "label_zh": "意圖讀錯"},
            {"code": "LOW_DENSITY", "label_zh": "資訊空洞 / 句終結者"},
            {"code": "MISSED_VIBE", "label_zh": "情緒位向錯誤"},
            {"code": "MISSED_JOKE_OR_CULTURE", "label_zh": "梗 / 文化脈絡漏接"},
            {"code": "GENERIC_REPLY", "label_zh": "泛用模板回覆"},
            {"code": "REPEATED_REPLY", "label_zh": "重複句型 / 模式塌陷"},
            {"code": "TOO_ROBOTIC_LOGIC", "label_zh": "過度理性 / 機器人感"},
            {"code": "WRONG_BOUNDARY", "label_zh": "邊界反應錯誤"},
            {"code": "GHOST_MEMORY", "label_zh": "幽靈記憶 / 因果斷裂"},
            {"code": "WRONG_MEMORY_USE", "label_zh": "記憶使用錯誤"},
            {"code": "RIGHTBRAIN_SURFACE_ERROR", "label_zh": "右腦表面化錯誤"},
        ],
    }


class RuntimeManager:
    def __init__(self):
        self._brain = None
        self._brain_init_lock = threading.Lock()
        self._brain_prewarm_thread = None
        self._brain_load_trace = {
            "schema": "uruha_brain_initialization_m17",
            "status": "not_started",
            "elapsed_seconds": 0.0,
            "prewarm_enabled": bool(WEB_PREWARM_BRAIN),
        }
        self._ears = None
        self._mouth = None
        self._lock = threading.Lock()
        self._human_gate_lock = threading.Lock()
        self._human_waiters = 0
        self._scheduler_trace = {
            "schema": "uruha_human_priority_scheduler_m19",
            "human_waiters": 0,
            "background_status": "not_started",
            "last_decision": "startup",
            "background_model_maintenance_allowed": False,
            "contains_raw_dialogue": False,
        }
        self._session_id = self._new_session_id()
        self._turn_index = 0
        self._last_activity_at = time.time()
        self._last_idle_consolidation_at = 0.0
        self._idle_seconds = 300
        self._idle_thread = threading.Thread(target=self._idle_consolidation_loop, daemon=True)
        self._idle_thread.start()

    def _new_session_id(self):
        return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

    def next_turn_meta(self):
        self._turn_index += 1
        return self._session_id, self._turn_index

    def get_brain(self):
        if self._brain is not None:
            return self._brain
        with self._brain_init_lock:
            if self._brain is not None:
                return self._brain
            started = time.perf_counter()
            self._brain_load_trace.update(
                {"status": "loading", "started_at": datetime.now().isoformat(timespec="seconds")}
            )
            print(Fore.CYAN + "🧠 [Web] Loading V2 brain...")
            try:
                self._brain = UruhaBrainV4_Mac()
            except Exception as exc:
                self._brain_load_trace.update(
                    {
                        "status": "error",
                        "elapsed_seconds": round(time.perf_counter() - started, 4),
                        "error_type": type(exc).__name__,
                    }
                )
                raise
            self._brain_load_trace.update(
                {
                    "status": "ready",
                    "elapsed_seconds": round(time.perf_counter() - started, 4),
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
        return self._brain

    def start_brain_prewarm(self):
        if not WEB_PREWARM_BRAIN or self._brain is not None:
            return False
        if self._brain_prewarm_thread and self._brain_prewarm_thread.is_alive():
            return False

        def load():
            try:
                self.get_brain()
            except Exception as exc:
                print(Fore.YELLOW + f"⚠️ [Web] Brain prewarm failed: {type(exc).__name__}")

        self._brain_load_trace["status"] = "queued"
        self._brain_prewarm_thread = threading.Thread(
            target=load,
            daemon=True,
            name="uruha-brain-prewarm",
        )
        self._brain_prewarm_thread.start()
        return True

    def mark_activity(self):
        self._last_activity_at = time.time()

    def begin_human_turn(self):
        """Register human work before it enters Gradio's queued executor."""
        with self._human_gate_lock:
            self._human_waiters += 1
            self._scheduler_trace.update(
                {
                    "human_waiters": self._human_waiters,
                    "last_decision": "human_admitted",
                    "human_priority_active": True,
                }
            )
        self.mark_activity()
        return time.perf_counter()

    def finish_human_turn(self):
        with self._human_gate_lock:
            self._human_waiters = max(0, self._human_waiters - 1)
            self._scheduler_trace.update(
                {
                    "human_waiters": self._human_waiters,
                    "last_decision": "human_completed",
                    "human_priority_active": self._human_waiters > 0,
                }
            )

    def human_turn_pending(self):
        with self._human_gate_lock:
            return self._human_waiters > 0

    def scheduler_trace(self):
        with self._human_gate_lock:
            return dict(self._scheduler_trace)

    def _record_background_decision(self, status, decision):
        with self._human_gate_lock:
            self._scheduler_trace.update(
                {
                    "human_waiters": self._human_waiters,
                    "background_status": status,
                    "last_decision": decision,
                    "human_priority_active": self._human_waiters > 0,
                }
            )

    def run_background_once(self):
        """Run one cooperative background tick without queueing ahead of a human."""
        if self._brain is None:
            self._record_background_decision("skipped", "brain_not_ready")
            return None
        if self.human_turn_pending():
            self._record_background_decision("skipped", "human_waiting")
            return None
        if not self._lock.acquire(blocking=False):
            self._record_background_decision("skipped", "brain_busy")
            return None
        try:
            if self.human_turn_pending():
                self._record_background_decision("skipped", "human_arrived_before_background")
                return None
            self._record_background_decision("running", "background_admitted")
            background_cycle = self._brain.run_background_cycle
            if "allow_model_maintenance" in inspect.signature(background_cycle).parameters:
                result = background_cycle(allow_model_maintenance=False)
            else:
                result = background_cycle()
            self._record_background_decision(
                "completed" if result else "idle_noop",
                "background_completed" if result else "background_not_due",
            )
            return result
        finally:
            self._lock.release()

    def _idle_consolidation_loop(self):
        while True:
            time.sleep(10)
            try:
                result = self.run_background_once()
                if result:
                    self._last_idle_consolidation_at = time.time()
                    goal = result.get("goal") or {}
                    print(
                        Fore.CYAN
                        + "🧠 [Web] Autonomous background cycle: "
                        + f"goal={goal.get('kind') or 'unknown'} "
                        + f"writes={len(result.get('memory_writes') or [])}"
                    )
            except Exception as exc:
                print(Fore.YELLOW + f"⚠️ [Web] Autonomous cycle failed: {exc}")

    def get_ears(self):
        if self._ears is None:
            print(Fore.CYAN + f"👂 [Web] Loading Whisper {WEB_WHISPER_MODEL}...")
            self._ears = UruhaEars(model_name=WEB_WHISPER_MODEL, model_device=WEB_WHISPER_DEVICE)
        return self._ears

    def get_mouth(self):
        if self._mouth is None:
            print(Fore.CYAN + f"👄 [Web] Connecting TTS server: {WEB_TTS_BASE_URL}")
            self._mouth = UruhaMouth(base_url=WEB_TTS_BASE_URL)
        return self._mouth

    def reset_brain_session(self):
        brain = self.get_brain()
        db_path = os.path.abspath(
            os.getenv(
                "URUHA_WEB_SESSION_DB_PATH",
                os.path.join(tempfile.gettempdir(), "uruha_web_session_db"),
            )
        )
        brain.reset_session(db_path)
        self._session_id = self._new_session_id()
        self._turn_index = 0
        self.mark_activity()
        return brain


RUNTIME = RuntimeManager()


def _status_markdown():
    tts_info = "未初始化"
    if RUNTIME._mouth is not None:
        tts_info = f"base_url={RUNTIME._mouth.base_url}, model_id={RUNTIME._mouth.model_id}"
    consolidation_info = "N/A"
    autonomous_info = "N/A"
    if RUNTIME._brain is not None:
        memory_runtime = RUNTIME._brain.memory.get_runtime_snapshot()
        consolidation_info = (
            f"pending={memory_runtime.get('pending_consolidation_turns', 0)}, "
            f"last={memory_runtime.get('last_consolidation_at') or 'never'}"
        )
        runtime_state = RUNTIME._brain.get_runtime_snapshot()
        autonomous = runtime_state.get("last_autonomous_result") or {}
        autonomous_goal = ((autonomous.get("goal") or {}).get("label") if isinstance(autonomous.get("goal"), dict) else None) or "none"
        pending_proactive = (runtime_state.get("pending_proactive_turn") or {}).get("line") or "none"
        delivered_proactive = (runtime_state.get("last_proactive_delivery") or {}).get("line") or "none"
        autonomous_info = (
            f"tick={runtime_state.get('autonomous_tick_index', 0)}, "
            f"goal={autonomous_goal}, "
            f"pending={pending_proactive}, "
            f"last_delivered={delivered_proactive}"
        )
    return (
        f"- Brain: {'loaded' if RUNTIME._brain is not None else 'lazy'}\n"
        f"- Whisper: model=`{WEB_WHISPER_MODEL}` device=`{WEB_WHISPER_DEVICE}`\n"
        f"- TTS: {tts_info}\n"
        f"- Session: `{RUNTIME._session_id}`\n"
        f"- Log: `{WEB_LOG_JSONL}`\n"
        f"- Annotation Log: `{HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH}`\n"
        f"- Consolidation: {consolidation_info}\n"
        f"- Autonomous: {autonomous_info}\n"
        f"- Note: this web UI is intended for a single active conversation session."
    )


def _append_history(history, role, content):
    history = list(history or [])
    history.append({"role": role, "content": content})
    return history


def _thinking_status(stage="idle"):
    return (
        _status_markdown()
        + "\n"
        + f"- Stage: `{stage}`"
    )


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _refresh_taxonomy_catalog():
    payload = _load_json(FAILURE_TAXONOMY_SCHEMA_PATH)
    if payload.get("failure_types"):
        return payload
    return _default_taxonomy_catalog()


TAXONOMY_CATALOG = _refresh_taxonomy_catalog()
TAXONOMY_VERSION = str(TAXONOMY_CATALOG.get("version") or "unknown")
FAILURE_TYPE_CHOICES = [
    (f"{item.get('code')} | {item.get('label_zh')}", item.get("code"))
    for item in (TAXONOMY_CATALOG.get("failure_types") or [])
]
VERDICT_CHOICES = [
    (item.get("label_zh"), item.get("value"))
    for item in (TAXONOMY_CATALOG.get("verdict_options") or [])
]
SEVERITY_CHOICES = [
    (item.get("label_zh"), item.get("value"))
    for item in (TAXONOMY_CATALOG.get("severity_options") or [])
]
VALID_FAILURE_TYPE_CODES = {item[1] for item in FAILURE_TYPE_CHOICES}


def _load_text(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _trim_text(text, limit=88):
    text = " ".join(str(text or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _load_unified_summary():
    return _load_json(UNIFIED_EVAL_SUMMARY_JSON_PATH) or {}


def _architecture_alignment_payload():
    unified = _load_unified_summary()
    if unified.get("alignment_snapshot"):
        return unified["alignment_snapshot"]

    arch = (_load_json(ARCH_REPORT_PATH) or {}).get("summary", {})
    v2 = (_load_json(V2_REPORT_PATH) or {}).get("summary", {})
    idle_result = arch.get("idle_consolidation_result") or {}
    return {
        "working_memory_buffer": {
            "status": "implemented" if arch.get("working_memory_budget_adherence") == 1.0 else "partial",
            "metric": arch.get("working_memory_budget_adherence"),
            "detail": "Memory query is filtered into a bounded working-memory view before planning.",
        },
        "high_low_road_router": {
            "status": "implemented" if arch.get("high_road_precision") == 1.0 and arch.get("low_road_precision") == 1.0 else "partial",
            "metric": {
                "high_road_precision": arch.get("high_road_precision"),
                "low_road_precision": arch.get("low_road_precision"),
            },
            "detail": "Low-road bypass is active for abuse/crisis and high-road remains the default.",
        },
        "bayesian_multi_plan": {
            "status": "implemented" if arch.get("bayesian_candidate_coverage") == 1.0 and arch.get("bayesian_probability_valid_rate") == 1.0 else "partial",
            "metric": {
                "candidate_coverage": arch.get("bayesian_candidate_coverage"),
                "probability_valid_rate": arch.get("bayesian_probability_valid_rate"),
            },
            "detail": "Planner now produces 3 candidate plans and reranks them with Bayesian-style scoring.",
        },
        "theory_of_mind_scratchpad": {
            "status": "partial" if arch.get("tom_subtext_proxy_rate", 0) < 0.8 else "implemented",
            "metric": {
                "scratchpad_presence_rate": arch.get("scratchpad_presence_rate"),
                "tom_subtext_proxy_rate": arch.get("tom_subtext_proxy_rate"),
            },
            "detail": "Internal monologue exists on every turn, but hidden-intent quality is only medium.",
        },
        "idle_memory_consolidation": {
            "status": "partial" if idle_result.get("wisdom_rule") in {None, "NO_RULE"} else "implemented",
            "metric": {
                "idle_consolidation_success": arch.get("idle_consolidation_success"),
                "last_rule": idle_result.get("wisdom_rule"),
            },
            "detail": "Idle consolidation is wired and running, but rule quality is still weak.",
        },
        "direct_answer_humanness": {
            "status": "implemented" if v2.get("direct_answer_rate_on_simple_queries", 0) >= 0.95 and v2.get("over_reframe_rate", 1.0) <= 0.03 else "partial",
            "metric": {
                "direct_answer_rate_on_simple_queries": v2.get("direct_answer_rate_on_simple_queries"),
                "over_reframe_rate": v2.get("over_reframe_rate"),
                "mode_match_rate": v2.get("mode_match_rate"),
            },
            "detail": "Simple queries are mostly answered directly instead of being over-reframed.",
        },
        "official_benchmarks": {
            "status": "partial",
            "metric": {
                "DailyDialog": "not yet",
                "ToMBench/ToMi": "proxy only",
                "MPI": "not yet",
                "RPEval": "proxy dimensions only",
            },
            "detail": "Current evals are literature-backed proxies, not full official benchmark reproductions.",
        },
    }


def _architecture_markdown():
    unified_md = _load_text(UNIFIED_EVAL_SUMMARY_MD_PATH).strip()
    if unified_md:
        return unified_md

    payload = _architecture_alignment_payload()
    lines = [
        "## Cognitive Architecture Alignment",
        "",
        "Current implementation is not fully identical to your blueprint. It is close on routing/planning, partial on ToM and consolidation, and incomplete on official benchmark integration.",
        "",
    ]
    for key, item in payload.items():
        lines.append(f"- `{key}`: **{item['status']}** — {item['detail']}")
    return "\n".join(lines)


def _annotation_report_markdown():
    text = _load_text(HUMAN_FEEDBACK_ANNOTATION_REPORT_MD_PATH).strip()
    if text:
        return text
    report = _load_json(HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH)
    summary = report.get("summary") or {}
    return "\n".join(
        [
            "## Human Annotation Report",
            "",
            f"- total_annotations: {summary.get('total_annotations', 0)}",
            f"- valid_annotations: {summary.get('valid_annotations', 0)}",
            f"- mixed_or_bad_cases: {summary.get('mixed_or_bad_cases', 0)}",
        ]
    )


def _annotation_candidate_markdown():
    text = _load_text(ANNOTATION_CANDIDATE_QUEUE_MD_PATH).strip()
    if text:
        return text
    report = _load_json(ANNOTATION_CANDIDATE_QUEUE_JSON_PATH)
    summary = report.get("summary") or {}
    return "\n".join(
        [
            "## Annotation Candidate Queue",
            "",
            f"- total_logged_turns: {summary.get('total_logged_turns', 0)}",
            f"- candidate_count: {summary.get('candidate_count', 0)}",
            f"- high_priority_count: {summary.get('high_priority_count', 0)}",
        ]
    )


def _annotation_draft_queue_payload():
    return _load_json(ANNOTATION_DRAFT_QUEUE_JSON_PATH) or {}


def _annotation_draft_queue_markdown():
    text = _load_text(ANNOTATION_DRAFT_QUEUE_MD_PATH).strip()
    if text:
        return text
    report = _annotation_draft_queue_payload()
    summary = report.get("summary") or {}
    return "\n".join(
        [
            "## Annotation Draft Queue",
            "",
            f"- candidate_count: {summary.get('candidate_count', 0)}",
            f"- draft_count: {summary.get('draft_count', 0)}",
            f"- high_priority_draft_count: {summary.get('high_priority_draft_count', 0)}",
        ]
    )


def _annotation_draft_choices():
    choices = []
    for row in (_annotation_draft_queue_payload().get("drafts") or [])[:100]:
        compact = row.get("compact_context") or {}
        label = (
            f"[{row.get('score', 0)}] "
            f"{compact.get('session_id') or '-'}#{compact.get('turn_index') or '-'} | "
            f"{_trim_text(compact.get('user_text') or '', 48)}"
        )
        choices.append((label, row.get("draft_id")))
    return choices


def _annotation_draft_rows(bucket_code="__ALL__", severity="ALL", reason_code="ALL", limit=None):
    rows = list((_annotation_draft_queue_payload().get("drafts") or []))
    if bucket_code and bucket_code != "__ALL__":
        rows = [row for row in rows if bucket_code in (row.get("suggested_failure_types") or [])]
    if severity and severity != "ALL":
        rows = [row for row in rows if row.get("suggested_severity") == severity]
    if reason_code and reason_code != "ALL":
        rows = [row for row in rows if reason_code in (row.get("reason_codes") or [])]
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    return rows


def _annotation_batch_bucket_choices():
    counter = {}
    for row in (_annotation_draft_queue_payload().get("drafts") or []):
        for code in row.get("suggested_failure_types") or []:
            counter[code] = counter.get(code, 0) + 1
    choices = [("ALL | 全部", "__ALL__")]
    label_map = {item[1]: item[0] for item in FAILURE_TYPE_CHOICES}
    for code, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]))):
        human_label = label_map.get(code, code)
        choices.append((f"{human_label} ({count})", code))
    return choices


def _annotation_batch_severity_choices():
    counter = {}
    for row in (_annotation_draft_queue_payload().get("drafts") or []):
        sev = row.get("suggested_severity") or "unknown"
        counter[sev] = counter.get(sev, 0) + 1
    choices = [("ALL | 全部", "ALL")]
    label_map = {item[1]: item[0] for item in SEVERITY_CHOICES}
    for sev, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]))):
        human_label = label_map.get(sev, sev)
        choices.append((f"{human_label} ({count})", sev))
    return choices


def _annotation_batch_reason_choices():
    counter = {}
    for row in (_annotation_draft_queue_payload().get("drafts") or []):
        for code in row.get("reason_codes") or []:
            counter[code] = counter.get(code, 0) + 1
    choices = [("ALL | 全部", "ALL")]
    for code, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]))):
        choices.append((f"{code} ({count})", code))
    return choices


def _find_annotation_draft(draft_id):
    if not draft_id:
        return {}
    for row in _annotation_draft_queue_payload().get("drafts") or []:
        if row.get("draft_id") == draft_id:
            return row
    return {}


def _annotation_draft_preview_markdown(draft_id=None):
    if not draft_id:
        summary = (_annotation_draft_queue_payload().get("summary") or {})
        return "\n".join(
            [
                "### Annotation Draft Preview",
                f"- draft_count=`{summary.get('draft_count', 0)}`",
                f"- high_priority=`{summary.get('high_priority_draft_count', 0)}`",
                "- 選一筆 draft 後可直接載入到 Human Annotation 表單。",
            ]
        )

    row = _find_annotation_draft(draft_id)
    if not row:
        return "### Annotation Draft Preview\n- draft not found"

    compact = row.get("compact_context") or {}
    return "\n".join(
        [
            "### Annotation Draft Preview",
            f"- draft_id=`{row.get('draft_id')}` score=`{row.get('score')}`",
            f"- session=`{compact.get('session_id')}` turn=`{compact.get('turn_index')}`",
            f"- user=`{compact.get('user_text') or ''}`",
            f"- reply=`{compact.get('assistant_reply') or ''}`",
            f"- intent=`{compact.get('intent') or '-'}` scene=`{compact.get('scene') or '-'}`",
            f"- suggested_verdict=`{row.get('suggested_verdict')}` severity=`{row.get('suggested_severity')}`",
            f"- suggested_failure=`{_compact_failure_list(row.get('suggested_failure_types'))}`",
            f"- reasons=`{_compact_failure_list(row.get('reason_codes'))}`",
            f"- notes=`{row.get('suggested_notes') or ''}`",
        ]
    )


def _annotation_batch_review_markdown(bucket_code="__ALL__", severity="ALL", reason_code="ALL", take_count=5):
    rows = _annotation_draft_rows(bucket_code, severity, reason_code, limit=take_count)
    bucket_label = "ALL" if bucket_code in {None, "", "__ALL__"} else bucket_code
    lines = [
        "### Batch Review",
        f"- bucket=`{bucket_label}` severity=`{severity}` reason=`{reason_code}`",
        f"- take_count=`{take_count}`",
        f"- available_after_filter=`{len(_annotation_draft_rows(bucket_code, severity, reason_code, limit=None))}`",
    ]
    if not rows:
        lines.append("- 目前沒有符合條件的 draft。")
        return "\n".join(lines)

    for row in rows:
        compact = row.get("compact_context") or {}
        lines.extend(
            [
                "",
                (
                    f"- draft_id=`{row.get('draft_id')}` score=`{row.get('score')}` "
                    f"verdict=`{row.get('suggested_verdict')}` severity=`{row.get('suggested_severity')}`"
                ),
                f"  - failure=`{_compact_failure_list(row.get('suggested_failure_types'))}`",
                f"  - reasons=`{_compact_failure_list(row.get('reason_codes'))}`",
                f"  - user=`{compact.get('user_text') or ''}`",
                f"  - reply=`{compact.get('assistant_reply') or ''}`",
            ]
        )
    return "\n".join(lines)


def _regression_eval_markdown():
    text = _load_text(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_MD_PATH).strip()
    if text:
        return text
    report = _load_json(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH)
    summary = report.get("summary") or {}
    return "\n".join(
        [
            "## Human Feedback Regression Eval",
            "",
            f"- total_cases: {summary.get('total_cases', 0)}",
            f"- overall_auto_pass_rate: {summary.get('overall_auto_pass_rate', 0.0)}",
            f"- generic_reply_rate: {summary.get('generic_reply_rate', 0.0)}",
        ]
    )


def _regression_diff_markdown():
    text = _load_text(HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_MD_PATH).strip()
    if text:
        return text
    report = _load_json(HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH)
    summary = report.get("summary") or {}
    return "\n".join(
        [
            "## Human Feedback Regression Diff",
            "",
            f"- improved_metric_count: {summary.get('improved_metric_count', 0)}",
            f"- regressed_metric_count: {summary.get('regressed_metric_count', 0)}",
            f"- improved_case_count: {summary.get('improved_case_count', 0)}",
            f"- regressed_case_count: {summary.get('regressed_case_count', 0)}",
        ]
    )


def _unified_eval_json():
    return _load_unified_summary()


def _get_file_info(path):
    if not path or not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        dt = datetime.fromtimestamp(mtime)
        return {
            "mtime": mtime,
            "time_str": dt.isoformat(timespec="seconds"),
            "name": os.path.basename(path)
        }
    except Exception:
        return None


def _all_snapshot_meta_paths():
    if not os.path.exists(HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR):
        return []
    try:
        meta_files = sorted([
            f for f in os.listdir(HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR)
            if f.endswith(".meta.json")
        ], reverse=True)
        return [os.path.join(HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR, f) for f in meta_files]
    except Exception:
        return []


def _snapshot_picker_choices():
    paths = _all_snapshot_meta_paths()
    if not paths:
        return [("None | 無快照", "")]
    choices = []
    for p in paths:
        fname = os.path.basename(p)
        meta = _load_json(p)
        label = meta.get("label", "manual")
        # 檔名格式通常是 YYYYMMDD_HHMMSS_label.meta.json
        ts = fname.split("_")[0] if "_" in fname else "-"
        display = f"[{ts}] {label} ({fname.replace('.meta.json', '')})"
        choices.append((display, p))
    return choices


def _resolve_snapshot_picker_value(current_val, choices):
    """
    解析刷新後的 picker value。
    1. 若 choices 為空，返回 ""
    2. 若 current_val 為空 -> Fallback 到最新 (choices[0][1])
    3. 若 current_val 非空 -> 保留原值 (不論是否 valid)，以維持 UI surface integrity
    """
    if not choices or choices[0][1] == "":
        return ""

    if not current_val:
        return choices[0][1] # Fallback to latest

    return current_val # Preserve surface state even if invalid



def _resolve_auto_diff_baseline_json(selected_meta_path):
    """
    為自動重跑 diff 流程解析應使用的 baseline json 路徑。
    回傳 (path, status_code)
    """
    # 1. 真正空選擇 -> 允許 Fallback 到最新快照
    if not selected_meta_path:
        latest_meta = _load_latest_snapshot_metadata()
        if latest_meta:
            path = latest_meta.get("snapshot_json")
            if path and os.path.exists(path):
                return path, "fallback_latest"
        return None, "no_baseline"

    # 2. 非空選擇 -> 必須有效，不得靜默 fallback
    if os.path.exists(selected_meta_path):
        meta = _load_json(selected_meta_path)
        path = meta.get("snapshot_json")
        if path and os.path.exists(path):
            return path, "success"
        else:
            return None, "invalid_snapshot_json"
    else:
        return None, "invalid_meta_path"


def _replay_diff_status_text(status_code, fallback="unknown reason"):
    mapping = {
        "no_baseline": "無任何基準快照",
        "invalid_meta_path": "選中的基準元數據已遺失",
        "invalid_snapshot_json": "選中的基準數據檔已遺失",
        "subprocess_failed": "Diff 腳本執行異常",
        "no_new_accepts": "無新採納草稿",
        "all_skipped": "重複草稿已被略過 (all skipped)",
        "current_eval_missing": "找不到目前的評測報表",
    }
    return mapping.get(status_code, fallback)


def _architecture_diff_status_text(status_code, fallback="skipped or failed"):
    mapping = {
        "no_baseline": "跳過：目前無任何基準快照 (no baseline available)",
        "invalid_meta_path": "跳過：選中的基準元數據已遺失 (selected meta missing)",
        "invalid_snapshot_json": "跳過：選中的基準數據檔已遺失 (snapshot json missing)",
        "subprocess_failed": "失敗：Diff 腳本執行異常 (script failed)",
        "current_eval_missing": "跳過：找不到目前的評測報表 (current eval missing)",
    }
    return mapping.get(status_code, fallback)


def _regression_unavailable_diff_markdown(status_code, surface="replay", fallback="skipped or failed"):
    if surface == "architecture":
        reason_text = _architecture_diff_status_text(status_code, fallback=fallback)
    else:
        reason_text = _replay_diff_status_text(status_code, fallback=fallback)
    return f"*Diff report unavailable ({reason_text})*"


def _unavailable_diff_response_payload(status_code, selected_meta_path, surface="replay", fallback="skipped or failed"):
    """
    Centralized helper to build the payload for unavailable diff states.
    Ensures diff markdown, empty json, and freshness are aligned.
    """
    diff_md = _regression_unavailable_diff_markdown(status_code, surface=surface, fallback=fallback)
    diff_json = {}
    fresh_md = _regression_freshness_markdown(selected_meta_path, diff_unavailable=True)
    return diff_md, diff_json, fresh_md


def _assemble_regression_panel_bundle(current_picker_val, diff_ran=True, diff_status=None, surface="replay", fallback_text=None, run_replay=True, has_rows=True, accepted_count=None, include_diff_panel=True):
    """
    Centralized builder for regression panel state components.
    Handles picker refresh, freshness, diff panel, and optional eval panel.
    """
    # 1. Snapshot Picker Refresh & Value Preservation
    new_choices = _snapshot_picker_choices()
    preserved_val = _resolve_snapshot_picker_value(current_picker_val, new_choices)

    # 2. Eval Panel Logic (Gated by run_replay)
    if not run_replay:
        eval_md = gr.update()
        eval_json = gr.update()
    elif not has_rows:
        eval_md = "*Evaluation skipped (no data)*"
        eval_json = {}
    elif accepted_count is not None and accepted_count <= 0:
        eval_md = "*Evaluation skipped (no new accepts)*"
        eval_json = {}
    else:
        eval_md = _regression_eval_markdown()
        eval_json = _load_json(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH)

    if fallback_text is None:
        fallback_text = "no rows accepted" if not has_rows else "skipped or failed"

    # 3. Diff Panel & Freshness Logic (Aligned with diff_ran)
    if not include_diff_panel:
        diff_md = gr.update()
        diff_json = gr.update()
        fresh_md = _regression_freshness_markdown(preserved_val, diff_unavailable=False)
    elif diff_ran:
        diff_md = _regression_diff_markdown()
        diff_json = _load_json(HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH)
        fresh_md = _regression_freshness_markdown(preserved_val, diff_unavailable=False)
    else:
        # Use existing helper for unavailable state consistency
        diff_md, diff_json, fresh_md = _unavailable_diff_response_payload(
            diff_status, preserved_val, surface=surface, fallback=fallback_text
        )

    return {
        "eval_md": eval_md,
        "eval_json": eval_json,
        "diff_md": diff_md,
        "diff_json": diff_json,
        "fresh_md": fresh_md,
        "picker_update": gr.update(choices=new_choices, value=preserved_val),
        "snapshot_status_md": _regression_snapshot_markdown(),
        "unified_eval_json": _load_unified_summary(),
    }


def _regression_freshness_markdown(selected_meta_path=None, diff_unavailable=False):
    eval_info = _get_file_info(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH)

    snap_meta = None
    baseline_title = "Baseline"
    invalid_selection = False

    if not selected_meta_path:
        # 1. Empty Selection -> Fallback to latest
        snap_meta = _load_latest_snapshot_metadata()
        baseline_title = "Latest Baseline (Default)"
        selected_meta_path = (_all_snapshot_meta_paths() or [None])[0]
    elif os.path.exists(selected_meta_path):
        # 2. Valid Selection
        snap_meta = _load_json(selected_meta_path)
        is_latest = (selected_meta_path == (_all_snapshot_meta_paths() or [None])[0])
        baseline_title = "Selected Baseline" if not is_latest else "Latest Baseline (Selected)"
    else:
        # 3. Invalid Selection -> Explicit Error
        invalid_selection = True
        baseline_title = "Selected Baseline (INVALID)"

    # 若強制標記為不可用，則不讀取現有 diff 報表，防止 stale 矛盾
    if diff_unavailable:
        diff_report = {}
        diff_info = None
    else:
        diff_report = _load_json(HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH)
        diff_info = _get_file_info(HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH)

    lines = ["### Regression Data Provenance & Freshness"]

    # 1. Current Eval
    if eval_info:
        lines.append(f"- **Current Eval**: `{eval_info['time_str']}` ({eval_info['name']})")
    else:
        lines.append("- **Current Eval**: `missing` (請先執行 Replay Eval)")

    # 2. Baseline
    if invalid_selection:
        lines.append(f"- **{baseline_title}**: `❌ File Missing` ({os.path.basename(selected_meta_path or 'null')})")
    elif snap_meta:
        lines.append(f"- **{baseline_title}**: `{snap_meta.get('created_at', '-')}` ({snap_meta.get('label', 'manual')})")
    else:
        lines.append(f"- **{baseline_title}**: `missing` (請先建立 Snapshot)")

    # 3. Current Diff
    diff_prov = diff_report.get("baseline_provenance") or {}
    diff_baseline_label = diff_prov.get("label", "unknown")
    diff_baseline_path = diff_prov.get("path", "")
    diff_baseline_time = diff_prov.get("created_at", "unknown time")

    if diff_unavailable:
        lines.append("- **Current Diff**: `unavailable` (本次執行未產出)")
    elif diff_info:
        diff_baseline_id = f"`{diff_baseline_label}` ({diff_baseline_time})"
        lines.append(f"- **Current Diff**: `{diff_info['time_str']}` (Baseline: {diff_baseline_id})")
    else:
        lines.append("- **Current Diff**: `missing` (請執行 Run Regression Diff)")

    # 4. Freshness & Match Logic
    freshness = "unknown"
    if diff_unavailable:
        freshness = "❌ **Unavailable**: Diff is not in sync with current turn"
    elif invalid_selection:
        freshness = "❌ **Invalid Baseline**: Cannot determine freshness"
    elif not diff_info:
        freshness = "❌ Diff Report Missing"
    elif not eval_info or not snap_meta:
        freshness = "⚠️ Incomplete Data (Diff status unreliable)"
    else:
        # 4a. Check Baseline Alignment (Provenance Match)
        # Convert meta path to expected snapshot json path
        expected_snap_json = snap_meta.get("snapshot_json")
        actual_diff_baseline_json = diff_baseline_path

        # 4b. Check Time Freshness
        diff_mtime = diff_info["mtime"]
        eval_mtime = eval_info["mtime"]

        snap_mtime = 0
        if expected_snap_json and os.path.exists(expected_snap_json):
            snap_mtime = os.path.getmtime(expected_snap_json)

        # Determine status
        if not actual_diff_baseline_json:
            freshness = "⚠️ **UNKNOWN / LEGACY**: Diff report lacks baseline provenance. Cannot verify alignment. Please rerun diff."
        elif actual_diff_baseline_json != expected_snap_json:
            diff_baseline_id = f"`{diff_baseline_label}` ({diff_baseline_time})"
            freshness = f"❌ **MISMATCH**: Diff was generated against {diff_baseline_id}, but you selected a different baseline."
        elif diff_mtime < eval_mtime - 1.0:
            freshness = "❌ **STALE**: Diff is older than Current Eval"
        elif diff_mtime < snap_mtime - 1.0:
            freshness = "❌ **STALE**: Diff is older than Baseline modification"
        else:
            freshness = "✅ **CURRENT**: Diff matches selected Baseline and latest Eval"

    lines.append(f"\n**Overall Status**: {freshness}")
    return "\n".join(lines)


def _load_latest_snapshot_metadata():
    if not os.path.exists(HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR):
        return {}
    try:
        meta_files = [
            f for f in os.listdir(HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR)
            if f.endswith(".meta.json")
        ]
        if not meta_files:
            return {}
        meta_files.sort(reverse=True)
        latest_meta_path = os.path.join(HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR, meta_files[0])
        return _load_json(latest_meta_path)
    except Exception:
        return {}


def _regression_snapshot_markdown():
    meta = _load_latest_snapshot_metadata()
    if not meta:
        return "### Latest Regression Baseline\n- 目前無任何快照。"

    return "\n".join([
        "### Latest Regression Baseline",
        f"- **Label**: `{meta.get('label', 'unknown')}`",
        f"- **Created**: `{meta.get('created_at', '-')}`",
        f"- **Cases**: `{meta.get('total_cases', 0)}`",
        f"- **Pass Rate**: `{meta.get('overall_auto_pass_rate', 0.0)}`",
        f"- **Generic Rate**: `{meta.get('generic_reply_rate', 0.0)}`",
        f"- **File**: `{os.path.basename(meta.get('snapshot_json', ''))}`",
    ])


def create_regression_snapshot(label):
    label = str(label or "manual").strip()
    if not label:
        label = "manual"

    if not os.path.exists(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH):
        return (
            f"❌ 建立快照失敗：找不到目前的評測報表 {HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH}。請先執行 Replay Eval。",
            _regression_snapshot_markdown(),
            _regression_freshness_markdown(),
            gr.update() # snapshot_picker
        )

    try:
        cmd = [sys.executable, os.path.join(BASE_DIR, "snapshot_human_feedback_regression_eval.py"), "--label", label]
        subprocess.run(cmd, cwd=BASE_DIR, check=True, timeout=60)

        new_choices = _snapshot_picker_choices()
        new_value = (new_choices[0][1] if new_choices else "") # 自動選中最新

        return (
            f"✅ 已成功建立快照：{label}",
            _regression_snapshot_markdown(),
            _regression_freshness_markdown(new_value),
            gr.update(choices=new_choices, value=new_value)
        )
    except Exception as e:
        return (
            f"❌ 建立快照時發生非預期錯誤: {e}",
            _regression_snapshot_markdown(),
            _regression_freshness_markdown(),
            gr.update()
        )


def run_regression_diff_manually(selected_meta_path):
    if not os.path.exists(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH):
        bundle = _assemble_regression_panel_bundle(selected_meta_path, diff_ran=False, diff_status="current_eval_missing", run_replay=False)
        return (
            "❌ Diff 跳過：找不到目前的評測報表 (current eval missing)。請先執行 Replay Eval。",
            bundle["diff_md"],
            bundle["diff_json"],
            bundle["fresh_md"]
        )

    snap_meta = None
    if not selected_meta_path:
        # 1. Empty Selection -> Fallback to latest
        snap_meta = _load_latest_snapshot_metadata()
    elif os.path.exists(selected_meta_path):
        # 2. Valid Selection
        snap_meta = _load_json(selected_meta_path)
    else:
        # 3. Invalid Selection -> Explicit Error
        bundle = _assemble_regression_panel_bundle(selected_meta_path, diff_ran=False, diff_status="invalid_meta_path", run_replay=False)
        return (
            f"❌ Diff 跳過：選中的快照元數據檔案遺失 ({os.path.basename(selected_meta_path)})。請重新整理快照列表。",
            bundle["diff_md"],
            bundle["diff_json"],
            bundle["fresh_md"]
        )

    if not snap_meta:
        bundle = _assemble_regression_panel_bundle(selected_meta_path, diff_ran=False, diff_status="no_baseline", run_replay=False)
        return (
            "❌ Diff 跳過：無 baseline snapshot。請先建立 Snapshot。",
            bundle["diff_md"],
            bundle["diff_json"],
            bundle["fresh_md"]
        )

    try:
        snap_json = snap_meta.get("snapshot_json")
        if not snap_json or not os.path.exists(snap_json):
             bundle = _assemble_regression_panel_bundle(selected_meta_path, diff_ran=False, diff_status="invalid_snapshot_json", run_replay=False)
             return (
                f"❌ Diff 跳過：選中的快照 JSON 遺失 ({os.path.basename(snap_json or 'null')})",
                bundle["diff_md"],
                bundle["diff_json"],
                bundle["fresh_md"]
            )

        cmd = [sys.executable, REGRESSION_DIFF_SCRIPT, "--before", snap_json]
        subprocess.run(cmd, cwd=BASE_DIR, check=True, timeout=600)

        bundle = _assemble_regression_panel_bundle(selected_meta_path, diff_ran=True, run_replay=False)
        return (
            f"✅ 已成功對標刷新 Regression Diff (Baseline: {snap_meta.get('label', 'unknown')})",
            bundle["diff_md"],
            bundle["diff_json"],
            bundle["fresh_md"]
        )
    except Exception as e:
        bundle = _assemble_regression_panel_bundle(selected_meta_path, diff_ran=False, diff_status="subprocess_failed", run_replay=False)
        return (
            f"❌ 執行 Diff 腳本時發生錯誤: {e}",
            bundle["diff_md"],
            bundle["diff_json"],
            bundle["fresh_md"]
        )


def _run_architecture_checks(current_snap_picker_val):
    commands = [
        [sys.executable, ARCH_DATASET_SCRIPT],
        [sys.executable, ARCH_EVAL_SCRIPT],
        [sys.executable, ANNOTATION_QUEUE_SCRIPT],
        [sys.executable, ANNOTATION_DRAFT_SCRIPT],
        [sys.executable, ANNOTATION_REPORT_SCRIPT],
        [sys.executable, REGRESSION_DATASET_SCRIPT],
        [sys.executable, REGRESSION_EVAL_SCRIPT],
        [sys.executable, os.path.join(BASE_DIR, "eval_v2_human_answer.py")],
        [sys.executable, UNIFIED_SUMMARY_SCRIPT],
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=BASE_DIR, check=True, timeout=600)

    # 解析並重跑 diff
    baseline_json, resolve_status = _resolve_auto_diff_baseline_json(current_snap_picker_val)
    auto_diff_success = False
    failure_reason = resolve_status

    if baseline_json and resolve_status in ("success", "fallback_latest"):
        try:
            subprocess.run([sys.executable, REGRESSION_DIFF_SCRIPT, "--before", baseline_json], cwd=BASE_DIR, check=True, timeout=600)
            auto_diff_success = True
        except Exception:
            auto_diff_success = False
            failure_reason = "subprocess_failed"
    else:
        auto_diff_success = False

    bundle = _assemble_regression_panel_bundle(
        current_snap_picker_val,
        diff_ran=auto_diff_success,
        diff_status=failure_reason,
        surface="architecture"
    )

    return (
        _architecture_markdown(),
        _architecture_alignment_payload(),
        _load_json(ARCH_REPORT_PATH),
        _load_json(V2_REPORT_PATH),
        _annotation_candidate_markdown(),
        _load_json(ANNOTATION_CANDIDATE_QUEUE_JSON_PATH),
        _annotation_draft_queue_markdown(),
        _annotation_draft_queue_payload(),
        _annotation_report_markdown(),
        _load_json(HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH),
        bundle["eval_md"],
        bundle["eval_json"],
        bundle["diff_md"],
        bundle["diff_json"],
        bundle["unified_eval_json"],
        bundle["snapshot_status_md"],
        bundle["fresh_md"],
        bundle["picker_update"],
        _status_markdown(),
    )


def _extract_trace_payload(result):
    logic = result.get("logic", {})
    mems = result.get("memory_data", {})
    return {
        "route_info": result.get("route_info"),
        "psyche_before": result.get("psyche_before"),
        "psyche_after": result.get("psyche_after"),
        "internal_monologue": logic.get("internal_monologue"),
        "planner_tick_trace": logic.get("planner_tick_trace"),
        "planner_tick_count": logic.get("planner_tick_count"),
        "self_correction_applied": logic.get("self_correction_applied"),
        "response_mode": logic.get("response_mode"),
        "surface_act": logic.get("surface_act"),
        "payload_level": logic.get("payload_level"),
        "cognitive_mode": logic.get("cognitive_mode"),
        "premise_check": logic.get("premise_check"),
        "subjective_note_jp": logic.get("subjective_note_jp"),
        "grounding": logic.get("grounding"),
        "bayes_candidates": logic.get("bayes_candidates"),
        "working_memory_summary": mems.get("working_memory_summary"),
        "working_memory_items": mems.get("working_memory_items"),
        "memory_provenance": mems.get("memory_provenance"),
        "reflection": result.get("reflection"),
        "memory_runtime": result.get("memory_runtime"),
        "runtime_trace": result.get("runtime_trace"),
        "runtime_state": result.get("runtime_state"),
    }


def _extract_memory_payload(result):
    mems = result.get("memory_data", {})
    return {
        "profile_summary": mems.get("profile"),
        "profile_structured": mems.get("profile_structured"),
        "recent_dialogue": mems.get("recent_dialogue"),
        "recent_turns": mems.get("recent_turns"),
        "short_term_summary": mems.get("short_term_summary"),
        "knowledge": mems.get("knowledge"),
        "episodes": mems.get("episodes"),
        "wisdom": mems.get("wisdom"),
        "procedural": mems.get("procedural"),
        "working_memory_summary": mems.get("working_memory_summary"),
        "working_memory_items": mems.get("working_memory_items"),
        "memory_provenance": mems.get("memory_provenance"),
    }


M24_CLIENT_COGNITION_BUDGET_BYTES = 360_000
M24_CLIENT_MEMORY_BUDGET_BYTES = 120_000
M24_CLIENT_TURN_BUDGET_BYTES = 520_000


def _json_size_m24(value):
    try:
        return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return len(str(value or "").encode("utf-8"))


def _bounded_client_value_m24(value, depth=0):
    """Bound browser payloads while the complete turn remains in local JSONL."""
    if depth >= 5:
        if isinstance(value, dict):
            return {"__m24_omitted__": f"dict:{len(value)}"}
        if isinstance(value, list):
            return {"__m24_omitted__": f"list:{len(value)}"}
    if isinstance(value, dict):
        keys = list(value.keys())
        retained = keys[:48]
        preview = {
            str(key): _bounded_client_value_m24(value.get(key), depth + 1)
            for key in retained
        }
        if len(keys) > len(retained):
            preview["__m24_omitted_keys__"] = len(keys) - len(retained)
        return preview
    if isinstance(value, list):
        retained = value[:16]
        preview = [_bounded_client_value_m24(item, depth + 1) for item in retained]
        if len(value) > len(retained):
            preview.append({"__m24_omitted_items__": len(value) - len(retained)})
        return preview
    if isinstance(value, str) and len(value) > 900:
        return value[:820] + f"… [M24 omitted {len(value) - 820} chars]"
    return value


def _compact_runtime_trace_m24(runtime_trace):
    runtime_trace = runtime_trace or {}
    retained_keys = (
        "cycle_index",
        "focus",
        "goal",
        "route_info",
        "blackboard",
        "selected_plan",
        "planner_tick_trace",
        "visible_language_guard",
        "user_mental_state_hypothesis",
        "hypothesis_verification",
        "hypothesis_calibration",
        "human_pragmatic_understanding_v2_13",
        "pragmatic_verification_v2_13",
        "longitudinal_user_model_v2_13",
        "longitudinal_model_update_v2_13",
        "personhood_loop_v2_13",
        "adaptive_person_model_m18",
        "adaptive_person_feedback_m18",
        "adaptive_context_scope_m18",
        "adaptive_scope_hierarchy_m18",
        "desired_response_state_m18",
        "desired_response_candidates_m18",
        "adaptive_response_dimensions_m18",
        "desired_response_prediction_m18",
        "adaptive_person_persistence_m18",
        "adaptive_person_surface_commitment_m18",
        "runtime_latency_m19",
        "human_priority_scheduler_m19",
        "correction_aware_surface_m20",
        "correction_surface_commit_m20",
        "surface_delivery_m20",
        "bounded_slow_path_planner_m21",
        "semantic_route_classifier_m22",
        "semantic_route_outcome_m22",
        "desired_response_mode_m23",
        "desired_response_surface_contract_m23",
        "explicit_desired_response_m25",
        "implicit_desired_response_m26",
        "causal_outcome_calibration_m27",
        "feedback_topic_transition_m28",
        "literal_topic_projection_m29",
        "semantic_authorization_m31",
        "semantic_commit_repair_m32",
        "source_semantic_atoms_m33",
        "semantic_atom_verification_m33",
        "source_anchored_semantic_commit_m33",
        "counterfactual_pragmatic_branch_m34",
        "memory_diff",
        "memory_writes",
    )
    return _bounded_client_value_m24(
        {key: runtime_trace.get(key) for key in retained_keys if key in runtime_trace}
    )


def _compact_runtime_state_m24(runtime_state):
    runtime_state = runtime_state or {}
    compact = {
        key: runtime_state.get(key)
        for key in (
            "cycle_index",
            "current_focus",
            "active_goal",
            "psyche",
            "open_loops",
            "adaptive_person_model",
            "current_desired_response_state",
            "last_desired_response_decision",
            "last_state_diff",
            "scheduler",
        )
        if key in runtime_state
    }
    compact["retained_history_counts"] = {
        "recent_turn_traces": len(runtime_state.get("recent_turn_traces") or []),
        "recent_autonomous_traces": len(runtime_state.get("recent_autonomous_traces") or []),
        "full_history_in_browser": False,
    }
    return _bounded_client_value_m24(compact)


def _client_cognition_payload_m24(cognition):
    """Return the progressive browser view, not the complete research record."""
    cognition = cognition or {}
    compact = {
        key: _bounded_client_value_m24(cognition.get(key))
        for key in (
            "route_info",
            "psyche_before",
            "psyche_after",
            "internal_monologue",
            "planner_tick_trace",
            "planner_tick_count",
            "self_correction_applied",
            "response_mode",
            "surface_act",
            "payload_level",
            "cognitive_mode",
            "premise_check",
            "subjective_note_jp",
            "grounding",
            "bayes_candidates",
            "working_memory_summary",
            "working_memory_items",
            "memory_provenance",
            "reflection",
            "memory_runtime",
        )
        if key in cognition
    }
    compact["runtime_trace"] = _compact_runtime_trace_m24(
        cognition.get("runtime_trace")
    )
    compact["runtime_state"] = _compact_runtime_state_m24(
        cognition.get("runtime_state")
    )
    original_bytes = _json_size_m24(cognition)
    compact_bytes = _json_size_m24(compact)
    compact["payload_budget_m24"] = {
        "schema": "uruha_progressive_client_payload_m24",
        "original_cognition_bytes": original_bytes,
        "browser_cognition_bytes": compact_bytes,
        "browser_budget_bytes": M24_CLIENT_COGNITION_BUDGET_BYTES,
        "budget_met": compact_bytes <= M24_CLIENT_COGNITION_BUDGET_BYTES,
        "full_trace_retained_in": "local_web_jsonl",
        "progressive_detail": True,
    }
    return compact


def _client_memory_payload_m24(memory):
    memory = memory or {}
    compact = _bounded_client_value_m24(memory)
    compact_bytes = _json_size_m24(compact)
    if isinstance(compact, dict):
        compact["payload_budget_m24"] = {
            "schema": "uruha_progressive_memory_payload_m24",
            "original_memory_bytes": _json_size_m24(memory),
            "browser_memory_bytes": compact_bytes,
            "browser_budget_bytes": M24_CLIENT_MEMORY_BUDGET_BYTES,
            "budget_met": compact_bytes <= M24_CLIENT_MEMORY_BUDGET_BYTES,
            "full_trace_retained_in": "local_web_jsonl",
        }
    return compact


def _client_turn_record_m24(record, cognition, memory):
    record = record or {}
    compact = {
        key: record.get(key)
        for key in (
            "timestamp",
            "session_id",
            "turn_index",
            "input_mode",
            "user_text",
            "assistant_reply",
            "planner_debug",
        )
        if key in record
    }
    logic = record.get("logic") or {}
    compact["logic"] = _bounded_client_value_m24(
        {
            key: logic.get(key)
            for key in (
                "intent",
                "scene",
                "response_mode",
                "surface_act",
                "payload_level",
                "grounding",
                "routing_path",
                "desired_response_mode_m23",
                "desired_response_surface_contract_m23",
                "explicit_desired_response_m25",
                "implicit_desired_response_m26",
                "causal_outcome_calibration_m27",
                "feedback_topic_transition_m28",
                "literal_topic_projection_m29",
                "semantic_authorization_m31",
                "semantic_commit_repair_m32",
                "source_semantic_atoms_m33",
                "semantic_atom_verification_m33",
                "source_anchored_semantic_commit_m33",
                "counterfactual_pragmatic_branch_m34",
                "semantic_route_classifier_m22",
                "semantic_route_outcome_m22",
                "bounded_slow_path_planner_m21",
            )
            if key in logic
        }
    )
    compact["cognition_trace"] = cognition
    compact["memory_snapshot"] = memory
    compact_bytes = _json_size_m24(compact)
    compact["payload_budget_m24"] = {
        "schema": "uruha_progressive_turn_state_m24",
        "original_turn_bytes": _json_size_m24(record),
        "browser_turn_bytes": compact_bytes,
        "browser_budget_bytes": M24_CLIENT_TURN_BUDGET_BYTES,
        "budget_met": compact_bytes <= M24_CLIENT_TURN_BUDGET_BYTES,
        "full_turn_retained_in": "local_web_jsonl",
    }
    return compact


def _observatory_result_from_log_record(record):
    record = record or {}
    cognition = record.get("cognition_trace") or {}
    memory_data = dict(record.get("memory_snapshot") or {})
    if not memory_data.get("working_memory_items"):
        memory_data["working_memory_items"] = cognition.get("working_memory_items") or []
    if not memory_data.get("memory_provenance"):
        memory_data["memory_provenance"] = cognition.get("memory_provenance") or {}
    return {
        "user_text": record.get("user_text") or "",
        "reply": record.get("assistant_reply") or "",
        "memory_data": memory_data,
        "runtime_trace": cognition.get("runtime_trace") or {},
        "runtime_state": cognition.get("runtime_state") or {},
    }


def _latest_observatory_result():
    try:
        with open(WEB_LOG_JSONL, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return {}
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except (TypeError, ValueError):
            continue
        result = _observatory_result_from_log_record(record)
        if result.get("runtime_trace", {}).get("blackboard"):
            return result
    return {}


def _preview_payload(payload):
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception:
        return str(payload)


def _float_or_zero(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def _empty_html(title, body):
    return (
        f'<div class="trace-empty"><strong>{escape(title)}</strong>'
        f'<div style="margin-top:8px;">{escape(body)}</div></div>'
    )


def _empty_flow_html(body):
    return render_memory_observatory({})


def _render_flow_html(result):
    return render_memory_observatory(result)


def _render_state_diff_html(result):
    runtime_state = (result or {}).get("runtime_state") or {}
    runtime_trace = (result or {}).get("runtime_trace") or {}
    route_info = (result or {}).get("route_info") or {}
    logic = (result or {}).get("logic") or {}
    memory_data = (result or {}).get("memory_data") or {}
    state_diff = runtime_state.get("last_state_diff") or runtime_trace.get("state_diff") or {}
    memory_diff = runtime_state.get("last_memory_diff") or runtime_trace.get("memory_diff") or {}
    selected_plan = runtime_state.get("last_selected_plan") or runtime_trace.get("selected_plan") or {}
    open_loops = runtime_state.get("open_loops") or []
    candidates = runtime_state.get("last_candidates") or []
    planner_ticks = runtime_state.get("planner_tick_trace") or runtime_trace.get("planner_tick_trace") or []
    autonomous = runtime_state.get("last_autonomous_result") or {}
    recent_autonomous = runtime_state.get("recent_autonomous_traces") or []
    pending_proactive = runtime_state.get("pending_proactive_turn") or {}

    if not state_diff and not memory_diff and not selected_plan:
        return _empty_html("State Diff", "尚無本輪狀態變化。")

    psyche = state_diff.get("psyche") or {}
    focus = state_diff.get("focus") or {}
    goal = state_diff.get("goal") or {}
    loop_items = "".join(
        f'<span class="trace-chip">{escape(loop.get("label", str(loop)))}</span>'
        for loop in open_loops
    ) or '<span class="muted">none</span>'

    candidate_lines = "".join(
        f"<li>{escape(str(item.get('candidate_label')))} | p={_float_or_zero(item.get('bayes_probability', 0.0)):.2f} | {escape(str(item.get('surface_act')))}</li>"
        for item in candidates[:3]
    ) or "<li>none</li>"
    bdi_lines = [
        f"user_belief={selected_plan.get('user_belief') or '-'}",
        f"my_hidden_knowledge={selected_plan.get('my_hidden_knowledge') or '-'}",
        f"user_expectation={selected_plan.get('user_expectation') or '-'}",
    ]
    plan_trace_lines = [
        f"focus_anchor={selected_plan.get('focus_anchor') or '-'}",
        f"reply_obligation={selected_plan.get('reply_obligation') or '-'}",
        f"memory_relevance={selected_plan.get('memory_relevance') if selected_plan.get('memory_relevance') is not None else '-'}",
        f"memory_relevance_label={selected_plan.get('memory_relevance_label') or '-'}",
        f"memory_speakability={selected_plan.get('memory_speakability') or '-'}",
    ]
    post_check = selected_plan.get("post_check") or {}
    post_check_lines = [
        f"cover_focus={post_check.get('did_reply_cover_focus')}",
        f"follow_obligation={post_check.get('did_reply_follow_obligation')}",
        f"use_memory_explicitly={post_check.get('did_reply_use_memory_explicitly')}",
        f"memory_use_expected={post_check.get('memory_use_expected')}",
    ]

    profile_added = (memory_diff.get("profile_added") or {})
    memory_lines = [
        f"recent_turns_delta={memory_diff.get('recent_turns_delta', 0)}",
        f"short_term_delta={memory_diff.get('short_term_delta', 0)}",
        f"pending_consolidation_delta={memory_diff.get('pending_consolidation_delta', 0)}",
    ]
    if profile_added.get("name"):
        memory_lines.append(f"name={profile_added.get('name')}")
    for field in ("favorites", "likes", "dislikes"):
        values = profile_added.get(field) or []
        if values:
            memory_lines.append(f"{field}={', '.join(str(v) for v in values)}")

    planner_lines = "".join(
        f"<li>tick {tick.get('tick')}: {escape(', '.join(tick.get('issues') or ['ok']))}</li>"
        for tick in planner_ticks
    ) or "<li>none</li>"
    autonomous_goal = (autonomous.get("goal") or {}).get("label") if isinstance(autonomous.get("goal"), dict) else None
    proactive_line = pending_proactive.get("line") or "none"
    working_memory_items = memory_data.get("working_memory_items") or []
    memory_provenance = memory_data.get("memory_provenance") or {}
    working_memory_lines = "".join(
        f"<li>{escape(str(item.get('text', '')))} | s={_float_or_zero(item.get('score', item.get('salience', 0.0))):.2f} | id={escape(str(item.get('trace_id') or '-'))}</li>"
        for item in working_memory_items[:5]
    ) or "<li>none</li>"
    provenance_lines = [
        f"retrieved_count={memory_provenance.get('retrieved_candidate_count', 0)}",
        f"ranked_count={memory_provenance.get('candidate_count', 0)}",
        f"selected_count={len(memory_provenance.get('selected_working_memory_trace_ids') or [])}",
        f"passed_count={len(memory_provenance.get('passed_to_leftbrain_trace_ids') or [])}",
    ]
    autonomous_history_lines = "".join(
        f"<li>{escape(str(((item.get('goal') or {}).get('label')) or 'none'))} | writes={len(item.get('memory_writes') or [])}</li>"
        for item in recent_autonomous[-3:]
    ) or "<li>none</li>"

    return (
        '<div class="state-grid">'
        '<div class="state-card">'
        "<h4>Route / Surface</h4>"
        f'<ul class="state-list"><li>route={escape(str(route_info.get("route") or "-"))}</li>'
        f'<li>response_mode={escape(str(logic.get("response_mode") or "-"))}</li>'
        f'<li>surface_act={escape(str(logic.get("surface_act") or "-"))}</li></ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Psyche</h4>"
        f'<ul class="state-list"><li>mood: {psyche.get("mood_before", 0)} → {psyche.get("mood_after", 0)} (delta {psyche.get("mood_delta", 0)})</li>'
        f'<li>trust: {psyche.get("trust_before", 0)} → {psyche.get("trust_after", 0)} (delta {psyche.get("trust_delta", 0)})</li></ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Focus / Goal</h4>"
        f'<ul class="state-list"><li>focus: {escape(str(focus.get("before") or "-"))} → {escape(str(focus.get("after") or "-"))}</li>'
        f'<li>goal: {escape(str(goal.get("before") or "-"))} → {escape(str(goal.get("after") or "-"))}</li></ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Open Loops</h4>"
        f"{loop_items}"
        "</div>"
        '<div class="state-card">'
        "<h4>Selected Plan</h4>"
        f'<pre class="trace-pre">{escape(_preview_payload(selected_plan))}</pre>'
        "</div>"
        '<div class="state-card">'
        "<h4>BDI Scratchpad</h4>"
        f'<ul class="state-list">{"".join(f"<li>{escape(line)}</li>" for line in bdi_lines)}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Plan Rich Trace</h4>"
        f'<ul class="state-list">{"".join(f"<li>{escape(line)}</li>" for line in plan_trace_lines)}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Post Check</h4>"
        f'<ul class="state-list">{"".join(f"<li>{escape(line)}</li>" for line in post_check_lines)}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Candidate Plans</h4>"
        f'<ul class="state-list">{candidate_lines}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Planner Ticks</h4>"
        f'<ul class="state-list">{planner_lines}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Memory Diff</h4>"
        f'<ul class="state-list">{"".join(f"<li>{escape(line)}</li>" for line in memory_lines)}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Working Memory</h4>"
        f'<div class="muted">summary={escape(str(memory_data.get("working_memory_summary") or "-"))}</div>'
        f'<ul class="state-list">{working_memory_lines}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Memory Provenance</h4>"
        f'<ul class="state-list">{"".join(f"<li>{escape(line)}</li>" for line in provenance_lines)}</ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Autonomous Runtime</h4>"
        f'<ul class="state-list"><li>autonomous_tick_index={runtime_state.get("autonomous_tick_index", 0)}</li>'
        f'<li>last_goal={escape(str(autonomous_goal or "none"))}</li>'
        f'<li>pending_proactive={escape(str(proactive_line))}</li>'
        f'<li>planner_tick_count={runtime_state.get("planner_tick_count", 0)}</li>'
        f'<li>self_correction_applied={escape(str(runtime_state.get("self_correction_applied", False)))}</li></ul>'
        "</div>"
        '<div class="state-card">'
        "<h4>Autonomous History</h4>"
        f'<ul class="state-list">{autonomous_history_lines}</ul>'
        "</div>"
        "</div>"
    )


def _selected_plan_from_annotation_record(record):
    cognition_trace = (record or {}).get("cognition_trace") or {}
    runtime_trace = cognition_trace.get("runtime_trace") or {}
    return runtime_trace.get("selected_plan") or {}


def _derive_annotation_proxy_flags(record):
    selected_plan = _selected_plan_from_annotation_record(record)
    post_check = selected_plan.get("post_check") or {}
    memory_relevance = _float_or_zero(selected_plan.get("memory_relevance"))
    memory_anchor = str(selected_plan.get("memory_anchor") or "").strip()
    memory_speakability = str(selected_plan.get("memory_speakability") or "").strip()
    did_use_memory = bool(post_check.get("did_reply_use_memory_explicitly"))
    return {
        "focus_anchor_miss": not bool(post_check.get("did_reply_cover_focus")),
        "obligation_miss": not bool(post_check.get("did_reply_follow_obligation")),
        "memory_misuse": memory_relevance >= 0.45 and memory_speakability in {"explicit_ok", "latent_ok"} and not did_use_memory,
        "memory_available_but_silent": memory_relevance >= 0.45 and bool(memory_anchor) and not did_use_memory,
        "vibe_manual_review": True,
        "robotic_manual_review": True,
    }


def _annotation_context_markdown(record):
    if not record:
        return (
            "### Human Annotation\n"
            "- 尚無可標記輪次\n"
            f"- taxonomy=`{TAXONOMY_VERSION}`\n"
            f"- source=`{FAILURE_TAXONOMY_MD_PATH}`"
        )

    selected_plan = _selected_plan_from_annotation_record(record)
    post_check = selected_plan.get("post_check") or {}
    proxy_flags = _derive_annotation_proxy_flags(record)
    active_flags = [name for name, value in proxy_flags.items() if value]
    planner_debug = (record or {}).get("planner_debug") or {}
    logic = (record or {}).get("logic") or {}
    return "\n".join(
        [
            "### Human Annotation",
            f"- session=`{record.get('session_id')}` turn=`{record.get('turn_index')}`",
            f"- user=`{record.get('user_text', '')}`",
            f"- reply=`{record.get('assistant_reply', '')}`",
            f"- intent=`{planner_debug.get('intent') or logic.get('intent') or '-'}` scene=`{planner_debug.get('scene') or logic.get('scene') or '-'}`",
            f"- focus_anchor=`{selected_plan.get('focus_anchor') or '-'}`",
            f"- reply_obligation=`{selected_plan.get('reply_obligation') or '-'}`",
            f"- memory_relevance=`{selected_plan.get('memory_relevance')}` (`{selected_plan.get('memory_relevance_label') or '-'}`) / speakability=`{selected_plan.get('memory_speakability') or '-'}`",
            f"- post_check: focus={post_check.get('did_reply_cover_focus')} obligation={post_check.get('did_reply_follow_obligation')} memory={post_check.get('did_reply_use_memory_explicitly')}",
            f"- proxy_flags={', '.join(active_flags) if active_flags else 'none'}",
        ]
    )


def _load_recent_annotation_records(limit=20):
    limit = max(1, int(limit or 20))
    if not os.path.exists(HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH):
        return []

    rows = []
    with open(HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    valid_rows = [
        row
        for row in rows
        if is_valid_annotation_record(row, valid_failure_types=VALID_FAILURE_TYPE_CODES)
    ]
    return list(reversed(valid_rows[-limit:]))


def _compact_failure_list(values):
    values = [str(value).strip() for value in (values or []) if str(value).strip()]
    return ", ".join(values) if values else "none"


def _annotation_history_payload(limit=20):
    records = _load_recent_annotation_records(limit)
    verdict_counter = {}
    for record in records:
        verdict = str(record.get("verdict") or "unknown")
        verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1

    items = []
    for record in records:
        planner_debug = record.get("planner_debug") or {}
        logic = record.get("logic") or {}
        selected_plan = record.get("selected_plan") or {}
        proxy_flags = [name for name, enabled in (record.get("proxy_flags") or {}).items() if enabled]
        items.append(
            {
                "timestamp": record.get("timestamp"),
                "session_id": record.get("session_id"),
                "turn_index": record.get("turn_index"),
                "verdict": record.get("verdict"),
                "severity": record.get("severity"),
                "failure_types": record.get("failure_types") or [],
                "intent": planner_debug.get("intent") or logic.get("intent"),
                "scene": planner_debug.get("scene") or logic.get("scene"),
                "focus_anchor": selected_plan.get("focus_anchor"),
                "reply_obligation": selected_plan.get("reply_obligation"),
                "proxy_flags": proxy_flags,
                "notes": record.get("notes") or "",
                "user_text": record.get("user_text") or "",
                "assistant_reply": record.get("assistant_reply") or "",
            }
        )

    return {
        "summary": {
            "path": HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
            "window_size": limit,
            "loaded_count": len(records),
            "verdict_counter": verdict_counter,
        },
        "items": items,
    }


def _annotation_history_markdown(limit=20):
    payload = _annotation_history_payload(limit)
    summary = payload.get("summary") or {}
    items = payload.get("items") or []
    verdict_counter = summary.get("verdict_counter") or {}

    lines = [
        "### Recent Human Annotations",
        f"- path=`{summary.get('path')}`",
        f"- window=`latest {summary.get('window_size')}` / loaded=`{summary.get('loaded_count')}`",
        (
            "- verdict_counter="
            + (
                ", ".join(f"{key}:{value}" for key, value in sorted(verdict_counter.items()))
                if verdict_counter
                else "none"
            )
        ),
    ]
    if not items:
        lines.append("- 尚無人工標記。")
        return "\n".join(lines)

    for item in items[: min(len(items), int(limit or 20))]:
        lines.extend(
            [
                "",
                (
                    f"- [{item.get('timestamp')}] "
                    f"session=`{item.get('session_id')}` turn=`{item.get('turn_index')}` "
                    f"verdict=`{item.get('verdict')}` severity=`{item.get('severity')}`"
                ),
                f"  - failure=`{_compact_failure_list(item.get('failure_types'))}`",
                f"  - intent=`{item.get('intent') or '-'}` scene=`{item.get('scene') or '-'}`",
                f"  - focus_anchor=`{item.get('focus_anchor') or '-'}` obligation=`{item.get('reply_obligation') or '-'}`",
                f"  - proxy_flags=`{_compact_failure_list(item.get('proxy_flags'))}`",
                f"  - user=`{item.get('user_text') or ''}`",
                f"  - reply=`{item.get('assistant_reply') or ''}`",
            ]
        )
        if item.get("notes"):
            lines.append(f"  - notes=`{item.get('notes')}`")
    return "\n".join(lines)


def refresh_annotation_history(limit):
    return _annotation_history_markdown(limit), _annotation_history_payload(limit)


def _validate_annotation_fields(latest_turn_record, verdict, severity, failure_types, history_limit):
    latest_turn_record = latest_turn_record or {}
    failure_types = normalize_failure_types(failure_types or [])
    notes_placeholder = None
    verdict = str(verdict or "").strip()
    severity = str(severity or "").strip()
    history_limit = max(1, int(history_limit or 20))
    source_error = invalid_turn_source_reason(latest_turn_record)
    if source_error:
        history_md, history_json = refresh_annotation_history(history_limit)
        return None, f"尚無有效可標記輪次：{source_error}。請先完成一輪真實對話或載入有效 draft。", history_md, history_json
    if verdict not in {item[1] for item in VERDICT_CHOICES}:
        history_md, history_json = refresh_annotation_history(history_limit)
        return None, "判定欄位無效。", history_md, history_json
    if severity not in {item[1] for item in SEVERITY_CHOICES}:
        history_md, history_json = refresh_annotation_history(history_limit)
        return None, "嚴重度欄位無效。", history_md, history_json
    unknown_failure_types = [code for code in failure_types if code not in VALID_FAILURE_TYPE_CODES]
    if unknown_failure_types:
        history_md, history_json = refresh_annotation_history(history_limit)
        return None, f"未知 failure type：{','.join(unknown_failure_types)}。", history_md, history_json
    if verdict in {"mixed", "fail"} and not failure_types:
        history_md, history_json = refresh_annotation_history(history_limit)
        return None, "`mixed/fail` 至少要選一個 failure type。", history_md, history_json
    return {
        "latest_turn_record": latest_turn_record,
        "verdict": verdict,
        "severity": severity,
        "failure_types": failure_types,
        "history_limit": history_limit,
        "notes_placeholder": notes_placeholder,
    }, None, None, None


def _build_annotation_record(source_record, verdict, severity, failure_types, notes):
    source_record = source_record or {}
    selected_plan = _selected_plan_from_annotation_record(source_record)
    post_check = selected_plan.get("post_check") or {}
    proxy_flags = _derive_annotation_proxy_flags(source_record)
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "taxonomy_version": TAXONOMY_VERSION,
        "session_id": source_record.get("session_id"),
        "turn_index": source_record.get("turn_index"),
        "input_mode": source_record.get("input_mode"),
        "verdict": verdict,
        "severity": severity,
        "failure_types": failure_types,
        "notes": notes,
        "user_text": source_record.get("user_text"),
        "assistant_reply": source_record.get("assistant_reply"),
        "memory_snapshot": source_record.get("memory_snapshot") or {},
        "planner_debug": source_record.get("planner_debug") or {},
        "selected_plan": selected_plan,
        "post_check": post_check,
        "proxy_flags": proxy_flags,
        "logic": source_record.get("logic") or {},
        "cognition_trace": source_record.get("cognition_trace") or {},
    }


def _annotation_turn_key(record):
    return (
        str(record.get("session_id") or "").strip(),
        str(record.get("turn_index") or "").strip(),
    )


def _load_existing_annotation_keys():
    return {
        _annotation_turn_key(record)
        for record in _load_recent_annotation_records(limit=100000)
    }


def _append_annotation_record(annotation_record):
    invalid_reason = invalid_annotation_reason(annotation_record, valid_failure_types=VALID_FAILURE_TYPE_CODES)
    if invalid_reason:
        raise ValueError(f"invalid human feedback annotation: {invalid_reason}")
    with open(HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(annotation_record, ensure_ascii=False) + "\n")


def _refresh_annotation_downstream_reports():
    subprocess.run([sys.executable, ANNOTATION_DRAFT_SCRIPT], cwd=BASE_DIR, check=True, timeout=120)
    subprocess.run([sys.executable, ANNOTATION_REPORT_SCRIPT], cwd=BASE_DIR, check=True, timeout=120)
    subprocess.run([sys.executable, REGRESSION_DATASET_SCRIPT], cwd=BASE_DIR, check=True, timeout=120)


def _run_regression_eval_downstream_reports(selected_meta_path=None):
    """執行 regression replay 及其後的 diff 報表。回傳 (success, status)"""
    # 1. 執行 replay eval
    subprocess.run([sys.executable, REGRESSION_EVAL_SCRIPT], cwd=BASE_DIR, check=True, timeout=600)

    # 2. 解析 baseline
    baseline_json, resolve_status = _resolve_auto_diff_baseline_json(selected_meta_path)

    if baseline_json and resolve_status in ("success", "fallback_latest"):
        try:
            subprocess.run([sys.executable, REGRESSION_DIFF_SCRIPT, "--before", baseline_json], cwd=BASE_DIR, check=True, timeout=600)
            return True, resolve_status
        except Exception:
            return False, "subprocess_failed"

    return False, resolve_status


def save_human_annotation(latest_turn_record, verdict, severity, failure_types, notes, history_limit):
    payload, error, history_md, history_json = _validate_annotation_fields(
        latest_turn_record, verdict, severity, failure_types, history_limit
    )
    if error:
        return error, gr.update(), gr.update(), history_md, history_json

    latest_turn_record = payload["latest_turn_record"]
    failure_types = payload["failure_types"]
    verdict = payload["verdict"]
    severity = payload["severity"]
    history_limit = payload["history_limit"]
    notes = str(notes or "").strip()
    annotation_record = _build_annotation_record(latest_turn_record, verdict, severity, failure_types, notes)
    try:
        _append_annotation_record(annotation_record)
        _refresh_annotation_downstream_reports()
    except Exception as exc:
        history_md, history_json = refresh_annotation_history(history_limit)
        return f"標記寫入失敗：{exc}", gr.update(), gr.update(), history_md, history_json

    summary = (
        f"已寫入人工標記：session={annotation_record['session_id']} "
        f"turn={annotation_record['turn_index']} "
        f"verdict={verdict} severity={severity} "
        f"failure={','.join(failure_types) if failure_types else 'none'} "
        f"path={HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH}；已更新 annotation/regression dataset 報表"
    )
    history_md, history_json = refresh_annotation_history(history_limit)
    return summary, gr.update(value=""), gr.update(value=[]), history_md, history_json


def save_human_annotation_with_replay(
    latest_turn_record,
    verdict,
    severity,
    failure_types,
    notes,
    history_limit,
    current_snap_picker_val,
):
    status_msg, notes_update, failures_update, history_md, history_json = save_human_annotation(
        latest_turn_record,
        verdict,
        severity,
        failure_types,
        notes,
        history_limit,
    )
    if not str(status_msg or "").startswith("已寫入人工標記"):
        bundle = _assemble_regression_panel_bundle(
            current_snap_picker_val,
            diff_ran=False,
            diff_status="annotation_save_failed",
            run_replay=False,
            include_diff_panel=True,
        )
        return (
            status_msg,
            notes_update,
            failures_update,
            history_md,
            history_json,
            bundle["eval_md"],
            bundle["eval_json"],
            bundle["diff_md"],
            bundle["diff_json"],
            bundle["fresh_md"],
            bundle["picker_update"],
        )

    try:
        diff_ran, diff_status = _run_regression_eval_downstream_reports(current_snap_picker_val)
        reason_text = _replay_diff_status_text(diff_status)
        replay_suffix = "；已執行 Regression Replay"
        replay_suffix += " + Diff" if diff_ran else f"；Diff 跳過：{reason_text}"
        bundle = _assemble_regression_panel_bundle(
            current_snap_picker_val,
            diff_ran=diff_ran,
            diff_status=diff_status,
            run_replay=True,
            has_rows=True,
            accepted_count=1,
            include_diff_panel=True,
        )
        status_msg = str(status_msg) + replay_suffix
    except Exception as exc:
        bundle = _assemble_regression_panel_bundle(
            current_snap_picker_val,
            diff_ran=False,
            diff_status="subprocess_failed",
            run_replay=False,
            include_diff_panel=True,
        )
        status_msg = f"{status_msg}；Regression Replay 失敗：{exc}"

    return (
        status_msg,
        notes_update,
        failures_update,
        history_md,
        history_json,
        bundle["eval_md"],
        bundle["eval_json"],
        bundle["diff_md"],
        bundle["diff_json"],
        bundle["fresh_md"],
        bundle["picker_update"],
    )


def refresh_annotation_draft_queue():
    return gr.update(choices=_annotation_draft_choices()), _annotation_draft_preview_markdown(None)


def preview_annotation_draft(draft_id):
    return _annotation_draft_preview_markdown(draft_id)


def load_annotation_draft(draft_id):
    row = _find_annotation_draft(draft_id)
    if not row:
        return (
            {},
            _annotation_context_markdown({}),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "draft not found",
            _annotation_draft_preview_markdown(draft_id),
        )

    source_record = row.get("source_record") or {}
    source_error = invalid_turn_source_reason(source_record)
    if source_error:
        return (
            {},
            _annotation_context_markdown({}),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            f"draft 無法載入：{source_error}",
            _annotation_draft_preview_markdown(draft_id),
        )
    return (
        source_record,
        _annotation_context_markdown(source_record),
        gr.update(value=row.get("suggested_verdict") or "mixed"),
        gr.update(value=row.get("suggested_severity") or "medium"),
        gr.update(value=row.get("suggested_failure_types") or []),
        gr.update(value=row.get("suggested_notes") or ""),
        (
            f"已載入 draft：draft_id={row.get('draft_id')} "
            f"session={source_record.get('session_id')} turn={source_record.get('turn_index')}"
        ),
        _annotation_draft_preview_markdown(draft_id),
    )


def refresh_annotation_batch_workbench(bucket_code, severity, reason_code, take_count):
    available_buckets = _annotation_batch_bucket_choices()
    available_severities = _annotation_batch_severity_choices()
    available_reasons = _annotation_batch_reason_choices()

    bucket_code = bucket_code if bucket_code in {v for _, v in available_buckets} else "__ALL__"
    severity = severity if severity in {v for _, v in available_severities} else "ALL"
    reason_code = reason_code if reason_code in {v for _, v in available_reasons} else "ALL"

    return (
        gr.update(choices=available_buckets, value=bucket_code),
        gr.update(choices=available_severities, value=severity),
        gr.update(choices=available_reasons, value=reason_code),
        _annotation_batch_review_markdown(bucket_code, severity, reason_code, take_count),
    )


def batch_accept_annotation_drafts(bucket_code, severity, reason_code, take_count, history_limit, current_snap_picker_val, run_replay=False):
    take_count = max(1, int(take_count or 1))
    history_limit = max(1, int(history_limit or 20))
    rows = _annotation_draft_rows(bucket_code, severity, reason_code, limit=take_count)

    # 內部輔助函數，確保回傳值數量正確 (15個)
    def _make_return_payload(msg, hist_md, hist_json, dr_choices, dr_prev, b_choices, b_sev, b_reas, b_prev,
                             reg_eval_md=None, reg_eval_json=None, reg_diff_md=None, reg_diff_json=None,
                             reg_fresh_md=None, reg_snap_picker=None):
        return (
            msg, hist_md, hist_json, dr_choices, dr_prev, b_choices, b_sev, b_reas, b_prev,
            reg_eval_md if reg_eval_md is not None else gr.update(),
            reg_eval_json if reg_eval_json is not None else gr.update(),
            reg_diff_md if reg_diff_md is not None else gr.update(),
            reg_diff_json if reg_diff_json is not None else gr.update(),
            reg_fresh_md if reg_fresh_md is not None else gr.update(),
            reg_snap_picker if reg_snap_picker is not None else gr.update()
        )

    if not rows:
        history_md, history_json = refresh_annotation_history(history_limit)

        diff_status = None
        if run_replay:
            _, diff_status = _resolve_auto_diff_baseline_json(current_snap_picker_val)

        bundle = _assemble_regression_panel_bundle(
            current_snap_picker_val,
            diff_ran=False,
            diff_status=diff_status,
            run_replay=run_replay,
            has_rows=False,
            accepted_count=0,
            include_diff_panel=run_replay,
        )

        return _make_return_payload(
            "目前沒有符合過濾條件可批次採納的 draft。",
            history_md, history_json,
            gr.update(choices=_annotation_draft_choices()),
            _annotation_draft_preview_markdown(None),
            gr.update(choices=_annotation_batch_bucket_choices(), value=bucket_code),
            gr.update(choices=_annotation_batch_severity_choices(), value=severity),
            gr.update(choices=_annotation_batch_reason_choices(), value=reason_code),
            _annotation_batch_review_markdown(bucket_code, severity, reason_code, take_count),
            reg_eval_md=bundle["eval_md"],
            reg_eval_json=bundle["eval_json"],
            reg_diff_md=bundle["diff_md"],
            reg_diff_json=bundle["diff_json"],
            reg_fresh_md=bundle["fresh_md"],
            reg_snap_picker=bundle["picker_update"]
        )

    existing_keys = _load_existing_annotation_keys()
    accepted = []
    skipped = []
    invalid = []
    for row in rows:
        source_record = row.get("source_record") or {}
        source_error = invalid_turn_source_reason(source_record)
        if source_error:
            invalid.append(f"{row.get('draft_id')}:{source_error}")
            continue
        turn_key = _annotation_turn_key(source_record)
        if turn_key in existing_keys:
            skipped.append(row.get("draft_id"))
            continue
        suggested_failure_types = normalize_failure_types(row.get("suggested_failure_types") or [])
        if (row.get("suggested_verdict") or "mixed") in {"mixed", "fail"} and not suggested_failure_types:
            invalid.append(f"{row.get('draft_id')}:missing suggested_failure_types")
            continue
        annotation_record = _build_annotation_record(
            source_record,
            row.get("suggested_verdict") or "mixed",
            row.get("suggested_severity") or "medium",
            suggested_failure_types,
            str(row.get("suggested_notes") or "").strip(),
        )
        try:
            _append_annotation_record(annotation_record)
        except Exception as exc:
            invalid.append(f"{row.get('draft_id')}:{exc}")
            continue
        existing_keys.add(turn_key)
        accepted.append(row.get("draft_id"))

    # 執行基本的下游更新 (draft queue, report, regression dataset)
    _refresh_annotation_downstream_reports()

    # 顯式 Replay 路徑
    replay_msg = ""
    diff_msg = ""
    diff_ran = False
    diff_status = "no_new_accepts" # 預設狀態

    if run_replay:
        if accepted:
            diff_ran, diff_status = _run_regression_eval_downstream_reports(current_snap_picker_val)
            replay_msg = " + 執行了 Regression Replay"

            reason_text = _replay_diff_status_text(diff_status)
            diff_msg = " (+ Regression Diff)" if diff_ran else f" (Diff 跳過：{reason_text})"
        else:
            # 有 rows 但全部被 skip (此處 rows 必非空，因為已通過 if not rows 攔截)
            diff_ran = False
            diff_status = "all_skipped"
            diff_msg = " (Diff 跳過：重複草稿已被略過)"

    history_md, history_json = refresh_annotation_history(history_limit)

    new_buckets = _annotation_batch_bucket_choices()
    new_severities = _annotation_batch_severity_choices()
    new_reasons = _annotation_batch_reason_choices()

    bucket_val = bucket_code if bucket_code in {v for _, v in new_buckets} else "__ALL__"
    severity_val = severity if severity in {v for _, v in new_severities} else "ALL"
    reason_val = reason_code if reason_code in {v for _, v in new_reasons} else "ALL"

    summary = (
        f"已批次採納 {len(accepted)} 筆 draft"
        + (f"；跳過已存在 {len(skipped)} 筆" if skipped else "")
        + (f"；無效略過 {len(invalid)} 筆" if invalid else "")
        + replay_msg + diff_msg
    )

    bundle = _assemble_regression_panel_bundle(
        current_snap_picker_val,
        diff_ran=diff_ran,
        diff_status=diff_status,
        run_replay=run_replay,
        has_rows=True,
        accepted_count=len(accepted),
        include_diff_panel=run_replay,
    )

    return _make_return_payload(
        summary,
        history_md,
        history_json,
        gr.update(choices=_annotation_draft_choices(), value=None),
        _annotation_draft_preview_markdown(None),
        gr.update(choices=new_buckets, value=bucket_val),
        gr.update(choices=new_severities, value=severity_val),
        gr.update(choices=new_reasons, value=reason_val),
        _annotation_batch_review_markdown(bucket_val, severity_val, reason_val, take_count),
        reg_eval_md=bundle["eval_md"],
        reg_eval_json=bundle["eval_json"],
        reg_diff_md=bundle["diff_md"],
        reg_diff_json=bundle["diff_json"],
        reg_fresh_md=bundle["fresh_md"],
        reg_snap_picker=bundle["picker_update"]
    )



def _iter_reply_chunks(text):
    text = (text or "").strip()
    if not text:
        return

    if re.search(r"[A-Za-z]", text) and not re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", text):
        words = text.split()
        assembled = []
        for index, word in enumerate(words, start=1):
            assembled.append(word)
            if index % 4 == 0 or index == len(words):
                yield " ".join(assembled)
        return

    tokens = re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]{1,3}|[A-Za-z0-9']+|[^\w\s]", text, flags=re.UNICODE)
    if not tokens:
        yield text
        return

    built = ""
    last_emitted_length = 0
    for index, token in enumerate(tokens):
        if re.fullmatch(r"[A-Za-z0-9']+", token):
            built = f"{built} {token}".strip()
        else:
            built += token
        punctuation_boundary = bool(re.fullmatch(r"[、。！？!?]", token))
        final_token = index == len(tokens) - 1
        if punctuation_boundary or final_token or len(built) - last_emitted_length >= 12:
            yield built
            last_emitted_length = len(built)


def begin_human_submission(value):
    """Queue-free admission marker used by text and audio UI events."""
    if value in (None, ""):
        return 0.0
    return RUNTIME.begin_human_turn()


def _run_turn(
    user_text,
    auto_tts,
    input_mode="text",
    acoustic_summary=None,
    frontend_enqueue_started=0.0,
    handler_started=0.0,
):
    user_text = (user_text or "").strip()
    if not user_text:
        return None

    RUNTIME.mark_activity()
    request_started = time.perf_counter()
    handler_started = float(handler_started or request_started)
    frontend_enqueue_started = float(frontend_enqueue_started or handler_started)
    brain_was_ready = getattr(RUNTIME, "_brain", None) is not None
    runtime_lock_wait_started = time.perf_counter()
    with RUNTIME._lock:
        runtime_lock_acquired = time.perf_counter()
        brain = RUNTIME.get_brain()
        brain_ready_at = time.perf_counter()
        turn_debug = brain.run_turn_debug
        if "input_context" in inspect.signature(turn_debug).parameters:
            turn = turn_debug(
                user_text,
                input_context={
                    "input_mode": str(input_mode or "text"),
                    "acoustic_summary": acoustic_summary,
                },
            )
        else:
            # Compatibility for narrow test doubles and older runtime adapters.
            turn = turn_debug(user_text)
    request_finished = time.perf_counter()
    latency = dict(
        (turn.get("runtime_trace") or {}).get("runtime_latency_m19")
        or (turn.get("runtime_trace") or {}).get("runtime_latency_m18")
        or (turn.get("runtime_trace") or {}).get("runtime_latency_m17")
        or {}
    )
    latency.update(
        {
            "schema": "uruha_runtime_latency_m19",
            "frontend_queue_wait_seconds": round(
                max(0.0, handler_started - frontend_enqueue_started), 4
            ),
            "runtime_lock_wait_seconds": round(
                runtime_lock_acquired - runtime_lock_wait_started, 4
            ),
            "cold_brain_initialization_seconds": (
                0.0
                if brain_was_ready
                else float((getattr(RUNTIME, "_brain_load_trace", {}) or {}).get("elapsed_seconds") or 0.0)
            ),
            "request_wait_for_brain_seconds": round(brain_ready_at - request_started, 4),
            "brain_work_seconds": round(request_finished - brain_ready_at, 4),
            "surface_stream_seconds": 0.0,
            "handler_total_seconds": round(request_finished - handler_started, 4),
            "end_to_end_after_enqueue_seconds": round(
                request_finished - frontend_enqueue_started, 4
            ),
            "user_wait_seconds": round(request_finished - frontend_enqueue_started, 4),
            "delivery_complete": False,
            "prewarm_status": str((getattr(RUNTIME, "_brain_load_trace", {}) or {}).get("status") or "unknown"),
            "contains_raw_dialogue": False,
        }
    )
    latency["target_met"] = latency["user_wait_seconds"] <= float(
        latency.get("target_seconds") or 20.0
    )
    turn.setdefault("logic", {})["runtime_latency_m17"] = dict(latency)
    turn.setdefault("logic", {})["runtime_latency_m18"] = dict(latency)
    turn.setdefault("logic", {})["runtime_latency_m19"] = dict(latency)
    runtime_trace = turn.setdefault("runtime_trace", {})
    runtime_trace["runtime_latency_m17"] = dict(latency)
    runtime_trace["runtime_latency_m18"] = dict(latency)
    runtime_trace["runtime_latency_m19"] = dict(latency)
    blackboard = list(runtime_trace.get("blackboard") or [])
    scheduler_snapshot = getattr(RUNTIME, "scheduler_trace", None)
    scheduler_trace = (
        scheduler_snapshot()
        if callable(scheduler_snapshot)
        else {
            "schema": "uruha_human_priority_scheduler_m19",
            "human_waiters": 0,
            "last_decision": "legacy_runtime_adapter",
            "contains_raw_dialogue": False,
        }
    )
    scheduler_trace.update(
        {
            "admission": "human_first",
            "frontend_queue_isolated": True,
            "poll_is_nonblocking": True,
        }
    )
    blackboard.insert(
        0,
        {
            "stage": "observe",
            "label": "human_priority_scheduler_m19",
            "payload": scheduler_trace,
            "salience": 0.98,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    )
    replaced = False
    for row in blackboard:
        if row.get("label") in {"runtime_latency_m17", "runtime_latency_m18", "runtime_latency_m19"}:
            row["label"] = "runtime_latency_m19"
            row["payload"] = dict(latency)
            replaced = True
    if not replaced:
        blackboard.append(
            {
                "stage": "observe",
                "label": "runtime_latency_m19",
                "payload": dict(latency),
                "salience": 0.94,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
    runtime_trace["blackboard"] = blackboard
    # The brain trace starts after ingestion, so carry the actual Web input into
    # the same payload used by the runtime node graph.
    turn["user_text"] = user_text

    audio_path = None
    if auto_tts:
        mouth = RUNTIME.get_mouth()
        tmp = tempfile.NamedTemporaryFile(prefix="uruha_web_reply_", suffix=".wav", delete=False)
        tmp.close()
        audio_path = mouth.synthesize_to_file(turn["reply"], output_file=tmp.name)

    logic = turn["logic"]
    debug = {
        "intent": logic.get("intent"),
        "scene": logic.get("scene"),
        "response_mode": logic.get("response_mode"),
        "surface_act": logic.get("surface_act"),
        "planner_tick_count": logic.get("planner_tick_count"),
        "self_correction_applied": logic.get("self_correction_applied"),
        "payload_level": logic.get("payload_level"),
        "core_message_jp": logic.get("core_message_jp"),
        "grounding": logic.get("grounding"),
        "routing_path": logic.get("routing_path"),
        "internal_monologue": logic.get("internal_monologue"),
    }
    return {
        "user_text": user_text,
        "reply": turn["reply"],
        "audio_path": audio_path,
        "debug": debug,
        "logic": logic,
        "memory_snapshot": _extract_memory_payload(turn),
        "cognition_trace": _extract_trace_payload(turn),
        "flow_html": _render_flow_html(turn),
        "state_html": _render_state_diff_html(turn),
    }


def _finalize_surface_delivery(
    result,
    frontend_enqueue_started,
    handler_started,
    surface_started,
    stream_chunk_count=0,
    lightweight_payload_update_count=0,
    full_payload_update_count=1,
):
    """Attach actual browser-delivery timing and redraw the final node graph."""
    finished_at = time.perf_counter()
    handler_started = float(handler_started or surface_started)
    frontend_enqueue_started = float(frontend_enqueue_started or handler_started)
    runtime_trace = (result.get("cognition_trace") or {}).get("runtime_trace") or {}
    latency = dict(
        runtime_trace.get("runtime_latency_m19")
        or runtime_trace.get("runtime_latency_m18")
        or {}
    )
    latency.update(
        {
            "schema": "uruha_runtime_latency_m19",
            "surface_stream_seconds": round(max(0.0, finished_at - surface_started), 4),
            "handler_total_seconds": round(max(0.0, finished_at - handler_started), 4),
            "end_to_end_after_enqueue_seconds": round(
                max(0.0, finished_at - frontend_enqueue_started), 4
            ),
            "user_wait_seconds": round(
                max(0.0, finished_at - frontend_enqueue_started), 4
            ),
            "delivery_complete": True,
            "contains_raw_dialogue": False,
        }
    )
    latency["target_met"] = latency["user_wait_seconds"] <= float(
        latency.get("target_seconds") or 20.0
    )
    surface_delivery = {
        "schema": "uruha_lightweight_surface_delivery_m20",
        "stream_chunk_count": int(stream_chunk_count),
        "lightweight_payload_update_count": int(lightweight_payload_update_count),
        "full_payload_update_count": int(full_payload_update_count),
        "full_cognitive_payload_during_partial_stream": False,
        "final_graph_commit_once": int(full_payload_update_count) == 1,
        "surface_stream_seconds": latency["surface_stream_seconds"],
        "contains_raw_dialogue": False,
    }
    result.setdefault("logic", {})["runtime_latency_m19"] = dict(latency)
    result.setdefault("logic", {})["surface_delivery_m20"] = dict(surface_delivery)
    runtime_trace["runtime_latency_m19"] = dict(latency)
    runtime_trace["runtime_latency_m18"] = dict(latency)
    runtime_trace["surface_delivery_m20"] = dict(surface_delivery)
    blackboard = runtime_trace.get("blackboard") or []
    for row in runtime_trace.get("blackboard") or []:
        if row.get("label") == "runtime_latency_m19":
            row["payload"] = dict(latency)
    blackboard.insert(
        max(0, len(blackboard) - 1),
        {
            "stage": "surface",
            "label": "surface_delivery_m20",
            "payload": dict(surface_delivery),
            "salience": 0.98,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    )
    observatory_result = {
        "user_text": result.get("user_text") or "",
        "reply": result.get("reply") or "",
        "logic": result.get("logic") or {},
        "memory_data": result.get("memory_snapshot") or {},
        "runtime_trace": runtime_trace,
        "runtime_state": (result.get("cognition_trace") or {}).get("runtime_state") or {},
    }
    result["flow_html"] = _render_flow_html(observatory_result)
    return latency


def _append_conversation_log(input_mode, result):
    session_id, turn_index = RUNTIME.next_turn_meta()
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "turn_index": turn_index,
        "input_mode": input_mode,
        "user_text": result["user_text"],
        "assistant_reply": result["reply"],
        "planner_debug": result["debug"],
        "logic": result.get("logic", {}),
        "cognition_trace": result.get("cognition_trace", {}),
        "memory_snapshot": result.get("memory_snapshot", {}),
    }
    with open(WEB_LOG_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    with open(WEB_LOG_TXT, "a", encoding="utf-8") as f:
        f.write(
            f"[{record['timestamp']}] session={session_id} turn={turn_index} mode={input_mode}\n"
            f"You: {record['user_text']}\n"
            f"Uruha: {record['assistant_reply']}\n"
            f"Intent: {record['planner_debug'].get('intent')} | "
            f"Scene: {record['planner_debug'].get('scene')} | "
            f"SurfaceAct: {record['planner_debug'].get('surface_act')}\n\n"
        )
    return record


def poll_proactive_turn(history, auto_tts):
    human_pending = getattr(RUNTIME, "human_turn_pending", lambda: False)
    if RUNTIME._brain is None or human_pending():
        return (gr.skip(),) * 7

    if not RUNTIME._lock.acquire(blocking=False):
        record_decision = getattr(RUNTIME, "_record_background_decision", None)
        if callable(record_decision):
            record_decision("skipped", "proactive_poll_brain_busy")
        return (gr.skip(),) * 7
    try:
        if human_pending():
            return (gr.skip(),) * 7
        brain = RUNTIME._brain
        proactive = brain.consume_pending_proactive_turn()
        memory_snapshot = brain.memory.get_runtime_snapshot() if proactive else {}
        autonomous_trace = brain.runtime.last_autonomous_result if proactive else {}
    finally:
        RUNTIME._lock.release()
    if not proactive:
        return (gr.skip(),) * 7

    reply = str(proactive.get("line") or "").strip()
    if not reply:
        return (gr.skip(),) * 7

    audio_path = None
    if auto_tts:
        tmp = tempfile.NamedTemporaryFile(prefix="uruha_web_proactive_", suffix=".wav", delete=False)
        tmp.close()
        try:
            audio_path = RUNTIME.get_mouth().synthesize_to_file(reply, output_file=tmp.name)
        except Exception as exc:
            _cleanup_input_audio(tmp.name)
            print(Fore.YELLOW + f"⚠️ [Web] Proactive TTS failed: {exc}")

    logic = {
        "intent": proactive.get("intent") or "chat",
        "scene": "casual",
        "response_mode": "proactive",
        "surface_act": "proactive_turn",
        "autonomous_proactive": proactive,
    }
    debug = {
        "intent": logic["intent"],
        "scene": logic["scene"],
        "response_mode": logic["response_mode"],
        "surface_act": logic["surface_act"],
        "proactive_kind": proactive.get("kind"),
        "delivery_key": proactive.get("delivery_key"),
    }
    result = {
        "user_text": "[沉默後的自主延續]",
        "reply": reply,
        "debug": debug,
        "logic": logic,
        "cognition_trace": {
            "autonomous": autonomous_trace,
            "delivery": proactive,
        },
        "memory_snapshot": memory_snapshot,
    }
    log_record = _append_conversation_log("autonomous_proactive", result)
    updated_history = _append_history(history, "assistant", reply)
    return (
        updated_history,
        updated_history,
        audio_path,
        _status_markdown(),
        log_record,
        _annotation_context_markdown(log_record),
        "自主延續已可標記。",
    )


def _cleanup_input_audio(audio_path):
    if not audio_path:
        return
    try:
        path = Path(audio_path)
        if path.exists() and path.is_file():
            path.unlink()
    except Exception as exc:
        print(Fore.YELLOW + f"⚠️ [Web] Failed to remove input audio: {audio_path} ({exc})")


def _submit_text_impl(message, history, auto_tts, frontend_enqueue_started):
    handler_started = time.perf_counter()
    user_text = (message or "").strip()
    if not user_text:
        yield history, history, "", None, gr.update(value={}), gr.update(value={}), _empty_flow_html("尚無本輪知識流。"), _empty_html("State Diff", "尚無本輪狀態變化。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip()
        return

    pending_history = _append_history(history, "user", user_text)
    pending_history = _append_history(pending_history, "assistant", "...")
    yield pending_history, pending_history, "", None, gr.update(value={}), gr.update(value={}), _empty_flow_html("思考中。"), _empty_html("State Diff", "等待本輪狀態完成。"), gr.update(value={}), _thinking_status("thinking"), gr.skip(), gr.skip(), gr.skip()

    result = _run_turn(
        user_text,
        auto_tts,
        input_mode="text",
        frontend_enqueue_started=frontend_enqueue_started,
        handler_started=handler_started,
    )
    if result is None:
        yield history, history, "", None, gr.update(value={}), gr.update(value={}), _empty_flow_html("本輪未產生結果。"), _empty_html("State Diff", "本輪未產生結果。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip()
        return
    streamed_history = list(pending_history)
    streamed_history[-1] = {"role": "assistant", "content": ""}
    debug_payload = dict(result["debug"])
    surface_started = time.perf_counter()
    lightweight_updates = 1
    yield streamed_history, streamed_history, "", None, gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), _thinking_status("streaming_reply"), gr.skip(), gr.skip(), gr.skip()

    partials = list(_iter_reply_chunks(result["reply"]))
    for partial in partials:
        streamed_history[-1] = {"role": "assistant", "content": partial}
        lightweight_updates += 1
        yield streamed_history, streamed_history, "", None, gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), _thinking_status("streaming_reply"), gr.skip(), gr.skip(), gr.skip()
        time.sleep(0.01)

    _finalize_surface_delivery(
        result,
        frontend_enqueue_started,
        handler_started,
        surface_started,
        stream_chunk_count=len(partials),
        lightweight_payload_update_count=lightweight_updates,
        full_payload_update_count=1,
    )
    log_record = _append_conversation_log("text", result)
    annotation_context = _annotation_context_markdown(log_record)
    annotation_status = "新輪次已可標記。"
    debug_payload["turn_index"] = log_record["turn_index"]
    debug_payload["session_id"] = log_record["session_id"]
    client_cognition = _client_cognition_payload_m24(result["cognition_trace"])
    client_memory = _client_memory_payload_m24(result["memory_snapshot"])
    client_record = _client_turn_record_m24(
        log_record,
        client_cognition,
        client_memory,
    )
    streamed_history[-1] = {"role": "assistant", "content": result["reply"]}
    yield streamed_history, streamed_history, "", result["audio_path"], debug_payload, client_cognition, result["flow_html"], result["state_html"], client_memory, _status_markdown(), client_record, annotation_context, annotation_status


def submit_text(message, history, auto_tts, frontend_enqueue_started=0.0):
    frontend_enqueue_started = float(frontend_enqueue_started or 0.0)
    if frontend_enqueue_started <= 0.0:
        frontend_enqueue_started = RUNTIME.begin_human_turn()
    try:
        yield from _submit_text_impl(
            message,
            history,
            auto_tts,
            frontend_enqueue_started,
        )
    finally:
        RUNTIME.finish_human_turn()


def _submit_audio_impl(audio_path, history, auto_tts, frontend_enqueue_started):
    handler_started = time.perf_counter()
    if not audio_path:
        yield history, history, "", None, gr.update(value={}), gr.update(value={}), _empty_flow_html("尚無本輪知識流。"), _empty_html("State Diff", "尚無本輪狀態變化。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
        return
    text = RUNTIME.get_ears().transcribe_audio_file(audio_path)
    if not text:
        _cleanup_input_audio(audio_path)
        yield history, history, text, None, gr.update(value={}), gr.update(value={}), _empty_flow_html("沒有辨識到語音內容。"), _empty_html("State Diff", "沒有辨識到語音內容。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip(), gr.update(value=None)
        return

    pending_history = _append_history(history, "user", text)
    pending_history = _append_history(pending_history, "assistant", "...")
    yield pending_history, pending_history, text, None, gr.update(value={}), gr.update(value={}), _empty_flow_html("思考中。"), _empty_html("State Diff", "等待本輪狀態完成。"), gr.update(value={}), _thinking_status("thinking"), gr.skip(), gr.skip(), gr.skip(), gr.skip()

    # The current audio frontend exposes a transcript but no validated acoustic
    # feature extractor.  Pass that boundary explicitly so the cognitive trace
    # marks prosody/speed/pause evidence unavailable instead of inventing tone.
    result = _run_turn(
        text,
        auto_tts,
        input_mode="audio",
        acoustic_summary=None,
        frontend_enqueue_started=frontend_enqueue_started,
        handler_started=handler_started,
    )
    if result is None:
        _cleanup_input_audio(audio_path)
        yield history, history, text, None, gr.update(value={}), gr.update(value={}), _empty_flow_html("本輪未產生結果。"), _empty_html("State Diff", "本輪未產生結果。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip(), gr.update(value=None)
        return
    streamed_history = list(pending_history)
    streamed_history[-1] = {"role": "assistant", "content": ""}
    debug_payload = dict(result["debug"])
    surface_started = time.perf_counter()
    lightweight_updates = 1
    yield streamed_history, streamed_history, result["user_text"], None, gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), _thinking_status("streaming_reply"), gr.skip(), gr.skip(), gr.skip(), gr.skip()

    partials = list(_iter_reply_chunks(result["reply"]))
    for partial in partials:
        streamed_history[-1] = {"role": "assistant", "content": partial}
        lightweight_updates += 1
        yield streamed_history, streamed_history, result["user_text"], None, gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), _thinking_status("streaming_reply"), gr.skip(), gr.skip(), gr.skip(), gr.skip()
        time.sleep(0.01)

    _finalize_surface_delivery(
        result,
        frontend_enqueue_started,
        handler_started,
        surface_started,
        stream_chunk_count=len(partials),
        lightweight_payload_update_count=lightweight_updates,
        full_payload_update_count=1,
    )
    log_record = _append_conversation_log("audio", result)
    annotation_context = _annotation_context_markdown(log_record)
    annotation_status = "新輪次已可標記。"
    debug_payload["turn_index"] = log_record["turn_index"]
    debug_payload["session_id"] = log_record["session_id"]
    client_cognition = _client_cognition_payload_m24(result["cognition_trace"])
    client_memory = _client_memory_payload_m24(result["memory_snapshot"])
    client_record = _client_turn_record_m24(
        log_record,
        client_cognition,
        client_memory,
    )
    _cleanup_input_audio(audio_path)
    streamed_history[-1] = {"role": "assistant", "content": result["reply"]}
    yield streamed_history, streamed_history, result["user_text"], result["audio_path"], debug_payload, client_cognition, result["flow_html"], result["state_html"], client_memory, _status_markdown(), client_record, annotation_context, annotation_status, gr.update(value=None)


def submit_audio(audio_path, history, auto_tts, frontend_enqueue_started=0.0):
    frontend_enqueue_started = float(frontend_enqueue_started or 0.0)
    if frontend_enqueue_started <= 0.0:
        frontend_enqueue_started = RUNTIME.begin_human_turn()
    try:
        yield from _submit_audio_impl(
            audio_path,
            history,
            auto_tts,
            frontend_enqueue_started,
        )
    finally:
        RUNTIME.finish_human_turn()


def handle_audio_stop(
    audio_path,
    history,
    auto_tts,
    voice_chat_mode,
    frontend_enqueue_started=0.0,
):
    if not audio_path:
        if frontend_enqueue_started:
            RUNTIME.finish_human_turn()
        yield history, history, "", None, gr.update(value={}), gr.update(value={}), _empty_flow_html("尚無本輪知識流。"), _empty_html("State Diff", "尚無本輪狀態變化。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
        return
    if voice_chat_mode:
        yield from submit_audio(
            audio_path,
            history,
            auto_tts,
            frontend_enqueue_started=frontend_enqueue_started,
        )
        return
    try:
        transcript = transcribe_audio_only(audio_path)
        _cleanup_input_audio(audio_path)
        yield history, history, transcript, None, gr.update(value={}), gr.update(value={}), _empty_flow_html("只完成轉錄，尚未送入大腦。"), _empty_html("State Diff", "只完成轉錄，尚未送入大腦。"), gr.update(value={}), _status_markdown(), gr.skip(), gr.skip(), gr.skip(), gr.update(value=None)
    finally:
        if frontend_enqueue_started:
            RUNTIME.finish_human_turn()


def transcribe_audio_only(audio_path):
    if not audio_path:
        return ""
    return RUNTIME.get_ears().transcribe_audio_file(audio_path)


def reset_session():
    RUNTIME.reset_brain_session()
    return [], [], None, gr.update(value={}), gr.update(value={}), _empty_flow_html("新 session，等待輸入。"), _empty_html("State Diff", "新 session，尚無狀態變化。"), gr.update(value={}), _status_markdown(), {}, _annotation_context_markdown({}), "", ""


def build_demo():
    with gr.Blocks(title="UruhaBrain Adaptive Cognition Runtime") as demo:
        history_state = gr.State([])
        latest_turn_state = gr.State({})
        text_enqueue_started_state = gr.State(0.0)
        audio_enqueue_started_state = gr.State(0.0)
        architecture_payload = _architecture_alignment_payload()
        unified_eval_payload = _unified_eval_json()

        gr.Markdown(
            "# UruhaBrain Adaptive Cognition Runtime\n"
            "開發目標是讓記憶、語用理解、期待回覆預測與錯誤修正真正參與每一輪對話。\n\n"
            "Chat 是主要產品入口；下方節點圖會顯示這一輪用了哪些狀態、選了哪種回覆方式，以及下一輪回饋如何改變個人模型。研究分頁保留為功能驗證紀錄，不再是開發主畫面。"
        )

        with gr.Tabs(selected="chat"):
            with gr.Tab("Research Closure · M11"):
                closure_stage_selector = gr.Radio(
                    choices=closure_stage_choices(),
                    value=DEFAULT_CLOSURE_STAGE,
                    label="切換證據階段；先看失敗是否被誠實保留",
                )
                closure_lab_html = gr.HTML(
                    value=render_research_closure(DEFAULT_CLOSURE_STAGE)
                )

            with gr.Tab("Register Repair · M10.2"):
                register_case_selector = gr.Radio(
                    choices=register_case_choices(),
                    value=DEFAULT_REGISTER_CASE_ID,
                    label="切換 18 個 source-disjoint cases，查看自然口吻修正是否保留行為",
                )
                register_lab_html = gr.HTML(
                    value=render_register_lab(DEFAULT_REGISTER_CASE_ID)
                )

            with gr.Tab("Blind Rating · M10.3"):
                gr.Markdown(
                    "## 真人盲評入口（目前不是結果）\n"
                    "A/B 來源不顯示，答案 key 不會載入這個頁面。請用匿名代號完成全部 18 案；至少三位互不代填、未看過 key 的真人，才進入正式分析。"
                )
                with gr.Row():
                    blind_rater_id = gr.Textbox(
                        label="匿名評分代號",
                        placeholder="至少 4 字元；只儲存單向雜湊，不儲存原字串",
                    )
                    blind_item_selector = gr.Dropdown(
                        choices=blind_item_choices(),
                        value=DEFAULT_BLIND_ITEM_ID,
                        label="18 個凍結案例",
                    )
                blind_progress_html = gr.HTML(value=render_rater_progress(""))
                blind_item_html = gr.HTML(
                    value=render_blind_rating_item(DEFAULT_BLIND_ITEM_ID)
                )
                gr.Markdown("### 四個維度都要分別評 A 與 B（1=很差，5=很好）")
                with gr.Row():
                    blind_semantic_a = gr.Radio([1, 2, 3, 4, 5], label="語意保留 · A")
                    blind_semantic_b = gr.Radio([1, 2, 3, 4, 5], label="語意保留 · B")
                with gr.Row():
                    blind_behavior_a = gr.Radio([1, 2, 3, 4, 5], label="行為符合 · A")
                    blind_behavior_b = gr.Radio([1, 2, 3, 4, 5], label="行為符合 · B")
                with gr.Row():
                    blind_natural_a = gr.Radio([1, 2, 3, 4, 5], label="自然口語日文 · A")
                    blind_natural_b = gr.Radio([1, 2, 3, 4, 5], label="自然口語日文 · B")
                with gr.Row():
                    blind_boundary_a = gr.Radio([1, 2, 3, 4, 5], label="不過度斷言 · A")
                    blind_boundary_b = gr.Radio([1, 2, 3, 4, 5], label="不過度斷言 · B")
                blind_preference = gr.Radio(
                    choices=["A", "B", "tie", "both_bad"],
                    label="整體偏好",
                )
                blind_independent = gr.Checkbox(
                    label="我是獨立真人評分者，沒有替另一位評分者代填",
                    value=False,
                )
                blind_key_unseen = gr.Checkbox(
                    label="評分前我沒有看過 A/B 對應條件的答案 key",
                    value=False,
                )
                blind_notes = gr.Textbox(label="可選備註", lines=2)
                blind_save = gr.Button("保存這一案", variant="primary")
                blind_save_status = gr.Markdown("尚未保存。")

            with gr.Tab("Behavior→Language · M10"):
                language_sample_selector = gr.Radio(
                    choices=language_case_choices(),
                    value=DEFAULT_LANGUAGE_SAMPLE_ID,
                    label="切換 16 個事件，查看行為預測如何變成日文，以及錯誤在哪一層",
                )
                language_lab_html = gr.HTML(
                    value=render_language_lab(DEFAULT_LANGUAGE_SAMPLE_ID)
                )

            with gr.Tab("Transfer · M9"):
                transfer_cutoff_selector = gr.Radio(
                    choices=transfer_cutoff_choices(),
                    value=DEFAULT_TRANSFER_CUTOFF,
                    label="切換第二人 Mira 的四個 sealed future windows",
                )
                transfer_lab_html = gr.HTML(
                    value=render_transfer_lab(DEFAULT_TRANSFER_CUTOFF)
                )

            with gr.Tab("Robustness · M8"):
                rolling_cutoff_selector = gr.Radio(
                    choices=rolling_cutoff_choices(),
                    value=DEFAULT_ROLLING_CUTOFF,
                    label="切換四個 sealed future windows，觀察同一系統的時間穩定性",
                )
                robustness_lab_html = gr.HTML(
                    value=render_robustness_lab(DEFAULT_ROLLING_CUTOFF)
                )

            with gr.Tab("Ablation Lab · M7"):
                ablation_component_selector = gr.Radio(
                    choices=ablation_component_choices(),
                    value=DEFAULT_ABLATION_COMPONENT,
                    label="切換要拔掉的認知元件，查看實際機率與指標變化",
                )
                ablation_lab_html = gr.HTML(
                    value=render_ablation_lab(DEFAULT_ABLATION_COMPONENT)
                )

            with gr.Tab("Behavior Predictor · M6"):
                behavior_sample_selector = gr.Radio(
                    choices=behavior_sample_choices(),
                    value=DEFAULT_BEHAVIOR_SAMPLE_ID,
                    label="切換 8 個 frozen future behavior holdout",
                )
                behavior_predictor_html = gr.HTML(
                    value=render_behavior_predictor_lab(DEFAULT_BEHAVIOR_SAMPLE_ID)
                )

            with gr.Tab("State Transition · M5"):
                transition_selector = gr.Radio(
                    choices=transition_choices(),
                    value=DEFAULT_TRANSITION_ID,
                    label="切換 8 個未參與訓練的 holdout 事件",
                )
                transition_html = gr.HTML(
                    value=render_transition_lab(DEFAULT_TRANSITION_ID)
                )

            with gr.Tab("HumanState · M4"):
                human_state_selector = gr.Radio(
                    choices=human_state_choices(),
                    value=DEFAULT_HUMAN_STATE_ID,
                    label="切換 2 個 timestamped state snapshots",
                )
                human_state_html = gr.HTML(
                    value=render_human_state_lab(DEFAULT_HUMAN_STATE_ID)
                )

            with gr.Tab("Memory Core · M3"):
                structured_memory_query = gr.Radio(
                    choices=structured_memory_query_choices(),
                    value=DEFAULT_STRUCTURED_MEMORY_QUERY_ID,
                    label="切換 6 個記憶檢索情境",
                )
                structured_memory_html = gr.HTML(
                    value=render_structured_memory_lab(DEFAULT_STRUCTURED_MEMORY_QUERY_ID)
                )

            with gr.Tab("Temporal Twin · M2"):
                temporal_sample = gr.Radio(
                    choices=temporal_sample_choices(),
                    value=DEFAULT_TEMPORAL_SAMPLE_ID,
                    label="切換 12 個被鎖住未來的預測事件",
                )
                temporal_lab_html = gr.HTML(
                    value=render_temporal_prediction_lab(DEFAULT_TEMPORAL_SAMPLE_ID)
                )

            with gr.Tab("50-Turn Repair"):
                memory_repair_checkpoint = gr.Radio(
                    choices=memory_repair_checkpoint_choices(),
                    value=DEFAULT_MEMORY_REPAIR_CHECKPOINT,
                    label="查看修正後的五個嚴格 checkpoint",
                )
                memory_repair_html = gr.HTML(
                    value=render_memory_repair_lab(DEFAULT_MEMORY_REPAIR_CHECKPOINT)
                )

            with gr.Tab("50-Turn A/B"):
                fifty_comparison_checkpoint = gr.Radio(
                    choices=fifty_comparison_checkpoint_choices(),
                    value=DEFAULT_FIFTY_COMPARISON_CHECKPOINT,
                    label="查看五個公平比較 checkpoint",
                )
                fifty_comparison_html = gr.HTML(
                    value=render_fifty_turn_comparison(DEFAULT_FIFTY_COMPARISON_CHECKPOINT)
                )

            with gr.Tab("Long Memory Lab"):
                long_memory_checkpoint = gr.Radio(
                    choices=long_memory_checkpoint_choices(),
                    value=DEFAULT_LONG_MEMORY_CHECKPOINT,
                    label="查看記憶回溯的四個關鍵點",
                )
                long_memory_lab_html = gr.HTML(
                    value=render_long_dialogue_lab(DEFAULT_LONG_MEMORY_CHECKPOINT)
                )

            with gr.Tab("Equation Lab"):
                with gr.Row():
                    equation_scenario = gr.Radio(
                        choices=equation_case_choices(),
                        value=DEFAULT_EQUATION_CASE_ID,
                        label="同一句話的六種情境",
                    )
                    equation_phase = gr.Radio(
                        choices=equation_phase_choices(),
                        value="1",
                        label="方程式階段",
                    )
                    equation_feedback_btn = gr.Button("展示猜錯後如何校正", variant="primary")
                equation_lab_html = gr.HTML(
                    value=render_equation_lab(DEFAULT_EQUATION_CASE_ID, "1")
                )

            with gr.Tab("V2.15 Evidence"):
                with gr.Row():
                    teacher_scenario = gr.Radio(
                        choices=scenario_choices(),
                        value=DEFAULT_SCENARIO_ID,
                        label="展示案例",
                    )
                    teacher_step = gr.Radio(
                        choices=step_choices(),
                        value="1",
                        label="證據步驟",
                    )
                    teacher_next_btn = gr.Button("下一個證據步驟", variant="primary")
                teacher_demo_html = gr.HTML(
                    value=render_teacher_demo(DEFAULT_SCENARIO_ID, "1")
                )

            with gr.Tab("Chat", id="chat"):
                proactive_poll_timer = gr.Timer(value=2.0, active=True)
                with gr.Row(elem_classes=["wrap"]):
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(label="Uruha", height=430)
                        audio_out = gr.Audio(label="TTS Output", type="filepath", autoplay=True, elem_id="uruha-tts")
                    with gr.Column(scale=2):
                        status = gr.Markdown(_status_markdown())
                        text_in = gr.Textbox(label="Text Input", lines=3, placeholder="直接輸入訊息")
                        with gr.Row():
                            send_btn = gr.Button("Send", variant="primary")
                            reset_btn = gr.Button("Reset Session")
                        audio_in = gr.Audio(label="Voice Input", sources=["microphone"], type="filepath", elem_id="uruha-mic")
                        with gr.Row():
                            transcribe_btn = gr.Button("Transcribe Only")
                            send_audio_btn = gr.Button("Transcribe + Send")
                        transcript = gr.Textbox(label="Transcript", lines=2)
                        auto_tts = gr.Checkbox(value=False, label="Auto TTS (requires local TTS server)")
                        voice_chat_mode = gr.Checkbox(value=False, label="Voice Chat Mode (enable hands-free auto-send)", elem_id="voice-chat-mode")

                        with gr.Accordion("Planner / Reply Debug", open=False):
                            debug_json = gr.JSON(label="Planner Debug")
                        with gr.Accordion("Cognitive Trace", open=False):
                            cognition_json = gr.JSON(label="Internal Loop Trace")
                        with gr.Accordion("Memory View", open=False):
                            memory_json = gr.JSON(label="Memory Snapshot")
                        with gr.Accordion("Human Annotation", open=False):
                            annotation_context = gr.Markdown(_annotation_context_markdown({}))
                            annotation_draft_preview = gr.Markdown(_annotation_draft_preview_markdown(None))
                            with gr.Row():
                                annotation_draft_choice = gr.Dropdown(
                                    choices=_annotation_draft_choices(),
                                    value=None,
                                    label="Draft Candidate",
                                    info="從歷史 Web log 自動挖出的高風險候選，可直接載入表單。",
                                )
                                annotation_draft_refresh_btn = gr.Button("Refresh Draft Queue")
                                annotation_draft_load_btn = gr.Button("Load Draft", variant="secondary")
                            with gr.Row():
                                annotation_batch_bucket = gr.Dropdown(
                                    choices=_annotation_batch_bucket_choices(),
                                    value="__ALL__",
                                    label="Batch Bucket",
                                    info="依 suggested failure type 分桶，快速處理同類型失敗案例。",
                                )
                                annotation_batch_severity = gr.Dropdown(
                                    choices=_annotation_batch_severity_choices(),
                                    value="ALL",
                                    label="Severity Filter",
                                )
                                annotation_batch_reason = gr.Dropdown(
                                    choices=_annotation_batch_reason_choices(),
                                    value="ALL",
                                    label="Reason Filter",
                                )
                            with gr.Row():
                                annotation_batch_take_count = gr.Dropdown(
                                    choices=[1, 3, 5, 10, 20],
                                    value=3,
                                    label="Batch Take Count",
                                )
                                annotation_batch_refresh_btn = gr.Button("Refresh Batch View")
                                annotation_batch_accept_btn = gr.Button("Accept Suggested Batch", variant="secondary")
                                annotation_batch_accept_replay_btn = gr.Button("Accept Batch + Replay Eval", variant="primary")
                            annotation_batch_preview = gr.Markdown(_annotation_batch_review_markdown("__ALL__", "ALL", "ALL", 3))
                            annotation_verdict = gr.Radio(
                                choices=VERDICT_CHOICES,
                                value="mixed",
                                label="Human Verdict",
                                info=f"taxonomy={TAXONOMY_VERSION}",
                            )
                            annotation_severity = gr.Radio(
                                choices=SEVERITY_CHOICES,
                                value="medium",
                                label="Severity",
                            )
                            annotation_failures = gr.CheckboxGroup(
                                choices=FAILURE_TYPE_CHOICES,
                                label="Failure Types",
                            )
                            annotation_notes = gr.Textbox(
                                label="Annotation Notes",
                                lines=4,
                                placeholder="寫下為什麼像人 / 不像人，以及你想怎麼修。",
                            )
                            with gr.Row():
                                annotation_history_limit = gr.Dropdown(
                                    choices=[10, 20, 50, 100],
                                    value=20,
                                    label="Recent Window",
                                )
                                annotation_save_btn = gr.Button("Save Annotation", variant="secondary")
                                annotation_save_replay_btn = gr.Button("Save + Replay Eval", variant="primary")
                                annotation_refresh_btn = gr.Button("Refresh Annotation Log")
                            annotation_status = gr.Markdown("")
                            annotation_history_md = gr.Markdown(_annotation_history_markdown(20))
                            annotation_history_json = gr.JSON(
                                label="Recent Annotation Records",
                                value=_annotation_history_payload(20),
                            )

                gr.Markdown("## Live Memory Flow")
                flow_html = gr.HTML(value=render_memory_observatory(_latest_observatory_result()))
                with gr.Accordion("Cognitive State & Decision Details", open=False):
                    state_html = gr.HTML(value=_empty_html("State Diff", "尚無本輪狀態變化。"))

            with gr.Tab("Architecture"):
                architecture_md = gr.Markdown(_architecture_markdown())
                with gr.Row():
                    rerun_arch_btn = gr.Button("Run Architecture Checks", variant="primary")

                with gr.Accordion("Regression Baseline Control", open=True):
                    with gr.Row():
                        snapshot_label_in = gr.Textbox(label="Snapshot Label", placeholder="e.g. before_patch_a", value="manual")
                        snapshot_btn = gr.Button("Snapshot Current Regression Eval", variant="secondary")
                        run_diff_btn = gr.Button("Run Regression Diff", variant="primary")

                    snapshot_picker = gr.Dropdown(
                        choices=_snapshot_picker_choices(),
                        value=(_all_snapshot_meta_paths() or [""])[0],
                        label="Selected Baseline Snapshot",
                        info="選擇要對標的歷史快照。手動 Diff 與新鮮度檢查將以此為準。"
                    )

                    with gr.Row():
                        snapshot_status_md = gr.Markdown(_regression_snapshot_markdown())
                        diff_status_md = gr.Markdown("")

                    regression_freshness_md = gr.Markdown(_regression_freshness_markdown())

                alignment_json = gr.JSON(label="Alignment Snapshot", value=architecture_payload)
                unified_eval_json = gr.JSON(label="Unified Eval Summary", value=unified_eval_payload)
                arch_report_json = gr.JSON(label="Cognitive Architecture Eval", value=_load_json(ARCH_REPORT_PATH))
                v2_report_json = gr.JSON(label="V2 Human-Answer Eval", value=_load_json(V2_REPORT_PATH))
                annotation_candidate_md = gr.Markdown(_annotation_candidate_markdown())
                annotation_candidate_json = gr.JSON(label="Annotation Candidate Queue", value=_load_json(ANNOTATION_CANDIDATE_QUEUE_JSON_PATH))
                annotation_draft_md = gr.Markdown(_annotation_draft_queue_markdown())
                annotation_draft_json = gr.JSON(label="Annotation Draft Queue", value=_annotation_draft_queue_payload())
                annotation_report_md = gr.Markdown(_annotation_report_markdown())
                annotation_report_json = gr.JSON(label="Human Annotation Report", value=_load_json(HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH))
                regression_eval_md = gr.Markdown(_regression_eval_markdown())
                regression_eval_json = gr.JSON(label="Human Feedback Regression Eval", value=_load_json(HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH))
                regression_diff_md = gr.Markdown(_regression_diff_markdown())
                regression_diff_json = gr.JSON(label="Human Feedback Regression Diff", value=_load_json(HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH))

        closure_stage_selector.change(
            fn=render_research_closure,
            inputs=[closure_stage_selector],
            outputs=[closure_lab_html],
            queue=False,
        )

        register_case_selector.change(
            fn=render_register_lab,
            inputs=[register_case_selector],
            outputs=[register_lab_html],
            queue=False,
        )

        blind_item_selector.change(
            fn=render_blind_rating_item,
            inputs=[blind_item_selector],
            outputs=[blind_item_html],
            queue=False,
        )

        blind_rater_id.change(
            fn=render_rater_progress,
            inputs=[blind_rater_id],
            outputs=[blind_progress_html],
            queue=False,
        )

        blind_save.click(
            fn=save_blind_rating,
            inputs=[
                blind_rater_id,
                blind_item_selector,
                blind_semantic_a,
                blind_semantic_b,
                blind_behavior_a,
                blind_behavior_b,
                blind_natural_a,
                blind_natural_b,
                blind_boundary_a,
                blind_boundary_b,
                blind_preference,
                blind_independent,
                blind_key_unseen,
                blind_notes,
            ],
            outputs=[blind_save_status, blind_progress_html],
            queue=False,
        )

        language_sample_selector.change(
            fn=render_language_lab,
            inputs=[language_sample_selector],
            outputs=[language_lab_html],
            queue=False,
        )

        transfer_cutoff_selector.change(
            fn=render_transfer_lab,
            inputs=[transfer_cutoff_selector],
            outputs=[transfer_lab_html],
            queue=False,
        )

        rolling_cutoff_selector.change(
            fn=render_robustness_lab,
            inputs=[rolling_cutoff_selector],
            outputs=[robustness_lab_html],
            queue=False,
        )

        ablation_component_selector.change(
            fn=render_ablation_lab,
            inputs=[ablation_component_selector],
            outputs=[ablation_lab_html],
            queue=False,
        )

        behavior_sample_selector.change(
            fn=render_behavior_predictor_lab,
            inputs=[behavior_sample_selector],
            outputs=[behavior_predictor_html],
            queue=False,
        )

        transition_selector.change(
            fn=render_transition_lab,
            inputs=[transition_selector],
            outputs=[transition_html],
            queue=False,
        )

        human_state_selector.change(
            fn=render_human_state_lab,
            inputs=[human_state_selector],
            outputs=[human_state_html],
            queue=False,
        )

        structured_memory_query.change(
            fn=render_structured_memory_lab,
            inputs=[structured_memory_query],
            outputs=[structured_memory_html],
            queue=False,
        )

        temporal_sample.change(
            fn=render_temporal_prediction_lab,
            inputs=[temporal_sample],
            outputs=[temporal_lab_html],
            queue=False,
        )

        memory_repair_checkpoint.change(
            fn=render_memory_repair_lab,
            inputs=[memory_repair_checkpoint],
            outputs=[memory_repair_html],
            queue=False,
        )

        fifty_comparison_checkpoint.change(
            fn=render_fifty_turn_comparison,
            inputs=[fifty_comparison_checkpoint],
            outputs=[fifty_comparison_html],
            queue=False,
        )

        long_memory_checkpoint.change(
            fn=render_long_dialogue_lab,
            inputs=[long_memory_checkpoint],
            outputs=[long_memory_lab_html],
            queue=False,
        )

        equation_scenario.change(
            fn=render_equation_lab,
            inputs=[equation_scenario, equation_phase],
            outputs=[equation_lab_html],
            queue=False,
        )
        equation_phase.change(
            fn=render_equation_lab,
            inputs=[equation_scenario, equation_phase],
            outputs=[equation_lab_html],
            queue=False,
        )
        equation_feedback_btn.click(
            fn=show_feedback_correction,
            inputs=[equation_scenario, equation_phase],
            outputs=[equation_scenario, equation_phase, equation_lab_html],
            queue=False,
        )

        teacher_scenario.change(
            fn=render_teacher_demo,
            inputs=[teacher_scenario, teacher_step],
            outputs=[teacher_demo_html],
            queue=False,
        )
        teacher_step.change(
            fn=render_teacher_demo,
            inputs=[teacher_scenario, teacher_step],
            outputs=[teacher_demo_html],
            queue=False,
        )
        teacher_next_btn.click(
            fn=advance_teacher_demo,
            inputs=[teacher_scenario, teacher_step],
            outputs=[teacher_step, teacher_demo_html],
            queue=False,
        )

        text_in.submit(
            fn=begin_human_submission,
            inputs=[text_in],
            outputs=[text_enqueue_started_state],
            queue=False,
            show_progress="hidden",
        ).then(
            fn=submit_text,
            inputs=[text_in, history_state, auto_tts, text_enqueue_started_state],
            outputs=[chatbot, history_state, text_in, audio_out, debug_json, cognition_json, flow_html, state_html, memory_json, status, latest_turn_state, annotation_context, annotation_status],
            queue=True,
            concurrency_limit=1,
            concurrency_id="human_turn_m19",
        )

        send_btn.click(
            fn=begin_human_submission,
            inputs=[text_in],
            outputs=[text_enqueue_started_state],
            queue=False,
            show_progress="hidden",
        ).then(
            fn=submit_text,
            inputs=[text_in, history_state, auto_tts, text_enqueue_started_state],
            outputs=[chatbot, history_state, text_in, audio_out, debug_json, cognition_json, flow_html, state_html, memory_json, status, latest_turn_state, annotation_context, annotation_status],
            queue=True,
            concurrency_limit=1,
            concurrency_id="human_turn_m19",
        )

        transcribe_btn.click(
            fn=transcribe_audio_only,
            inputs=[audio_in],
            outputs=[transcript],
            queue=True,
        )

        send_audio_btn.click(
            fn=begin_human_submission,
            inputs=[audio_in],
            outputs=[audio_enqueue_started_state],
            queue=False,
            show_progress="hidden",
        ).then(
            fn=submit_audio,
            inputs=[audio_in, history_state, auto_tts, audio_enqueue_started_state],
            outputs=[chatbot, history_state, transcript, audio_out, debug_json, cognition_json, flow_html, state_html, memory_json, status, latest_turn_state, annotation_context, annotation_status, audio_in],
            queue=True,
            concurrency_limit=1,
            concurrency_id="human_turn_m19",
        )

        audio_in.stop_recording(
            fn=begin_human_submission,
            inputs=[audio_in],
            outputs=[audio_enqueue_started_state],
            queue=False,
            show_progress="hidden",
        ).then(
            fn=handle_audio_stop,
            inputs=[audio_in, history_state, auto_tts, voice_chat_mode, audio_enqueue_started_state],
            outputs=[chatbot, history_state, transcript, audio_out, debug_json, cognition_json, flow_html, state_html, memory_json, status, latest_turn_state, annotation_context, annotation_status, audio_in],
            queue=True,
            concurrency_limit=1,
            concurrency_id="human_turn_m19",
        )

        reset_btn.click(
            fn=reset_session,
            inputs=None,
            outputs=[chatbot, history_state, audio_out, debug_json, cognition_json, flow_html, state_html, memory_json, status, latest_turn_state, annotation_context, annotation_status, transcript],
            queue=False,
        )

        proactive_poll_timer.tick(
            fn=poll_proactive_turn,
            inputs=[history_state, auto_tts],
            outputs=[chatbot, history_state, audio_out, status, latest_turn_state, annotation_context, annotation_status],
            queue=False,
            trigger_mode="always_last",
        )

        annotation_save_btn.click(
            fn=save_human_annotation,
            inputs=[latest_turn_state, annotation_verdict, annotation_severity, annotation_failures, annotation_notes, annotation_history_limit],
            outputs=[annotation_status, annotation_notes, annotation_failures, annotation_history_md, annotation_history_json],
            queue=False,
        )

        annotation_save_replay_btn.click(
            fn=save_human_annotation_with_replay,
            inputs=[
                latest_turn_state,
                annotation_verdict,
                annotation_severity,
                annotation_failures,
                annotation_notes,
                annotation_history_limit,
                snapshot_picker,
            ],
            outputs=[
                annotation_status,
                annotation_notes,
                annotation_failures,
                annotation_history_md,
                annotation_history_json,
                regression_eval_md,
                regression_eval_json,
                regression_diff_md,
                regression_diff_json,
                regression_freshness_md,
                snapshot_picker,
            ],
            queue=True,
        )

        annotation_refresh_btn.click(
            fn=refresh_annotation_history,
            inputs=[annotation_history_limit],
            outputs=[annotation_history_md, annotation_history_json],
            queue=False,
        )
        annotation_draft_refresh_btn.click(
            fn=refresh_annotation_draft_queue,
            inputs=None,
            outputs=[annotation_draft_choice, annotation_draft_preview],
            queue=False,
        )
        annotation_draft_choice.change(
            fn=preview_annotation_draft,
            inputs=[annotation_draft_choice],
            outputs=[annotation_draft_preview],
            queue=False,
        )
        annotation_draft_load_btn.click(
            fn=load_annotation_draft,
            inputs=[annotation_draft_choice],
            outputs=[
                latest_turn_state,
                annotation_context,
                annotation_verdict,
                annotation_severity,
                annotation_failures,
                annotation_notes,
                annotation_status,
                annotation_draft_preview,
            ],
            queue=False,
        )
        annotation_batch_refresh_btn.click(
            fn=refresh_annotation_batch_workbench,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count],
            outputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_preview],
            queue=False,
        )
        annotation_batch_bucket.change(
            fn=refresh_annotation_batch_workbench,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count],
            outputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_preview],
            queue=False,
        )
        annotation_batch_severity.change(
            fn=refresh_annotation_batch_workbench,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count],
            outputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_preview],
            queue=False,
        )
        annotation_batch_reason.change(
            fn=refresh_annotation_batch_workbench,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count],
            outputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_preview],
            queue=False,
        )
        annotation_batch_take_count.change(
            fn=refresh_annotation_batch_workbench,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count],
            outputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_preview],
            queue=False,
        )
        # 批次審閱輸出元件清單 (15個)
        batch_review_outputs = [
            annotation_status,
            annotation_history_md,
            annotation_history_json,
            annotation_draft_choice,
            annotation_draft_preview,
            annotation_batch_bucket,
            annotation_batch_severity,
            annotation_batch_reason,
            annotation_batch_preview,
            regression_eval_md,
            regression_eval_json,
            regression_diff_md,
            regression_diff_json,
            regression_freshness_md,
            snapshot_picker,
        ]

        annotation_batch_accept_btn.click(
            fn=batch_accept_annotation_drafts,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count, annotation_history_limit, snapshot_picker, gr.State(False)],
            outputs=batch_review_outputs,
            queue=False,
        )
        annotation_batch_accept_replay_btn.click(
            fn=batch_accept_annotation_drafts,
            inputs=[annotation_batch_bucket, annotation_batch_severity, annotation_batch_reason, annotation_batch_take_count, annotation_history_limit, snapshot_picker, gr.State(True)],
            outputs=batch_review_outputs,
            queue=True, # Replay 耗時較長，啟用 queue
        )
        annotation_history_limit.change(
            fn=refresh_annotation_history,
            inputs=[annotation_history_limit],
            outputs=[annotation_history_md, annotation_history_json],
            queue=False,
        )

        rerun_arch_btn.click(
            fn=_run_architecture_checks,
            inputs=[snapshot_picker],
            outputs=[
                architecture_md,
                alignment_json,
                arch_report_json,
                v2_report_json,
                annotation_candidate_md,
                annotation_candidate_json,
                annotation_draft_md,
                annotation_draft_json,
                annotation_report_md,
                annotation_report_json,
                regression_eval_md,
                regression_eval_json,
                regression_diff_md,
                regression_diff_json,
                unified_eval_json,
                snapshot_status_md,
                regression_freshness_md,
                snapshot_picker,
                status,
            ],
            queue=True,
        )

        snapshot_btn.click(
            fn=create_regression_snapshot,
            inputs=[snapshot_label_in],
            outputs=[status, snapshot_status_md, regression_freshness_md, snapshot_picker],
            queue=False,
        )

        run_diff_btn.click(
            fn=run_regression_diff_manually,
            inputs=[snapshot_picker],
            outputs=[diff_status_md, regression_diff_md, regression_diff_json, regression_freshness_md],
            queue=False,
        )

        snapshot_picker.change(
            fn=_regression_freshness_markdown,
            inputs=[snapshot_picker],
            outputs=[regression_freshness_md],
            queue=False,
        )

    return demo


def smoke_test():
    demo = build_demo()
    RUNTIME.get_mouth()
    return {
        "gradio": "ok",
        "whisper_model": WEB_WHISPER_MODEL,
        "tts_base_url": WEB_TTS_BASE_URL,
        "tts_model_id": RUNTIME.get_mouth().model_id,
        "demo_built": bool(demo),
    }


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        print(json.dumps(smoke_test(), ensure_ascii=False, indent=2))
        raise SystemExit(0)

    demo = build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=WEB_SERVER_NAME,
        server_port=WEB_SERVER_PORT,
        inbrowser=False,
        css=WEB_CSS,
        head=WEB_HEAD,
    )
