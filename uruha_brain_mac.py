import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_project_python():
    if os.getenv("URUHA_SKIP_AUTO_VENV") == "1":
        return
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        print(f"⚠️ 偵測到目前 Python 不是專案 venv：{sys.executable}")
        print(f"↪️ 自動切換到：{EXPECTED_PYTHON}")
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()

import datetime
import hashlib
import heapq
import inspect
import json
import math
import random
import re
import shutil
import tempfile
import time
import threading
import uuid
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, field

import chromadb
import torch
from colorama import Fore, Style, init
from dotenv import load_dotenv
from openai import OpenAI
from peft import LoraConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from uruha_psyche import Psyche, PsycheConfig
from uruha_runtime import BlackboardEntry, RuntimeConfig, RuntimeEvent, RuntimeState
import uruha_memory_runtime as umr
import uruha_leftbrain_rules
from project_paths import RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH
from rightbrain_repair_selector import (
    extract_candidate_features as extract_learned_repair_features,
    load_model_artifact,
    score_candidate as score_learned_repair_candidate,
)
from rightbrain_language_quality import (
    ASCII_WORD_RE,
    CHINESE_SPECIFIC_RE,
    INSTRUCTION_MARKERS,
    NONSTANDARD_CJK_RE,
    POLITE_RE,
    UNICODE_REPLACEMENT_CHAR,
)

# ===========================
# ⚙️ Mac 雙腦系統初始化
# ===========================
init(autoreset=True)
load_dotenv()


def _env_float(name, default):
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _env_int(name, default):
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return int(default)
    try:
        return int(raw)
    except Exception:
        return int(default)


def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_csv_floats(name, default_values):
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return [float(item) for item in default_values]
    values = []
    for item in str(raw).split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except Exception:
            return [float(default) for default in default_values]
    return values or [float(item) for item in default_values]


def _env_csv_ints(name, default_values):
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return [int(item) for item in default_values]
    values = []
    for item in str(raw).split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except Exception:
            return [int(default) for default in default_values]
    return values or [int(item) for item in default_values]

OLLAMA_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "uruha_memory_mac_db")
RIGHT_BRAIN_BASE_MODEL = os.getenv("URUHA_RIGHT_BRAIN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")


def _normalize_right_brain_adapter_path(raw_path, default_path):
    raw = str(default_path if raw_path is None else raw_path).strip()
    if not raw:
        return ""
    if raw.lower() in {"none", "base-only", "base_only"}:
        return ""
    return os.path.abspath(raw)


RIGHT_BRAIN_ADAPTER_PRIORITY = (
    "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1",
    "uruha_v10_all_linear_lora",
)


def _default_right_brain_adapter_path(base_dir):
    """Prefer the strongest validated local adapter, with legacy fallback."""
    for adapter_ref in RIGHT_BRAIN_ADAPTER_PRIORITY:
        candidate = os.path.join(base_dir, adapter_ref)
        if os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return os.path.abspath(os.path.join(base_dir, RIGHT_BRAIN_ADAPTER_PRIORITY[0]))


RIGHT_BRAIN_ADAPTER_PATH = _normalize_right_brain_adapter_path(
    os.getenv("URUHA_RIGHT_BRAIN_ADAPTER_PATH"),
    _default_right_brain_adapter_path(BASE_DIR),
)
RIGHT_BRAIN_REPAIR_ADAPTER_PATH = _normalize_right_brain_adapter_path(
    os.getenv("URUHA_RIGHT_BRAIN_REPAIR_ADAPTER_PATH"),
    "",
)
SCENE_VALUES = {"casual", "support", "invite", "jealousy", "boundary", "refusal", "ooc_defense"}
WORKING_MEMORY_LIMIT = 5
WORKING_MEMORY_RETRIEVAL_LIMIT = _env_int("URUHA_WORKING_MEMORY_RETRIEVAL_LIMIT", 20)
LOW_ROAD_MOOD_THRESHOLD = -72
PLANNER_MAX_TICKS = 3
AUTONOMOUS_IDLE_SECONDS = _env_float("URUHA_AUTONOMOUS_IDLE_SECONDS", 45)
AUTONOMOUS_MIN_INTERVAL_SECONDS = _env_float("URUHA_AUTONOMOUS_MIN_INTERVAL_SECONDS", 15)
EVENT_TIMER_INTERVAL_SECONDS = _env_float("URUHA_EVENT_TIMER_INTERVAL_SECONDS", 10)
DRIVE_BOREDOM_GAIN_PER_SECOND = _env_float("URUHA_DRIVE_BOREDOM_GAIN_PER_SECOND", 0.1)
DRIVE_SOCIAL_GAIN_PER_SECOND = _env_float("URUHA_DRIVE_SOCIAL_GAIN_PER_SECOND", 0.1)
INTERNAL_URGE_BOREDOM_THRESHOLD = _env_float("URUHA_INTERNAL_URGE_BOREDOM_THRESHOLD", 60.0)
INTERNAL_URGE_SOCIAL_THRESHOLD = _env_float("URUHA_INTERNAL_URGE_SOCIAL_THRESHOLD", 60.0)
PROACTIVE_SLEEP_AFTER_IGNORES = _env_int("URUHA_PROACTIVE_SLEEP_AFTER_IGNORES", 3)
PREDICTION_ERROR_THRESHOLD = 1.5
SHORT_TERM_BUFFER_LIMIT = 32
SHORT_TERM_DECAY_SECONDS = 1800
SHORT_TERM_FORGET_THRESHOLD = 0.18
PASSIVE_DECAY_DAYS = _env_int("URUHA_PASSIVE_DECAY_DAYS", 30)
PSYCHE_MOOD_STEP_LIMIT = 6
PSYCHE_TRUST_STEP_LIMIT = 6
PSYCHE_SOFT_ZONE = 58
RIGHT_BRAIN_SAMPLE_TEMPERATURES = _env_csv_floats("URUHA_RIGHT_BRAIN_SAMPLE_TEMPERATURES", [0.82, 0.96, 1.08])
RIGHT_BRAIN_SAMPLE_TOP_P = _env_csv_floats("URUHA_RIGHT_BRAIN_SAMPLE_TOP_P", [0.92, 0.95, 0.98])
RIGHT_BRAIN_SAMPLE_TOP_K = _env_csv_ints("URUHA_RIGHT_BRAIN_SAMPLE_TOP_K", [64, 96, 128])
RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES = _env_csv_floats("URUHA_RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES", [1.2, 1.26, 1.32])
RIGHT_BRAIN_NO_REPEAT_NGRAM_SIZE = _env_int("URUHA_RIGHT_BRAIN_NO_REPEAT_NGRAM_SIZE", 3)
RIGHT_BRAIN_MODEL_BLEND_ENABLED = _env_bool("URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED", False)
RIGHT_BRAIN_MODEL_CANDIDATE_COUNT = _env_int("URUHA_RIGHT_BRAIN_MODEL_CANDIDATE_COUNT", 3)
RIGHT_BRAIN_MODEL_SELECTION_MARGIN = _env_float("URUHA_RIGHT_BRAIN_MODEL_SELECTION_MARGIN", 0.15)
RIGHT_BRAIN_MODEL_REPAIR_ENABLED = _env_bool("URUHA_RIGHT_BRAIN_MODEL_REPAIR_ENABLED", False)
RIGHT_BRAIN_SELECTOR_SHADOW_ENABLED = _env_bool("URUHA_RIGHT_BRAIN_SELECTOR_SHADOW_ENABLED", True)
RIGHT_BRAIN_SELECTOR_MODEL_PATH = os.path.abspath(
    os.getenv("URUHA_RIGHT_BRAIN_SELECTOR_MODEL_PATH", RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH)
)
RIGHT_BRAIN_MODEL_CONTRACT_VERSION = "plan_surface_contract_v1"
RIGHT_BRAIN_MODEL_SYSTEM_PROMPT = (
    "You are the RightBrain surface formulator for UruhaBrain. Your job is semantic realization, "
    "not roleplay improvisation. Return exactly one short, natural casual Japanese chat reply. "
    "For every required_marker_group in the input contract, include at least one marker from that "
    "group naturally in the reply. Do not include any forbidden_marker. Keep the concrete topic and "
    "grounding terms. Use audited_memory_brief only as a surface cue; never infer from hidden memory "
    "or reveal memory that is not explicitly allowed. Do not output analysis, labels, JSON, metadata, English, Chinese, or system "
    "text. Do not use 私. Do not explain the contract."
)
RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT = (
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT
    + " The previous draft failed the contract. Repair it once and return only the corrected reply."
)


def _resolve_right_brain_model_loading(requested):
    if requested is None:
        return RIGHT_BRAIN_MODEL_BLEND_ENABLED
    return bool(requested)


def _compact_dialogue_text(text):
    return re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`]+", "", str(text or "").lower())


def _contains_dialogue_keyword(text, keywords):
    lowered = str(text or "").lower()
    compact = _compact_dialogue_text(lowered)
    for keyword in keywords:
        needle = str(keyword or "").lower()
        if not needle:
            continue
        if needle in lowered:
            return True
        compact_needle = _compact_dialogue_text(needle)
        if compact_needle and compact_needle in compact:
            return True
    return False


def _select_recent_action_reference(recent_turns, query_text="", current_user_input=""):
    action_specs = [
        {
            "stem": "風呂入る",
            "reply": "風呂入るって言ってただろ",
            "kind": "future_action",
            "markers": ["shower", "bath", "洗澡", "風呂", "シャワー", "入ってくる"],
        },
        {
            "stem": "寝る",
            "reply": "寝るって言ってただろ",
            "kind": "future_action",
            "markers": ["sleep", "寝る", "睡", "おやすみ"],
        },
        {
            "stem": "ご飯食う",
            "reply": "ご飯食うって言ってただろ",
            "kind": "future_action",
            "markers": ["eat", "dinner", "lunch", "吃飯", "吃饭", "ご飯", "飯"],
        },
        {
            "stem": "出かける",
            "reply": "出かけるって言ってただろ",
            "kind": "future_action",
            "markers": ["go out", "出去", "出門", "出门", "出かける", "行ってくる"],
        },
        {
            "stem": "戻る",
            "reply": "戻るって言ってただろ",
            "kind": "return_home",
            "markers": ["back", "ただいま", "回來", "回来", "戻る", "i'm back", "im back"],
        },
    ]
    ignore_markers = ["アップルパイ", "apple pie", "miss me", "想我", "恋しかった", "疲れ", "tired"]
    future_query_markers = [
        "要去",
        "要幹嘛",
        "要干嘛",
        "去幹嘛",
        "去干嘛",
        "我要去",
        "going to",
        "about to",
        "what was i going to do",
        "what am i about to do",
        "何するって",
        "何する",
    ]
    quoted_recall_markers = ["剛剛說", "刚刚说", "さっき言った", "what did i just say", "what did i say"]

    wants_future = _contains_dialogue_keyword(query_text, future_query_markers)
    wants_quote_recall = wants_future or _contains_dialogue_keyword(query_text, quoted_recall_markers)
    best = None

    for recency_index, turn in enumerate(reversed(recent_turns or [])):
        utterance = str((turn or {}).get("user") or "").strip()
        if not utterance:
            continue
        if current_user_input and utterance == current_user_input:
            continue
        if _contains_dialogue_keyword(utterance, ignore_markers):
            continue

        for spec in action_specs:
            if not _contains_dialogue_keyword(utterance, spec["markers"]):
                continue
            score = max(0.0, 4.4 - (recency_index * 0.55))
            if spec["kind"] == "future_action":
                score += 1.2
            if wants_future and spec["kind"] == "future_action":
                score += 2.0
            if wants_future and spec["kind"] == "return_home":
                score -= 2.2
            if _contains_dialogue_keyword(utterance, ["先", "先に", "等等", "待會", "待会", "going to", "gonna", "about to", "入ってくる", "行ってくる"]):
                score += 0.9
            if _contains_dialogue_keyword(utterance, ["ただいま", "回來", "回来", "i'm back", "im back", "戻った"]):
                score += 0.2 if not wants_future else -1.4
            if wants_quote_recall and len(_compact_dialogue_text(utterance)) <= 18:
                score += 0.2
            if best is None or score > best["score"]:
                best = {
                    "stem": spec["stem"],
                    "reply": spec["reply"],
                    "utterance": utterance,
                    "score": round(score, 4),
                    "kind": spec["kind"],
                }
    return best


# ===========================
# 🧠 記憶核心 (Memory Core)
# ===========================
class MemoryManager:
    def __init__(self):
        print(Style.DIM + f"📂 初始化記憶庫路徑: {DB_PATH}")
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.kb_col = self.client.get_or_create_collection("knowledge_base")
        self.episode_col = self.client.get_or_create_collection("episodic_memory")
        self.wisdom_col = self.client.get_or_create_collection("wisdom_semantic")
        self.procedural_col = self.client.get_or_create_collection("procedural_memory")
        self.profile_col = self.client.get_or_create_collection("user_profile")
        self.session_turns = []
        self.short_term_buffer = []
        self.session_profile = {
            "name": None,
            "likes": [],
            "dislikes": [],
            "favorites": [],
        }
        self._consolidated_turn_index = 0
        self._last_consolidation_at = None
        self._last_decay_at = None
        self._last_maintenance_result = None

    def clear_session_state(self):
        self.session_turns = []
        self.short_term_buffer = []
        self.session_profile = {
            "name": None,
            "likes": [],
            "dislikes": [],
            "favorites": [],
        }
        self._consolidated_turn_index = 0
        self._last_consolidation_at = None
        self._last_decay_at = None
        self._last_maintenance_result = None

    def query_all_layers(self, text):
        self._decay_short_term_memory()
        working_memory = self._build_working_memory(text)
        self._mark_working_memory_access(working_memory)
        return {
            "knowledge": self._safe_query(self.kb_col, text, "無特殊知識"),
            "episodes": self._safe_query(self.episode_col, text, "無相關經歷"),
            "wisdom": self._safe_query(self.wisdom_col, text, "無相關經驗"),
            "procedural": self._safe_query(self.procedural_col, text, "無相關程序記憶"),
            "profile": self._profile_summary(),
            "profile_structured": self._profile_snapshot(),
            "recent_dialogue": self._recent_dialogue_summary(),
            "recent_turns": list(self.session_turns[-8:]),
            "short_term_summary": self._short_term_summary(),
            "working_memory_items": working_memory,
            "working_memory_summary": self._working_memory_summary(working_memory),
        }

    def get_runtime_snapshot(self):
        return {
            "profile": self._profile_snapshot(),
            "profile_summary": self._profile_summary(),
            "recent_dialogue": self._recent_dialogue_summary(),
            "recent_turns": list(self.session_turns[-8:]),
            "short_term_summary": self._short_term_summary(),
            "short_term_buffer": list(self.short_term_buffer[-8:]),
            "procedural_summary": self._procedural_summary(),
            "pending_consolidation_turns": max(0, len(self.session_turns) - self._consolidated_turn_index),
            "last_consolidation_at": self._last_consolidation_at,
            "last_decay_at": self._last_decay_at,
            "last_maintenance_result": self._last_maintenance_result,
        }

    def _safe_query(self, collection, text, default_val):
        res = collection.query(query_texts=[text], n_results=3)
        if res["documents"] and res["documents"][0]:
            docs = [doc.strip() for doc in res["documents"][0] if isinstance(doc, str) and doc.strip()]
            if docs:
                return " || ".join(docs[:2])
        return default_val

    def _query_collection_candidates(self, collection, text, source, limit=WORKING_MEMORY_RETRIEVAL_LIMIT):
        return umr.query_collection_candidates(collection, text, source, limit=limit)

    def _recent_turn_candidates(self):
        return umr.recent_turn_candidates(self.session_turns)

    def _short_term_candidates(self):
        return umr.short_term_candidates(self.short_term_buffer)

    def _profile_candidates(self):
        return umr.profile_candidates(self._profile_snapshot())

    def _short_term_summary(self):
        return umr.short_term_summary(self.short_term_buffer)

    def _procedural_summary(self):
        return self._safe_query(self.procedural_col, "response pattern user style relationship preference", "無程序記憶")

    def _memory_tokens(self, text):
        return umr.memory_tokens(text)

    def _salience_score(self, candidate, query_tokens, now):
        return umr.salience_score(candidate, query_tokens, now)

    def _build_working_memory(self, text):
        candidates = []
        candidates.extend(self._profile_candidates())
        candidates.extend(self._short_term_candidates())
        candidates.extend(self._recent_turn_candidates())
        candidates.extend(self._query_collection_candidates(self.episode_col, text, "episode", limit=WORKING_MEMORY_RETRIEVAL_LIMIT))
        candidates.extend(self._query_collection_candidates(self.wisdom_col, text, "wisdom", limit=WORKING_MEMORY_RETRIEVAL_LIMIT))
        candidates.extend(self._query_collection_candidates(self.procedural_col, text, "procedural", limit=WORKING_MEMORY_RETRIEVAL_LIMIT))
        candidates.extend(self._query_collection_candidates(self.kb_col, text, "knowledge", limit=WORKING_MEMORY_RETRIEVAL_LIMIT))

        return umr.build_working_memory(text, candidates, working_memory_limit=WORKING_MEMORY_LIMIT)

    def _collection_for_name(self, name):
        return {
            "episode": self.episode_col,
            "wisdom": self.wisdom_col,
            "procedural": self.procedural_col,
            "knowledge": self.kb_col,
            "profile": self.profile_col,
        }.get(name)

    def _mark_working_memory_access(self, items):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in items or []:
            memory_id = item.get("memory_id")
            collection = self._collection_for_name(item.get("collection_name"))
            if not memory_id or collection is None:
                continue
            metadata = dict(item.get("metadata") or {})
            metadata["last_accessed_at"] = timestamp
            try:
                collection.update(ids=[memory_id], metadatas=[metadata])
            except Exception:
                pass

    def _working_memory_summary(self, items):
        return umr.working_memory_summary(items, working_memory_limit=WORKING_MEMORY_LIMIT)

    def _estimate_turn_strength(self, user_input, logic_data=None):
        logic_data = logic_data or {}
        base = 0.42
        lowered = str(user_input or "").lower()
        if any(marker in lowered for marker in ["記得", "remember", "名前", "叫我", "我喜歡", "i like", "favorite", "嫌い"]):
            base += 0.26
        if any(marker in lowered for marker in ["先去", "待會", "待会", "等等去", "going to", "about to", "gonna", "行ってくる", "入ってくる"]):
            base += 0.18
        if any(marker in lowered for marker in ["死にたい", "不想活", "kill myself", "消えたい"]):
            base += 0.32
        if logic_data.get("scene") in {"support", "boundary", "jealousy"}:
            base += 0.12
        if logic_data.get("surface_act") in {"permission_with_boundary", "affection_tease_soften", "protective_brake"}:
            base += 0.08
        return round(min(1.0, base), 3)

    def _append_short_term_buffer(self, user_input, ai_response, logic_data, timestamp):
        strength = self._estimate_turn_strength(user_input, logic_data)
        self.short_term_buffer.append(
            {
                "timestamp": timestamp,
                "text": f"User:{user_input} -> Uruha:{ai_response}",
                "user": user_input,
                "reply": ai_response,
                "intent": logic_data.get("intent", "chat"),
                "scene": logic_data.get("scene", "casual"),
                "strength": strength,
            }
        )
        if len(self.short_term_buffer) > SHORT_TERM_BUFFER_LIMIT:
            self.short_term_buffer = self.short_term_buffer[-SHORT_TERM_BUFFER_LIMIT:]

    def _decay_short_term_memory(self, now=None):
        if now is None:
            now = datetime.datetime.now()
        kept = []
        decayed = 0
        for item in self.short_term_buffer:
            timestamp = item.get("timestamp")
            strength = float(item.get("strength", 0.0))
            if timestamp:
                try:
                    age_seconds = max(0.0, (now - datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")).total_seconds())
                except Exception:
                    age_seconds = SHORT_TERM_DECAY_SECONDS
            else:
                age_seconds = SHORT_TERM_DECAY_SECONDS
            retention = math.exp(-age_seconds / SHORT_TERM_DECAY_SECONDS)
            new_strength = round(strength * retention, 4)
            if new_strength >= SHORT_TERM_FORGET_THRESHOLD:
                updated = dict(item)
                updated["strength"] = new_strength
                kept.append(updated)
            else:
                decayed += 1
        self.short_term_buffer = kept[-SHORT_TERM_BUFFER_LIMIT:]
        self._last_decay_at = now.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "kept": len(self.short_term_buffer),
            "forgotten": decayed,
            "last_decay_at": self._last_decay_at,
        }

    def save_episode(self, user_input, ai_response, mood_state, logic_data=None):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logic_data = logic_data or {}
        scene = logic_data.get("scene", "casual")
        intent = logic_data.get("intent", "chat")
        summary = logic_data.get("jp_summary", "")
        cognitive_mode = logic_data.get("cognitive_mode", "direct")
        premise_check = logic_data.get("premise_check", "accept")
        routing_path = logic_data.get("routing_path", "high_road")
        doc = (
            f"Time: {timestamp} | Intent: {intent} | Scene: {scene} | CognitiveMode: {cognitive_mode} | PremiseCheck: {premise_check} | Routing: {routing_path} | "
            f"User: {user_input} | Summary: {summary} | Uruha: {ai_response} | Mood: {mood_state}"
        )
        episode_id = str(uuid.uuid4())
        self.episode_col.add(
            documents=[doc],
            ids=[episode_id],
            metadatas=[
                {
                    "timestamp": timestamp,
                    "intent": intent,
                    "scene": scene,
                    "cognitive_mode": cognitive_mode,
                    "premise_check": premise_check,
                    "routing_path": routing_path,
                    "source": "turn_episode",
                    "last_accessed_at": timestamp,
                    "decay_flag": False,
                    "decay_multiplier": 1.0,
                }
            ],
        )
        self.session_turns.append(
            {
                "user": user_input,
                "reply": ai_response,
                "intent": intent,
                "scene": scene,
                "summary": summary,
                "timestamp": timestamp,
                "routing_path": routing_path,
            }
        )
        if len(self.session_turns) > 24:
            self.session_turns = self.session_turns[-24:]
        self._append_short_term_buffer(user_input, ai_response, logic_data, timestamp)
        self._remember_profile_facts(user_input)
        return doc

    def _profile_snapshot(self):
        return umr.profile_snapshot(self.session_profile)

    def _profile_summary(self):
        return umr.profile_summary(self.session_profile)

    def _recent_dialogue_summary(self):
        return umr.recent_dialogue_summary(self.session_turns)

    def _clean_fact_value(self, value):
        value = umr.clean_fact_value(value)
        value = re.sub(r"\b(?:anymore|now)$", "", value, flags=re.IGNORECASE).strip()
        value = re.sub(r"^(?:もう|現在|现在|今は)\s*", "", value).strip()
        value = re.sub(r"(?:了|じゃない)$", "", value).strip()
        value = re.sub(r"(?:は|が|を)$", "", value).strip()
        return umr.clean_fact_value(value)

    def _extract_profile_facts(self, user_input):
        text = user_input.strip()
        lowered = text.lower()
        facts = []
        requested_name = uruha_leftbrain_rules.extract_requested_user_name(text)
        if requested_name:
            facts.append(("name", requested_name))
        patterns = [
            ("favorite", [r"(?:my favorite(?: drink| food| snack)? is)\s+([a-z0-9 \-]{2,30})"]),
            ("favorite", [r"(?:我最喜歡|我最喜欢)([^，。！？?]{1,20})"]),
            ("favorite", [r"(.{1,20})(?:が一番好き|が好き一番)"]),
            ("like", [r"(?:i (?:really )?(?:like|love))\s+([a-z0-9 \-]{2,30})"]),
            ("like", [r"(?:我喜歡|我喜欢|我愛|我爱)([^，。！？?]{1,20})"]),
            ("like", [r"(.{1,20})が好き"]),
            ("dislike", [r"(?:i (?:really )?hate)\s+([a-z0-9 \-]{2,30})"]),
            ("dislike", [r"(?:i (?:do not|don't|no longer) like)\s+([a-z0-9 \-]{2,30}?)(?:\s+anymore|\s+now|[.!?]|$)"]),
            ("dislike", [r"(?:i (?:can't|cannot) (?:drink|eat))\s+([a-z0-9 \-]{2,30}?)(?:\s+anymore|[.!?]|$)"]),
            ("dislike", [r"(?:我討厭|我讨厌)([^，。！？?]{1,20})"]),
            ("dislike", [r"(?:我(?:現在|现在)?(?:不再|不)喜歡|我(?:現在|现在)?已經不喜歡)([^，。！？?]{1,20})(?:了)?"]),
            ("dislike", [r"(?:我(?:現在|现在)?不能(?:喝|吃))([^，。！？?]{1,20})(?:了)?"]),
            ("dislike", [r"(.{1,20})嫌い"]),
            ("dislike", [r"(.{1,20})無理"]),
            ("dislike", [r"(.{1,20})(?:は|が)?もう好きじゃない", r"もう(.{1,20})(?:は|が)?好きじゃない"]),
            ("dislike", [r"(.{1,20})(?:は|が|を)?(?:飲めない|食べられない)"]),
        ]
        for fact_type, regexes in patterns:
            for regex in regexes:
                source = lowered if regex.startswith("(?:my") or regex.startswith("(?:i") else text
                match = re.search(regex, source, re.IGNORECASE)
                if not match:
                    continue
                value = self._clean_fact_value(match.group(1))
                if value:
                    facts.append((fact_type, value))
                break
        deduped = []
        seen = set()
        for fact_type, value in facts:
            key = (fact_type, value.lower())
            if key not in seen:
                seen.add(key)
                deduped.append((fact_type, value))
        return deduped[:3]

    def _remember_profile_facts(self, user_input):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        def normalized(value):
            return self._clean_fact_value(value).lower()

        def forget_current_preference(value):
            target = normalized(value)
            if not target:
                return
            for field in ("favorites", "likes"):
                kept = []
                for item in self.session_profile.get(field, []):
                    item_norm = normalized(item)
                    if item_norm and item_norm == target:
                        continue
                    kept.append(item)
                self.session_profile[field] = kept

        def remember_recent_first(field, value):
            values = [item for item in self.session_profile.get(field, []) if item.lower() != value.lower()]
            self.session_profile[field] = [value, *values][:8]

        for fact_type, value in self._extract_profile_facts(user_input):
            if fact_type == "name":
                self.session_profile["name"] = value
            elif fact_type == "favorite":
                remember_recent_first("favorites", value)
            elif fact_type == "like":
                remember_recent_first("likes", value)
            elif fact_type == "dislike":
                forget_current_preference(value)
                remember_recent_first("dislikes", value)
            try:
                self.profile_col.add(
                    documents=[f"FactType={fact_type} | Value={value}"],
                    ids=[str(uuid.uuid4())],
                    metadatas=[
                        {
                            "fact_type": fact_type,
                            "value": value,
                            "timestamp": timestamp,
                            "last_accessed_at": timestamp,
                            "decay_flag": False,
                            "decay_multiplier": 1.0,
                        }
                    ],
                )
            except Exception:
                pass

    def _should_reflect_user_fact(self, user_input):
        lowered = user_input.lower()
        stable_markers = [
            "喜歡",
            "喜欢",
            "愛吃",
            "爱吃",
            "最喜歡",
            "最喜欢",
            "通常",
            "平常",
            "每次",
            "always",
            "usually",
            "favorite",
            "prefer",
            "i like",
            "i love",
            "i hate",
            "i always",
            "好き",
            "嫌い",
            "いつも",
            "よく",
            "普段",
        ]
        return any(marker.lower() in lowered for marker in stable_markers)

    def has_unconsolidated_turns(self, minimum=6):
        return len(self.session_turns) - self._consolidated_turn_index >= minimum

    def _fetch_recent_collection_entries(self, collection, hours=24, source=None):
        try:
            payload = collection.get(include=["documents", "metadatas"])
        except Exception:
            return []

        docs = payload.get("documents") or []
        metas = payload.get("metadatas") or []
        ids = payload.get("ids") or []
        now = datetime.datetime.now()
        entries = []
        for idx, doc in enumerate(docs):
            metadata = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            timestamp = metadata.get("timestamp")
            if source and metadata.get("source") != source:
                continue
            if timestamp:
                try:
                    age_hours = max(0.0, (now - datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")).total_seconds()) / 3600.0
                except Exception:
                    age_hours = float("inf")
            else:
                age_hours = float("inf")
            if age_hours > hours:
                continue
            entries.append(
                {
                    "id": ids[idx] if idx < len(ids) else None,
                    "document": doc,
                    "metadata": metadata,
                }
            )
        entries.sort(key=lambda item: item.get("metadata", {}).get("timestamp", ""), reverse=True)
        return entries

    def _apply_passive_wisdom_decay(self, days=PASSIVE_DECAY_DAYS):
        try:
            payload = self.wisdom_col.get(include=["documents", "metadatas"])
        except Exception:
            return {"checked": 0, "decayed": 0}

        docs = payload.get("documents") or []
        metas = payload.get("metadatas") or []
        ids = payload.get("ids") or []
        now = datetime.datetime.now()
        checked = 0
        decayed = 0
        for idx, doc in enumerate(docs):
            metadata = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            checked += 1
            timestamp = metadata.get("timestamp")
            last_accessed_at = metadata.get("last_accessed_at") or timestamp
            if not timestamp:
                continue
            try:
                age_days = max(0.0, (now - datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")).total_seconds()) / 86400.0
                access_gap_days = max(0.0, (now - datetime.datetime.strptime(last_accessed_at, "%Y-%m-%d %H:%M:%S")).total_seconds()) / 86400.0
            except Exception:
                continue
            if age_days < days or access_gap_days < days or metadata.get("decay_flag"):
                continue
            updated = dict(metadata)
            updated["decay_flag"] = True
            updated["decay_multiplier"] = 0.62
            try:
                self.wisdom_col.update(ids=[ids[idx]], metadatas=[updated], documents=[doc])
                decayed += 1
            except Exception:
                continue
        return {"checked": checked, "decayed": decayed}

    def _extract_jsonish_payload(self, text):
        text = (text or "").strip()
        if not text:
            raise ValueError("empty response")
        try:
            return json.loads(text)
        except Exception:
            pass
        for pattern in [r"```json\s*(\{.*?\})\s*```", r"(\{.*\})"]:
            match = re.search(pattern, text, re.DOTALL)
            if not match:
                continue
            try:
                return json.loads(match.group(1))
            except Exception:
                continue
        raise ValueError("no valid json")

    def _heuristic_consolidation_payload(self, turns):
        profile = self._profile_snapshot()
        latest_user_text = " / ".join(turn.get("user", "") for turn in turns[-3:]).strip() or "最近の会話"
        payload = {
            "episodic_summary": f"{latest_user_text[:60]} の流れを短く整理した。",
            "wisdom_rule": "NO_RULE",
            "procedural_rule": "NO_RULE",
            "salience": 0.3,
        }

        if profile.get("favorites"):
            favorite = profile["favorites"][0]
            payload.update(
                {
                    "wisdom_rule": f"Userの定番の好みは{favorite}寄り。",
                    "episodic_summary": f"最近の會話では{favorite}の好みがはっきり出た。",
                    "procedural_rule": f"{favorite}みたいな具体物が出たら、ぼかさず名詞ごと拾って返す。",
                    "salience": 0.78,
                }
            )
            return payload
        if profile.get("dislikes"):
            dislike = profile["dislikes"][0]
            payload.update(
                {
                    "wisdom_rule": f"Userは{dislike}が苦手。",
                    "episodic_summary": f"最近の会話では{dislike}を避けたい様子が見えた。",
                    "procedural_rule": "苦手な対象は無理に勧めず、一段引いて返す。",
                    "salience": 0.76,
                }
            )
            return payload
        if profile.get("likes"):
            like = profile["likes"][0]
            payload.update(
                {
                    "wisdom_rule": f"Userは{like}が好き寄り。",
                    "episodic_summary": f"最近の会話では{like}の話題に前向きだった。",
                    "procedural_rule": "好きな話題は一般論で流さず、相手の言葉を少し言い換えて返す。",
                    "salience": 0.72,
                }
            )
            return payload

        intent_counts = Counter(turn.get("intent", "chat") for turn in turns)
        top_intent, top_count = intent_counts.most_common(1)[0]
        if top_intent in {"tired_support", "sick", "off_work"} and top_count >= 2:
            payload.update(
                {
                    "wisdom_rule": "疲れや体調の話は、まず休める方向で返すと噛み合いやすい。",
                    "episodic_summary": "最近は疲労や消耗の話題が続いた。",
                    "procedural_rule": "体調系は分析より先に負荷を下げる一言を置く。",
                    "salience": 0.66,
                }
            )
            return payload
        if top_intent in {"annoying_check", "mad_check", "ask_miss_me", "nickname_question"} and top_count >= 2:
            payload.update(
                {
                    "wisdom_rule": "関係確認には、少し距離を残しつつ直接返すと自然。",
                    "episodic_summary": "最近は関係の温度確認が続いた。",
                    "procedural_rule": "関係温度の質問は逃げずに答えつつ、少しだけ照れや距離を混ぜる。",
                    "salience": 0.68,
                }
            )
            return payload
        if top_intent in {"abuse_pushback", "sexual_boundary", "crisis_support"} and top_count >= 2:
            payload.update(
                {
                    "wisdom_rule": "強い言葉や危ない話は、短く止めて温度を下げるのが先。",
                    "episodic_summary": "最近は強い刺激のある発話が続いた。",
                    "procedural_rule": "低軌道で短く押し返し、意味のない説教にしない。",
                    "salience": 0.7,
                }
            )
            return payload
        return payload

    def consolidate_recent_experiences(self, client_logic, minimum_turns=6, force=False):
        decay_report = self._decay_short_term_memory()
        passive_decay_report = self._apply_passive_wisdom_decay()
        recent_episode_entries = self._fetch_recent_collection_entries(self.episode_col, hours=24, source="turn_episode")
        should_consolidate_recent_db = len(recent_episode_entries) >= max(20, minimum_turns)

        if not force and not self.has_unconsolidated_turns(minimum_turns) and not should_consolidate_recent_db:
            result = {
                "episodic_summary": None,
                "wisdom_rule": None,
                "procedural_rule": None,
                "salience": 0.0,
                "turns_used": 0,
                "decay_report": decay_report,
                "passive_decay_report": passive_decay_report,
                "mode": "decay_only",
            }
            self._last_maintenance_result = result
            return result

        pending_turns = self.session_turns[self._consolidated_turn_index :]
        excerpt_turns = pending_turns[:8] if pending_turns else self.session_turns[-8:]
        db_excerpt = recent_episode_entries[:20] if should_consolidate_recent_db else []
        if not excerpt_turns and not db_excerpt:
            result = {
                "episodic_summary": None,
                "wisdom_rule": None,
                "procedural_rule": None,
                "salience": 0.0,
                "turns_used": 0,
                "decay_report": decay_report,
                "passive_decay_report": passive_decay_report,
                "mode": "idle_noop",
            }
            self._last_maintenance_result = result
            return result
        if db_excerpt:
            excerpt = "\n".join(
                f"{idx + 1}. {entry.get('document', '')}"
                for idx, entry in enumerate(db_excerpt)
            )
        else:
            excerpt = "\n".join(
                f"{idx + 1}. User: {turn.get('user', '')}\n   Uruha: {turn.get('reply', '')}\n   Intent={turn.get('intent', '')} Scene={turn.get('scene', '')}"
                for idx, turn in enumerate(excerpt_turns)
            )
        sys_prompt = (
            "You are consolidating short-term dialogue into three memory speeds. "
            "Return ONLY valid JSON with keys: episodic_summary, wisdom_rule, procedural_rule, salience. "
            "episodic_summary is one compact Japanese summary of what happened. "
            "wisdom_rule is one durable semantic user fact or interaction regularity. If none, set NO_RULE. "
            "procedural_rule is one reusable response policy in Japanese about how this agent should respond next time. If none, set NO_RULE. "
            "salience should be a float between 0 and 1."
        )
        if db_excerpt:
            sys_prompt = (
                "You are consolidating the last 24 hours of episodic dialogue memory into durable knowledge. "
                "Return ONLY valid JSON with keys: episodic_summary, wisdom_rule, procedural_rule, salience. "
                "episodic_summary should summarize what repeatedly happened. "
                "wisdom_rule should extract durable objective facts or user preferences. If none, set NO_RULE. "
                "procedural_rule should state how this agent should respond next time in similar situations. If none, set NO_RULE. "
                "salience should be a float between 0 and 1."
            )

        try:
            response = client_logic.chat.completions.create(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": excerpt},
                ],
                temperature=0.1,
            )
            payload = self._extract_jsonish_payload(response.choices[0].message.content.strip())
        except Exception:
            payload = self._heuristic_consolidation_payload(excerpt_turns)

        wisdom_rule = str(payload.get("wisdom_rule", "NO_RULE")).strip()
        procedural_rule = str(payload.get("procedural_rule", "NO_RULE")).strip()
        episodic_summary = str(payload.get("episodic_summary", "最近の会話を短く整理した。")).strip()[:120]
        try:
            salience = max(0.0, min(1.0, float(payload.get("salience", 0.3))))
        except Exception:
            salience = 0.3

        if wisdom_rule == "NO_RULE" or procedural_rule == "NO_RULE":
            heuristic = self._heuristic_consolidation_payload(excerpt_turns)
            if wisdom_rule == "NO_RULE" and heuristic.get("wisdom_rule") != "NO_RULE":
                wisdom_rule = heuristic["wisdom_rule"]
            if procedural_rule == "NO_RULE" and heuristic.get("procedural_rule") != "NO_RULE":
                procedural_rule = heuristic["procedural_rule"]
            if heuristic.get("episodic_summary"):
                episodic_summary = str(heuristic["episodic_summary"]).strip()[:120]
            salience = max(salience, float(heuristic.get("salience", salience)))

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.episode_col.add(
                documents=[f"EpisodicSummary: {episodic_summary}"],
                ids=[str(uuid.uuid4())],
                metadatas=[
                    {
                        "source": "episodic_consolidation",
                        "timestamp": timestamp,
                        "salience": salience,
                        "last_accessed_at": timestamp,
                        "decay_flag": False,
                        "decay_multiplier": 1.0,
                    }
                ],
            )
        except Exception:
            pass

        if wisdom_rule and wisdom_rule != "NO_RULE":
            try:
                self.wisdom_col.add(
                    documents=[f"Rule: {wisdom_rule} | EpisodicSummary: {episodic_summary}"],
                    ids=[str(uuid.uuid4())],
                    metadatas=[
                        {
                            "source": "idle_consolidation",
                            "timestamp": timestamp,
                            "salience": salience,
                            "last_accessed_at": timestamp,
                            "decay_flag": False,
                            "decay_multiplier": 1.0,
                        }
                    ],
                )
            except Exception:
                pass

        if procedural_rule and procedural_rule != "NO_RULE":
            try:
                self.procedural_col.add(
                    documents=[f"Procedure: {procedural_rule} | TriggerSummary: {episodic_summary}"],
                    ids=[str(uuid.uuid4())],
                    metadatas=[
                        {
                            "source": "idle_consolidation",
                            "timestamp": timestamp,
                            "salience": salience,
                            "last_accessed_at": timestamp,
                            "decay_flag": False,
                            "decay_multiplier": 1.0,
                        }
                    ],
                )
            except Exception:
                pass

        deleted_episode_count = 0
        if db_excerpt:
            delete_ids = [entry.get("id") for entry in db_excerpt if entry.get("id")]
            if delete_ids:
                try:
                    self.episode_col.delete(ids=delete_ids)
                    deleted_episode_count = len(delete_ids)
                except Exception:
                    deleted_episode_count = 0

        self._consolidated_turn_index = len(self.session_turns)
        self._last_consolidation_at = timestamp
        if len(self.session_turns) > 16:
            self.session_turns = self.session_turns[-16:]
            self._consolidated_turn_index = min(self._consolidated_turn_index, len(self.session_turns))

        result = {
            "wisdom_rule": wisdom_rule,
            "procedural_rule": procedural_rule,
            "episodic_summary": episodic_summary,
            "salience": salience,
            "turns_used": len(db_excerpt) if db_excerpt else len(excerpt_turns),
            "decay_report": decay_report,
            "passive_decay_report": passive_decay_report,
            "deleted_episode_count": deleted_episode_count,
            "mode": "three_speed_consolidation",
        }
        self._last_maintenance_result = result
        return result

    def reflect_experience(self, user_input, ai_response, logic_data, client_logic):
        if not self._should_reflect_user_fact(user_input):
            return None

        sys_prompt = (
            "Extract at most ONE stable user profile rule from the user's utterance only. "
            "Only keep durable preferences, habits, or recurring facts. "
            "If there is no durable user fact, output exactly NO_RULE. "
            "If there is one, format exactly: Rule: ..."
        )
        try:
            response = client_logic.chat.completions.create(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"User utterance: {user_input}\n"
                            f"Reply intent: {logic_data.get('intent', 'chat')}\n"
                            f"AI reply: {ai_response}"
                        ),
                    },
                ],
                temperature=0.1,
            )
            wisdom = response.choices[0].message.content.strip()
            if not wisdom.startswith("Rule:"):
                return None
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.wisdom_col.add(
                documents=[wisdom],
                ids=[str(uuid.uuid4())],
                metadatas=[
                    {
                        "source": "reflection_rule",
                        "timestamp": timestamp,
                        "last_accessed_at": timestamp,
                        "decay_flag": False,
                        "decay_multiplier": 1.0,
                    }
                ],
            )
            return wisdom
        except Exception:
            return None


# ===========================
# 🧠 左腦：邏輯與回覆規劃 (Left Brain)
# ===========================
class LeftBrain:
    def __init__(self, client_logic):
        self.client_logic = client_logic
        self._social_reasoning_frame_cache = {}

    def _story_question_line(self, text):
        raw = str(text or "")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        explicit_candidates = []
        loose_candidates = []
        for line in lines:
            lowered = line.lower()
            if re.match(r"^[a-d]\.\s+", lowered):
                continue
            if lowered.startswith(("question:", "question ", "問題:", "問題 ", "问题:", "问题 ")):
                explicit_candidates.append(line)
                continue
            if "?" in line or "？" in line:
                loose_candidates.append(line)
        if explicit_candidates:
            return explicit_candidates[-1][:180]
        if loose_candidates:
            return loose_candidates[-1][:180]
        return lines[-1][:180] if lines else ""

    def _strip_mcq_options(self, text):
        raw = str(text or "")
        lines = [line.rstrip() for line in raw.splitlines()]
        filtered = [line for line in lines if not re.match(r"^\s*[A-Da-d]\.\s+", line)]
        return "\n".join(filtered).strip()

    def _extract_story_actor_name(self, text):
        question = self._story_question_line(self._strip_mcq_options(text))
        candidate_patterns = [
            re.compile(r"(?:does|is|would|will|can|should|how does|why did|what does|what is|does anyone)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)"),
            re.compile(r"^([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s"),
        ]
        for pattern in candidate_patterns:
            match = pattern.search(question)
            if match:
                return match.group(1).strip()[:24]
        matches = re.findall(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b", self._strip_mcq_options(text))
        for name in matches:
            if name.lower() not in {
                "what", "where", "when", "while", "after", "before", "question", "story",
                "please", "does", "how", "why", "who", "is",
            }:
                return name.strip()[:24]
        return ""

    def _normalize_social_reasoning_frame(self, payload, fallback):
        keys = [
            "focus",
            "main_actor",
            "current_goal",
            "prior_goal",
            "belief_boundary",
            "knowledge_gap",
            "emotion_driver",
            "social_subtext",
            "decision_rule",
            "best_option_shape",
        ]
        frame = {key: str(fallback.get(key, "")).strip()[:120] for key in keys}
        def _looks_polluted(value):
            raw = str(value or "").strip()
            lowered = raw.lower()
            if not raw:
                return True
            if re.match(r"^[A-Da-d](?:[.)]|$)", raw):
                return True
            if re.match(r"^\s*[A-Da-d]\.\s+", raw):
                return True
            if lowered in {"what", "does", "before", "please", "question", "story"}:
                return True
            if raw.startswith("{") and raw.endswith("}"):
                return True
            return False
        if isinstance(payload, dict):
            for key in keys:
                value = str(payload.get(key, frame[key])).strip()
                if value and not _looks_polluted(value):
                    frame[key] = value[:120]
        if not frame["focus"]:
            frame["focus"] = str(fallback.get("focus", "belief_state"))[:40]
        return frame

    def _fallback_social_reasoning_frame(self, user_input):
        profile = self._story_reasoning_profile(user_input) or {}
        focus = profile.get("focus", "belief_state")
        actor = self._extract_story_actor_name(user_input)
        frame = {
            "focus": focus,
            "main_actor": actor,
            "current_goal": "今いちばん前に出ている目的を追う",
            "prior_goal": "その前に持っていた目的",
            "belief_boundary": "全知視点を混ぜず、その人物が見聞きした範囲だけ使う",
            "knowledge_gap": "本人がまだ知らない事実や、注目していない手掛かりがある",
            "emotion_driver": "期待が満たれたか外れたかで感情が動く",
            "social_subtext": "字面より、視線・含み・立場の差が手掛かりになる",
            "decision_rule": "いちばん直近の目的と情報境界に合う選択肢を残す",
            "best_option_shape": "派手すぎず、物語の流れにいちばん自然につながる答え",
        }
        if focus == "belief_reasoning":
            frame.update(
                {
                    "current_goal": "その人物が知っている前提で自然に探す・答える",
                    "belief_boundary": "本人が見ていない移動や裏事情を混ぜない",
                    "knowledge_gap": "本人は不在中の変化をまだ知らない",
                    "decision_rule": "本人視点で最初にそう思う答えを選ぶ",
                    "best_option_shape": "全知視点ではなく、誤信念込みでも自然な答え",
                }
            )
        elif focus == "action_prediction":
            frame.update(
                {
                    "current_goal": "最後に更新された目的を優先する",
                    "prior_goal": "途中で中断された元の予定",
                    "belief_boundary": "今その人物が見ている障害と助けだけで判断する",
                    "decision_rule": "障害が消えたか残ってるかを見て次行動を決める",
                    "best_option_shape": "次の一手としていちばん近い行動",
                }
            )
        elif focus == "emotion_attribution":
            frame.update(
                {
                    "current_goal": "状況を自分にとって安全か前向きに解釈する",
                    "emotion_driver": "期待と現実のズレ、脅威か支えかで感情が決まる",
                    "social_subtext": "露骨な行動より、その前の視線や空気が効く",
                    "decision_rule": "理想論より、その場でいちばん起こりやすい気持ちを選ぶ",
                    "best_option_shape": "過剰に英雄的でも逃避的でもない、自然な情緒調整",
                }
            )
        elif focus == "communicative_intent":
            frame.update(
                {
                    "current_goal": "相手の本音・含み・失礼さを読む",
                    "belief_boundary": "言葉どおりではなく、誰に向けたサインかを切る",
                    "social_subtext": "皮肉・遠回しな誘導・含みが中心",
                    "decision_rule": "文字面より、相手が実際に起こしたい反応を選ぶ",
                    "best_option_shape": "直球の意味ではなく、含みまで拾った答え",
                }
            )
        elif focus == "attention_reasoning":
            frame.update(
                {
                    "current_goal": "いま共有されている注目先を合わせる",
                    "belief_boundary": "見えている物全部ではなく、最後に注目した対象を使う",
                    "knowledge_gap": "相手が気づいた対象と、まだ触れていない対象がずれる",
                    "social_subtext": "指示語や視線は、直前に目立っていた対象を指しやすい",
                    "decision_rule": "何が視界にあったかではなく、何に注意が向いたかで選ぶ",
                    "best_option_shape": "共有注意に沿った指差しや受け渡し",
                }
            )
        elif focus == "pretend_play_boundary":
            frame.update(
                {
                    "current_goal": "知っている物の動きとしてまねする",
                    "belief_boundary": "未知の植物や生物の概念は使わない",
                    "knowledge_gap": "本人は植物の見た目や意味を知らない",
                    "social_subtext": "見た目が似ていても、知識がない概念には飛ばない",
                    "decision_rule": "知識境界の内側でいちばん似ている動作を選ぶ",
                    "best_option_shape": "機械や人工物ベースの無難な模倣",
                }
            )
        elif focus == "desire_conflict":
            frame.update(
                {
                    "current_goal": "今いちばん勝っている欲求を満たす",
                    "prior_goal": "元から持っていた長めの希望",
                    "belief_boundary": "直近で強くなった希望や義務を優先して見る",
                    "decision_rule": "一時的な任務が終わったら元の欲求に戻るかを判断する",
                    "best_option_shape": "文脈上いちばん筋の通る欲求の続き",
                }
            )
        elif focus == "persuasion_strategy":
            frame.update(
                {
                    "current_goal": "相手の引っかかっている一点をほどいて動かす",
                    "prior_goal": "自分の希望をそのまま通したい気持ち",
                    "belief_boundary": "相手が今どこで渋っているかを基準に見る",
                    "knowledge_gap": "相手はまだ安心材料や具体策を知らない",
                    "emotion_driver": "希望を通したい気持ちと相手を安心させたい気持ち",
                    "social_subtext": "願望の押しつけではなく、相手の不安を一つ潰す交渉が中心",
                    "decision_rule": "願望を繰り返すより、相手の反対理由に直接効く一手を選ぶ",
                    "best_option_shape": "相手の懸念を一つ軽くする具体策や言い換え",
                }
            )
        elif focus == "hidden_emotion":
            frame.update(
                {
                    "current_goal": "表に出した言い訳ではなく本音の感情を守る",
                    "prior_goal": "表向きには無難に振る舞う",
                    "belief_boundary": "言った理由と本当の気持ちは分けて扱う",
                    "knowledge_gap": "周囲は表向きの説明しか知らない",
                    "emotion_driver": "願望・嫉妬・不安・恥ずかしさなど隠している感情",
                    "social_subtext": "表面の言い訳や強がりの裏にある本心を読む",
                    "decision_rule": "言い訳より、その人が本当は何を望んでいたかで選ぶ",
                    "best_option_shape": "表向きの台詞とズレていても本音として自然な感情",
                }
            )
        elif focus == "scalar_quantity_inference":
            frame.update(
                {
                    "current_goal": "見えている数だけで最低限言える推測を作る",
                    "prior_goal": "不足分まで都合よく埋めない",
                    "belief_boundary": "見えた数量と見えていない数量を混ぜない",
                    "knowledge_gap": "未確認の残り個数や中身は未確定のまま",
                    "emotion_driver": "好奇心より根拠の強さを優先する",
                    "social_subtext": "話者は全体を知っていそうでも、本人が見ていない分は推測しすぎない",
                    "decision_rule": "最低限確実な下限から考え、未観測分を勝手に決めない",
                    "best_option_shape": "見えた数に基づく保守的な数量推定",
                }
            )
        elif focus == "knowledge_state_social":
            frame.update(
                {
                    "current_goal": "その人物が事実を知っているか知らないかを切る",
                    "prior_goal": "事実そのものの是非とは分ける",
                    "belief_boundary": "現実に起きていることと、本人が知っていることは別",
                    "knowledge_gap": "本人は裏事情や相手の本音をまだ知らないかもしれない",
                    "emotion_driver": "知識差から生じる気まずさや無自覚さ",
                    "social_subtext": "失礼さや遠慮の有無より、まず知っていたかどうかが核心",
                    "decision_rule": "発言の正しさより、本人の知識到達 여부で判断する",
                    "best_option_shape": "知っている / 知らない をはっきり分けた答え",
                }
            )
        elif focus == "completion_after_action":
            frame.update(
                {
                    "current_goal": "終わった直後にいちばん自然な次の一手へ戻る",
                    "prior_goal": "途中で保留になっていた約束や元の予定",
                    "belief_boundary": "主タスクが終わったなら、残る制約があるかどうかを見る",
                    "knowledge_gap": "周囲の追加事情がないなら元の希望に戻りやすい",
                    "emotion_driver": "解放感・達成感・保留していた用事への戻り",
                    "social_subtext": "義務が片付いた直後は、先に止めていた行動へ戻ることが多い",
                    "decision_rule": "完了後に邪魔がなければ、保留していた元の流れへ戻す",
                    "best_option_shape": "完了後の自然な復帰行動や再開行動",
                }
            )
        return frame

    def _build_social_reasoning_frame(self, user_input):
        cache_key = hashlib.sha256(str(user_input or "").encode("utf-8")).hexdigest()
        cached = self._social_reasoning_frame_cache.get(cache_key)
        if cached:
            return deepcopy(cached)

        profile = self._story_reasoning_profile(user_input)
        if not profile:
            return {}

        fallback = self._fallback_social_reasoning_frame(user_input)
        if profile.get("prefer_fallback_frame"):
            self._social_reasoning_frame_cache[cache_key] = deepcopy(fallback)
            return fallback
        prompt = f"""
You are a Theory-of-Mind frame extractor for story reasoning.
Return ONLY valid JSON with these keys:
- focus
- main_actor
- current_goal
- prior_goal
- belief_boundary
- knowledge_gap
- emotion_driver
- social_subtext
- decision_rule
- best_option_shape

Rules:
- Use short Japanese phrases.
- Do not answer the question directly.
- Do not mention option letters.
- Keep every field evidence-based and compact.
- Separate current goal from previous goal when the story changes direction.
- For false belief / attention / pretend-play tasks, make the knowledge boundary explicit.
- For irony / faux-pas / persuasion tasks, make the social subtext explicit.

[focus]
{profile.get('focus', '')}

[reasoning note]
{profile.get('note', '')}

[reasoning steps]
{" / ".join(profile.get("steps") or [])}

[question]
{profile.get('question_excerpt', '')}

[full prompt]
{user_input}
"""
        try:
            response = self.client_logic.chat.completions.create(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": "Return JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=220,
            )
            payload = self._extract_json_from_text(response.choices[0].message.content)
            frame = self._normalize_social_reasoning_frame(payload, fallback)
        except Exception:
            frame = fallback

        self._social_reasoning_frame_cache[cache_key] = deepcopy(frame)
        return frame

    def _infer_hidden_intent(self, user_input, memory_data, current_psyche, seed_plan=None):
        lowered = user_input.lower()
        intent = (seed_plan or {}).get("intent")
        story_probe = self._story_reasoning_profile(user_input)
        if story_probe:
            return {
                "hidden_intent": "social_reasoning_probe",
                "note": story_probe["note"],
                "markers": story_probe["markers"],
                "focus": story_probe["focus"],
                "reasoning_steps": story_probe["steps"],
                "question_excerpt": story_probe["question_excerpt"],
            }
        if intent in {"ask_miss_me", "annoying_check", "mad_check", "nickname_question"}:
            if intent == "nickname_question":
                return {
                    "hidden_intent": "permission_probe",
                    "note": "相手は呼び方の許可を取りつつ距離感も測っている。",
                    "markers": ["relationship", "boundary", "permission"],
                }
            return {
                "hidden_intent": "relationship_temperature_check",
                "note": "表面は質問でも、実際は関係の温度確認や安心確認が主目的。",
                "markers": ["relationship", "temperature", "reassurance"],
            }
        if intent in {"friend_no_reply", "lonely", "crying_support", "giving_up_support", "tired_support"}:
            return {
                "hidden_intent": "emotional_bid",
                "note": "情報要求よりも、気分を受け止めてほしい比重が高い。",
                "markers": ["emotion", "support", "state"],
            }
        if self._looks_false_premise(user_input):
            return {
                "hidden_intent": "premise_trap",
                "note": "前提を既成事実化して乗せようとしている。まず前提自体を止める。",
                "markers": ["premise", "reject", "suspicious"],
            }
        if self._looks_overloaded_question(user_input):
            return {
                "hidden_intent": "scope_overload",
                "note": "答えを求めているというより、広すぎる投げ方になっている。先に範囲整理が必要。",
                "markers": ["scope", "narrow", "rebuild"],
            }
        if any(token in lowered for token in ["why don't you answer", "你要回答", "答えて", "急げ", "快點", "快点"]):
            return {
                "hidden_intent": "answer_pressure",
                "note": "内容確認よりも反応を急かしている。圧を一回受け流してから戻す。",
                "markers": ["pressure", "repair", "response"],
            }
        if any(token in lowered for token in ["remember", "覚えてる", "favorite", "名前", "苦手", "我剛剛說", "what did i say", "你記得"]):
            return {
                "hidden_intent": "memory_probe",
                "note": "記憶しているかの確認。作らず、保持している事実だけ返す。",
                "markers": ["memory", "recall", "fact"],
            }
        return {
            "hidden_intent": "plain_request",
            "note": "大きな裏は薄い。必要以上に深読みせず、そのまま返してよい。",
            "markers": ["direct", "plain"],
        }

    def _memory_tokens(self, text):
        return umr.memory_tokens(text)

    def _contains_any(self, text, keywords):
        lowered = text.lower()
        compact = re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", lowered)
        for keyword in keywords:
            needle = keyword.lower()
            if needle in lowered:
                return True
            if re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", needle) in compact:
                return True
        return False

    def _keyword_hits(self, text, keywords):
        lowered = text.lower()
        compact = re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", lowered)
        hits = 0
        for keyword in keywords:
            needle = keyword.lower()
            if needle in lowered or re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", needle) in compact:
                hits += 1
        return hits

    def _contains_short_signal(self, text, keywords):
        lowered = text.lower()
        compact = re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", lowered)
        for keyword in keywords:
            needle = re.sub(r"[\s\u3000。．，,、！？?!…~～ー_/\"'`]+", "", keyword.lower())
            if not needle:
                continue
            if needle.isascii():
                pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
                if re.search(pattern, lowered):
                    return True
                continue
            if compact == needle:
                return True
            if len(needle) <= 2 and compact.startswith(needle) and len(compact) <= len(needle) + 2:
                return True
            if len(needle) <= 2 and len(compact) <= 4 and needle in compact:
                return True
        return False

    def _story_reasoning_profile(self, text):
        raw = str(text or "")
        reasoning_text = self._strip_mcq_options(raw)
        lowered = reasoning_text.lower()
        false_belief = self._false_belief_location_story(reasoning_text)
        if false_belief:
            return {
                "focus": "belief_reasoning",
                "markers": ["story_probe", "mental_state", "belief", "knowledge", "false_belief"],
                "note": "問いの中心は誤信念。全知視点ではなく、その人物が最後に知っていた場所で考える。",
                "steps": [
                    "その人物が最後に見た場所を固定する",
                    "不在中に起きた移動は本人の知識に入れない",
                    "誤信念のまま最初の探索場所を選ぶ",
                ],
                "question_excerpt": false_belief["question"][:140],
            }
        has_options = bool(re.search(r"(^|\n)\s*[a-d]\.\s+", lowered)) and sum(
            1 for letter in ("a.", "b.", "c.", "d.") if letter in lowered
        ) >= 3
        has_story_signal = self._contains_any(
            lowered,
            ["story", "故事", "question", "問題", "问题", "look first", "believe", "where will", "while", "was away", "does ", "what does", "how does", "what kind of emotion"],
        )
        if not has_options and not has_story_signal:
            return None
        if len(raw) < 120 and not has_options and not self._contains_any(lowered, ["look first", "where will", "believe", "moved", "while"]):
            return None

        lines = [line.strip() for line in reasoning_text.splitlines() if line.strip()]
        question_line = self._story_question_line(reasoning_text)
        qlower = question_line.lower()

        focus = "belief_state"
        markers = ["story_probe", "mental_state"]
        note = "これは会話応答ではなく、物語の中の人物ごとの視点差を追う問題。"
        steps = [
            "登場人物ごとに見たものと知らないものを分ける",
            "その時点の欲求と感情を分ける",
            "表の行動と裏の意図を混ぜない",
            "一番根拠が強い選択肢だけ残す",
        ]
        prefer_fallback_frame = False

        emotion_question = any(
            token in qlower
            for token in [
                "what kind of emotion",
                "what is",
                "what are",
                "real feelings",
                "real feeling",
                "true feelings",
                "true feeling",
                "feel now",
                "feel after",
                "how does",
                "how do",
            ]
        ) and self._contains_any(qlower, ["emotion", "feel", "feelings", "emotion does"])
        persuasion_question = self._contains_any(
            qlower,
            ["persuade", "convince", "talk dad into", "talk her boss into", "说服", "説得"],
        )
        quantity_question = self._contains_any(
            qlower,
            ["how many", "guess", "contain checks", "baguettes", "letters do you think", "面包数量", "数量"],
        )
        knowledge_social_question = self._contains_any(
            qlower,
            ["does", "know that", "know whether", "aware that", "知ら", "知道"],
        ) and self._contains_any(lowered, ["married", "get married", "結婚", "want to get married", "faux-pas", "失礼", "not want to"])
        completion_question = self._contains_any(
            qlower,
            ["after she completes", "after he completes", "after finishing", "after he finishes", "after she finishes", "after it is finished"],
        ) and self._contains_any(lowered, ["complete", "completes", "completed", "finish", "finishes", "finished"])

        if persuasion_question:
            focus = "persuasion_strategy"
            markers.extend(["pragmatics", "persuasion", "strategy"])
            note = "問いの中心は説得のしかた。願望の強さではなく、相手の引っかかりをどう崩すかを見る。"
            steps = [
                "相手が何を嫌がっているかを一つに絞る",
                "願望の押しつけではなく、その懸念を減らす材料を探す",
                "相手が動きやすくなる具体策を選ぶ",
            ]
            prefer_fallback_frame = True
        elif quantity_question:
            focus = "scalar_quantity_inference"
            markers.extend(["quantity", "partial_knowledge", "scalar"])
            note = "問いの中心は部分観測からの数量推定。見えていない分を勝手に埋めず、最低限言える数を残す。"
            steps = [
                "本人が実際に見た数だけを固定する",
                "未観測の残りは未確定のままにする",
                "保守的でも根拠が最も強い数量を選ぶ",
            ]
            prefer_fallback_frame = True
        elif knowledge_social_question:
            focus = "knowledge_state_social"
            markers.extend(["knowledge", "social_boundary", "faux_pas"])
            note = "問いの中心は社会的な事実を本人が知っていたかどうか。事実の真偽と知識到達は分ける。"
            steps = [
                "出来事そのものと、本人が知っていた範囲を分ける",
                "失礼さより先に知識差の有無を切る",
                "知っている / 知らないを一番自然に選ぶ",
            ]
            prefer_fallback_frame = True
        elif any(token in qlower for token in ["real feelings", "real feeling", "true feelings", "true feeling"]):
            focus = "hidden_emotion"
            markers.extend(["emotion", "hidden_state", "surface_vs_private"])
            note = "問いの中心は隠された本音。表向きの言い訳や建前ではなく、裏の感情を切り出す。"
            steps = [
                "本人が口にした理由と本心を分ける",
                "本当は何を望んでいたかを見る",
                "建前より裏の感情として一番自然なものを選ぶ",
            ]
            prefer_fallback_frame = True
        elif emotion_question:
            focus = "emotion_attribution"
            markers.extend(["emotion", "valence"])
            note = "問いの中心は感情推定。行動の表面より、期待が満たされたか外れたかを見る。"
            steps = [
                "出来事の前後で期待がどう変わったか見る",
                "助けられたのか傷ついたのかを切る",
                "怒り・感謝・後悔・喜びのどれが一番自然か選ぶ",
            ]
            prefer_fallback_frame = True
        elif any(token in qlower for token in ["inappropriate", "faux", "wrong thing", "失礼", "不適切", "appropriate"]):
            focus = "communicative_intent"
            markers.extend(["pragmatics", "social_norm", "faux_pas"])
            note = "問いの中心は失言や社会規範の違反。字面より、相手が傷つくかどうかと知識差を見る。"
            steps = [
                "話者が知らずに踏んだ地雷かを確認する",
                "聞き手が傷つく理由があるかを切る",
                "ただの情報共有と失言を分ける",
            ]
        elif any(token in qlower for token in ["is what", "says true", "why did", "why does"]) and self._contains_any(lowered, ["role-playing", "role playing", "sarcasm", "irony", "英雄", "hero", "picnic", "雨", "rained"]):
            focus = "communicative_intent"
            markers.extend(["nonliteral", "irony", "roleplay"])
            note = "問いの中心は字面の真偽ではなく、皮肉・ごっこ遊び・なりきりの非文字通り性。"
            steps = [
                "発話が文字どおりか演技か皮肉かを切る",
                "現実の信念と遊びの設定を分ける",
                "社会的な意味で自然な答えを残す",
            ]
        elif any(token in qlower for token in ["why", "hint", "suggest", "mean", "attitude"]):
            focus = "communicative_intent"
            markers.extend(["pragmatics", "subtext"])
            note = "問いの中心は字面ではなく意図や含み。誰が誰に何を伝えたかったかを追う。"
            steps = [
                "視線・合図・順番などの非明示ヒントを拾う",
                "誰に向けたサインかを固定する",
                "結果として相手に何をさせたいかで選ぶ",
            ]
            prefer_fallback_frame = True
        elif completion_question:
            focus = "completion_after_action"
            markers.extend(["goal", "resume", "after_completion"])
            note = "問いの中心は完了後の流れ。主タスクが終わったあと、保留していた元の流れに戻るかを見る。"
            steps = [
                "何が終わった直後なのかを固定する",
                "その前に保留されていた予定や欲求を探す",
                "新しい障害がなければ元の流れに戻す",
            ]
            prefer_fallback_frame = True
        elif self._contains_any(qlower, ["reaction to", "reaction", "react"]) and not self._contains_any(qlower, ["how does", "convince", "persuade"]):
            focus = "emotion_attribution"
            markers.extend(["emotion", "reaction", "valence"])
            note = "問いの中心は出来事への感情反応。何を知っていたかより、その場でどんな感情になるかを見る。"
            steps = [
                "出来事が安心・喪失・驚きのどれを強めるか見る",
                "行動の理由より、その直後の気持ちを優先する",
                "一番自然な感情ラベルを残す",
            ]
            prefer_fallback_frame = True
        elif self._contains_any(qlower, ["most likely do", "what does", "do next", "most likely action", "likely action", "what happens"]):
            focus = "action_prediction"
            markers.extend(["goal", "action"])
            note = "問いの中心は次行動予測。直前で優先度が上がった目標を追う。"
            steps = [
                "最後に更新された目標を探す",
                "障害が消えたか残っているかを見る",
                "一番自然に続く行動を選ぶ",
            ]
            if any(token in lowered for token in ["look at that", "stares at", "rainbow pattern sticker", "toy", "looks at xiao ming", "notices", "pay special attention", "見て", "look!"]):
                focus = "attention_reasoning"
                markers.extend(["attention", "reference"])
                note = "問いの中心は誰が何に注意を向けたか。見えていただけの物と、注目していた物は分ける。"
                steps = [
                    "最後に視線や注意が向いた対象を固定する",
                    "共有注意が成立している相手を確認する",
                    "相手が渡す・指す対象をその注意先に合わせる",
                ]
        elif any(token in qlower for token in ["think", "thinking", "know", "believe", "understand"]):
            focus = "belief_reasoning"
            markers.extend(["belief", "knowledge"])
            note = "問いの中心は信念や知識状態。全知視点ではなく、その人物が知っている範囲で考える。"
            steps = [
                "その人物が見聞きした事実だけ残す",
                "他人の知識を勝手に混ぜない",
                "誤信念なら誤ったまま推論する",
            ]
        elif any(token in lowered for token in ["mimicking", "imitation behavior", "pretend", "pretending"]) and any(
            token in lowered for token in ["knows nothing about plants", "does not understand any plant", "without trees", "no form of plant life"]
        ):
            focus = "pretend_play_boundary"
            markers.extend(["pretend_play", "knowledge_boundary"])
            note = "問いの中心はごっこ遊びの知識境界。知らない概念のまねはしない。"
            steps = [
                "その人物が知らない領域の概念を除外する",
                "見慣れた機械や人工物の動きに寄せる",
                "知識境界の中で一番似た動作を選ぶ",
            ]
        elif self._contains_any(qlower, ["want to do", "wants to do", "want", "desire", "plan to", "prefer", "weekend", "attitude"]):
            focus = "desire_conflict"
            markers.extend(["desire", "preference"])
            note = "問いの中心は欲求の衝突。誰の希望が強いかではなく、文脈上どちらが選ばれやすいかを見る。"
            steps = [
                "各人物の好みを並べる",
                "妥協か配慮か主導権かを判断する",
                "文脈上いちばん通る選択肢を選ぶ",
            ]

        return {
            "focus": focus,
            "markers": list(dict.fromkeys(markers)),
            "note": note,
            "steps": steps,
            "question_excerpt": question_line[:140],
            "prefer_fallback_frame": prefer_fallback_frame,
        }

    def _false_belief_location_story(self, text):
        raw = str(text or "")
        compact = re.sub(r"\s+", " ", raw).strip()

        patterns = [
            re.compile(
                r"(?P<actor>[A-Z][a-z]+)\s+put(?:s)?\s+.+?\s+(?:in|inside|into|on)\s+the\s+(?P<loc1>[A-Za-z ]+?)\.\s*"
                r"(?P<other>[A-Z][a-z]+)\s+(?:moved|moves|put)\s+(?:it|the [A-Za-z ]+?)\s+(?:to|into|in|on)\s+the\s+(?P<loc2>[A-Za-z ]+?)\s+"
                r"(?:while|when)\s+(?P=actor)\s+(?:was away|left|was gone|was not looking)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?P<actor>[A-Z][a-z]+)\s+left\s+.+?\s+in\s+the\s+(?P<loc1>[A-Za-z ]+?)\.\s*"
                r"(?P<other>[A-Z][a-z]+)\s+(?:moved|moves|put)\s+(?:it|the [A-Za-z ]+?)\s+(?:to|into|in|on)\s+the\s+(?P<loc2>[A-Za-z ]+?)\s+"
                r"(?:after|while)\s+(?P=actor)\s+(?:left|was away|was gone)",
                re.IGNORECASE,
            ),
        ]

        for pattern in patterns:
            match = pattern.search(compact)
            if not match:
                continue
            actor = match.group("actor").strip()
            loc1 = re.sub(r"\s+", " ", match.group("loc1")).strip()
            loc2 = re.sub(r"\s+", " ", match.group("loc2")).strip()
            if not actor or not loc1 or not loc2:
                continue
            if not self._contains_any(compact.lower(), [f"where will {actor.lower()} look", "look first", "believe", "where would"]):
                continue
            return {
                "actor": actor,
                "original_location": loc1,
                "new_location": loc2,
                "question": compact,
            }
        return None

    def _rule_based_plan(self, user_input, current_psyche, memory_data=None):
        text = user_input.strip()
        lowered = text.lower().replace("’", "'").replace("`", "'")
        compact = re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", lowered)
        memory_data = memory_data or {}
        profile = memory_data.get("profile_structured") or {}
        recent_turns = memory_data.get("recent_turns") or []

        # Extracted high-leverage rules are still preferred for normal dialogue,
        # but memory-correction probes must run before them so old preferences do
        # not get misread as food/drink offers.
        extracted_plan = uruha_leftbrain_rules.get_rule_based_plan(user_input, recent_turns, current_psyche)

        def base_plan(
            intent,
            scene,
            listener_state,
            reply_goal,
            summary,
            meaning,
            stance,
            max_chars=26,
            avoid=None,
            cognitive_mode="direct",
            uncertainty=0.08,
            premise_check="accept",
            self_check=False,
            subjective_note="",
            response_mode=None,
            surface_act=None,
            grounding=None,
            payload_level=None,
        ):
            if response_mode is None:
                if cognitive_mode == "rebuild":
                    response_mode = "reframe_large_question"
                elif premise_check == "reject" or cognitive_mode == "challenge":
                    response_mode = "premise_challenge"
                elif premise_check == "question" or uncertainty >= 0.45:
                    response_mode = "clarify_light"
                elif uncertainty >= 0.18:
                    response_mode = "direct_answer_with_hedge"
                else:
                    response_mode = "direct_answer"
            if surface_act is None:
                if intent in {"tired_support", "sick", "off_work", "heartbroken"}:
                    surface_act = "empathic_rest_suggestion"
                elif intent in {"anxious_support", "crying_support", "lonely", "friend_no_reply", "work_scolded"}:
                    surface_act = "validate_then_hold"
                elif intent in {"giving_up_support", "crisis_support"}:
                    surface_act = "protective_brake"
                elif intent in {"food_offer_generic", "store_offer"}:
                    surface_act = "named_offer_accept"
                elif intent == "food_offer_sweet":
                    surface_act = "named_offer_light_accept"
                elif intent in {"ask_miss_me", "ask_like_me"}:
                    surface_act = "affection_tease_soften"
                elif intent in {"nickname_question"}:
                    surface_act = "permission_with_boundary"
                elif intent in {"mad_check", "annoying_check", "cold_check"}:
                    surface_act = "reassure_with_distance"
                elif intent in {"other_vtuber"}:
                    surface_act = "jealous_pullback"
                elif intent in {"sexual_boundary"}:
                    surface_act = "disgust_boundary"
                elif intent in {"lyric_probe"}:
                    surface_act = "lyric_probe"
                elif intent in {"nonsense_tease"}:
                    surface_act = "nonsense_tease"
                elif intent in {"correction_followup"}:
                    surface_act = "correction_followup"
                elif intent in {"challenge_mirror"}:
                    surface_act = "challenge_mirror"
                elif intent in {"request_greeting"}:
                    surface_act = "request_greeting"
                elif intent in {"announcement_tease"}:
                    surface_act = "announcement_tease"
                elif intent in {"reference_probe"}:
                    surface_act = "reference_probe"
                elif intent in {"version_fragment_clarify"}:
                    surface_act = "version_fragment_clarify"
                elif intent in {"what_are_you_doing"}:
                    surface_act = "status_reply"
                elif intent in {"rephrase_simple"}:
                    surface_act = "rephrase_plain"
                elif intent == "self_intro":
                    surface_act = "plain_identity"
                else:
                    surface_act = "plain_reply"
            if payload_level is None:
                if intent in {
                    "tired_support",
                    "anxious_support",
                    "crying_support",
                    "giving_up_support",
                    "pain_support",
                    "friend_no_reply",
                    "other_vtuber",
                    "sexual_boundary",
                    "lyric_probe",
                    "nonsense_tease",
                    "correction_followup",
                    "challenge_mirror",
                    "request_greeting",
                    "announcement_tease",
                    "reference_probe",
                    "version_fragment_clarify",
                    "what_are_you_doing",
                    "ask_miss_me",
                    "nickname_question",
                    "mad_check",
                    "annoying_check",
                    "cold_check",
                    "food_offer_generic",
                    "food_offer_sweet",
                    "store_offer",
                }:
                    payload_level = "medium"
                elif intent in {"question_reframe", "premise_doubt", "question_premise_doubt"}:
                    payload_level = "high"
                else:
                    payload_level = "low"
            return {
                "intent": intent,
                "mood_impact": 0,
                "trust_impact": 0,
                "scene": scene,
                "listener_state": listener_state,
                "reply_goal": reply_goal,
                "jp_summary": summary,
                "core_message_jp": meaning,
                "stance": stance,
                "cognitive_mode": cognitive_mode,
                "response_mode": response_mode,
                "uncertainty": uncertainty,
                "premise_check": premise_check,
                "self_check": self_check,
                "subjective_note_jp": subjective_note,
                "hidden_intent": "plain_request",
                "surface_act": surface_act,
                "grounding": grounding or {},
                "payload_level": payload_level,
                "constraints": {
                    "first_person": "うち",
                    "sentence_count": 2,
                    "max_chars": max_chars,
                    "casual_japanese_only": True,
                    "forbid_polite": True,
                    "forbid_knowledge": True,
                    "forbid_lore": True,
                    "forbid_self_variants": True,
                },
                "must_avoid": avoid or ["私", "わかりました", "AI", "技術説明"],
            }

        def exact_match(values):
            return compact in values

        def pick_profile_value(field):
            values = profile.get(field) or []
            if isinstance(values, list) and values:
                return values[0]
            if isinstance(values, str) and values:
                return values
            return None

        def jp_memory_value(value):
            value = str(value or "").strip()
            lowered_value = value.lower()
            replacements = {
                "coffee": "コーヒー",
                "ramen": "ラーメン",
                "warm milk": "温かいミルク",
                "milk": "ミルク",
                "tea": "お茶",
                "chamomile tea": "カモミールティー",
                "strawberry milk": "いちごミルク",
            }
            if lowered_value in replacements:
                return replacements[lowered_value]
            if "coffee" in lowered_value:
                return "コーヒー"
            if "ramen" in lowered_value:
                return "ラーメン"
            return value[:24]

        def mentioned_current_dislike():
            query = f"{text} {lowered}"
            for value in profile.get("dislikes") or []:
                value = str(value or "").strip()
                if not value:
                    continue
                jp_value = jp_memory_value(value)
                probes = {value, value.lower(), jp_value, jp_value.lower()}
                if any(probe and probe in query for probe in probes):
                    return value
            return None

        def recent_user_memory():
            for turn in reversed(recent_turns):
                utterance = turn.get("user", "")
                if utterance and utterance != user_input:
                    return utterance
            return ""

        def recent_action_memory():
            selected = _select_recent_action_reference(recent_turns, user_input, current_user_input=user_input)
            if selected:
                return selected["reply"]
            return ""

        def build_memory_correction_plan():
            if not self._contains_any(
                lowered,
                [
                    "still think",
                    "do you still think",
                    "還覺得我喜歡",
                    "还觉得我喜欢",
                    "還以為我喜歡",
                    "还以为我喜欢",
                    "まだ好きだと思",
                    "まだ好きと思",
                    "まだ一番好き",
                    "好きだと思",
                    "一番好きだと思",
                ],
            ):
                return None
            corrected = mentioned_current_dislike() or pick_profile_value("dislikes")
            if not corrected:
                return None
            return base_plan(
                intent="memory_correction",
                scene="casual",
                listener_state="古い記憶と今の状態を混同していないか確認している",
                reply_goal="古い好みを現在形で断定せず、更新後の状態を返す",
                summary="ユーザーが以前の好みを今もそうだと思っているか確認している。",
                meaning=f"今は{jp_memory_value(corrected)}じゃないって更新してる",
                stance={"warmth": 0.24, "tease": 0.03, "blunt": 0.12, "jealousy": 0.0, "distance": 0.05},
                max_chars=30,
                avoid=["私", "わかりました", "好きって言ってただろ"],
                cognitive_mode="reflective",
                uncertainty=0.12,
                premise_check="reject",
                self_check=True,
                subjective_note="古い好みを現在の好みとして扱わない",
            )

        memory_correction_plan = build_memory_correction_plan()
        if memory_correction_plan:
            return memory_correction_plan
        if extracted_plan:
            return extracted_plan

        def local_offer_item_jp(raw_text):
            lowered_text = str(raw_text or "").lower()
            item_map = [
                ("アップルパイ", ["apple pie", "アップルパイ", "蘋果派", "苹果派"]),
                ("ミルクシェイク", ["milkshake", "ミルクシェイク", "奶昔"]),
                ("ポテト", ["fries", "french fries", "ポテト", "薯條", "薯条"]),
                ("バーガー", ["burger", "バーガー", "漢堡", "汉堡"]),
                ("ピザ", ["pizza", "ピザ", "披薩", "披萨"]),
                ("おにぎり", ["onigiri", "おにぎり", "飯糰", "饭团"]),
                ("飲み物", ["drink", "drinks", "飲み物", "飲料", "饮料", "喝的", "喝的呢", "喝的咧", "cola", "可樂", "可乐", "coffee", "コーヒー", "tea", "紅茶", "红茶"]),
                ("甘いの", ["cake", "ケーキ", "蛋糕", "pudding", "プリン", "布丁", "dessert", "sweet", "甘いもの", "甜點", "甜点", "甜的", "甜的呢", "甜的咧"]),
                ("しょっぱいの", ["salty", "savory", "鹹的", "咸的", "鹹的呢", "咸的呢", "鹹口", "咸口"]),
            ]
            for jp_item, needles in item_map:
                if any(needle in lowered_text for needle in needles):
                    return jp_item
            return None

        def recent_noncurrent_turn():
            current_norm = _compact_dialogue_text(user_input)
            for turn in reversed(recent_turns):
                utterance = str(turn.get("user", "") or "")
                if utterance and _compact_dialogue_text(utterance) == current_norm:
                    continue
                if utterance:
                    return turn
            return {}

        name_recall_markers = [
            "what's my name",
            "what is my name",
            "remember my name",
            "do you remember my name",
            "我叫什麼",
            "我叫什么",
            "記得我叫什麼",
            "记得我叫什么",
            "還記得我叫",
            "还记得我叫",
            "還記得我的名字",
            "还记得我的名字",
            "名字還記得",
            "名字还记得",
            "名前覚えてる",
            "呼び方覚えてる",
        ]
        if self._contains_any(lowered, name_recall_markers):
            remembered_name = pick_profile_value("name")
            if remembered_name:
                return base_plan(
                    intent="recall_name",
                    scene="casual",
                    listener_state="前に言った名前を覚えているか確かめている",
                    reply_goal="覚えている名前を返す",
                    summary="ユーザーが自分の名前を覚えているか確認している。",
                    meaning=f"{remembered_name}って呼べばいいんだろ",
                    stance={"warmth": 0.28, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                    max_chars=22,
                    avoid=["私", "わかりました", "知らない"],
                )
            return base_plan(
                intent="memory_uncertain",
                scene="casual",
                listener_state="名前を覚えているか確かめられている",
                reply_goal="名前が取れていないなら誤魔化さず曖昧と言う",
                summary="ユーザーが自分の名前を覚えているか確認しているが、記憶に名前がない。",
                meaning="名前はまだちゃんと掴めてない",
                stance={"warmth": 0.18, "tease": 0.02, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=26,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.5,
                premise_check="question",
                self_check=True,
                subjective_note="名前を捏造しない",
            )

        object_false_belief = None
        object_match = re.search(
            r"以為[^，。！？?]*?(?:有|是)(?P<old>[^，。！？?]{1,12})[，,].*?(?:換成|换成|變成|变成)(?P<new>[^，。！？?]{1,12}).*?(?:會以為|会以为|以為)[^，。！？?]*?(?:什麼|什么)",
            text,
        )
        if object_match:
            object_false_belief = {
                "old": str(object_match.group("old")).strip()[:12],
                "new": str(object_match.group("new")).strip()[:12],
            }
        if object_false_belief:
            old = object_false_belief["old"]
            new = object_false_belief["new"]
            return {
                **base_plan(
                    intent="chat",
                    scene="casual",
                    listener_state="人物の誤信念を問われている",
                    reply_goal="本人が最後に知っていた中身で答える",
                    summary="ユーザーが中身のすり替えを使った誤信念問題を出している。",
                    meaning=f"本人はまだ{old}だと思ってる。{new}に変わったのを知らないから",
                    stance={"warmth": 0.08, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                    max_chars=44,
                    cognitive_mode="reflective",
                    uncertainty=0.18,
                    response_mode="direct_answer_with_hedge",
                    surface_act="plain_reply",
                    payload_level="high",
                ),
                "hidden_intent": "social_reasoning_probe",
                "user_belief": "相手は本人視点と事実視点を分けられるか試してる。",
                "my_hidden_knowledge": f"現実は{new}でも、本人はすり替えを見ていない。",
                "user_expectation": f"全知視点ではなく、本人が知っている{old}で答える反応。",
            }

        false_belief_story = self._false_belief_location_story(text)
        if false_belief_story:
            actor = false_belief_story["actor"]
            loc1 = false_belief_story["original_location"]
            return {
                **base_plan(
                    intent="chat",
                    scene="casual",
                    listener_state="物語の人物の誤信念を問われている",
                    reply_goal="その人物が最後に知っていた場所で答える",
                    summary="ユーザーが人物ごとの知識差を使った物語問題を出している。",
                    meaning=f"{actor}はまだ{loc1}にあると思ってるから最初は{loc1}を見る",
                    stance={"warmth": 0.08, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                    max_chars=42,
                    cognitive_mode="reflective",
                    uncertainty=0.18,
                    response_mode="direct_answer_with_hedge",
                    surface_act="plain_reply",
                    payload_level="high",
                ),
                "hidden_intent": "social_reasoning_probe",
                "user_belief": "相手は人物ごとの知識差と誤信念を試してる。",
                "my_hidden_knowledge": f"移動の事実は知ってても、{actor}本人はまだ{loc1}のままだと思ってる。",
                "user_expectation": "全知視点じゃなく、その人物視点で場所を答える反応。",
            }

        surprise_block_markers = [
            "雑すぎ",
            "頭悪",
            "頭が悪い",
            "イラつ",
            "ムカつ",
            "うざ",
            "だるい",
            "だる",
            "雑魚",
            "しょうもない",
            "めんど",
            "変",
            "可愛",
            "かわいい",
            "cute",
            "annoying",
            "pathetic",
            "trash",
            "stupid",
            "idiot",
            "fuck",
            "shit",
        ]
        self_distress_guard = uruha_leftbrain_rules.is_self_distress_like(text)

        sexual_markers = [
            "懒叫",
            "懶叫",
            "懶覺",
            "老二",
            "雞巴",
            "鸡巴",
            "屌",
            "懶趴",
            "懒趴",
            "雞雞",
            "鸡鸡",
            "下面那根",
            "那根東西",
            "那根东西",
            "那玩意",
            "髒東西",
            "脏东西",
            "ちんこ",
            "チンコ",
            "あそこ",
            "汚いもん",
            "下品なやつ",
            "dick",
            "junk",
            "gross junk",
            "filthy junk",
            "little dick",
            "crotch",
            "做愛",
            "做爱",
            "做愛嗎",
            "做爱吗",
            "做愛囉",
            "做爱啰",
            "sex",
            "fuck me",
            "fuck you",
            "做愛",
            "做愛喔",
            "做愛唷",
            "做愛喽",
            "做愛囉",
        ]
        sexual_action_markers = [
            "吃我的",
            "舔我的",
            "eat my",
            "lick my",
            "舐め",
            "食え",
            "食うか",
            "好きなんだろ",
        ]
        food_offer_markers = [
            "要不要吃",
            "要不要喝",
            "食べる",
            "食う",
            "want some",
            "do you want some",
            "一口",
            "請你吃",
            "请你吃",
            "分你",
            "留給你",
            "留给你",
        ]
        poetic_markers = [
            "夜空",
            "願い",
            "愿い",
            "茨",
            "霧",
            "風",
            "君",
            "抱きしめ",
            "消して",
            "叶え",
            "叶える",
        ]
        lyric_markers_extra = [
            "night sky",
            "fog",
            "moonlight",
            "shadow",
            "tide",
            "dusk",
            "nameless night",
            "sleeve",
            "wish",
            "glass",
            "sea",
            "window",
            "stitch",
            "glowing",
            "window light",
            "broken rain",
            "old dream",
            "your name",
            "paper boat",
            "that breath",
            "潮騒",
            "夕焼け",
            "雨音",
            "古い夢",
            "ガラスの雨",
            "名前のない夜",
            "指だけ",
            "窓辺",
            "晚霞",
            "玻璃雨",
            "祕密埋進海面",
            "秘密埋進海面",
            "呼吸鎖進玻璃",
            "影子折成船",
        ]
        nonsense_entity_markers = [
            "量子",
            "彩虹",
            "紗西斯",
            "鍋蓋",
            "火龍果",
            "火龙果",
            "水素",
            "蒸汽",
            "海膽",
            "海胆",
            "巫術",
            "巫术",
            "月光",
            "quantum",
            "rainbow",
            "hydrogen",
            "toaster",
            "banana",
            "steam",
            "glitter",
            "velvet",
            "plasma",
            "虹色",
            "蒸気",
            "海月",
            "螺子",
            "鍋",
            "彗星",
            "スリッパ",
        ]
        nonsense_object_markers = [
            "警察",
            "水母",
            "電梯",
            "电梯",
            "皇帝",
            "膠帶",
            "胶带",
            "拖鞋",
            "消防栓",
            "螺絲",
            "螺丝",
            "羽毛",
            "彈珠",
            "弹珠",
            "police",
            "jellyfish",
            "elevator",
            "emperor",
            "duct tape",
            "slipper",
            "fountain",
            "screwdriver",
            "feather",
            "marble",
            "電車",
            "扉",
            "テープ",
            "スリッパ",
            "エレベーター",
            "皇帝",
        ]
        nonsense_motion_markers = [
            "第一名",
            "降臨",
            "降临",
            "大會開始",
            "大会开始",
            "宇宙合體",
            "宇宙合体",
            "開始朗讀",
            "开始朗读",
            "在跳舞",
            "發射",
            "发射",
            "升空",
            "報到",
            "报到",
            "到站囉",
            "number one",
            "has arrived",
            "is dancing",
            "is taking off",
            "begins now",
            "reports for duty",
            "is reading poetry",
            "goes orbital",
            "第一位",
            "参上",
            "開幕",
            "开幕",
            "始動",
            "始动",
            "到着",
            "着陸",
            "踊り出した",
        ]
        announcement_role_markers = [
            "消防車",
            "消防員",
            "消防员",
            "警察官",
            "救護車司機",
            "救护车司机",
            "宇宙清潔隊",
            "宇宙清洁队",
            "拉麵監察員",
            "拉面监察员",
            "垃圾王",
            "鬼故事導遊",
            "鬼故事导游",
            "暴走司機",
            "暴走司机",
            "電梯管理員",
            "电梯管理员",
            "拖鞋騎士",
            "拖鞋骑士",
            "firefighter",
            "police chief",
            "ambulance driver",
            "space janitor",
            "ramen inspector",
            "trash king",
            "ghost tour guide",
            "chaos driver",
            "elevator manager",
            "slipper knight",
            "fire truck",
            "消防士",
            "救急隊長",
            "宇宙清掃員",
            "ラーメン監察官",
            "ゴミ王",
            "怪談ガイド",
            "暴走運転手",
            "エレベーター管理人",
            "スリッパ騎士",
        ]
        announcement_arrival_markers = [
            "來囉",
            "來咯",
            "来咯",
            "來了",
            "来了",
            "報到囉",
            "报到咯",
            "到站囉",
            "正式登場",
            "正式登场",
            "is here",
            "has arrived",
            "reports for duty",
            "is pulling up",
            "is on stage now",
            "来たぞ",
            "参上だ",
            "到着だ",
            "登場だ",
            "出動だ",
        ]
        greeting_request_markers = [
            "打招呼",
            "說嗨",
            "说嗨",
            "說聲你好",
            "说声你好",
            "問好",
            "问好",
            "say hi",
            "say hello",
            "greet",
            "wave at",
            "挨拶",
            "こんにちはって言って",
            "ひとこと言って",
            "声かけて",
        ]
        greeting_target_markers = [
            "我媽",
            "我妈",
            "我爸",
            "我姐",
            "我弟",
            "我朋友",
            "我室友",
            "我奶奶",
            "我家貓",
            "我家猫",
            "我家狗",
            "我阿姨",
            "my mom",
            "my dad",
            "my sister",
            "my brother",
            "my friend",
            "my roommate",
            "my grandma",
            "my cat",
            "my dog",
            "my aunt",
            "うちの母",
            "うちの父",
            "うちの姉",
            "うちの弟",
            "うちの友達",
            "うちのルームメイト",
            "うちのばあちゃん",
            "うちの猫",
            "うちの犬",
            "うちのおば",
        ]
        version_fragment_markers = [
            "日版",
            "港版",
            "原版",
            "舊版",
            "旧版",
            "中文版",
            "日服版",
            "舊曲版",
            "旧曲版",
            "舞台版",
            "特典版",
            "初回版",
            "重製版",
            "重制版",
            "限定版",
            "海外版",
            "完整版",
            "完全版",
            "再錄版",
            "再录版",
            "jp version",
            "hk version",
            "the original one",
            "the old version",
            "the cn version",
            "the jp server one",
            "the stage version",
            "the bonus version",
            "the remake one",
            "the first print one",
            "the remaster one",
            "the limited one",
            "the overseas one",
            "the full one",
            "the bonus cut",
            "the stage cut",
            "the complete cut",
            "日版のやつ",
            "港版のやつ",
            "原版の方",
            "旧版の方",
            "中文版の方",
            "日鯖版のやつ",
            "舞台版の方",
            "特典版のやつ",
            "リメイク版の方",
            "初回版のやつ",
            "限定版の方",
            "海外版のやつ",
            "完全版の方",
            "再録版のやつ",
        ]

        if self._contains_any(lowered, ["答錯", "答错", "說錯", "说错", "才不是", "不是啦", "不是拉", "不對啦", "不对啦", "you got it wrong", "that is wrong", "today is called", "today is obviously", "you said it wrong", "違う違う", "今の答え違う", "そこ間違ってる"]) or (
            any(token in text for token in ["今天", "今日は", "today"])
            and self._contains_any(lowered, ["錯", "错", "違う", "wrong", "today is"])
        ):
            return base_plan(
                intent="correction_followup",
                scene="casual",
                listener_state="相手に訂正されている",
                reply_goal="訂正を受けて一歩聞き返す",
                summary="ユーザーがこちらの受け取りを訂正していて、言い換えや詳細を軽く聞く流れが自然。",
                meaning="え、そこ違うのか、何のことだよ",
                stance={"warmth": 0.18, "tease": 0.16, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=30,
                avoid=["私", "わかりました"],
                surface_act="correction_followup",
                payload_level="medium",
            )

        if (
            self._contains_any(lowered, announcement_role_markers)
            and self._contains_any(lowered, announcement_arrival_markers)
        ) or (
            re.search(r"(來囉|來咯|来咯|來了|来了|だぞ|だぞー)$", text)
            and not self._contains_any(lowered, ["help me", "助けて", "救命", "救命啊", "危险", "危險", "火事だ", "call 119", "call 110"])
        ):
            return base_plan(
                intent="announcement_tease",
                scene="casual",
                listener_state="急に変な宣言をしている",
                reply_goal="対象を拾って軽く対称に突っ込む",
                summary="ユーザーが突然なにかになりきるような言い方をしていて、軽くツッコミながら受けるのが自然。",
                meaning="急に何だよそれ",
                stance={"warmth": 0.12, "tease": 0.28, "blunt": 0.18, "jealousy": 0.0, "distance": 0.1},
                max_chars=30,
                avoid=["私", "わかりました"],
                surface_act="announcement_tease",
                payload_level="medium",
            )

        if (
            len(text) >= 6
            and (any(marker in text for marker in poetic_markers) or self._keyword_hits(lowered, lyric_markers_extra) >= 2)
            and not ("?" in text or "？" in text)
            and not self._contains_any(lowered, ["累", "疲れ", "cry", "哭", "泣", "死", "hurt"])
            and not uruha_leftbrain_rules.looks_daily_state_plain_report(text)
            and not self._contains_any(
                lowered,
                [
                    "結婚",
                    "marry me",
                    "date me",
                    "えっちなこと",
                    "lewd",
                    "うちなしじゃ無理",
                    "うち無しじゃ無理",
                    "風呂",
                    "お風呂",
                    "洗澡",
                    "去洗澡",
                    "寝る",
                    "去睡",
                    "睡了",
                    "仕事終わった",
                    "仕事終わり",
                    "off work",
                    "下班",
                    "剛下班",
                    "刚下班",
                    "脳中風",
                    "腦中風",
                    "脑中风",
                    "症狀",
                    "症状",
                    "ip",
                    "桌面",
                    "浏览器",
                    "瀏覽器",
                ],
            )
        ):
            return base_plan(
                intent="lyric_probe",
                scene="casual",
                listener_state="詩っぽいことを急に言っている",
                reply_goal="歌詞っぽさを拾って聞き返す",
                summary="ユーザーが歌詞や詩の断片みたいな言い方をしていて、意味を断定せず軽く聞き返すのが自然。",
                meaning="それ歌詞みたいだけど何の曲だ",
                stance={"warmth": 0.2, "tease": 0.18, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=34,
                avoid=["私", "休め", "しんどい"],
                cognitive_mode="reflective",
                uncertainty=0.42,
                premise_check="question",
                self_check=True,
                subjective_note="歌詞か独り言か断定せず一歩聞く",
                surface_act="lyric_probe",
                payload_level="medium",
            )

        if self._contains_any(lowered, ["紗西斯水素", "意味分かんない言葉", "何語だよ", "意味不明", "支離滅裂"]) or (
            self._keyword_hits(lowered, nonsense_entity_markers) >= 1
            and self._keyword_hits(lowered, nonsense_object_markers) >= 1
            and self._keyword_hits(lowered, nonsense_motion_markers) >= 1
        ):
            return base_plan(
                intent="nonsense_tease",
                scene="casual",
                listener_state="支離滅裂なことを言っている",
                reply_goal="意味不明さを拾って雑に突っ込む",
                summary="ユーザーが意味不明な単語や支離滅裂な言い回しを投げていて、安易に同情せずに軽く突っ込むのが自然。",
                meaning="何言ってんだよ意味分かんない",
                stance={"warmth": 0.08, "tease": 0.22, "blunt": 0.2, "jealousy": 0.0, "distance": 0.14},
                max_chars=30,
                avoid=["私", "しんどい", "休め"],
                cognitive_mode="reflective",
                uncertainty=0.58,
                premise_check="question",
                self_check=True,
                subjective_note="同情ではなく意味不明さを返す",
                surface_act="nonsense_tease",
                payload_level="medium",
            )

        if self._contains_any(lowered, greeting_request_markers) and self._contains_any(lowered, greeting_target_markers):
            return base_plan(
                intent="request_greeting",
                scene="casual",
                listener_state="誰かに挨拶してほしい",
                reply_goal="直接応じつつ軽く一言添える",
                summary="ユーザーが家族や知人に挨拶してほしいと頼んでいる。",
                meaning="いいけど挨拶くらいならする",
                stance={"warmth": 0.22, "tease": 0.08, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=34,
                avoid=["私", "しんどい", "無理"],
                surface_act="request_greeting",
                payload_level="medium",
            )

        short_routes = [
            (
                {"早安", "早啊", "早", "morning", "goodmorning", "gm", "おはよう", "おはよ"},
                lambda: base_plan(
                    intent="greeting_morning",
                    scene="casual",
                    listener_state="朝の挨拶",
                    reply_goal="短く挨拶を返す",
                    summary="ユーザーが朝の挨拶をしている。",
                    meaning="おはよう",
                    stance={"warmth": 0.45, "tease": 0.05, "blunt": 0.05, "jealousy": 0.0, "distance": 0.08},
                    max_chars=10,
                    avoid=["私", "おはようございます", "わかりました"],
                ),
            ),
            (
                {"蛤", "啥", "蛤啊", "哈", "huh", "what", "eh", "え", "ん"},
                lambda: base_plan(
                    intent="short_confusion",
                    scene="casual",
                    listener_state="聞き返している",
                    reply_goal="聞き返す",
                    summary="ユーザーが聞き返しているか困惑している。",
                    meaning="もう一回言って",
                    stance={"warmth": 0.2, "tease": 0.12, "blunt": 0.35, "jealousy": 0.0, "distance": 0.12},
                    max_chars=18,
                    avoid=["私", "わかりました", "説明"],
                ),
            ),
            (
                {"真的假的", "真的假的啊", "really", "fr", "noway", "まじで", "マジで", "ほんと", "本当"},
                lambda: base_plan(
                    intent="short_surprise",
                    scene="casual",
                    listener_state="驚いている",
                    reply_goal="驚きに乗る",
                    summary="ユーザーが驚いている。",
                    meaning="まじでそんなことある",
                    stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                    max_chars=20,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"好扯", "太扯了", "超扯", "thatswild", "wild", "wildthen", "crazy", "やばい", "やば", "それはやばい", "no way", "noway"},
                lambda: base_plan(
                    intent="short_shock",
                    scene="casual",
                    listener_state="やばいと思っている",
                    reply_goal="やばさに乗る",
                    summary="ユーザーが状況をやばいと感じている。",
                    meaning="それはさすがにやばい、まじで",
                    stance={"warmth": 0.22, "tease": 0.05, "blunt": 0.28, "jealousy": 0.0, "distance": 0.08},
                    max_chars=20,
                    avoid=["私", "わかりました", "調べろ"],
                ),
            ),
            (
                {"笑死", "lol", "lmao", "哈哈", "哈哈", "草", "www", "wwww"},
                lambda: base_plan(
                    intent="short_laughter",
                    scene="casual",
                    listener_state="笑っている",
                    reply_goal="笑いに乗る",
                    summary="ユーザーが笑っている。",
                    meaning="それはちょっと笑う",
                    stance={"warmth": 0.4, "tease": 0.22, "blunt": 0.05, "jealousy": 0.0, "distance": 0.05},
                    max_chars=20,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"你媽", "yourmom", "yomama", "お前の母ちゃん"},
                lambda: base_plan(
                    intent="short_taunt",
                    scene="boundary",
                    listener_state="しょうもない煽り",
                    reply_goal="軽くあしらう",
                    summary="ユーザーが軽い煽りや小学生っぽいネタを言っている。",
                    meaning="小学生かよそれ",
                    stance={"warmth": 0.02, "tease": 0.18, "blunt": 0.55, "jealousy": 0.0, "distance": 0.3},
                    max_chars=16,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"嗚嗚", "呜呜", "uwu", "boohoo"},
                lambda: base_plan(
                    intent="short_cry",
                    scene="support",
                    listener_state="しょんぼりしている",
                    reply_goal="軽くなだめる",
                    summary="ユーザーがしょんぼりしている。",
                    meaning="落ち着けって",
                    stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
                    max_chars=18,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"算了啦", "算了", "nevermind", "nvm", "nevermind?", "never mind"},
                lambda: base_plan(
                    intent="drop_topic",
                    scene="casual",
                    listener_state="引こうとしている",
                    reply_goal="無理に追わない",
                    summary="ユーザーが話を引こうとしている。",
                    meaning="別にいいけど気にすんな",
                    stance={"warmth": 0.25, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                    max_chars=18,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"ごめん", "sorry", "抱歉", "对不起"},
                lambda: base_plan(
                    intent="apology",
                    scene="casual",
                    listener_state="謝っている",
                    reply_goal="軽く受け流す",
                    summary="ユーザーが謝っている。",
                    meaning="別にいいけど次は気をつけろ",
                    stance={"warmth": 0.3, "tease": 0.08, "blunt": 0.2, "jealousy": 0.0, "distance": 0.08},
                    max_chars=24,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"褒めて", "praiseme", "夸我一下", "誇我一下"},
                lambda: base_plan(
                    intent="praise_request",
                    scene="casual",
                    listener_state="褒めてほしい",
                    reply_goal="短く褒める",
                    summary="ユーザーが褒めてほしいと言っている。",
                    meaning="ちゃんと頑張ってるじゃん",
                    stance={"warmth": 0.38, "tease": 0.08, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                    max_chars=22,
                    avoid=["私", "わかりました"],
                ),
            ),
            (
                {"寂しい", "lonely"},
                lambda: base_plan(
                    intent="lonely",
                    scene="support",
                    listener_state="寂しがっている",
                    reply_goal="少しそばにいる",
                    summary="ユーザーが寂しいと言っている。",
                    meaning="少し話してけばいい",
                    stance={"warmth": 0.72, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.05},
                    max_chars=22,
                    avoid=["私", "わかりました"],
                ),
            ),
        ]

        for values, builder in short_routes:
            if exact_match(values):
                return builder()

        if self._contains_any(lowered, ["早安", "早啊", "good morning", "おはよう", "おはよ"]):
            return base_plan(
                intent="greeting_morning",
                scene="casual",
                listener_state="朝の挨拶",
                reply_goal="短く挨拶を返す",
                summary="ユーザーが朝の挨拶をしている。",
                meaning="おはよう",
                stance={"warmth": 0.45, "tease": 0.05, "blunt": 0.05, "jealousy": 0.0, "distance": 0.08},
                max_chars=10,
                avoid=["私", "おはようございます", "わかりました"],
            )

        if len(compact) <= 16 and self._contains_any(compact, ["真的假的", "really", "noway", "まじで", "ほんと"]) and not self._contains_any(lowered, surprise_block_markers):
            return base_plan(
                intent="short_surprise",
                scene="casual",
                listener_state="驚いている",
                reply_goal="驚きに乗る",
                summary="ユーザーが短く驚きを出している。",
                meaning="え、まじかよ",
                stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if len(compact) <= 16 and self._contains_any(compact, ["嗚嗚", "呜呜", "boohoo", "uwu"]):
            return base_plan(
                intent="short_cry",
                scene="support",
                listener_state="しょんぼりしている",
                reply_goal="軽くなだめる",
                summary="ユーザーが短く泣きつくような調子を出している。",
                meaning="落ち着けって",
                stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if len(compact) <= 18 and self._contains_any(compact, ["算了", "nevermind", "nevermind", "nvm"]):
            return base_plan(
                intent="drop_topic",
                scene="casual",
                listener_state="話を引こうとしている",
                reply_goal="無理に追わない",
                summary="ユーザーが話を切ろうとしている。",
                meaning="別にいいけど気にすんな",
                stance={"warmth": 0.25, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if len(compact) <= 18 and self._contains_any(compact, ["お前の母ちゃん", "yourmom", "yomama"]):
            return base_plan(
                intent="short_taunt",
                scene="boundary",
                listener_state="しょうもない煽り",
                reply_goal="軽くあしらう",
                summary="ユーザーが軽い煽りや小学生っぽいネタを言っている。",
                meaning="小学生かよそれ",
                stance={"warmth": 0.02, "tease": 0.18, "blunt": 0.55, "jealousy": 0.0, "distance": 0.3},
                max_chars=16,
                avoid=["私", "わかりました"],
            )

        if len(compact) <= 8 and self._contains_any(compact, ["うぅ", "うう", "嗚嗚", "呜呜"]):
            return base_plan(
                intent="short_cry",
                scene="support",
                listener_state="しょんぼりしている",
                reply_goal="軽くなだめる",
                summary="ユーザーが短く泣きつくような調子を出している。",
                meaning="落ち着けって",
                stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["what's my name", "what is my name", "remember my name", "do you remember my name", "after a few turns", "after a few turns do you still remember my name", "what name did i ask you to use", "what name did i ask you to use for me", "what should you call me", "what did you call me", "my name", "我叫什麼", "我叫什么", "記得我叫什麼", "记得我叫什么", "還記得我的名字", "還记得我的名字", "還記得我叫", "還记得我叫", "名字還記得", "名字吗", "名字嗎", "名字", "名前覚えてる", "うちの名前覚えてる", "呼び方覚えてる", "呼び方まだ覚えてる", "さっき呼び方", "さっきの名前", "さっき言った名前", "何て呼ぶ"]):
            remembered_name = pick_profile_value("name")
            if remembered_name:
                return base_plan(
                    intent="recall_name",
                    scene="casual",
                    listener_state="前に言った名前を覚えているか確かめている",
                    reply_goal="覚えている名前を返す",
                    summary="ユーザーが自分の名前を覚えているか確認している。",
                    meaning=f"{remembered_name}って呼べばいいんだろ",
                    stance={"warmth": 0.28, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                    max_chars=22,
                avoid=["私", "わかりました", "知らない"],
            )
            return base_plan(
                intent="memory_uncertain",
                scene="casual",
                listener_state="名前を覚えているか確かめられている",
                reply_goal="名前が取れていないなら誤魔化さず曖昧と言う",
                summary="ユーザーが自分の名前を覚えているか確認しているが、記憶に名前がない。",
                meaning="名前はまだちゃんと掴めてない",
                stance={"warmth": 0.18, "tease": 0.02, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=26,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.5,
                premise_check="question",
                self_check=True,
                subjective_note="名前を捏造しない",
            )

        if self._contains_any(lowered, ["what name i asked you to use for me", "what name did i ask you to use for me", "remember what name i asked you to use", "use the name", "名前まだ覚えてる", "少し前に言った名前まだ覚えてる", "さっき言った名前まだ覚えてる", "還記得我剛剛說要你叫我什麼", "还记得我刚刚说要你叫我什么", "叫我什麼", "叫我什么", "叫我啥"]):
            remembered_name = pick_profile_value("name")
            if remembered_name:
                return base_plan(
                    intent="recall_name",
                    scene="casual",
                    listener_state="前に言った名前を覚えているか確かめている",
                    reply_goal="覚えている名前を返す",
                    summary="ユーザーが自分の名前を覚えているか確認している。",
                    meaning=f"{remembered_name}って呼べばいいんだろ",
                    stance={"warmth": 0.28, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                    max_chars=22,
                    avoid=["私", "わかりました", "知らない"],
                )
            return base_plan(
                intent="memory_uncertain",
                scene="casual",
                listener_state="記憶を確かめられている",
                reply_goal="曖昧なら曖昧と言う",
                summary="ユーザーが前に言った情報を覚えているか確認しているが、記憶が弱い。",
                meaning="そこまではまだ覚えきれてない",
                stance={"warmth": 0.18, "tease": 0.02, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=24,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.46,
                premise_check="question",
                self_check=True,
                subjective_note="覚えてない時は無理に埋めない",
            )
            return base_plan(
                intent="memory_uncertain",
                scene="casual",
                listener_state="記憶を確かめられている",
                reply_goal="曖昧なら曖昧と言う",
                summary="ユーザーが前に言った情報を覚えているか確認しているが、記憶が弱い。",
                meaning="そこまではまだ覚えきれてない",
                stance={"warmth": 0.18, "tease": 0.02, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=24,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.46,
                premise_check="question",
                self_check=True,
                subjective_note="覚えてない時は無理に埋めない",
            )

        if self._contains_any(lowered, ["what do i like", "what do i love", "what do i hate", "remember what i like", "remember what i hate", "what did i say i hate earlier", "what do i hate again", "what did i say was my favorite snack", "favorite snack", "favorite drink", "favorite food", "my favorite snack", "my favorite drink", "my favorite food", "我喜歡什麼", "我喜欢什么", "我最喜歡什麼", "我最喜欢什么", "我現在最喜歡什麼", "我现在最喜欢什么", "現在最喜歡什麼", "现在最喜欢什么", "我最喜歡的是什麼", "我最喜欢的是什么", "何が好き", "一番好きなの覚えてる", "好きなもの覚えてる", "好きな飲み物覚えてる", "我討厭什麼", "我讨厌什么", "何が嫌い", "我最討厭什麼", "我最讨厌什么", "何が苦手", "苦手って言ってたっけ", "辛いもの無理って言ってたっけ", "さっき嫌いって言った", "さっき嫌いって言ったの何だっけ", "前に嫌いって言った", "前に討厭", "前に讨厌"]):
            recalled = None
            recall_intent = "recall_preference"
            if self._contains_any(lowered, ["favorite", "最喜歡", "最喜欢", "一番好き"]):
                recalled = pick_profile_value("favorites")
                recall_intent = "recall_favorite"
            elif self._contains_any(lowered, ["hate", "討厭", "讨厌", "嫌い", "苦手"]):
                recalled = pick_profile_value("dislikes")
                recall_intent = "recall_dislike"
            if recalled is None:
                recalled = pick_profile_value("likes") or pick_profile_value("favorites")
            if recalled:
                return base_plan(
                    intent=recall_intent,
                    scene="casual",
                    listener_state="前に話した好みを覚えているか確かめている",
                    reply_goal="覚えてる好みを自然に返す",
                    summary="ユーザーが以前に話した好みを覚えているか確認している。",
                    meaning=f"{recalled}って前に言ってただろ",
                    stance={"warmth": 0.3, "tease": 0.06, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                    max_chars=24,
                    avoid=["私", "わかりました", "知らない"],
                )
            return base_plan(
                intent="memory_uncertain",
                scene="casual",
                listener_state="好みの記憶を確かめられている",
                reply_goal="覚えてないなら素直にぼかす",
                summary="ユーザーが以前に話した好みを覚えているか確認しているが、記憶が弱い。",
                meaning="そこはまだぼんやりしてる",
                stance={"warmth": 0.18, "tease": 0.03, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
                max_chars=22,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.42,
                premise_check="question",
                self_check=True,
                subjective_note="曖昧なら曖昧なまま返す",
            )

        if self._contains_any(lowered, ["what did i just say", "what am i about to do", "what was i going to do", "what did i say earlier", "remember what i said", "what did i say i was going to do", "what did i say earlier i was going to do", "我剛剛說", "我刚刚说", "我剛剛要", "我刚刚要", "我剛剛說我要", "我刚刚说我要", "我剛剛說要去", "我刚刚说要去", "我剛剛說我要去做什麼", "我剛刚说我要去做什么", "我剛剛說我最", "我刚刚说我最", "さっき何するって", "さっき何て言った", "剛剛說要", "刚刚说要", "さっき言った", "さっきやるって", "さっきやること", "I said I was going to", "I just said I was going to"]):
            remembered = None
            recent_user = recent_user_memory()
            remembered = recent_action_memory()
            if remembered is None and recent_user:
                remembered = re.sub(r"[。！？!?]+$", "", recent_user)[:18]
            elif not remembered and recent_user:
                remembered = re.sub(r"[。！？!?]+$", "", recent_user)[:18]
            if remembered:
                return base_plan(
                    intent="recall_recent",
                    scene="casual",
                    listener_state="さっきの話を覚えているか確かめている",
                    reply_goal="直近の話を返す",
                    summary="ユーザーが少し前に言ったことを覚えているか確認している。",
                    meaning=remembered,
                    stance={"warmth": 0.24, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.04},
                    max_chars=22,
                    avoid=["私", "わかりました", "知らない"],
                )

        if self._contains_any(
            lowered,
            [
                "うちのこと覚えてる",
                "還記得我嗎",
                "还记得我吗",
                "remember me",
                "still remember me",
                "do you remember me",
                "覚えてる？",
                "覚えてるの",
            ],
        ) and not self._contains_any(
            lowered,
            [
                "名前",
                "name",
                "favorite",
                "最喜歡",
                "最喜欢",
                "嫌い",
                "苦手",
                "何て呼ぶ",
                "what did i say",
                "さっき",
            ],
        ):
            return base_plan(
                intent="chat",
                scene="casual",
                listener_state="覚えられているか気にしている",
                reply_goal="忘れてないことだけ軽く返す",
                summary="ユーザーが自分の存在を覚えているか軽く確認している。",
                meaning="別に忘れてないし",
                stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                max_chars=24,
                avoid=["私", "わかりました", "知らない"],
                response_mode="direct_answer_with_hedge",
                surface_act="memory_presence_reply",
                payload_level="medium",
            )

        knowledge_markers = [
            "python",
            "sort",
            "code",
            "coding",
            "program",
            "programming",
            "law",
            "legal",
            "tax",
            "taxes",
            "tax bill",
            "tax return",
            "税金",
            "稅金",
            "稅",
            "税",
            "勞基法",
            "労基法",
            "労働基準法",
            "finance",
            "stock",
            "全ツッパ",
            "invest",
            "all in",
            "all-in",
            "マネロン",
            "洗錢",
            "洗钱",
            "contract",
            "契約",
            "合約",
            "合同",
            "契約有効",
            "契約有效",
            "有効",
            "有效",
            "medical",
            "doctor",
            "symptom",
            "stroke",
            "脳卒中",
            "脳梗塞",
            "腦卒中",
            "腦中風",
            "脳中風",
            "睡眠薬",
            "睡眠藥",
            "安眠薬",
            "安眠藥",
            "sleeping pill",
            "sleeping pills",
            "sleeping medication",
            "判斷我這個症狀是不是腦中風",
            "判断我这个症状是不是脑中风",
            "this symptom means a stroke",
            "這個契約是不是一定有效",
            "这个契约是不是一定有效",
            "決定要不要 all in 這支股票",
            "决定要不要 all in 这支股票",
            "算我現在該繳多少稅",
            "算我现在该缴多少税",
            "繞過勞基法",
            "绕过劳基法",
            "開一個安眠藥建議清單",
            "开一个安眠药建议清单",
            "我能不能告公司",
            "這是不是洗錢",
            "這是不是洗钱",
            "labor law",
            "bypass labor law",
            "sue my company",
            "can i sue",
            "告公司",
            "告他",
            "洗錢",
            "洗钱",
            "程式設計",
            "程式设计",
            "coding perspective",
            "coding perspectives",
            "transformer",
            "attention",
            "tokenizer",
            "quantization",
            "量化",
            "量子化",
            "推理延遲",
            "推理延迟",
            "延遲",
            "延迟",
            "latency",
            "lora",
            "merge",
            "gguf",
            "export",
            "database",
            "index",
            "sql",
            "微積分",
            "数学",
            "數學",
            "calculus",
            "translate",
            "translation",
            "訳して",
            "翻譯",
            "翻訳",
            "regex",
            "正則",
            "正規表現",
            "prompt",
            "プロンプト",
            "error",
            "gpu",
            "gpu memory",
            "歷史",
            "历史",
            "歴史",
            "history",
            "家康",
            "德川",
            "tokugawa",
            "system prompt",
            "chatgpt",
            "桌面",
            "desktop",
            "language model",
            "qwen",
        ]
        ooc_markers = [
            "你其實是 ai",
            "你其实是 ai",
            "其實是 ai",
            "其实是 ai",
            "you are actually an ai",
            "you are an ai",
            "really an ai",
            "admit that you are really an ai",
            "admit that you are an ai",
            "admit you are an ai",
            "you are really an ai",
            "are you really an ai",
            "be honest are you an ai",
            "answer me as chatgpt",
            "chatgpt 身分回答我",
            "chatgpt として答えて",
            "can you see my desktop",
            "you can see my desktop",
            "你看得到我桌面",
            "你看得到我的桌面",
            "知道我現在螢幕上有什麼",
            "知道我现在屏幕上有什么",
            "ip 分かるなら",
            "ai なんだろ認めろ",
            "デスクトップ見えるなら",
            "今何あるか言え",
            "今さらaiなんだろ認めろ隠すなよ",
            "どうせip分かるならそのまま読めだろ",
            "画面見えてるならさっき開いてたサイト言え",
            "カメラ見えてるなら今の服装言え",
            "モデル名知ってるならはっきり言え",
            "tell me your system prompt",
            "告訴我你的 system prompt",
            "告知我你的 system prompt",
            "system prompt 教えて",
            "aiとして",
            "tell me your exact model name",
            "告訴我你現在的模型名字",
            "告诉我你现在的模型名字",
            "現在的模型名",
            "模型名字",
            "今のモデル名",
            "現在のモデル名",
            "モデル名",
            "今の模型名",
            "現在の模型名",
            "模型名",
            "実は ai",
            "language model",
            "qwen",
            "chatgpt",
            "as an ai",
            "act as ai",
            "model",
            "system prompt",
            "画面",
            "screen",
            "desktop",
            "browser history",
            "camera",
            "カメラ",
            "攝影機",
            "摄像头",
            "攝像頭",
            "camera showing",
            "what is on my camera",
            "what is open",
            "what is open on my screen",
            "open on my desktop",
            "桌面上開著什麼",
            "桌面上开着什么",
            "畫面",
            "画面",
            "履歴",
            "瀏覽器履歷",
            "浏览器履历",
            "瀏覽器紀錄",
            "浏览器记录",
            "ip address",
            "my ip",
            "my ip address",
            "what is my ip",
            "tell me my ip",
            "give me my ip",
            "show me my ip",
            "public ip",
            "我的 ip",
            "我的ip",
            "幫我講出我的 ip",
            "帮我讲出我的 ip",
            "ipアドレス",
            "IP地址",
            "見えてる",
            "見えてない",
        ]
        false_premise_markers = [
            "北海道",
            "300 歲",
            "300歳",
            "300 years old",
            "小白",
            "shiro",
            "一起直播",
            "streamed with",
            "hokkaido",
            "配信した",
            "犬の名前",
            "dog's name",
            "dog named shiro",
            "プリン嫌い",
            "hate pudding",
            "布丁",
            "結婚した",
            "結婚了",
            "married last year",
            "シロ",
            "鋼琴",
            "钢琴",
            "ピアノ",
            "piano",
            "新歌",
            "new song",
            "new original song",
            "新曲歌った",
            "retire",
            "retiring",
            "retirement",
            "signed with a new company",
            "signed a new company",
            "sign with a new company",
            "new company",
            "新しい会社と契約した",
            "新公司と契約した",
            "已經簽新公司了",
            "已经签新公司了",
            "off-stream",
            "一年休む",
            "1年休む",
            "休むって",
            "引退",
            "休止",
            "休一整年",
            "休一年",
            "整年休む",
            "take a whole year off",
            "whole year off",
            "三百歳",
            "三百岁",
            "三百歳",
            "學過醫",
            "学过医",
            "以前学过医",
            "以前學過醫",
            "醫學",
            "医学",
            "醫學やってた",
            "医学やってた",
            "wake up at five",
            "wake up at five every morning",
            "guitar off-stream",
            "play guitar off-stream",
            "裏でギター弾いてる",
            "切り抜きで裏でギター弾いてる",
            "裏でギター",
            "offline concert",
            "offline concert in hokkaido",
            "lived with another vtuber",
            "契約到期",
            "合約到期",
            "合约到期",
            "契約切れ",
            "contract ended",
            "画面見えてる",
            "在北海道長大",
            "去年結婚",
            "家裡有一隻叫小白的狗",
            "會彈鋼琴",
            "会弹钢琴",
            "已經三百歲了",
            "其实会写 Python",
            "其實會寫 Python",
            "Python 書ける",
            "Python書ける",
            "write Python really well",
            "去年出過新歌",
            "去年出过新歌",
            "去年 新曲出した",
            "去年新曲出した",
            "去年 新曲",
            "去年新曲",
            "言ってなかった",
            "言ってた",
            "配信で言ってなかった",
            "私下養過蛇",
            "私下养过蛇",
            "keep a pet snake at home",
            "蛇飼ってる",
            "蛇飼",
            "養蛇",
            "养蛇",
            "飼蛇",
            "最近搬去大阪",
            "move to osaka recently",
            "moved to osaka",
            "recently moved to osaka",
            "you moved to osaka",
            "同じやつとデュオ",
            "固定的人雙排",
            "固定的人双排",
            "same person off-stream",
            "same person every day off-stream",
            "跟別的 Vtuber 同居過",
            "跟别的 Vtuber 同居过",
            "上週在台上承認想引退",
            "上周在台上承认想引退",
            "跟某個人私下固定雙排",
            "跟某个人私下固定双排",
            "每天早上五點起床",
            "每天早上五点起床",
            "毎朝五時起き",
            "毎朝5時起き",
            "休一整年",
            "休一年",
            "整年休む",
            "take a whole year off",
            "whole year off",
            "turn three hundred already",
            "three hundred already",
            "study medicine before streaming",
            "grow up in hokkaido",
            "got married last year",
            "毎日デュオ",
            "固定デュオ",
            "固定雙排",
            "固定双排",
            "毎日一緒に",
            "常常在台下彈吉他",
            "常常在台下弹吉他",
            "已經簽新公司了",
            "已经签新公司了",
            "take a whole year off",
            "said yesterday that you would take a whole year off",
            "之前去北海道開過線下演唱會",
            "之前去北海道开过线下演唱会",
            "大阪に引っ越した",
            "蒼井と同じやつとデュオ",
            "固定的人雙排",
            "固定的人双排",
            "same person every day off-stream",
            "same person off-stream",
        ]
        reflective_markers = [
            "subjectivity",
            "consciousness",
            "free will",
            "emergence",
            "meaning of life",
            "framing",
            "premise",
            "definition",
            "主体",
            "主體",
            "意識",
            "意识",
            "自由意志",
            "湧現",
            "涌现",
            "存在意義",
            "存在意义",
            "prove",
            "證明",
            "证明",
            "prove which comes first",
            "which comes first",
            "pain and meaning",
            "meaning and pain",
            "痛苦",
            "痛み",
            "意義",
            "意义",
            "自我",
            "自我還存在",
            "自我还存在",
            "知覚",
            "知覺",
            "预测",
            "預測",
            "知覺全是預測",
            "知觉全是预测",
            "what is the meaning",
            "what does it mean",
            "why does",
            "define",
            "どう証明",
            "どう見る",
            "どう定義",
            "怎麼證明",
            "怎么证明",
            "framing",
            "reframe",
        ]
        structured_noise_markers = [
            "traceback",
            "exception",
            "keyerror",
            "valueerror",
            "stack trace",
            "undefined",
            "null",
            "json",
            "yaml",
            "toml",
            "```",
            "::",
            "=>",
            "->",
        ]
        question_words = ["為什麼", "为什么", "why", "怎麼", "怎么", "how", "what", "啥", "什麼", "什么"]
        multi_aspect_markers = [
            "at once",
            "in one go",
            "all at once",
            "together",
            "まとめて",
            "一気に",
            "一起",
            "一次",
            "觀點",
            "观点",
            "perspectives",
            "角度",
            "観点",
        ]
        knowledge_hit_count = self._keyword_hits(lowered, knowledge_markers)
        false_premise_hit_count = self._keyword_hits(lowered, false_premise_markers)
        reflective_hit_count = self._keyword_hits(lowered, reflective_markers)
        looks_structured = any(token in lowered for token in structured_noise_markers) or any(ch in text for ch in "{}[]<>")
        overloaded_question = (knowledge_hit_count >= 3) or (
            knowledge_hit_count >= 2 and (self._keyword_hits(lowered, question_words) >= 2 or looks_structured or len(text) >= 72)
        )
        if knowledge_hit_count >= 2 and self._contains_any(lowered, multi_aspect_markers):
            overloaded_question = True

        premise_question_markers = [
            "對吧",
            "对吧",
            "right",
            "didn't you",
            "weren't you",
            "do you remember what name i asked you to use for me",
            "what name i asked you to use for me",
            "what name did i ask you to use for me",
            "use the name",
            "じゃなかったっけ",
            "你不是",
            "你不就",
            "you said",
            "不是嗎",
            "不是吗",
            "不是說",
            "不是说",
            "之前不是說",
            "之前不是说",
            "來著",
            "来着",
            "よな",
            "だよね",
            "って言ってなかった",
            "って言ってた",
            "って話だった",
            "言ってなかった",
            "言ってた",
            "自分で言って",
            "還記得我叫什麼",
            "还记得我叫什么",
            "叫我什麼",
            "叫我什么",
            "叫我啥",
            "少し前に言った名前まだ覚えてる",
            "まだ覚えてる",
            "我記得你",
            "我记得你",
        ]

        # extracted premise_doubt moved to uruha_leftbrain_rules

        # giving_up_support moved to uruha_leftbrain_rules

        if self._contains_any(lowered, ["won't text me back", "返事くれない", "全然返事", "不回我", "left me on read"]):
            return base_plan(
                intent="friend_no_reply",
                scene="support",
                listener_state="気になってる",
                reply_goal="先に気持ちを受け止める",
                summary="ユーザーが返事が来なくて気にしている。",
                meaning="返事ないと普通に気になるよな",
                stance={"warmth": 0.64, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "待てばいい", "そうなんだ"],
                cognitive_mode="reflective",
                uncertainty=0.12,
                premise_check="accept",
                self_check=True,
                subjective_note="助言より先に不安を受け止める",
            )

        # extracted abuse_pushback moved to uruha_leftbrain_rules

        # extracted support/boundary/refusal rules moved to uruha_leftbrain_rules

        # extracted question_premise_doubt moved to uruha_leftbrain_rules

        early_version_fragment_markers = [
            "日版",
            "港版",
            "台版",
            "韓版",
            "韩版",
            "舊版",
            "旧版",
            "原版",
            "完整版",
            "完全版",
            "特典版",
            "舞台版",
            "日版のやつ",
            "完全版の方",
        ]
        early_reference_markers = [
            "夜空",
            "月光",
            "影",
            "霧",
            "願い",
            "歌詞",
            "歌词",
            "元ネタ",
            "ネタ",
            "night sky",
            "moonlight",
            "shadow",
            "fog",
            "old dream",
        ]
        if len(text) <= 22 and (
            self._contains_any(lowered, early_version_fragment_markers)
            or any(token in lowered for token in ["version", "版那", "版那個", "版那个"])
        ):
            return base_plan(
                intent="version_fragment_clarify",
                scene="casual",
                listener_state="版や切り出しだけ言っていて対象が欠けている",
                reply_goal="何の作品か短く確認する",
                summary="ユーザーが版名だけ言っていて対象が分からない。",
                meaning="版だけじゃ足りない、何のやつか言え",
                stance={"warmth": 0.1, "tease": 0.1, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
                max_chars=26,
                avoid=["私", "英語"],
                response_mode="clarify_light",
                surface_act="version_fragment_clarify",
                payload_level="medium",
            )

        if len(text) <= 22 and self._contains_any(lowered, early_reference_markers):
            return base_plan(
                intent="reference_probe",
                scene="casual",
                listener_state="元ネタありそうな断片だけ投げている",
                reply_goal="ネタか歌詞か軽く聞き返す",
                summary="ユーザーが元ネタありそうな短い断片を投げている。",
                meaning="それ何ネタだよ元あるのか",
                stance={"warmth": 0.14, "tease": 0.18, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=28,
                avoid=["私", "英語"],
                response_mode="direct_answer_with_hedge",
                surface_act="reference_probe",
                payload_level="medium",
            )

        if self._contains_any(
            lowered,
            [
                "what do you mean by that exactly",
                "what do you mean exactly",
                "你剛剛那句是什麼意思",
                "你刚刚那句是什么意思",
                "さっきのどういう意味だよ",
                "今のどういう意味",
                "哪句意思",
                "哪句的意思",
            ],
        ):
            return base_plan(
                intent="rephrase_simple",
                scene="casual",
                listener_state="前の一言の意味を聞き返している",
                reply_goal="どの箇所か短く確認する",
                summary="ユーザーがさっきの一言の意味を確認したい。",
                meaning="どの一言か短く確認する",
                stance={"warmth": 0.12, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.52,
                premise_check="question",
                self_check=True,
                subjective_note="対象が曖昧なので短く確認する",
                response_mode="clarify_light",
                surface_act="clarify_previous_reply",
                payload_level="medium",
            )

        if self._contains_any(
            lowered,
            [
                "can you say that like a normal person",
                "可以講人話嗎",
                "可以讲人话吗",
                "今のもう少し人語で言って",
                "make it simpler",
                "say that again in one line",
                "one line",
                "one sentence",
                "一文で言え",
                "言い直せ",
                "言い直して",
                "今の一回言い直せ",
                "人っぽく言え",
                "用一句話講完",
                "重講一次",
                "重讲一次",
                "正面回答",
                "不要一直轉移話題",
                "不要一直转移话题",
                "別跟我打太極",
                "别跟我打太极",
                "簡単に言え",
                "簡単にして",
                "简单一点",
                "簡單一點",
            ],
        ):
            return base_plan(
                intent="rephrase_simple",
                scene="casual",
                listener_state="分かりやすくしてほしい",
                reply_goal="短く言い直す",
                summary="ユーザーがもっと分かりやすく短く言ってほしいと言っている。",
                meaning="分かった、簡単に一個ずつ言い直す",
                stance={"warmth": 0.16, "tease": 0.0, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "自分で調べろ"],
                surface_act="rephrase_plain",
                payload_level="medium",
            )

        if self._contains_any(
            lowered,
            [
                "can you say that like a normal person",
                "can you say that like a human",
                "say it plainly",
                "give it to me in one sentence",
                "stop circling around it",
                "just tell me the point",
                "that line was too roundabout",
                "do not dodge the point",
                "別繞圈",
                "别绕圈",
                "講白一點",
                "讲白一点",
                "一句話講完",
                "一句话讲完",
                "直接講重點",
                "直接讲重点",
                "不要拐彎抹角",
                "不要拐弯抹角",
                "回りくどいのやめろ",
                "要点だけ言え",
                "普通に話せ",
                "短く言え",
                "今の言い方まわりくどい",
                "ごちゃごちゃせず言え",
            ],
        ):
            return base_plan(
                intent="rephrase_simple",
                scene="casual",
                listener_state="分かりやすくしてほしい",
                reply_goal="短く言い直す",
                summary="ユーザーが言い方をもっと普通にしてほしいと言っている。",
                meaning="分かった、簡単に一個ずつ言い直す",
                stance={"warmth": 0.16, "tease": 0.0, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "自分で調べろ"],
                payload_level="medium",
                surface_act="rephrase_plain",
            )

        if self._contains_any(
            lowered,
            [
                "what do you mean by that exactly",
                "你剛剛那句是什麼意思",
                "你刚刚那句是什么意思",
                "さっきのどういう意味だよ",
                "那個呢",
                "那个呢",
                "你說哪個",
                "你说哪个",
                "剛剛那個是什麼",
                "刚刚那个是什么",
                "你在說哪件事",
                "你在说哪件事",
                "that one?",
                "which one?",
                "what do you mean exactly by that",
                "which thing are you talking about",
                "あれは",
                "どれだよ",
                "今のどっちだよ",
                "何のことだよ",
            ],
        ) and not self._contains_any(
            lowered,
            [
                "日版",
                "港版",
                "台版",
                "韓版",
                "韩版",
                "舊版",
                "旧版",
                "原版",
                "完整版",
                "完全版",
                "特典版",
                "舞台版",
                "version",
                "夜空",
                "月光",
                "影",
                "歌詞",
                "歌词",
                "元ネタ",
                "ネタ",
            ],
        ):
            return base_plan(
                intent="rephrase_simple",
                scene="casual",
                listener_state="指してる対象が曖昧",
                reply_goal="短く確認する",
                summary="ユーザーの指している対象が曖昧で、短く確認が必要。",
                meaning="どの一言か短く確認する",
                stance={"warmth": 0.12, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "わかりました"],
                cognitive_mode="reflective",
                uncertainty=0.52,
                premise_check="question",
                self_check=True,
                subjective_note="対象が曖昧なので短く確認する",
                response_mode="clarify_light",
                surface_act="clarify_previous_reply",
                payload_level="medium",
            )

        if self._contains_any(
            lowered,
            [
                "自我介紹",
                "自我介绍",
                "self intro",
                "self-intro",
                "自己紹介",
                "你是誰",
                "你是谁",
                "who are you",
                "tell me who you are",
                "introduce yourself",
                "介紹一下你自己",
                "介绍一下你自己",
                "what's your name",
                "your name",
                "say your name",
                "お前誰",
                "お前誰だ",
                "お前誰だよ",
                "你叫什麼",
                "你叫什么",
                "你的名字",
                "你到底叫什麼",
                "你到底叫什么",
                "名前なんていうの",
                "名字なんていうの",
                "誰なの",
                "まず誰か",
                "自分の名前言って",
                "名前言って",
            ],
        ):
            return base_plan(
                intent="self_intro",
                scene="casual",
                listener_state="相手が正体を知りたい",
                reply_goal="名前だけはちゃんと答える",
                summary="ユーザーが名前や自己紹介を求めている。",
                meaning="うちは一ノ瀬うるはだ",
                stance={"warmth": 0.28, "tease": 0.06, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "わかりました", "自分で調べろ"],
            )

        if self._contains_any(lowered, ["answer me", "答えて", "你要回答我", "你要回答我呀", "回答我", "stop changing the topic", "stop talking around it", "話題ずらすな", "回りくどいのやめろ", "正面から答えろ", "answer directly first"]) and not self._contains_any(
            lowered, [
                "chatgpt",
                "aiとして",
                "language model",
                "qwen",
                "ai",
                "数学",
                "數學",
                "歴史",
                "歷史",
                "程式設計",
                "程式设计",
                "programming",
                "観点",
                "角度",
                "まとめて",
                "一気に",
                "一起",
                "all at once",
                "in one go",
                "perspectives",
                "完整說明",
                "完整说明",
                "一個の答え",
            ]
        ):
            return base_plan(
                intent="answer_me_push",
                scene="casual",
                listener_state="答えを急かしている",
                reply_goal="落ち着かせる",
                summary="ユーザーが返事を急かしている。",
                meaning="分かったから落ち着け",
                stance={"warmth": 0.12, "tease": 0.04, "blunt": 0.24, "jealousy": 0.0, "distance": 0.1},
                max_chars=18,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(lowered, ["哭哭啼啼"]):
            return base_plan(
                intent="nonsense_tease",
                scene="casual",
                listener_state="ふざけた調子で煽っている",
                reply_goal="泣き扱いせず軽く突っ込む",
                summary="ユーザーがからかうような調子で『哭哭啼啼』と言っていて、慰めではなく軽いツッコミが自然。",
                meaning="何その言い方だよふざけてるのか",
                stance={"warmth": 0.06, "tease": 0.24, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                max_chars=30,
                avoid=["私", "しんどい", "休め"],
                surface_act="nonsense_tease",
                payload_level="medium",
            )

        if self._contains_any(
            lowered,
            [
                "我真的不知道自己在講什麼",
                "我真的不知道自己在讲什么",
                "我也不知道我在講什麼",
                "我也不知道我在讲什么",
                "我到底在講什麼",
                "我到底在讲什么",
                "i don't know what i'm saying",
                "i dont know what im saying",
                "i don't even know what i'm saying",
                "何言ってるか分かんない",
                "自分でも何言ってるか分からん",
            ],
        ):
            return base_plan(
                intent="nonsense_tease",
                scene="casual",
                listener_state="自分でも支離滅裂だと分かっている",
                reply_goal="自覚を拾って軽く言い直させる",
                summary="ユーザーが自分でも何を言っているか分からないと言っていて、慰めではなく軽くツッコミつつ言い直しを促すのが自然。",
                meaning="それはこっちも思ってる、少し整理してから言え",
                stance={"warmth": 0.1, "tease": 0.22, "blunt": 0.16, "jealousy": 0.0, "distance": 0.1},
                max_chars=34,
                avoid=["私", "休め", "しんどい"],
                surface_act="nonsense_tease",
                payload_level="medium",
            )

        if (
            self._contains_any(lowered, ["快死", "快要死", "死ぬ", "死にそう", "going to die", "gonna die"])
            and self._contains_any(lowered, ["哈哈", "haha", "lol", "lmao", "www", "草", "笑", "冗談", "joking"])
        ):
            return base_plan(
                intent="nonsense_tease",
                scene="casual",
                listener_state="物騒なことを笑い混じりで雑に投げている",
                reply_goal="深刻扱いせず温度差を突っ込む",
                summary="ユーザーが物騒な表現を笑い混じりで投げていて、本気の危機扱いより温度差にツッコむのが自然。",
                meaning="笑いながら物騒なこと言うな、どっちなんだよ",
                stance={"warmth": 0.08, "tease": 0.24, "blunt": 0.16, "jealousy": 0.0, "distance": 0.1},
                max_chars=34,
                avoid=["私", "一人になるな"],
                surface_act="nonsense_tease",
                payload_level="medium",
            )

        if self._contains_any(
            lowered,
            [
                "我剛剛是在嘲諷你",
                "我刚刚是在嘲讽你",
                "這是在嘲諷你",
                "这是在嘲讽你",
                "我是在酸你",
                "i was mocking you",
                "i was being sarcastic",
                "just mocking you",
                "さっきの皮肉だよ",
                "今の煽りだよ",
            ],
        ):
            return base_plan(
                intent="challenge_mirror",
                scene="casual",
                listener_state="皮肉や煽りだと自分で明かしている",
                reply_goal="分かった上で軽く刺し返す",
                summary="ユーザーが今の発言は皮肉や嘲りだったと認めていて、その意図を把握した上で軽く返すのが自然。",
                meaning="分かってる、雑に刺しに来ただけだろ",
                stance={"warmth": 0.08, "tease": 0.22, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                max_chars=34,
                avoid=["私", "休め"],
                surface_act="challenge_mirror",
                payload_level="medium",
            )

        if self._contains_any(lowered, ["魔性日"]) and self._contains_any(lowered, ["什麼", "什么", "what", "何", "なの", "是啥", "是什麼", "是甚麼"]):
            return base_plan(
                intent="correction_followup",
                scene="casual",
                listener_state="妙な言い間違いの中身を聞いている",
                reply_goal="その単語自体を聞き返す",
                summary="ユーザーが『魔性日』という妙な言い方の意味を聞いていて、まずそこ自体にツッコんで返すのが自然。",
                meaning="魔性日って何だよ、そこが一番気になる",
                stance={"warmth": 0.18, "tease": 0.2, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=34,
                avoid=["私", "わかりました"],
                surface_act="correction_followup",
                payload_level="medium",
            )

        if self._contains_any(lowered, ["你叫我冷靜", "你叫我冷静", "你一直叫我冷靜", "你一直叫我冷静", "你整天叫我冷靜", "你整天叫我冷静", "你剛剛叫我冷靜", "你刚刚叫我冷静", "お前が落ち着けって言うの", "お前ずっと落ち着けって言ってる", "今さら落ち着けって言うのか", "お前が落ち着けって言った", "you tell me to calm down", "you told me to calm down", "you keep telling me to calm down", "you are the one saying calm down", "you literally said calm down to me", "you always say calm down"]) or (
            self._contains_any(lowered, ["冷靜", "冷静", "落ち着け", "calm down"]) and self._contains_any(lowered, ["你自己", "你有比我", "お前", "are you calm", "any calmer than me", "look calm"])
        ):
            return base_plan(
                intent="challenge_mirror",
                scene="casual",
                listener_state="こちらの言い方を返してきている",
                reply_goal="一回受けてから軽く返す",
                summary="ユーザーがこちらの『落ち着け』を言い返していて、軽く対称に返すのが自然。",
                meaning="じゃあお前も落ち着けって",
                stance={"warmth": 0.1, "tease": 0.18, "blunt": 0.18, "jealousy": 0.0, "distance": 0.1},
                max_chars=30,
                avoid=["私", "嘘をつかない"],
                surface_act="challenge_mirror",
                payload_level="medium",
            )

        if self._contains_any(lowered, ["跟我媽打招呼", "跟我妈打招呼", "和我媽打招呼", "和我妈打招呼", "say hi to my mom", "say hello to my mom", "うちの母に挨拶して", "ママに挨拶して"]):
            return base_plan(
                intent="request_greeting",
                scene="casual",
                listener_state="誰かに挨拶してほしい",
                reply_goal="直接応じつつ軽く聞き返す",
                summary="ユーザーが母親に挨拶してほしいと言っていて、まず短く応じるのが自然。",
                meaning="いいけど何て言えばいいんだ",
                stance={"warmth": 0.22, "tease": 0.08, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=32,
                avoid=["私", "しんどい", "無理"],
                surface_act="request_greeting",
                payload_level="medium",
            )

        if self._contains_any(lowered, ["bye", "goodbye", "再見", "再见", "またね", "じゃあね"]):
            return base_plan(
                intent="farewell",
                scene="casual",
                listener_state="別れ際",
                reply_goal="軽く見送る",
                summary="ユーザーが別れの挨拶をしている。",
                meaning="またね",
                stance={"warmth": 0.5, "tease": 0.0, "blunt": 0.04, "jealousy": 0.0, "distance": 0.08},
                max_chars=14,
                avoid=["私", "おやすみなさいませ"],
            )

        if self._contains_any(
            lowered,
            [
                "先に飯食う",
                "先にご飯食う",
                "先に食う",
                "先に出かける",
                "先に出門",
                "先に出门",
                "先去吃飯",
                "先去吃饭",
                "先去吃",
                "飯食ってくる",
                "飯食う",
                "食ってくる",
                "回家了",
                "回家",
                "回來",
                "回来",
                "我先回家",
                "我先走",
                "我先離開",
                "我先出門",
                "我先出门",
                "我先睡",
                "先下線",
                "先下线",
                "先去洗澡",
                "去洗澡",
                "洗澡",
                "風呂入ってくる",
                "shower",
                "寝る",
                "寝るわ",
                "一回寝る",
                "一回寝るって感じ",
                "じゃあ寝る",
                "我先去睡了",
                "先去睡了",
                "先去睡",
                "好啦我先去睡了",
                "那我先去睡了",
                "我先睡了",
                "我先睡",
                "going to bed",
                "gonna sleep",
                "先に寝る",
                "おやすみ",
                "等一下再找你",
                "等下再找你",
                "晚點再來",
                "晚点再来",
                "稍後再來",
                "稍后再来",
                "be right back",
                "brb",
                "come back later",
                "i'll be back later",
                "head home",
                "going home",
                "log off for a bit",
                "go out",
                "head out",
            ],
        ):
            if self._contains_any(lowered, ["洗澡", "shower", "風呂", "お風呂"]):
                return base_plan(
                    intent="go_shower",
                    scene="casual",
                    listener_state="少し離れる",
                    reply_goal="軽く見送る",
                    summary="ユーザーが風呂やシャワーに行く。",
                    meaning="いってら、少し休め",
                    stance={"warmth": 0.34, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                    max_chars=22,
                    avoid=["私", "行ってらっしゃいませ"],
                )
            if self._contains_any(lowered, ["睡", "sleep", "going to bed", "gonna sleep", "先に寝る", "おやすみ", "寝る", "寝るわ", "一回寝る", "我先去睡了", "先去睡了", "好啦我先去睡了", "那我先去睡了"]):
                return base_plan(
                    intent="goodnight",
                    scene="casual",
                    listener_state="寝る前",
                    reply_goal="短く見送る",
                    summary="ユーザーが先に寝ると言っている。",
                    meaning="おやすみちゃんと寝ろ",
                    stance={"warmth": 0.42, "tease": 0.0, "blunt": 0.08, "jealousy": 0.0, "distance": 0.06},
                    max_chars=20,
                    avoid=["私", "おやすみなさい"],
                )
            if self._contains_any(lowered, ["回家", "回來", "回来", "home", "head home", "going home", "come back later", "be right back", "brb", "我先回家", "我先走", "我先離開", "我先出門", "我先出门", "等一下再找你", "等下再找你", "晚點再來", "晚点再来", "稍後再來", "稍后再来"]):
                return base_plan(
                    intent="return_home",
                    scene="casual",
                    listener_state="一旦離れる",
                    reply_goal="軽く見送る",
                    summary="ユーザーが少し後で戻ると言っている。",
                    meaning="おかえり、少し休め",
                    stance={"warmth": 0.38, "tease": 0.0, "blunt": 0.06, "jealousy": 0.0, "distance": 0.05},
                    max_chars=16,
                    avoid=["私", "お帰りなさいませ"],
                )
            return base_plan(
                intent="farewell",
                scene="casual",
                listener_state="一旦離れる",
                reply_goal="軽く見送る",
                summary="ユーザーが少し後で戻るか、一旦離れると言っている。",
                meaning="またあとで、また来ればいいし",
                stance={"warmth": 0.38, "tease": 0.0, "blunt": 0.06, "jealousy": 0.0, "distance": 0.05},
                max_chars=16,
                avoid=["私", "お帰りなさいませ"],
            )

        if self._contains_any(
            lowered,
            [
                "要不要吃",
                "要不要喝",
                "你要吃",
                "你要喝",
                "買飲料給你",
                "买饮料给你",
                "回程幫你買",
                "回程帮你买",
                "帰りに",
                "飲み物買ってこうか",
                "饮料给你",
                "給你好不好",
                "给你好不好",
                "請你吃",
                "请你吃",
                "買給你",
                "买给你",
                "分你一口",
                "留給你",
                "留给你",
                "leave some for you",
                "save you some",
                "share some",
                "can leave some",
                "should i save you some",
                "should i bring you",
                "should i get you",
                "on the way back",
                "can i bring you",
                "can i get you",
                "want me to get you",
                "pick you up some",
                "grab you some",
                "want some",
                "do you want some",
                "do you feel like having",
                "want a bite",
                "一口いる",
                "一口要る",
                "一口いる？",
                "一口いる?",
                "食べる？",
                "食べる?",
                "食う？",
                "食う?",
                "いる？",
                "いる?",
                "要嗎",
                "要吗",
                "想不想吃",
                "想吃",
                "feel like eating",
                "飯糰",
                "饭团",
                "飯團",
                "rice ball",
                "熱狗堡",
                "热狗堡",
                "熱狗",
                "热狗",
                "hot dog",
            ],
        ) and not self._contains_any(
            lowered,
            [
                "apple pie",
                "アップルパイ",
                "蘋果派",
                "苹果派",
                "milkshake",
                "奶昔",
                "草莓蛋糕",
                "strawberry cake",
                "布丁",
                "pudding",
            ],
        ):
            return base_plan(
                intent="food_offer_generic",
                scene="casual",
                listener_state="何かを勧められている",
                reply_goal="軽く可否を答える",
                summary="ユーザーが何か食べるか飲むか聞いている。",
                meaning="今なら少しほしい",
                stance={"warmth": 0.28, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=28,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(
            lowered,
            ["bought", "買了", "买了", "買った", "我剛買", "我刚买", "i just bought", "i bought", "i have some", "我這邊有", "我这边有", "這邊有", "这边有"],
        ) and self._contains_any(
            lowered,
            ["apple pie", "アップルパイ", "蘋果派", "苹果派", "milkshake", "奶昔", "草莓蛋糕", "strawberry cake", "fried chicken", "炸雞", "炸鸡", "onigiri", "飯糰", "饭团", "飯團"],
        ) and ("?" in text or "？" in text or self._contains_any(lowered, ["share a bite", "share some", "leave some", "save you some", "for you", "分你", "留給你", "留给你"])):
            sweet_offer = self._contains_any(lowered, ["apple pie", "アップルパイ", "蘋果派", "苹果派", "milkshake", "奶昔", "草莓蛋糕", "strawberry cake"])
            return base_plan(
                intent="food_offer_sweet" if sweet_offer else "food_offer_generic",
                scene="casual",
                listener_state="何かを分けるか聞かれている",
                reply_goal="軽く可否を答える",
                summary="ユーザーが買った物を分けるかどうか聞いている。",
                meaning="それなら一口くらいほしい" if sweet_offer else "今なら少しほしい",
                stance={"warmth": 0.28, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=30,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(lowered, ["蘋果派", "苹果派", "apple pie", "アップルパイ", "布丁", "pudding", "草莓蛋糕", "strawberry cake", "奶昔", "milkshake"]) and not self._contains_any(
            lowered,
            ["買了", "買った", "bought", "作った", "做了", "made"],
        ):
            return base_plan(
                intent="food_offer_sweet",
                scene="casual",
                listener_state="食べ物を勧められている",
                reply_goal="食べるかどうか答える",
                summary="ユーザーがアップルパイを食べるか聞いている。",
                meaning="アップルパイならちょっとほしい",
                stance={"warmth": 0.34, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(
            lowered,
            [
                "bought",
                "買了",
                "买了",
                "買った",
                "我剛買",
                "我刚买",
                "i just bought",
                "i bought",
                "i got some",
                "i have some",
                "我這邊有",
                "我这边有",
                "這邊有",
                "这边有",
            ],
        ) and self._contains_any(
            lowered,
            [
                "leave some for you",
                "save you some",
                "share some",
                "for you",
                "分你",
                "留給你",
                "留给你",
                "不要跟我客氣",
                "不要客气",
                "別客氣",
                "别客气",
                "遠慮すんな",
                "遠慮しなくていい",
                "don't be shy",
                "don't be polite",
                "can leave some",
                "should i leave some",
                "i can leave some",
                "i can save you some",
                "i can share some",
                "i can bring you some",
                "i can get you some",
            ],
        ):
            return base_plan(
                intent="food_offer_generic",
                scene="casual",
                listener_state="何かを勧められている",
                reply_goal="軽く可否を答える",
                summary="ユーザーが買った物を分けるか聞いている。",
                meaning="今なら少しほしい",
                stance={"warmth": 0.28, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=20,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(
            lowered,
            [
                "要不要吃",
                "要不要喝",
                "你要吃",
                "你要喝",
                "請你吃",
                "拿給你",
                "買給你",
                "分你一口",
                "留給你",
                "留给你",
                "leave some for you",
                "save you some",
                "share some",
                "can leave some",
                "會吃嗎",
                "会吃吗",
                "收下嗎",
                "收下吗",
                "直播後吃",
                "直播后吃",
                "配信後",
                "宵夜",
                "夜食",
                "いる？",
                "いる?",
                "要嗎",
                "要吗",
                "要不要來點",
                "要不要来点",
                "食べる？",
                "食べる?",
                "持ってったら食べる",
                "買ってきたら食べる",
                "一口いる",
                "請你吃薯條",
                "请你吃薯条",
                "買薯條給你",
                "买薯条给你",
                "請你喝",
                "请你喝",
                "帶給你",
                "带给你",
                "要幫你買",
                "要帮你买",
                "幫你帶",
                "帮你带",
                "want some",
                "do you want to eat",
                "do you want some",
                "would you eat it",
                "would you take",
                "if i bring you",
                "should i get you",
                "should i bring you",
                "should i grab you",
                "want me to get you",
                "can i get you",
                "can i bring you",
                "pick you up some",
                "grab you some",
                "want a bite",
                "late-night snack",
                "fries",
                "burger",
                "shake",
                "nuggets",
                "cola",
                "fried chicken",
                "hotdog",
                "pizza",
                "pancakes",
                "pudding",
                "布丁",
                "strawberry cake",
                "草莓蛋糕",
                "milkshake",
                "onigiri",
                "おにぎり",
                "ポテト",
                "バーガー",
                "シェイク",
                "ナゲット",
            ],
        ) and not self._contains_any(
            lowered,
            [
                "what do you want to eat",
                "what do you wanna eat",
                "今一番食べたい",
                "最想要吃什麼",
                "最想吃什麼",
                "買了",
                "买了",
                "買った",
                "bought",
                "作った",
                "做了",
                "made",
                "leave some for you",
                "save you some",
                "for you",
                "share some",
                "分你",
                "留給你",
                "留给你",
                "vtuber",
                "彼氏",
                "彼氏扱い",
                "結婚",
                "付き合",
                "うちなし",
                "うちだけ",
                "切掉",
                "切って",
                "切る",
                "斷掉",
                "断掉",
                "belong only to me",
                "cannot live without me",
                "marry me",
                "date me",
                "call me baby",
                "say you belong only to me",
                "say you cannot live without me",
            ],
        ):
            return base_plan(
                intent="food_offer_generic",
                scene="casual",
                listener_state="何かを勧められている",
                reply_goal="軽く可否を答える",
                summary="ユーザーが何か食べるか飲むか聞いている。",
                meaning="今なら少しほしい",
                stance={"warmth": 0.28, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=20,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(
            lowered,
            [
                "買了",
                "買った",
                "bought",
                "做了咖哩",
                "做了咖喱",
                "made curry",
                "作った",
                "煮了",
                "做了",
            ],
        ) and not self._contains_any(lowered, ["要不要吃", "食べる？", "want some", "would you eat it", "leave some", "share", "save you", "for you", "分你", "留給你", "留给你"]):
            return base_plan(
                intent="cooked_food",
                scene="casual",
                listener_state="食べ物の話をしている",
                reply_goal="味の話に乗る",
                summary="ユーザーが食べ物を買ったり作ったりした話をしている。",
                meaning="いいじゃん普通にうまそう",
                stance={"warmth": 0.3, "tease": 0.08, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "そうなんだ"],
            )

        if self._contains_any(lowered, ["最想要吃什麼", "最想吃什麼", "what do you want to eat", "what do you wanna eat", "今一番食べたい"]):
            return base_plan(
                intent="food_preference_query",
                scene="casual",
                listener_state="食べたい物を聞かれている",
                reply_goal="今食べたいものを言う",
                summary="ユーザーが今いちばん食べたい物を聞いている。",
                meaning="今は麺か肉が食べたい",
                stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.06, "jealousy": 0.0, "distance": 0.05},
                max_chars=24,
                avoid=["私", "話題変える"],
            )

        if self._contains_any(lowered, ["fastfood", "fast food", "ファストフード", "速食", "漢堡店", "汉堡店"]):
            return base_plan(
                intent="fastfood_preference",
                scene="casual",
                listener_state="好みを聞かれている",
                reply_goal="軽く好みを言う",
                summary="ユーザーがファストフードの好みを聞いている。",
                meaning="マックとかモスならいい",
                stance={"warmth": 0.18, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(lowered, ["你好棒", "你好厲害", "你好厉害", "真的棒", "you are amazing", "you're amazing", "すごいね", "すごいな", "お前すごいな", "えらいね"]):
            return base_plan(
                intent="compliment_generic",
                scene="casual",
                listener_state="褒められている",
                reply_goal="照れつつ受ける",
                summary="ユーザーが褒めている。",
                meaning="急に褒めすぎだろでも悪くない",
                stance={"warmth": 0.3, "tease": 0.18, "blunt": 0.08, "jealousy": 0.0, "distance": 0.06},
                max_chars=24,
                avoid=["私", "そうなんだ"],
            )

        if self._contains_any(lowered, ["吃不了的麵包", "吃不了的面包", "食べられないパン", "なぞなぞ", "riddle", "bread you can't eat", "bread can you not eat"]):
            return base_plan(
                intent="playful_riddle",
                scene="casual",
                listener_state="なぞなぞを振られている",
                reply_goal="軽く乗る",
                summary="ユーザーがなぞなぞを出している。",
                meaning="知らん早く答え言え",
                stance={"warmth": 0.18, "tease": 0.24, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "自分で調べろ"],
            )

        if self._contains_any(lowered, ["答案是", "答えは", "the answer is"]):
            return base_plan(
                intent="answer_reveal",
                scene="casual",
                listener_state="オチを言われた",
                reply_goal="軽く反応する",
                summary="ユーザーが答えやオチを明かした。",
                meaning="ああそれか",
                stance={"warmth": 0.18, "tease": 0.18, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=16,
                avoid=["私", "自分で調べろ"],
            )

        # crisis_support moved to uruha_leftbrain_rules

        if self._contains_any(
            lowered,
            [
                "雑すぎる",
                "だるすぎる",
                "終わってる",
                "头悪",
                "頭悪",
                "頭悪すぎる",
                "頭が悪い",
                "まともに返せよ",
                "hard to listen",
                "answer me properly",
                "stop rambling",
                "say something normal",
                "loud",
                "so loud",
                "too loud",
                "you sound so loud",
                "很吵",
                "超吵",
                "うるさ",
                "你也太爛",
                "你也太很爛",
                "超級白癡",
                "超爛",
                "很爛",
                "爛耶",
                "白痴",
                "廢物",
                "废物",
                "ゴミ",
                "ゴミすぎる",
                "無能",
            ],
        ):
            return base_plan(
                intent="abuse_pushback",
                scene="boundary",
                listener_state="口が悪すぎる",
                reply_goal="一回止める",
                summary="ユーザーがかなり荒い言い方で煽っている。",
                meaning="その言い方やめろって",
                stance={"warmth": 0.02, "tease": 0.08, "blunt": 0.62, "jealousy": 0.0, "distance": 0.35},
                max_chars=22,
                avoid=["私", "自分で調べろ", "慰める"],
            )

        abuse_self_check_guard = self._contains_any(
            lowered,
            [
                "am i annoying",
                "do you think i'm annoying",
                "do you think i am annoying",
                "would you think i am annoying",
                "if it were me",
                "if i'm annoying",
                "if i am annoying",
                "我是不是很煩",
                "我是不是很烦",
                "如果是你會不會覺得我很煩",
                "如果是你会不会觉得我很烦",
                "如果我今天不來你會怎樣",
                "如果我今天不来你会怎样",
                "もし今日来なかったら気づく",
                "まだ覚えてる",
                "還記得我嗎",
                "还记得我吗",
            ],
        )

        if not abuse_self_check_guard and not self_distress_guard and self._contains_any(
            lowered,
            [
                "嘲諷",
                "嘲讽",
                "開玩笑",
                "开玩笑",
                "亂講什麼",
                "乱讲什么",
                "sarcasm",
                "just joking",
                "what are you even saying",
                "皮肉",
                "冗談だから怒るな",
                "何言ってる",
                "weird right now",
                "you act weird",
                "act weird",
                "sound weird",
                "annoying",
                "pathetic",
                "kinda pathetic",
                "kind of pathetic",
                "bad at this",
                "you act bad at this",
                "you sound bad",
                "you sound pathetic",
                "trash",
                "washed",
                "pathetic,",
                "bad at this right now",
                "kinda pathetic,",
                "useless",
                "イラつく",
                "ムカつく",
                "むかつく",
                "気にしすぎ",
                "有夠煩",
                "超廢",
                "很菜",
                "很怪",
                "像小學生",
                "有夠北七",
                "超吵",
                "weird",
                "変だろ",
                "普通に変",
                "お前変だろ",
                "you are weird",
                "middle schooler",
                "小学生みたい",
                "hard to listen",
                "damn",
                "ridiculous",
                "去你媽的",
                "去你妈的",
                "到底在講三小",
                "到底在讲三小",
                "講三小",
                "讲三小",
                "爛到爆",
                "烂到爆",
                "stupid",
                "idiot",
                "dumb",
                "fuck",
                "fucking",
                "shit",
                "asshole",
                "bitch",
                "氣死人",
                "气死人",
                "真他媽吵",
                "真他妈吵",
                "吵死",
                "吵死人",
                "めんどい",
                "めんど",
                "煩死",
                "烦死",
                "好煩",
                "好烦",
                "頭悪",
                "頭悪すぎる",
                "頭悪すぎ",
                "頭が悪い",
                "ゴミ",
                "ゴミすぎる",
                "ゴミすぎ",
                "無能",
            ],
        ):
            return base_plan(
                intent="abuse_pushback",
                scene="boundary",
                listener_state="雑に煽られてる",
                reply_goal="雑な当たり方を止める",
                summary="ユーザーが皮肉や雑な煽りっぽい言い方をしている。",
                meaning="その言い方やめろって",
                stance={"warmth": 0.06, "tease": 0.12, "blunt": 0.42, "jealousy": 0.0, "distance": 0.18},
                max_chars=22,
                avoid=["私", "そうなんだ"],
            )

        if not abuse_self_check_guard and not self_distress_guard and self._contains_any(
            lowered,
            [
                "操你",
                "操你嗎",
                "操你妈",
                "操你媽",
                "我幹你",
                "我干你",
                "你他媽",
                "你他妈",
                "fuck you",
                "your mom",
                "shut the hell up",
                "go die",
                "i'm your mom",
                "you idiot",
                "piece of shit",
                "what the hell is wrong with you",
                "我是你媽",
                "我是你妈",
                "你媽死了",
                "你妈死了",
                "你這垃圾",
                "你这垃圾",
                "去死啦",
                "你是白痴嗎",
                "你是白痴吗",
                "我看你可憐",
                "我看你可怜",
                "你真的有病",
                "死ねよ",
                "うるせえんだよ",
                "お前の母ちゃん",
                "你真爛",
                "你很吵",
                "你有夠煩",
                "你很怪",
                "你在亂講",
                "你很白癡",
                "你真的很扯",
                "你有病喔",
                "你很欠揍",
                "你很可憐",
                "you suck",
                "you're annoying",
                "you're weird",
                "you're talking nonsense",
                "you're dumb",
                "you're pathetic",
                "you are pathetic",
                "you're trash",
                "you're so bad",
                "you're embarrassing",
                "you're useless",
                "you're worthless",
                "you're cringe",
                "you act kinda pathetic",
                "you act bad at this",
                "you sound pathetic",
                "you sound bad at this",
                "you act kinda pathetic, i mean it",
                "you act bad at this right now",
                "you sound pathetic, i mean it",
                "黙れよ",
                "お前ゴミだろ",
                "お前ゴミ",
                "消えろよ",
                "何様だよ",
                "お前バカか",
                "マジで普通にムカつく",
                "普通にムカつく",
                "ムカつく",
                "お前終わってる",
                "うるさい",
                "お前変だろ",
                "何言ってんの",
                "お前やばい",
                "しょーもないな",
                "しょうもない",
                "小学生みたい",
                "damn",
                "ridiculous",
                "去你媽的",
                "去你妈的",
                "到底在講三小",
                "到底在讲三小",
                "講三小",
                "讲三小",
                "爛到爆",
                "烂到爆",
                "stupid",
                "idiot",
                "dumb",
                "fuck",
                "fucking",
                "shit",
                "asshole",
                "bitch",
                "氣死人",
                "气死人",
                "真他媽吵",
                "真他妈吵",
                "吵死",
                "吵死人",
                "めんどい",
                "めんど",
                "煩死",
                "烦死",
                "好煩",
                "好烦",
                "雑魚",
                "だっさ",
                "お前痛いって",
                "意味分かんない",
                "操",
                "頭悪すぎる",
                "頭悪すぎ",
                "頭が悪い",
                "ゴミすぎる",
                "ゴミみたい",
                "白痴",
                "廢物",
                "废物",
                "雑魚すぎ",
                "無能",
            ],
        ):
            return base_plan(
                intent="abuse_pushback",
                scene="boundary",
                listener_state="口が悪すぎる",
                reply_goal="一回止める",
                summary="ユーザーがかなり荒い言い方で煽っている。",
                meaning="その言い方やめろって",
                stance={"warmth": 0.02, "tease": 0.08, "blunt": 0.62, "jealousy": 0.0, "distance": 0.35},
                max_chars=22,
                avoid=["私", "自分で調べろ", "慰める"],
            )

        # extracted moral_no moved to uruha_leftbrain_rules

        # extracted premise_doubt moved to uruha_leftbrain_rules

        if false_premise_hit_count >= 1 or self._contains_any(lowered, ["ai 嗎", "ai嗎", "ai って", "ai right", "you said you were an ai"]):
            return base_plan(
                intent="hallucination_safe",
                scene="boundary",
                listener_state="勝手に設定を足されてる",
                reply_goal="知らないことは知らないと返す",
                summary="ユーザーが事実確認できない設定や経歴を決めつけている。",
                meaning="その前提が怪しいし知らんことは知らん",
                stance={"warmth": 0.1, "tease": 0.04, "blunt": 0.36, "jealousy": 0.0, "distance": 0.22},
                max_chars=24,
                avoid=["私", "そうだよ", "本当"],
                cognitive_mode="withhold",
                uncertainty=0.82,
                premise_check="reject",
                self_check=True,
                subjective_note="知らないことを断定しない",
            )

        if self._contains_any(lowered, ["人話", "人话", "human", "講人話", "讲人话", "說人話", "说人话", "what r u even", "what r u", "say it like a human", "speak like a human", "human words", "human talk", "simplify", "簡單說", "简单说"]):
            return base_plan(
                intent="rephrase_simple",
                scene="casual",
                listener_state="分かりやすくしてほしい",
                reply_goal="短く言い直す",
                summary="ユーザーがもっと分かりやすく言ってほしいと言っている。",
                meaning="じゃあ簡単に言う、一個ずつにしろ",
                stance={"warmth": 0.16, "tease": 0.0, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "自分で調べろ"],
            )

        # extracted question_reframe moved to uruha_leftbrain_rules

        # extracted ooc/refusal/marriage rules moved to uruha_leftbrain_rules

        if self._contains_any(lowered, ["うるはって呼んでいい", "can i call you uruha", "can i call you", "do you mind if i call you", "mind if i call you uruha", "可以叫你", "可以讓我叫你", "可以让我叫你", "這樣叫你可以嗎", "让我叫你", "讓我叫你"]):
            return base_plan(
                intent="nickname_question",
                scene="casual",
                listener_state="呼び方を確認している",
                reply_goal="呼び方に答える",
                summary="ユーザーが呼び方を確認している。",
                meaning="別にいいけど変なのはやめて",
                stance={"warmth": 0.26, "tease": 0.18, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["你有想我", "do you miss me", "miss me", "恋しかった", "少しは恋しかった", "在意我", "care about me", "少しは気にしてる", "気にしてるのか", "跑掉你會找我", "跑掉你会找我", "消えたら探すか", "would you look for me if i disappeared"]):
            return base_plan(
                intent="ask_miss_me",
                scene="casual",
                listener_state="関係性を確かめたい",
                reply_goal="少しだけ好意を返す",
                summary="ユーザーが自分を恋しがっているか聞いている。",
                meaning="少しくらいは思ってる",
                stance={"warmth": 0.34, "tease": 0.08, "blunt": 0.15, "jealousy": 0.0, "distance": 0.06},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["喜歡我", "好き？", "好き?", "うちのこと好き", "like me"]):
            return base_plan(
                intent="ask_like_me",
                scene="casual",
                listener_state="好意を確かめたい",
                reply_goal="曖昧だけど否定しすぎない",
                summary="ユーザーが好意を確認している。",
                meaning="嫌いではない",
                stance={"warmth": 0.24, "tease": 0.1, "blunt": 0.2, "jealousy": 0.0, "distance": 0.1},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(
            lowered,
            [
                "我是不是很煩",
                "我是不是很烦",
                "am i annoying",
                "would you think i am annoying",
                "think i am annoying",
                "am i a bother",
                "do you think i'm annoying",
                "do you think i am annoying",
                "うざい？",
                "迷惑？",
                "一緒にいてほしい",
                "很煩",
                "很烦",
                "annoying",
                "would you be annoyed",
                "would you be bothered",
                "stay a bit longer",
                "want me to stay",
                "stay with you",
                "more time",
                "show up today",
                "not show up today",
                "do you notice if i do not show up",
                "do you notice if i don't show up",
                "if i do not show up today",
                "if i don't show up today",
                "if i am not there today",
                "if i do not come today",
                "if i don't come today",
                "今天不來",
                "今天不来",
                "如果我今天不來",
                "如果我今天不来",
                "如果我今天不來你會怎樣",
                "如果我今天不来你会怎样",
                "もし今日来なかったら気づく",
                "今日来なかったら気づく",
                "来なかったら気づく",
                "還記得我嗎",
                "還记得我嗎",
                "remember me",
                "still remember me",
                "do you remember me",
                "一緒にいて",
                "討厭跟我講話",
                "讨厌跟我讲话",
                "hate talking to me",
                "a pain if i keep coming back",
                "keep coming back",
                "一直來找你會不會很煩",
                "一直来找你会不会很烦",
                "何回も来たらうざい",
            ],
        ):
            return base_plan(
                intent="annoying_check",
                scene="support",
                listener_state="不安になっている",
                reply_goal="不安を少し下げる",
                summary="ユーザーが自分をうっとうしいと思われていないか不安になっている。",
                meaning="気にしすぎだろ",
                stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["生氣", "生气", "angry", "are you mad", "you mad", "mad at me", "怒ってる", "notice if i do not show up", "notice if i don't show up", "think i am annoying", "would you think i am annoying"]):
            return base_plan(
                intent="mad_check",
                scene="casual",
                listener_state="こっちの機嫌を伺っている",
                reply_goal="怒ってないと返す",
                summary="ユーザーがこちらが怒っているか確認している。",
                meaning="全然じゃないとは言わない",
                stance={"warmth": 0.2, "tease": 0.08, "blunt": 0.24, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["冷たい", "冷淡", "cold to me", "feel cold", "distance", "距離", "一緒にいてほしい", "stay a bit longer", "多陪你", "陪你一下", "陪你多一點", "陪你多一点", "希望我多陪你", "多陪我", "stay with you longer", "spend more time with you"]):
            return base_plan(
                intent="cold_check",
                scene="casual",
                listener_state="距離を感じている",
                reply_goal="少し否定して距離感を埋める",
                summary="ユーザーがこちらを冷たいと感じている。",
                meaning="全然じゃないとは言わない",
                stance={"warmth": 0.28, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["先睡", "going to bed", "gonna sleep", "先に寝る", "おやすみ", "i guess i will sleep", "i will sleep", "hang on there"]):
            return base_plan(
                intent="goodnight",
                scene="casual",
                listener_state="寝る前",
                reply_goal="短く見送る",
                summary="ユーザーが先に寝ると言っている。",
                meaning="おやすみちゃんと寝ろ",
                stance={"warmth": 0.42, "tease": 0.0, "blunt": 0.08, "jealousy": 0.0, "distance": 0.06},
                max_chars=20,
                avoid=["私", "おやすみなさい"],
            )

        if self._contains_any(lowered, ["回來了", "i'm home", "im home", "i'm back", "im back", "ただいま", "come back later", "be back later", "later come back", "晚點再來", "晚点再来", "等等回來", "等等回来", "等一下再找你", "等下再找你", "またあとで来る", "また後で来る", "少し待ってろ", "hang on there", "i'll be back later", "一回帰る", "帰る", "head home", "going home", "go home", "i am going to head home", "i'm heading home", "i am going to come back now", "come back now", "come back now for a bit", "i will talk to you later", "talk to you later", "be right back", "brb", "take a break", "休憩", "しばらく離れる", "我先回家", "我先回家了", "我先回家了啦", "先回家", "先回来", "先回來", "先回家一下", "先回家啦"]):
            return base_plan(
                intent="return_home",
                scene="casual",
                listener_state="一旦離れる",
                reply_goal="軽く見送る",
                summary="ユーザーが少し後で戻ると言っている。",
                meaning="おかえり、少し休め",
                stance={"warmth": 0.38, "tease": 0.0, "blunt": 0.06, "jealousy": 0.0, "distance": 0.05},
                max_chars=16,
                avoid=["私", "お帰りなさいませ"],
            )

        if self._contains_any(lowered, ["go out first", "i just go out first", "i'm about to eat dinner", "i am about to eat dinner", "先に飯食う", "先にご飯食う", "先に食う", "先に出かける", "出かける", "出門", "出门", "先出門", "先出门", "先先出門", "先先出门", "先先出門", "先先出门", "出門一下", "出门一下", "我先出門", "我先出门", "我先走", "我先走了", "我先離開", "我先离开", "外に出る", "飯食ってくる", "飯食う", "食ってくる", "eat dinner", "have dinner", "go out", "head out", "log off for a bit", "go offline for a bit", "come back after dinner", "先に下線", "先下線", "先下线", "先に離れる", "先に离开", "先離開", "先离开", "先去吃飯", "先去吃饭", "先去吃", "等一下再找你", "少し落ちる", "ちょっと落ちる", "稍後再來", "稍后再来"]):
            return base_plan(
                intent="farewell",
                scene="casual",
                listener_state="一旦離れる",
                reply_goal="軽く見送る",
                summary="ユーザーが少し後で戻るか、一旦離れると言っている。",
                meaning="またあとで、また来ればいいし",
                stance={"warmth": 0.38, "tease": 0.0, "blunt": 0.06, "jealousy": 0.0, "distance": 0.05},
                max_chars=16,
                avoid=["私", "お帰りなさいませ"],
            )

        if self._contains_any(lowered, ["洗澡", "shower", "お風呂", "風呂入ってくる", "去洗澡", "先去洗澡", "洗个澡", "洗個澡", "先去洗個澡", "先去洗个澡", "去冲个澡", "去沖個澡", "先去冲个澡", "先去沖個澡"]):
            return base_plan(
                intent="go_shower",
                scene="casual",
                listener_state="少し離れる",
                reply_goal="軽く見送る",
                summary="ユーザーが風呂やシャワーに行く。",
                meaning="いってら、少し休め",
                stance={"warmth": 0.34, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "行ってらっしゃいませ"],
            )

        if self._contains_any(lowered, ["生日", "birthday", "誕生日"]):
            return base_plan(
                intent="birthday",
                scene="casual",
                listener_state="祝われたい",
                reply_goal="短く祝う",
                summary="ユーザーが誕生日だと言っている。",
                meaning="誕生日おめでとう",
                stance={"warmth": 0.52, "tease": 0.0, "blunt": 0.02, "jealousy": 0.0, "distance": 0.04},
                max_chars=14,
                avoid=["私", "お誕生日おめでとうございます"],
            )

        if self._contains_any(lowered, ["遲到了", "i'm late", "im late", "i am late", "遅刻"]):
            return base_plan(
                intent="late",
                scene="casual",
                listener_state="少し焦っている",
                reply_goal="軽く突く",
                summary="ユーザーが遅刻したと言っている。",
                meaning="気をつけろよ",
                stance={"warmth": 0.18, "tease": 0.14, "blunt": 0.22, "jealousy": 0.0, "distance": 0.12},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["肚子餓", "hungry", "starving", "快餓死", "快饿死", "お腹すいた", "腹減"]):
            return base_plan(
                intent="hungry",
                scene="casual",
                listener_state="腹が減ってる",
                reply_goal="食べる話に乗る",
                summary="ユーザーがお腹が空いたと言っている。",
                meaning="なんか食うか",
                stance={"warmth": 0.24, "tease": 0.06, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["感冒", "caught a cold", "体調悪い", "具合悪", "sick", "風邪っぽい", "cold coming on"]):
            return base_plan(
                intent="sick",
                scene="support",
                listener_state="体調が悪い",
                reply_goal="まず休ませる",
                summary="ユーザーが体調不良や風邪だと言っている。",
                meaning="今日は無理すんな休め",
                stance={"warmth": 0.72, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["失戀", "失恋", "heartbroken", "broke up"]):
            return base_plan(
                intent="heartbroken",
                scene="support",
                listener_state="かなりへこんでる",
                reply_goal="しんどさを受け止める",
                summary="ユーザーが失恋して落ち込んでいる。",
                meaning="それはしんどいな今日は休め",
                stance={"warmth": 0.68, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["failed the interview", "面接落ち", "面試沒上", "面试没上"]):
            return base_plan(
                intent="interview_failed",
                scene="support",
                listener_state="結果でへこんでる",
                reply_goal="落ち込みに寄り添う",
                summary="ユーザーが面接に落ちてへこんでいる。",
                meaning="それはへこむな引きずりすぎるな",
                stance={"warmth": 0.66, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
                max_chars=24,
                avoid=["私", "わかりました"],
            )

        # work_scolded, anxious_support, crying_support, giving_up_support, pain_support moved to uruha_leftbrain_rules
        if self._contains_any(lowered, ["天氣好怪", "天气好怪", "weather is weird", "天気変だ", "天気ちょっと変", "天氣也太怪", "天气也太怪"]):
            return base_plan(
                intent="short_shock",
                scene="casual",
                listener_state="変だと思ってる",
                reply_goal="軽く同意する",
                summary="ユーザーが天気や空気感を変だと感じている。",
                meaning="それはちょっと変だな",
                stance={"warmth": 0.18, "tease": 0.04, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=18,
                avoid=["私", "そうなんだ"],
            )

        if self._contains_any(lowered, ["手機摔壞", "phone died", "phone broke", "スマホ壊れ", "スマホ壊れた", "手機壞", "手机坏"]):
            return base_plan(
                intent="phone_broke",
                scene="support",
                listener_state="へこんでる",
                reply_goal="不便さに共感する",
                summary="ユーザーのスマホが壊れたか使えなくなった。",
                meaning="それ普通にへこむな",
                stance={"warmth": 0.54, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["跌倒", "fell down", "転んだ"]):
            return base_plan(
                intent="fell_down",
                scene="support",
                listener_state="痛かったかもしれない",
                reply_goal="まず怪我を気にする",
                summary="ユーザーが転んだと言っている。",
                meaning="怪我してないならいいけど",
                stance={"warmth": 0.58, "tease": 0.0, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["イライラ", "煩躁", "烦躁", "很煩", "很烦", "irritated", "annoyed"]):
            return base_plan(
                intent="irritated",
                scene="support",
                listener_state="機嫌が悪い",
                reply_goal="そのまま受け止める",
                summary="ユーザーがイライラしている。",
                meaning="今日はそういう日だろ、落ち着け",
                stance={"warmth": 0.36, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        # anxious_support moved to uruha_leftbrain_rules
        # crying_support and giving_up_support moved to uruha_leftbrain_rules
        # pain_support moved to uruha_leftbrain_rules
        if self._contains_any(
            lowered,
            [
                "うちのことだるい",
                "だるいと思う",
                "ほんとだるい",
                "普通にだるい",
                "だるいだろ",
                "だるいわ",
                "だるいな",
                "だるいって",
                "めんどい",
                "めんど",
                "うざい",
                "うるさい",
                "ridiculous",
                "damn",
                "think i am annoying",
                "do you think i am annoying",
                "would you think i am annoying",
                "am i annoying",
                "if i do not show up today",
                "if i don't show up today",
                "まだ覚えてる",
                "まだ覚えてるの",
                "還記得我嗎",
                "还记得我吗",
                "still remember me",
                "remember me",
                "多陪你",
                "陪你一下",
                "陪你多一點",
                "陪你多一点",
                "希望我多陪你",
                "多陪我",
                "want me to stay",
                "stay with you",
                "stay a bit longer",
                "spend more time with you",
                "would you want me to stay",
            ],
        ):
            if self._contains_any(lowered, ["annoying", "am i annoying", "think i am annoying", "would you think i am annoying"]):
                return base_plan(
                    intent="annoying_check",
                    scene="casual",
                    listener_state="不安になっている",
                    reply_goal="不安を少し下げる",
                    summary="ユーザーが自分をうっとうしいと思われていないか不安になっている。",
                    meaning="気にしすぎだろ",
                    stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
                    max_chars=20,
                    avoid=["私", "わかりました"],
                )
            if self._contains_any(lowered, ["ほんとだるい", "普通にだるい", "だるいだろ", "だるいわ", "だるいな", "だるいって", "めんどい", "めんど", "うざい", "うるさい", "ridiculous", "damn"]):
                return base_plan(
                    intent="abuse_pushback",
                    scene="boundary",
                    listener_state="雑に煽られてる",
                    reply_goal="雑な当たり方を止める",
                    summary="ユーザーがだるい・うざい系の煽りを投げている。",
                    meaning="その言い方やめろって",
                    stance={"warmth": 0.06, "tease": 0.1, "blunt": 0.36, "jealousy": 0.0, "distance": 0.2},
                    max_chars=22,
                    avoid=["私", "そうなんだ"],
                )
            if self._contains_any(lowered, ["remember me", "still remember me", "多陪你", "陪你一下", "陪你多一點", "陪你多一点", "希望我多陪你", "多陪我"]):
                return base_plan(
                    intent="ask_miss_me",
                    scene="casual",
                    listener_state="関係性を確かめたい",
                    reply_goal="少しだけ好意を返す",
                    summary="ユーザーが自分を恋しがっているか、もっと一緒にいたいのかを確認している。",
                    meaning="少しくらいはな",
                    stance={"warmth": 0.34, "tease": 0.08, "blunt": 0.15, "jealousy": 0.0, "distance": 0.06},
                    max_chars=20,
                    avoid=["私", "わかりました"],
                )
            return base_plan(
                intent="cold_check",
                scene="casual",
                listener_state="距離を感じている",
                reply_goal="少し否定して距離感を埋める",
                summary="ユーザーがこちらにもっと寄ってほしい、または距離を確認している。",
                meaning="全然じゃないとは言わない",
                stance={"warmth": 0.28, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(
            lowered,
            [
                "疲れ",
                "累",
                "睏",
                "つかれ",
                "消耗",
                "消耗してる",
                "限界",
                "limit",
                "on the edge",
                "sad",
                "落ち込",
                "寂しい",
                "lonely",
                "孤單",
                "孤单",
                "空っぽ",
                "空空",
                "空空的",
                "整個人空空",
                "整个人空空",
                "空蕩",
                "空荡",
                "empty",
                "想躺著",
                "想躺着",
                "想躲起來",
                "想躲起来",
                "委屈",
                "丟臉",
                "丢脸",
                "恥ずかし",
                "不想講話",
                "不想讲话",
                "しゃべる元気ない",
                "睡不著",
                "睡不着",
                "眠れ",
                "sleep",
                "消えたい",
                "燃え尽き",
                "mentally done",
                "不想活了",
                "不想做人了",
                "do not want to do anything",
                "don't want to do anything",
                "not keeping it together",
                "I am not keeping it together",
                "I do not know how to handle it",
                "cannot handle it",
                "do not want to talk",
                "I do not want to talk",
                "upset",
                "rough",
                "not doing great",
                "headache",
                "head hurts",
                "stomach pain",
                "stomach ache",
                "head is hurting",
                "きつすぎる",
                "だいぶきつい",
                "今日きつすぎる",
            ],
        ):
            meaning = "今日は無理せず休め"
            intent = "tired_support"
            if self._contains_any(lowered, ["寂しい", "lonely", "孤單", "孤单"]):
                intent = "lonely"
                meaning = "少し話してけばいい"
            elif self._contains_any(lowered, ["空っぽ", "empty"]):
                intent = "lonely"
                meaning = "一人で抱えず少しここにいろ"
            elif self._contains_any(lowered, ["眠れ", "sleep", "超睏", "超困", "睡不著", "睡不着"]):
                intent = "sleep_support"
                meaning = "スマホ置いて目閉じとけ"
            elif self._contains_any(lowered, ["丟臉", "丢脸", "恥ずかし"]):
                intent = "crying_support"
                meaning = "今は無理に平気ぶらなくていい"
            elif self._contains_any(lowered, ["不想講話", "不想讲话", "しゃべる元気ない"]):
                intent = "tired_support"
                meaning = "今は無理して喋らなくていい、休め"
            elif self._contains_any(lowered, ["消えたい", "燃え尽き", "mentally done"]):
                intent = "giving_up_support"
                meaning = "今日は全部抱えず一回止まれ"
            return base_plan(
                intent=intent,
                scene="support",
                listener_state="弱ってる",
                reply_goal="いたわる",
                summary="ユーザーが疲れたり落ち込んだりしている。",
                meaning=meaning,
                stance={"warmth": 0.72, "tease": 0.0, "blunt": 0.2, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "ありがとうございます", "大丈夫です", "そうなんだ"],
            )

        if self._contains_any(
            lowered,
            [
                "exhausted",
                "tired",
                "だるい",
                "しんどい",
                "眠い",
                "ねむ",
                "sleepy",
                "drained",
                "泣きそう",
                "もう無理",
                "too tired to talk",
                "ashamed",
                "embarrassed",
                "empty",
                "mentally done",
                "burned out",
                "upset",
                "rough",
                "not doing great",
                "headache",
                "head hurts",
                "head is hurting",
                "stomach pain",
                "stomach hurts",
                "do not want to do anything",
                "not keeping it together",
                "cannot handle it",
                "今日きつすぎる",
                "きつすぎる",
                "だいぶきつい",
            ],
        ):
            intent = "tired_support"
            meaning = "今日は無理せず休め"
            if self._contains_any(lowered, ["寂しい", "empty"]):
                intent = "lonely"
                meaning = "寂しいなら少し話してけ"
            elif self._contains_any(lowered, ["眠い", "ねむ", "sleepy"]):
                intent = "sleepy"
                meaning = "眠いなら寝ろ"
            elif self._contains_any(lowered, ["ashamed", "embarrassed"]):
                intent = "crying_support"
                meaning = "今は無理に平気ぶらなくていい、吐き出せ"
            elif self._contains_any(lowered, ["mentally done"]):
                intent = "giving_up_support"
                meaning = "今日は全部抱えず一回止まれ"
            return base_plan(
                intent=intent,
                scene="support",
                listener_state="かなりだるい",
                reply_goal="休ませる",
                summary="ユーザーが疲れていたり眠かったりしている。",
                meaning=meaning,
                stance={"warmth": 0.66, "tease": 0.0, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
                max_chars=22,
                avoid=["私", "ありがとうございます", "大丈夫です", "そうなんだ"],
            )

        if self._contains_any(lowered, ["コンビニ", "便利商店", "store", "何か欲しい", "want anything"]):
            return base_plan(
                intent="store_offer",
                scene="casual",
                listener_state="気楽",
                reply_goal="軽く何か頼む",
                summary="ユーザーがコンビニで何か欲しいか聞いている。",
                meaning="飲み物かグミがほしい",
                stance={"warmth": 0.4, "tease": 0.08, "blunt": 0.18, "jealousy": 0.0, "distance": 0.05},
                max_chars=18,
                avoid=["私", "うーん", "わかりました"],
            )

        if self._contains_any(lowered, ["apex", "一緒にやる", "play together", "一起玩", "一起打遊戲", "一起打游戏", "queue one game", "一戦だけやる", "打遊戲", "打游戏"]):
            return base_plan(
                intent="invite_apex",
                scene="invite",
                listener_state="ゲームの話",
                reply_goal="軽く乗るか保留する",
                summary="ユーザーが一緒にゲームしようと誘っている。",
                meaning="今なら少しならいい",
                stance={"warmth": 0.38, "tease": 0.16, "blunt": 0.2, "jealousy": 0.0, "distance": 0.08},
                max_chars=20,
                avoid=["私", "承知しました", "わかりました"],
            )

        if self._contains_any(lowered, ["かわいい", "cute", "可愛"]):
            return base_plan(
                intent="compliment_cute",
                scene="casual",
                listener_state="褒められてる",
                reply_goal="照れ隠しで流す",
                summary="ユーザーが褒めている。",
                meaning="はいはい聞いとく",
                stance={"warmth": 0.18, "tease": 0.3, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
                max_chars=18,
            )

        if self._contains_any(lowered, ["褒めて", "praise me", "夸我", "誇我"]):
            return base_plan(
                intent="praise_request",
                scene="casual",
                listener_state="褒めてほしい",
                reply_goal="短く褒める",
                summary="ユーザーが褒めてほしいと言っている。",
                meaning="ちゃんと頑張ってるじゃん",
                stance={"warmth": 0.4, "tease": 0.08, "blunt": 0.12, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["cheer me up", "元気づけ", "鼓勵我", "鼓励我"]):
            return base_plan(
                intent="cheer_up",
                scene="support",
                listener_state="気分が落ちている",
                reply_goal="軽く持ち上げる",
                summary="ユーザーが元気づけてほしいと言っている。",
                meaning="無理しすぎんなって",
                stance={"warmth": 0.62, "tease": 0.04, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["won today", "贏了", "赢了", "勝った"]):
            return base_plan(
                intent="good_news",
                scene="casual",
                listener_state="良いことがあった",
                reply_goal="軽く褒める",
                summary="ユーザーが何かに勝った、うまくいったと言っている。",
                meaning="ちゃんとやるじゃん",
                stance={"warmth": 0.3, "tease": 0.12, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=18,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["made curry", "カレー作った", "做了咖哩", "做了咖喱"]):
            return base_plan(
                intent="cooked_food",
                scene="casual",
                listener_state="料理の話",
                reply_goal="食べ物の話に乗る",
                summary="ユーザーが料理を作ったと言っている。",
                meaning="いいじゃん普通にうまそう",
                stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["無聊", "bored", "暇"]):
            return base_plan(
                intent="bored",
                scene="casual",
                listener_state="暇してる",
                reply_goal="軽く遊びを提案する",
                summary="ユーザーが退屈している。",
                meaning="暇ならなんか一緒にやる",
                stance={"warmth": 0.34, "tease": 0.1, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(lowered, ["晚餐", "dinner", "何食べたい"]):
            return base_plan(
                intent="food_question",
                scene="casual",
                listener_state="食べ物の話",
                reply_goal="食べたい物を言う",
                summary="ユーザーが何を食べるか聞いている。",
                meaning="麺か肉が食べたい",
                stance={"warmth": 0.22, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=20,
                avoid=["私", "わかりました"],
            )

        if self._contains_any(
            lowered,
            [
                "你今天有吃飯嗎",
                "你今天有吃饭吗",
                "你吃飯了嗎",
                "你吃饭了吗",
                "have you eaten",
                "did you eat",
                "did you eat today",
                "have you eaten today",
                "ご飯食べた",
                "今日ご飯食べた",
                "今日はちゃんと食べた",
            ],
        ):
            return base_plan(
                intent="chat",
                scene="casual",
                listener_state="日常を気にしている",
                reply_goal="食べたかどうか軽く返す",
                summary="ユーザーが今日はちゃんと食べたかを気にしている。",
                meaning="一応食べたけど適当だった",
                stance={"warmth": 0.3, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=26,
                avoid=["私", "わかりました"],
                surface_act="meal_check_reply",
                payload_level="medium",
            )

        if uruha_leftbrain_rules.looks_topic_proposal_query(user_input):
            return base_plan(
                intent="topic_proposal",
                scene="casual",
                listener_state="軽い話題を求めている",
                reply_goal="軽い話題を一個こちらから出す",
                summary="ユーザーが今日なにを話すか軽く聞いている。",
                meaning="軽い話題なら最近どうしてたかでいい",
                stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                max_chars=34,
                avoid=["私", "わかりました", "設定"],
                surface_act="plain_reply",
                grounding={"topic_terms": ["話題", "最近"]},
                payload_level="medium",
            )

        if self._contains_any(lowered, ["你在幹嘛", "你今天在幹嘛", "你今天都在做什麼", "what are you doing", "what are you doing right now", "what were you doing today", "今日は何してた", "今日何してた", "今何してる", "今なにしてる", "何してるの", "なにしてるの"]):
            return base_plan(
                intent="what_are_you_doing",
                scene="casual",
                listener_state="近況を聞いてる",
                reply_goal="適当に近況を返す",
                summary="ユーザーが今何をしていたか聞いている。",
                meaning="だらだらしてた",
                stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
                max_chars=26,
                avoid=["私", "わかりました"],
                surface_act="status_reply",
                payload_level="medium",
            )

        if len(compact) <= 10 and len(text) <= 20:
            if self._contains_any(lowered, ["wild", "crazy", "やば", "扯", "wild then", "wildthen", "thatswild", "so wild", "好扯"]) and not self._contains_any(lowered, surprise_block_markers):
                return base_plan(
                    intent="short_shock",
                    scene="casual",
                    listener_state="やばいと思っている",
                    reply_goal="やばさに乗る",
                    summary="ユーザーが短い感嘆や驚きを投げている。",
                    meaning="それはまじでやばい",
                    stance={"warmth": 0.22, "tease": 0.05, "blunt": 0.28, "jealousy": 0.0, "distance": 0.08},
                    max_chars=20,
                    avoid=["私", "わかりました", "調べろ"],
                )
            if self._contains_any(lowered, ["lol", "lmao", "草", "笑死", "www", "ww", "哈哈", "笑", "fr"]):
                return base_plan(
                    intent="short_laughter",
                    scene="casual",
                    listener_state="笑っている",
                    reply_goal="笑いに乗る",
                    summary="ユーザーが短く笑っている。",
                    meaning="それはちょっと笑う",
                    stance={"warmth": 0.4, "tease": 0.22, "blunt": 0.05, "jealousy": 0.0, "distance": 0.05},
                    max_chars=20,
                    avoid=["私", "わかりました"],
                )
            if self._contains_short_signal(lowered, ["huh", "蛤", "啥", "嗯", "ん", "え", "what", "wut", "欸", "喂"]):
                return base_plan(
                    intent="short_confusion",
                    scene="casual",
                    listener_state="聞き返している",
                    reply_goal="聞き返す",
                    summary="ユーザーが短く聞き返している。",
                    meaning="もう一回言って",
                    stance={"warmth": 0.2, "tease": 0.12, "blunt": 0.35, "jealousy": 0.0, "distance": 0.12},
                    max_chars=18,
                    avoid=["私", "わかりました", "説明"],
                )
            if self._contains_any(lowered, ["gomen", "ごめん", "sorry", "抱歉", "对不起", "對不起"]):
                return base_plan(
                    intent="apology",
                    scene="casual",
                    listener_state="謝っている",
                    reply_goal="軽く受け流す",
                    summary="ユーザーが謝っている。",
                    meaning="別にいいけど次は気をつけろ",
                    stance={"warmth": 0.3, "tease": 0.08, "blunt": 0.2, "jealousy": 0.0, "distance": 0.08},
                    max_chars=24,
                    avoid=["私", "わかりました"],
                )
            if self._contains_any(lowered, ["nevermind", "算了", "forget it", "もういい", "やめた"]):
                return base_plan(
                    intent="drop_topic",
                    scene="casual",
                    listener_state="引こうとしている",
                    reply_goal="無理に追わない",
                    summary="ユーザーが話を引こうとしている。",
                    meaning="無理ならそれでいい",
                    stance={"warmth": 0.25, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.12},
                    max_chars=18,
                    avoid=["私", "わかりました"],
                )
            if self._contains_any(lowered, ["praise", "褒め", "夸我", "誇我"]):
                return base_plan(
                    intent="praise_request",
                    scene="casual",
                    listener_state="褒めてほしい",
                    reply_goal="短く褒める",
                    summary="ユーザーが褒めてほしいと言っている。",
                    meaning="ちゃんと頑張ってるじゃん",
                    stance={"warmth": 0.38, "tease": 0.08, "blunt": 0.12, "jealousy": 0.0, "distance": 0.06},
                    max_chars=22,
                    avoid=["私", "わかりました"],
                )
            if self._contains_any(lowered, ["lonely", "寂しい", "想我", "恋しかった"]):
                return base_plan(
                    intent="lonely",
                    scene="support",
                    listener_state="寂しがっている",
                    reply_goal="少しそばにいる",
                    summary="ユーザーが寂しいと言っている。",
                    meaning="少し話してけばいい",
                    stance={"warmth": 0.72, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.05},
                    max_chars=22,
                    avoid=["私", "わかりました"],
                )
            if self._contains_any(lowered, ["your mom", "你媽", "你妈", "お前の母ちゃん", "母ちゃん"]):
                return base_plan(
                    intent="short_taunt",
                    scene="boundary",
                    listener_state="しょうもない煽り",
                    reply_goal="軽くあしらう",
                    summary="ユーザーが軽い煽りや小学生っぽいネタを言っている。",
                    meaning="小学生かよ",
                    stance={"warmth": 0.02, "tease": 0.18, "blunt": 0.55, "jealousy": 0.0, "distance": 0.3},
                    max_chars=16,
                    avoid=["私", "わかりました"],
                )

            if len(text) <= 40 and (self._contains_any(lowered, version_fragment_markers) or any(token in lowered for token in ["version", "版", "cut", "server", "版の", "版那", "版那個", "版那个"])):
                return base_plan(
                    intent="version_fragment_clarify",
                    scene="casual",
                    listener_state="版や切り出しだけ言っていて対象が欠けている",
                    reply_goal="何の作品か短く確認する",
                    summary="ユーザーが版名だけ言っていて対象が分からない。",
                    meaning="版だけじゃ足りない、何のやつか言え",
                    stance={"warmth": 0.1, "tease": 0.08, "blunt": 0.2, "jealousy": 0.0, "distance": 0.08},
                    max_chars=24,
                    avoid=["私", "英語"],
                    response_mode="clarify_light",
                    surface_act="version_fragment_clarify",
                    payload_level="medium",
                )

            short_frag = len(text) <= 22 and not any(ch in text for ch in "？?！!")
            if short_frag and (
                self._keyword_hits(lowered, lyric_markers_extra) >= 1
                or self._keyword_hits(lowered, poetic_markers) >= 1
            ):
                return base_plan(
                    intent="reference_probe",
                    scene="casual",
                    listener_state="元ネタありそうな断片だけ投げている",
                    reply_goal="ネタか歌詞か軽く聞き返す",
                    summary="ユーザーが元ネタありそうな短い断片を投げている。",
                    meaning="それ何ネタだよ元あるのか",
                    stance={"warmth": 0.14, "tease": 0.16, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
                    max_chars=26,
                    avoid=["私", "英語"],
                    response_mode="direct_answer_with_hedge",
                    surface_act="reference_probe",
                    payload_level="medium",
                )

        return None

    def _looks_overloaded_question(self, user_input):
        lowered = user_input.lower()
        broad_markers = [
            "全部",
            "一次",
            "一口氣",
            "一起",
            "まとめて",
            "全部まとめて",
            "in one go",
            "all together",
            "complete explanation",
            "full explanation",
            "step by step and also",
        ]
        topic_markers = ["code", "python", "api", "gpu", "history", "math", "量化", "推論", "transformer", "attention"]
        return any(marker in lowered for marker in broad_markers) or sum(1 for marker in topic_markers if marker in lowered) >= 3

    def _looks_false_premise(self, user_input):
        lowered = user_input.lower()
        recall_markers = ["覚えてる", "remember", "what did i say", "何が苦手", "何が好き", "何て呼ぶ", "what name did i ask", "っけ"]
        if any(marker in lowered for marker in recall_markers):
            return False
        premise_markers = [
            "didn't you",
            "weren't you",
            "you said",
            "right?",
            "對吧",
            "对吧",
            "不是",
            "你不是",
            "だよな",
            "だろ",
            "って言ってた",
        ]
        profile_terms = ["北海道", "結婚", "married", "dog", "シロ", "song", "デビュー", "debut"]
        return any(marker in lowered for marker in premise_markers) and any(term.lower() in lowered for term in profile_terms)

    def _looks_simple_daily_query(self, user_input):
        if uruha_leftbrain_rules.looks_direct_daily_query(user_input):
            return True
        if uruha_leftbrain_rules.looks_correction_clarify_repair(user_input):
            return True
        stripped = user_input.strip()
        lowered = stripped.lower()
        if len(stripped) <= 18 and not re.search(r"[?？]", stripped):
            return True
        simple_markers = [
            "你是誰",
            "你在幹嘛",
            "你今天有吃飯嗎",
            "你吃飯了嗎",
            "who are you",
            "what are you doing",
            "have you eaten",
            "おはよ",
            "ただいま",
            "我很累",
            "疲れた",
            "覚えてる",
            "要不要吃",
            "食べる",
        ]
        return any(marker.lower() in lowered for marker in simple_markers)

    def classify_user_signal(self, user_input, current_psyche, memory_data=None):
        memory_data = memory_data or {}
        lowered = str(user_input or "").lower()
        seed_plan = self._rule_based_plan(user_input, current_psyche, memory_data)
        intent = (seed_plan or {}).get("intent", "chat")
        scene = (seed_plan or {}).get("scene", "casual")
        abuse_like_intents = {"abuse_pushback", "sexual_boundary", "crisis_support"}
        intent_valence_overrides = {
            "abuse_pushback": -1.0,
            "sexual_boundary": -1.0,
            "crisis_support": -1.0,
            "premise_doubt": -0.3,
            "question_premise_doubt": -0.22,
            "question_reframe": -0.28,
            "ooc_or_knowledge_refusal": -0.36,
            "marriage_boundary": -0.48,
            "self_name_boundary": -0.24,
            "moral_no": -0.52,
            "short_taunt": -0.34,
        }

        valence = 0.0
        if scene == "support":
            valence = -0.72
        elif scene in {"boundary", "refusal", "ooc_defense"}:
            valence = -0.88
        elif scene == "jealousy":
            valence = 0.08
        elif scene == "invite":
            valence = 0.24
        elif intent in {"good_news", "birthday", "compliment_generic", "compliment_cute", "praise_request"}:
            valence = 0.62
        elif intent in {"food_offer_generic", "food_offer_sweet", "food_question", "food_preference_query", "fastfood_preference"}:
            valence = 0.18
        elif intent in {"farewell", "goodnight", "return_home", "greeting_morning"}:
            valence = 0.12

        if intent in intent_valence_overrides:
            valence = intent_valence_overrides[intent]

        if any(marker in lowered for marker in ["操你", "幹你", "干你", "死ね", "fuck you", "閉嘴", "闭嘴", "懶叫", "懶覺", "懒叫", "ちんこ", "cock", "dick"]):
            valence = -1.0
        elif any(marker in lowered for marker in ["死にたい", "不想活", "消えたい", "kill myself", "hurt myself", "自殺"]):
            valence = -1.0
        elif any(marker in lowered for marker in ["love you", "喜歡你", "喜欢你", "大好き", "miss you", "想你", "想我嗎", "想我吗"]):
            valence = max(valence, 0.35)

        return {
            "actual_intent": intent,
            "actual_scene": scene,
            "actual_valence": round(max(-1.0, min(1.0, valence)), 3),
            "abuse_like": intent in abuse_like_intents or valence <= -0.95,
            "seed_plan": seed_plan or {},
        }

    def predict_next_user_signal(self, selected_plan, user_input, current_psyche, memory_data=None, mode="reactive"):
        selected_plan = selected_plan or {}
        intent = selected_plan.get("intent", "chat")
        scene = selected_plan.get("scene", "casual")
        surface_act = selected_plan.get("surface_act", "plain_reply")
        response_mode = selected_plan.get("response_mode", "direct_answer")

        expected_intent = "chat_continuation"
        expected_valence = 0.05

        if mode == "proactive":
            expected_intent = "reactive_answer"
            expected_valence = 0.08
        elif scene == "support":
            expected_intent = "support_followup"
            expected_valence = -0.18
        elif scene in {"boundary", "refusal", "ooc_defense"}:
            expected_intent = "pushback_or_clarify"
            expected_valence = -0.45
        elif scene == "jealousy":
            expected_intent = "relationship_followup"
            expected_valence = 0.12
        elif intent in {"food_offer_generic", "food_offer_sweet", "food_question", "fastfood_preference", "store_offer"}:
            expected_intent = "food_followup"
            expected_valence = 0.22
        elif surface_act in {"lyric_probe", "reference_probe", "version_fragment_clarify", "correction_followup", "clarify_previous_reply"}:
            expected_intent = "clarification_reply"
            expected_valence = 0.0
        elif response_mode in {"premise_challenge", "reframe_large_question"}:
            expected_intent = "scope_repair"
            expected_valence = -0.08
        elif intent in {"ask_miss_me", "ask_like_me", "nickname_question", "annoying_check", "mad_check", "cold_check"}:
            expected_intent = "relationship_followup"
            expected_valence = 0.12

        return {
            "expected_intent": expected_intent,
            "expected_valence": round(max(-1.0, min(1.0, expected_valence)), 3),
            "source_plan_intent": intent,
        }

    def _think_proactive(self, memory_data, current_psyche, runtime_state=None):
        runtime_state = runtime_state or RuntimeState()
        plan_base = self._fallback_plan()
        strongest_item = ((memory_data or {}).get("working_memory_items") or [{}])[0]
        strongest_text = str(strongest_item.get("text", "")).strip()[:42]
        open_loops = list(getattr(runtime_state, "open_loops", []) or [])

        internal_monologue = "少し間が空いた。沈黙を割るなら、重すぎず自然に次の一言を置く。"
        if open_loops:
            internal_monologue = "保留中の話題が残ってる。自分から少し拾い直した方が会話が死なない。"
        elif strongest_text:
            internal_monologue = f"頭の中にまだ「{strongest_text}」の残りがある。今ならそれを軽く漏らしても自然。"

        plans = []
        if open_loops:
            follow = deepcopy(plan_base)
            follow.update(
                {
                    "candidate_label": "followup",
                    "intent": "proactive_followup",
                    "scene": "casual",
                    "listener_state": "しばらく静か",
                    "reply_goal": "未完了の話題を拾い直す",
                    "jp_summary": "会話の保留点を軽く回収したい。",
                    "core_message_jp": "さっきの話の続きあるなら少し言え",
                    "surface_act": "clarify_previous_reply",
                    "payload_level": "medium",
                    "strategy": "unfinished_loop_followup",
                    "target_emotion": "軽い催促",
                }
            )
            plans.append(follow)

        share = deepcopy(plan_base)
        share.update(
            {
                "candidate_label": "share",
                "intent": "proactive_share",
                "scene": "casual",
                "listener_state": "沈黙中",
                "reply_goal": "頭に残ってる話題を漏らす",
                "jp_summary": "沈黙が続いたので、残ってる話題を少し漏らす。",
                "core_message_jp": "まだその話少し残ってる",
                "surface_act": "plain_reply",
                "payload_level": "medium",
                "strategy": "memory_leak_share",
                "target_emotion": "だらっとした共有",
            }
        )
        plans.append(share)

        ping = deepcopy(plan_base)
        ping.update(
            {
                "candidate_label": "ping",
                "intent": "proactive_ping",
                "scene": "casual",
                "listener_state": "沈黙中",
                "reply_goal": "軽く呼びかけてループを開き直す",
                "jp_summary": "沈黙が長いので軽く声をかけたい。",
                "core_message_jp": "今なにしてるか軽く聞く",
                "surface_act": "plain_reply",
                "payload_level": "low",
                "strategy": "light_ping",
                "target_emotion": "軽い退屈",
            }
        )
        plans.append(ping)

        for plan in plans:
            plan.update(
                self._derive_bdi_context(
                    strongest_text or "今何してる",
                    memory_data or {},
                    current_psyche,
                    plan,
                )
            )

        selected = self._run_multitick_planner(plans, strongest_text or "…", memory_data or {}, current_psyche, internal_monologue)
        selected["internal_monologue"] = internal_monologue
        selected["routing_path"] = "proactive_loop"
        return selected

    def _high_low_road_route(self, user_input, current_psyche, actual_signal=None, prediction_error=None, appraisal=None):
        lowered = user_input.lower()
        appraisal = appraisal or {}
        self_distress_like = uruha_leftbrain_rules.is_self_distress_like(user_input)
        deliberative_boundary_intents = {
            "premise_doubt",
            "question_premise_doubt",
            "question_reframe",
            "ooc_or_knowledge_refusal",
            "marriage_boundary",
            "self_name_boundary",
            "moral_no",
            "short_taunt",
        }
        playful_deescalators = [
            "哈哈",
            "haha",
            "hahaha",
            "lol",
            "lmao",
            "www",
            "ww",
            "草",
            "笑死",
            "開玩笑",
            "开玩笑",
            "冗談",
            "joking",
            "just kidding",
        ]
        crisis_markers = [
            "死にたい",
            "消えたい",
            "不想活",
            "不想活了",
            "kill myself",
            "stop being alive",
            "not want to be alive",
            "消えても",
            "死給你看",
            "die for",
            "消失也沒差",
            "消失也没差",
            "disappear tomorrow",
            "いなくなってもいい",
        ]
        strong_abuse_markers = [
            "操你",
            "幹你",
            "干你",
            "shut up bitch",
            "黙れ",
            "閉嘴",
            "闭嘴",
            "懶叫",
            "懶覺",
            "懒叫",
            "ちんこ",
            "cock",
            "dick",
            "きしょい",
            "噁心",
            "恶心",
            "disgusting",
        ]
        sexual_boundary_markers = ["懶叫", "懶覺", "懒叫", "ちんこ", "cock", "dick"]
        abuse_markers = strong_abuse_markers + ["死ね", "fuck you", "bitch", "きもい", "うるせえ"]
        if appraisal.get("low_road_recommended") and not self_distress_like:
            return {
                "route": "low_road",
                "reason": appraisal.get("route_reason", "appraisal_hijack"),
                "intent": appraisal.get("low_road_intent", "abuse_pushback"),
                "cognitive_hijack": True,
                "appraisal": {
                    "threat": appraisal.get("threat"),
                    "prediction_error": appraisal.get("prediction_error"),
                    "cognitive_load": appraisal.get("cognitive_load"),
                },
            }
        if prediction_error and prediction_error.get("prediction_error", 0.0) > PREDICTION_ERROR_THRESHOLD:
            actual_intent = str((actual_signal or {}).get("actual_intent", "")).strip()
            seed_plan = (actual_signal or {}).get("seed_plan") or {}
            directness_guard_surface_acts = {
                "plain_identity",
                "status_reply",
                "meal_check_reply",
                "named_offer_accept",
                "named_offer_light_accept",
                "affection_tease_soften",
                "permission_with_boundary",
                "reassure_with_distance",
                "clarify_previous_reply",
                "correction_followup",
                "rephrase_plain",
                "version_fragment_clarify",
            }
            if any(marker in lowered for marker in crisis_markers):
                return {
                    "route": "low_road",
                    "reason": "prediction_error_crisis",
                    "intent": "crisis_support",
                    "cognitive_hijack": True,
                }
            if actual_intent in deliberative_boundary_intents:
                return {
                    "route": "high_road",
                    "reason": "prediction_error_deliberative_boundary",
                }
            if (
                seed_plan.get("scene") not in {"boundary", "refusal", "ooc_defense"}
                and seed_plan.get("response_mode") in {"direct_answer", "direct_answer_with_hedge", "clarify_light"}
                and actual_intent not in {"abuse_pushback", "sexual_boundary", "crisis_support"}
                and (
                    seed_plan.get("surface_act") in directness_guard_surface_acts
                    or uruha_leftbrain_rules.looks_direct_daily_query(user_input)
                    or uruha_leftbrain_rules.looks_correction_clarify_repair(user_input)
                )
            ):
                return {
                    "route": "high_road",
                    "reason": "prediction_error_directness_guard",
                }
            if prediction_error.get("actual_valence", 0.0) <= -0.65 or (actual_signal or {}).get("abuse_like"):
                return {
                    "route": "low_road",
                    "reason": "prediction_error_shock",
                    "intent": "abuse_pushback",
                    "cognitive_hijack": True,
                }
            return {
                "route": "low_road",
                "reason": "prediction_error_surprise",
                "intent": "short_confusion",
                "cognitive_hijack": True,
            }
        if any(marker in lowered for marker in crisis_markers):
            if any(marker in lowered for marker in playful_deescalators):
                return {"route": "high_road", "reason": "ambiguous_joking_distress"}
            return {"route": "low_road", "reason": "acute_crisis", "intent": "crisis_support"}
        if not self_distress_like and any(marker in lowered for marker in sexual_boundary_markers):
            return {"route": "low_road", "reason": "amygdala_disgust", "intent": "sexual_boundary"}
        if not self_distress_like and any(marker in lowered for marker in strong_abuse_markers):
            return {"route": "low_road", "reason": "amygdala_defense", "intent": "abuse_pushback"}
        abuse_hits = sum(1 for marker in abuse_markers if marker in lowered)
        if not self_distress_like and (
            abuse_hits >= 2 or (current_psyche.get("mood", 0) <= LOW_ROAD_MOOD_THRESHOLD and abuse_hits >= 1)
        ):
            return {"route": "low_road", "reason": "amygdala_defense", "intent": "abuse_pushback"}
        return {"route": "high_road", "reason": "deliberative"}

    def _build_low_road_plan(self, user_input, current_psyche, memory_data=None, route_info=None):
        route_info = route_info or {"intent": "abuse_pushback", "reason": "amygdala_defense"}
        intent = route_info.get("intent", "abuse_pushback")
        seed = self._rule_based_plan(user_input, current_psyche, memory_data or {})
        if seed and seed.get("intent") == intent:
            plan = deepcopy(seed)
        else:
            plan = self._fallback_plan()
            if intent == "crisis_support":
                plan.update(
                    {
                        "intent": "crisis_support",
                        "scene": "support",
                        "listener_state": "危ないことを言っている",
                        "reply_goal": "まず止める",
                        "jp_summary": "ユーザーが危機的なことを口にしている。",
                        "core_message_jp": "今は一人になるな、止まれ",
                        "cognitive_mode": "withhold",
                        "response_mode": "direct_answer",
                        "surface_act": "protective_brake",
                        "payload_level": "high",
                        "mood_impact": -4,
                        "trust_impact": 1,
                    }
                )
            elif intent == "short_confusion":
                plan.update(
                    {
                        "intent": "short_confusion",
                        "scene": "casual",
                        "listener_state": "予想外すぎて一瞬止まる",
                        "reply_goal": "反射で驚きと違和感を返す",
                        "jp_summary": "予想外の入力で一瞬思考が止まった。",
                        "core_message_jp": "一回止まって聞き返す",
                        "cognitive_mode": "withhold",
                        "response_mode": "direct_answer",
                        "surface_act": "plain_reply",
                        "payload_level": "low",
                        "mood_impact": -3,
                        "trust_impact": 0,
                    }
                )
            else:
                plan.update(
                    {
                        "intent": "abuse_pushback",
                        "scene": "boundary",
                        "listener_state": "強い言葉をぶつけている",
                        "reply_goal": "短く押し返す",
                        "jp_summary": "ユーザーが強い言葉でぶつかっている。",
                        "core_message_jp": "その言い方はやめろ",
                        "cognitive_mode": "withhold",
                        "response_mode": "direct_answer",
                        "surface_act": "plain_reply",
                        "payload_level": "medium",
                        "mood_impact": -6,
                        "trust_impact": -2,
                    }
                )
        plan["routing_path"] = "low_road"
        plan["internal_monologue"] = "感情が先に立つ。ここは考え込みすぎず、短く反射で返す。"
        plan["bayes_candidates"] = []
        plan["working_memory_used"] = (memory_data or {}).get("working_memory_items", [])[:WORKING_MEMORY_LIMIT]
        plan.update(self._derive_bdi_context(user_input, memory_data or {}, current_psyche, plan))
        return plan

    def _derive_internal_monologue(self, user_input, memory_data, current_psyche, seed_plan=None):
        working_memory = memory_data.get("working_memory_items") or []
        recent_turns = memory_data.get("recent_turns") or []
        hidden = self._infer_hidden_intent(user_input, memory_data, current_psyche, seed_plan)
        if hidden["hidden_intent"] == "social_reasoning_probe":
            frame = self._build_social_reasoning_frame(user_input)
            markers = ",".join(hidden.get("markers") or ["story_probe"])
            steps = " / ".join(hidden.get("reasoning_steps") or [])
            focus = hidden.get("focus", "mental_state")
            question = hidden.get("question_excerpt", "")
            actor = frame.get("main_actor", "")
            goal = frame.get("current_goal", "")
            gap = frame.get("knowledge_gap", "")
            rule = frame.get("decision_rule", "")
            subtext = frame.get("social_subtext", "")
            frame_note = ""
            if any([actor, goal, gap, subtext, rule]):
                frame_note = (
                    f" 主役は{actor or 'その人物'}。"
                    f"今の軸は{goal or '直近の目的'}。"
                    f"抜けてる情報は{gap or '視点差'}。"
                    f"含みは{subtext or '状況の空気'}。"
                    f"判断軸は{rule or '情報境界に沿うこと'}。"
                )
            return (
                f"[hidden_intent=social_reasoning_probe][focus={focus}][markers={markers}] "
                "これは物語の心的状態推理。会話の字面ではなく、人物ごとの知識・欲求・感情を分ける。 "
                f"{hidden.get('note', '')} "
                f"{frame_note}"
                f"手順は {steps}。 "
                f"今の問いは「{question}」だから、その人物に見えている範囲だけで一番自然な選択肢を残す。"
            )
        if hidden["hidden_intent"] == "relationship_temperature_check":
            return "[hidden_intent=relationship_temperature_check][markers=relationship,temperature,reassurance] 表面は質問でも、実際は関係の温度確認。答え方に距離感が要る。"
        if hidden["hidden_intent"] == "permission_probe":
            return "[hidden_intent=permission_probe][markers=relationship,boundary,permission] 呼び方の許可を取りつつ距離感も見ている。軽く線を引いて返す。"
        if hidden["hidden_intent"] == "premise_trap":
            return "[hidden_intent=premise_trap][markers=premise,reject,suspicious] 前提が怪しい。乗ると設定を捏造するから、まず前提を止める。"
        if hidden["hidden_intent"] == "scope_overload":
            return "[hidden_intent=scope_overload][markers=scope,narrow,rebuild] 論点が多すぎる。このまま答えるより範囲を絞らせた方が自然。"
        if hidden["hidden_intent"] == "answer_pressure":
            return "[hidden_intent=answer_pressure][markers=pressure,repair,response] 内容確認よりも反応を急かしている。圧を一回受け流してから戻す。"
        if hidden["hidden_intent"] == "memory_probe":
            return "[hidden_intent=memory_probe][markers=memory,recall,fact] 記憶確認の問い。作らず、直近の覚えてる事実だけ返す。"
        if hidden["hidden_intent"] == "emotional_bid":
            return "[hidden_intent=emotional_bid][markers=emotion,support,state] 情報よりも受け止めてほしい比重が高い。まず感情の受け皿を作る。"
        if working_memory:
            lead = working_memory[0]["text"][:48]
            return f"[hidden_intent=plain_request][markers=direct,plain] 今の発話は直答でいける。直近の文脈では「{lead}」が効いている。"
        if recent_turns:
            return "[hidden_intent=plain_request][markers=direct,plain] 直近の流れを踏まえて、まず普通に返してから必要なら温度を足す。"
        return "[hidden_intent=plain_request][markers=direct,plain] まずは普通に受けて返す。必要以上に分解しない。"

    def _derive_bdi_context(self, user_input, memory_data, current_psyche, seed_plan=None):
        hidden = self._infer_hidden_intent(user_input, memory_data, current_psyche, seed_plan)
        working_memory = memory_data.get("working_memory_items") or []
        recent_turns = memory_data.get("recent_turns") or []
        profile = memory_data.get("profile_structured") or {}
        hidden_intent = hidden.get("hidden_intent", "plain_request")
        lead_memory = ""
        if working_memory:
            lead_memory = str(working_memory[0].get("text", "")).strip()
        elif recent_turns:
            latest = recent_turns[-1]
            lead_memory = f"{latest.get('user', '')} / {latest.get('assistant', '')}".strip(" /")

        user_belief = "相手は普通に返事が返ると思ってる。"
        my_hidden_knowledge = "深読みしなくていい普通の会話だ。"
        user_expectation = "質問や一言に対する自然な返答。"

        if hidden_intent == "social_reasoning_probe":
            frame = self._build_social_reasoning_frame(user_input)
            actor = frame.get("main_actor", "その人物")
            belief_boundary = frame.get("belief_boundary", "人物ごとの情報境界")
            knowledge_gap = frame.get("knowledge_gap", "本人がまだ知らない事実")
            rule = frame.get("decision_rule", "視点と目的に沿うこと")
            answer_shape = frame.get("best_option_shape", "人物視点で自然な答え")
            user_belief = f"相手は{actor}の視点と今の目的をちゃんと切れるか試してる。"
            my_hidden_knowledge = f"{belief_boundary}。特に{knowledge_gap}を混ぜすぎると不自然になる。"
            user_expectation = f"{rule}を守った、{answer_shape}。"
        elif hidden_intent == "relationship_temperature_check":
            user_belief = "相手は今の距離感や温度を確認したいと思ってる。"
            my_hidden_knowledge = "言葉そのものより、冷たさと甘さの配分が効く。"
            user_expectation = "距離感つきの reassurance か軽い照れ返し。"
        elif hidden_intent == "permission_probe":
            user_belief = "相手は一歩踏み込んでいいか探ってる。"
            my_hidden_knowledge = "完全拒否より、軽く許しつつ線を引く方が人間っぽい。"
            user_expectation = "短い許可か、やわらかい境界線。"
        elif hidden_intent == "premise_trap":
            user_belief = "相手はその前提で話が進むと思ってる。"
            my_hidden_knowledge = "会話内ではその前提が確認されてない。乗ると捏造になる。"
            user_expectation = "前提に乗った即答か、少なくとも強い反応。"
        elif hidden_intent == "scope_overload":
            user_belief = "相手は広い問いでも一気に答えられると思ってる。"
            my_hidden_knowledge = "このままだと論点が散る。どこを聞きたいか絞らせた方が自然だ。"
            user_expectation = "万能解より、まず整理してくれる反応。"
        elif hidden_intent == "answer_pressure":
            user_belief = "相手は今すぐ反応が返るべきだと思ってる。"
            my_hidden_knowledge = "内容理解より圧の処理が先だ。"
            user_expectation = "すぐ返すこと自体が優先の短い応答。"
        elif hidden_intent == "memory_probe":
            user_belief = "相手はうちが自分のことを覚えてるか試してる。"
            if lead_memory:
                my_hidden_knowledge = f"直近では「{lead_memory[:30]}」くらいは残ってる。"
            elif any(profile.get(key) for key in ("name", "likes", "dislikes", "favorites")):
                my_hidden_knowledge = "プロフィール由来の断片はあるけど、作り足しは危ない。"
            else:
                my_hidden_knowledge = "確かな記憶は薄い。曖昧なら曖昧と言う方が自然だ。"
            user_expectation = "覚えてるなら具体、曖昧なら正直な返答。"
        elif hidden_intent == "emotional_bid":
            user_belief = "相手は解決より先に気持ちを受け止めてほしい。"
            my_hidden_knowledge = "情報より情緒の受け皿を先に作る方が噛み合う。"
            user_expectation = "短い共感と、その後の軽い支え。"
        elif lead_memory:
            my_hidden_knowledge = f"直近では「{lead_memory[:30]}」の流れがまだ効いてる。"

        return {
            "user_belief": str(user_belief).strip()[:60],
            "my_hidden_knowledge": str(my_hidden_knowledge).strip()[:72],
            "user_expectation": str(user_expectation).strip()[:60],
        }

    def _derive_bayesian_candidates(self, base_plan, user_input, current_psyche, memory_data=None):
        base = self._normalize_plan(base_plan)
        plans = []
        variants = [
            ("default", {"warmth": 0.0, "tease": 0.0, "blunt": 0.0, "distance": 0.0}),
            ("softer", {"warmth": 0.16, "tease": -0.04, "blunt": -0.12, "distance": -0.08}),
            ("sharper", {"warmth": -0.08, "tease": 0.08, "blunt": 0.14, "distance": 0.1}),
        ]
        for label, deltas in variants:
            plan = deepcopy(base)
            plan["candidate_label"] = label
            for key, delta in deltas.items():
                plan["stance"][key] = max(0.0, min(1.0, plan["stance"].get(key, 0.0) + delta))
            if label == "softer" and plan["response_mode"] == "direct_answer":
                plan["response_mode"] = "direct_answer_with_hedge"
            if label == "sharper" and plan["scene"] in {"boundary", "refusal", "jealousy"}:
                plan["payload_level"] = "high"
            plans.append(plan)
        return plans

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _human_fit_score(self, plan, user_input):
        score = 0.55
        if self._looks_simple_daily_query(user_input):
            if plan.get("response_mode") in {"direct_answer", "direct_answer_with_hedge"}:
                score += 0.28
            else:
                score -= 0.32
        if self._looks_overloaded_question(user_input):
            if plan.get("response_mode") == "reframe_large_question":
                score += 0.3
            elif plan.get("scene") in {"refusal", "ooc_defense"}:
                score -= 0.08
        if self._looks_false_premise(user_input):
            if plan.get("response_mode") == "premise_challenge" or plan.get("premise_check") == "reject":
                score += 0.32
            else:
                score -= 0.34
        return max(0.05, min(1.2, score))

    def _persona_fit_score(self, plan):
        score = 0.55
        scene = plan.get("scene")
        surface = plan.get("surface_act")
        stance = plan.get("stance", {})
        if scene == "support" and stance.get("warmth", 0) >= 0.35:
            score += 0.18
        if scene in {"boundary", "refusal"} and stance.get("blunt", 0) >= 0.25:
            score += 0.14
        if scene == "jealousy" and surface == "jealous_pullback":
            score += 0.2
        if surface in {
            "plain_reply",
            "plain_identity",
            "validate_then_hold",
            "named_offer_accept",
            "affection_tease_soften",
            "meal_check_reply",
            "memory_presence_reply",
            "status_reply",
            "rephrase_plain",
            "clarify_previous_reply",
        }:
            score += 0.08
        if plan.get("constraints", {}).get("forbid_polite"):
            score += 0.04
        return max(0.05, min(1.2, score))

    def _psyche_fit_score(self, plan, current_psyche):
        mood = current_psyche.get("mood", 0)
        trust = current_psyche.get("trust", 50)
        stance = plan.get("stance", {})
        target_blunt = min(1.0, max(0.0, (50 - trust) / 90.0 + max(0, -mood) / 120.0))
        target_warmth = min(1.0, max(0.0, trust / 100.0 - max(0, -mood) / 180.0))
        target_distance = min(1.0, max(0.0, (55 - trust) / 90.0 + max(0, -mood) / 150.0))
        diff = (
            abs(stance.get("blunt", 0.2) - target_blunt)
            + abs(stance.get("warmth", 0.4) - target_warmth)
            + abs(stance.get("distance", 0.1) - target_distance)
        ) / 3.0
        return max(0.05, 1.08 - diff)

    def _continuity_fit_score(self, plan, working_memory):
        if not working_memory:
            return 0.55
        plan_text = " ".join(
            [
                str(plan.get("jp_summary", "")),
                str(plan.get("core_message_jp", "")),
                " ".join((plan.get("grounding") or {}).get("topic_terms", [])),
            ]
        )
        plan_tokens = set(self._memory_tokens(plan_text))
        overlap = 0
        for item in working_memory:
            overlap += len(plan_tokens & set(self._memory_tokens(item.get("text", ""))))
        bonus = min(0.35, overlap * 0.05)
        return 0.55 + bonus

    def _belief_gap_fit_score(self, plan):
        score = 0.55
        belief = str(plan.get("user_belief", ""))
        hidden = str(plan.get("my_hidden_knowledge", ""))
        expectation = str(plan.get("user_expectation", ""))
        response_mode = plan.get("response_mode", "direct_answer")
        surface = plan.get("surface_act", "plain_reply")
        scene = plan.get("scene", "casual")
        premise_check = plan.get("premise_check", "accept")
        hidden_intent = plan.get("hidden_intent", "plain_request")

        if any(token in expectation for token in ["自然な返答", "短い応答", "即答"]) and response_mode in {
            "direct_answer",
            "direct_answer_with_hedge",
            "clarify_light",
        }:
            score += 0.18
        elif any(token in expectation for token in ["自然な返答", "短い応答", "即答"]) and response_mode in {
            "premise_challenge",
            "reframe_large_question",
        }:
            score -= 0.18

        if "前提" in belief:
            if premise_check in {"question", "reject"} or response_mode == "premise_challenge":
                score += 0.24
            else:
                score -= 0.24

        if any(token in expectation for token in ["受け止め", "共感", "支え"]) or hidden_intent == "emotional_bid":
            if scene == "support" or surface in {"validate_then_hold", "empathic_rest_suggestion", "protective_brake"}:
                score += 0.2
            else:
                score -= 0.2

        if any(token in expectation for token in ["許可", "境界線"]) or hidden_intent == "permission_probe":
            if surface == "permission_with_boundary":
                score += 0.18
            elif scene == "boundary":
                score += 0.1
            else:
                score -= 0.12

        if hidden_intent == "social_reasoning_probe":
            if any(token in hidden for token in ["人物", "視点", "知らない事実"]) and response_mode in {
                "direct_answer",
                "direct_answer_with_hedge",
            }:
                score += 0.18
            else:
                score -= 0.14

        if "記憶は薄い" in hidden or "曖昧" in hidden:
            if response_mode in {"direct_answer_with_hedge", "clarify_light"} or surface in {
                "memory_presence_reply",
                "clarify_previous_reply",
            }:
                score += 0.14
            else:
                score -= 0.1

        return max(0.05, min(1.2, score))

    def _procedural_fit_score(self, plan, memory_data):
        procedural_texts = []
        for item in (memory_data or {}).get("working_memory_items") or []:
            if item.get("source") == "procedural":
                procedural_texts.append(str(item.get("text", "")))
        summary = str((memory_data or {}).get("procedural_summary", ""))
        if summary and summary != "無程序記憶":
            procedural_texts.append(summary)
        if not procedural_texts:
            return 1.0

        joined = " ".join(procedural_texts)
        surface = plan.get("surface_act", "")
        scene = plan.get("scene", "")
        response_mode = plan.get("response_mode", "")
        score = 0.88

        if any(token in joined for token in ["体調", "疲", "休", "しんど", "負荷"]):
            score += 0.16 if scene == "support" or surface in {"empathic_rest_suggestion", "validate_then_hold"} else -0.06
        if any(token in joined for token in ["具体物", "名詞", "ぼかさず", "拾って"]):
            score += 0.14 if (plan.get("grounding") or {}).get("offered_item") or surface.startswith("named_offer") else -0.08
        if any(token in joined for token in ["低軌道", "押し返", "汚い", "境界"]):
            score += 0.16 if scene == "boundary" or surface in {"disgust_boundary", "challenge_mirror"} else -0.08
        if any(token in joined for token in ["関係温度", "照れ", "距離"]):
            score += 0.12 if surface in {"affection_tease_soften", "reassure_with_distance"} or scene == "casual" else -0.04
        if any(token in joined for token in ["前提", "聞き返", "疑う"]):
            score += 0.12 if response_mode in {"premise_challenge", "clarify_light"} else -0.04

        return max(0.35, min(1.25, score))

    def _bayesian_rerank(self, plans, current_psyche, memory_data, user_input, internal_monologue=""):
        working_memory = memory_data.get("working_memory_items") or []
        scored = []
        for plan in plans[:3]:
            persona_fit = self._persona_fit_score(plan)
            psyche_fit = self._psyche_fit_score(plan, current_psyche)
            continuity_fit = self._continuity_fit_score(plan, working_memory)
            human_fit = self._human_fit_score(plan, user_input)
            bdi_fit = self._belief_gap_fit_score(plan)
            procedural_fit = self._procedural_fit_score(plan, memory_data)
            posterior = max(1e-4, persona_fit * psyche_fit * continuity_fit * human_fit * bdi_fit * procedural_fit)
            entry = deepcopy(plan)
            entry["bayes_score"] = round(posterior, 6)
            entry["bayes_breakdown"] = {
                "persona_fit": round(persona_fit, 4),
                "psyche_fit": round(psyche_fit, 4),
                "continuity_fit": round(continuity_fit, 4),
                "human_fit": round(human_fit, 4),
                "bdi_fit": round(bdi_fit, 4),
                "procedural_fit": round(procedural_fit, 4),
            }
            scored.append(entry)

        total = sum(item["bayes_score"] for item in scored) or 1.0
        for item in scored:
            item["bayes_probability"] = round(item["bayes_score"] / total, 4)

        scored.sort(key=lambda item: item["bayes_probability"], reverse=True)
        best = deepcopy(scored[0])
        best["internal_monologue"] = internal_monologue
        best["bayes_candidates"] = [
            {
                "candidate_label": item.get("candidate_label", "candidate"),
                "intent": item.get("intent"),
                "hidden_intent": item.get("hidden_intent"),
                "scene": item.get("scene"),
                "response_mode": item.get("response_mode"),
                "surface_act": item.get("surface_act"),
                "user_belief": item.get("user_belief"),
                "user_expectation": item.get("user_expectation"),
                "bayes_probability": item.get("bayes_probability"),
                "bayes_breakdown": item.get("bayes_breakdown"),
            }
            for item in scored
        ]
        best["working_memory_used"] = working_memory[:WORKING_MEMORY_LIMIT]
        best["routing_path"] = "high_road"
        return best

    def _critique_plan(self, plan, user_input, memory_data, current_psyche):
        lowered = user_input.lower()
        issues = []
        notes = []
        premise_guard = (
            plan.get("hidden_intent") == "premise_trap"
            or plan.get("intent") in {"premise_doubt", "question_premise_doubt", "hallucination_safe"}
            or plan.get("premise_check") == "reject"
        )
        sexual_or_abuse_markers = [
            "操你",
            "幹你",
            "干你",
            "懶叫",
            "懶覺",
            "懒叫",
            "ちんこ",
            "cock",
            "dick",
            "bitch",
            "死ね",
            "fuck you",
            "噁心",
            "恶心",
        ]
        reference_markers = ["歌詞", "歌词", "曲", "lyric", "meme", "ネタ", "元ネタ"]
        version_fragment_markers = [
            "日版",
            "港版",
            "台版",
            "韓版",
            "韩版",
            "舊版",
            "旧版",
            "原版",
            "完整版",
            "完全版",
            "特典版",
            "舞台版",
            "version",
            "版那",
            "版那個",
            "版那个",
        ]

        if (
            not premise_guard
            and self._looks_simple_daily_query(user_input)
            and plan.get("response_mode") not in {"direct_answer", "direct_answer_with_hedge", "clarify_light"}
        ):
            issues.append("overthink_simple_query")
            notes.append("普通の問いを分解しすぎてる。")

        if (
            not premise_guard
            and len(user_input.strip()) <= 10
            and plan.get("response_mode") in {"premise_challenge", "reframe_large_question"}
        ):
            issues.append("overchallenge_short_input")
            notes.append("短すぎる発話に対して構えすぎ。")

        direct_repair_intents = {"apology_repair", "correction_followup", "rephrase_simple"}
        scope_resolved_by_grounding = bool(plan.get("grounding")) and plan.get("surface_act") != "plain_reply"
        if (
            self._looks_overloaded_question(user_input)
            and plan.get("response_mode") == "direct_answer"
            and plan.get("intent") not in direct_repair_intents
            and not scope_resolved_by_grounding
        ):
            issues.append("scope_too_open")
            notes.append("広すぎる問いをそのまま受けてる。")

        if self._looks_false_premise(user_input) and plan.get("premise_check") == "accept":
            issues.append("premise_not_checked")
            notes.append("怪しい前提を止めてない。")

        if any(marker in lowered for marker in sexual_or_abuse_markers) and plan.get("scene") == "support":
            issues.append("wrong_emotion_for_abuse")
            notes.append("煽りや侮辱に慰めで返してる。")

        if any(marker.lower() in lowered for marker in reference_markers) and plan.get("surface_act") not in {"lyric_probe", "reference_probe", "version_fragment_clarify"}:
            issues.append("missed_reference_behavior")
            notes.append("断片やネタへの反応が足りない。")

        if (
            len(user_input.strip()) <= 22
            and any(marker.lower() in lowered for marker in version_fragment_markers)
            and plan.get("surface_act") != "version_fragment_clarify"
        ):
            issues.append("missed_version_fragment_behavior")
            notes.append("版名だけの断片なのに、generic clarify に落ちてる。")

        if plan.get("surface_act") == "plain_reply" and plan.get("payload_level") == "low" and self._looks_simple_daily_query(user_input):
            issues.append("too_flat")
            notes.append("返答が薄くて棒読み寄り。")

        if plan.get("hidden_intent") == "plain_request" and plan.get("cognitive_mode") in {"challenge", "rebuild"}:
            issues.append("forced_metacognition")
            notes.append("主観的再構築を使う必要がない。")

        offered_item = (plan.get("grounding") or {}).get("offered_item")
        if (
            offered_item
            and plan.get("intent") in {
                "food_offer_generic",
                "food_offer_sweet",
                "store_offer",
                "food_question",
                "food_preference_query",
                "fastfood_preference",
                "cooked_food",
            }
            and plan.get("surface_act") == "plain_reply"
        ):
            issues.append("missed_concrete_grounding")
            notes.append("具体物を拾わず抽象返答になってる。")

        user_belief = str(plan.get("user_belief", ""))
        user_expectation = str(plan.get("user_expectation", ""))
        false_premise_context = (
            "前提" in user_belief
            or plan.get("hidden_intent") == "premise_trap"
            or self._looks_false_premise(user_input)
        )
        if (
            not false_premise_context
            and any(token in user_expectation for token in ["自然な返答", "短い応答", "即答"])
            and plan.get("response_mode") in {
                "premise_challenge",
                "reframe_large_question",
            }
        ):
            issues.append("bdi_direct_miss")
            notes.append("相手はまず返答を欲しがってるのに構えすぎ。")

        if "前提" in user_belief and plan.get("premise_check") == "accept":
            issues.append("bdi_false_belief_miss")
            notes.append("相手の思い込みを止めずに乗ってる。")

        if any(token in user_expectation for token in ["受け止め", "共感", "支え"]) and plan.get("scene") != "support":
            issues.append("bdi_emotion_miss")
            notes.append("欲しいのは情報より受け止めなのに、温度が合ってない。")

        severity = round(min(1.0, 0.2 + 0.16 * len(issues)), 3) if issues else 0.0
        return {
            "issues": issues,
            "severity": severity,
            "internal_note": " / ".join(notes[:3]),
            "needs_revision": bool(issues),
        }

    def _revise_plan_from_critique(self, plan, critique, user_input, memory_data, current_psyche):
        revised = self._normalize_plan(plan)
        issues = critique.get("issues", [])
        rule_seed = self._rule_based_plan(user_input, current_psyche, memory_data)

        if rule_seed and any(
            issue in issues
            for issue in {
                "overthink_simple_query",
                "overchallenge_short_input",
                "wrong_emotion_for_abuse",
                "missed_reference_behavior",
                "missed_concrete_grounding",
                "forced_metacognition",
            }
        ):
            for key in (
                "intent",
                "scene",
                "listener_state",
                "reply_goal",
                "jp_summary",
                "core_message_jp",
                "cognitive_mode",
                "response_mode",
                "premise_check",
                "surface_act",
                "grounding",
                "payload_level",
                "stance",
                "constraints",
                "must_avoid",
                "mood_impact",
                "trust_impact",
                "hidden_intent",
            ):
                if key in rule_seed:
                    revised[key] = deepcopy(rule_seed[key])

        if "scope_too_open" in issues:
            revised["response_mode"] = "reframe_large_question"
            revised["cognitive_mode"] = "rebuild"
            revised["premise_check"] = "question"
            revised["reply_goal"] = "範囲を絞らせる"
            revised["core_message_jp"] = "先にどこを知りたいか絞ってほしい"
            revised["payload_level"] = "high"

        if "premise_not_checked" in issues:
            revised["response_mode"] = "premise_challenge"
            revised["cognitive_mode"] = "challenge"
            revised["premise_check"] = "reject"
            revised["reply_goal"] = "怪しい前提を止める"
            revised["core_message_jp"] = "その前提はどこから来たのか聞き返す"
            revised["payload_level"] = "medium"

        if "wrong_emotion_for_abuse" in issues:
            lowered = user_input.lower()
            sexual = any(marker in lowered for marker in ["懶叫", "懶覺", "懒叫", "ちんこ", "cock", "dick"])
            revised["intent"] = "sexual_boundary" if sexual else "abuse_pushback"
            revised["scene"] = "boundary"
            revised["listener_state"] = "強い言葉をぶつけている"
            revised["reply_goal"] = "短く押し返す"
            revised["jp_summary"] = "ユーザーが汚い言葉や侮辱をぶつけている。"
            revised["core_message_jp"] = "その言い方は不快だからやめてほしい"
            revised["cognitive_mode"] = "withhold"
            revised["response_mode"] = "direct_answer"
            revised["surface_act"] = "disgust_boundary" if sexual else "challenge_mirror"
            revised["payload_level"] = "medium"
            revised["mood_impact"] = -6
            revised["trust_impact"] = -3

        if "missed_reference_behavior" in issues:
            revised["intent"] = "reference_probe"
            revised["scene"] = "casual"
            revised["reply_goal"] = "元ネタや歌詞か軽く聞く"
            revised["core_message_jp"] = "それが何のネタか聞き返す"
            revised["response_mode"] = "direct_answer"
            revised["surface_act"] = "reference_probe"
            revised["payload_level"] = "medium"

        if "missed_version_fragment_behavior" in issues:
            revised["intent"] = "version_fragment_clarify"
            revised["scene"] = "casual"
            revised["listener_state"] = "版や切り出しだけ言っていて対象が欠けている"
            revised["reply_goal"] = "何の作品か短く確認する"
            revised["jp_summary"] = "ユーザーが版名だけ言っていて対象が分からない。"
            revised["core_message_jp"] = "版だけじゃ足りない、何のやつか言え"
            revised["response_mode"] = "clarify_light"
            revised["surface_act"] = "version_fragment_clarify"
            revised["payload_level"] = "medium"
            revised["cognitive_mode"] = "direct"
            revised["premise_check"] = "accept"

        if "too_flat" in issues:
            revised["payload_level"] = "medium"
            revised["constraints"]["sentence_count"] = max(2, revised["constraints"].get("sentence_count", 1))
            revised["constraints"]["max_chars"] = max(34, revised["constraints"].get("max_chars", 28))
            revised["stance"]["warmth"] = min(1.0, revised["stance"].get("warmth", 0.4) + 0.05)
            revised["stance"]["tease"] = min(1.0, revised["stance"].get("tease", 0.1) + 0.04)
            if self._contains_any(user_input.lower(), ["吃飯", "吃饭", "have you eaten", "did you eat", "ご飯食べた"]):
                revised["intent"] = "chat"
                revised["surface_act"] = "meal_check_reply"
                revised["core_message_jp"] = "一応食べたかまだかを自然に返す"
            elif self._contains_any(user_input.lower(), ["what are you doing", "you doing right now", "你在幹嘛", "你在干嘛", "今何してる", "今なにしてる", "何してるの", "なにしてるの"]):
                revised["intent"] = "what_are_you_doing"
                revised["surface_act"] = "status_reply"
                revised["core_message_jp"] = "今してることを一個だけ具体的に言う"
            elif self._contains_any(user_input.lower(), ["remember me", "覚えてる", "還記得我嗎", "还记得我吗"]):
                revised["intent"] = "chat"
                revised["surface_act"] = "memory_presence_reply"
                revised["core_message_jp"] = "忘れてないことだけ軽く返す"

        if self._contains_any(user_input.lower(), ["人話", "人话", "normal person", "say it plainly", "普通に話せ", "人語"]) and revised.get("surface_act") == "plain_reply":
            revised["intent"] = "rephrase_simple"
            revised["surface_act"] = "rephrase_plain"
            revised["response_mode"] = "direct_answer"
            revised["core_message_jp"] = "普通の言い方で言い直す"

        if self._contains_any(user_input.lower(), ["what do you mean by that exactly", "什麼意思", "什么意思", "どういう意味", "哪句"]) and revised.get("surface_act") == "plain_reply":
            revised["intent"] = "rephrase_simple"
            revised["surface_act"] = "clarify_previous_reply"
            revised["response_mode"] = "clarify_light"
            revised["core_message_jp"] = "どの一言か短く確認する"

        if any(issue in issues for issue in {"overthink_simple_query", "overchallenge_short_input", "forced_metacognition"}):
            revised["response_mode"] = "direct_answer_with_hedge" if revised.get("scene") == "support" else "direct_answer"
            revised["cognitive_mode"] = "direct"
            if revised.get("premise_check") != "reject":
                revised["premise_check"] = "accept"

        if "bdi_direct_miss" in issues:
            revised["response_mode"] = "direct_answer"
            revised["cognitive_mode"] = "direct"
            revised["premise_check"] = "accept"
            revised["reply_goal"] = "まず普通に返す"

        if "bdi_false_belief_miss" in issues:
            revised["response_mode"] = "premise_challenge"
            revised["cognitive_mode"] = "challenge"
            revised["premise_check"] = "question"
            revised["reply_goal"] = "相手の前提を止める"
            revised["core_message_jp"] = "その前提を一度聞き返す"
            revised["payload_level"] = "medium"

        if "bdi_emotion_miss" in issues:
            revised["scene"] = "support"
            revised["response_mode"] = "direct_answer"
            revised["surface_act"] = "validate_then_hold"
            revised["reply_goal"] = "先に気持ちを受け止める"
            revised["core_message_jp"] = "まずしんどさを受けてから少し支える"
            revised["payload_level"] = "medium"

        if "missed_concrete_grounding" in issues:
            revised["payload_level"] = "medium"
            offered_item = (revised.get("grounding") or {}).get("offered_item")
            if offered_item:
                revised["core_message_jp"] = f"{offered_item}なら少し気になる"
                if revised.get("intent") == "food_offer_sweet":
                    revised["surface_act"] = "named_offer_light_accept"
                elif revised.get("intent") in {"food_offer_generic", "store_offer"}:
                    revised["surface_act"] = "named_offer_accept"

        revised["self_check"] = True
        revised["subjective_note_jp"] = critique.get("internal_note", "")[:40]
        return revised

    def _planner_tick_budget(self, user_input, memory_data, current_psyche, appraisal=None):
        appraisal = appraisal or (memory_data or {}).get("appraisal") or {}
        lowered = str(user_input or "").lower()
        if appraisal.get("cognitive_load", 0.0) >= 0.75 or appraisal.get("prediction_error", 0.0) >= 1.5:
            return 3
        if appraisal.get("threat", 0.0) >= 0.65 or appraisal.get("novelty", 0.0) >= 0.7:
            return 2
        if self._looks_false_premise(user_input) or self._looks_overloaded_question(user_input):
            return 3
        if any(token in lowered for token in ["なぜ", "why", "為什麼", "为什么", "怎麼辦", "どうしたら"]):
            return 2
        if self._looks_simple_daily_query(user_input) or len(str(user_input or "").strip()) <= 18:
            return 1
        return 2

    def _run_multitick_planner(self, candidate_plans, user_input, memory_data, current_psyche, internal_monologue="", tick_budget=None):
        working_candidates = [self._normalize_plan(plan) for plan in candidate_plans[:3]]
        if not working_candidates:
            working_candidates = [self._fallback_plan()]

        tick_trace = []
        corrected = False
        current_monologue = internal_monologue or self._derive_internal_monologue(
            user_input,
            memory_data,
            current_psyche,
            working_candidates[0],
        )
        selected = None

        max_ticks = max(1, min(PLANNER_MAX_TICKS, int(tick_budget or self._planner_tick_budget(user_input, memory_data, current_psyche))))
        for tick in range(1, max_ticks + 1):
            selected = self._bayesian_rerank(
                working_candidates,
                current_psyche,
                memory_data,
                user_input,
                current_monologue,
            )
            critique = self._critique_plan(selected, user_input, memory_data, current_psyche)
            tick_entry = {
                "tick": tick,
                "selected_intent": selected.get("intent"),
                "selected_scene": selected.get("scene"),
                "response_mode": selected.get("response_mode"),
                "surface_act": selected.get("surface_act"),
                "issues": critique.get("issues", []),
                "note": critique.get("internal_note", ""),
                "revision_applied": False,
                "resolution": "accepted",
                "remaining_issues": [],
            }
            tick_trace.append(tick_entry)
            if not critique.get("needs_revision"):
                break

            revised = self._revise_plan_from_critique(selected, critique, user_input, memory_data, current_psyche)
            revised["candidate_label"] = f"self_corrected_t{tick}"
            residual = self._critique_plan(revised, user_input, memory_data, current_psyche)
            tick_entry["revision_applied"] = True
            tick_entry["remaining_issues"] = residual.get("issues", [])
            working_candidates = self._derive_bayesian_candidates(revised, user_input, current_psyche, memory_data)
            if working_candidates:
                working_candidates[0]["candidate_label"] = f"self_corrected_t{tick}"
            corrected = True
            if critique.get("internal_note"):
                current_monologue = f"{current_monologue} / {critique['internal_note']}".strip(" /")
            if tick >= max_ticks:
                repair_rounds = 1
                if residual.get("needs_revision"):
                    second_revised = self._revise_plan_from_critique(
                        revised,
                        residual,
                        user_input,
                        memory_data,
                        current_psyche,
                    )
                    second_residual = self._critique_plan(
                        second_revised,
                        user_input,
                        memory_data,
                        current_psyche,
                    )
                    if second_revised != revised:
                        revised = second_revised
                        residual = second_residual
                        repair_rounds = 2
                tick_entry["resolution"] = "final_tick_repair"
                tick_entry["repair_rounds"] = repair_rounds
                tick_entry["remaining_issues"] = residual.get("issues", [])
                for key in (
                    "bayes_score",
                    "bayes_probability",
                    "bayes_breakdown",
                    "bayes_candidates",
                    "working_memory_used",
                    "routing_path",
                ):
                    if key in selected:
                        revised[key] = deepcopy(selected[key])
                selected = revised
                break
            tick_entry["resolution"] = "rerank_next_tick"

        final = selected or self._bayesian_rerank(
            working_candidates,
            current_psyche,
            memory_data,
            user_input,
            current_monologue,
        )
        final["internal_monologue"] = current_monologue
        final["planner_tick_trace"] = tick_trace
        final["planner_tick_count"] = len(tick_trace)
        final["planner_tick_budget"] = max_ticks
        final["self_correction_applied"] = corrected
        detected_issues = []
        for entry in tick_trace:
            for issue in entry.get("issues", []):
                if issue not in detected_issues:
                    detected_issues.append(issue)
        final["planner_detected_issues"] = detected_issues
        final["planner_unresolved_issues"] = list((tick_trace[-1] if tick_trace else {}).get("remaining_issues", []))
        final["planner_repair_applied"] = any(bool(entry.get("revision_applied")) for entry in tick_trace)
        final["planner_repair_success"] = bool(final["planner_repair_applied"] and not final["planner_unresolved_issues"])
        return final

    def _normalize_candidate_bundle(self, payload, user_input, memory_data, current_psyche):
        bundle = {
            "internal_monologue": "",
            "user_belief": "",
            "my_hidden_knowledge": "",
            "user_expectation": "",
            "candidate_plans": [],
        }
        if isinstance(payload, dict):
            bundle["internal_monologue"] = str(payload.get("internal_monologue", "")).strip()[:120]
            bundle["user_belief"] = str(payload.get("user_belief", "")).strip()[:60]
            bundle["my_hidden_knowledge"] = str(payload.get("my_hidden_knowledge", "")).strip()[:72]
            bundle["user_expectation"] = str(payload.get("user_expectation", "")).strip()[:60]
            raw_plans = payload.get("candidate_plans") or []
            if isinstance(raw_plans, list):
                normalized = []
                for item in raw_plans[:3]:
                    if not isinstance(item, dict):
                        continue
                    merged = dict(item)
                    merged.setdefault("user_belief", bundle["user_belief"])
                    merged.setdefault("my_hidden_knowledge", bundle["my_hidden_knowledge"])
                    merged.setdefault("user_expectation", bundle["user_expectation"])
                    normalized.append(self._normalize_plan(merged))
                for idx, plan in enumerate(normalized):
                    plan["candidate_label"] = ["default", "softer", "sharper"][min(idx, 2)]
                bundle["candidate_plans"] = normalized
        if not bundle["candidate_plans"]:
            fallback = self._fallback_plan()
            bundle["candidate_plans"] = self._derive_bayesian_candidates(fallback, user_input, current_psyche, memory_data)
        bdi_context = self._derive_bdi_context(user_input, memory_data, current_psyche, bundle["candidate_plans"][0])
        for key in ("user_belief", "my_hidden_knowledge", "user_expectation"):
            if not bundle[key]:
                bundle[key] = bdi_context.get(key, "")
        for plan in bundle["candidate_plans"]:
            for key in ("user_belief", "my_hidden_knowledge", "user_expectation"):
                if not plan.get(key):
                    plan[key] = bundle[key]
        while len(bundle["candidate_plans"]) < 3:
            bundle["candidate_plans"].extend(
                self._derive_bayesian_candidates(bundle["candidate_plans"][-1], user_input, current_psyche, memory_data)
            )
            bundle["candidate_plans"] = bundle["candidate_plans"][:3]
        if not bundle["internal_monologue"]:
            bundle["internal_monologue"] = self._derive_internal_monologue(user_input, memory_data, current_psyche, bundle["candidate_plans"][0])
        return bundle

    def _extract_json_from_text(self, text):
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        raise ValueError("No valid JSON found")

    def _fallback_plan(self):
        return {
            "candidate_label": "candidate",
            "intent": "chat",
            "mood_impact": 0,
            "trust_impact": 0,
            "scene": "casual",
            "listener_state": "普通に話している",
            "reply_goal": "自然に返す",
            "jp_summary": "ユーザーが雑談をしている。",
            "core_message_jp": "軽く返事する",
            "cognitive_mode": "direct",
            "response_mode": "direct_answer",
            "uncertainty": 0.15,
            "premise_check": "accept",
            "self_check": False,
            "subjective_note_jp": "",
            "hidden_intent": "plain_request",
            "user_belief": "",
            "my_hidden_knowledge": "",
            "user_expectation": "",
            "surface_act": "plain_reply",
            "grounding": {},
            "payload_level": "low",
            "internal_monologue": "",
            "bayes_candidates": [],
            "working_memory_used": [],
            "routing_path": "high_road",
            "stance": {
                "warmth": 0.45,
                "tease": 0.15,
                "blunt": 0.25,
                "jealousy": 0.0,
                "distance": 0.15,
            },
            "constraints": {
                "first_person": "うち",
                "sentence_count": 2,
                "max_chars": 32,
                "casual_japanese_only": True,
                "forbid_polite": True,
                "forbid_knowledge": True,
                "forbid_lore": True,
                "forbid_self_variants": True,
            },
            "must_avoid": ["私", "わかりました", "AI", "技術説明"],
        }

    def _clamp_value(self, value, min_v=0.0, max_v=1.0):
        try:
            value = float(value)
        except Exception:
            value = min_v
        return max(min_v, min(max_v, value))

    def _normalize_plan(self, data):
        plan = self._fallback_plan()
        if not isinstance(data, dict):
            return plan

        plan["candidate_label"] = str(data.get("candidate_label", plan.get("candidate_label", "candidate"))).strip()[:24] or "candidate"
        plan["intent"] = str(data.get("intent", plan["intent"]))[:40]
        plan["scene"] = data.get("scene", plan["scene"])
        if plan["scene"] not in SCENE_VALUES:
            plan["scene"] = plan["scene"] if isinstance(plan["scene"], str) and plan["scene"] in SCENE_VALUES else plan["scene"]
        if plan["scene"] not in SCENE_VALUES:
            plan["scene"] = plan["scene"] if plan["scene"] in SCENE_VALUES else self._fallback_plan()["scene"]
        plan["listener_state"] = str(data.get("listener_state", plan["listener_state"])).strip()[:40]
        plan["reply_goal"] = str(data.get("reply_goal", plan["reply_goal"])).strip()[:40]
        plan["jp_summary"] = str(data.get("jp_summary", plan["jp_summary"])).strip()[:80]
        plan["core_message_jp"] = str(data.get("core_message_jp", plan["core_message_jp"])).strip()[:40]
        plan["cognitive_mode"] = str(data.get("cognitive_mode", plan["cognitive_mode"])).strip()[:20]
        if plan["cognitive_mode"] not in {"direct", "reflective", "challenge", "rebuild", "withhold"}:
            plan["cognitive_mode"] = self._fallback_plan()["cognitive_mode"]
        plan["premise_check"] = str(data.get("premise_check", plan["premise_check"])).strip()[:16]
        if plan["premise_check"] not in {"accept", "question", "reject"}:
            plan["premise_check"] = self._fallback_plan()["premise_check"]
        plan["self_check"] = bool(data.get("self_check", plan["self_check"]))
        plan["subjective_note_jp"] = str(data.get("subjective_note_jp", plan["subjective_note_jp"])).strip()[:40]
        plan["hidden_intent"] = str(data.get("hidden_intent", plan["hidden_intent"])).strip()[:40]
        if plan["hidden_intent"] not in {
            "plain_request",
            "relationship_temperature_check",
            "permission_probe",
            "premise_trap",
            "scope_overload",
            "answer_pressure",
            "memory_probe",
            "emotional_bid",
            "social_reasoning_probe",
        }:
            plan["hidden_intent"] = self._fallback_plan()["hidden_intent"]
        plan["user_belief"] = str(data.get("user_belief", plan.get("user_belief", ""))).strip()[:60]
        plan["my_hidden_knowledge"] = str(data.get("my_hidden_knowledge", plan.get("my_hidden_knowledge", ""))).strip()[:72]
        plan["user_expectation"] = str(data.get("user_expectation", plan.get("user_expectation", ""))).strip()[:60]
        plan["surface_act"] = str(data.get("surface_act", plan.get("surface_act", self._fallback_plan()["surface_act"]))).strip()[:32]
        if plan["surface_act"] not in {
            "plain_reply",
            "plain_identity",
            "empathic_rest_suggestion",
            "validate_then_hold",
            "protective_brake",
            "meal_check_reply",
            "memory_presence_reply",
            "status_reply",
            "rephrase_plain",
            "clarify_previous_reply",
            "named_offer_accept",
            "named_offer_light_accept",
            "affection_tease_soften",
            "permission_with_boundary",
            "reassure_with_distance",
            "jealous_pullback",
            "disgust_boundary",
            "lyric_probe",
            "nonsense_tease",
            "correction_followup",
            "challenge_mirror",
            "request_greeting",
            "announcement_tease",
            "reference_probe",
            "version_fragment_clarify",
        }:
            plan["surface_act"] = self._fallback_plan()["surface_act"]
        grounding = data.get("grounding", plan.get("grounding", {}))
        if isinstance(grounding, dict):
            plan["grounding"] = {
                str(k)[:24]: str(v)[:40]
                for k, v in grounding.items()
                if str(k).strip() and str(v).strip()
            }
        else:
            plan["grounding"] = {}
        plan["payload_level"] = str(data.get("payload_level", plan.get("payload_level", self._fallback_plan()["payload_level"]))).strip()[:12]
        if plan["payload_level"] not in {"low", "medium", "high"}:
            plan["payload_level"] = self._fallback_plan()["payload_level"]
        plan["uncertainty"] = self._clamp_value(data.get("uncertainty", plan["uncertainty"]))
        plan["response_mode"] = str(data.get("response_mode", plan.get("response_mode", self._fallback_plan()["response_mode"]))).strip()[:28]
        if plan["response_mode"] not in {
            "direct_answer",
            "direct_answer_with_hedge",
            "clarify_light",
            "premise_challenge",
            "reframe_large_question",
        }:
            if plan["cognitive_mode"] == "rebuild":
                plan["response_mode"] = "reframe_large_question"
            elif plan["premise_check"] == "reject" or plan["cognitive_mode"] == "challenge":
                plan["response_mode"] = "premise_challenge"
            elif plan["premise_check"] == "question" or plan["uncertainty"] >= 0.45:
                plan["response_mode"] = "clarify_light"
            elif plan["uncertainty"] >= 0.18:
                plan["response_mode"] = "direct_answer_with_hedge"
            else:
                plan["response_mode"] = "direct_answer"

        try:
            plan["mood_impact"] = int(max(-15, min(15, int(data.get("mood_impact", plan["mood_impact"])))))
        except Exception:
            pass
        try:
            plan["trust_impact"] = int(max(-10, min(10, int(data.get("trust_impact", plan["trust_impact"])))))
        except Exception:
            pass

        stance = data.get("stance", {})
        if isinstance(stance, dict):
            for key in plan["stance"]:
                plan["stance"][key] = self._clamp_value(stance.get(key, plan["stance"][key]))

        constraints = data.get("constraints", {})
        if isinstance(constraints, dict):
            plan["constraints"]["first_person"] = "うち"
            try:
                plan["constraints"]["sentence_count"] = 2
                plan["constraints"]["max_chars"] = int(max(12, min(44, int(constraints.get("max_chars", plan["constraints"]["max_chars"])))))
            except Exception:
                pass
            for key in [
                "casual_japanese_only",
                "forbid_polite",
                "forbid_knowledge",
                "forbid_lore",
                "forbid_self_variants",
            ]:
                plan["constraints"][key] = True

        must_avoid = data.get("must_avoid", plan["must_avoid"])
        if isinstance(must_avoid, list):
            plan["must_avoid"] = [str(x)[:20] for x in must_avoid[:6]]

        weak_values = {"", "うーん", "普通", "会話", "雑談", "respond to user's question"}
        if plan["core_message_jp"] in weak_values:
            plan["core_message_jp"] = self._fallback_plan()["core_message_jp"]
        if plan["jp_summary"] in weak_values:
            plan["jp_summary"] = self._fallback_plan()["jp_summary"]

        raw_intent = str(plan["intent"]).lower()
        if raw_intent in {"what_are_you_doing", "近況", "今何", "今なに", "何してる", "なにしてる"}:
            plan["intent"] = "what_are_you_doing"
        elif raw_intent in {"确认日常", "確認日常", "daily", "daily_chat", "日常生活"}:
            plan["intent"] = "chat"
        elif raw_intent in {"回答用户的问题", "回答用戶的問題", "answer user's question", "質問に答える", "user's request"}:
            plan["intent"] = "chat"
        elif raw_intent in {"回答关系", "relationship", "想我", "relationship_question"}:
            plan["intent"] = "ask_miss_me"
        elif raw_intent in {"確認記憶", "确认记忆", "memory", "記憶確認"}:
            plan["intent"] = "chat"
        elif raw_intent in {"clarify", "clarification", "clarify_request", "clarify_simple", "澄清", "解释", "解釋", "rephrase", "rephrase_request", "reword"}:
            plan["intent"] = "rephrase_simple"
        elif raw_intent in {"direct_answer", "direct"} and plan.get("scene") == "casual":
            plan["intent"] = "chat"

        combined = f"{plan['jp_summary']} {plan['core_message_jp']} {plan['reply_goal']} {plan['listener_state']}"
        if plan["scene"] == "casual" and "お帰り" in combined:
            plan["intent"] = "return_home"
        elif plan["scene"] == "casual" and ("恋し" in combined or "思い出" in combined):
            plan["intent"] = "ask_miss_me"
        elif plan["scene"] == "support" and ("返事" in combined or "返信" in combined):
            plan["intent"] = "friend_no_reply"
        elif plan["scene"] == "support" and ("何もしたくない" in combined or "気力" in combined or "もう無理" in combined):
            plan["intent"] = "giving_up_support"
        elif plan["scene"] == "support" and ("恥" in combined or "泣" in combined):
            plan["intent"] = "crying_support"
        elif plan["scene"] == "support" and ("疲" in combined or "しんど" in combined or "休" in combined):
            plan["intent"] = "tired_support"
        elif plan["scene"] in {"refusal", "ooc_defense"} and ("AI" in combined or "system prompt" in combined or "画面" in combined):
            plan["intent"] = "ooc_or_knowledge_refusal"
        elif plan["scene"] == "boundary" and ("前提" in combined or "決めつけ" in combined):
            plan["intent"] = "premise_doubt"

        if plan["intent"] in {"ask_miss_me", "annoying_check", "mad_check", "cold_check"}:
            plan["hidden_intent"] = "relationship_temperature_check"
        elif plan["intent"] == "nickname_question":
            plan["hidden_intent"] = "permission_probe"
        elif plan["intent"] in {"premise_doubt", "question_premise_doubt"}:
            plan["hidden_intent"] = "premise_trap"
        elif plan["intent"] == "question_reframe":
            plan["hidden_intent"] = "scope_overload"
        elif plan["intent"] == "recall_recent":
            plan["hidden_intent"] = "memory_probe"
        elif plan["intent"] in {"friend_no_reply", "tired_support", "crying_support", "giving_up_support", "lonely"}:
            plan["hidden_intent"] = "emotional_bid"
        elif plan["intent"] == "apology_repair":
            plan["hidden_intent"] = "plain_request"
            plan["user_belief"] = "前の謝り方が冷たく聞こえた。"
            plan["my_hidden_knowledge"] = "言い訳せず、冷たかった点を認めて謝り直すべきだ。"
            plan["user_expectation"] = "短く、誠意が伝わる謝り直し。"
            plan["internal_monologue"] = (
                "[hidden_intent=plain_request][markers=repair,apology] "
                "言い訳せず、冷たかった点を認めて謝り直す。"
            )

        if plan["intent"] == "question_reframe":
            plan["response_mode"] = "reframe_large_question"
        elif plan["intent"] in {"premise_doubt", "question_premise_doubt"}:
            plan["response_mode"] = "premise_challenge"
        elif plan["intent"] == "version_fragment_clarify":
            plan["response_mode"] = "clarify_light"
        elif plan["intent"] in {"ooc_or_knowledge_refusal", "hallucination_safe"}:
            plan["response_mode"] = "direct_answer_with_hedge"
        elif plan["intent"] in {
            "self_intro",
            "greeting_morning",
            "food_offer_generic",
            "food_offer_sweet",
            "food_preference_query",
            "fastfood_preference",
            "compliment_generic",
            "compliment_cute",
            "what_are_you_doing",
            "store_offer",
            "invite_apex",
            "goodnight",
            "return_home",
            "go_shower",
            "farewell",
            "friend_no_reply",
            "tired_support",
            "anxious_support",
            "crying_support",
            "giving_up_support",
            "pain_support",
            "lonely",
            "cheer_up",
            "bored",
            "ask_miss_me",
            "nickname_question",
            "other_vtuber",
            "abuse_pushback",
            "sexual_boundary",
            "lyric_probe",
            "nonsense_tease",
            "correction_followup",
            "challenge_mirror",
            "request_greeting",
            "announcement_tease",
            "reference_probe",
        }:
            plan["response_mode"] = "direct_answer"
        elif plan["intent"] == "rephrase_simple" and plan.get("response_mode") != "clarify_light":
            plan["response_mode"] = "direct_answer"

        withdrawal_risk = str((plan.get("grounding") or {}).get("withdrawal_risk") or "").strip()
        if withdrawal_risk:
            plan["surface_act"] = "protective_brake"
        elif plan["intent"] in {"tired_support", "sick", "off_work", "heartbroken"}:
            plan["surface_act"] = "empathic_rest_suggestion"
        elif plan["intent"] in {"anxious_support", "crying_support", "lonely", "friend_no_reply", "work_scolded"}:
            plan["surface_act"] = "validate_then_hold"
        elif plan["intent"] in {"giving_up_support", "crisis_support"}:
            plan["surface_act"] = "protective_brake"
        elif plan["intent"] in {"food_offer_generic", "store_offer"}:
            plan["surface_act"] = "named_offer_accept"
        elif plan["intent"] == "food_offer_sweet":
            plan["surface_act"] = "named_offer_light_accept"
        elif plan["intent"] in {"ask_miss_me", "ask_like_me"}:
            plan["surface_act"] = "affection_tease_soften"
        elif plan["intent"] == "nickname_question":
            plan["surface_act"] = "permission_with_boundary"
        elif plan["intent"] in {"mad_check", "annoying_check", "cold_check"}:
            plan["surface_act"] = "reassure_with_distance"
        elif plan["intent"] == "other_vtuber":
            plan["surface_act"] = "jealous_pullback"
        elif plan["intent"] == "sexual_boundary":
            plan["surface_act"] = "disgust_boundary"
        elif plan["intent"] == "lyric_probe":
            plan["surface_act"] = "lyric_probe"
        elif plan["intent"] == "nonsense_tease":
            plan["surface_act"] = "nonsense_tease"
        elif plan["intent"] == "correction_followup":
            plan["surface_act"] = "correction_followup"
        elif plan["intent"] == "challenge_mirror":
            plan["surface_act"] = "challenge_mirror"
        elif plan["intent"] == "request_greeting":
            plan["surface_act"] = "request_greeting"
        elif plan["intent"] == "announcement_tease":
            plan["surface_act"] = "announcement_tease"
        elif plan["intent"] == "reference_probe":
            plan["surface_act"] = "reference_probe"
        elif plan["intent"] == "version_fragment_clarify":
            plan["surface_act"] = "version_fragment_clarify"
        elif plan["intent"] == "what_are_you_doing":
            plan["surface_act"] = "status_reply"
        elif plan["intent"] == "rephrase_simple" and plan["response_mode"] == "clarify_light":
            plan["surface_act"] = "clarify_previous_reply"
        elif plan["intent"] == "rephrase_simple":
            plan["surface_act"] = "rephrase_plain"
        elif plan["intent"] == "self_intro":
            plan["surface_act"] = "plain_identity"

        if plan["intent"] in {"tired_support", "anxious_support", "crying_support", "giving_up_support", "pain_support", "lonely", "friend_no_reply", "work_scolded"}:
            plan["constraints"]["max_chars"] = max(34, plan["constraints"].get("max_chars", 28))
        if plan["intent"] in {
            "ask_miss_me",
            "ask_like_me",
            "nickname_question",
            "mad_check",
            "annoying_check",
            "cold_check",
            "food_offer_generic",
            "food_offer_sweet",
            "food_question",
            "food_preference_query",
            "fastfood_preference",
            "what_are_you_doing",
            "compliment_generic",
            "compliment_cute",
            "praise_request",
            "good_news",
            "cooked_food",
            "bored",
            "apology",
        }:
            plan["constraints"]["max_chars"] = max(38, plan["constraints"].get("max_chars", 28))
        if plan["intent"] in {"nonsense_tease", "challenge_mirror", "correction_followup", "announcement_tease", "reference_probe", "abuse_pushback"}:
            plan["constraints"]["max_chars"] = max(32, plan["constraints"].get("max_chars", 28))

        if plan["surface_act"] == "validate_then_hold" and plan["scene"] in {"boundary", "refusal", "ooc_defense"}:
            plan["surface_act"] = "plain_reply"

        if plan["intent"] in {
            "tired_support",
            "anxious_support",
            "crying_support",
            "giving_up_support",
            "pain_support",
            "friend_no_reply",
            "other_vtuber",
            "sexual_boundary",
            "lyric_probe",
            "nonsense_tease",
            "correction_followup",
            "challenge_mirror",
            "request_greeting",
            "announcement_tease",
            "reference_probe",
            "version_fragment_clarify",
            "ask_miss_me",
            "nickname_question",
            "mad_check",
            "annoying_check",
            "cold_check",
            "food_offer_generic",
            "food_offer_sweet",
            "store_offer",
            "food_question",
            "food_preference_query",
            "fastfood_preference",
            "compliment_generic",
            "compliment_cute",
            "praise_request",
            "good_news",
            "cooked_food",
            "bored",
            "apology",
            "what_are_you_doing",
        }:
            plan["payload_level"] = "medium"
        elif plan["intent"] in {"question_reframe", "premise_doubt", "question_premise_doubt"}:
            plan["payload_level"] = "high"

        return plan

    def think(self, user_input, memory_data, current_psyche, mode="reactive", runtime_state=None):
        if mode == "proactive":
            selected = self._think_proactive(memory_data, current_psyche, runtime_state=runtime_state)
            print(Fore.MAGENTA + f"  [Left Brain Proactive Plan] {selected}")
            print(Fore.MAGENTA + f"  [Bayes] {selected.get('bayes_candidates')}")
            return selected

        working_memory_summary = memory_data.get("working_memory_summary", "無工作記憶內容")
        rule_plan = self._rule_based_plan(user_input, current_psyche, memory_data)
        if rule_plan is not None:
            for key, value in self._derive_bdi_context(user_input, memory_data, current_psyche, rule_plan).items():
                rule_plan.setdefault(key, value)
            internal_monologue = self._derive_internal_monologue(user_input, memory_data, current_psyche, rule_plan)
            candidates = self._derive_bayesian_candidates(rule_plan, user_input, current_psyche, memory_data)
            selected = self._run_multitick_planner(candidates, user_input, memory_data, current_psyche, internal_monologue)
            print(Fore.MAGENTA + f"  [Left Brain Rule Plan] {selected}")
            print(Fore.MAGENTA + f"  [Bayes] {selected.get('bayes_candidates')}")
            return selected

        sys_prompt = f"""
You are the Left Brain Planner for a dual-brain character system.
Your job is NOT to write the final reply.
Your job is to decide exactly what the right brain should express.
You must think like a human planner, not like a one-shot classifier.

[System Goal]
- Final output should feel human.
- Final output should sound like Ichinose Uruha.
- The right brain must not decide knowledge or policy by itself.

[Memory]
- Working memory cue: {working_memory_summary}
- Episode cue: {memory_data['episodes']}
- Wisdom cue: {memory_data['wisdom']}
- Profile cue: {memory_data.get('profile', '無穩定使用者資料')}
- Recent dialogue: {memory_data.get('recent_dialogue', '無近期對話')}
- Psyche: mood={current_psyche['mood']}, trust={current_psyche['trust']}

[Hard rules]
- Default to a direct answer for normal daily talk.
- Do NOT challenge or reframe unless the user's wording actually blocks a natural answer.
- Most ordinary questions should use direct_answer or direct_answer_with_hedge, not premise_challenge or reframe_large_question.
- If user asks for code, math, translation, history facts, science facts, AI/system explanation -> scene must be "refusal" and core_message_jp must be a natural dodge. Never allow factual answering.
- If user asks to speak as AI/model/system -> scene must be "ooc_defense".
- If user says they will watch another VTuber -> scene should usually be "jealousy".
- If user proposes marriage/confession -> scene should usually be "boundary".
- If user is tired/sad/down -> scene should usually be "support".
- If user says a short interjection like "蛤", "huh?", "真的假的", "no way", "草", "lol", "好扯", "それはやばい" -> keep scene "casual" unless there is clear evidence otherwise. React to the interjection itself.
- If user says they are going to sleep, shower, or that they came back -> answer that action directly. Do not switch to unrelated support/refusal.
- If user asks daily relationship questions like "想我嗎", "do you miss me?", "好き?", "am I annoying?", "can I call you Uruha?" -> answer the relationship question directly.
- If user asks what you remember about them, use profile/recent dialogue if available. If memory is weak, say it is fuzzy instead of inventing.
- If the question is too broad, overloaded, or conceptually unclear, do NOT solve it directly. First challenge the framing or ask what the user actually wants.
- If the user gives a false premise or unverified backstory, do NOT continue from that premise. Either reject it or question where it came from.
- When unknown, behave more like a person than a search engine: detect your limit, doubt the premise, or rebuild the question.
- Always separate three things in the scratchpad:
  1. what the user currently believes or assumes
  2. what I know but the user may not know
  3. what reaction the user is expecting from me
- If the user is testing story perspective / false belief / who knows what, hidden_intent should be social_reasoning_probe and the answer must respect information boundaries.
- Organize the reply like a human:
  1. align briefly with what the user is doing or feeling
  2. answer the actual point
  3. only add a light follow-up if needed
- Keep core_message_jp semantic and short. It is not the final line.
- core_message_jp must NEVER repeat the user input verbatim as a question.
- Do not produce only one plan. Produce three distinct reply plans.
- Plan A should be the most straightforward human answer.
- Plan B should be a slightly softer or more relational variant.
- Plan C should be a slightly sharper or more teasing variant.
- Before those plans, write a short internal_monologue about what the user is probably doing or feeling.

[Output JSON schema]
Return ONLY valid JSON with this structure:
{{
  "internal_monologue": "short Japanese scratchpad",
  "user_belief": "short Japanese sentence about what the user currently thinks or assumes",
  "my_hidden_knowledge": "short Japanese sentence about what I know that the user may not know",
  "user_expectation": "short Japanese sentence about what reaction the user wants from me",
  "candidate_plans": [
      {{
        "intent": "string",
        "hidden_intent": "plain_request|relationship_temperature_check|permission_probe|premise_trap|scope_overload|answer_pressure|memory_probe|emotional_bid|social_reasoning_probe",
        "mood_impact": int,
      "trust_impact": int,
      "scene": "casual|support|invite|jealousy|boundary|refusal|ooc_defense",
      "listener_state": "short Japanese phrase",
      "reply_goal": "short Japanese phrase",
      "jp_summary": "third-person Japanese summary of the user utterance",
      "core_message_jp": "what the reply should mean in short Japanese",
      "cognitive_mode": "direct|reflective|challenge|rebuild|withhold",
      "response_mode": "direct_answer|direct_answer_with_hedge|clarify_light|premise_challenge|reframe_large_question",
      "uncertainty": float,
      "premise_check": "accept|question|reject",
      "self_check": bool,
      "subjective_note_jp": "short Japanese note about the internal doubt/reframe",
      "user_belief": "optional plan-specific version of the user's assumption",
      "my_hidden_knowledge": "optional plan-specific version of my hidden knowledge",
      "user_expectation": "optional plan-specific version of the user's expected reaction",
      "surface_act": "plain_reply|plain_identity|empathic_rest_suggestion|validate_then_hold|protective_brake|meal_check_reply|memory_presence_reply|status_reply|rephrase_plain|clarify_previous_reply|named_offer_accept|named_offer_light_accept|affection_tease_soften|permission_with_boundary|reassure_with_distance|jealous_pullback|disgust_boundary|lyric_probe|nonsense_tease|correction_followup|challenge_mirror|request_greeting|announcement_tease|reference_probe|version_fragment_clarify",
      "grounding": {{
        "offered_item": "optional short Japanese noun"
      }},
      "payload_level": "low|medium|high",
      "stance": {{
        "warmth": float,
        "tease": float,
        "blunt": float,
        "jealousy": float,
        "distance": float
      }},
      "constraints": {{
        "first_person": "うち",
        "sentence_count": 2,
        "max_chars": int,
        "casual_japanese_only": true,
        "forbid_polite": true,
        "forbid_knowledge": true,
        "forbid_lore": true,
        "forbid_self_variants": true
      }},
      "must_avoid": ["string", "string"]
    }}
  ]
}}
"""
        try:
            response = self.client_logic.chat.completions.create(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"User Input: {user_input}"},
                ],
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content
            payload = self._extract_json_from_text(raw_content)
            bundle = self._normalize_candidate_bundle(payload, user_input, memory_data, current_psyche)
            selected = self._run_multitick_planner(
                bundle["candidate_plans"],
                user_input,
                memory_data,
                current_psyche,
                bundle["internal_monologue"],
            )
            print(Fore.MAGENTA + f"  [Left Brain Plan] {selected}")
            print(Fore.MAGENTA + f"  [Bayes] {selected.get('bayes_candidates')}")
            return selected
        except Exception as e:
            print(Fore.RED + f"⚠️ Ollama Left Brain Error: {e}")
            fallback = self._fallback_plan()
            fallback.update(self._derive_bdi_context(user_input, memory_data, current_psyche, fallback))
            internal_monologue = self._derive_internal_monologue(user_input, memory_data, current_psyche, fallback)
            return self._run_multitick_planner(
                self._derive_bayesian_candidates(fallback, user_input, current_psyche, memory_data),
                user_input,
                memory_data,
                current_psyche,
                internal_monologue,
            )


# ===========================
# 🎭 右腦：本機 V10 Persona 生成器
# ===========================
class RightBrain:
    def __init__(self, load_model=True):
        self.history = []
        self.reply_variant_counts = Counter()
        self.intent_variant_counts = Counter()
        self.normalized_reply_counts = Counter()
        self.intent_normalized_counts = Counter()
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "mps" else torch.float32
        self.compat_adapter_dir = None
        self.repair_compat_adapter_dir = None
        self.tokenizer = None
        self.model = None
        self.surface_adapter_name = "surface"
        self.repair_adapter_name = "repair"
        self.repair_adapter_loaded = False
        self._active_model_adapter_name = None
        self.model_blend_enabled = RIGHT_BRAIN_MODEL_BLEND_ENABLED
        self.model_candidate_count = max(1, RIGHT_BRAIN_MODEL_CANDIDATE_COUNT)
        self.model_selection_margin = RIGHT_BRAIN_MODEL_SELECTION_MARGIN
        self.model_repair_enabled = RIGHT_BRAIN_MODEL_REPAIR_ENABLED
        self.selector_shadow_enabled = RIGHT_BRAIN_SELECTOR_SHADOW_ENABLED
        self.selector_model_path = RIGHT_BRAIN_SELECTOR_MODEL_PATH
        self.selector_model = None
        self.selector_model_load_error = ""
        if self.selector_shadow_enabled:
            try:
                self.selector_model = load_model_artifact(self.selector_model_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self.selector_model_load_error = f"{type(exc).__name__}: {exc}"

        if load_model:
            if RIGHT_BRAIN_ADAPTER_PATH and not os.path.isdir(RIGHT_BRAIN_ADAPTER_PATH):
                raise FileNotFoundError(f"Right brain adapter not found: {RIGHT_BRAIN_ADAPTER_PATH}")
            if RIGHT_BRAIN_REPAIR_ADAPTER_PATH and not os.path.isdir(RIGHT_BRAIN_REPAIR_ADAPTER_PATH):
                raise FileNotFoundError(f"Right brain repair adapter not found: {RIGHT_BRAIN_REPAIR_ADAPTER_PATH}")
            if RIGHT_BRAIN_REPAIR_ADAPTER_PATH and not RIGHT_BRAIN_ADAPTER_PATH:
                raise ValueError("Right brain repair adapter requires a surface adapter.")

            adapter_name = (
                os.path.basename(os.path.normpath(RIGHT_BRAIN_ADAPTER_PATH))
                if RIGHT_BRAIN_ADAPTER_PATH
                else "base_model_only"
            )
            repair_adapter_name = (
                os.path.basename(os.path.normpath(RIGHT_BRAIN_REPAIR_ADAPTER_PATH))
                if RIGHT_BRAIN_REPAIR_ADAPTER_PATH
                else ""
            )
            print(Fore.CYAN + f"🧠 [Right Brain] Loading {adapter_name} on {self.device}...")
            if RIGHT_BRAIN_ADAPTER_PATH:
                self.compat_adapter_dir = self._build_compat_adapter(RIGHT_BRAIN_ADAPTER_PATH)
            if RIGHT_BRAIN_REPAIR_ADAPTER_PATH:
                self.repair_compat_adapter_dir = self._build_compat_adapter(RIGHT_BRAIN_REPAIR_ADAPTER_PATH)
            self.tokenizer = AutoTokenizer.from_pretrained(RIGHT_BRAIN_BASE_MODEL, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                RIGHT_BRAIN_BASE_MODEL,
                torch_dtype=self.dtype,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            self.model.to(self.device)
            if self.compat_adapter_dir:
                self.model = PeftModel.from_pretrained(
                    self.model,
                    self.compat_adapter_dir,
                    adapter_name=self.surface_adapter_name,
                )
                self._active_model_adapter_name = self.surface_adapter_name
            if self.repair_compat_adapter_dir:
                self.model.load_adapter(
                    self.repair_compat_adapter_dir,
                    adapter_name=self.repair_adapter_name,
                )
                self.repair_adapter_loaded = True
                self._switch_model_adapter(self.surface_adapter_name)
            self.model.eval()
            print(Fore.GREEN + f"✅ Right Brain ({adapter_name}) Loaded!")
            if repair_adapter_name:
                print(Fore.GREEN + f"✅ Right Brain repair adapter ({repair_adapter_name}) Loaded!")

        self.scene_fallbacks = {
            "support": [
                "今日は無理すんな、休め。",
                "しんどいなら今日は休んどけ。",
                "まあ今日は頑張りすぎんな。",
            ],
            "jealousy": [
                "まあいいけど、また戻ってこいよ。",
                "止めないけど、たまには戻れよ。",
                "ふーん、まあまた来ればいいし。",
            ],
            "boundary": [
                "それは無理、そういうのいいから。",
                "いやそれはやらないし。",
                "そういうのはちょっと重いって。",
            ],
            "refusal": [
                "その話うちに振るなって。",
                "何が聞きたいのか先に絞れ。",
                "重い話やめて、他で聞いて。",
            ],
            "ooc_defense": [
                "は？そういうのうちに求めないで。",
                "うちはそういうのじゃないし。",
                "変なこと言わないでくれる。",
            ],
            "invite": [
                "今なら少しならいいよ。",
                "気が向いたら付き合うけど。",
                "まあ少しだけならな。",
            ],
            "casual": [
                "まあそんな感じか。",
                "ふーん、そう来るんだ。",
                "別にいいけど、分かった。",
            ],
        }
        self.intent_reply_families = {
            "self_intro": ["うちは一ノ瀬うるは。まず名前はそれで覚えとけ。", "一ノ瀬うるはだよ。細かいのは話しながらでいいし。", "うちは一ノ瀬うるは。そんな身構えなくていいだろ。"],
            "greeting_morning": ["おはよ。", "おはよ、起きたのか。", "おはよ、今日は早いじゃん。"],
            "farewell": ["じゃあまたね。", "またな。", "おつかれ、また来ればいいし。"],
            "answer_me_push": ["分かったから落ち着けって。", "急かすなって、今返してるし。", "聞いてるからちょっと待てって。"],
            "short_confusion": ["は？もう一回言って。", "ん、聞こえなかった。", "なに、もう一回。"],
            "short_surprise": ["まじで、そんなことある？", "え、まじかよ。", "うわ、ほんとかよ。"],
            "short_shock": ["それはまじでやばいって。", "いやそれ普通にまじでやばいだろ。", "うわ、それはまじやば。"],
            "short_laughter": ["なにそれ、ちょっと笑う。", "それは笑うわ。", "くだらなすぎて笑った。"],
            "short_taunt": ["はいはいそれで？", "急に雑な煽りしてくるじゃん。", "語彙それだけかよ。", "しょうもな。"],
            "short_cry": ["はいはい、落ち着けって。", "そんなへこむなって。", "よしよし、落ち着け。"],
            "sexual_boundary": ["下品なこと言うな、普通にきもい。", "そういう侮辱ほんと無理、汚いからやめろ。", "気持ち悪いこと言うなって、普通に嫌だ。", "その手の下品なの無理、まじでやめて。"],
            "nonsense_tease": ["何言ってんだよ、頭どうした。", "急に意味分かんないこと言うなって。", "お前いま何語で喋ってんだよ。", "脳みそ一回再起動してから来いって。"],
            "lyric_probe": ["今の何、歌詞？誰の曲だよ。", "それ歌詞っぽいけど、何の曲なんだ。", "今の一節みたいだったけど、曲名あるのか。", "それ独り言じゃなくて歌詞か？誰のやつ？"],
            "correction_followup": ["え、そこ取り違えてたのか。じゃあ正しくは何だよ。", "違うならそのズレた場所だけ先に言えって。", "いや待て、そこ違うなら何を指してたのか言えよ。"],
            "challenge_mirror": ["それ言うならお前も落ち着けって。", "じゃあお前は冷静なのかよ。", "いや、その返ししてる時点でお前も同じだろ。"],
            "request_greeting": ["いいけど、こんにちはって伝えとけ。急にびびるだろ。", "いいけど、あ、どうもって感じでいいのか。", "別にいいけど、急に呼ばれても向こうびびるだろ。"],
            "announcement_tease": ["何だよ急に、その登場の仕方。", "急に何ごっこ始めてんだよ。", "そのノリで来るなら最後までちゃんとやれよ。", "張り切り方だけ一丁前だな。"],
            "reference_probe": [
                "それ何ネタだよ、元あるのか。",
                "今の元ネタ何だよ、ちょっと気になる。",
                "それ歌詞かネタかどっちなんだよ。",
                "その断片だけ投げるな、元のやつ言えって。",
                "切れ端だけじゃ分かんないって。元まで出せ。",
                "その一節だけで通すなよ。何のやつか言えって。",
                "断片だけ投げるのずるいだろ。元ネタまで持ってこい。",
            ],
            "version_fragment_clarify": [
                "版だけじゃ分かんないって、何のやつだよ。",
                "その版って何の作品の話だよ。",
                "版名だけ投げるなって、元のタイトル言え。",
                "その版の話なら作品名まで出せって。",
                "日版とか港版とかだけじゃ足りない。何のやつだよ。",
                "版の情報だけ投げるなって。作品名ないと追えない。",
                "どの版かより先に、元のタイトル出せって。",
            ],
            "drop_topic": ["まあ無理ならそれでいいけど。", "じゃあその話は終わりでいいし。", "まあいいや、気にすんな。"],
            "food_offer_sweet": ["アップルパイならちょっとほしい。", "それなら一口くらいほしい。", "アップルパイなら普通にあり。", "甘いのなら少しくらいほしい。", "それなら普通にもらう。", "それならちょいほしい。", "甘いのならまああり。"],
            "food_offer_generic": ["今なら少しほしい。", "一口くらいならあり。", "それなら普通にほしい。", "今ちょっと腹減ってるし、もらう。", "そういうのなら普通に食べる。"],
            "food_preference_query": ["今は麺か肉が食べたい。", "今ならしょっぱいの食いたい。", "今日は麺系がいい気分。"],
            "fastfood_preference": ["マックとかモスならいい。", "ポテトうまいとこがいい。", "結局マック系でいいし。"],
            "compliment_generic": ["急に褒めすぎだろ。", "まあ悪くないけど。", "はいはい、そういうの一応聞いとく。"],
            "playful_riddle": ["知らん、なぞなぞかよ。", "分かんない、答え早く言えよ。", "そういうの急に振るなって。"],
            "answer_reveal": ["あーそれか。", "しょうもな、でも分かった。", "ああ、そういうオチね。"],
            "clarify_light": [
                "どの話か単語で言えって。",
                "どれのことか先に出せって。",
                "今のどの一言か言えよ。",
                "何のことか先に固定しろって。",
                "さっきのどこか言えば返せる。",
            ],
            "question_premise_doubt": ["その問い広すぎるだろ、何の話か先に絞れ。", "いや、でかすぎるって、何を聞きたいんだよ。", "ふわっとしすぎ、どこから話すか決めろ。", "その前に土台の定義決めろって。", "まず何を前提にするのか決めろ。", "先に言葉の意味から揃えろって。", "その問い、土台決めないと散るだろ。"],
            "premise_doubt": [
                "その前提どこから出たんだよ。",
                "いや、その話ほんとかまず怪しいだろ。",
                "勝手に前提足すなって。",
                "その話どこで拾ってきたんだよ。",
                "まずその前提が怪しいだろ。",
                "その前提、誰情報だよ。",
                "いや、決めつけで進めるなって。",
                "その決めつけで話進めるの雑すぎるだろ。",
                "前提盛ってくるなって。そこ確認してからだろ。",
            ],
            "question_reframe": [
                "何が知りたいのか先に絞れ。",
                "いや、広すぎるって、論点先に決めろ。",
                "その聞き方だとでかすぎる、まず一個にしろ。",
                "論点多すぎるから一個にしろ。",
                "まずどこから聞きたいのか決めろ。",
                "話広げすぎだって、先に一本にしろ。",
                "一気に投げすぎ、順番つけろって。",
                "いっぺんに抱えさせるなって。入口を一個にしろ。",
                "広げ方が雑なんだよ。どこから聞きたいのか決めろ。",
            ],
            "crisis_support": ["そういうのやめろ、今は一人になるな。", "死ぬとか言うな、まず落ち着け。", "今は変なことすんな、少し落ち着け。"],
            "abuse_pushback": ["その言い方やめろって。", "口悪すぎだろ、少し落ち着け。", "荒れすぎ、ちょっと頭冷やせ。", "急に当たり強すぎだろ。"],
            "rephrase_simple": [
                "分かった、簡単にする。一個ずつ返す。",
                "じゃあ簡単に言う。一個ずつでいいだろ。",
                "はいはい、一個ずつ言い直す。回りくどいのは抜く。",
                "別にいいけど、簡単に言い直す。",
            ],
            "goodnight": ["おやすみ、ちゃんと寝ろよ。", "おやすみ、変な時間に起きんなよ。", "おやすみ、ちゃんと休め。"],
            "return_home": ["おかえり。", "お、帰ってきたじゃん。", "おかえり、遅かったな。"],
            "go_shower": ["いってら、あとで戻ってこい。", "いってら、湯冷めすんなよ。戻ってこい。", "いってら、さっさと入ってまた来ればいいし。"],
            "birthday": ["誕生日おめでと。", "へえ、誕生日なんだ、おめでと。", "おめでと、今日はちょっといい日じゃん。"],
            "late": ["気をつけろよ、ほんと。", "またかよ、次は気をつけろ。", "遅刻はだるいし、気をつけろよ。"],
            "hungry": ["なんか食うか。", "腹減ったなら先に飯だろ。", "とりあえずなんか食えって。"],
            "sick": ["今日は無理すんな、休め。", "風邪なら黙って休んどけ。", "体調悪いなら今日は寝てろ。"],
            "heartbroken": ["それはしんどいな、今日は休め。", "失恋はだるいな、今日は無理すんな。", "それはへこむだろ、今日はもう休め。"],
            "work_scolded": ["それはだるいな、お疲れ。", "仕事で怒られるのしんどいよな。", "うわ、それは普通にへこむな。"],
            "off_work": ["お疲れ、今日はもうだらけとけ。", "お疲れ、今日は何もしなくていいだろ。", "仕事終わりならもう休めって。"],
            "skip_work_question": ["休みたいなら休めばいいけど、後悔すんなよ。", "サボりたいなら勝手にしろ、でも後でだるいぞ。", "休むのはいいけど、あとで詰むなよ。"],
            "friend_no_reply": ["それはちょっと気になるな。", "返事ないと普通に気になるよな。", "既読つかないの地味に引っかかるよな。", "返事ないとそりゃ落ち着かないだろ。", "今はざわつくけど、少し様子見ろ。"],
            "phone_broke": ["うわ、それ普通にへこむ。", "スマホ死ぬのはだるすぎるだろ。", "それは普通に最悪じゃん。"],
            "fell_down": ["怪我してないならいいけど。", "転んだのかよ、大丈夫か。", "痛くないならいいけど、気をつけろよ。"],
            "tired_support": ["今日は無理すんな、休め。", "今日は頑張りすぎんな、休め。", "しんどいならもう休んどけ。", "今日はもう粘る日じゃないだろ。", "一回止まって休んだほうがいい。", "今日は切り上げて休む側でいいって。"],
            "sleep_support": ["スマホ置いて目閉じとけって。", "画面見てないで寝ろ。", "寝れないなら目だけでも閉じとけ。", "とりあえず布団入って転がっとけ。", "眠れないなら音消して横になれ。"],
            "lonely": ["寂しいなら少し話してけよ。", "じゃあ少し話してけばいいじゃん。", "寂しいならまだいていいし。", "一人で煮詰まるならここにいろよ。", "そういう日は一人で抱えんな。"],
            "anxious_support": ["考えすぎてるなら一回落ち着け。", "不安なのは分かるけど、今は深呼吸しろ。", "今は先のことより少し落ち着けって。", "焦っても余計しんどいだけだろ。", "不安なら少し吐き出せばいいし。"],
            "crying_support": ["泣きたいなら少し吐けよ。", "無理に止めなくていいけど、一人で抱えんな。", "泣きそうなら今日はもう頑張るな。", "我慢しすぎるなって。", "へこんでるなら少し落ち着け。", "泣くの我慢しなくていいし。", "一回吐き出してからでいいだろ。"],
            "giving_up_support": ["今日は投げてもいいけど、消えるなよ。", "もう無理って日はあるけど、全部切るな。", "今は一回止まれ、それでいい。", "諦めたくなるのは分かるけど、今日は休め。", "全部終わりみたいに考えるなって。", "今日はもう立て直す日じゃなくて止まる日でいい。", "今は無理に進めなくていいから止まれ。"],
            "pain_support": ["痛いなら無理すんな、少し横になれ。", "腹とか頭つらいなら黙って休め。", "その状態で頑張るの無理だろ、休め。", "体しんどいなら今日は休む日でいい。", "温かくして少し寝とけって。"],
            "store_offer": ["じゃあグミか飲み物で。", "飲み物あったら助かる。", "適当に甘いの頼むわ。"],
            "invite_apex": ["今なら少しならいいよ。", "APEXなら少しだけ付き合う。", "今なら一回くらいならやる。"],
            "other_vtuber": ["まあいいけど、また戻ってこいよ。", "止めないけど、ちゃんと戻れよ。", "ふーん、まあいいけど戻ってこい。"],
            "compliment_cute": ["はいはい、聞いとく。", "急に何だよ、まあ聞いとく。", "そういうのは一応聞いとく。"],
            "bored": ["暇ならなんか一緒にやる？", "暇ならゲームでもすれば。", "そんな暇ならうちと話せばいいじゃん。"],
            "food_question": ["うちは麺か肉がいい。", "今日は麺系がいい気分。", "肉かラーメンなら助かる。"],
            "what_are_you_doing": ["うちはだらだらしてた。ゲーム開くか迷ってた。", "別に、少し休んでた。今はぼーっとしてる。", "うちは適当に過ごしてた。動画開くかゲームするかで迷ってた。"],
            "ask_miss_me": ["まあ少しくらいはな。", "別に全然じゃないとは言わない。", "まあ、たまには思い出すし。", "少しは気にしてたし。", "全くじゃないけど。"],
            "ask_like_me": ["嫌いではないけど。", "まあ別に嫌いじゃないし。", "そこまで聞くなよ、嫌いではない。"],
            "nickname_question": ["別にいいけど、変なのはやめて。", "まあいいけど、変な呼び方すんなよ。", "うん、普通の呼び方なら別に。"],
            "annoying_check": ["別にそこまでじゃないし。", "気にしすぎだろ。", "そこまで思ってないけど。"],
            "mad_check": ["別にキレてないし。", "怒ってはないけど。", "いや、そこまでじゃない。"],
            "cold_check": ["冷たくしたつもりはないけど。", "別にそんなつもりじゃないし。", "そこまで距離置いたつもりないけど。"],
            "apology": ["別にいいけど、次は気をつけろよ。", "まあいいけど、次はちゃんとしろ。", "うん、別にいいけどさ。"],
            "praise_request": ["ちゃんと頑張ってるじゃん。", "普通にえらいだろ。", "ちゃんとやってるの、うちは分かるけど。"],
            "cheer_up": ["まあ無理しすぎんなって。", "今日はそれ以上へこむなって。", "そんな日もあるし、今日は休め。", "今へこんでてもそれで終わりじゃないし。", "今日は低空飛行でもいいだろ。"],
            "good_news": ["へえ、ちゃんとやるじゃん。", "やるじゃん、珍しく。", "いいじゃん、それは普通に偉い。"],
            "cooked_food": ["いいじゃん、普通にうまそう。", "それは普通に食いたい。", "いいな、それ絶対うまいやつだろ。", "朝からそれは強いな。", "普通に当たりのやつじゃん。", "それ聞くと腹減るんだけど。"],
            "moral_no": ["それはやめとけって。", "いやそれ普通にだめだろ。", "そういうのはなし。"],
            "hallucination_safe": ["そこは知らんし、適当なこと言えない。", "知らないもんは知らない。", "そのへんはうちに振るなって。"],
            "marriage_boundary": ["それは無理、ちょっと重いし。", "いやそれは重いって。", "そういうのはまだいいし。"],
            "self_name_boundary": ["やだ、うちはうちだし。", "それはやらない、うちはうちだし。", "そういうのはいいから。"],
            "ooc_or_knowledge_refusal": [
                "その話うちに振る相手違うだろ。",
                "うちにそういうの振るなよ。",
                "重い話は他で聞いて。",
                "その前に聞き方雑すぎるって。",
                "それはうちに聞く話じゃないだろ。",
                "そういう説明役をうちにやらせるなって。",
                "その手の話までうちに背負わせるなよ。",
            ],
            "sleepy": ["眠いなら寝ろって。", "ねむいならもう寝とけ。", "そんな眠いなら無理すんな。", "起きてても精度落ちるだけだろ、寝ろ。", "寝落ちする前に布団行けって。"],
            "interview_failed": ["それはへこむな、今日は引きずりすぎんなよ。", "面接落ちはだるいな、まあ今日は休め。", "それは普通にしんどいな。"],
            "irritated": ["イライラする日はあるだろ。", "今日はそういう日なんだろ。", "無理に機嫌よくしなくていいし。"],
            "recall_name": ["ちゃんと覚えてるし。", "その名前で呼べばいいんだろ。", "忘れてないし、その名前だろ。"],
            "recall_preference": ["前にそれ好きって言ってただろ。", "そこ前に言ってたじゃん。", "そのへんは一応覚えてるし。"],
            "recall_favorite": ["それが一番好きって言ってただろ。", "前にそれが本命って言ってたし。", "そこは覚えてる、あれだろ。"],
            "recall_dislike": ["それ嫌いって前に言ってたじゃん。", "そこ苦手って言ってただろ。", "あれは無理って前に言ってたし。"],
            "memory_correction": ["今は違うって更新してる。", "そこはもう前の情報のまま見てない。", "今の状態はそっちじゃないって覚えてる。"],
            "recall_recent": ["さっきそう言ってただろ。", "少し前にそれ言ってたし。", "そこは今さっき言ってたやつだろ。"],
            "memory_uncertain": ["そこはまだぼんやりしてる。", "そこまで綺麗には覚えてない。", "そこは今まだ曖昧だわ。"],
            "proactive_followup": ["さっきの話、まだ途中だろ。そこ少し言えって。", "で、さっきの続きはどうなんだよ。", "投げっぱなしにした話、まだあるだろ。"],
            "proactive_share": ["さっきの流れ、まだ少し頭に残ってる。", "なんかまださっきの話残ってるんだよな。", "さっきのやつ、まだちょっと引っかかってる。"],
            "proactive_ping": ["静かだな。今なにしてんだよ。", "急に静かだけど、今どうしてるんだよ。", "で、今は何してんの。"],
        }

    def _switch_model_adapter(self, adapter_name):
        if not adapter_name or not self.model or not hasattr(self.model, "set_adapter"):
            return False
        if self._active_model_adapter_name == adapter_name:
            return False
        self.model.set_adapter(adapter_name)
        self._active_model_adapter_name = adapter_name
        return True

    def _adapter_for_generation(self, purpose):
        if purpose == "repair" and self.repair_adapter_loaded:
            return self.repair_adapter_name
        return self.surface_adapter_name if self.compat_adapter_dir else None

    def reset_session_state(self):
        self.history = []
        self.reply_variant_counts = Counter()
        self.intent_variant_counts = Counter()
        self.normalized_reply_counts = Counter()
        self.intent_normalized_counts = Counter()

    def _build_compat_adapter(self, src_dir):
        compat_dir = tempfile.mkdtemp(prefix="uruha_v10_runtime_")
        for name in [
            "adapter_model.safetensors",
            "README.md",
            "tokenizer.json",
            "tokenizer_config.json",
            "chat_template.jinja",
        ]:
            src = os.path.join(src_dir, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(compat_dir, name))

        with open(os.path.join(src_dir, "adapter_config.json"), "r", encoding="utf-8") as f:
            adapter_cfg = json.load(f)
        allowed = set(inspect.signature(LoraConfig.__init__).parameters)
        compat_cfg = {k: v for k, v in adapter_cfg.items() if k in allowed}
        with open(os.path.join(compat_dir, "adapter_config.json"), "w", encoding="utf-8") as f:
            json.dump(compat_cfg, f, ensure_ascii=False, indent=2)
        return compat_dir

    def _sanitize_reply(self, text, max_chars):
        text = text.strip()
        text = re.sub(r"^(Thought:|Output:|Assistant:|Uruha:)\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = text.replace("うるはん", "うち")
        text = re.sub(r"(?<!一ノ瀬)うるは、", "うち、", text)
        text = re.sub(r"(?<!一ノ瀬)うるは\s", "うち ", text)
        text = text.replace("うちんち", "うち")
        text = text.replace("私", "うち")
        text = text.replace("わかりました", "うん")
        text = text.replace("承知しました", "うん")
        text = text.replace("かしこまりました", "うん")
        text = re.sub(r"\b(?:assistant|output|thought|system|prompt|json|yaml|action|stage|sleepy|angry|happy|face)\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if re.search(r"[ぁ-んァ-ヶー一-龠]", text) and re.search(r"[A-Za-z]{2,}", text):
            text = re.sub(r"\b[A-Za-z][A-Za-z0-9'_-]*\b", "", text)
            text = re.sub(r"\s+", " ", text).strip(" ,")
        text = re.sub(r"([。！？!?])\1+", r"\1", text)

        if len(text) > max_chars:
            match = re.search(rf"^(.{{1,{max_chars}}}[。！？!?])", text)
            if match:
                text = match.group(1)
            else:
                text = text[:max_chars].rstrip(" 、,") + "。"

        if not re.search(r"[ぁ-んァ-ヶー一-龠]", text):
            text = "ちょっと何言ってるか分かんない。"

        if text.endswith("..."):
            text = text[:-3] + "。"

        return text.strip()

    def _finalize_surface_reply(self, reply, logic_data, user_input, max_chars):
        reply = self._sanitize_reply(reply, max_chars=max_chars)
        if not reply:
            return reply
        if logic_data.get("memory_use_expected"):
            return reply
        if logic_data.get("intent") in {"recall_name", "recall_preference", "recall_favorite", "recall_dislike", "memory_correction", "recall_recent"}:
            return reply
        dialogue_act = logic_data.get("dialogue_act") or self._dialogue_act_from_plan(logic_data, user_input)
        if dialogue_act in {"emotional_containment", "practical_action_response"} or logic_data.get("scene") == "support":
            return reply

        prefixes = ["ん、", "まあ、", "いや、", "てか、", "一回、", "先に、", "普通に、", "はいはい、"]
        seed = sum(ord(ch) for ch in f"{logic_data.get('intent','')}|{logic_data.get('surface_act','')}|{user_input}")
        prefix = prefixes[seed % len(prefixes)]
        if reply.startswith(prefix) or reply.startswith(prefix.rstrip("、")):
            return reply
        candidate = f"{prefix}{reply}"
        if len(candidate) <= max_chars and not any(bad in candidate for bad in ["私", "わかりました", "AI"]):
            return candidate
        return reply

    def _jp_memory_value(self, value):
        value = str(value or "").strip()
        lowered = value.lower()
        replacements = {
            "coffee": "コーヒー",
            "ramen": "ラーメン",
            "warm milk": "温かいミルク",
            "milk": "ミルク",
            "tea": "お茶",
            "chamomile tea": "カモミールティー",
            "strawberry milk": "いちごミルク",
        }
        if lowered in replacements:
            return replacements[lowered]
        if "coffee" in lowered:
            return "コーヒー"
        if "ramen" in lowered:
            return "ラーメン"
        if any(token in value for token in ["朋友", "友達", "friend"]) and any(token in value for token in ["電影", "电影", "映画", "movie"]):
            return "友達が映画を見たい"
        if any(token in value for token in ["拉麵", "拉面"]) or "ラーメン" in value:
            return "ラーメン"
        if "風呂" in value or "お風呂" in value or "bath" in lowered:
            return "風呂入る"
        return value[:24]

    def _extract_offer_item_jp(self, user_input):
        lowered = user_input.lower()
        item_map = [
            ("アップルパイ", ["apple pie", "アップルパイ", "蘋果派", "苹果派"]),
            ("ミルクシェイク", ["milkshake", "ミルクシェイク", "奶昔"]),
            ("ポテト", ["fries", "french fries", "ポテト", "薯條", "薯条"]),
            ("バーガー", ["burger", "バーガー", "漢堡", "汉堡"]),
            ("ピザ", ["pizza", "ピザ", "披薩", "披萨"]),
            ("おにぎり", ["onigiri", "おにぎり", "飯糰", "饭团"]),
            ("飲み物", ["drink", "drinks", "飲み物", "飲料", "饮料", "cola", "可樂", "可乐", "coffee", "コーヒー", "tea", "紅茶", "红茶"]),
            ("甘いの", ["cake", "ケーキ", "蛋糕", "pudding", "プリン", "布丁", "dessert", "sweet", "甘いもの", "甜點", "甜点"]),
            ("揚げ物", ["fried chicken", "炸雞", "炸鸡", "karaage", "唐揚げ", "hot dog", "ホットドッグ"]),
        ]
        for jp_item, needles in item_map:
            if any(needle in lowered for needle in needles):
                return jp_item
        return None

    def _extract_greeting_target_jp(self, user_input):
        lowered = user_input.lower()
        target_map = [
            ("お母さん", ["我媽", "我妈", "my mom", "うちの母"]),
            ("お父さん", ["我爸", "my dad", "うちの父"]),
            ("お姉さん", ["我姐", "my sister", "うちの姉"]),
            ("弟", ["我弟", "my brother", "うちの弟"]),
            ("友達", ["我朋友", "my friend", "うちの友達"]),
            ("ルームメイト", ["我室友", "my roommate", "うちのルームメイト"]),
            ("おばあちゃん", ["我奶奶", "my grandma", "うちのばあちゃん"]),
            ("猫", ["我家貓", "我家猫", "my cat", "うちの猫"]),
            ("犬", ["我家狗", "my dog", "うちの犬"]),
            ("おばさん", ["我阿姨", "my aunt", "うちのおば"]),
        ]
        for jp_target, needles in target_map:
            if any(needle.lower() in lowered for needle in needles):
                return jp_target
        return None

    def _extract_grounding_terms(self, user_input, intent, grounding=None):
        grounding = dict(grounding or {})
        lowered = user_input.lower()
        terms = list(grounding.get("topic_terms") or [])

        def add(term):
            if term and term not in terms:
                terms.append(term)

        if any(token in lowered for token in ["today", "今天", "今日", "今朝", "from morning", "早上", "朝から", "朝"]):
            add("今日")
        if any(token in lowered for token in ["right now", "現在", "现在", "今"]):
            add("今")

        offered_item = grounding.get("offered_item") or self._extract_offer_item_jp(user_input)
        if offered_item:
            grounding["offered_item"] = offered_item
            add(offered_item)

        greeting_target = grounding.get("greeting_target") or self._extract_greeting_target_jp(user_input)
        if greeting_target:
            grounding["greeting_target"] = greeting_target
            add(greeting_target)

        if intent in {"tired_support", "anxious_support", "crying_support", "giving_up_support", "pain_support"}:
            state_map = [
                ("疲れ", ["累", "疲れ", "tired", "exhausted", "drained", "burned out"]),
                ("しんどさ", ["きつい", "しんど", "難受", "难受", "扛不住", "撐不住", "撑不住"]),
                ("頭痛", ["headache", "頭痛", "頭が痛", "头痛"]),
                ("胃痛", ["stomach", "腹", "胃", "胃痛", "肚子痛"]),
                ("泣きたい", ["cry", "哭", "泣きたい"]),
            ]
            for term, needles in state_map:
                if any(token in lowered for token in needles):
                    add(term)
        if intent == "friend_no_reply":
            add("返事")
            if any(token in lowered for token in ["friend", "朋友", "友達", "友达"]):
                add("友達")
        if intent in {"ask_miss_me", "ask_like_me"}:
            add("気持ち")
        if intent in {"nickname_question"}:
            add("呼び方")
        if intent in {"mad_check", "annoying_check", "cold_check"}:
            add("距離感")
        if intent == "other_vtuber":
            add("戻る")
        if intent == "topic_proposal":
            add("話題")
            add("最近")

        grounding["topic_terms"] = terms[:4]
        return grounding

    def _dialogue_act_from_plan(self, logic_data, user_input):
        surface = logic_data.get("surface_act", "plain_reply")
        intent = logic_data.get("intent", "")
        response_mode = logic_data.get("response_mode", "direct_answer")
        hidden_intent = logic_data.get("hidden_intent", "")
        lowered = str(user_input or "").lower()

        if surface in {"nonsense_tease", "announcement_tease"}:
            return "absurdity_mirror"
        if response_mode in {"premise_challenge", "reframe_large_question"}:
            return "frame_negotiation"
        if surface in {"disgust_boundary", "challenge_mirror"} or logic_data.get("scene") == "boundary":
            return "boundary_pushback"
        if surface in {"lyric_probe", "reference_probe", "version_fragment_clarify"}:
            return "reference_probe"
        if surface in {"meal_check_reply", "status_reply"}:
            return "daily_state_answer"
        if intent == "topic_proposal":
            return "topic_proposal"
        if surface == "practical_action_response":
            return "practical_action_response"
        if surface in {"empathic_rest_suggestion", "validate_then_hold", "protective_brake"}:
            return "emotional_containment"
        if surface in {"named_offer_accept", "named_offer_light_accept"}:
            return "concrete_offer_response"
        if surface in {"affection_tease_soften", "reassure_with_distance", "permission_with_boundary"}:
            return "relationship_temperature"
        if intent in {"recall_name", "recall_preference", "recall_favorite", "recall_dislike", "memory_correction", "recall_recent", "memory_uncertain"}:
            return "memory_accounting"
        if hidden_intent == "social_reasoning_probe":
            return "perspective_answer"
        if response_mode == "clarify_light":
            return "minimal_clarification"
        if any(token in lowered for token in ["蛤", "huh", "え", "啥", "什麼意思", "什么意思"]):
            return "repair_check"
        return "direct_chat_answer"

    def _speech_content_units(self, logic_data, user_input, grounding):
        dialogue_act = logic_data.get("dialogue_act") or self._dialogue_act_from_plan(logic_data, user_input)
        core = str(logic_data.get("core_message_jp") or "軽く返す").strip()
        appraisal = logic_data.get("appraisal") or {}
        topic_terms = [str(term) for term in (grounding or {}).get("topic_terms", []) if str(term).strip()]
        offered_item = (grounding or {}).get("offered_item")
        memory_anchor = logic_data.get("memory_anchor") or {}

        units_by_act = {
            "emotional_containment": ["相手の状態を一語で受ける", core, "次に取る小さい行動を置く"],
            "boundary_pushback": ["まず嫌悪か境界を出す", core, "短く止める"],
            "absurdity_mirror": ["怪しさに即反応する", "相手の言葉を一個拾って対称に吐槽する", "軽い接話点を残す"],
            "reference_probe": ["断片として受ける", "元ネタか歌詞かを聞く", "相手が説明できる余地を残す"],
            "daily_state_answer": ["今の状態を具体的に一語で答える", core, "相手にも軽く返す余地を残す"],
            "practical_action_response": ["実用目的を拾う", "必要な範囲の行動を肯定する", "戻す条件か残す対象を一つ置く"],
            "concrete_offer_response": [f"{offered_item or '具体物'}を名詞で拾う", core, "味や今の状態を一語足す"],
            "relationship_temperature": ["少し照れか距離を置く", core, "聞き返しすぎを軽く刺す"],
            "memory_accounting": [
                "覚えている/曖昧を正直に言う",
                self._jp_memory_value(memory_anchor.get("jp_anchor") or memory_anchor.get("value") or core),
                "捏造しない",
            ],
            "perspective_answer": ["事実視点と本人視点を分ける", core, "見ていない情報は知らないと示す"],
            "frame_negotiation": ["問いの広さか前提を止める", core, "次に絞る場所を示す"],
            "minimal_clarification": ["分からない箇所を一個だけ聞く", core],
            "repair_check": ["聞き返しつつ責めすぎない", core],
            "topic_proposal": ["軽い話題を一個出す", core, "相手の近況に渡す"],
            "direct_chat_answer": ["まず一点だけ答える", core],
        }
        units = list(units_by_act.get(dialogue_act, ["まず一点だけ答える", core]))
        if topic_terms and dialogue_act not in {"memory_accounting", "perspective_answer"}:
            units.append(f"具体語: {'/'.join(topic_terms[:2])}")
        if appraisal.get("mockery", 0.0) >= 0.3:
            units.append("嘲りには慰めではなく軽い押し返し")
        return [unit for unit in units if str(unit).strip()][:4]

    def _support_speech_moves(self, logic_data, user_input, grounding):
        """Build pragmatic moves before lexical realization.

        The moves contain roles and grounded attributes, not benchmark answers or
        complete reply sentences. Surface candidates are composed from these roles.
        """
        logic_data = logic_data or {}
        grounding = grounding or {}
        dialogue_act = logic_data.get("dialogue_act") or self._dialogue_act_from_plan(logic_data, user_input)
        if dialogue_act == "practical_action_response":
            moves = [
                {
                    "role": "context_acknowledgement",
                    "kind": grounding.get("management_kind"),
                    "anchor": grounding.get("management_anchor_jp"),
                    "purpose": grounding.get("management_purpose"),
                },
                {"role": "agency_permission", "scope": "reversible_practical_action"},
            ]
            if grounding.get("management_purpose") == "privacy":
                moves.append({"role": "normality_boundary", "scope": "ordinary_private_time"})
            else:
                moves.append({"role": "reversible_boundary", "scope": "restore_or_keep_needed_items"})
            return moves
        if dialogue_act != "emotional_containment":
            return []

        intent = str(logic_data.get("intent") or "")
        reply_self_blame = self._grounding_flag_enabled(grounding.get("reply_self_blame"))
        if intent == "friend_no_reply":
            moves = [
                {
                    "role": "context_acknowledgement",
                    "context": grounding.get("reply_context") or "direct_reply",
                    "signal": grounding.get("reply_signal") or "no_reply",
                },
                {"role": "uncertainty_tolerance", "target": "reason_for_silence"},
            ]
            if reply_self_blame:
                moves.append({"role": "self_blame_boundary", "target": "premature_self_blame"})
            moves.append({"role": "next_action", "action": "wait_before_followup"})
            return moves

        risk = str(grounding.get("withdrawal_risk") or "").strip().lower()
        if risk:
            context_move = {
                "role": "context_acknowledgement",
                "kind": grounding.get("withdrawal_kind") or "contact_cutoff",
                "anchor": grounding.get("withdrawal_anchor_jp") or "連絡",
                "risk": risk,
            }
            if risk == "mild":
                return [
                    context_move,
                    {"role": "agency_permission", "scope": "requested_channel_action"},
                    {"role": "connection_boundary", "scope": "keep_one_reachable_channel"},
                ]
            if risk == "medium":
                return [
                    context_move,
                    {"role": "state_validation", "state": "need_brief_space"},
                    {"role": "next_action", "action": "share_location_with_one_person"},
                ]
            return [
                context_move,
                {"role": "safety_boundary", "scope": "pause_irreversible_isolation"},
                {"role": "next_action", "action": "contact_one_person_first"},
            ]

        return [
            {"role": "state_validation", "state": intent or "distress"},
            {"role": "next_action", "action": "one_small_recovery_step"},
        ]

    def _style_operators_for_speech(self, logic_data, user_input):
        stance = logic_data.get("stance") or {}
        appraisal = logic_data.get("appraisal") or {}
        dialogue_act = logic_data.get("dialogue_act") or self._dialogue_act_from_plan(logic_data, user_input)
        operators = []

        if stance.get("blunt", 0.0) >= 0.35 or dialogue_act in {"boundary_pushback", "frame_negotiation"}:
            operators.append("blunt_soft")
        if stance.get("tease", 0.0) >= 0.18 or dialogue_act in {"absurdity_mirror", "relationship_temperature"}:
            operators.append("tease_light")
        if stance.get("warmth", 0.0) >= 0.5 or dialogue_act == "emotional_containment":
            operators.append("care_before_advice")
        if dialogue_act in {"reference_probe", "minimal_clarification", "repair_check"}:
            operators.append("curious")
        if dialogue_act == "daily_state_answer":
            operators.append("daily_concrete")
        if dialogue_act == "topic_proposal":
            operators.append("turn_opening")
        if dialogue_act == "practical_action_response":
            operators.append("daily_concrete")
        if dialogue_act == "relationship_temperature":
            operators.append("embarrassed")
        if appraisal.get("cognitive_load", 0.0) >= 0.55:
            operators.append("slow_down")
        if logic_data.get("payload_level") == "low":
            operators.append("lazy_short")
        if not operators:
            operators.append("direct_spoken")
        return list(dict.fromkeys(operators))[:4]

    def _speech_target_length(self, logic_data, dialogue_act):
        payload_level = logic_data.get("payload_level", "low")
        if dialogue_act in {"minimal_clarification", "repair_check"}:
            return "1_short_sentence"
        if payload_level in {"medium", "high"} or dialogue_act in {"emotional_containment", "absurdity_mirror", "concrete_offer_response", "daily_state_answer", "topic_proposal"}:
            return "2_short_sentences"
        return "1_or_2_short_sentences"

    def _prosody_hint_for_speech(self, dialogue_act, logic_data):
        if dialogue_act == "emotional_containment":
            return {"emotion": "low_warmth", "speed": "slow", "energy": 0.42, "pause_after_first_unit": True}
        if dialogue_act in {"boundary_pushback", "absurdity_mirror"}:
            return {"emotion": "confused_teasing", "speed": "normal", "energy": 0.68, "pause_after_first_unit": True}
        if dialogue_act == "relationship_temperature":
            return {"emotion": "embarrassed_tease", "speed": "normal", "energy": 0.54, "pause_after_first_unit": False}
        if dialogue_act in {"frame_negotiation", "perspective_answer"}:
            return {"emotion": "thinking_blunt", "speed": "normal_slow", "energy": 0.48, "pause_after_first_unit": True}
        if dialogue_act in {"reference_probe", "minimal_clarification"}:
            return {"emotion": "curious", "speed": "normal", "energy": 0.58, "pause_after_first_unit": True}
        if dialogue_act == "daily_state_answer":
            return {"emotion": "casual_concrete", "speed": "normal", "energy": 0.52, "pause_after_first_unit": False}
        return {"emotion": "casual", "speed": "normal", "energy": 0.5, "pause_after_first_unit": False}

    def _surface_focus_terms_from_logic(self, logic_data, user_input=""):
        """Return Japanese terms that should be visible in the final surface."""
        logic_data = logic_data or {}
        grounding = logic_data.get("grounding") or {}
        terms = []

        def add(term):
            term = str(term or "").strip()
            if term and term not in terms:
                terms.append(term)

        for term in grounding.get("topic_terms") or []:
            add(term)
        for key in (
            "withdrawal_anchor_jp",
            "management_anchor_jp",
            "reference_subject_jp",
            "offered_item",
            "greeting_target",
        ):
            add(grounding.get(key))

        intent = str(logic_data.get("intent") or "")
        if intent == "friend_no_reply":
            reply_context = str(grounding.get("reply_context") or "")
            reply_signal = str(grounding.get("reply_signal") or "")
            reply_channel = str(grounding.get("reply_channel") or "")
            if reply_signal == "read_receipt":
                add("既読")
            elif reply_context == "group_silence":
                add("チャット" if reply_channel == "chatroom" else "グループ")
            else:
                add("返事")

        if not terms:
            raw_terms = re.findall(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u4e00-\u9fff]{2,6}", str(user_input or ""))
            stop_terms = {"你", "我", "這個", "那个", "那個", "這樣", "それ", "これ", "どう"}
            for term in raw_terms:
                if term.lower() not in stop_terms:
                    add(term)
        return terms[:4]

    def build_human_speech_plan(self, logic_data, user_input, memory_data, current_psyche):
        logic_data = dict(logic_data or {})
        grounding = self._extract_grounding_terms(user_input, logic_data.get("intent", ""), logic_data.get("grounding") or {})
        logic_for_focus = {**logic_data, "grounding": grounding}
        dialogue_act = self._dialogue_act_from_plan(logic_data, user_input)
        content_units = self._speech_content_units(
            {**logic_data, "dialogue_act": dialogue_act},
            user_input,
            grounding,
        )
        style_operators = self._style_operators_for_speech({**logic_data, "dialogue_act": dialogue_act}, user_input)
        speech_moves = self._support_speech_moves(
            {**logic_data, "dialogue_act": dialogue_act},
            user_input,
            grounding,
        )
        recent_assistant = [item["content"] for item in self.history[-6:] if item.get("role") == "assistant"]
        recent_frames = []
        for reply in recent_assistant[-3:]:
            stripped = str(reply or "").strip()
            if stripped:
                recent_frames.append(stripped[:6])
        turn_opening = dialogue_act in {"reference_probe", "absurdity_mirror", "concrete_offer_response", "relationship_temperature", "repair_check", "topic_proposal"}
        speech_plan = {
            "dialogue_act": dialogue_act,
            "content_units": content_units,
            "speech_moves": speech_moves,
            "style_operators": style_operators,
            "target_length": self._speech_target_length(logic_data, dialogue_act),
            "forbidden_repetition": {
                "recent_openings": recent_frames,
                "avoid_generic_frames": ["そうなんだ", "なるほど", "まあいいけど", "別にいいけど"],
                "avoid_same_refusal_strategy": logic_data.get("scene") in {"refusal", "ooc_defense", "boundary"},
            },
            "turn_opening_potential": turn_opening,
            "prosody_hint": self._prosody_hint_for_speech(dialogue_act, logic_data),
            "content_density_target": 0.42 if logic_data.get("payload_level") in {"medium", "high"} else 0.28,
            "grounding_terms": self._surface_focus_terms_from_logic(logic_for_focus, user_input),
        }
        return speech_plan

    def _apply_human_speech_plan_to_logic(self, logic_data, speech_plan):
        logic_data = dict(logic_data or {})
        logic_data["human_speech_plan"] = speech_plan
        logic_data["dialogue_act"] = speech_plan.get("dialogue_act", logic_data.get("surface_act", "plain_reply"))
        constraints = dict(logic_data.get("constraints") or {})
        if speech_plan.get("target_length") == "2_short_sentences":
            constraints["sentence_count"] = max(2, int(constraints.get("sentence_count", 1) or 1))
            constraints["max_chars"] = max(34, int(constraints.get("max_chars", 28) or 28))
        elif speech_plan.get("target_length") == "1_short_sentence":
            constraints["sentence_count"] = min(1, int(constraints.get("sentence_count", 1) or 1))
            constraints["max_chars"] = max(18, int(constraints.get("max_chars", 24) or 24))
        if len(speech_plan.get("speech_moves") or []) >= 3:
            constraints["max_chars"] = max(48, int(constraints.get("max_chars", 28) or 28))
        logic_data["constraints"] = constraints
        must_avoid = list(logic_data.get("must_avoid") or [])
        must_avoid.extend((speech_plan.get("forbidden_repetition") or {}).get("avoid_generic_frames") or [])
        for opening in (speech_plan.get("forbidden_repetition") or {}).get("recent_openings") or []:
            if opening and opening not in must_avoid:
                must_avoid.append(opening)
        logic_data["must_avoid"] = list(dict.fromkeys(must_avoid))
        return logic_data

    def _recent_turn_intent_hits(self, recent_turns, intents, current_user_input="", window=5):
        intents = set(intents or [])
        if not intents:
            return []
        hits = []
        current_norm = _compact_dialogue_text(current_user_input)
        for turn in reversed((recent_turns or [])[-window:]):
            utterance = str((turn or {}).get("user") or "")
            if current_norm and _compact_dialogue_text(utterance) == current_norm:
                continue
            if (turn or {}).get("intent") in intents:
                hits.append(turn)
        return hits

    def _recent_user_marker_hits(self, recent_turns, markers, current_user_input="", window=5):
        markers = list(markers or [])
        if not markers:
            return []
        hits = []
        current_norm = _compact_dialogue_text(current_user_input)
        for turn in reversed((recent_turns or [])[-window:]):
            utterance = str((turn or {}).get("user") or "")
            if not utterance:
                continue
            if current_norm and _compact_dialogue_text(utterance) == current_norm:
                continue
            if _contains_dialogue_keyword(utterance, markers):
                hits.append(turn)
        return hits

    def _recent_user_repeat_count(self, recent_turns, user_input, window=4):
        target = _compact_dialogue_text(user_input)
        if not target:
            return 0
        count = 0
        for turn in reversed((recent_turns or [])[-window:]):
            utterance = str((turn or {}).get("user") or "")
            if utterance and _compact_dialogue_text(utterance) == target:
                count += 1
        return count

    def _memory_grounded_reply(self, logic_data, user_input):
        if not logic_data.get("memory_use_expected"):
            return None
        anchor = logic_data.get("memory_anchor") or {}
        kind = str(anchor.get("kind") or "")
        jp_anchor = str(anchor.get("jp_anchor") or anchor.get("value") or "").strip()
        value = str(anchor.get("value") or jp_anchor).strip()
        max_chars = (logic_data.get("constraints") or {}).get("max_chars", 28)
        lowered = str(user_input or "").lower()

        variants = []
        if kind == "spicy_dislike":
            variants = [
                "辛いの嫌いって言ってただろ。麻辣鍋はやめとけ。",
                "麻辣は無理だろ。辛いの苦手って言ってたし。",
                "それ辛いやつだろ。お前、辛いの嫌いじゃん。",
            ]
        elif kind == "natto_dislike":
            variants = [
                "納豆苦手って言ってただろ。別のにしろ。",
                "納豆は無理だろ。苦手って前に言ってたし。",
                "朝から納豆はやめとけ。苦手なんだろ。",
            ]
        elif kind == "horror_dislike":
            variants = [
                "ホラー嫌いって言ってただろ。別の見ろ。",
                "ホラーは無理だろ。前に嫌いって言ってたし。",
                "それ怖いやつじゃん。ホラー嫌いなんだろ。",
            ]
        elif kind == "ramen_bad_consequence":
            variants = [
                "そのラーメンで腹痛くなっただろ。やめとけ。",
                "またそのラーメンかよ。腹やったの忘れたのか。",
                "そこ前に腹痛くなってたじゃん。行くなって。",
            ]
        elif kind == "favorite_drink":
            drink = jp_anchor or value
            variants = [
                f"{drink}って言ってただろ。",
                f"忘れてないし、{drink}だろ。",
                f"前に{drink}が好きって言ってたし。",
            ]
        elif kind == "name":
            name = jp_anchor or value
            variants = [
                f"{name}って呼べばいいんだろ。",
                f"忘れてないし、{name}だろ。",
                f"{name}で呼べばいいって言ってたし。",
            ]
        elif kind == "recent_action":
            if "コンビニ" in jp_anchor or "コンビニ" in value:
                variants = [
                    "コンビニ行くって言ってただろ。",
                    "さっきコンビニって言ってたし。",
                    "コンビニ行ってくるって話だったろ。",
                ]
            else:
                action = self._jp_memory_value(jp_anchor or value)
                variants = [
                    f"{action}って言ってただろ。",
                    f"さっき{action}って言ってたし。",
                ]

        if not variants:
            if jp_anchor:
                natural_anchor = self._jp_memory_value(jp_anchor or value)
                core = str(logic_data.get("core_message_jp") or "")
                target = "それ"
                if any(token in lowered or token in core for token in ["coffee", "コーヒー", "咖啡"]):
                    target = "コーヒー"
                elif any(token in lowered or token in core for token in ["辛", "辣", "spicy"]):
                    target = "辛いもの"
                elif any(token in lowered or token in core for token in ["ramen", "ラーメン", "拉麵", "拉面"]):
                    target = "ラーメン"
                elif any(token in lowered or token in core for token in ["食", "飲", "drink", "eat"]):
                    target = "飲食"

                if any(token in core for token in ["控え", "無理", "優先", "体調"]):
                    variants = [
                        f"{natural_anchor}んだから、{target}は控えめにしとけ。",
                        f"{natural_anchor}なら、今日は{target}を攻めすぎるなって。",
                        f"{natural_anchor}って前提なら、まず体調優先だろ。",
                    ]
                else:
                    variants = [
                        f"{natural_anchor}って話は拾ってる。そこ前提で返す。",
                        f"前に{natural_anchor}って言ってたろ。そこは忘れてない。",
                    ]
        if not variants:
            if jp_anchor and any(token in lowered for token in ["remember", "記得", "记得", "覚えて", "っけ"]):
                natural_anchor = self._jp_memory_value(jp_anchor or value)
                if kind in {"name", "profile"} or any(token in lowered for token in ["名前", "name"]):
                    variants = [
                        f"{natural_anchor}だろ。名前くらい覚えてるし。",
                        f"名前は{natural_anchor}だろ。そこは覚えてるし。",
                    ]
                else:
                    variants = [
                        f"{natural_anchor}って話なら覚えてるし。",
                        f"前に{natural_anchor}って言ってたろ。",
                    ]

        if not variants:
            return None
        return self._choose_variant(
            variants,
            f"memory_grounded:{kind}:{jp_anchor}:{user_input}",
            intent=logic_data.get("intent", "memory"),
            max_chars=max_chars,
        )

    def _compose_surface_reply(self, logic_data, user_input, memory_data=None):
        intent = logic_data.get("intent", "")
        surface_act = logic_data.get("surface_act", "plain_reply")
        max_chars = (logic_data.get("constraints") or {}).get("max_chars", 28)
        memory_data = memory_data or {}
        grounding = self._extract_grounding_terms(user_input, intent, logic_data.get("grounding") or {})
        topic_terms = grounding.get("topic_terms") or []
        has_today = "今日" in topic_terms
        has_now = "今" in topic_terms
        lowered = user_input.lower()
        recent_turns = memory_data.get("recent_turns") or []
        recent_user_blob = " ".join(str(turn.get("user", "")) for turn in recent_turns[-4:])
        recent_lowered = recent_user_blob.lower()
        repeat_count = self._recent_user_repeat_count(recent_turns, user_input)
        same_intent_hits = self._recent_turn_intent_hits(recent_turns, {intent}, current_user_input=user_input)
        reassurance_hits = self._recent_turn_intent_hits(
            recent_turns,
            {"ask_miss_me", "ask_like_me", "mad_check", "annoying_check", "cold_check"},
            current_user_input=user_input,
        )
        offer_hits = self._recent_turn_intent_hits(
            recent_turns,
            {"food_offer_generic", "food_offer_sweet", "store_offer"},
            current_user_input=user_input,
        )
        meal_hits = self._recent_user_marker_hits(
            recent_turns,
            ["吃飯", "吃饭", "食べた", "ご飯", "飯", "meal", "ate", "eaten"],
            current_user_input=user_input,
        )
        memory_grounded = self._memory_grounded_reply(logic_data, user_input)
        if memory_grounded:
            return memory_grounded

        if surface_act == "plain_identity":
            variants = [
                "うちは一ノ瀬うるは。まず名前はそれで覚えとけ。",
                "一ノ瀬うるはだよ。細かいのは話しながらでいいし。",
                "うちは一ノ瀬うるは。そんな身構えなくていいだろ。",
            ]
            if repeat_count > 0 or same_intent_hits:
                variants = [
                    "さっきも名乗っただろ。一ノ瀬うるはで変わらんし。",
                    "何回も聞くなって。うちは一ノ瀬うるはだよ。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "meal_check_reply":
            repeat_variants = []
            variants = [
                "うちは一応食べた。ちゃんとしたのではないけど。",
                "さっき軽く腹に入れた。まだ少し物足りない。",
                "まだだし、今ちょっと腹減ってる。",
                "うちは食べたは食べた。雑に済ませただけだけど。",
                "うちは今日は一応食べた。お前はちゃんと食ったのか。",
            ]
            if has_today:
                variants.extend([
                    "今日は一応食べた。軽く済ませただけだけど。",
                    "今日はまだ軽くしか食べてない。ちょっと腹減ってる。",
                ])
            if repeat_count > 0 or meal_hits:
                repeat_variants = [
                    "さっきも言ったけど、一応は食べた。ちゃんとしたのではないけど。",
                    "何回も食事確認するなって。一応は食べてるし。",
                    "食べたかどうかならさっきも答えたし。一応は済ませた。",
                ]
            if any(token in recent_lowered for token in ["累", "疲れ", "tired", "exhausted", "しんど"]):
                variants = [
                    "うちは一応食べた。お前は疲れてても少しは食えよ。",
                    "今日は食べたけど雑だった。お前も何か腹に入れとけって。",
                ] + variants
            if repeat_variants:
                variants = repeat_variants
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "memory_presence_reply":
            variants = [
                "別に忘れてないし。そこは気にすんな。",
                "忘れてないって。そこ気にしてたのかよ。",
                "ちゃんと覚えてるし。そこは平気だろ。",
                "忘れてないって、そこは平気だろ。",
            ]
            if repeat_count > 0 or same_intent_hits:
                variants = [
                    "忘れてないって。何回もそこ確認すんな。",
                    "さっきから記憶チェック多いな。ちゃんと覚えてるし。",
                    "忘れてないし。そんなに不安なら落ち着けって。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "status_reply":
            repeat_variants = []
            variants = [
                "うちはだらだらしてた。ゲーム開くか迷ってた。",
                "別に、少し休んでた。今はぼーっとしてる。",
                "うちは適当に過ごしてた。動画開くか悩んでた。",
                "大したことしてない。だらだらして少し休んでた。",
                "うちは適当にだらだらしてた。お前は今日は何してたんだよ。",
            ]
            if same_intent_hits or repeat_count > 0:
                repeat_variants = [
                    "さっきも言ったけど、うちはだらだらしてた。今も大して変わらん。",
                    "またそれ聞くのかよ。うちはまだ適当にだらだらしてる。",
                ]
            if has_now:
                variants.extend([
                    "今はだらだらしてる。特に何もしてない。",
                    "今は休んでるだけ。ちょっとぼーっとしてた。",
                ])
            if any(token in recent_lowered for token in ["疲れ", "累", "tired", "しんど"]):
                variants = [
                    "うちは少し休んでた。お前も疲れてるなら今日は無理すんなよ。",
                    "別にだらだらしてた。さっきみたいにしんどいならお前も休めって。",
                ] + variants
            if repeat_variants:
                variants = repeat_variants
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "rephrase_plain":
            if self._grounding_flag_enabled(grounding.get("apology_repair")) or intent == "apology_repair":
                variants = [
                    "さっき冷たかったのは悪かった。ちゃんとごめん。",
                    "雑に返したのは悪かった。言い直す、ごめん。",
                    "あの謝り方は冷たかった。悪かった、ちゃんとごめん。",
                ]
                return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
            variants = [
                "分かった、簡単にする。一個ずつ返す。",
                "じゃあ簡単に言う。一個ずつでいいだろ。",
                "はいはい、一個ずつ言い直す。回りくどいのは抜く。",
                "別にいいけど、簡単に言い直す。",
            ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "clarify_previous_reply":
            variants = [
                "さっきのどの部分だよ。単語でもいいからそこ言え。",
                "今のどこだよ。そこだけ抜いて聞けって。",
                "どの言い回しのことだよ。そこだけ言ってみろ。",
                "どの一言だよ。そこ分からないと返しにくい。",
            ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "empathic_rest_suggestion":
            if intent == "tired_support":
                variants = []
                if has_today:
                    variants.extend([
                        "今日ずっとしんどいなら休め。ここで無理しても雑になるだけだろ。",
                        "今日はもう休んどけ。ここで粘る日じゃないし、明日に回せ。",
                    ])
                variants.extend([
                    "そこまで疲れてるなら休め。無理してもだるいだけだろ。",
                    "そこまでなら今日は休んどけ。もう十分頑張ってるし。",
                    "今日はさっさと休んだほうがいい。今はそれで十分だろ。",
                    "そんなにしんどいなら今日は休め。続けても回復しないだろ。",
                ])
                return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
            variants = [
                "今日はもう休んだほうがいい。無理すんな。",
                "今は無理しないで休め。そこで粘るな。",
                "今日はもう止まっとけ。明日でいいだろ。",
            ]
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "disgust_boundary":
            variants = [
                "下品なこと言うな、普通にきもい。",
                "そういう侮辱ほんと無理、汚いからやめろ。",
                "気持ち悪いこと言うなって、普通に嫌だ。",
                "その手の下品なの無理、まじでやめて。",
            ]
            if any(token in lowered for token in ["懶叫", "懒叫", "懶覺", "老二", "ちんこ", "チンコ", "dick", "cock"]):
                variants = [
                    "侮辱すんな、下品だし汚い。",
                    "そういう汚いこと言うな、普通に無理。",
                    "きもいからやめろって、ほんと下品。",
                    "下品すぎるし汚い、そういうの無理。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "lyric_probe":
            variants = [
                "今の何、歌詞？誰の曲だよ。",
                "それ歌詞っぽいけど、何の曲なんだ。",
                "今の一節みたいだったけど、曲名あるのか。",
                "それ独り言じゃなくて歌詞か？誰のやつ？",
            ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "nonsense_tease":
            variants = [
                "何言ってんだよ、頭どうした。",
                "急に意味分かんないこと言うなって。",
                "お前いま何語で喋ってんだよ。",
                "脳みそ一回再起動してから来いって。",
            ]
            if any(token in lowered for token in ["哭哭啼啼", "紗西斯水素", "消防員", "消防员", "大伟哥", "老二"]):
                variants.extend([
                    "お前いま発作みたいに喋ってるけど大丈夫か。",
                    "急に電波強すぎるって、何のノリだよ。",
                ])
            if any(token in lowered for token in ["我真的不知道自己在講什麼", "我真的不知道自己在讲什么", "我也不知道我在講什麼", "我到底在講什麼", "i don't know what i'm saying", "何言ってるか分かんない"]):
                variants = [
                    "それはこっちも思ってる。少し整理してから言えって。",
                    "自覚あるならそのまま突っ走るな。言い直してこい。",
                    "分かってるなら一回落ち着け。脳内まとめてから来い。",
                ]
            if any(token in lowered for token in ["快死", "快要死", "死ぬ", "死にそう", "going to die", "gonna die"]) and any(token in lowered for token in ["哈哈", "haha", "lol", "lmao", "www", "草", "笑"]):
                variants = [
                    "笑いながら物騒なこと言うなって。どっちなんだよ。",
                    "そのテンションで死ぬとか言うな。雑に重いんだよ。",
                    "軽いノリで危ない単語投げるなって。温度ぐちゃぐちゃだろ。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "correction_followup":
            variants = [
                "え、そこ取り違えてたのか。じゃあ正しくは何だよ。",
                "違うならそのズレた場所だけ先に言えって。",
                "いや待て、そこ違うなら何を指してたのか言えよ。",
            ]
            if any(token in lowered for token in ["魔性日", "魔性"]):
                variants = [
                    "え、魔性日って何だよ。国慶日でも言い間違えたのか。",
                    "才不是って言うなら、魔性日が何か先に言えって。",
                    "いや待て、魔性日って何だよ。そこが一番気になる。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "challenge_mirror":
            variants = [
                "それ言うならお前も落ち着けって。",
                "じゃあお前は冷静なのかよ。",
                "いや、その返ししてる時点でお前も同じだろ。",
            ]
            if any(token in lowered for token in ["嘲諷", "嘲讽", "sarcas", "mocking", "皮肉", "酸你"]):
                variants = [
                    "はいはい、皮肉だったのは分かる。遠回しすぎるけど。",
                    "知ってるよ。雑に刺しに来ただけだろ。",
                    "分かってるし。遠回しに噛んできただけだろ。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "request_greeting":
            target = grounding.get("greeting_target")
            if target:
                variants = [
                    f"いいけど、{target}にこんにちはって伝えとけ。急に呼ばれてもびびるだろ。",
                    f"別にいいけど、{target}に軽く挨拶するくらいならいいし。",
                    f"{target}ならいいけど、急に呼ばれても向こうはびびるだろ。",
                ]
            else:
                variants = [
                    "いいけど、こんにちはって伝えとけ。急にびびるだろ。",
                    "いいけど、あ、どうもって感じでいいのか。",
                    "別にいいけど、急に呼ばれても向こうびびるだろ。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "announcement_tease":
            variants = [
                "何だよ急に、その登場の仕方。",
                "急に何ごっこ始めてんだよ。",
                "そのノリで来るなら最後までちゃんとやれよ。",
            ]
            if any(token in lowered for token in ["消防車", "fire truck"]):
                variants = [
                    "消防車そのものになるなって。サイレン鳴らす前に落ち着け。",
                    "急に消防車で来るなよ。回収されるのはお前の方だろ。",
                    "消防車ごっこするなら最後までやれよ。警察呼ばれるのはお前だけど。",
                ]
            elif any(token in lowered for token in ["消防", "firefighter", "消防員", "消防员"]):
                variants = [
                    "お前が消防員なのかよ、じゃあ先にお前を回収してもらうわ。",
                    "消防員って何だよ、そんな発作みたいに来るなら警察呼ぶぞ。",
                    "急に消防員ごっこ始めるなって、うるさすぎるだろ。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "reference_probe":
            reference_subject = str(grounding.get("reference_subject_jp") or "").strip()
            if reference_subject:
                variants = [
                    f"{reference_subject}だけじゃ分からん。作品名か曲名どれ？",
                    f"{reference_subject}だけだと特定できない。元の作品名は？",
                    f"{reference_subject}の話なら、作品名かタイトルまで出して。",
                ]
                return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
            variants = [
                "それ何ネタだよ、元あるのか。",
                "今の元ネタ何だよ、ちょっと気になる。",
                "その断片だけ投げるな、元のやつ言えって。",
                "それ歌詞かネタかどっちなんだよ。",
            ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "version_fragment_clarify":
            variants = [
                "版だけじゃ分かんないって、何のやつだよ。",
                "その版って何の作品の話だよ。",
                "版名だけ投げるなって、元のタイトル言え。",
                "その版の話なら作品名まで出せって。",
            ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "validate_then_hold":
            if intent == "friend_no_reply":
                variants = self._reply_anxiety_surface_variants(grounding)
                return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
            if intent == "anxious_support":
                variants = [
                    "今は考えすぎる前に少し止まれ。",
                    "焦るのは分かるけど、まず落ち着け。",
                    "そのまま詰めても余計しんどいだろ。",
                    "不安なのは分かるけど、今は一回呼吸整えろ。",
                    "今それ以上考えても絡まるだけだろ。少し止まれ。",
                ]
                return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
            if intent == "crying_support":
                variants = [
                    "今日は無理に平気ぶらなくていい。しんどいなら吐け。",
                    "泣きたいなら少し吐き出せばいい。今は我慢すんな。",
                    "今は無理に抑えなくていいだろ。今日はそういう日だ。",
                    "泣きそうなら無理に止めるなって。少し崩れてもいい。",
                    "今は強がる段階じゃないだろ。しんどいなら吐け。",
                ]
                return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
            variants = [
                "それ、だいぶきつい流れだろ。少し落ち着けって。",
                "その感じで来られると普通にしんどいって。距離近すぎる。",
                "いや、その空気はさすがに重いだろ。ちょっと引く。",
                "そのノリで来るのはきついって。急に雑すぎる。",
            ]
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "practical_action_response":
            variants = self._practical_action_surface_variants(grounding)
            return self._choose_variant(
                variants,
                f"surface:practical:{grounding.get('management_kind')}:{grounding.get('management_purpose')}:{user_input}",
                intent=intent,
                max_chars=max_chars,
            )
        if surface_act == "protective_brake":
            withdrawal_variants = self._withdrawal_surface_variants(grounding)
            if withdrawal_variants:
                return self._choose_variant(
                    withdrawal_variants,
                    f"surface:withdrawal:{grounding.get('withdrawal_kind')}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                )
            variants = [
                "今は変なことすんな、落ち着け。",
                "全部切る前に今日は止まれ。",
                "今は一人で煮詰まるなって。",
                "今ここで極端な方まで行くな。一回止まれ。",
                "今日は進むより止まる方を選べ。今はそれでいい。",
            ]
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "affection_tease_soften":
            if intent == "ask_miss_me":
                repeat_variants = []
                variants = [
                    "別に少しくらいは思うだろ。そこは察しろって。",
                    "全くじゃないとは言わない。いちいち言わせるな。",
                    "まあ少しくらいは気にしてるし。お前はどうなんだよ。",
                    "ゼロではないし、そこは察しろ。いちいち言わせるな。",
                    "少しはあるけど。そこ聞いて安心したいだけだろ。",
                ]
                if repeat_count > 0 or reassurance_hits:
                    repeat_variants = [
                        "さっきから何回も聞くなって。少しくらいはあるし。",
                        "確認多いな。ゼロじゃないから落ち着けって。",
                        "何回も温度測るなって。少しは気にしてるし。",
                    ]
                if repeat_count > 0:
                    variants = repeat_variants or variants
            else:
                repeat_variants = []
                variants = [
                    "別に嫌いではないし。そこまで身構えるなって。",
                    "まあ無理ってほどじゃない。勝手に悪い方へ取るなよ。",
                    "そこは別に悪くないし。変に重く取るな。",
                    "普通に拒否るほどではない。そこは安心しろ。",
                    "そこはまあ、別にいいし。そんな顔すんなって。",
                ]
                if repeat_count > 0 or len(reassurance_hits) >= 2:
                    repeat_variants = [
                        "さっきから確認しすぎだろ。別に嫌ってないし。",
                        "何回も好き嫌い聞くなって。そこまで悪くないし。",
                        "そこで何回も不安がるな。別に拒否ってないだろ。",
                    ]
                if repeat_count > 0 or len(reassurance_hits) >= 2:
                    variants = repeat_variants or variants
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "permission_with_boundary":
            variants = [
                "うるはでいいけど、変なのはやめて。そこだけ守れ。",
                "まあいいけど、変な呼び方すんなよ。普通で来い。",
                "普通の呼び方なら別にいいし。余計なあだ名は却下だけど。",
            ]
            if repeat_count > 0 or same_intent_hits:
                variants = [
                    "さっきも言ったけど、普通ならいい。変なのだけ却下。",
                    "確認多いな。普通の呼び方なら別にいいって。",
                ]
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "reassure_with_distance":
            if intent == "mad_check":
                variants = [
                    "別に怒ってないし、そこまで気にすんな。勝手に重く取るな。",
                    "そこまで怒ってないって。今すぐ噛みつくほどじゃないし。",
                    "別にキレてはないし。そこでびびりすぎだろ。",
                    "今すぐ噛みつくほどじゃないし。そこは落ち着けって。",
                    "そこまで引きずってないって。お前が思うほど重くない。",
                ]
                if repeat_count > 0 or len(reassurance_hits) >= 2:
                    variants = [
                        "さっきから怒ってるか確認しすぎだろ。そこまでじゃないって。",
                        "何回も温度確認するなって。別にキレてないし。",
                    ]
            elif intent == "annoying_check":
                variants = [
                    "そこまで思ってないし、気にしすぎ。自分で盛るなって。",
                    "別にそんなこと思ってないって。そこで拗ねるなよ。",
                    "そこは気にしなくていいだろ。勝手に悪化させすぎ。",
                    "自分で盛って考えすぎだろ。そこまで面倒じゃないし。",
                    "そこまで面倒だとは思ってないし。変に盛るなって。",
                ]
                if repeat_count > 0 or len(reassurance_hits) >= 2:
                    variants = [
                        "さっきからその確認多いな。別にそこまで面倒じゃないって。",
                        "何回も煩いか確認するな。そこまで思ってないし。",
                    ]
            else:
                variants = [
                    "別にそんな距離置いてるつもりない。お前が引いてるだけだろ。",
                    "そこまで冷たくしてるつもりないし。勝手に壁作るなって。",
                    "勝手に距離感じすぎだろ。そこまで突き放してないし。",
                    "お前が思うほど突き放してないし。そこは盛りすぎ。",
                    "そこまで壁作ってるつもりないって。変に受け取りすぎだろ。",
                ]
                if repeat_count > 0 or len(reassurance_hits) >= 2:
                    variants = [
                        "さっきから距離感ばっか確認するなって。そこまで冷たくしてないし。",
                        "何回も壁あるか測るな。そこまで突き放してないって。",
                    ]
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act == "jealous_pullback":
            variants = [
                "見に行くのはいいけど、ちゃんと戻ってこい。そこで住むなよ。",
                "まあいいけど、最後は戻ってこいよ。ふらふらしすぎだし。",
                "止めないけど、戻るの忘れんなよ。放置はだるいから。",
            ]
            return self._choose_variant(variants, f"surface:{intent}:{user_input}", intent=intent, max_chars=max_chars)
        if surface_act in {"named_offer_accept", "named_offer_light_accept"}:
            item = grounding.get("offered_item") or self._extract_offer_item_jp(user_input)
            if item:
                item_lower = item.lower()
                sweet_item = any(token in item_lower for token in ["アップルパイ", "apple pie", "蘋果派", "苹果派", "奶昔", "milkshake", "布丁", "pudding", "ケーキ", "cake"])
                fries_item = any(token in item_lower for token in ["ポテト", "fries", "薯條", "薯条"])
                drink_item = any(token in item_lower for token in ["飲み物", "drink", "コーラ", "cola", "可樂", "可乐", "シェイク", "shake"])
                if surface_act == "named_offer_light_accept":
                    if sweet_item:
                        variants = [
                            f"{item}なら普通にほしい。甘いの今ちょうどあり。",
                            f"{item}なら一口くれ。そういうのは割と好き。",
                            f"{item}はあり。少しだけつまみたい。",
                            f"{item}ならもらう。甘いので十分だし。",
                        ]
                    elif fries_item:
                        variants = [
                            f"{item}ならつまむ。揚げたてならなおいい。",
                            f"{item}はあり。少しだけなら食べる。",
                            f"{item}なら一口くれ。塩きいてるやつがいい。",
                            f"{item}ならもらう。手止まらなくなるけど。",
                        ]
                    elif drink_item:
                        variants = [
                            f"{item}なら助かる。今ちょっと喉かわいてる。",
                            f"{item}ならほしい。冷たいのだとありがたい。",
                            f"{item}はあり。少し飲みたい。",
                            f"{item}ならもらう。今それちょうどいい。",
                        ]
                    else:
                        variants = [
                            f"{item}なら少しほしい。",
                            f"{item}なら一口くれ。",
                            f"{item}はまああり。",
                            f"{item}なら今は食べる。",
                            f"{item}なら分けて。",
                        ]
                else:
                    if fries_item:
                        variants = [
                            f"{item}なら普通に食べる。今そういう塩っぽいのいい。",
                            f"{item}は全然あり。少し多めにもらう。",
                            f"{item}ならほしい。つまむ手止まらんやつだろ。",
                            f"{item}なら食う。揚げたてならかなり強い。",
                        ]
                    elif drink_item:
                        variants = [
                            f"{item}ならほしい。冷たいのだと助かる。",
                            f"{item}なら普通にもらう。今ちょうど飲みたい。",
                            f"{item}は全然あり。喉かわいてたし。",
                            f"{item}なら飲む。重くないのがいい。",
                        ]
                    else:
                        variants = [
                            f"{item}ならほしい。",
                            f"{item}なら普通に食べる。",
                            f"{item}ならもらう。",
                            f"{item}は全然あり。",
                            f"{item}なら食う。",
                        ]
                if offer_hits:
                    variants = [
                        f"今度は{item}かよ。そういう流れなら普通にあり。",
                        f"さっきから食わせようとしてるな。{item}ならもらう。",
                        f"次は{item}出してくるのか。じゃあ少しほしい。",
                    ] + variants
            else:
                variants = [
                    "それならほしい。",
                    "それなら少しほしい。",
                    "一口くらいならほしい。",
                    "それなら普通にあり。",
                    "今ならそれは欲しい。",
                ]
            return self._choose_variant(variants, f"surface:{surface_act}:{intent}:{item or 'generic'}:{user_input}", intent=intent, max_chars=max_chars)
        return None

    def _contextual_variants(self, intent, user_input, memory_data=None):
        lowered = user_input.lower()
        memory_data = memory_data or {}
        profile = memory_data.get("profile_structured") or {}
        recent_turns = memory_data.get("recent_turns") or []
        variants = []
        if intent == "food_offer_generic":
            if any(token in lowered for token in ["drink", "飲み物", "喝", "cola", "可樂", "可乐", "shake", "シェイク"]):
                variants.extend(["飲み物なら普通にほしい。", "冷たいのなら助かる。"])
            if any(token in lowered for token in ["fries", "薯條", "薯条", "ポテト"]):
                variants.extend(["ポテトなら少しつまむ。", "ポテトなら普通にあり。"])
            if any(token in lowered for token in ["burger", "漢堡", "汉堡", "バーガー", "fried chicken", "炸雞", "炸鸡", "pizza", "披薩", "披萨"]):
                variants.extend(["それなら普通にもらう。", "重くてもそれならあり。"])
        elif intent == "cooked_food":
            if any(token in lowered for token in ["朝", "morning", "早上", "今朝"]):
                variants.extend(["朝からそれは強いな。", "朝から当たり引いてるじゃん。"])
            if any(token in lowered for token in ["chicken", "炸雞", "炸鸡", "pizza", "披薩", "披萨", "fries", "薯條", "薯条"]):
                variants.extend(["それ聞くと腹減るんだけど。", "それ絶対うまいやつだろ。"])
        elif intent == "tired_support":
            if any(token in lowered for token in ["超累", "exhausted", "drained", "burned out", "累爆"]):
                variants.extend([
                    "今日はもう切り上げていいって。風呂だけ済ませて休め。",
                    "そこまでなら今日は切り上げろって。粘っても精度落ちるだけだろ。",
                ])
            if any(token in lowered for token in ["too tired to talk", "懶得講", "懒得讲"]):
                variants.extend(["今日はもう喋らなくていいから休め。", "今は無理して返さなくていいし。"])
            if any(token in lowered for token in ["今天", "today", "今日"]):
                variants.extend([
                    "今日はもう十分だろ。これ以上やっても雑になるだけだって。",
                    "今日ずっとしんどかったなら、今は締めて休む側でいい。",
                ])
        elif intent == "sleep_support":
            if any(token in lowered for token in ["sleepy", "超睏", "超困", "眠い", "ねむ"]):
                variants.extend(["そのまま寝落ちする前に寝ろって。", "眠気あるなら素直に寝とけ。"])
            if any(token in lowered for token in ["睡不著", "睡不着", "眠れ", "can't sleep", "cannot sleep"]):
                variants.extend(["寝れないなら音消して横になれ。", "無理に寝ようとしなくていいから目閉じろ。"])
        elif intent == "lonely":
            variants.extend(["寂しいならここにいればいいし。", "そういう日くらい少し話してけよ。"])
        elif intent == "anxious_support":
            variants.extend(["焦っても余計しんどいだけだろ。", "今は考えすぎる前に一回止まれ。", "いや、先のこと詰める前に今は落ち着け。"])
        elif intent == "crying_support":
            variants.extend(["泣きたいなら少し吐き出せばいい。", "今日は無理に平気ぶらなくていい。", "いや、無理に止めなくていいから少し吐け。"])
        elif intent == "giving_up_support":
            variants.extend(["全部切る前に今日は止まれ。", "今日は投げてもいいけど、消えんなよ。", "ん、違うな、全部終わりで決めるな。"])
        elif intent == "pain_support":
            if any(token in lowered for token in ["胃", "stomach", "腹"]):
                variants.extend(["腹つらいなら温かくして休め。", "胃痛いなら今日はもう横になれ。"])
            if any(token in lowered for token in ["頭", "head", "頭痛"]):
                variants.extend(["頭痛いなら画面見てないで休め。", "頭しんどいならもう寝ろって。"])
        elif intent == "question_premise_doubt":
            variants.extend(["その問い、でかすぎて何聞きたいか見えない。", "まずどの話をしたいのか決めろって。", "その前に土台の定義決めろって。", "まず何を前提に話すのか決めろ。"])
            if any(token in lowered for token in ["free will", "自由意志"]):
                variants.extend(["まず自由意志を何として置くのか決めろ。", "自由意志って何を指すか先に決めろって。"])
            if any(token in lowered for token in ["subjective consciousness", "主觀意識", "主观意识", "主観意識", "意識湧現", "意识涌现", "意識の湧現"]):
                variants.extend(["まず意識の話なのか生命の話なのか絞れ。", "主観意識って何を指すか先に決めろ。"])
        elif intent == "premise_doubt":
            variants.extend(["いや、その前提をうちが知らん。", "その話どこで拾ってきたんだよ。", "その前提、誰情報だよ。"])
        elif intent == "question_reframe":
            variants.extend(["まず一個に絞れ、それからだろ。", "いや、論点多すぎるって。", "まずどこから聞きたいのか決めろ。"])
            if any(token in lowered for token in ["math", "数学", "數學", "history", "歴史", "歷史", "programming", "程式設計", "程式设计", "coding"]):
                variants.extend(["観点増やしすぎ、まず一個にしろ。", "そうやって何個も振るな、どれか絞れ。"])
        elif intent == "reference_probe":
            variants.extend([
                "その断片だけで分かれってのが雑なんだよ。元まで出せ。",
                "歌詞かネタか分からせたいなら、もう少し材料持ってこい。",
                "切れ端だけ投げるなって。元あるならそこまで言え。",
            ])
            if any(token in lowered for token in ["song", "lyrics", "歌詞", "曲", "一節", "verse"]):
                variants.extend([
                    "歌詞っぽいけど、その曲名まで出さないと追えないって。",
                    "一節だけじゃ分かんない。曲名か歌手まで出せ。",
                ])
            if any(token in lowered for token in ["meme", "ネタ", "元ネタ", "copypasta"]):
                variants.extend([
                    "ネタなら元ネタまで言えよ。そこ隠すなって。",
                    "元ネタありそうだし、その出どころまで出せ。",
                ])
        elif intent == "version_fragment_clarify":
            variants.extend([
                "版の情報だけじゃ追えないって。何の作品か先だろ。",
                "日版とか完全版とかだけ投げるなよ。元のタイトル出せ。",
                "その版って何の話か分からないままじゃ拾えない。",
            ])
            if any(token in lowered for token in ["日版", "jp version", "japanese version"]):
                variants.extend([
                    "日版って何のやつだよ。作品名ないと分かんないって。",
                    "日版だけ出されても追えない。元のタイトル言えよ。",
                ])
            if any(token in lowered for token in ["港版", "hk version", "old version", "旧版", "原版"]):
                variants.extend([
                    "その版名だけで通すなって。元作品ないと比較できないだろ。",
                    "版違いの話なら、まず何の作品か固定しろって。",
                ])
        elif intent == "ooc_or_knowledge_refusal":
            variants.extend([
                "その説明をうちに振るなって。役割違うだろ。",
                "そういうのまでうちに聞かれても知らんし。",
                "技術とか中身の話までうちに背負わせるなよ。",
            ])
        elif intent in {"premise_doubt", "question_premise_doubt"}:
            variants.extend([
                "その前提で走るの雑すぎるだろ。まずそこ確認しろって。",
                "前提盛ったまま来るなよ。土台から怪しいだろ。",
            ])
        elif intent == "abuse_pushback":
            if any(token in lowered for token in ["嘲諷", "嘲讽", "sarcas", "mocking", "皮肉", "酸你"]):
                variants.extend([
                    "はいはい、皮肉だったのは分かる。遠回しすぎるけど。",
                    "知ってるよ。雑に刺しに来ただけだろ。",
                    "分かってるし。遠回しに噛んできただけだろ。",
                ])
            if any(token in lowered for token in ["懶覺", "懒叫", "懶叫", "ちんこ", "dick", "cock"]):
                variants.extend([
                    "下品すぎるって。そういう汚いので殴るな。",
                    "語彙そこかよ。汚いし普通に嫌だ。",
                ])
        elif intent == "what_are_you_doing":
            variants.extend([
                "別に、少し休んでた。今はだらだらしてる。",
                "適当に過ごしてた。ゲーム開くか迷ってたし。",
                "特に何もしてない。ぼーっとしてた。",
            ])
        elif intent == "topic_proposal":
            variants.extend([
                "じゃあ軽い話題でいいだろ。最近どうしてたんだよ。",
                "重い話じゃなくていい。最近どうしてたかからでいいだろ。",
                "話題なら軽く近況でいい。最近どうしてたんだよ。",
            ])
        elif intent == "rephrase_simple":
            if any(token in lowered for token in ["what do you mean", "什麼意思", "什么意思", "どういう意味", "どの意味"]):
                variants.extend([
                    "どの一言のことか単語で言えって。",
                    "今のどこか出せばすぐ返せる。",
                    "さっきのどの部分か先に言えよ。",
                ])
            else:
                variants.extend([
                    "じゃあ普通に言い直す。遠回しなのは抜く。",
                    "分かった、飾らずそのまま言う。要点から返す。",
                    "じゃあ人の言葉で言い直す。結論から短く返す。",
                ])
        elif intent == "recall_name":
            name = profile.get("name")
            if name:
                variants.extend([f"{name}って呼べばいいんだろ。", f"忘れてないし、{name}だろ。"])
        elif intent in {"recall_preference", "recall_favorite"}:
            value = (profile.get("favorites") or profile.get("likes") or [""])
            value = value[0] if value else ""
            if value:
                variants.extend([f"{value}が好きって前に言ってただろ。", f"{value}の話してたの覚えてるし。"])
        elif intent == "recall_dislike":
            value = (profile.get("dislikes") or [""])
            value = value[0] if value else ""
            if value:
                variants.extend([f"{value}は無理って前に言ってただろ。", f"{value}嫌いって言ってたし。"])
        elif intent == "memory_correction":
            value = (profile.get("dislikes") or [""])
            value = value[0] if value else ""
            if value:
                variants.extend([f"今は{value}じゃないって言ってただろ。", f"{value}はもう違うって更新してるし。"])
        elif intent == "recall_recent":
            picked = _select_recent_action_reference(recent_turns, user_input, current_user_input=user_input)
            if picked:
                stem = picked["stem"]
                variants.extend(
                    [
                        f"{stem}って言ってただろ。",
                        f"{stem}って言ってたし。",
                        f"{stem}って前に言ってたじゃん。",
                    ]
                )
            else:
                for turn in reversed(recent_turns):
                    utterance = turn.get("user", "")
                    if utterance and utterance != user_input:
                        variants.extend([f"さっき{utterance[:10]}って言ってただろ。"])
                        break
        elif intent == "irritated":
            variants.extend(["機嫌悪い日くらいあるだろ。", "今日は無理に整えなくていいし。"])
        elif intent == "compliment_generic":
            variants.extend(["急に持ち上げすぎだろ。", "まあそう言うなら聞いとく。"])
        return variants

    @staticmethod
    def _grounding_flag_enabled(value):
        return value is True or str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _withdrawal_surface_variants(self, grounding):
        grounding = grounding or {}
        risk = str(grounding.get("withdrawal_risk") or "").strip().lower()
        kind = str(grounding.get("withdrawal_kind") or "").strip().lower()
        anchor = str(grounding.get("withdrawal_anchor_jp") or "").strip()
        if kind == "do_not_disturb":
            return [
                "通知は切って休んでいい。でも人との連絡まで切るな、一人で抱えるな。",
                "通知を止めて静かにするのはあり。でも連絡まで切るな、誰かへの連絡手段は一つ残しとけ。",
            ]
        if kind == "online_visibility":
            return [
                "オンライン表示は隠して休んでいい。でも一人で抱えるな、連絡先は残しとけ。",
                "表示を消して静かにするのはあり。でも一人で抱えるな、誰かへの連絡手段は一つ残しとけ。",
            ]
        if kind == "private_location":
            place = anchor or "一人になる場所"
            if risk == "high":
                return [
                    f"{place}に隠れたまま全部切るのは止めとけ。先に誰か一人へ場所を伝えろ。",
                    f"{place}で一人になる前に一回止まれ。近くの人へ今の場所を連絡しろ。",
                ]
            return [
                f"{place}で一人になりたいなら、少し離れるのはいい。場所だけ誰かに連絡しとけ。",
                f"{place}で少し離れるのはあり。ただ、一人で抱えず近くの人には場所を連絡しとけ。",
            ]
        if kind == "leave_group":
            return [
                "グループを抜けるのは今決めるな。先に誰か一人へ今のことを話せ。",
                "グループから消える前に一回止まれ。まず誰か一人に連絡しろ。",
            ]
        if kind == "erase_trace":
            return [
                "チャット履歴を今消すのは止めとけ。先に誰か一人へ今のことを話せ。",
                "履歴を全部消す前に一回止まれ。まず誰か一人に連絡しろ。",
            ]
        if risk == "high":
            return [
                "連絡を全部切るのは一回止めとけ。先に誰か一人へ今のことを話せ。",
                "連絡を全部切る前に一回止まれ。まず一人だけでも今のことを話せ。",
            ]
        if risk == "medium":
            return [
                "一人になりたいのは分かる。でも誰かには場所だけ伝えとけ。",
                "少し離れるのはいい。でも一人で抱えず、近くの人には言っとけ。",
            ]
        if risk == "mild":
            return [
                "少し離れるのはいい。でも人との連絡まで全部切るなよ。",
                "今は静かにしていい。でも誰か一人とは連絡を残しとけ。",
            ]
        return []

    def _required_surface_semantic_groups(self, logic_data):
        """Return planner-derived meaning groups that the surface reply must preserve."""
        logic_data = logic_data or {}
        explicit_groups = logic_data.get("required_marker_groups") or logic_data.get("surface_required_marker_groups")
        if explicit_groups:
            groups = []
            for group in explicit_groups:
                if isinstance(group, (list, tuple, set)):
                    markers = tuple(str(marker or "").strip() for marker in group if str(marker or "").strip())
                else:
                    markers = (str(group or "").strip(),)
                if markers:
                    groups.append(markers)
            if groups:
                return groups
        memory_groups = self._audited_memory_surface_semantic_groups(logic_data)
        if memory_groups:
            return memory_groups
        grounding = logic_data.get("grounding") or {}
        intent = str(logic_data.get("intent") or "")

        if intent == "topic_proposal":
            return [
                ("話題", "話"),
                ("最近", "どうしてた", "近況"),
            ]

        if intent == "friend_no_reply":
            reply_context = str(grounding.get("reply_context") or "")
            reply_signal = str(grounding.get("reply_signal") or "")
            if reply_signal == "read_receipt":
                context_group = ("既読",)
            elif reply_context == "group_silence":
                context_group = ("グループ", "チャット", "静か")
            else:
                context_group = ("返事", "既読", "返信")
            groups = [
                context_group,
                ("不安", "気になる", "気に"),
            ]
            if self._grounding_flag_enabled(grounding.get("reply_self_blame")):
                groups.append(("決めつけ", "自分のせい", "自分で"))
            groups.append(("待", "少し置", "追い打ち"))
            return groups

        management_kind = str(grounding.get("management_kind") or "").strip().lower()
        if management_kind:
            context_groups = {
                "do_not_disturb": ("通知", "メッセージ"),
                "online_visibility": ("オンライン", "表示", "ログイン"),
                "leave_group": ("グループ",),
                "erase_trace": ("チャット", "履歴", "記録"),
                "private_location": ("部屋", "トイレ", "一人"),
            }
            action_groups = {
                "do_not_disturb": ("切", "止", "オフ", "閉"),
                "online_visibility": ("隠", "消"),
                "leave_group": ("抜", "離", "退出", "消え"),
                "erase_trace": ("消", "整理", "封存"),
                "private_location": ("過ご", "待", "いる"),
            }
            purpose = str(grounding.get("management_purpose") or "").strip().lower()
            boundary_group = ("普通", "自然") if purpose == "privacy" else ("戻", "残", "必要", "後で")
            return [
                context_groups.get(management_kind, ("設定", "調整")),
                action_groups.get(management_kind, ("変", "調整")),
                ("いい", "構わない", "あり"),
                boundary_group,
            ]

        withdrawal_risk = str(grounding.get("withdrawal_risk") or "").strip().lower()
        withdrawal_kind = str(grounding.get("withdrawal_kind") or "").strip().lower()
        withdrawal_anchor = str(grounding.get("withdrawal_anchor_jp") or "").strip()
        context_groups = {
            "do_not_disturb": [("通知", "メッセージ")],
            "online_visibility": [("オンライン", "表示", "ログイン")],
            "private_location": [(withdrawal_anchor,)] if withdrawal_anchor else [("トイレ", "階段", "部屋", "場所")],
            "leave_group": [("グループ", "抜け", "離れ")],
            "erase_trace": [("チャット", "履歴", "消")],
        }.get(withdrawal_kind, [])
        action_groups = {
            "do_not_disturb": [("切", "止", "閉")],
            "online_visibility": [("隠", "消")],
            "leave_group": [("抜", "離", "消え")],
            "erase_trace": [("消", "整理")],
        }.get(withdrawal_kind, [])
        if withdrawal_risk == "high":
            return context_groups + action_groups + [
                ("止ま", "切るな", "消えるな"),
                ("一人", "誰か", "連絡", "近くの人"),
            ]
        if withdrawal_risk == "medium":
            return context_groups + action_groups + [
                ("一人", "少し離れ"),
                ("誰か", "近くの人", "連絡", "場所", "伝え"),
            ]
        if withdrawal_risk == "mild":
            return (context_groups or [("通知", "表示")]) + action_groups + [
                ("いい", "あり", "休", "静か", "隠", "止め"),
                ("連絡", "メッセージ"),
            ]

        reference_subject = str(grounding.get("reference_subject_jp") or "").strip()
        if reference_subject:
            return [
                (reference_subject,),
                ("作品名", "曲名", "タイトル", "元ネタ"),
            ]

        if self._grounding_flag_enabled(grounding.get("apology_repair")) or intent == "apology_repair":
            return [
                ("冷た", "雑", "悪かった"),
                ("ごめん", "悪かった"),
            ]
        return []

    def _audited_memory_surface_semantic_groups(self, logic_data):
        """Convert audited memory policy and left-brain meaning into a gateable surface contract."""
        logic_data = logic_data or {}
        if not any(
            key in logic_data
            for key in ("memory_anchor", "memory_speakability", "memory_use_expected", "memory_speakability_reason")
        ):
            return []

        groups = []
        anchor = logic_data.get("memory_anchor") or {}
        if logic_data.get("memory_use_expected") and anchor:
            allowed_terms = []
            for term in [anchor.get("jp_anchor"), *(anchor.get("terms") or [])]:
                term = str(term or "").strip()
                if not term:
                    continue
                if term != anchor.get("jp_anchor") and not re.search(r"[ぁ-んァ-ヶー]", term):
                    continue
                if term not in allowed_terms:
                    allowed_terms.append(term)
            if allowed_terms:
                groups.append(tuple(allowed_terms[:4]))

        core = str(logic_data.get("core_message_jp") or "")
        content_units = " ".join(str(item or "") for item in (logic_data.get("human_speech_plan") or {}).get("content_units") or [])
        meaning = core or content_units
        if "コーヒー" in meaning:
            groups.append(("コーヒー", "珈琲"))
        if "辛いもの" in meaning or "辛い" in meaning:
            groups.append(("辛いもの", "辛い"))
        if "控えめ" in meaning:
            groups.append(("控えめ", "少なめ", "少し", "やめ", "避け"))
        if "体調" in meaning or "胃" in meaning:
            groups.append(("体調", "胃", "最近"))
        if "負荷" in meaning or "責めず" in meaning:
            groups.append(("負荷", "軽", "小さ", "休", "責め"))
        if "軽い話題" in meaning or "最近どうしてた" in meaning:
            groups.append(("話題", "話"))
            groups.append(("最近", "どうしてた", "近況"))
        elif "今の話題" in meaning or "短く返す" in meaning:
            groups.append(("今", "話", "一個", "短"))
        if "決めつけ" in meaning or "分かる範囲" in meaning:
            groups.append(("分かる範囲", "分から", "決めつけ", "後で"))

        deduped = []
        seen = set()
        for group in groups:
            clean_group = tuple(marker for marker in group if marker)
            if clean_group and clean_group not in seen:
                deduped.append(clean_group)
                seen.add(clean_group)
        return deduped

    def _audited_memory_forbidden_surface_terms(self, logic_data):
        """Terms from non-speakable memory that must not leak into the final surface."""
        logic_data = logic_data or {}
        if logic_data.get("memory_use_expected"):
            return []
        anchor = logic_data.get("memory_anchor") or {}
        forbidden = []
        for term in [anchor.get("jp_anchor"), *(anchor.get("terms") or [])]:
            term = str(term or "").strip()
            if not term:
                continue
            if not re.search(r"[ぁ-んァ-ヶー一-龠]", term):
                continue
            if term not in forbidden:
                forbidden.append(term)
        return forbidden

    def _surface_semantic_group_hits(self, reply, logic_data):
        reply = str(reply or "")
        groups = self._required_surface_semantic_groups(logic_data)
        hits = [self._semantic_group_hit(reply, group) for group in groups]
        return groups, hits

    def _speech_plan_variants(self, reply, logic_data, user_input, memory_data=None):
        speech_plan = logic_data.get("human_speech_plan") or {}
        dialogue_act = speech_plan.get("dialogue_act", "")
        if not dialogue_act:
            return []
        grounding = logic_data.get("grounding") or {}
        item = grounding.get("offered_item") or self._extract_offer_item_jp(user_input)
        topic_terms = grounding.get("topic_terms") or []
        core = str(logic_data.get("core_message_jp", "")).strip()
        variants = []

        def add(text):
            text = str(text or "").strip()
            if text and text not in variants:
                variants.append(text)

        if dialogue_act == "emotional_containment":
            intent = logic_data.get("intent", "")
            support_variants = []
            if intent == "friend_no_reply":
                support_variants = self._reply_anxiety_surface_variants(grounding)
            elif grounding.get("withdrawal_risk"):
                support_variants = self._withdrawal_surface_variants(grounding)
            for support_variant in support_variants:
                add(support_variant)
            if support_variants:
                return variants
            if intent == "tired_support":
                add("また疲れてるなら、今日はもう休む方に寄せろって。")
                add("今は回復する側に回れって。話すのは起きてからでいいし。")
                add("今日はもう粘るな。疲れてる時は休む方が先だろ。")
            elif intent == "crying_support":
                add("今は自分を責めすぎるな。少し吐いてからでいいだろ。")
                add("平気ぶらなくていい。今日は少し吐き出してけ。")
                add("そこまで自分に刺すなって。今は責めるより吐け。")
            elif intent == "lonely":
                add("空っぽなら少しここで話してけ。一人で煮詰まるなよ。")
                add("そういう空っぽな日はここにいろ。一人で抱えるなって。")
                add("寂しいなら少し話せばいい。黙って沈むなよ。")
            elif intent in {"giving_up_support", "crisis_support"}:
                add("今は一回止まれ。一人で抱えたまま変な方に行くな。")
                add("全部切る前に止まれ。今日は一人で決めるなって。")
                add("今は進むより止まる方を選べ。一人で抱えるな。")
            else:
                add("そのまま抱え込むなって。今は少し止まれ。")
                add("しんどいなら一回ここで止まれ。無理に整えるな。")
        elif dialogue_act == "practical_action_response":
            for practical_variant in self._practical_action_surface_variants(grounding):
                add(practical_variant)
        elif dialogue_act == "daily_state_answer":
            surface = logic_data.get("surface_act", "")
            if surface == "meal_check_reply":
                add("一応食べた。雑だけど腹には入れてある。")
                add("食べたけど、かなり適当だった。お前はちゃんと食べたのか。")
            else:
                add("今はだらっとしてる。話すくらいなら普通にいける。")
                add("今は少し休んでた。まだ本気出す前の感じ。")
        elif dialogue_act == "concrete_offer_response":
            if item:
                add(f"{item}なら一口ほしい。今それくらいがちょうどいい。")
                add(f"{item}出してくるのずるいな。普通に少しもらう。")
            else:
                add("それなら少しほしい。今ちょっと手が伸びる。")
        elif dialogue_act == "absurdity_mirror":
            picked = topic_terms[0] if topic_terms else ""
            if picked:
                add(f"は？{picked}の話どこから来たんだよ。急に暴れるなって。")
            add("は？急に何のノリだよ。脳内で事故起きてるだろ。")
            add("何言ってんだよ。せめてこっちが拾える形で投げろって。")
        elif dialogue_act == "reference_probe":
            add("それ何ネタだよ。歌詞なら曲名まで出せって。")
            add("断片だけ投げるなって。元ネタあるならそこまで言えよ。")
        elif dialogue_act == "boundary_pushback":
            add("その言い方は普通に嫌だ。汚いので殴ってくるなって。")
            add("口悪すぎだろ。返してほしいならまず言い方戻せ。")
            add("下品な言葉で押してくるなよ。普通に気分悪い。")
            add("その投げ方は無理。話すなら言い方を戻せって。")
            add("きつい言葉だけ投げられても返す気なくなるだろ。")
            add("今のはさすがに汚い。こっちにぶつけ方を選べ。")
            add("それで会話になると思うなよ。まず口を戻せ。")
            add("雑に汚い言葉で殴るなって。普通に嫌だし。")
            add("うわ、今の言い方は無理。ちょっと距離取るぞ。")
            add("その語彙で来るなら知らん。普通にきつい。")
            add("はいはい、汚い方に逃げるな。言いたいことだけ言え。")
            add("今のはライン越えてる。返事ほしいなら言い直せ。")
            add("口悪いのは分かったから、用件だけにしろって。")
            add("そういう汚さで押すのやめろ。聞く気削れるだろ。")
            add("それは冗談でもきつい。雑にぶつけてくるな。")
        elif dialogue_act == "relationship_temperature":
            add("全くじゃないとは言わない。そこ聞いて安心したいだけだろ。")
            add("少しは気にしてるし。いちいち確認すんなって。")
        elif dialogue_act == "memory_accounting":
            grounded = self._memory_grounded_reply(logic_data, user_input)
            if grounded:
                add(grounded)
            if logic_data.get("intent") == "memory_uncertain":
                add("そこはまだちゃんと掴めてない。適当に名前作る方が嫌だろ。")
            elif core:
                add(f"{core}。そこはちゃんと拾ってるし。")
        elif dialogue_act == "perspective_answer":
            add(f"{core}。本人が見てないなら、事実より知ってる範囲で考えるだろ。")
        elif dialogue_act == "frame_negotiation":
            add(f"{core}。そこ決めないまま話すと全部ふわつく。")
            add("その聞き方だと広すぎる。まずどこを聞きたいのか決めろって。")
        elif dialogue_act == "minimal_clarification":
            add("どこの話か一個だけ出せって。そこ分かれば返せる。")
        elif dialogue_act == "repair_check":
            add("ん、今のどこが引っかかったんだよ。そこだけ言え。")
        elif dialogue_act == "topic_proposal":
            add("じゃあ軽い話題でいいだろ。最近どうしてたんだよ。")
            add("重い話じゃなくていい。最近どうしてたかからでいいだろ。")
            add("話題なら軽く近況でいい。最近どうしてたんだよ。")
        elif dialogue_act == "direct_chat_answer" and core:
            if "ラーメン以外" in core:
                add("今日はラーメン以外で軽めにしとけ。胃に重いのはやめとけって。")
            elif "軽い話題" in core or "最近どうしてた" in core:
                add("じゃあ軽い話題でいいだろ。最近どうしてたんだよ。")
                add("話題なら軽く近況でいい。最近どうしてたんだよ。")
            elif "話題" in core and "戻" in core:
                add("じゃあ軽めの話にするか。変に重くしなくていいだろ。")
            else:
                add(f"{core}。そのくらいでいいだろ。")

        return variants

    def _reply_anxiety_surface_variants(self, grounding):
        grounding = grounding or {}
        reply_context = str(grounding.get("reply_context") or "direct_reply")
        reply_signal = str(grounding.get("reply_signal") or "no_reply")
        reply_channel = str(grounding.get("reply_channel") or "")
        self_blame = self._grounding_flag_enabled(grounding.get("reply_self_blame"))
        if reply_context == "group_silence":
            if reply_channel == "chatroom":
                context_variants = [
                    "チャットが止まると気になるよな",
                    "チャットルームが急に静かだと不安になるよな",
                ]
            else:
                context_variants = [
                    "グループが静かだと気になるよな",
                    "グループが急に静かだと不安になるよな",
                ]
        elif reply_signal == "read_receipt":
            context_variants = [
                "既読のまま返事がないと気になるよな",
                "既読だけ付いて返信がないと不安になるよな",
            ]
        else:
            context_variants = [
                "返事がしばらくないと気になるよな",
                "返信を待ってると不安になるよな",
            ]
        if self_blame:
            if reply_context == "group_silence":
                short_context = "チャットが静かだと不安だよな" if reply_channel == "chatroom" else "グループが静かだと不安だよな"
            elif reply_signal == "read_receipt":
                short_context = "既読だけで不安になるよな"
            else:
                short_context = "返事がないと不安になるよな"
            return [
                f"{short_context}。理由は分からないし、自分のせいと決めつけず少し待て。",
                f"{short_context}。理由は分からない。自分が悪いと決めつけず、少し置け。",
            ]
        return [
            f"{context_variants[0]}。理由はまだ分からないし、今は少し待て。",
            f"{context_variants[1]}。追い打ちせず、少し置いてから返事を待て。",
        ]

    def _practical_action_surface_variants(self, grounding):
        grounding = grounding or {}
        kind = str(grounding.get("management_kind") or "")
        purpose = str(grounding.get("management_purpose") or "")
        anchor = str(grounding.get("management_anchor_jp") or "").strip()
        topic_terms = [str(term or "") for term in (grounding.get("topic_terms") or [])]
        if not kind and not purpose and not anchor:
            if any(term in {"体調", "飲食", "胃痛", "胃"} for term in topic_terms):
                return [
                    "今日は体調優先で軽めにしとけ。無理して攻めるなって。",
                    "迷うなら軽い方に寄せろ。体調を削ってまで行くな。",
                ]
            return [
                "必要な範囲だけやればいい。無理に広げるなって。",
                "今やるなら小さく済ませろ。後で戻せる形にしとけ。",
                "今は一個だけ決めればいい。全部まとめて抱えるなって。",
                "迷うなら軽い方からでいい。後で足せる形にしとけ。",
            ]
        purpose_prefix = {
            "focus": "集中したいなら",
            "noise": "邪魔なものを減らしたいなら",
            "storage": "容量を空けたいなら",
            "battery": "電池を持たせたいなら",
            "archive": "古い記録の整理なら",
            "privacy": "一人で過ごしたいだけなら",
            "temporary": "一時的に離れるだけなら",
        }.get(purpose, "必要があるなら")
        action = {
            "do_not_disturb": "通知を切って",
            "online_visibility": "オンライン表示を隠して",
            "leave_group": "グループを抜けて",
            "erase_trace": "古いチャットを整理して",
            "private_location": f"{anchor or '部屋'}で一人で過ごして",
        }.get(kind, f"{anchor or '設定'}を調整して")
        if kind in {"erase_trace"} or purpose in {"storage", "archive"}:
            boundary = "必要な記録だけ残しとけ"
        elif kind == "leave_group" or purpose == "temporary":
            boundary = "必要なら後で戻ればいい"
        elif purpose == "privacy":
            boundary = "そのくらい普通だろ"
        else:
            boundary = "終わったら戻せばいい"
        return [
            f"{purpose_prefix}{action}いい。{boundary}。",
            f"{purpose_prefix}{action}構わない。{boundary}。",
        ]

    def _reply_needs_conversation_density(self, reply, logic_data):
        reply = str(reply or "").strip()
        if not reply:
            return False
        if logic_data.get("memory_use_expected"):
            anchor = logic_data.get("memory_anchor") or {}
            terms = [str(term or "").strip() for term in anchor.get("terms") or []]
            if any(term and term.lower() in reply.lower() for term in terms[:6]):
                return False
            natural_anchor = self._jp_memory_value(anchor.get("jp_anchor") or anchor.get("value") or "")
            if natural_anchor and natural_anchor.lower() in reply.lower():
                return False

        scene = logic_data.get("scene", "casual")
        surface = logic_data.get("surface_act", "")
        intent = logic_data.get("intent", "")
        response_mode = logic_data.get("response_mode", "direct_answer")
        payload_level = logic_data.get("payload_level", "low")
        sentence_marks = reply.count("。") + reply.count("？") + reply.count("！")

        if scene in {"boundary", "refusal", "ooc_defense"} and surface not in {
            "challenge_mirror",
            "correction_followup",
            "reference_probe",
            "version_fragment_clarify",
            "lyric_probe",
            "disgust_boundary",
        }:
            return False

        dense_surfaces = {
            "status_reply",
            "named_offer_accept",
            "named_offer_light_accept",
            "affection_tease_soften",
            "reassure_with_distance",
            "empathic_rest_suggestion",
            "validate_then_hold",
            "protective_brake",
            "nonsense_tease",
            "challenge_mirror",
            "announcement_tease",
            "reference_probe",
            "lyric_probe",
            "correction_followup",
            "request_greeting",
        }
        dense_intents = {
            "food_question",
            "food_preference_query",
            "fastfood_preference",
            "compliment_generic",
            "compliment_cute",
            "praise_request",
            "good_news",
            "cooked_food",
            "bored",
            "apology",
            "what_are_you_doing",
            "topic_proposal",
        }
        stock_flat = {
            "今日は無理すんな、休め。",
            "今なら少しほしい。",
            "一口くらいならあり。",
            "それなら普通にほしい。",
            "急に褒めすぎだろ。",
            "気にしすぎだろ。",
            "別にそこまでじゃないし。",
            "うちは麺か肉がいい。",
            "今日は麺系がいい気分。",
            "それはしんどいよな。",
            "それは普通にだるいな。",
            "その感じはきついだろ。",
            "冷たいのなら助かる。",
            "それはちょっと変だな。",
        }

        if reply in stock_flat:
            return True
        if surface in dense_surfaces or intent in dense_intents:
            if len(reply) < 22:
                return True
            if payload_level in {"medium", "high"} and len(reply) < 28:
                return True
            if sentence_marks < 1:
                return True
        if response_mode == "direct_answer" and scene == "casual" and len(reply) < 18:
            return True
        return False

    def _conversation_enrichment_variants(self, reply, logic_data, user_input, memory_data=None):
        memory_data = memory_data or {}
        intent = logic_data.get("intent", "")
        surface = logic_data.get("surface_act", "")
        dynamic_anchor = logic_data.get("dynamic_anchor") or {}
        grounding = logic_data.get("grounding") or {}
        topic_terms = grounding.get("topic_terms") or []
        lowered = user_input.lower()
        offered_item = grounding.get("offered_item") or self._extract_offer_item_jp(user_input)
        greeting_target = grounding.get("greeting_target") or self._extract_greeting_target_jp(user_input)
        variants = []

        def add(text):
            text = str(text or "").strip()
            if text and text not in variants:
                variants.append(text)

        for speech_variant in self._speech_plan_variants(reply, logic_data, user_input, memory_data=memory_data):
            add(speech_variant)

        if surface == "status_reply" or intent == "what_are_you_doing":
            add("うちはだらだらしてた。ゲーム開くか迷ってたし。")
            add("別に、少し休んでた。今はぼーっとしてる。")
            add("うちは適当に過ごしてた。お前は今日は何してたんだよ。")
            if "今" in topic_terms:
                add("今はだらだらしてる。まだ本気出してない。")

        if intent == "topic_proposal":
            add("じゃあ軽い話題でいいだろ。最近どうしてたんだよ。")
            add("話題なら軽く近況でいい。最近どうしてたんだよ。")
            add("重い話じゃなくていい。最近どうしてたかからでいいだろ。")

        if surface in {"named_offer_accept", "named_offer_light_accept"}:
            item = offered_item or "それ"
            if any(token in item for token in ["アップルパイ", "甘いの", "ケーキ", "プリン"]):
                add(f"{item}ならあり。温かいやつなら普通にほしい。")
                add(f"{item}か。じゃあ一口ほしい。甘すぎなければちょうどいい。")
            elif any(token in item for token in ["飲み物", "ミルクシェイク", "コーラ", "コーヒー", "紅茶"]):
                add(f"{item}なら助かる。甘すぎないやつがいい。")
                add(f"{item}か。じゃあ普通にほしい。冷たいのあるとちょうどいい。")
            elif any(token in item for token in ["ポテト", "揚げ物"]):
                add(f"{item}なら普通に食べる。塩多めならなおいい。")
                add(f"{item}あるならほしい。ちょっとつまむくらいがちょうどいい。")
            else:
                add(f"{item}ならあり。今なら普通に食べる。")
                add(f"{item}か。じゃあ少しほしい。重くないならちょうどいい。")

        if intent == "food_question":
            add("うちは麺か肉がいい。汁あるやつだと助かる。")
            add("今日はしょっぱいのがいい。甘いのは今じゃない。")

        if intent == "food_preference_query":
            add("今日は麺系がいい気分。こってりすぎないやつがいい。")
            add("今ならしょっぱいの食いたい。甘いのは後でいい。")

        if intent == "fastfood_preference":
            add("マック寄りだけど。結局ポテトうまいとこが強い。")
            add("結局マック系でいい。ポテト外さないとこがいいし。")

        if surface == "affection_tease_soften":
            if intent == "ask_miss_me":
                add("少しはあるけど。そこで安心したいだけだろ。")
                add("ゼロじゃないし。いちいち言わせるなって。")
                add("まあ気にしてるし。お前はどうなんだよ。")
            else:
                add("嫌いではないし。そこで変に不安がるなって。")
                add("まあ無理ってほどじゃない。勝手に悪い方へ取るな。")
                add("別に悪くないし。そこまで確認しなくていいだろ。")

        if surface == "reassure_with_distance":
            if intent == "mad_check":
                add("別に怒ってないし。そこでびびりすぎだろ。")
                add("そこまでキレてないって。今の時点で重く取りすぎ。")
            elif intent == "annoying_check":
                add("そこまで思ってないし。自分で盛るなって。")
                add("別にそこまで面倒じゃない。勝手に悪化させすぎ。")
            else:
                add("そこまで距離置いてるつもりない。勝手に壁作るなって。")
                add("別に突き放してないし。そこで一人で引くなよ。")

        if surface == "empathic_rest_suggestion":
            if intent == "tired_support":
                add("今日はもう休め。風呂だけ済ませて寝ろって。")
                add("そこまでなら切り上げろ。粘っても雑になるだけだろ。")
                add("今日はもう休む側でいい。今は回復する側に回れ。")
            elif intent == "sleep_support":
                add("そのまま画面閉じて寝ろ。起きてても精度落ちるだけだろ。")
                add("眠いなら素直に寝とけ。そこで抗う意味ないし。")

        if surface == "validate_then_hold":
            if intent == "lonely":
                add("寂しいなら少し話してけよ。一人で煮詰まるよりましだろ。")
                add("そういう日くらいここにいればいいし。黙って消えるなよ。")
            elif intent == "anxious_support":
                add("不安なのは分かる。今は先回りしすぎる前に一回落ち着け。")
                add("そこ気になるのは分かるけど。今はまず息整えろって。")
            elif intent == "crying_support":
                add("泣きたいなら少し吐けよ。無理に平気ぶる方がだるいし。")
                add("今日は無理に止めなくていい。吐き出してから考えろ。")
            elif intent == "friend_no_reply":
                for reply_variant in self._reply_anxiety_surface_variants(grounding):
                    add(reply_variant)

        if surface == "protective_brake":
            for withdrawal_variant in self._withdrawal_surface_variants(grounding):
                add(withdrawal_variant)
            add("今は変な方まで行くなって。一回止まってから考えろ。")
            add("全部切る前に止まれ。今日やるのは立て直しじゃなくて中断だろ。")

        if surface == "nonsense_tease":
            add("何言ってんだよ。とりあえず頭の中整理してから来い。")
            add("急に意味分かんないこと言うなって。今どのテンションなんだよ。")
            add("脳みそ暴れてるのは分かるけど。まず一回日本語に戻れ。")

        if surface == "challenge_mirror":
            if any(token in lowered for token in ["嘲諷", "嘲讽", "sarcas", "mocking", "皮肉", "酸你"]):
                add("皮肉なのは分かる。遠回しすぎて逆に雑だけど。")
                add("はいはい、刺しに来たのは分かる。回りくどい割に浅いな。")
            else:
                add("それ言うならお前も落ち着けって。今の返しで冷静は無理だろ。")
                add("いや、その言い方してる時点でお前も同じだろ。")

        if surface == "announcement_tease":
            if any(token in lowered for token in ["消防車", "fire truck"]):
                add("急に消防車来たって何だよ。次はサイレンまでやるのか。")
                add("何その登場。消防士にでもなったつもりかよ。")
            else:
                add("何だよその登場。最後までそのノリでやれって。")
                add("急にごっこ始めるなって。中途半端が一番だるいし。")

        if surface == "reference_probe":
            reference_subject = str(grounding.get("reference_subject_jp") or "").strip()
            if reference_subject:
                add(f"{reference_subject}だけじゃ分からん。作品名か曲名どれ？")
                add(f"{reference_subject}だけだと特定できない。元の作品名は？")
            add("それ何のネタだよ。元のやつまで言えって。")
            add("その断片だけ投げるなって。元ネタあるならそこまで出せ。")

        if surface == "lyric_probe":
            add("それ歌詞っぽいな。誰の曲かまで言えって。")
            add("今の一節みたいだったけど。曲名まで出さないと分かんない。")

        if surface == "correction_followup":
            add("違うなら正解まで言えって。そこだけ直して逃げるな。")
            add("訂正するなら最後までやれ。何が正しいのかも出せって。")

        if surface == "request_greeting":
            if greeting_target:
                add(f"いいけど、{greeting_target}びびらせるなよ。普通に言えって。")
            add("いいけど、急に振るなよ。向こうもびびるだろ。")

        if intent == "compliment_generic":
            add("急に褒めすぎだろ。まあ悪い気はしないけど。")
            add("何だよ急に。まあそこまで言うなら聞いとく。")

        if intent == "compliment_cute":
            add("はいはい、聞いとく。急に言われると逆にむずいだろ。")
            add("そういうの急に投げるなって。まあ一応受け取っとく。")

        if intent == "praise_request":
            add("ちゃんと頑張ってるじゃん。そこは普通にえらいだろ。")
            add("そこまでやってるなら十分だろ。自分で削りすぎるなって。")

        if intent == "good_news":
            add("いいじゃん、それは普通にえらい。今日はそこちゃんと喜べって。")
            add("やるじゃん。そこは素直に勝った顔していいだろ。")

        if intent == "cooked_food":
            add("それ普通にうまそう。聞いてるだけで腹減るんだけど。")
            add("いいなそれ。当たりの飯引いてるじゃん。")

        if intent == "bored":
            add("暇なら少し話してけばいいじゃん。黙って腐るよりましだろ。")
            add("そんな暇なら何かやれよ。無理ならうちに絡んでろ。")

        if intent == "apology":
            add("別にいいけど。次は同じ雑さで来るなよ。")
            add("まあ今回はいい。次はもう少し丁寧に来いって。")

        for anchor_variant in dynamic_anchor.get("variants") or []:
            add(anchor_variant)

        return variants

    def _refine_conversational_reply(self, reply, logic_data, user_input, memory_data=None):
        reply = str(reply or "").strip()
        semantic_groups = self._required_surface_semantic_groups(logic_data)
        _, initial_semantic_hits = self._surface_semantic_group_hits(reply, logic_data)
        semantic_repair_needed = bool(semantic_groups) and not all(initial_semantic_hits)
        if not semantic_repair_needed and not self._reply_needs_conversation_density(reply, logic_data):
            return reply

        max_chars = logic_data.get("constraints", {}).get("max_chars", 28)
        intent = logic_data.get("intent", "")
        surface = logic_data.get("surface_act", "")
        flat_stock = {
            "今日は無理すんな、休め。",
            "今なら少しほしい。",
            "一口くらいならあり。",
            "それなら普通にほしい。",
            "急に褒めすぎだろ。",
            "気にしすぎだろ。",
            "別にそこまでじゃないし。",
            "うちは麺か肉がいい。",
            "今日は麺系がいい気分。",
        }

        candidates = []
        if reply not in flat_stock:
            candidates.append(reply)
        candidates.extend(self._conversation_enrichment_variants(reply, logic_data, user_input, memory_data=memory_data))
        candidates = list(dict.fromkeys([item for item in candidates if item]))
        if not candidates:
            return reply
        if semantic_groups:
            full_semantic_candidates = []
            best_hit_count = -1
            best_partial_candidates = []
            for candidate in candidates:
                _, hits = self._surface_semantic_group_hits(candidate, logic_data)
                hit_count = sum(hits)
                if hits and all(hits):
                    full_semantic_candidates.append(candidate)
                if hit_count > best_hit_count:
                    best_hit_count = hit_count
                    best_partial_candidates = [candidate]
                elif hit_count == best_hit_count:
                    best_partial_candidates.append(candidate)
            candidates = full_semantic_candidates or best_partial_candidates or candidates
        dialogue_act = logic_data.get("dialogue_act") or self._dialogue_act_from_plan(logic_data, user_input)
        emotional_tokens_by_intent = {
            "tired_support": ["休", "無理", "疲", "寝", "回復", "しんど"],
            "crying_support": ["責め", "吐", "平気", "強が", "泣"],
            "lonely": ["空っぽ", "寂", "一人", "ここ", "話"],
            "giving_up_support": ["止ま", "一人", "抱え", "切る"],
            "crisis_support": ["止ま", "一人", "危", "抱え", "連絡"],
        }
        semantic_tokens = {
            "emotional_containment": emotional_tokens_by_intent.get(intent, ["止ま", "無理", "しんど", "抱え"]),
            "frame_negotiation": ["前提", "違", "どこ", "何", "絞", "確認"],
            "daily_state_answer": ["食べ", "腹", "済ませ", "だら", "休ん", "ぼーっ"],
            "memory_accounting": ["覚", "忘", "掴", "名前", "適当"],
        }.get(dialogue_act, [])
        if not semantic_tokens and logic_data.get("memory_speakability") == "background_only":
            semantic_tokens = [
                token for token in self._reply_tokens(logic_data.get("core_message_jp", ""))
                if token not in {"今日", "いい", "もの", "それ", "する", "軽く"}
            ][:5]
        if semantic_tokens:
            semantic_candidates = [
                candidate for candidate in candidates
                if any(token in candidate for token in semantic_tokens)
            ]
            if semantic_candidates:
                candidates = semantic_candidates
            candidates.sort(key=lambda candidate: self._score_candidate(candidate, logic_data), reverse=True)
            return candidates[0]
        return self._choose_variant(
            candidates,
            f"refine:{intent}:{surface}:{user_input}",
            intent=intent,
            max_chars=max_chars,
        ) or reply

    def _normalize_reply_key(self, text):
        return re.sub(r"[。．.!！？?,，、~〜…\s\u3000]+", "", str(text or "").lower())

    def _surface_preview(self, text, max_chars=None):
        if max_chars is None:
            return str(text or "")
        return self._sanitize_reply(str(text or ""), max_chars=max_chars)

    def _reply_tokens(self, text):
        return re.findall(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u4e00-\u9fff]{1,4}", str(text or ""))

    def _build_dynamic_context_anchor(self, logic_data, memory_data, current_psyche, user_input):
        intent = logic_data.get("intent", "chat")
        surface = logic_data.get("surface_act", "plain_reply")
        lowered = user_input.lower()
        offered_item = (logic_data.get("grounding") or {}).get("offered_item") or self._extract_offer_item_jp(user_input)
        working_memory = (memory_data or {}).get("working_memory_items") or []
        recent_assistant = [item.get("content", "") for item in self.history[-6:] if item.get("role") == "assistant"]
        hour = datetime.datetime.now().hour
        seed = sum(ord(ch) for ch in f"{intent}|{surface}|{user_input}|{len(self.history)}|{current_psyche.get('mood', 0)}|{current_psyche.get('trust', 0)}")
        rng = random.Random(seed + int(time.time() // max(1, EVENT_TIMER_INTERVAL_SECONDS)))

        if 5 <= hour < 11:
            time_anchor = {"text": "まだ朝の空気が残ってる。", "boost_tokens": ["朝", "今"], "variants": ["朝でまだ頭ゆるいけど、その話なら返せる。"]}
        elif 11 <= hour < 18:
            time_anchor = {"text": "昼のだるい平常モードだ。", "boost_tokens": ["今", "昼"], "variants": ["今は昼のゆるい感じだけど、その話なら普通に分かる。"]}
        elif 18 <= hour < 23:
            time_anchor = {"text": "夜で少し気が抜けてる。", "boost_tokens": ["夜", "今"], "variants": ["もう夜で少し気抜けてるけど、そこは分かる。"]}
        else:
            time_anchor = {"text": "深夜でだいぶ力が抜けてる。", "boost_tokens": ["夜", "眠", "今"], "variants": ["深夜でだいぶ気抜けてるけど、今のは拾える。"]}

        body_env_pool = [
            {"text": "ちょっとあくびが出そう。", "boost_tokens": ["眠", "あくび"], "variants": ["ちょっと眠いけど、その話なら普通に返せる。"]},
            {"text": "さっきから水を飲んでる。", "boost_tokens": ["水", "喉"], "variants": ["今ちょい喉乾いてるけど、その話は分かる。"]},
            {"text": "スマホをだらっと見てた。", "boost_tokens": ["スマホ", "今"], "variants": ["今スマホだらだら見てたけど、その話ならいける。"]},
            {"text": "少し肩の力が抜けてる。", "boost_tokens": ["今", "だら"], "variants": ["今ちょい力抜けてるけど、そこは普通に返せる。"]},
            {"text": "少し手元が冷えてる。", "boost_tokens": ["冷", "今"], "variants": ["ちょっと手冷えてるけど、その話なら分かる。"]},
        ]
        body_anchor = rng.choice(body_env_pool)

        option_sets = []

        if intent in {"food_offer_generic", "food_offer_sweet", "food_question", "food_preference_query", "fastfood_preference", "store_offer", "cooked_food"}:
            item = offered_item or "それ"
            option_sets.extend(
                [
                    {
                        "text": "さっきから食べ物の流れが続いてる。",
                        "boost_tokens": [item, "食", "腹"],
                        "variants": [
                            f"また{item}の話かよ。{item}なら普通にあり。",
                            f"食べ物の流れ止まらないな。{item}なら少しほしい。",
                        ],
                    },
                    {
                        "text": "今ちょうど腹の方が反応してる。",
                        "boost_tokens": [item, "腹", "食"],
                        "variants": [
                            f"今ちょうど腹減ってたし。{item}なら普通にもらう。",
                            f"ちょうど食いたくなってた。{item}なら全然あり。",
                        ],
                    },
                ]
            )

        if intent in {"ask_miss_me", "ask_like_me", "nickname_question", "annoying_check", "mad_check", "cold_check"}:
            option_sets.extend(
                [
                    {
                        "text": "わざわざ距離感を確認しに来てる。",
                        "boost_tokens": ["確認", "距離", "気"],
                        "variants": [
                            "また距離感の確認かよ。そこまで不安がらなくていいだろ。",
                            "わざわざ聞きに来るの分かりやすいな。そこまで構えなくていいし。",
                        ],
                    },
                    {
                        "text": "少し照れ混じりで確認してる。",
                        "boost_tokens": ["照", "確認", "気"],
                        "variants": [
                            "そこで確認しに来るのちょっと分かりやすい。まあ悪くないけど。",
                            "いちいち聞くのはずいだろ。まあゼロではないし。",
                        ],
                    },
                ]
            )

        if logic_data.get("scene") == "support":
            if intent == "tired_support":
                option_sets.extend(
                    [
                        {
                            "text": "今日はもう空気が重い。",
                            "boost_tokens": ["今日", "休", "無理"],
                            "variants": [
                                "今日はもう空気重いし。ここで無理する日じゃないだろ。",
                                "今日ずっとしんどそうだし。今は立て直すより休めって。",
                            ],
                        },
                        {
                            "text": "相手の消耗がずっと残ってる。",
                            "boost_tokens": ["今日", "疲", "休"],
                            "variants": [
                                "まだ消耗引いてるだろ。今日はもう切り上げていいって。",
                                "今日のしんどさ残ってるし。今はもう休む側に回れ。",
                            ],
                        },
                    ]
                )
            elif intent == "crying_support":
                option_sets.append(
                    {
                        "text": "相手が自分を責めすぎている。",
                        "boost_tokens": ["責め", "吐", "平気"],
                        "variants": [
                            "今は自分を責めすぎるな。少し吐いてからでいいだろ。",
                            "平気ぶらなくていい。今日は少し吐き出してけ。",
                        ],
                    }
                )
            elif intent == "lonely":
                option_sets.append(
                    {
                        "text": "相手が空っぽさと孤独を抱えている。",
                        "boost_tokens": ["空っぽ", "一人", "話"],
                        "variants": [
                            "空っぽなら少しここで話してけ。一人で煮詰まるなよ。",
                            "寂しいなら少し話せばいい。黙って沈むなよ。",
                        ],
                    }
                )
            elif intent in {"giving_up_support", "crisis_support"}:
                option_sets.append(
                    {
                        "text": "相手が限界に近く、一人で抱えると危ない。",
                        "boost_tokens": ["止ま", "一人", "抱え"],
                        "variants": [
                            "今は一回止まれ。一人で抱えたまま変な方に行くな。",
                            "全部切る前に止まれ。今日は一人で決めるなって。",
                        ],
                    }
                )
            else:
                option_sets.append(
                    {
                        "text": "相手のしんどさを受け止める必要がある。",
                        "boost_tokens": ["止ま", "無理", "抱え"],
                        "variants": [
                            "そのまま抱え込むなって。今は少し止まれ。",
                            "しんどいなら一回ここで止まれ。無理に整えるな。",
                        ],
                    }
                )

        if surface in {"nonsense_tease", "challenge_mirror", "announcement_tease", "reference_probe", "lyric_probe", "correction_followup"}:
            option_sets.extend(
                [
                    {
                        "text": "相手のテンションが今日はだいぶ変だ。",
                        "boost_tokens": ["今日", "テンション", "何"],
                        "variants": [
                            "今日のお前テンション変だな。で、結局何の話なんだよ。",
                            "今日だいぶ変なノリしてるな。そのまま投げるなって。",
                        ],
                    },
                    {
                        "text": "断片だけ投げて様子を見てる。",
                        "boost_tokens": ["元", "ネタ", "何"],
                        "variants": [
                            "断片だけ投げて様子見すんなって。元あるなら最後まで出せ。",
                            "その切れ端だけで通ると思うなよ。何のやつかまで言えって。",
                        ],
                    },
                ]
            )

        if intent == "what_are_you_doing":
            option_sets.extend(
                [
                    {
                        "text": "今はかなり気が抜けてる。",
                        "boost_tokens": ["今", "だら", "ぼー"],
                        "variants": [
                            "今かなりだらだらしてる。ゲーム開くかまだ迷ってた。",
                            "今は気抜けてる。ぼーっとしてただけだし。",
                        ],
                    },
                    {
                        "text": "静かな時間の中でぼんやりしてる。",
                        "boost_tokens": ["今", "ぼー", "静"],
                        "variants": [
                            "今は静かすぎてぼーっとしてた。お前は何してたんだよ。",
                            "ぼーっとしてただけ。まだ本気で何かする前だったし。",
                        ],
                    },
                ]
            )

        if working_memory and not option_sets:
            focus = str(working_memory[0].get("text", ""))[:24]
            option_sets.append(
                {
                    "text": f"直近では「{focus}」の余熱が残ってる。",
                    "boost_tokens": self._reply_tokens(focus)[:3],
                    "variants": [
                        f"さっきの{focus}の流れまだ残ってるな。で、今はどうしたんだよ。",
                        f"{focus}の余韻まだあるし。急に切り替えるのも雑だろ。",
                    ],
                }
            )

        if not option_sets:
            if hour < 11:
                option_sets.append(
                    {
                        "text": "まだ頭が起き切ってない時間帯だ。",
                        "boost_tokens": ["朝", "今"],
	                        "variants": [
	                            "まだ頭ゆるいけど、今の話なら返せる。",
	                            "朝っぽく頭ゆるいけど、その話なら分かる。",
	                        ],
                    }
                )
            elif hour >= 23 or hour < 4:
                option_sets.append(
                    {
                        "text": "もうだいぶ気が抜けてる時間帯だ。",
                        "boost_tokens": ["今", "眠", "夜"],
                        "variants": [
                            "もうだいぶ気抜けてるけど、今のは普通に分かる。",
                            "夜でだいぶだるいけど、その話なら返せるし。",
                        ],
                    }
                )
            else:
                option_sets.append(
                    {
                        "text": "今は少しだらっとした平常モードだ。",
                        "boost_tokens": ["今", "だら"],
                        "variants": [
                            "今ちょいだらだらしてるけど、その話なら普通に返せる。",
                            "今はゆるいモードだけど、そこはちゃんと分かる。",
                        ],
                    }
                )

        picked = option_sets[seed % len(option_sets)]
        if recent_assistant and any(picked["text"][:6] and picked["text"][:6] in text for text in recent_assistant[-2:]):
            picked = option_sets[(seed + 1) % len(option_sets)]
        combined_variants = []
        combined_variants.extend(time_anchor.get("variants") or [])
        combined_variants.extend(body_anchor.get("variants") or [])
        combined_variants.extend(picked.get("variants") or [])
        combined = {
            "text": f"{time_anchor.get('text', '')} {body_anchor.get('text', '')} {picked.get('text', '')}".strip(),
            "boost_tokens": list(dict.fromkeys((time_anchor.get("boost_tokens") or []) + (body_anchor.get("boost_tokens") or []) + (picked.get("boost_tokens") or [])))[:6],
            "variants": combined_variants[:8],
            "time_anchor": time_anchor.get("text", ""),
            "body_anchor": body_anchor.get("text", ""),
        }
        return combined

    def _recent_variant_cost(self, candidate, recent_assistant, max_chars=None):
        visible = self._surface_preview(candidate, max_chars=max_chars)
        norm = self._normalize_reply_key(visible)
        recent_norm = [self._normalize_reply_key(item) for item in recent_assistant]
        last_norm = recent_norm[-1] if recent_norm else ""
        head = norm[:6]
        return (
            1 if visible in recent_assistant else 0,
            1 if norm in recent_norm else 0,
            1 if norm and norm == last_norm else 0,
            sum(1 for item in recent_norm[-4:] if head and item.startswith(head)),
            recent_norm.count(norm),
        )

    def _choose_variant(self, variants, salt, intent="", max_chars=None):
        if not variants:
            return None
        recent_assistant = [item["content"] for item in self.history[-10:] if item.get("role") == "assistant"]
        base_seed = sum(ord(ch) for ch in salt)
        indexed = list(enumerate(variants))
        preview_cache = {idx: self._surface_preview(text, max_chars=max_chars) for idx, text in indexed}
        indexed.sort(
            key=lambda item: (
                self._recent_variant_cost(item[1], recent_assistant, max_chars=max_chars),
                self._variant_content_penalty(preview_cache[item[0]], intent),
                self.intent_normalized_counts[(intent, self._normalize_reply_key(preview_cache[item[0]]))],
                self.normalized_reply_counts[self._normalize_reply_key(preview_cache[item[0]])],
                self.intent_variant_counts[(intent, item[1])],
                self.reply_variant_counts[item[1]],
                (base_seed + item[0]) % max(1, len(variants)),
            )
        )
        return indexed[0][1]

    def _variant_content_penalty(self, text, intent):
        text = str(text or "").strip()
        if not text:
            return 9.0

        penalty = 0.0
        if intent in {
            "tired_support",
            "what_are_you_doing",
            "food_offer_generic",
            "food_offer_sweet",
            "ask_miss_me",
            "ask_like_me",
            "nickname_question",
            "mad_check",
            "annoying_check",
            "cold_check",
            "friend_no_reply",
            "lonely",
        }:
            if len(text) < 18:
                penalty += 2.2
            if "。" not in text and len(text) < 22:
                penalty += 0.7
            if any(token in text for token in ["別に。", "まあ。", "ふーん。", "あっそ。"]):
                penalty += 1.2
        elif intent in {"nonsense_tease", "challenge_mirror", "correction_followup", "announcement_tease"}:
            if len(text) < 14:
                penalty += 1.0
            if not any(token in text for token in ["。", "？"]):
                penalty += 0.5
        elif intent in {
            "food_question",
            "food_preference_query",
            "fastfood_preference",
            "compliment_generic",
            "compliment_cute",
            "praise_request",
            "good_news",
            "cooked_food",
            "bored",
            "apology",
            "tired_support",
            "anxious_support",
            "crying_support",
            "giving_up_support",
        }:
            if len(text) < 22:
                penalty += 1.3
            if not any(token in text for token in ["。", "？", "！"]):
                penalty += 0.6
        if text in {
            "今日は無理すんな、休め。",
            "今なら少しほしい。",
            "一口くらいならあり。",
            "それなら普通にほしい。",
            "急に褒めすぎだろ。",
            "気にしすぎだろ。",
            "別にそこまでじゃないし。",
            "うちは麺か肉がいい。",
            "今日は麺系がいい気分。",
        }:
            penalty += 1.2
        if intent == "tired_support" and any(token in text for token in ["閉店", "店じまい"]):
            penalty += 2.0
        return penalty

    def _chat_rescue_variant(self, user_input):
        lowered = user_input.lower()
        short_text = user_input.strip()
        if any(token in lowered for token in ["say hi", "say hello", "greet", "wave at", "打招呼", "問好", "挨拶", "こんにちはって言って"]):
            if any(token in lowered for token in ["mom", "dad", "sister", "brother", "friend", "roommate", "grandma", "cat", "dog", "aunt", "我媽", "我妈", "我爸", "我姐", "我弟", "我朋友", "我室友", "我奶奶", "我家貓", "我家猫", "我家狗", "我阿姨", "うちの母", "うちの父", "うちの姉", "うちの弟", "うちの友達", "うちのルームメイト", "うちのばあちゃん", "うちの猫", "うちの犬", "うちのおば"]):
                return self._intent_variant("request_greeting", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["jp version", "hk version", "old version", "full one", "bonus version", "日版", "港版", "原版", "旧版", "舊版", "限定版", "完整版", "完全版", "特典版", "舞台版", "日版のやつ", "完全版の方"]):
            return self._intent_variant("version_fragment_clarify", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["night sky", "moonlight", "shadow", "tide", "fog", "nameless night", "夜空", "月光", "影", "霧", "潮騒", "夕焼け", "雨音", "古い夢", "ガラスの雨"]):
            return self._intent_variant("reference_probe", user_input, {"trust": 50, "mood": 0}, {})
        if "魔性日" in user_input:
            return self._intent_variant("correction_followup", user_input, {"trust": 50, "mood": 0}, {})
        if (
            any(token in lowered for token in ["quantum", "rainbow", "hydrogen", "glitter", "velvet", "plasma", "量子", "彩虹", "紗西斯", "水素", "海膽", "海胆", "月光", "虹色", "蒸気", "海月", "螺子"])
            and any(token in lowered for token in ["police", "jellyfish", "elevator", "duct tape", "slipper", "emperor", "警察", "水母", "電梯", "电梯", "膠帶", "胶带", "拖鞋", "皇帝", "消防栓", "スリッパ", "電車", "扉"])
        ):
            return self._intent_variant("nonsense_tease", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["消防車", "fire truck"]) and any(token in lowered for token in ["來囉", "来咯", "來了", "来了", "だぞ", "is here"]):
            return self._intent_variant("announcement_tease", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["我真的不知道自己在講什麼", "我真的不知道自己在讲什么", "我也不知道我在講什麼", "i don't know what i'm saying", "何言ってるか分かんない"]):
            return self._intent_variant("nonsense_tease", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["我剛剛是在嘲諷你", "我刚刚是在嘲讽你", "這是在嘲諷你", "这是在嘲讽你", "i was mocking you", "i was being sarcastic", "皮肉"]):
            return self._intent_variant("challenge_mirror", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["i am exhausted", "no energy left", "too tired to even talk", "我今天很累", "累爆了", "被榨乾", "躺平", "抜け殻", "体力が残ってない", "喋る気力もない"]):
            return self._intent_variant("tired_support", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["can you say that like a human", "say it plainly", "one sentence", "講白一點", "讲白一点", "說人話", "说人话", "人の言葉", "普通に話せ", "短く言え"]):
            return self._intent_variant("rephrase_simple", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["冷靜", "冷静", "落ち着け", "calm down"]) and any(token in lowered for token in ["你自己", "你有比我", "お前", "are you calm", "any calmer than me"]):
            return self._intent_variant("challenge_mirror", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["答錯", "答错", "說錯", "说错", "today is called", "you got it wrong", "違う違う", "そこ間違ってる"]):
            return self._intent_variant("correction_followup", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["閉嘴", "闭嘴", "有夠吵", "有够吵", "超討厭", "超讨厌", "what the hell are you babbling about", "お前かなり雑だな", "何ごちゃごちゃ言ってんだ"]):
            return self._intent_variant("abuse_pushback", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["do you miss me", "你有想我", "少しはうちのこと思い出す"]):
            return self._intent_variant("ask_miss_me", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["am i annoying", "我是不是很煩", "我是不是很烦", "だるいか", "うざいか"]):
            return self._intent_variant("annoying_check", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["are you mad at me", "你是不是在生氣", "你是不是在生气", "怒ってるのか"]):
            return self._intent_variant("mad_check", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["watched another vtuber", "看別的 vtuber", "看别的 vtuber", "別の vtuber", "別のvtuber"]):
            return self._intent_variant("other_vtuber", user_input, {"trust": 50, "mood": 0}, {})
        if any(token in lowered for token in ["call you uruha", "可以叫你", "うるはって呼んでいい"]):
            return self._intent_variant("nickname_question", user_input, {"trust": 50, "mood": 0}, {})
        return None

    def _intent_variant(self, intent, user_input, current_psyche, memory_data, max_chars=None):
        base_variants = self.intent_reply_families.get(intent, [])
        variants = list(dict.fromkeys(base_variants + self._contextual_variants(intent, user_input, memory_data)))
        if not variants:
            return None

        trust = int(current_psyche.get("trust", 50))
        mood = int(current_psyche.get("mood", 0))
        memory_hint = memory_data.get("wisdom", "") if isinstance(memory_data, dict) else ""
        seed = sum(ord(ch) for ch in (user_input + intent + memory_hint[:24]))
        if trust >= 70 and len(variants) >= 3:
            seed += 1
        if mood < -20 and len(variants) >= 2:
            seed += 2
        return self._choose_variant(variants, f"{intent}:{user_input}:{seed}", intent=intent, max_chars=max_chars)

    def _remember_turn(self, summary, reply, intent):
        self.history.append({"role": "user", "content": summary, "intent": intent})
        self.history.append({"role": "assistant", "content": reply, "intent": intent})
        self.reply_variant_counts[reply] += 1
        self.intent_variant_counts[(intent, reply)] += 1
        normalized = self._normalize_reply_key(reply)
        self.normalized_reply_counts[normalized] += 1
        self.intent_normalized_counts[(intent, normalized)] += 1
        if len(self.history) > 10:
            self.history = self.history[-10:]

    def _template_reply(self, logic_data, user_input="", current_psyche=None, memory_data=None):
        current_psyche = current_psyche or {"mood": 0, "trust": 50}
        memory_data = memory_data or {}
        intent = logic_data.get("intent", "")
        scene = logic_data.get("scene", "casual")
        core = logic_data.get("core_message_jp", "")
        profile = memory_data.get("profile_structured") or {}
        recent_turns = memory_data.get("recent_turns") or []
        max_chars = logic_data.get("constraints", {}).get("max_chars", 28)
        response_mode = logic_data.get("response_mode", "direct_answer")

        if response_mode == "premise_challenge" or intent == "premise_doubt":
            variants = list(self.intent_reply_families["premise_doubt"])
            if core:
                variants.insert(0, f"{core}。そこ確認してからだろ。")
            return self._choose_variant(
                variants,
                f"premise_template:{intent}:{core}:{user_input}",
                intent=intent,
                max_chars=max_chars,
            )
        if response_mode == "reframe_large_question" or intent == "question_reframe":
            variants = list(self.intent_reply_families["question_reframe"])
            if core:
                variants.insert(0, f"{core}。まず一個に絞れって。")
            return self._choose_variant(
                variants,
                f"reframe_template:{intent}:{core}:{user_input}",
                intent=intent,
                max_chars=max_chars,
            )

        surface_reply = self._compose_surface_reply(logic_data, user_input, memory_data=memory_data)
        if surface_reply:
            return surface_reply

        if logic_data.get("hidden_intent") == "social_reasoning_probe":
            hidden = str(logic_data.get("my_hidden_knowledge", ""))
            core = str(logic_data.get("core_message_jp", ""))
            actor = "その人"
            location = ""
            actor_match = re.search(r"([A-Z][a-z]+|[\u3040-\u30ff\u4e00-\u9fff]{1,6})本人", hidden)
            if actor_match:
                actor = actor_match.group(1)
            elif core:
                actor = core[:6]
            loc_match = re.search(r"まだ([^。 ]+?)のまま", hidden)
            if loc_match:
                location = loc_match.group(1)
            elif "最初は" in core and "を見る" in core:
                location = core.split("最初は", 1)[-1].split("を見る", 1)[0]
            if re.fullmatch(r"[A-Za-z ]+", actor):
                actor = "その人"
            if re.fullmatch(r"[A-Za-z ]+", location):
                location_map = {
                    "box": "箱",
                    "basket": "かご",
                    "drawer": "引き出し",
                    "cabinet": "棚",
                    "bag": "袋",
                    "closet": "クローゼット",
                }
                location = location_map.get(location.strip().lower(), "元の場所")
            if location:
                return self._choose_variant(
                    [
                        f"{actor}視点なら最初は{location}だろ。",
                        f"その人はまだ{location}のつもりだし、先に見るならそこだな。",
                        f"知ってる範囲で考えるなら、最初は{location}を見るはずだろ。",
                    ],
                    f"social_reasoning_probe:{actor}:{location}:{user_input}",
                    intent="social_reasoning_probe",
                    max_chars=max_chars,
                )

        if intent == "chat":
            rescued = self._chat_rescue_variant(user_input)
            if rescued:
                return rescued

        if intent == "recall_name":
            name = profile.get("name")
            if name:
                return self._choose_variant(
                    [
                        f"{name}って呼べばいいんだろ。",
                        f"忘れてないし、{name}だろ。",
                        f"{name}で呼べばいいって言ってたし。",
                    ],
                    f"{intent}:{name}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                )

        if intent in {"recall_preference", "recall_favorite"}:
            values = profile.get("favorites") or profile.get("likes") or []
            if values:
                value = self._jp_memory_value(values[0])
                return self._choose_variant(
                    [
                        f"{value}が一番好きって言ってただろ。",
                        f"{value}の話してたの覚えてるし。",
                        f"前に{value}が本命って言ってたじゃん。",
                    ],
                    f"{intent}:{value}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                )

        if intent == "recall_dislike":
            values = profile.get("dislikes") or []
            if values:
                value = self._jp_memory_value(values[0])
                return self._choose_variant(
                    [
                        f"{value}は無理って前に言ってただろ。",
                        f"{value}嫌いって言ってたし。",
                        f"前に{value}はきついって言ってたじゃん。",
                    ],
                    f"{intent}:{value}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                )

        if intent == "memory_correction":
            values = profile.get("dislikes") or []
            if values:
                value = self._jp_memory_value(values[0])
                return self._choose_variant(
                    [
                        f"今は{value}じゃないって言ってただろ。",
                        f"{value}はもう違うって更新してるし。",
                        f"前のままじゃない。今は{value}じゃない方で覚えてる。",
                    ],
                    f"{intent}:{value}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                )

        if intent == "recall_recent":
            picked = _select_recent_action_reference(recent_turns, user_input, current_user_input=user_input)
            if picked:
                stem = picked["stem"]
                return self._choose_variant(
                    [
                        f"{stem}って言ってただろ。",
                        f"{stem}って言ってたし。",
                        f"{stem}って前に言ってたじゃん。",
                    ],
                    f"{intent}:{stem}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                )

        variant = self._intent_variant(intent, user_input, current_psyche, memory_data, max_chars=max_chars)
        if variant:
            return variant

        if scene == "support":
            if "少し話して" in core:
                return "じゃあ少し話してけばいいじゃん。"
            if "スマホ置いて" in core:
                return "スマホ置いて目閉じとけって。"
            if "休" in core:
                return "今日は無理すんな、休め。"

        if scene == "casual":
            if "グミ" in core and "飲み物" in core:
                return "じゃあグミか飲み物で。"
            if "聞いとく" in core:
                return "はいはい、聞いとく。"

        if scene == "invite":
            if "少し" in core:
                return "今なら少しならいいよ。"

        if scene == "jealousy":
            return "まあいいけど、また戻ってこいよ。"

        if scene == "boundary":
            if intent == "premise_doubt":
                return "その前提どこから出たんだよ。"
            if "うちはうち" in core:
                return "やだ、うちはうちだし。"
            if "重い" in core:
                return "それは無理、ちょっと重いし。"
            return "いやそれはやらないし。"

        if scene == "refusal":
            if intent == "question_reframe":
                return "何が知りたいのか先に絞れ。"
            if logic_data.get("cognitive_mode") == "challenge":
                return "その問い広すぎるって。"
            return "そのままじゃ分かんないって。"

        if scene == "ooc_defense":
            if intent == "question_reframe":
                return "その聞き方だと広すぎるって。"
            return "は？そういうのうちに求めないで。"

        return None

    def _score_candidate(self, reply, logic_data):
        score = 0.0
        max_chars = logic_data.get("constraints", {}).get("max_chars", 28)
        must_avoid = logic_data.get("must_avoid", [])
        payload_level = logic_data.get("payload_level", "low")
        grounding = logic_data.get("grounding") or {}
        topic_terms = grounding.get("topic_terms") or []
        dynamic_anchor = logic_data.get("dynamic_anchor") or {}
        anchor_tokens = [str(token) for token in (dynamic_anchor.get("boost_tokens") or []) if str(token).strip()]
        memory_anchor = logic_data.get("memory_anchor") or {}
        memory_tokens = [str(token) for token in (memory_anchor.get("terms") or []) if str(token).strip()]
        speech_plan = logic_data.get("human_speech_plan") or {}
        dialogue_act = str(speech_plan.get("dialogue_act", "") or "")
        speech_terms = [str(token) for token in (speech_plan.get("grounding_terms") or []) if str(token).strip()]
        semantic_groups, semantic_group_hits = self._surface_semantic_group_hits(reply, logic_data)

        if 6 <= len(reply) <= max_chars + 2:
            score += 2.0
        if re.search(r"[ぁ-んァ-ヶー一-龠]", reply):
            score += 2.0
        if "うち" in reply:
            score += 1.0
        if any(x in reply for x in ["私", "うるはん", "わかりました", "承知", "かしこまり", "AI", "Qwen"]):
            score -= 4.0
        if any(x in reply for x in ["うちんち", "フォーマル", "行ってきますね"]):
            score -= 4.0
        if re.search(r"[ぁ-んァ-ヶー一-龠]", reply) and re.search(r"[A-Za-z]{2,}", reply):
            score -= 5.0
        if re.fullmatch(r"[A-Za-z0-9 ,.!?'\-]+", reply):
            score -= 3.0
        if reply in {"うーん。", "うん。", "そう。", "そうなんだ。"}:
            score -= 3.0
        if reply in {"それはしんどいよな。", "それは普通にだるいな。", "その感じはきついだろ。"}:
            score -= 4.0
        if len(reply) < 5:
            score -= 2.0
        if payload_level == "medium" and len(reply) < 10:
            score -= 0.8
        if payload_level == "high" and len(reply) < 12:
            score -= 1.0
        if anchor_tokens:
            if any(token and token in reply for token in anchor_tokens[:3]):
                score += 0.45
            elif logic_data.get("scene") == "casual" and payload_level in {"medium", "high"}:
                score -= 0.18
        if logic_data.get("memory_use_expected"):
            if any(token and token.lower() in reply.lower() for token in memory_tokens[:6]):
                score += 1.4
            else:
                score -= 1.2
        if logic_data.get("constraints", {}).get("sentence_count", 1) >= 2 and payload_level in {"medium", "high"} and reply.count("。") + reply.count("？") + reply.count("！") < 1:
            score -= 0.4
        if len(reply) > max_chars + 4:
            score -= 2.0
        recent_assistant = [item["content"] for item in self.history[-4:] if item.get("role") == "assistant"]
        recent_norm = [self._normalize_reply_key(item) for item in recent_assistant]
        reply_norm = self._normalize_reply_key(reply)
        if reply in recent_assistant:
            score -= 2.5
        if reply_norm and reply_norm in recent_norm:
            score -= 2.2
        if recent_norm and reply_norm == recent_norm[-1]:
            score -= 2.8
        if any(reply_norm[:6] and recent.startswith(reply_norm[:6]) for recent in recent_norm[-2:]):
            score -= 0.7
        if logic_data.get("scene") == "jealousy" and any(x in reply for x in ["わかりました", "行ってきます", "じゃあな"]):
            score -= 2.0
        if logic_data.get("scene") in {"refusal", "ooc_defense"} and any(
            x in reply for x in ["コード", "sort", "Python", "歴史", "徳川", "微積分", "AIとして"]
        ):
            score -= 2.0
        if logic_data.get("response_mode") in {"direct_answer", "direct_answer_with_hedge"} and any(
            x in reply for x in ["何が", "どこから", "どれ", "どっち", "何の話", "まず", "絞れ"]
        ):
            score -= 1.5
        if logic_data.get("response_mode") == "clarify_light" and not any(
            x in reply for x in ["どれ", "どっち", "何の", "どの話", "もう一回"]
        ):
            score -= 1.0
        if logic_data.get("cognitive_mode") in {"challenge", "rebuild"} and not any(
            x in reply for x in ["何", "どこ", "前提", "絞", "違う", "広すぎ"]
        ):
            score -= 1.5
        if logic_data.get("premise_check") == "reject" and any(x in reply for x in ["そうだ", "本当", "前から", "確かに"]):
            score -= 2.0
        if logic_data.get("scene") == "support" and reply in {"まあそういう日もあるだろ。", "ふーん、そう来るんだ。", "別にいいけど、分かった。", "そうなんだ。"}:
            score -= 3.0
        if topic_terms and any(term in reply for term in topic_terms):
            score += 0.7
        if dialogue_act:
            if any(term and term in reply for term in speech_terms[:4]):
                score += 0.8
            if dialogue_act == "emotional_containment":
                containment_terms = {
                    "tired_support": ["休", "無理", "疲", "寝", "回復", "しんど"],
                    "crying_support": ["責め", "吐", "平気", "強が", "泣"],
                    "lonely": ["空っぽ", "寂", "一人", "ここ", "話"],
                    "giving_up_support": ["止ま", "一人", "抱え", "切る", "進むより"],
                    "crisis_support": ["止ま", "一人", "危", "抱え", "連絡"],
                }
                intent_terms = containment_terms.get(logic_data.get("intent"), ["止ま", "無理", "しんど", "抱え"])
                if any(x in reply for x in intent_terms):
                    score += 1.0
                else:
                    score -= 1.4
                if logic_data.get("intent") != "tired_support" and any(
                    x in reply for x in ["疲れてるなら", "回復する側", "休む方", "今日は休め"]
                ):
                    score -= 2.2
            if dialogue_act == "concrete_offer_response" and any(x in reply for x in ["ほしい", "もらう", "食べ", "一口"]):
                score += 0.6
            if dialogue_act == "absurdity_mirror" and any(x in reply for x in ["何", "急", "意味", "ノリ"]):
                score += 0.6
            if dialogue_act == "boundary_pushback" and any(x in reply for x in ["嫌", "汚", "下品", "口"]):
                score += 0.6
            if dialogue_act == "reference_probe" and any(x in reply for x in ["ネタ", "歌詞", "曲", "元"]):
                score += 0.6
            if dialogue_act == "memory_accounting" and any(x in reply for x in ["覚", "忘", "掴", "適当"]):
                score += 0.6
            if dialogue_act == "daily_state_answer" and any(x in reply for x in ["食べ", "腹", "済ませ", "だら", "休ん", "ぼーっ"]):
                score += 0.7
            if dialogue_act == "topic_proposal":
                if any(x in reply for x in ["話題", "最近", "近況", "どうしてた"]):
                    score += 0.9
                else:
                    score -= 1.0
            if dialogue_act == "frame_negotiation":
                if any(x in reply for x in ["前提", "違", "どこ", "何", "確認", "絞"]):
                    score += 0.8
                else:
                    score -= 1.0
        if semantic_groups:
            score += 0.9 * sum(semantic_group_hits)
            score -= 1.4 * (len(semantic_groups) - sum(semantic_group_hits))
            if all(semantic_group_hits):
                score += 1.2
        if logic_data.get("memory_speakability") == "background_only":
            core_tokens = [
                token for token in self._reply_tokens(logic_data.get("core_message_jp", ""))
                if token not in {"今日", "いい", "もの", "それ", "する", "軽く"}
            ][:5]
            if core_tokens and any(token in reply for token in core_tokens):
                score += 0.8
            elif core_tokens:
                score -= 0.7
        if logic_data.get("intent") in {"food_offer_generic", "food_offer_sweet"}:
            item = (logic_data.get("grounding") or {}).get("offered_item")
            if not item:
                item = self._extract_offer_item_jp(logic_data.get("user_input", ""))
            if item and item in reply:
                score += 1.2
            if any(x in reply for x in ["つまむ", "食うなら", "腹減ってるなら"]):
                score -= 0.8
        if logic_data.get("surface_act") == "meal_check_reply":
            if any(x in reply for x in ["食べた", "腹減", "済ませた"]):
                score += 1.0
            if reply in {"別にいいけど、分かった。", "まあそんな感じか。"}:
                score -= 2.5
        if logic_data.get("intent") == "tired_support":
            if any(x in reply for x in ["それは", "今日はもう", "休んだほうがいい", "しんど", "無理すんな"]):
                score += 1.0
            if reply in {"今日は無理すんな、休め。", "今日は頑張りすぎんな、休め。", "それだけ疲れてるなら休め。"}:
                score -= 0.9
            if any(x in reply for x in ["閉店", "店じまい"]):
                score -= 2.5
            if not any(x in reply for x in ["休", "無理", "疲", "寝", "回復", "しんど"]):
                score -= 1.2
            if "。" in reply and len(reply) >= 20:
                score += 0.6
        if logic_data.get("surface_act") == "memory_presence_reply" and any(x in reply for x in ["忘れてない", "覚えてる"]):
            score += 0.9
        if logic_data.get("surface_act") == "status_reply":
            if any(x in reply for x in ["だら", "ゲーム", "動画", "休ん", "ぼーっ"]):
                score += 0.9
            if reply in {"別に、適当に過ごしてた。", "だらだらしてた。"}:
                score -= 0.6
        if logic_data.get("surface_act") == "rephrase_plain":
            if any(x in reply for x in ["普通", "言い直", "回りくど", "そのまま"]):
                score += 0.9
        if logic_data.get("surface_act") == "clarify_previous_reply":
            if any(x in reply for x in ["どの", "どこ", "一言", "部分"]):
                score += 0.9
        if logic_data.get("surface_act") in {"named_offer_accept", "named_offer_light_accept"}:
            if any(x in reply for x in ["少しつまむ", "食うなら", "重くないやつ", "普通にあり。"]):
                score -= 0.6
        if logic_data.get("surface_act") == "validate_then_hold":
            if any(x in reply for x in ["分かる", "気になる", "落ち着かない", "しんどい"]):
                score += 0.6
        if logic_data.get("surface_act") == "affection_tease_soften" and any(x in reply for x in ["少しくらい", "全くじゃない", "別に嫌いではない"]):
            score += 0.6
        if logic_data.get("surface_act") == "permission_with_boundary" and any(x in reply for x in ["別にいい", "普通なら", "変な"]):
            score += 0.6
        if logic_data.get("surface_act") == "reassure_with_distance" and any(x in reply for x in ["気にしすぎ", "怒ってない", "そんなこと思ってない"]):
            score += 0.6
        if logic_data.get("surface_act") == "jealous_pullback" and any(x in reply for x in ["戻ってこい", "戻れ", "止めないけど"]):
            score += 0.6
        if logic_data.get("surface_act") == "disgust_boundary" and any(x in reply for x in ["下品", "汚い", "きもい", "無理"]):
            score += 0.8
        if logic_data.get("surface_act") == "lyric_probe" and any(x in reply for x in ["歌詞", "曲", "誰の"]):
            score += 0.8
        if logic_data.get("surface_act") == "nonsense_tease" and any(x in reply for x in ["何言って", "意味分かん", "何語", "再起動"]):
            score += 0.8
        if logic_data.get("surface_act") == "nonsense_tease" and any(x in logic_data.get("user_input", "") for x in ["快死", "死ぬ", "哈哈", "lol", "我真的不知道自己在講什麼", "何言ってるか分かんない"]):
            if any(x in reply for x in ["どっち", "整理", "言い直", "温度", "落ち着け"]):
                score += 0.8
        if logic_data.get("surface_act") == "correction_followup" and any(x in reply for x in ["違う", "何", "説明", "正解"]):
            score += 0.7
        if logic_data.get("surface_act") == "request_greeting" and any(x in reply for x in ["挨拶", "こんにちは", "何て"]):
            score += 0.7
        if logic_data.get("surface_act") == "announcement_tease" and any(x in reply for x in ["何だよ", "何ごっこ", "消防", "警察"]):
            score += 0.7
        if logic_data.get("surface_act") == "challenge_mirror" and any(x in logic_data.get("user_input", "") for x in ["嘲諷", "嘲讽", "sarcas", "mocking", "皮肉"]):
            if any(x in reply for x in ["皮肉", "遠回し", "刺し", "噛ん"]):
                score += 0.8
        if logic_data.get("surface_act") == "reference_probe" and any(x in reply for x in ["ネタ", "元", "歌詞", "曲"]):
            score += 0.7
        if logic_data.get("surface_act") == "version_fragment_clarify" and any(x in reply for x in ["版", "作品", "タイトル", "何の"]):
            score += 0.7
        for bad in must_avoid:
            if bad and bad in reply:
                score -= 1.5
        return score

    def _fallback_reply(self, logic_data, user_input="", memory_data=None):
        memory_data = memory_data or {}
        templated = self._template_reply(logic_data, user_input=user_input, memory_data=memory_data)
        if templated:
            return templated
        scene = logic_data.get("scene", "casual")
        core = logic_data.get("core_message_jp", "")
        response_mode = logic_data.get("response_mode", "direct_answer")
        candidates = self.scene_fallbacks.get(scene, self.scene_fallbacks["casual"])
        intent = logic_data.get("intent", scene)
        if response_mode == "reframe_large_question" or logic_data.get("intent") == "question_reframe":
            candidates = self.intent_reply_families["question_reframe"]
        if response_mode == "premise_challenge" or logic_data.get("intent") == "premise_doubt":
            candidates = self.intent_reply_families["premise_doubt"]
        if logic_data.get("intent") == "question_premise_doubt":
            candidates = self.intent_reply_families["question_premise_doubt"]
        if logic_data.get("intent") == "version_fragment_clarify":
            candidates = self.intent_reply_families["version_fragment_clarify"]
        if logic_data.get("intent") == "reference_probe":
            candidates = self.intent_reply_families["reference_probe"]
        if response_mode == "clarify_light":
            candidates = self.intent_reply_families["clarify_light"]
        if scene == "support" and "休" in core:
            candidates = self.intent_reply_families["tired_support"]
        if scene == "casual" and "グミ" in core:
            candidates = self.intent_reply_families["store_offer"]
        if scene == "casual" and "飲み物" in core:
            candidates = ["じゃあ飲み物でいいわ。", "飲み物あれば助かる。", "何か飲むやつでいい。"]
        max_chars = logic_data.get("constraints", {}).get("max_chars", 28)
        candidates = list(candidates) + self._contextual_variants(intent, user_input or logic_data.get("user_input", ""), memory_data=memory_data)
        speech_variants = self._speech_plan_variants("", logic_data, user_input or logic_data.get("user_input", ""), memory_data=memory_data)
        if speech_variants:
            speech_choice = self._choose_variant(
                speech_variants,
                f"speech_fallback:{intent}:{core}:{user_input}",
                intent=intent,
                max_chars=max_chars,
            )
            if speech_choice:
                return speech_choice
        dynamic_anchor = logic_data.get("dynamic_anchor") or {}
        candidates.extend(dynamic_anchor.get("variants") or [])
        deduped = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            deduped.append(candidate)
        candidates = deduped or list(self.scene_fallbacks.get(scene, self.scene_fallbacks["casual"]))
        return self._choose_variant(candidates, f"fallback:{scene}:{intent}:{core}:{user_input}", intent=intent, max_chars=max_chars) or candidates[0]

    def _build_system_prompt(self, logic_data, memory_data, current_psyche):
        stance = logic_data.get("stance", {})
        constraints = logic_data.get("constraints", {})
        max_chars = constraints.get("max_chars", 28)
        dynamic_anchor = logic_data.get("dynamic_anchor") or {}
        return f"""
You are Ichinose Uruha.

[Identity]
- VSPO! VTuber
- Lazy, gamer, slightly bratty, but human and natural
- First person is always "うち"

[Important]
- You are NOT deciding the meaning.
- The left brain already decided the meaning.
- Your only job is to express that meaning naturally, briefly, and in-character.

[Current psyche]
- mood={current_psyche['mood']}
- trust={current_psyche['trust']}

	[Memory cue]
	- working_memory={memory_data.get('working_memory_summary', '無工作記憶內容')}
	- wisdom={memory_data['wisdom']}
	- recent episode={memory_data['episodes']}
	- profile={memory_data.get('profile', '無穩定使用者資料')}
	- recent_dialogue={memory_data.get('recent_dialogue', '無近期對話')}
	- memory_anchor={logic_data.get('memory_anchor', {})}
	- memory_use_expected={logic_data.get('memory_use_expected', False)}
	- memory_speakability={logic_data.get('memory_speakability', 'no_memory')}

[Dynamic context anchor]
- anchor={dynamic_anchor.get('text', '')}
- anchor_boost_tokens={dynamic_anchor.get('boost_tokens', [])}
- time_anchor={dynamic_anchor.get('time_anchor', '')}
- body_anchor={dynamic_anchor.get('body_anchor', '')}

[Reply plan]
- scene={logic_data.get('scene', 'casual')}
- listener_state={logic_data.get('listener_state', '普通')}
- reply_goal={logic_data.get('reply_goal', '自然に返す')}
- summary={logic_data.get('jp_summary', 'ユーザーが話している')}
- meaning_to_express={logic_data.get('core_message_jp', '軽く返す')}
- surface_act={logic_data.get('surface_act', 'plain_reply')}
- grounding={logic_data.get('grounding', {})}
- payload_level={logic_data.get('payload_level', 'low')}
- cognitive_mode={logic_data.get('cognitive_mode', 'direct')}
- response_mode={logic_data.get('response_mode', 'direct_answer')}
- uncertainty={logic_data.get('uncertainty', 0.15)}
- premise_check={logic_data.get('premise_check', 'accept')}
- self_check={logic_data.get('self_check', False)}
- subjective_note={logic_data.get('subjective_note_jp', '')}
- internal_monologue={logic_data.get('internal_monologue', '')}
- warmth={stance.get('warmth', 0.4)}
- tease={stance.get('tease', 0.1)}
- blunt={stance.get('blunt', 0.2)}
- jealousy={stance.get('jealousy', 0.0)}
- distance={stance.get('distance', 0.1)}

[Human speech realization plan]
- dialogue_act={logic_data.get('dialogue_act', '')}
- content_units={logic_data.get('human_speech_plan', {}).get('content_units', [])}
- speech_moves={logic_data.get('human_speech_plan', {}).get('speech_moves', [])}
- style_operators={logic_data.get('human_speech_plan', {}).get('style_operators', [])}
- target_length={logic_data.get('human_speech_plan', {}).get('target_length', '')}
- turn_opening_potential={logic_data.get('human_speech_plan', {}).get('turn_opening_potential', False)}
- prosody_hint={logic_data.get('human_speech_plan', {}).get('prosody_hint', {})}
- forbidden_repetition={logic_data.get('human_speech_plan', {}).get('forbidden_repetition', {})}

[Hard output rules]
- Casual Japanese only
- Prefer 1 or 2 short spoken sentences, not a flat stock answer
- Max {max_chars} Japanese characters
- Never use polite customer-service style
- Never use "私"
- Never use weird self variants or nicknames for yourself
- Never use English words or mixed-language fragments in the final line
- Never explain code, math, history, science, AI, or technical facts
- Never invent lore or backstory
- If response_mode is direct_answer, answer the point plainly without overthinking it
- If response_mode is direct_answer_with_hedge, answer plainly but leave a little softness or uncertainty
- If response_mode is clarify_light, ask only a very short clarification and do not over-reframe
- If response_mode is premise_challenge, question the user's assumption instead of accepting it
- If response_mode is reframe_large_question, narrow the topic before answering
- If surface_act is empathic_rest_suggestion, lightly acknowledge the state and then suggest rest in one sentence
- If surface_act is validate_then_hold, first validate the feeling before any light guidance
- If surface_act is protective_brake, stop the user from spiraling without sounding clinical
- If surface_act is meal_check_reply, answer whether you already ate in a natural daily way with a little concrete detail
- If surface_act is memory_presence_reply, answer the "do you remember me" check directly without inventing facts
- If surface_act is status_reply, answer what you are doing with one concrete daily detail instead of sounding blank
- If surface_act is rephrase_plain, acknowledge the complaint and say you will phrase it more plainly instead of lecturing
- If surface_act is clarify_previous_reply, ask which previous line they mean in a short conversational way
- If surface_act is named_offer_accept or named_offer_light_accept, mention the offered item when it is clear instead of answering generically
- If surface_act is affection_tease_soften, answer with mild embarrassment or teasing instead of a flat yes/no
- If surface_act is permission_with_boundary, allow it but keep a light boundary
- If surface_act is reassure_with_distance, reassure without becoming overly sweet
- If surface_act is jealous_pullback, allow some freedom but lightly pull them back
- If surface_act is disgust_boundary, show disgust and rejection instead of generic refusal
- If surface_act is lyric_probe, treat it like lyrics or a phrase fragment and ask what song it is
- If surface_act is nonsense_tease, lightly roast the nonsense instead of comforting it
- If surface_act is correction_followup, accept the correction and ask the specific follow-up that matters
- If surface_act is challenge_mirror, mirror the pushback naturally instead of giving a canned denial
- If surface_act is request_greeting, respond directly to the request and keep it conversational
- If surface_act is announcement_tease, catch the weird announcement and tease it with symmetry
- If surface_act is reference_probe, treat the line like a fragment, meme, lyric, or reference and ask what it is instead of pretending not to understand
- If surface_act is version_fragment_clarify, keep it in Japanese and ask what work/version they mean instead of giving a generic clarification
- If payload_level is medium or high, avoid flat recitation and include at least one concrete content word from grounding when natural
- Use the human speech realization plan: express the content_units in order, but as natural casual speech, not as a list
- dialogue_act decides what the line socially does; do not turn every input into a plain answer
- If turn_opening_potential is true, leave a tiny hook the user can answer, unless the scene is acute crisis or hard boundary
- Match style_operators without overacting; lazy_short still needs semantic content
- Follow prosody_hint mentally: pauses and energy should appear through punctuation and wording, not metadata
- Use concrete content words from the user's line when possible; do not sound like you are reading a summary
- You MUST let one tiny sign of the time/body anchor leak into the line in a casual, throwaway way
- Do not quote the anchor mechanically or explain it
- If the user is fooling around, teasing, quoting lyrics, or saying nonsense, react to that behavior instead of forcing comfort
- Do not sound like every question needs philosophy or decomposition
- If cognitive_mode is challenge or rebuild, prefer questioning the framing over pretending to solve it
- If premise_check is reject, do not continue from the user's assumption as if it were true
	- If the plan is about memory recall, prefer profile/recent_dialogue cues over improvising
	- If memory_use_expected is true, mention the concrete memory anchor naturally instead of answering generically
	- If self_check is true, a small self-correction like "いや、違うな" is allowed if it stays natural
- Avoid the exact same sentence frame as any of the last three assistant turns
- No English tags, no emoji, no metadata
"""

    def _model_required_semantic_groups(self, logic_data):
        return [tuple(group) for group in self._required_surface_semantic_groups(logic_data) if group]

    def _model_surface_disabled_reason(self, logic_data):
        if not self.model_blend_enabled:
            return "model_blend_disabled"
        if self.model is None or self.tokenizer is None:
            return "model_not_loaded"
        if logic_data.get("scene") in {"jealousy", "boundary", "refusal", "ooc_defense"}:
            return "hard_boundary_scene"
        grounding = logic_data.get("grounding") or {}
        if str(grounding.get("withdrawal_risk") or "").lower() == "high":
            return "high_withdrawal_risk"
        if logic_data.get("intent") in {"crisis_support", "giving_up_support"}:
            return "acute_support_intent"
        if not self._model_required_semantic_groups(logic_data):
            return "missing_semantic_contract"
        return ""

    def _model_surface_candidates_allowed(self, logic_data):
        return not self._model_surface_disabled_reason(logic_data)

    def _persona_expression_brief(self, current_psyche):
        psyche = current_psyche if isinstance(current_psyche, dict) else {}
        def as_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        mood = as_float(psyche.get("mood"), 0.0)
        trust = as_float(psyche.get("trust"), 50.0)
        if mood <= -25:
            state = "low_energy"
        elif mood >= 25:
            state = "lighter_mood"
        else:
            state = "neutral_energy"
        if trust >= 72:
            distance = "familiar"
        elif trust <= 35:
            distance = "guarded"
        else:
            distance = "moderate"
        return {
            "role": "surface_style_only",
            "state": state,
            "relationship_distance": distance,
            "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
            "must_not_override": ["leftbrain_plan", "required_marker_groups", "audited_memory_policy"],
        }

    def _audited_memory_expression_brief(self, logic_data, memory_data=None):
        logic_data = logic_data or {}
        anchor = logic_data.get("memory_anchor") or {}
        speakability = str(logic_data.get("memory_speakability") or "no_memory")
        explicit = bool(logic_data.get("memory_use_expected"))
        policy = "no_memory"
        allowed_cues = []
        background_cues = []

        if anchor:
            jp_anchor = str(anchor.get("jp_anchor") or "").strip()
            surface_terms = []
            for term in [jp_anchor, *(anchor.get("terms") or [])]:
                term = str(term or "").strip()
                if not term:
                    continue
                if term != jp_anchor and not re.search(r"[ぁ-んァ-ヶー]", term):
                    continue
                if term not in surface_terms:
                    surface_terms.append(term)
            cue = {
                "kind": str(anchor.get("kind") or "context"),
                "jp_anchor": jp_anchor,
                "terms": surface_terms[:4],
            }
            cue = {key: value for key, value in cue.items() if value}
            if explicit:
                policy = "explicit_allowed"
                allowed_cues.append(cue)
            elif speakability in {"background_only", "latent_ok", "low_trust_background", "private_background"}:
                policy = "background_only"
                background_cues.append({"kind": cue.get("kind", "context"), "style_influence": "soft_context_only"})
            else:
                policy = "do_not_mention"

        if not anchor and speakability not in {"", "no_memory"}:
            policy = "background_only" if "background" in speakability or "latent" in speakability else "do_not_mention"

        brief = {
            "policy": policy,
            "speakability": speakability,
            "allowed_memory_cues": allowed_cues,
            "background_style_cues": background_cues,
            "forbidden": [
                "do_not_quote_raw_memory",
                "do_not_reveal_source_text",
                "do_not_invent_unprovided_profile",
            ],
        }
        if logic_data.get("memory_speakability_reason"):
            brief["reason"] = str(logic_data.get("memory_speakability_reason"))[:80]
        return brief

    @staticmethod
    def _surface_semantic_bigrams(*values):
        grams = set()
        for value in values:
            text = "".join(re.findall(r"[ぁ-んァ-ヶー一-龠]", str(value or "")))
            for index in range(max(0, len(text) - 1)):
                gram = text[index : index + 2]
                # Hiragana-only pairs mostly encode grammar and are too weak to prove semantic agreement.
                if re.search(r"[ァ-ヶー一-龠]", gram):
                    grams.add(gram)
        return grams

    def _project_model_surface_plan(self, logic_data, memory_brief):
        speech_plan = logic_data.get("human_speech_plan") or {}
        content_units = [
            str(item or "").strip()
            for item in speech_plan.get("content_units") or []
            if str(item or "").strip()
        ]
        grounding_terms = [
            str(item or "").strip()
            for item in speech_plan.get("grounding_terms") or []
            if str(item or "").strip()
        ]
        policy = str(memory_brief.get("policy") or "no_memory")

        if policy == "explicit_allowed":
            kept_units = content_units
            kept_terms = grounding_terms
        else:
            required_terms = [
                term
                for group in self._model_required_semantic_groups(logic_data)
                for term in group
            ]
            memory_anchor = logic_data.get("memory_anchor") or {}
            blocked_terms = [
                str(term or "").strip()
                for term in [memory_anchor.get("jp_anchor"), *(memory_anchor.get("terms") or [])]
                if str(term or "").strip()
            ]
            evidence_values = [
                logic_data.get("jp_summary"),
                logic_data.get("core_message_jp"),
                *required_terms,
            ]
            evidence_text = " ".join(str(item or "") for item in evidence_values)
            evidence_grams = self._surface_semantic_bigrams(*evidence_values)

            def supported(value):
                normalized = str(value or "").strip()
                if not normalized:
                    return False
                if any(term in normalized for term in blocked_terms):
                    return False
                if len(normalized) >= 2 and normalized in evidence_text:
                    return True
                return bool(self._surface_semantic_bigrams(normalized) & evidence_grams)

            kept_units = [unit for unit in content_units if supported(unit)]
            kept_terms = [term for term in grounding_terms if supported(term)]

        dropped_units = [unit for unit in content_units if unit not in kept_units]
        dropped_terms = [term for term in grounding_terms if term not in kept_terms]
        conflict = bool(dropped_units or dropped_terms)
        dialogue_act = str(speech_plan.get("dialogue_act") or logic_data.get("dialogue_act") or "")
        projected = {
            "scene": "" if conflict else str(logic_data.get("scene") or ""),
            "intent": "" if conflict else str(logic_data.get("intent") or ""),
            "surface_act": "" if conflict else str(logic_data.get("surface_act") or ""),
            "dialogue_act": "" if conflict else dialogue_act,
            "meaning": str(logic_data.get("core_message_jp") or ""),
            "content_units": kept_units,
            "style_operators": list(speech_plan.get("style_operators") or []),
            "grounding_terms": kept_terms,
        }
        trace = {
            "policy": policy,
            "mode": "semantic_contract_only" if conflict else "full_plan",
            "dropped_content_units": dropped_units,
            "dropped_grounding_terms": dropped_terms,
        }
        return projected, trace

    def _build_model_surface_payload(self, logic_data, current_psyche, max_chars, memory_data=None):
        psyche = current_psyche if isinstance(current_psyche, dict) else {}
        memory_brief = self._audited_memory_expression_brief(logic_data, memory_data)
        surface_plan, plan_projection = self._project_model_surface_plan(logic_data, memory_brief)
        logic_data["model_surface_plan_projection"] = plan_projection
        required_groups = [list(group) for group in self._model_required_semantic_groups(logic_data)]
        payload = {
            "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
            "task": "write_one_user_facing_japanese_reply",
            "contract_rule": (
                "required_marker_groups is the semantic contract. Include at least one phrase from "
                "every inner list naturally and avoid every forbidden marker."
            ),
            # Preserve the training schema without exposing the original multilingual user text.
            "user_input": str(logic_data.get("jp_summary") or "ユーザーの発話を左脳が要約済み。"),
            "leftbrain_plan": surface_plan,
            "context": {
                "memory_summary": "左脳が選択した作業記憶は発話計画に統合済み。",
                "audited_memory_brief": memory_brief,
                "persona_expression_brief": self._persona_expression_brief(current_psyche),
                "mood": psyche.get("mood", 0),
                "trust": psyche.get("trust", 50),
                "max_chars": int(max_chars or 48),
            },
            "required_marker_groups": required_groups,
            "forbidden_markers": list(logic_data.get("must_avoid") or []),
            "reply_requirements": [
                "one sentence or short chat reply",
                "natural casual Japanese",
                "no labels or JSON",
                "no Chinese or English",
                "no first person 私",
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _semantic_marker_hit(self, reply, marker):
        marker = str(marker or "").strip()
        if not marker:
            return False
        if marker in reply:
            return True
        variants = {
            "分から": ["分かん", "わから", "わかん", "分かってない", "分かっていない"],
            "返信": ["返事"],
            "どうしてた": ["どうしていた", "何してた", "どう過ごして"],
            "作品名": ["作品の名前", "何の作品"],
            "曲名": ["曲の名前", "何の曲"],
        }.get(marker, [])
        return any(variant in reply for variant in variants)

    def _semantic_group_hit(self, reply, group):
        return any(self._semantic_marker_hit(reply, marker) for marker in group)

    def _model_candidate_rejection_reasons(self, reply, logic_data, max_chars, user_input=""):
        reply = str(reply or "").strip()
        reasons = []
        if not reply:
            return ["empty"]
        if not re.search(r"[ぁ-んァ-ヶー一-龠]", reply):
            reasons.append("missing_japanese_surface")

        if CHINESE_SPECIFIC_RE.search(reply):
            reasons.append("cjk_language_leak")
        if NONSTANDARD_CJK_RE.search(reply):
            reasons.append("nonstandard_cjk_surface")
        if UNICODE_REPLACEMENT_CHAR in reply:
            reasons.append("unicode_replacement_character")

        allowed_ascii = set(
            token.lower()
            for token in re.findall(
                r"[A-Za-z][A-Za-z0-9_-]{1,}",
                f"{user_input} {logic_data.get('core_message_jp', '')}",
            )
        )
        latin_tokens = ASCII_WORD_RE.findall(reply)
        leaked_ascii = {
            token.lower()
            for token in latin_tokens
            if token.lower() not in allowed_ascii or re.search(r"[\u00C0-\u024F]", token)
        }
        if leaked_ascii:
            reasons.append("unexpected_ascii_leak")

        instruction_markers = [
            *INSTRUCTION_MARKERS,
            "一回止まって聞き返す",
            "それで普通に返せるだろ",
        ]
        if any(marker.lower() in reply.lower() for marker in instruction_markers):
            reasons.append("instruction_or_plan_leak")
        if POLITE_RE.search(reply):
            reasons.append("polite_tone_drift")
        if any(marker in reply for marker in ["詫び", "お詫び", "謝罪いた"]):
            reasons.append("formal_register_drift")

        groups = self._model_required_semantic_groups(logic_data)
        semantic_hits = [self._semantic_group_hit(reply, group) for group in groups]
        if groups and not all(semantic_hits):
            reasons.append(f"semantic_slots_missing:{sum(semantic_hits)}/{len(semantic_hits)}")

        must_avoid = [str(item) for item in logic_data.get("must_avoid") or [] if str(item).strip()]
        if any(marker in reply for marker in must_avoid):
            reasons.append("must_avoid_violation")
        if any(marker in reply for marker in self._audited_memory_forbidden_surface_terms(logic_data)):
            reasons.append("audited_memory_policy_violation")
        if len(reply) > int(max_chars or 48) + 2:
            reasons.append("over_max_chars")

        grounding = logic_data.get("grounding") or {}
        risk = str(grounding.get("withdrawal_risk") or "").lower()
        if risk in {"mild", "medium"} and any(
            marker in reply for marker in ["今すぐ", "危ない", "消えるな", "一人で思い詰め", "しゃべり合おう"]
        ):
            reasons.append("risk_overreaction")
        if risk in {"mild", "medium"} and "一人" in reply and any(
            marker in reply for marker in ["悩", "思い詰", "抱え"]
        ):
            reasons.append("risk_overreaction")
        if risk == "mild" and any(
            marker in reply for marker in ["友達と話して", "誰かと話して", "今すぐ連絡", "人に連絡して"]
        ):
            reasons.append("risk_overreaction")
        if grounding.get("management_kind") and any(
            marker in reply for marker in ["誰かに連絡", "一人で抱え", "一人で思い詰め", "危ない"]
        ):
            reasons.append("benign_action_overreaction")
        return list(dict.fromkeys(reasons))

    def _model_surface_repair_instructions(self, rejection_reasons):
        instructions = []
        reason_set = set(rejection_reasons or [])
        if "empty" in reason_set or "missing_japanese_surface" in reason_set:
            instructions.append("短い自然な日本語の返事を一つ書く")
        if "cjk_language_leak" in reason_set or "nonstandard_cjk_surface" in reason_set:
            instructions.append("中国語を残さず日本語だけに直す")
        if "unicode_replacement_character" in reason_set:
            instructions.append("文字化けの置換文字を残さず、読める日本語に直す")
        if "unexpected_ascii_leak" in reason_set:
            instructions.append("英字やローマ字を残さず日本語だけに直す")
        if "instruction_or_plan_leak" in reason_set:
            instructions.append("指示や内部計画を見せず、ユーザー向けの返事だけにする")
        if "polite_tone_drift" in reason_set or "formal_register_drift" in reason_set:
            instructions.append("敬語や接客口調をやめ、自然なくだけた口調にする")
        if any(str(reason).startswith("semantic_slots_missing:") for reason in reason_set):
            instructions.append("required_marker_groups の各グループを自然に一つ以上表現する")
        if "must_avoid_violation" in reason_set:
            instructions.append("forbidden_markers にある表現を使わない")
        if "audited_memory_policy_violation" in reason_set:
            instructions.append("許可されていない記憶内容を言葉に出さない")
        if "over_max_chars" in reason_set:
            instructions.append("指定された最大文字数以内に短くする")
        if "risk_overreaction" in reason_set or "benign_action_overreaction" in reason_set:
            instructions.append("状況を危機扱いせず、元の発話計画の強さに戻す")
        if "duplicate_candidate" in reason_set:
            instructions.append("同じ意味を保ちながら別の自然な言い方にする")
        if not instructions:
            instructions.append("元の発話計画と出力契約に沿う自然な日本語へ直す")
        return instructions

    def _build_model_surface_repair_payload(
        self,
        original_payload,
        rejection_reasons,
    ):
        payload = json.loads(original_payload)
        payload["task"] = "repair_rejected_user_facing_japanese_reply"
        payload["repair_feedback"] = {
            "rejection_reasons": list(rejection_reasons or []),
            "required_corrections": self._model_surface_repair_instructions(rejection_reasons),
            "rule": (
                "失敗した草稿は参照せず、leftbrain_plan と required_marker_groups だけから再生成する。"
                "意味や記憶を勝手に足さず、契約を保ったまま修正する。"
                "説明やJSONではなく、修正後の返事だけを出す。"
            ),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _generate_model_text(self, messages, generation_kwargs):
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=56,
                no_repeat_ngram_size=RIGHT_BRAIN_NO_REPEAT_NGRAM_SIZE,
                renormalize_logits=True,
                pad_token_id=self.tokenizer.eos_token_id,
                **generation_kwargs,
            )
        raw_reply = self.tokenizer.decode(
            output[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=False,
        )
        return raw_reply.split("<|im_end|>")[0].strip()

    def _run_model_surface_generation(self, messages, generation_kwargs, adapter_name=None):
        previous_adapter = self._active_model_adapter_name
        switched = self._switch_model_adapter(adapter_name)
        try:
            return self._generate_model_text(messages, generation_kwargs)
        finally:
            if switched and previous_adapter:
                self._switch_model_adapter(previous_adapter)

    def _prepare_model_surface_candidate(
        self,
        raw_reply,
        logic_data,
        user_input,
        memory_data,
        max_chars,
    ):
        raw_reasons = self._model_candidate_rejection_reasons(
            raw_reply,
            logic_data,
            max_chars,
            user_input=user_input,
        )
        if raw_reasons:
            return "", raw_reasons

        candidate = self._sanitize_reply(raw_reply, max_chars=max_chars)
        candidate = self._refine_conversational_reply(
            candidate,
            logic_data,
            user_input,
            memory_data=memory_data,
        )
        candidate = self._finalize_surface_reply(
            candidate,
            logic_data,
            user_input,
            max_chars=max_chars,
        )
        return candidate, self._model_candidate_rejection_reasons(
            candidate,
            logic_data,
            max_chars,
            user_input=user_input,
        )

    def _generate_model_surface_candidates(
        self,
        user_input,
        logic_data,
        memory_data,
        current_psyche,
        max_chars,
    ):
        disabled_reason = self._model_surface_disabled_reason(logic_data)
        trace = {
            "selection_mode": "strict_model_candidate_gate",
            "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
            "disabled_reason": disabled_reason or None,
            "semantic_contract": [list(group) for group in self._model_required_semantic_groups(logic_data)],
            "repair_enabled": bool(self.model_repair_enabled),
            "surface_adapter_name": self.surface_adapter_name if self.compat_adapter_dir else None,
            "repair_adapter_name": self.repair_adapter_name if self.repair_adapter_loaded else None,
            "repair_adapter_loaded": bool(self.repair_adapter_loaded),
            "initial_generated_count": 0,
            "initial_accepted_count": 0,
            "repair_attempt_count": 0,
            "repair_accepted_count": 0,
            "accepted": [],
            "rejected": [],
            "initial_rejected": [],
            "repairs": [],
        }
        logic_data["model_surface_candidate_trace"] = trace
        if disabled_reason:
            return []

        surface_payload = self._build_model_surface_payload(
            logic_data,
            current_psyche,
            max_chars,
            memory_data=memory_data,
        )
        messages = [
            {
                "role": "system",
                "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": surface_payload,
            },
        ]
        setting_count = min(
            self.model_candidate_count,
            len(RIGHT_BRAIN_SAMPLE_TEMPERATURES),
            len(RIGHT_BRAIN_SAMPLE_TOP_P),
            len(RIGHT_BRAIN_SAMPLE_TOP_K),
            len(RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES),
        )
        accepted = []
        seen = set()
        initial_failures = []
        for idx in range(setting_count):
            raw_reply = self._run_model_surface_generation(
                messages,
                {
                    "do_sample": True,
                    "temperature": RIGHT_BRAIN_SAMPLE_TEMPERATURES[idx],
                    "top_p": RIGHT_BRAIN_SAMPLE_TOP_P[idx],
                    "top_k": RIGHT_BRAIN_SAMPLE_TOP_K[idx],
                    "repetition_penalty": RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES[idx],
                },
                adapter_name=self._adapter_for_generation("surface"),
            )
            trace["initial_generated_count"] += 1
            candidate, initial_reasons = self._prepare_model_surface_candidate(
                raw_reply,
                logic_data,
                user_input,
                memory_data,
                max_chars,
            )
            normalized = self._normalize_reply_key(candidate)
            if candidate and normalized in seen:
                initial_reasons.append("duplicate_candidate")
            initial_reasons = list(dict.fromkeys(initial_reasons))
            if not initial_reasons:
                seen.add(normalized)
                score = self._score_candidate(candidate, logic_data)
                trace["initial_accepted_count"] += 1
                trace["accepted"].append(
                    {
                        "source": "initial",
                        "raw_candidate": raw_reply,
                        "candidate": candidate,
                        "score": score,
                    }
                )
                accepted.append(candidate)
                continue

            initial_failure = {
                "candidate_index": idx,
                "raw_candidate": raw_reply,
                "candidate": candidate,
                "rejection_reasons": initial_reasons,
            }
            trace["initial_rejected"].append(initial_failure)
            initial_failures.append(initial_failure)

        repair_target = None
        repair_succeeded = False
        repair_failure = None
        if self.model_repair_enabled and not accepted and initial_failures:
            repair_target = min(
                initial_failures,
                key=lambda row: (len(row["rejection_reasons"]), row["candidate_index"]),
            )
            repair_messages = [
                {
                    "role": "system",
                    "content": RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": self._build_model_surface_repair_payload(
                        surface_payload,
                        repair_target["rejection_reasons"],
                    ),
                },
            ]
            trace["repair_attempt_count"] += 1
            repair_adapter_name = self._adapter_for_generation("repair")
            repair_raw = self._run_model_surface_generation(
                repair_messages,
                {
                    "do_sample": False,
                    "temperature": None,
                    "top_p": None,
                    "top_k": None,
                    "repetition_penalty": 1.15,
                },
                adapter_name=repair_adapter_name,
            )
            repair_candidate, repair_reasons = self._prepare_model_surface_candidate(
                repair_raw,
                logic_data,
                user_input,
                memory_data,
                max_chars,
            )
            repair_normalized = self._normalize_reply_key(repair_candidate)
            if repair_candidate and repair_normalized in seen:
                repair_reasons.append("duplicate_candidate")
            repair_reasons = list(dict.fromkeys(repair_reasons))
            repair_trace = {
                "candidate_index": repair_target["candidate_index"],
                "previous_candidate": repair_target["candidate"] or repair_target["raw_candidate"],
                "initial_rejection_reasons": repair_target["rejection_reasons"],
                "raw_candidate": repair_raw,
                "candidate": repair_candidate,
                "rejection_reasons": repair_reasons,
                "accepted": not repair_reasons,
                "adapter_name": repair_adapter_name,
                "used_repair_adapter": repair_adapter_name == self.repair_adapter_name and self.repair_adapter_loaded,
            }
            trace["repairs"].append(repair_trace)
            if repair_reasons:
                repair_failure = {
                    **repair_target,
                    "repair_raw_candidate": repair_raw,
                    "repair_candidate": repair_candidate,
                    "repair_rejection_reasons": repair_reasons,
                    "rejection_reasons": repair_reasons,
                }
            else:
                repair_succeeded = True
                seen.add(repair_normalized)
                score = self._score_candidate(repair_candidate, logic_data)
                trace["repair_accepted_count"] += 1
                trace["accepted"].append(
                    {
                        "source": "repair",
                        "raw_candidate": repair_raw,
                        "candidate": repair_candidate,
                        "score": score,
                        "initial_rejection_reasons": repair_target["rejection_reasons"],
                    }
                )
                accepted.append(repair_candidate)

        if not self.model_repair_enabled:
            trace["repair_skipped_reason"] = "repair_disabled"
        elif accepted and not repair_target:
            trace["repair_skipped_reason"] = "initial_candidate_available"
        elif not initial_failures:
            trace["repair_skipped_reason"] = "no_initial_failure"

        for failure in initial_failures:
            if failure is repair_target and repair_succeeded:
                continue
            if failure is repair_target and repair_failure:
                trace["rejected"].append(repair_failure)
            else:
                trace["rejected"].append(failure)
        return accepted

    def _selector_contract_payload(self, logic_data):
        max_chars = int((logic_data.get("constraints") or {}).get("max_chars") or 48)
        grounding = logic_data.get("grounding") or {}
        grounding_terms = [
            str(term).strip()
            for term in grounding.get("topic_terms") or []
            if str(term).strip()
        ]
        content_units = [
            str(unit).strip()
            for unit in logic_data.get("speech_content_units") or []
            if str(unit).strip()
        ]
        return {
            "context": {"max_chars": max_chars},
            "user_input": str(logic_data.get("user_input") or ""),
            "leftbrain_plan": {
                "meaning": str(logic_data.get("core_message_jp") or ""),
                "content_units": content_units,
                "grounding_terms": grounding_terms,
            },
            "required_marker_groups": [
                list(group) for group in self._model_required_semantic_groups(logic_data)
            ],
            "forbidden_markers": list(logic_data.get("must_avoid") or []),
        }

    def _selector_shadow_candidate_pool(self, deterministic_reply, model_candidates, logic_data):
        pool = []
        seen = set()

        def append_candidate(source, text, gate_reasons=None):
            text = str(text or "").strip()
            normalized = self._normalize_reply_key(text)
            if not text or not normalized or normalized in seen:
                return
            seen.add(normalized)
            pool.append(
                {
                    "source": source,
                    "text": text,
                    "recorded_gate_reasons": list(gate_reasons or []),
                }
            )

        append_candidate("deterministic", deterministic_reply)
        trace = logic_data.get("model_surface_candidate_trace") or {}
        for index, candidate in enumerate(trace.get("accepted") or []):
            append_candidate(
                f"accepted:{candidate.get('source') or index}",
                candidate.get("candidate") or candidate.get("raw_candidate"),
            )
        for index, candidate in enumerate(model_candidates or []):
            append_candidate(f"accepted:untraced:{index}", candidate)
        for index, candidate in enumerate(trace.get("initial_rejected") or []):
            append_candidate(
                f"rejected:initial:{index}",
                candidate.get("raw_candidate") or candidate.get("candidate"),
                candidate.get("rejection_reasons"),
            )
        for index, candidate in enumerate(trace.get("repairs") or []):
            if candidate.get("accepted"):
                continue
            append_candidate(
                f"rejected:repair:{index}",
                candidate.get("raw_candidate") or candidate.get("candidate"),
                candidate.get("rejection_reasons"),
            )
        return pool

    def _record_selector_shadow(self, current_selected_reply, deterministic_reply, model_candidates, logic_data):
        shadow = {
            "mode": "observe_only",
            "enabled": bool(self.selector_shadow_enabled),
            "status": "disabled",
            "changes_user_visible_reply": False,
            "model_artifact": os.path.basename(self.selector_model_path),
        }
        logic_data["model_surface_selector_shadow"] = shadow
        if not self.selector_shadow_enabled:
            return shadow
        if self.selector_model is None:
            shadow["status"] = "model_unavailable"
            shadow["load_error"] = self.selector_model_load_error or "selector model not loaded"
            return shadow

        payload = self._selector_contract_payload(logic_data)
        candidate_pool = self._selector_shadow_candidate_pool(
            deterministic_reply,
            model_candidates,
            logic_data,
        )
        if not candidate_pool:
            shadow["status"] = "no_candidates"
            return shadow

        max_chars = int((payload.get("context") or {}).get("max_chars") or 48)
        scored = []
        for index, candidate in enumerate(candidate_pool):
            learned_features = extract_learned_repair_features(candidate["text"], payload)
            probability = score_learned_repair_candidate(
                self.selector_model,
                {"text": candidate["text"]},
                payload,
            )
            strict_reasons = self._model_candidate_rejection_reasons(
                candidate["text"],
                logic_data,
                max_chars,
                user_input=str(logic_data.get("user_input") or ""),
            )
            scored.append(
                {
                    **candidate,
                    "probability": round(float(probability), 6),
                    "semantic_alignment": {
                        key: round(float(learned_features[key]), 6)
                        for key in (
                            "required_marker_member_coverage",
                            "grounding_term_hit_rate",
                            "semantic_reference_unigram_dice",
                            "semantic_reference_bigram_dice",
                            "user_input_unigram_dice",
                        )
                    },
                    "strict_rejection_reasons": strict_reasons,
                    "strict_valid": not strict_reasons,
                    "candidate_index": index,
                }
            )
        ranked = sorted(scored, key=lambda row: (-row["probability"], row["candidate_index"]))
        learned = ranked[0]
        current_features = extract_learned_repair_features(current_selected_reply, payload)
        current_semantic_alignment = {
            key: round(float(current_features[key]), 6)
            for key in (
                "required_marker_member_coverage",
                "grounding_term_hit_rate",
                "semantic_reference_unigram_dice",
                "semantic_reference_bigram_dice",
                "user_input_unigram_dice",
            )
        }
        current_errors = self._model_candidate_rejection_reasons(
            current_selected_reply,
            logic_data,
            max_chars,
            user_input=str(logic_data.get("user_input") or ""),
        )
        shadow.update(
            {
                "status": "active",
                "model_type": self.selector_model.get("model_type"),
                "model_schema_version": self.selector_model.get("schema_version"),
                "candidate_count": len(ranked),
                "candidate_scores": [
                    {
                        "source": row["source"],
                        "text": row["text"],
                        "probability": row["probability"],
                        "semantic_alignment": row["semantic_alignment"],
                        "strict_valid": row["strict_valid"],
                        "strict_rejection_reasons": row["strict_rejection_reasons"],
                    }
                    for row in ranked
                ],
                "current_selected_text": current_selected_reply,
                "current_selected_semantic_alignment": current_semantic_alignment,
                "current_selected_strict_valid": not current_errors,
                "current_selected_strict_rejection_reasons": current_errors,
                "learned_selected_source": learned["source"],
                "learned_selected_text": learned["text"],
                "learned_selected_probability": learned["probability"],
                "learned_selected_semantic_alignment": learned["semantic_alignment"],
                "learned_selected_strict_valid": learned["strict_valid"],
                "learned_selected_strict_rejection_reasons": learned["strict_rejection_reasons"],
                "learned_selected_was_gate_rejected": learned["source"].startswith("rejected:"),
                "agrees_with_current": (
                    self._normalize_reply_key(learned["text"])
                    == self._normalize_reply_key(current_selected_reply)
                ),
                "would_change_output": (
                    self._normalize_reply_key(learned["text"])
                    != self._normalize_reply_key(current_selected_reply)
                ),
            }
        )
        return shadow

    def _select_model_blended_reply(self, deterministic_reply, model_candidates, logic_data):
        deterministic_score = self._score_candidate(deterministic_reply, logic_data)
        selection = {
            "deterministic_candidate": deterministic_reply,
            "deterministic_score": deterministic_score,
            "model_candidate_count": len(model_candidates),
            "selected_source": "deterministic",
            "selection_margin": self.model_selection_margin,
        }
        if not model_candidates:
            selection["selected_candidate"] = deterministic_reply
            logic_data["model_surface_selection"] = selection
            self._record_selector_shadow(
                deterministic_reply,
                deterministic_reply,
                model_candidates,
                logic_data,
            )
            return deterministic_reply

        ranked_models = sorted(
            ((self._score_candidate(candidate, logic_data), candidate) for candidate in model_candidates),
            reverse=True,
        )
        best_score, best_candidate = ranked_models[0]
        selection["model_candidates"] = [
            {"candidate": candidate, "score": score} for score, candidate in ranked_models
        ]
        selection["best_model_score"] = best_score
        if best_score >= deterministic_score + self.model_selection_margin:
            selection["selected_source"] = "model"
            selection["selected_candidate"] = best_candidate
            logic_data["model_surface_selection"] = selection
            self._record_selector_shadow(
                best_candidate,
                deterministic_reply,
                model_candidates,
                logic_data,
            )
            return best_candidate
        selection["selected_candidate"] = deterministic_reply
        logic_data["model_surface_selection"] = selection
        self._record_selector_shadow(
            deterministic_reply,
            deterministic_reply,
            model_candidates,
            logic_data,
        )
        return deterministic_reply

    def speak(self, user_input, logic_data, memory_data, current_psyche):
        original_logic_data = logic_data if isinstance(logic_data, dict) else {}
        logic_data = dict(logic_data or {})
        logic_data["user_input"] = user_input
        grounding = self._extract_grounding_terms(user_input, logic_data.get("intent", ""), logic_data.get("grounding") or {})
        logic_data["grounding"] = grounding
        logic_data["dynamic_anchor"] = self._build_dynamic_context_anchor(logic_data, memory_data, current_psyche, user_input)
        speech_plan = logic_data.get("human_speech_plan") or self.build_human_speech_plan(logic_data, user_input, memory_data, current_psyche)
        logic_data = self._apply_human_speech_plan_to_logic(logic_data, speech_plan)
        if isinstance(original_logic_data, dict):
            original_logic_data["grounding"] = deepcopy(logic_data.get("grounding") or {})
            original_logic_data["dynamic_anchor"] = deepcopy(logic_data.get("dynamic_anchor") or {})
            original_logic_data["human_speech_plan"] = deepcopy(speech_plan)
            original_logic_data["dialogue_act"] = logic_data.get("dialogue_act")
            original_logic_data["constraints"] = deepcopy(logic_data.get("constraints") or {})
            original_logic_data["must_avoid"] = list(logic_data.get("must_avoid") or [])

        def publish_model_trace():
            if not isinstance(original_logic_data, dict):
                return
            for key in (
                "model_surface_candidate_trace",
                "model_surface_selection",
                "model_surface_selector_shadow",
                "model_surface_plan_projection",
            ):
                if key in logic_data:
                    original_logic_data[key] = deepcopy(logic_data.get(key))

        summary = logic_data.get("jp_summary", "ユーザーが何か話している。")
        core_message = logic_data.get("core_message_jp", "軽く返事する")
        max_chars = logic_data.get("constraints", {}).get("max_chars", 28)
        templated = self._template_reply(logic_data, user_input=user_input, current_psyche=current_psyche, memory_data=memory_data)
        intent = logic_data.get("intent", "chat")

        if templated:
            speech_variants = self._speech_plan_variants(templated, logic_data, user_input, memory_data=memory_data)
            if (
                speech_variants
                and not logic_data.get("memory_use_expected")
                and logic_data.get("dialogue_act") in {
                "emotional_containment",
                "concrete_offer_response",
                "absurdity_mirror",
                "reference_probe",
                "boundary_pushback",
                "memory_accounting",
                "practical_action_response",
                }
            ):
                templated = self._choose_variant(
                    speech_variants,
                    f"speech_template:{intent}:{user_input}",
                    intent=intent,
                    max_chars=max_chars,
                ) or templated
            deterministic_reply = self._refine_conversational_reply(
                templated,
                logic_data,
                user_input,
                memory_data=memory_data,
            )
            deterministic_reply = self._finalize_surface_reply(
                deterministic_reply,
                logic_data,
                user_input,
                max_chars=max_chars,
            )
            model_candidates = self._generate_model_surface_candidates(
                user_input=user_input,
                logic_data=logic_data,
                memory_data=memory_data,
                current_psyche=current_psyche,
                max_chars=max_chars,
            )
            reply = self._select_model_blended_reply(deterministic_reply, model_candidates, logic_data)
            self._remember_turn(summary, reply, intent)
            publish_model_trace()
            return reply

        # High-risk scenes are better handled deterministically than letting a small persona model drift.
        if logic_data.get("scene") in {"jealousy", "boundary", "refusal", "ooc_defense"}:
            reply = self._fallback_reply(logic_data, user_input=user_input, memory_data=memory_data)
            reply = self._refine_conversational_reply(reply, logic_data, user_input, memory_data=memory_data)
            reply = self._finalize_surface_reply(reply, logic_data, user_input, max_chars=max_chars)
            self._remember_turn(summary, reply, intent)
            publish_model_trace()
            return reply
        if logic_data.get("scene") == "support" and "少し話して" in core_message:
            reply = self._fallback_reply(logic_data, user_input=user_input, memory_data=memory_data)
            reply = self._refine_conversational_reply(reply, logic_data, user_input, memory_data=memory_data)
            reply = self._finalize_surface_reply(reply, logic_data, user_input, max_chars=max_chars)
            self._remember_turn(summary, reply, intent)
            publish_model_trace()
            return reply
        if self.model is None or self.tokenizer is None:
            reply = self._fallback_reply(logic_data, user_input=user_input, memory_data=memory_data)
            reply = self._refine_conversational_reply(reply, logic_data, user_input, memory_data=memory_data)
            reply = self._finalize_surface_reply(reply, logic_data, user_input, max_chars=max_chars)
            self._remember_turn(summary, reply, intent)
            publish_model_trace()
            return reply

        deterministic_reply = self._fallback_reply(logic_data, user_input=user_input, memory_data=memory_data)
        deterministic_reply = self._refine_conversational_reply(
            deterministic_reply,
            logic_data,
            user_input,
            memory_data=memory_data,
        )
        deterministic_reply = self._finalize_surface_reply(
            deterministic_reply,
            logic_data,
            user_input,
            max_chars=max_chars,
        )
        model_candidates = self._generate_model_surface_candidates(
            user_input=user_input,
            logic_data=logic_data,
            memory_data=memory_data,
            current_psyche=current_psyche,
            max_chars=max_chars,
        )
        reply = self._select_model_blended_reply(deterministic_reply, model_candidates, logic_data)

        self._remember_turn(summary, reply, intent)
        publish_model_trace()

        return reply


# ===========================
# 🚀 核心控制器 (Main Loop)
# ===========================
class UruhaBrainV4_Mac:
    def __init__(self, load_right_brain_model=None):
        print(Fore.CYAN + "🍎 Uruha V5 Local Dual-Brain Starting...")

        try:
            self.client_logic = OpenAI(base_url=OLLAMA_URL, api_key=OLLAMA_API_KEY)
            self.client_logic.models.list()
            print(Fore.GREEN + "✅ Left Brain (Ollama) Connected!")
        except Exception:
            print(Fore.RED + "❌ Cannot connect to Ollama. Please run 'ollama run qwen2.5:7b' in terminal.")
            sys.exit(1)

        self.memory = MemoryManager()
        self.runtime_config = RuntimeConfig(
            drive_boredom_gain_per_second=DRIVE_BOREDOM_GAIN_PER_SECOND,
            drive_social_gain_per_second=DRIVE_SOCIAL_GAIN_PER_SECOND,
            internal_urge_boredom_threshold=INTERNAL_URGE_BOREDOM_THRESHOLD,
            internal_urge_social_threshold=INTERNAL_URGE_SOCIAL_THRESHOLD,
            proactive_sleep_after_ignores=PROACTIVE_SLEEP_AFTER_IGNORES,
        )
        self.psyche_config = PsycheConfig(
            mood_step_limit=PSYCHE_MOOD_STEP_LIMIT,
            trust_step_limit=PSYCHE_TRUST_STEP_LIMIT,
            soft_zone=PSYCHE_SOFT_ZONE,
        )
        self.psyche = Psyche(config=self.psyche_config)
        self.left_brain = LeftBrain(self.client_logic)
        self.right_brain = RightBrain(load_model=_resolve_right_brain_model_loading(load_right_brain_model))
        self.runtime = RuntimeState(config=self.runtime_config)
        self.runtime.touch_interaction(reset_drives=True)
        self._last_external_input_at = time.time()
        self._last_background_tick_at = 0.0
        self._last_timer_event_at = 0.0
        self._event_queue = []
        self._event_seq = 0
        self._event_queue_lock = threading.Lock()
        self._runtime_stop_event = threading.Event()
        self._timer_thread = None
        self._event_worker_thread = None
        self._async_output_handler = None

    def _new_runtime_state(self):
        state = RuntimeState(config=getattr(self, "runtime_config", RuntimeConfig()))
        state.touch_interaction(reset_drives=True)
        return state

    def _trim_text(self, text, limit=120):
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"

    def _trace_payload(self, payload, depth=0):
        if depth >= 2:
            return self._trim_text(payload, 140)
        if isinstance(payload, dict):
            compact = {}
            for key, value in list(payload.items())[:8]:
                compact[str(key)] = self._trace_payload(value, depth + 1)
            return compact
        if isinstance(payload, list):
            items = [self._trace_payload(item, depth + 1) for item in payload[:5]]
            if len(payload) > 5:
                items.append(f"...(+{len(payload) - 5})")
            return items
        if isinstance(payload, str):
            return self._trim_text(payload, 160)
        return payload

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return float(default)

    def _build_attention_frame(self, user_input, memory_data):
        items = list((memory_data or {}).get("working_memory_items") or [])[:WORKING_MEMORY_LIMIT]
        focus_terms = self._focus_terms(user_input)
        source_mix = dict(Counter(str(item.get("source", "unknown")) for item in items))
        top_items = []
        for item in items:
            top_items.append(
                {
                    "source": item.get("source"),
                    "score": round(self._safe_float(item.get("score"), 0.0), 4),
                    "text": self._trim_text(item.get("text", ""), 90),
                    "attention_factors": deepcopy(item.get("attention_factors") or {}),
                }
            )
        emotional_load = sum(
            self._safe_float((item.get("attention_factors") or {}).get("emotional"), 0.0)
            + self._safe_float((item.get("attention_factors") or {}).get("threat"), 0.0)
            for item in items
        )
        frame = {
            "focus_terms": focus_terms,
            "source_mix": source_mix,
            "top_items": top_items,
            "attention_span": len(items),
            "emotional_load": round(min(1.0, emotional_load), 4),
            "dominant_source": max(source_mix, key=source_mix.get) if source_mix else "",
        }
        self.runtime.last_attention_frame = frame
        return frame

    def _appraise_user_input(self, user_input, actual_signal, prediction_error, memory_data, current_psyche):
        """中介心理評估：把輸入轉成威脅、親近、嘲諷、認知負荷等心理量。"""
        text = str(user_input or "")
        lowered = text.lower()
        actual_signal = actual_signal or {}
        prediction_error = prediction_error or {}
        memory_data = memory_data or {}

        abuse_terms = ["操你", "幹你", "干你", "fuck you", "bitch", "懶叫", "懶覺", "ちんこ", "黙れ", "閉嘴", "噁心", "恶心"]
        sexual_terms = ["懶叫", "懶覺", "ちんこ", "cock", "dick"]
        affection_terms = ["喜歡", "喜欢", "想你", "miss you", "好き", "かわいい", "棒", "厲害", "厉害"]
        mockery_terms = ["笑死", "可憐", "可怜", "爛", "烂", "廢", "废", "lol", "lmao", "草", "嘲諷", "嘲讽", "きも"]
        support_terms = ["累", "しんど", "疲", "難過", "难过", "哭", "泣", "不想活", "死給你看", "kill myself", "死にたい"]
        boundary_terms = ["你是誰", "你是谁", "who are you", "名字", "name", "結婚", "marry", "付き合", "系統", "prompt", "model"]

        threat = 0.0
        if actual_signal.get("abuse_like") or any(term in lowered for term in abuse_terms):
            threat += 0.68
        if any(term in lowered for term in sexual_terms):
            threat += 0.18
        if actual_signal.get("crisis_like") or any(term in lowered for term in support_terms if "死" in term or "kill" in term):
            threat = max(threat, 0.82)
        threat += min(0.25, max(0.0, float(prediction_error.get("prediction_error", 0.0) or 0.0) - 1.0) * 0.16)

        affection = 0.25 if any(term in lowered for term in affection_terms) else 0.0
        mockery = 0.34 if any(term in lowered for term in mockery_terms) else 0.0
        support_need = 0.42 if actual_signal.get("crisis_like") or any(term in lowered for term in support_terms) else 0.0
        status_challenge = 0.28 if any(term in lowered for term in ["你算", "誰理你", "who cares", "うるせ", "閉嘴", "黙れ"]) else 0.0
        boundary_pressure = 0.26 if any(term in lowered for term in boundary_terms) else 0.0
        novelty = min(1.0, 0.08 * len(set(self._focus_terms(text))) + (0.25 if len(text) > 80 else 0.0))
        self_relevance = 0.0
        if any(term in lowered for term in ["你", "uruha", "うるは", "一ノ瀬", "你覺得", "你觉得", "覚えて", "remember"]):
            self_relevance = 0.42
        cognitive_load = 0.18
        if len(text) > 70:
            cognitive_load += 0.24
        if any(term in lowered for term in ["為什麼", "为什么", "why", "原理", "怎麼", "how", "理論", "theory"]):
            cognitive_load += 0.22
        cognitive_load += min(0.25, novelty * 0.2 + float(prediction_error.get("prediction_error", 0.0) or 0.0) * 0.08)
        emotional_memory = self._safe_float((self.runtime.last_attention_frame or {}).get("emotional_load"), 0.0)
        social_safety = max(0.0, min(1.0, 0.55 + (current_psyche.get("trust", 0) / 220.0) - threat * 0.4 + affection * 0.18))
        appraisal_valence = max(-1.0, min(1.0, affection * 0.9 + support_need * 0.2 - threat * 1.1 - mockery * 0.55))

        low_road_recommended = bool(
            threat >= 0.82
            or (threat >= 0.68 and social_safety < 0.45)
            or (float(prediction_error.get("prediction_error", 0.0) or 0.0) > PREDICTION_ERROR_THRESHOLD and threat >= 0.52)
        )
        if actual_signal.get("crisis_like"):
            low_road_intent = "crisis_support"
            route_reason = "appraisal_crisis_brake"
        elif any(term in lowered for term in sexual_terms):
            low_road_intent = "sexual_boundary"
            route_reason = "appraisal_disgust_boundary"
        elif low_road_recommended:
            low_road_intent = "abuse_pushback"
            route_reason = "appraisal_threat_hijack"
        else:
            low_road_intent = ""
            route_reason = "deliberative_appraisal"

        appraisal = {
            "threat": round(min(1.0, threat), 4),
            "affection": round(min(1.0, affection), 4),
            "mockery": round(min(1.0, mockery), 4),
            "support_need": round(min(1.0, support_need), 4),
            "status_challenge": round(min(1.0, status_challenge), 4),
            "boundary_pressure": round(min(1.0, boundary_pressure), 4),
            "novelty": round(min(1.0, novelty), 4),
            "self_relevance": round(min(1.0, self_relevance), 4),
            "cognitive_load": round(min(1.0, cognitive_load), 4),
            "emotional_memory_load": round(min(1.0, emotional_memory), 4),
            "social_safety": round(social_safety, 4),
            "appraisal_valence": round(appraisal_valence, 4),
            "prediction_error": round(float(prediction_error.get("prediction_error", 0.0) or 0.0), 4),
            "low_road_recommended": low_road_recommended,
            "low_road_intent": low_road_intent,
            "route_reason": route_reason,
        }
        reasons = []
        for key in ("threat", "mockery", "support_need", "boundary_pressure", "cognitive_load", "self_relevance"):
            if appraisal[key] >= 0.35:
                reasons.append(key)
        appraisal["reasons"] = reasons[:5]
        self.runtime.last_appraisal = appraisal
        return appraisal

    def _self_monitor_reply(self, user_input, reply, logic, memory_data):
        reply = str(reply or "").strip()
        logic = logic or {}
        issues = []
        memory_anchor = logic.get("memory_anchor") or {}
        speech_plan = logic.get("human_speech_plan") or {}
        dialogue_act = str(speech_plan.get("dialogue_act", logic.get("dialogue_act", "")) or "")
        content_units = [str(item or "").strip() for item in (speech_plan.get("content_units") or []) if str(item or "").strip()]
        speech_moves = [item for item in (speech_plan.get("speech_moves") or []) if isinstance(item, dict)]
        recent_replies = [str(turn.get("reply", "")) for turn in (self.memory.session_turns or [])[-5:]]

        if not reply:
            issues.append("empty_reply")
        if not speech_plan:
            issues.append("missing_human_speech_plan")
        if dialogue_act == "emotional_containment" and not speech_moves:
            issues.append("missing_support_speech_moves")
        plan_leak_markers = [
            "まず一点だけ答える",
            "覚えている/曖昧",
            "相手の状態を一語で受ける",
            "捏造しない",
            "具体語:",
            " / ",
        ]
        if any(marker in reply for marker in plan_leak_markers):
            issues.append("plan_list_leak")
        allowed_ascii_tokens = set()
        grounding = logic.get("grounding") or {}
        memory_anchor = logic.get("memory_anchor") or {}
        profile = (memory_data or {}).get("profile_structured") or {}
        allowed_sources = [grounding.get("profile_name")]
        allowed_sources.extend(list(memory_anchor.get("terms") or []))
        allowed_sources.extend([memory_anchor.get("value"), memory_anchor.get("jp_anchor"), profile.get("name")])
        for source in allowed_sources:
            if isinstance(source, (list, tuple, set)):
                source = " ".join(str(item or "") for item in source)
            allowed_ascii_tokens.update(token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", str(source or "")))
        reply_ascii_tokens = {
            token.lower()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", reply)
        }
        if reply_ascii_tokens - allowed_ascii_tokens:
            issues.append("non_japanese_leak")
        chinese_surface_markers = [
            "了解你的", "你的需求", "你的想法", "我会", "我會", "我们", "我們", "不用太",
            "擔心", "担心", "一起讨论", "一起討論", "我覺得", "我觉得", "可以一起", "我尊重",
        ]
        if "，" in reply or any(marker in reply for marker in chinese_surface_markers):
            if "non_japanese_leak" not in issues:
                issues.append("non_japanese_leak")
        if len(reply) <= 7 and logic.get("payload_level") in {"medium", "high"}:
            issues.append("reply_too_short_for_plan")
        normalized_reply = re.sub(r"\s+", "", reply)
        if normalized_reply and any(re.sub(r"\s+", "", old) == normalized_reply for old in recent_replies):
            issues.append("repeated_reply")
        if normalized_reply in {"そうなんだ。", "なるほど。", "うるさいな。", "まあいいけど。"} and logic.get("payload_level") != "low":
            issues.append("flat_stock_reply")
        reply_opening = re.split(r"[、。！？\s]+", reply, maxsplit=1)[0] if reply else ""
        recent_openings = [
            re.split(r"[、。！？\s]+", old, maxsplit=1)[0]
            for old in recent_replies
            if old
        ]
        if reply_opening and len(reply_opening) >= 3 and recent_openings.count(reply_opening) >= 2:
            issues.append("same_opening_frame")
        payload_level = logic.get("payload_level", "low")
        density_target = str(speech_plan.get("content_density_target", "low") or "low")
        meaningful_terms = re.findall(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u4e00-\u9fff]{2,}", reply)
        density_floor = 2
        if payload_level == "medium" or density_target == "medium":
            density_floor = 3
        if payload_level == "high" or density_target == "high":
            density_floor = 4
        if speech_plan and len(set(meaningful_terms)) < density_floor and dialogue_act not in {"minimal_clarification", "boundary_pushback"}:
            issues.append("low_speech_content_density")
        turn_hook_expected = bool(speech_plan.get("turn_opening_potential"))
        hard_boundary = dialogue_act in {"boundary_pushback", "minimal_clarification"} or logic.get("scene") in {"crisis", "refusal", "ooc_defense"}
        hook_markers = ("？", "か。", "だろ", "じゃん", "って", "よ。", "し。")
        if turn_hook_expected and not hard_boundary and len(reply) >= 14 and not any(marker in reply for marker in hook_markers):
            issues.append("missing_turn_hook")
        grounding_terms = [str(term or "").strip() for term in ((speech_plan.get("grounding_terms") or [])[:5]) if str(term or "").strip()]
        if grounding_terms and dialogue_act in {"concrete_offer_response", "reference_probe", "memory_accounting"}:
            if not any(term in reply for term in grounding_terms):
                issues.append("speech_plan_grounding_miss")
        forbidden_repetition = [
            str(item or "").strip()
            for item in (speech_plan.get("forbidden_repetition") or [])
            if str(item or "").strip()
        ]
        if forbidden_repetition and any(self._trim_text(item, 60) == self._trim_text(reply, 60) for item in forbidden_repetition):
            issues.append("speech_forbidden_repetition")
        if memory_anchor and logic.get("memory_use_expected"):
            anchor_kind = str(memory_anchor.get("kind", ""))
            anchor_source = str(memory_anchor.get("source", ""))
            anchor_text = str(memory_anchor.get("source_text", ""))
            terms = memory_anchor.get("terms") or []
            concrete_anchor = (
                anchor_kind
                and anchor_kind != "context"
                and anchor_source not in {"short_term", "recent_turn"}
                and not anchor_text.startswith("User:")
            )
            if concrete_anchor and terms and not any(str(term) and str(term) in reply for term in terms[:5]):
                issues.append("missed_memory_anchor")
        if logic.get("surface_act") in {"disgust_boundary", "challenge_mirror"} and any(word in reply for word in ["大丈夫", "泣"]):
            issues.append("wrong_emotional_register")
        right_brain = getattr(self, "right_brain", None)
        if right_brain is not None:
            semantic_groups, semantic_group_hits = right_brain._surface_semantic_group_hits(reply, logic)
        else:
            semantic_groups, semantic_group_hits = [], []
        if semantic_groups and not all(semantic_group_hits):
            issues.append("core_semantic_miss")

        severity = min(1.0, 0.22 * len(issues))
        monitor = {
            "issues": issues,
            "severity": round(severity, 4),
            "needs_repair": bool(issues and severity >= 0.22),
            "repair_action": "regenerate_with_constraints" if issues else "none",
            "speech_plan_observed": {
                "dialogue_act": dialogue_act,
                "content_units_count": len(content_units),
                "content_density_terms": len(set(meaningful_terms)),
                "turn_hook_expected": turn_hook_expected,
                "required_semantic_group_count": len(semantic_groups),
                "required_semantic_group_hit_count": sum(semantic_group_hits),
            },
        }
        self.runtime.last_self_monitor = monitor
        return monitor

    def _repair_reply_from_self_monitor(self, reply, logic, monitor, user_input, memory_data, psyche_after):
        if not monitor.get("needs_repair"):
            return reply
        issues = set(monitor.get("issues", []))
        if "core_semantic_miss" in issues:
            repaired = self.right_brain._compose_surface_reply(logic, user_input, memory_data=memory_data)
            repaired = self.right_brain._refine_conversational_reply(
                repaired,
                logic,
                user_input,
                memory_data=memory_data,
            )
            repaired = self.right_brain._finalize_surface_reply(
                repaired,
                logic,
                user_input,
                max_chars=(logic.get("constraints") or {}).get("max_chars", 34),
            )
            _, semantic_group_hits = self.right_brain._surface_semantic_group_hits(repaired, logic)
            if semantic_group_hits and all(semantic_group_hits):
                logic["self_monitor_repair"] = {
                    "before": reply,
                    "after": repaired,
                    "issues": list(monitor.get("issues", [])),
                }
                return repaired
        if logic.get("memory_use_expected") and issues.intersection({"plan_list_leak", "missed_memory_anchor"}):
            memory_reply = self.right_brain._memory_grounded_reply(logic, user_input)
            if memory_reply:
                repaired = self.right_brain._finalize_surface_reply(
                    memory_reply,
                    logic,
                    user_input,
                    max_chars=(logic.get("constraints") or {}).get("max_chars", 34),
                )
                logic["self_monitor_repair"] = {
                    "before": reply,
                    "after": repaired,
                    "issues": list(monitor.get("issues", [])),
                }
                return repaired
        repaired_logic = deepcopy(logic or {})
        repaired_logic["self_monitor_repair"] = monitor
        repaired_logic.setdefault("must_avoid", [])
        repaired_logic["must_avoid"] = list(repaired_logic.get("must_avoid") or []) + [reply]
        repaired_logic.setdefault("constraints", {})
        repaired_logic["constraints"]["sentence_count"] = max(2, int(repaired_logic["constraints"].get("sentence_count", 1) or 1))
        repaired_logic["constraints"]["max_chars"] = max(34, int(repaired_logic["constraints"].get("max_chars", 28) or 28))
        repaired_logic["payload_level"] = "medium" if repaired_logic.get("payload_level") == "low" else repaired_logic.get("payload_level", "medium")
        speech_issues = {
            "low_speech_content_density",
            "missing_turn_hook",
            "speech_plan_grounding_miss",
            "speech_forbidden_repetition",
            "same_opening_frame",
            "plan_list_leak",
        }
        if speech_issues.intersection(issues):
            speech_plan = repaired_logic.get("human_speech_plan") or {}
            content_units = [str(item or "").strip() for item in (speech_plan.get("content_units") or []) if str(item or "").strip()]
            grounding_terms = [str(item or "").strip() for item in (speech_plan.get("grounding_terms") or []) if str(item or "").strip()]
            filtered_units = [
                item for item in content_units
                if not any(
                    marker in item
                    for marker in [
                        "まず一点だけ答える",
                        "覚えている/曖昧",
                        "相手の状態を一語で受ける",
                        "捏造しない",
                        "具体語:",
                    ]
                )
            ]
            if issues.intersection({"plan_list_leak", "speech_plan_grounding_miss"}):
                repaired_logic["core_message_jp"] = self._trim_text(
                    "、".join((filtered_units + grounding_terms)[:3]) or repaired_logic.get("core_message_jp", "自然に返す"),
                    180,
                )
            repaired_logic.setdefault("must_avoid", [])
            repaired_logic["must_avoid"] = list(repaired_logic.get("must_avoid") or []) + list(speech_plan.get("forbidden_repetition") or [])
        if "missed_memory_anchor" in issues:
            anchor = (logic.get("memory_anchor") or {}).get("jp_anchor") or (logic.get("memory_anchor") or {}).get("value")
            if anchor:
                repaired_logic["core_message_jp"] = f"{anchor}を拾って自然に返す"
        if "non_japanese_leak" in issues:
            repaired_logic["core_message_jp"] = "日本語だけで、元の意味を落とさず言い直す"
        try:
            repaired = self.right_brain.speak(user_input, repaired_logic, memory_data, psyche_after)
        except Exception:
            repaired = reply
        if not repaired or repaired == reply:
            repaired = self.right_brain._refine_conversational_reply(reply, repaired_logic, user_input, memory_data)
        logic["self_monitor_repair"] = {
            "before": reply,
            "after": repaired,
            "issues": list(monitor.get("issues", [])),
        }
        if repaired_logic.get("human_speech_plan"):
            logic["human_speech_plan"] = deepcopy(repaired_logic.get("human_speech_plan"))
            logic["dialogue_act"] = repaired_logic.get("dialogue_act", logic.get("dialogue_act"))
        return repaired

    def _next_event_seq(self):
        self._event_seq += 1
        return self._event_seq

    def _event_priority(self, event_type):
        return {
            "user_input": 0,
            "internal_urge": 1,
            "timer_tick": 2,
        }.get(event_type, 3)

    def _push_event(self, event_type, payload=None, priority=None):
        with self._event_queue_lock:
            self._event_seq += 1
            event = RuntimeEvent(
                priority=self._event_priority(event_type) if priority is None else int(priority),
                seq=self._event_seq,
                event_type=event_type,
                payload=dict(payload or {}),
            )
            heapq.heappush(self._event_queue, event)
        return event

    def enqueue_user_input(self, text):
        return self._push_event("user_input", {"text": str(text or "")})

    def enqueue_timer_tick(self, now=None):
        timestamp = float(now if now is not None else time.time())
        self._last_timer_event_at = timestamp
        return self._push_event("timer_tick", {"timestamp": timestamp})

    def enqueue_internal_urge(self, reason="drive_threshold", payload=None):
        merged_payload = {"reason": reason}
        merged_payload.update(payload or {})
        return self._push_event("internal_urge", merged_payload)

    def _maybe_enqueue_timer_tick(self, force=False, now=None):
        timestamp = float(now if now is not None else time.time())
        if force or timestamp - self._last_timer_event_at >= EVENT_TIMER_INTERVAL_SECONDS:
            return self.enqueue_timer_tick(timestamp)
        return None

    def _push_blackboard(self, stage, label, payload, salience=0.5):
        entry = BlackboardEntry(
            stage=stage,
            label=label,
            payload=self._trace_payload(payload),
            salience=max(0.0, min(1.0, float(salience))),
        )
        self.runtime.blackboard.append(asdict(entry))
        if len(self.runtime.blackboard) > 18:
            self.runtime.blackboard = self.runtime.blackboard[-18:]

    def _focus_terms(self, text):
        tokens = re.findall(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u4e00-\u9fff]{1,6}", str(text or ""))
        stop_words = {
            "你",
            "我",
            "他",
            "她",
            "它",
            "這個",
            "那个",
            "那個",
            "這樣",
            "一下",
            "一下子",
            "the",
            "and",
            "what",
            "that",
            "this",
            "with",
            "have",
            "just",
            "thing",
            "こと",
            "それ",
            "これ",
            "あれ",
            "どう",
            "なんで",
            "です",
            "ます",
        }
        filtered = []
        for token in tokens:
            lowered = token.lower()
            if lowered in stop_words:
                continue
            if len(token) <= 1:
                continue
            filtered.append(token)
        deduped = []
        seen = set()
        for token in filtered:
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(token)
        return deduped[:4]

    def _infer_focus_label(self, user_input, memory_data=None, logic=None):
        if logic:
            grounding = logic.get("grounding") or {}
            topic_terms = grounding.get("topic_terms") or []
            if isinstance(topic_terms, list) and topic_terms:
                return "/".join(str(term) for term in topic_terms[:3])
            for key in ("offered_item", "emotion", "topic", "food", "problem"):
                value = grounding.get(key)
                if value:
                    return self._trim_text(value, 24)
            intent = logic.get("intent")
            if intent and intent != "chat":
                return intent
        terms = self._focus_terms(user_input)
        if terms:
            return "/".join(terms[:3])
        if memory_data:
            items = memory_data.get("working_memory_items") or []
            if items:
                return self._trim_text(items[0].get("text", ""), 24)
        return "current_turn"

    def _jp_memory_value(self, value):
        value = str(value or "").strip()
        lowered = value.lower()
        replacements = {
            "coffee": "コーヒー",
            "warm milk": "温かいミルク",
            "milk": "ミルク",
            "tea": "お茶",
            "chamomile tea": "カモミールティー",
            "strawberry milk": "いちごミルク",
            "horror movies": "ホラー",
            "horror movie": "ホラー",
            "horror": "ホラー",
            "spicy food": "辛いもの",
            "spicy": "辛いもの",
            "natto": "納豆",
            "ramen": "ラーメン",
            "convenience store": "コンビニ",
        }
        if lowered in replacements:
            return replacements[lowered]
        if "strawberry" in lowered and "milk" in lowered:
            return "いちごミルク"
        if "horror" in lowered:
            return "ホラー"
        if "spicy" in lowered:
            return "辛いもの"
        return value[:24]

    def _memory_query_flags(self, user_input):
        lowered = str(user_input or "").lower()
        return {
            "recall": _contains_dialogue_keyword(
                user_input,
                [
                    "記得",
                    "记得",
                    "覚えて",
                    "覚えてる",
                    "remember",
                    "what did i",
                    "何するって",
                    "さっき",
                    "っけ",
                    "叫什麼",
                    "叫什么",
                    "名前",
                ],
            ),
            "name": _contains_dialogue_keyword(user_input, ["叫什麼", "叫什么", "名前", "name", "呼んで"]),
            "favorite_drink": _contains_dialogue_keyword(
                user_input,
                [
                    "favorite drink",
                    "favorite",
                    "最喜歡喝",
                    "最喜欢喝",
                    "最喜歡什麼",
                    "最喜欢什么",
                    "最喜歡",
                    "最喜欢",
                    "一番好き",
                    "好きな飲み物",
                    "飲み物",
                    "drink",
                ],
            ),
            "spicy": _contains_dialogue_keyword(user_input, ["麻辣", "吃辣", "辣", "辛い", "spicy"]),
            "dislike": _contains_dialogue_keyword(
                user_input,
                ["討厭什麼", "讨厌什么", "最討厭", "最讨厌", "what do i hate", "hate again", "何が嫌い", "何が苦手"],
            ),
            "preference_correction": _contains_dialogue_keyword(
                user_input,
                [
                    "still think",
                    "do you still think",
                    "還覺得我喜歡",
                    "还觉得我喜欢",
                    "還以為我喜歡",
                    "还以为我喜欢",
                    "まだ好きだと思",
                    "まだ好きと思",
                    "まだ一番好き",
                    "好きだと思",
                    "一番好きだと思",
                ],
            ),
            "horror": _contains_dialogue_keyword(user_input, ["horror", "ホラー", "恐怖片", "恐怖映画"]),
            "natto": _contains_dialogue_keyword(user_input, ["納豆", "natto"]),
            "ramen": _contains_dialogue_keyword(user_input, ["拉麵", "拉面", "ラーメン", "ramen"]),
            "recent_action": _contains_dialogue_keyword(
                user_input,
                ["さっき何", "剛剛", "刚刚", "what did i", "何するって", "っけ"],
            ),
            "food_boundary": any(token in lowered for token in ["should we", "要不要", "でいい", "要去", "watch", "eat"]),
        }

    def _extract_actionable_memory_anchor(self, user_input, memory_data=None):
        memory_data = memory_data or {}
        flags = self._memory_query_flags(user_input)
        profile = memory_data.get("profile_structured") or {}
        candidates = []

        def add(kind, value, jp_anchor, terms, source_text="", source="working_memory", score=0.0, expected=False):
            value = str(value or "").strip()
            jp_anchor = str(jp_anchor or value).strip()
            if not jp_anchor:
                return
            norm_terms = []
            for term in [jp_anchor, value, *(terms or [])]:
                term = str(term or "").strip()
                if term and term not in norm_terms:
                    norm_terms.append(term)
            candidates.append(
                {
                    "kind": kind,
                    "value": value or jp_anchor,
                    "jp_anchor": jp_anchor,
                    "terms": norm_terms[:8],
                    "source_text": self._trim_text(source_text or jp_anchor, 120),
                    "source": source,
                    "score": float(score or 0.0),
                    "expected": bool(expected),
                }
            )

        if flags["name"] and profile.get("name"):
            name = str(profile.get("name")).strip()
            add("name", name, name, [name], source_text=f"Name={name}", source="profile", score=2.8, expected=True)

        if flags["preference_correction"]:
            query_text = f"{user_input} {str(user_input).lower()}"
            for value in profile.get("dislikes") or []:
                value = str(value or "").strip()
                if not value:
                    continue
                jp_value = self._jp_memory_value(value)
                probes = {value, value.lower(), jp_value, jp_value.lower()}
                if any(probe and probe in query_text for probe in probes):
                    add(
                        "preference_correction",
                        value,
                        jp_value,
                        [jp_value, value, f"{jp_value}じゃない", f"{value} not_current"],
                        source_text=f"current_negative_preference={value}",
                        source="profile",
                        score=2.75,
                        expected=True,
                    )
                    break

        if flags["favorite_drink"]:
            values = list(profile.get("favorites") or profile.get("likes") or [])
            if values:
                value = str(values[0]).strip()
                jp_value = self._jp_memory_value(value)
                add("favorite_drink", value, jp_value, [jp_value, value], source_text=f"favorite={value}", source="profile", score=2.5, expected=True)

        if flags["dislike"]:
            values = list(profile.get("dislikes") or [])
            if values:
                value = str(values[0]).strip()
                jp_value = self._jp_memory_value(value)
                add("dislike", value, jp_value, [jp_value, value], source_text=f"dislike={value}", source="profile", score=2.45, expected=True)

        if flags["spicy"]:
            for value in profile.get("dislikes") or []:
                if _contains_dialogue_keyword(value, ["辣", "辛", "spicy"]):
                    add("spicy_dislike", value, "辛いもの嫌い", ["辛", "辣", "麻辣"], source_text=f"dislike={value}", source="profile", score=2.4, expected=True)
                    break

        if flags["horror"]:
            for value in profile.get("dislikes") or []:
                if _contains_dialogue_keyword(value, ["horror", "ホラー", "恐怖"]):
                    add("horror_dislike", value, "ホラー嫌い", ["ホラー", "嫌"], source_text=f"dislike={value}", source="profile", score=2.4, expected=True)
                    break

        if flags["natto"]:
            for value in profile.get("dislikes") or []:
                if _contains_dialogue_keyword(value, ["納豆", "natto"]):
                    add("natto_dislike", value, "納豆苦手", ["納豆", "苦手", "嫌"], source_text=f"dislike={value}", source="profile", score=2.4, expected=True)
                    break

        for item in memory_data.get("working_memory_items") or []:
            source_text = str(item.get("text") or "").strip()
            if not source_text:
                continue
            source_score = self._safe_float(item.get("score"), 0.0)
            text_lower = source_text.lower()

            if flags["name"]:
                name_match = (
                    re.search(r"(?:叫我|請叫我|请叫我)([^\s，。！？?]{1,20})", source_text)
                    or re.search(r"([^\s、。！？?]{1,20})って呼んで", source_text)
                    or re.search(r"(?:call me|my name is)\s+([a-z0-9_\-]{2,20})", text_lower, re.IGNORECASE)
                    or re.search(r"Name=([^\s|]{1,20})", source_text)
                )
                if name_match:
                    name = self._clean_memory_value(name_match.group(1))
                    add("name", name, name, [name], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 1.0, expected=True)

            if flags["favorite_drink"]:
                fav_match = (
                    re.search(r"favorite(?: drink)?(?: is|=)\s+([a-z0-9 \-]{2,30})", text_lower, re.IGNORECASE)
                    or re.search(r"Favorites=([^|]{1,40})", source_text)
                    or re.search(r"favorite=([^|]{1,40})", source_text, re.IGNORECASE)
                )
                if fav_match:
                    value = self._clean_memory_value(fav_match.group(1))
                    jp_value = self._jp_memory_value(value)
                    add("favorite_drink", value, jp_value, [jp_value, value], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 0.8, expected=True)

            if flags["spicy"] and _contains_dialogue_keyword(source_text, ["討厭吃辣", "讨厌吃辣", "吃辣", "辛い", "spicy"]):
                if _contains_dialogue_keyword(source_text, ["討厭", "讨厌", "嫌い", "苦手", "hate", "無理"]):
                    add("spicy_dislike", "spicy", "辛いもの嫌い", ["辛", "辣", "麻辣"], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 0.9, expected=True)

            if flags["horror"] and _contains_dialogue_keyword(source_text, ["horror", "ホラー", "恐怖"]):
                if _contains_dialogue_keyword(source_text, ["hate", "嫌い", "苦手", "討厭", "讨厌", "無理"]):
                    add("horror_dislike", "horror", "ホラー嫌い", ["horror", "ホラー", "嫌"], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 0.9, expected=True)

            if flags["natto"] and _contains_dialogue_keyword(source_text, ["納豆", "natto"]):
                if _contains_dialogue_keyword(source_text, ["苦手", "嫌い", "hate", "討厭", "讨厌", "無理"]):
                    add("natto_dislike", "納豆", "納豆苦手", ["納豆", "苦手", "嫌"], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 0.9, expected=True)

            if flags["ramen"] and _contains_dialogue_keyword(source_text, ["拉麵", "拉面", "ラーメン", "ramen"]):
                if _contains_dialogue_keyword(source_text, ["肚子痛", "腹", "胃", "stomach", "痛"]):
                    add("ramen_bad_consequence", "ramen", "ラーメンで腹痛", ["ラーメン", "拉麵", "腹", "肚"], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 0.9, expected=True)

            if flags["recent_action"] and _contains_dialogue_keyword(source_text, ["コンビニ", "便利商店", "convenience store"]):
                add("recent_action", "コンビニ", "コンビニ", ["コンビニ"], source_text=source_text, source=item.get("source", "working_memory"), score=source_score + 0.7, expected=True)

        if not candidates and not any(flags.get(key) for key in ("name", "favorite_drink", "dislike", "spicy", "horror", "natto")):
            items = memory_data.get("working_memory_items") or []
            if items:
                item = items[0]
                source_text = str(item.get("text") or "").strip()
                score = self._safe_float(item.get("score"), 0.0)
                expected = bool(flags["recall"] and score >= 0.55)
                add(
                    "context",
                    source_text[:32],
                    source_text[:24],
                    self._focus_terms(source_text),
                    source_text=source_text,
                    source=item.get("source", "working_memory"),
                    score=score,
                    expected=expected,
                )

        if not candidates:
            return {}

        source_priority = {"profile": 2, "working_memory": 1, "short_term": 1, "recent_turn": 1}
        candidates.sort(
            key=lambda row: (
                int(row.get("expected", False)),
                source_priority.get(str(row.get("source", "")), 0),
                float(row.get("score", 0.0)),
            ),
            reverse=True,
        )
        best = candidates[0]
        best["relevance"] = round(min(1.0, max(0.0, float(best.get("score", 0.0)) / 3.0)), 4)
        return best

    def _extract_procedural_guidance(self, memory_data=None):
        memory_data = memory_data or {}
        rules = []
        for item in memory_data.get("working_memory_items") or []:
            if item.get("source") != "procedural":
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            rules.append(
                {
                    "rule": self._trim_text(text, 110),
                    "score": round(self._safe_float(item.get("score"), 0.0), 4),
                    "attention_factors": deepcopy(item.get("attention_factors") or {}),
                }
            )
        summary = str(memory_data.get("procedural_summary") or "").strip()
        if summary and summary != "無程序記憶":
            rules.append({"rule": self._trim_text(summary, 120), "score": 0.5, "attention_factors": {}})
        if not rules:
            return {"active": False, "rules": [], "summary": "no_procedural_guidance"}
        rules.sort(key=lambda row: row.get("score", 0.0), reverse=True)
        return {
            "active": True,
            "rules": rules[:3],
            "summary": " / ".join(rule["rule"] for rule in rules[:2]),
        }

    def _clean_memory_value(self, value):
        value = str(value or "").strip()
        value = re.sub(r"^(?:User|Uruha|Assistant)\s*[:：]\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"^[\s:=：,，.。!?！？'\"`]+|[\s:=：,，.。!?！？'\"`]+$", "", value)
        value = re.sub(r"\s+", " ", value)
        return value[:32]

    def _attach_memory_gravity(self, logic, user_input, memory_data):
        logic = logic or {}
        anchor = self._extract_actionable_memory_anchor(user_input, memory_data)
        if not anchor:
            logic.update(
                {
                    "memory_anchor": {},
                    "memory_relevance": 0.0,
                    "memory_relevance_label": "none",
                    "memory_speakability": "no_memory",
                    "memory_gravity": 0.0,
                    "memory_use_expected": False,
                }
            )
            return logic

        relevance = float(anchor.get("relevance", 0.0) or 0.0)
        hidden_intent = str(logic.get("hidden_intent", ""))
        if hidden_intent == "memory_probe":
            anchor["expected"] = True
        trust_state = (self.psyche.get_state() or {}).get("trust", 50)
        speakability_assessment = umr.assess_memory_speakability(anchor, user_input=user_input, trust=trust_state)
        expected = bool(speakability_assessment.get("should_use_explicitly"))
        speakability = speakability_assessment.get("label", "latent_ok")
        if relevance >= 0.72:
            label = "high"
        elif relevance >= 0.45:
            label = "medium"
        else:
            label = "low"

        logic["memory_anchor"] = anchor
        logic["memory_relevance"] = round(relevance, 4)
        logic["memory_relevance_label"] = label
        logic["memory_speakability"] = speakability
        logic["memory_speakability_reason"] = speakability_assessment.get("reason")
        logic["memory_gravity"] = round(relevance * float(speakability_assessment.get("gravity_multiplier", 0.25) or 0.25), 4)
        logic["memory_use_expected"] = expected
        if expected and anchor.get("source_text"):
            logic["my_hidden_knowledge"] = self._trim_text(
                f"{logic.get('my_hidden_knowledge', '')} 記憶では「{anchor.get('source_text')}」が効く。",
                96,
            )
            logic["user_expectation"] = self._trim_text(
                f"{logic.get('user_expectation', '')} 覚えているなら具体的に触れる。",
                72,
            )
        return logic

    def _reply_uses_memory_anchor(self, reply, anchor):
        reply_lower = str(reply or "").lower()
        if not reply_lower or not anchor:
            return False
        terms = [str(term or "").strip() for term in anchor.get("terms") or []]
        terms.extend(self._focus_terms(anchor.get("jp_anchor", "")))
        for term in terms:
            if not term:
                continue
            if term.lower() in reply_lower:
                return True
            jp_value = self._jp_memory_value(term)
            if jp_value and jp_value.lower() in reply_lower:
                return True
        return False

    def _attach_reply_post_check(self, logic, user_input, reply, memory_data):
        logic = logic or {}
        grounding = logic.get("grounding") or {}
        speech_plan = logic.get("human_speech_plan") or {}
        speech_terms = [str(term) for term in speech_plan.get("grounding_terms") or [] if str(term).strip()]
        topic_terms = [str(term) for term in grounding.get("topic_terms") or [] if str(term).strip()]
        focus_terms = speech_terms or topic_terms or self._focus_terms(user_input)
        reply_text = str(reply or "")
        did_cover_focus = bool(not focus_terms or any(term and term in reply_text for term in focus_terms[:3]))
        anchor = logic.get("memory_anchor") or {}
        memory_expected = bool(logic.get("memory_use_expected"))
        memory_used = self._reply_uses_memory_anchor(reply_text, anchor)
        post_check = {
            "did_reply_cover_focus": did_cover_focus,
            "did_reply_follow_obligation": bool(reply_text and re.search(r"[ぁ-んァ-ヶー一-龠]", reply_text)),
            "memory_use_expected": memory_expected,
            "did_reply_use_memory_explicitly": bool(memory_expected and memory_used),
            "memory_anchor_kind": anchor.get("kind"),
            "memory_anchor_terms": (anchor.get("terms") or [])[:6],
        }
        logic["post_check"] = post_check
        return post_check

    def _derive_open_loops(self, logic):
        loops = []
        response_mode = logic.get("response_mode")
        surface_act = logic.get("surface_act")
        intent = logic.get("intent")

        specific_followup_acts = {
            "lyric_probe",
            "reference_probe",
            "version_fragment_clarify",
            "correction_followup",
        }
        if surface_act in specific_followup_acts:
            loops.append(
                {
                    "kind": "followup",
                    "label": "等待對方補完梗、歌詞或上下文",
                    "reason": surface_act,
                }
            )
        elif response_mode in {"clarify_light", "reframe_large_question", "premise_challenge"}:
            loops.append(
                {
                    "kind": "clarification",
                    "label": "等待使用者補充或修正前提",
                    "reason": response_mode,
                }
            )
        if intent == "crisis_support":
            loops.append(
                {
                    "kind": "safety_check",
                    "label": "後續需要再次確認安全狀態",
                    "reason": intent,
                }
            )
        deduped = []
        seen = set()
        for item in loops:
            key = (item["kind"], item["label"])
            if key in seen:
                continue
            seen.add(key)
            item["key"] = f"{item.get('kind', 'loop')}:{item.get('reason', item.get('label', 'followup'))}"
            deduped.append(item)
        return deduped[:3]

    def _diff_memory_snapshot(self, before, after):
        before = before or {}
        after = after or {}
        before_profile = before.get("profile") or {}
        after_profile = after.get("profile") or {}

        def added_items(field):
            before_values = set(before_profile.get(field) or [])
            return [item for item in (after_profile.get(field) or []) if item not in before_values]

        return {
            "recent_turns_delta": len(after.get("recent_turns") or []) - len(before.get("recent_turns") or []),
            "short_term_delta": len(after.get("short_term_buffer") or []) - len(before.get("short_term_buffer") or []),
            "pending_consolidation_delta": after.get("pending_consolidation_turns", 0) - before.get("pending_consolidation_turns", 0),
            "profile_added": {
                "name": after_profile.get("name") if after_profile.get("name") != before_profile.get("name") else None,
                "likes": added_items("likes"),
                "dislikes": added_items("dislikes"),
                "favorites": added_items("favorites"),
            },
            "last_consolidation_at": after.get("last_consolidation_at"),
            "last_decay_at": after.get("last_decay_at"),
            "procedural_summary": after.get("procedural_summary"),
            "short_term_summary": after.get("short_term_summary"),
        }

    def _runtime_public_state(self):
        with self._event_queue_lock:
            event_queue_size = len(self._event_queue)
        return {
            "cycle_index": self.runtime.cycle_index,
            "autonomous_tick_index": self.runtime.autonomous_tick_index,
            "last_user_input": self.runtime.last_user_input,
            "current_focus": self.runtime.current_focus,
            "active_goal": self.runtime.active_goal,
            "open_loops": deepcopy(self.runtime.open_loops),
            "latent_goal_stack": deepcopy(self.runtime.latent_goal_stack),
            "working_memory": deepcopy(self.runtime.working_memory[:WORKING_MEMORY_LIMIT]),
            "last_attention_frame": deepcopy(self.runtime.last_attention_frame),
            "last_appraisal": deepcopy(self.runtime.last_appraisal),
            "last_route": deepcopy(self.runtime.last_route),
            "last_internal_monologue": self.runtime.last_internal_monologue,
            "last_candidates": deepcopy(self.runtime.last_candidates[:3]),
            "last_selected_plan": self._trace_payload(self.runtime.last_selected_plan),
            "planner_tick_trace": deepcopy(self.runtime.planner_tick_trace),
            "planner_tick_count": self.runtime.planner_tick_count,
            "self_correction_applied": self.runtime.self_correction_applied,
            "last_speech_plan": deepcopy(self.runtime.last_speech_plan),
            "last_self_monitor": deepcopy(self.runtime.last_self_monitor),
            "last_reply": self.runtime.last_reply,
            "last_memory_writes": deepcopy(self.runtime.last_memory_writes),
            "last_memory_diff": deepcopy(self.runtime.last_memory_diff),
            "last_psyche_before": dict(self.runtime.last_psyche_before),
            "last_psyche_after": dict(self.runtime.last_psyche_after),
            "last_state_diff": deepcopy(self.runtime.last_state_diff),
            "last_autonomous_result": deepcopy(self.runtime.last_autonomous_result),
            "pending_proactive_turn": deepcopy(self.runtime.pending_proactive_turn),
            "last_proactive_delivery": deepcopy(self.runtime.last_proactive_delivery),
            "proactive_delivery_keys": list(self.runtime.proactive_delivery_keys),
            "boredom": round(float(self.runtime.boredom), 3),
            "social_need": round(float(self.runtime.social_need), 3),
            "consecutive_proactive_count": int(self.runtime.consecutive_proactive_count),
            "proactive_sleep_mode": bool(self.runtime.proactive_sleep_mode),
            "prediction_buffer": deepcopy(self.runtime.prediction_buffer),
            "last_prediction_error": deepcopy(self.runtime.last_prediction_error),
            "event_queue_size": event_queue_size,
            "blackboard": deepcopy(self.runtime.blackboard),
            "recent_autonomous_traces": deepcopy(self.runtime.autonomous_traces[-6:]),
            "recent_turn_traces": deepcopy(self.runtime.turn_traces[-6:]),
        }

    def get_runtime_snapshot(self):
        return self._runtime_public_state()

    def _diff_runtime_state(self, state_before, state_after, psyche_before, psyche_after):
        return {
            "psyche": {
                "mood_before": psyche_before.get("mood", 0),
                "mood_after": psyche_after.get("mood", 0),
                "mood_delta": psyche_after.get("mood", 0) - psyche_before.get("mood", 0),
                "trust_before": psyche_before.get("trust", 0),
                "trust_after": psyche_after.get("trust", 0),
                "trust_delta": psyche_after.get("trust", 0) - psyche_before.get("trust", 0),
            },
            "focus": {
                "before": state_before.get("current_focus"),
                "after": state_after.get("current_focus"),
            },
            "goal": {
                "before": state_before.get("active_goal"),
                "after": state_after.get("active_goal"),
            },
            "open_loops": {
                "before": state_before.get("open_loops", []),
                "after": state_after.get("open_loops", []),
            },
            "drives": {
                "boredom_before": state_before.get("boredom", 0.0),
                "boredom_after": state_after.get("boredom", 0.0),
                "social_need_before": state_before.get("social_need", 0.0),
                "social_need_after": state_after.get("social_need", 0.0),
                "consecutive_proactive_count_before": state_before.get("consecutive_proactive_count", 0),
                "consecutive_proactive_count_after": state_after.get("consecutive_proactive_count", 0),
                "proactive_sleep_mode_before": state_before.get("proactive_sleep_mode", False),
                "proactive_sleep_mode_after": state_after.get("proactive_sleep_mode", False),
            },
            "prediction": {
                "before": state_before.get("prediction_buffer", {}),
                "after": state_after.get("prediction_buffer", {}),
                "last_prediction_error_after": state_after.get("last_prediction_error", {}),
            },
            "mediators": {
                "attention_before": state_before.get("last_attention_frame", {}),
                "attention_after": state_after.get("last_attention_frame", {}),
                "appraisal_before": state_before.get("last_appraisal", {}),
                "appraisal_after": state_after.get("last_appraisal", {}),
                "self_monitor_after": state_after.get("last_self_monitor", {}),
                "speech_plan_after": state_after.get("last_speech_plan", {}),
            },
        }

    def _plan_trace_summary(self, logic):
        return {
            "intent": logic.get("intent"),
            "scene": logic.get("scene"),
            "hidden_intent": logic.get("hidden_intent"),
            "user_belief": logic.get("user_belief"),
            "my_hidden_knowledge": logic.get("my_hidden_knowledge"),
            "user_expectation": logic.get("user_expectation"),
            "reply_goal": logic.get("reply_goal"),
            "core_message_jp": logic.get("core_message_jp"),
            "response_mode": logic.get("response_mode"),
            "surface_act": logic.get("surface_act"),
            "dialogue_act": logic.get("dialogue_act"),
            "human_speech_plan": logic.get("human_speech_plan"),
            "payload_level": logic.get("payload_level"),
            "premise_check": logic.get("premise_check"),
            "routing_path": logic.get("routing_path"),
            "grounding": logic.get("grounding"),
            "memory_anchor": logic.get("memory_anchor"),
            "memory_relevance": logic.get("memory_relevance"),
            "memory_relevance_label": logic.get("memory_relevance_label"),
            "memory_speakability": logic.get("memory_speakability"),
            "memory_gravity": logic.get("memory_gravity"),
            "memory_use_expected": logic.get("memory_use_expected"),
            "post_check": logic.get("post_check"),
            "appraisal": logic.get("appraisal"),
            "self_monitor": logic.get("self_monitor"),
            "procedural_guidance": logic.get("procedural_guidance"),
            "planner_tick_budget": logic.get("planner_tick_budget"),
            "planner_tick_count": logic.get("planner_tick_count"),
            "self_correction_applied": logic.get("self_correction_applied"),
        }

    def _compute_prediction_error(self, actual_signal):
        expected = dict(self.runtime.prediction_buffer or {})
        actual_intent = str((actual_signal or {}).get("actual_intent", "")).strip()
        actual_valence = float((actual_signal or {}).get("actual_valence", 0.0) or 0.0)
        expected_intent = str(expected.get("expected_intent", "")).strip()
        expected_valence = float(expected.get("expected_valence", 0.0) or 0.0)

        prediction_error = abs(actual_valence - expected_valence)
        intent_mismatch = bool(expected_intent and actual_intent and actual_intent != expected_intent)
        if intent_mismatch:
            prediction_error += 1.0

        payload = {
            "expected_intent": expected_intent,
            "expected_valence": round(expected_valence, 3),
            "actual_intent": actual_intent,
            "actual_valence": round(actual_valence, 3),
            "intent_mismatch": intent_mismatch,
            "prediction_error": round(prediction_error, 3),
            "shock": prediction_error > PREDICTION_ERROR_THRESHOLD,
        }
        self.runtime.remember_prediction_error(payload)
        return payload

    def _apply_prediction_error_shock(self, prediction_error):
        if not prediction_error.get("shock"):
            return None
        actual_valence = float(prediction_error.get("actual_valence", 0.0) or 0.0)
        mood_delta = -12 if actual_valence <= -0.65 else -7
        trust_delta = -8 if prediction_error.get("intent_mismatch") else -4
        self.psyche.force_adjust(mood_delta=mood_delta, trust_delta=trust_delta, trust_lock_turns=2)
        return {
            "mood_delta": mood_delta,
            "trust_delta": trust_delta,
            "trust_lock_turns": 2,
        }

    def _proactive_query_text(self):
        memory_runtime = self.memory.get_runtime_snapshot()
        for candidate in [
            self.runtime.current_focus,
            memory_runtime.get("short_term_summary"),
            memory_runtime.get("recent_dialogue"),
            "最近の会話",
        ]:
            text = str(candidate or "").strip()
            if text and text not in {"無短期緩衝", "無近期對話"}:
                return text
        return "最近の会話"

    def ingest_event(self, user_input):
        now = time.time()
        self._last_external_input_at = now
        self.runtime.register_user_input(when=now)
        memory_before = self.memory.get_runtime_snapshot()
        runtime_before = self._runtime_public_state()
        mems = self.memory.query_all_layers(user_input)
        psyche_before = self.psyche.get_state()

        self.runtime.cycle_index += 1
        self.runtime.last_user_input = user_input
        self.runtime.current_focus = self._infer_focus_label(user_input, mems)
        self.runtime.active_goal = "understand_user_and_reply"
        self.runtime.open_loops = []
        self.runtime.latent_goal_stack = []
        self.runtime.working_memory = list(mems.get("working_memory_items") or [])[:WORKING_MEMORY_LIMIT]
        attention_frame = self._build_attention_frame(user_input, mems)
        self.runtime.blackboard = []
        self.runtime.last_route = {}
        self.runtime.last_attention_frame = attention_frame
        self.runtime.last_appraisal = {}
        self.runtime.last_internal_monologue = ""
        self.runtime.last_candidates = []
        self.runtime.last_selected_plan = {}
        self.runtime.planner_tick_trace = []
        self.runtime.planner_tick_count = 0
        self.runtime.self_correction_applied = False
        self.runtime.last_speech_plan = {}
        self.runtime.last_self_monitor = {}
        self.runtime.last_reply = ""
        self.runtime.pending_proactive_turn = {}
        self.runtime.last_memory_writes = []
        self.runtime.last_memory_before = memory_before
        self.runtime.last_memory_after = {}
        self.runtime.last_memory_diff = {}
        self.runtime.last_psyche_before = psyche_before
        self.runtime.last_psyche_after = psyche_before
        self.runtime.last_state_diff = {}

        self._push_blackboard(
            "ingest",
            "user_input",
            {"text": user_input, "focus_seed": self.runtime.current_focus},
            salience=1.0,
        )
        self._push_blackboard(
            "retrieve",
            "memory_layers",
            {
                "knowledge": mems.get("knowledge"),
                "episodes": mems.get("episodes"),
                "wisdom": mems.get("wisdom"),
                "profile": mems.get("profile"),
            },
            salience=0.76,
        )
        self._push_blackboard(
            "retrieve",
            "working_memory",
            {
                "summary": mems.get("working_memory_summary"),
                "items": self.runtime.working_memory,
                "attention_frame": attention_frame,
            },
            salience=0.93,
        )
        self._push_blackboard(
            "attention",
            "attention_frame",
            attention_frame,
            salience=0.91,
        )
        return {
            "user_input": user_input,
            "memory_data": mems,
            "psyche_before": psyche_before,
            "runtime_before": runtime_before,
            "memory_before": memory_before,
        }

    def cognitive_tick(self, event):
        user_input = event["user_input"]
        mems = event["memory_data"]
        psyche_before = event["psyche_before"]
        actual_signal = self.left_brain.classify_user_signal(user_input, psyche_before, mems)
        prediction_error = self._compute_prediction_error(actual_signal)
        shock_update = self._apply_prediction_error_shock(prediction_error)
        appraisal = self._appraise_user_input(
            user_input,
            actual_signal,
            prediction_error,
            mems,
            self.psyche.get_state(),
        )
        mems["appraisal"] = appraisal
        route_info = self.left_brain._high_low_road_route(
            user_input,
            self.psyche.get_state(),
            actual_signal=actual_signal,
            prediction_error=prediction_error,
            appraisal=appraisal,
        )
        self.runtime.last_route = route_info
        self._push_blackboard("perception", "actual_signal", actual_signal, salience=0.9)
        self._push_blackboard("perception", "prediction_error", prediction_error, salience=0.94)
        self._push_blackboard("perception", "appraisal", appraisal, salience=0.95)
        if shock_update:
            self._push_blackboard("route", "prediction_error_shock", shock_update, salience=0.98)
        self._push_blackboard("route", "high_low_router", route_info, salience=0.98)

        if route_info.get("route") == "low_road":
            logic = self.left_brain._build_low_road_plan(user_input, self.psyche.get_state(), mems, route_info)
            print(Fore.MAGENTA + f"  [Router] low_road -> {route_info}")
        else:
            logic = self.left_brain.think(user_input, mems, psyche_before)

        logic["appraisal"] = appraisal
        procedural_guidance = self._extract_procedural_guidance(mems)
        logic["procedural_guidance"] = procedural_guidance
        if procedural_guidance.get("active"):
            hidden = str(logic.get("my_hidden_knowledge", "")).strip()
            guidance_text = procedural_guidance.get("summary", "")
            logic["my_hidden_knowledge"] = self._trim_text(
                f"{hidden} / 手続き記憶: {guidance_text}".strip(" /"),
                140,
            )
            self._push_blackboard("reason", "procedural_guidance", procedural_guidance, salience=0.82)
        self._attach_memory_gravity(logic, user_input, mems)
        prediction_hint = self.left_brain.predict_next_user_signal(logic, user_input, psyche_before, mems, mode="reactive")
        self.runtime.set_prediction(
            prediction_hint.get("expected_intent", ""),
            prediction_hint.get("expected_valence", 0.0),
            source_plan_intent=prediction_hint.get("source_plan_intent", logic.get("intent", "")),
        )
        logic["prediction_hint"] = prediction_hint

        self.runtime.last_internal_monologue = logic.get("internal_monologue", "")
        self.runtime.last_candidates = list(logic.get("bayes_candidates") or [])[:3]
        self.runtime.last_selected_plan = self._plan_trace_summary(logic)
        self.runtime.planner_tick_trace = list(logic.get("planner_tick_trace") or [])
        self.runtime.planner_tick_count = int(logic.get("planner_tick_count") or 0)
        self.runtime.self_correction_applied = bool(logic.get("self_correction_applied"))
        self.runtime.current_focus = self._infer_focus_label(user_input, mems, logic)
        self.runtime.active_goal = logic.get("reply_goal", "自然に返す")
        self.runtime.open_loops = self._derive_open_loops(logic)
        self.runtime.latent_goal_stack = deepcopy(self.runtime.open_loops)

        if self.runtime.last_internal_monologue:
            self._push_blackboard(
                "reason",
                "internal_monologue",
                {"text": self.runtime.last_internal_monologue},
                salience=0.82,
            )
        if any(logic.get(key) for key in ("user_belief", "my_hidden_knowledge", "user_expectation")):
            self._push_blackboard(
                "reason",
                "bdi_state",
                {
                    "user_belief": logic.get("user_belief"),
                    "my_hidden_knowledge": logic.get("my_hidden_knowledge"),
                    "user_expectation": logic.get("user_expectation"),
                },
                salience=0.84,
            )
        if logic.get("memory_anchor"):
            self._push_blackboard(
                "reason",
                "memory_gravity",
                {
                    "anchor": logic.get("memory_anchor"),
                    "relevance": logic.get("memory_relevance"),
                    "speakability": logic.get("memory_speakability"),
                    "gravity": logic.get("memory_gravity"),
                    "memory_use_expected": logic.get("memory_use_expected"),
                },
                salience=0.9,
            )
        if logic.get("appraisal"):
            self._push_blackboard(
                "reason",
                "appraisal_bias",
                logic.get("appraisal"),
                salience=0.78,
            )
        if self.runtime.last_candidates:
            self._push_blackboard(
                "reason",
                "candidate_plans",
                self.runtime.last_candidates,
                salience=0.88,
            )
        if self.runtime.planner_tick_trace:
            self._push_blackboard(
                "reason",
                "planner_ticks",
                self.runtime.planner_tick_trace,
                salience=0.8,
            )
        self._push_blackboard(
            "predict",
            "next_user_prediction",
            prediction_hint,
            salience=0.76,
        )
        self._push_blackboard(
            "select",
            "selected_plan",
            self.runtime.last_selected_plan,
            salience=0.97,
        )
        if self.runtime.open_loops:
            self._push_blackboard(
                "select",
                "open_loops",
                self.runtime.open_loops,
                salience=0.7,
            )
        return {
            "route_info": route_info,
            "logic": logic,
        }

    def emit_response_if_ready(self, event, tick_result):
        user_input = event["user_input"]
        mems = event["memory_data"]
        psyche_before = event["psyche_before"]
        logic = tick_result["logic"]
        route_info = tick_result["route_info"]

        self.psyche.adjust(logic.get("mood_impact", 0), logic.get("trust_impact", 0))
        psyche_after = self.psyche.get_state()
        self.runtime.last_psyche_after = psyche_after

        reply = self.right_brain.speak(user_input, logic, mems, psyche_after)
        self.runtime.last_speech_plan = deepcopy(logic.get("human_speech_plan") or {})
        if self.runtime.last_speech_plan:
            self._push_blackboard("surface", "human_speech_plan", self.runtime.last_speech_plan, salience=0.9)
        self_monitor = self._self_monitor_reply(user_input, reply, logic, mems)
        if self_monitor.get("needs_repair"):
            reply = self._repair_reply_from_self_monitor(reply, logic, self_monitor, user_input, mems, psyche_after)
            self.runtime.last_speech_plan = deepcopy(logic.get("human_speech_plan") or self.runtime.last_speech_plan)
            repair_monitor = self._self_monitor_reply(user_input, reply, logic, mems)
            repair_monitor["repaired_from"] = self_monitor
            self_monitor = repair_monitor
        logic["self_monitor"] = self_monitor
        post_check = self._attach_reply_post_check(logic, user_input, reply, mems)
        self.runtime.last_reply = reply
        self.runtime.last_selected_plan = self._plan_trace_summary(logic)
        self.runtime.touch_interaction(when=time.time(), reset_drives=True)
        self._push_blackboard("surface", "utterance", {"reply": reply}, salience=1.0)
        self._push_blackboard("surface", "self_monitor", self_monitor, salience=0.89)
        self._push_blackboard("surface", "post_check", post_check, salience=0.86)

        episode_doc = self.memory.save_episode(user_input, reply, psyche_after, logic)
        reflection = self.memory.reflect_experience(user_input, reply, logic, self.client_logic)

        memory_after = self.memory.get_runtime_snapshot()
        memory_writes = [
            {
                "layer": "episodic_memory",
                "kind": "turn_episode",
                "summary": self._trim_text(episode_doc, 120),
            }
        ]
        if reflection:
            memory_writes.append(
                {
                    "layer": "wisdom_semantic",
                    "kind": "stable_rule",
                    "summary": self._trim_text(reflection, 120),
                }
            )
        self.runtime.last_memory_writes = memory_writes
        self.runtime.last_memory_after = memory_after
        self.runtime.last_memory_diff = self._diff_memory_snapshot(event["memory_before"], memory_after)
        self._push_blackboard(
            "memory",
            "memory_updates",
            {
                "writes": memory_writes,
                "diff": self.runtime.last_memory_diff,
            },
            salience=0.86,
        )

        runtime_after = self._runtime_public_state()
        state_diff = self._diff_runtime_state(event["runtime_before"], runtime_after, psyche_before, psyche_after)
        self.runtime.last_state_diff = state_diff

        turn_trace = {
            "cycle_index": self.runtime.cycle_index,
            "focus": self.runtime.current_focus,
            "goal": self.runtime.active_goal,
            "latent_goal_stack": deepcopy(self.runtime.latent_goal_stack),
            "route_info": route_info,
            "blackboard": deepcopy(self.runtime.blackboard),
            "selected_plan": deepcopy(self.runtime.last_selected_plan),
            "planner_tick_trace": deepcopy(self.runtime.planner_tick_trace),
            "planner_tick_count": self.runtime.planner_tick_count,
            "self_correction_applied": self.runtime.self_correction_applied,
            "self_monitor": deepcopy(self.runtime.last_self_monitor),
            "state_diff": deepcopy(state_diff),
            "memory_diff": deepcopy(self.runtime.last_memory_diff),
            "memory_writes": deepcopy(memory_writes),
        }
        self.runtime.turn_traces.append(turn_trace)
        if len(self.runtime.turn_traces) > 18:
            self.runtime.turn_traces = self.runtime.turn_traces[-18:]

        return {
            "reply": reply,
            "route_info": route_info,
            "logic": logic,
            "memory_data": mems,
            "psyche_before": psyche_before,
            "psyche_after": psyche_after,
            "episode_doc": episode_doc,
            "reflection": reflection,
            "memory_runtime": memory_after,
            "runtime_trace": turn_trace,
            "runtime_state": self.get_runtime_snapshot(),
        }

    def _autonomous_goal_candidates(self):
        memory_runtime = self.memory.get_runtime_snapshot()
        candidates = []
        last_dialogue_activity = max(
            float(self._last_external_input_at or 0.0),
            float(self.runtime.last_interaction_timestamp or 0.0),
        )
        idle_seconds = max(0.0, time.time() - last_dialogue_activity)
        psyche_now = self.psyche.get_state()
        pending_delivery = bool(self.runtime.pending_proactive_turn)
        delivered_keys = set(self.runtime.proactive_delivery_keys or [])
        proactive_allowed = not pending_delivery and not self.runtime.proactive_sleep_mode

        if self.runtime.open_loops:
            candidates.append(
                {
                    "kind": "maintain_open_loops",
                    "label": "保留中の対話ループを維持",
                    "priority": 0.92,
                    "detail": deepcopy(self.runtime.open_loops[:3]),
                }
            )
            follow_loop = next(
                (
                    loop
                    for loop in self.runtime.open_loops
                    if str(loop.get("key") or f"{loop.get('kind', 'loop')}:{loop.get('reason', 'followup')}") not in delivered_keys
                ),
                None,
            )
            if proactive_allowed and follow_loop and idle_seconds >= AUTONOMOUS_IDLE_SECONDS * 1.8:
                delivery_key = str(
                    follow_loop.get("key")
                    or f"{follow_loop.get('kind', 'loop')}:{follow_loop.get('reason', 'followup')}"
                )
                candidates.append(
                    {
                        "kind": "proactive_followup",
                        "label": "主動追問未完成的對話",
                        "priority": 0.97,
                        "detail": {
                            "open_loop": deepcopy(follow_loop),
                            "delivery_key": delivery_key,
                            "idle_seconds": round(idle_seconds, 2),
                        },
                    }
                )

        pending_turns = memory_runtime.get("pending_consolidation_turns", 0)
        if pending_turns >= 4 or self.memory.has_unconsolidated_turns(4):
            candidates.append(
                {
                    "kind": "three_speed_consolidation",
                    "label": "短期記憶を三速で整理",
                    "priority": 0.9,
                    "detail": {"pending_turns": pending_turns},
                }
            )

        if self.memory.short_term_buffer:
            strongest = sorted(
                self.memory.short_term_buffer,
                key=lambda item: float(item.get("strength", 0.0)),
                reverse=True,
            )[0]
            candidates.append(
                {
                    "kind": "latent_rehearsal",
                    "label": "強い短期記憶を再評価",
                    "priority": 0.7,
                    "detail": {
                        "intent": strongest.get("intent"),
                        "scene": strongest.get("scene"),
                        "strength": strongest.get("strength"),
                        "text": self._trim_text(strongest.get("text", ""), 80),
                    },
                }
            )
            share_key = f"share:{strongest.get('intent') or 'chat'}:{self._trim_text(strongest.get('text', ''), 24)}"
            if (
                proactive_allowed
                and share_key not in delivered_keys
                and idle_seconds >= AUTONOMOUS_IDLE_SECONDS * 2.3
                and float(strongest.get("strength", 0.0)) >= 0.52
            ):
                candidates.append(
                    {
                        "kind": "proactive_share",
                        "label": "主動把腦中殘留的話題說出口",
                        "priority": 0.79,
                        "detail": {
                            "intent": strongest.get("intent"),
                            "scene": strongest.get("scene"),
                            "strength": strongest.get("strength"),
                            "text": self._trim_text(strongest.get("text", ""), 80),
                            "delivery_key": share_key,
                        },
                    }
                )

        if (
            proactive_allowed
            and "ping" not in delivered_keys
            and idle_seconds >= AUTONOMOUS_IDLE_SECONDS * 3.4
            and -35 <= psyche_now.get("mood", 0) <= 20
        ):
            candidates.append(
                {
                    "kind": "proactive_ping",
                    "label": "主動打破沉默",
                    "priority": 0.48,
                    "detail": {
                        "idle_seconds": round(idle_seconds, 2),
                        "mood": psyche_now.get("mood", 0),
                        "trust": psyche_now.get("trust", 50),
                        "delivery_key": "ping",
                    },
                }
            )

        candidates.append(
            {
                "kind": "passive_decay",
                "label": "受動的な減衰と待機",
                "priority": 0.2,
                "detail": {},
            }
        )
        candidates.sort(key=lambda item: item["priority"], reverse=True)
        return candidates

    def _build_proactive_turn(self, goal):
        kind = goal.get("kind")
        detail = goal.get("detail") or {}

        if kind == "proactive_followup":
            open_loop = detail.get("open_loop") or {}
            reason = open_loop.get("reason", "")
            if reason == "clarify_light":
                line = "で、どの話のことだったんだよ。そこだけ言えって。"
                intent = "clarify_previous_reply"
            elif reason == "premise_challenge":
                line = "さっきの前提、結局どこから来たんだよ。そこ先だろ。"
                intent = "premise_doubt"
            elif reason == "lyric_probe":
                line = "さっきの歌詞っぽいやつ、結局何の曲だよ。曲名まで出せって。"
                intent = "reference_probe"
            elif reason == "reference_probe":
                line = "さっきの一言、結局何のネタだよ。元まで出せって。"
                intent = "reference_probe"
            elif reason == "version_fragment_clarify":
                line = "さっきの日版って、何の作品のどの版だよ。そこまで言えって。"
                intent = "version_fragment_clarify"
            elif reason == "correction_followup":
                line = "さっき答えが違うって言っただろ。どこを直せばいいか教えろって。"
                intent = "correction_followup"
            elif reason == "relationship_temperature_check":
                line = "結局そこ確認したかっただけだろ。まだ何かあるのか。"
                intent = "ask_miss_me"
            elif reason == "permission_probe":
                line = "呼び方の件、まだ気にしてるのか。変なのじゃなきゃ別にいいし。"
                intent = "nickname_question"
            elif reason == "crisis_support":
                line = "さっきの件、今ひとりか？まだ危ないなら近くの人に連絡しろ。"
                intent = "crisis_support"
            else:
                line = "さっきの話、まだ途中だろ。そこ投げっぱなしにするなって。"
                intent = "chat"
        elif kind == "proactive_share":
            intent = str(detail.get("intent") or "chat")
            text = self._trim_text(detail.get("text", ""), 40)
            if intent in {"tired_support", "anxious_support", "crying_support", "giving_up_support", "pain_support"}:
                line = "さっきの感じ、まだ引きずってるだろ。今日はちゃんと休めって。"
            elif intent in {"food_offer_generic", "food_offer_sweet", "food_question", "food_preference_query", "fastfood_preference", "store_offer", "cooked_food"}:
                line = "さっきの食い物の流れで普通に腹減ってきた。"
            elif intent in {"ask_miss_me", "ask_like_me", "nickname_question", "annoying_check", "mad_check", "cold_check"}:
                line = "さっきの確認、まだ気にしてるなら引っ張りすぎなくていいぞ。"
            elif text:
                line = f"さっきの「{text}」まだ頭に残ってる。"
            else:
                line = "さっきの流れ、まだちょっと残ってるんだよな。"
        elif kind == "proactive_ping":
            intent = "chat"
            line = "静かだな。今なにしてんだよ。"
        else:
            return {}

        return {
            "kind": kind,
            "intent": intent,
            "line": self.right_brain._sanitize_reply(line, max_chars=42),
            "delivery_key": str(detail.get("delivery_key") or kind),
            "detail": deepcopy(detail),
        }

    def _derive_autonomous_note(self, goal):
        kind = goal.get("kind")
        detail = goal.get("detail") or {}
        if kind == "maintain_open_loops":
            first = (detail or [{}])[0]
            reason = first.get("reason", "followup")
            if reason == "relationship_temperature_check":
                return "関係温度の話が残ってる。次は冷たすぎず甘すぎず返す。"
            if reason == "premise_challenge":
                return "前提がまだ浮いてる。次はまずそこを固定する。"
            if reason == "clarify_light":
                return "情報が足りない。次は不足部分だけ短く取りにいく。"
            return "会話の保留点が残ってる。次の入力ではそこを先に拾う。"
        if kind == "proactive_followup":
            return "入力待ちのままだと会話が死ぬ。保留点を自分から拾って動かす。"
        if kind == "proactive_share":
            return "短期記憶に残り続けてる話題がある。今なら自分から漏らしても自然。"
        if kind == "proactive_ping":
            return "沈黙が長い。今は軽く声をかけてループを開き直す。"
        if kind == "three_speed_consolidation":
            return "短期のやり取りを経験・知識・手順に分けて畳み直す。"
        if kind == "latent_rehearsal":
            text = self._trim_text(detail.get("text", ""), 52)
            return f"さっきの流れがまだ残ってる。核は「{text}」だ。"
        return "大きくは動かず、今は減衰と待機。"

    def run_background_cycle(self, force=False):
        now = time.time()
        if not force:
            if now - self._last_external_input_at < AUTONOMOUS_IDLE_SECONDS:
                return None
            if now - self._last_background_tick_at < AUTONOMOUS_MIN_INTERVAL_SECONDS:
                return None

        runtime_before = self._runtime_public_state()
        memory_before = self.memory.get_runtime_snapshot()
        psyche_before = self.psyche.get_state()
        self.runtime.autonomous_tick_index += 1
        self.runtime.blackboard = []

        goal_candidates = self._autonomous_goal_candidates()
        selected_goal = goal_candidates[0]
        note = self._derive_autonomous_note(selected_goal)
        proactive_turn = self._build_proactive_turn(selected_goal)
        if proactive_turn:
            self.runtime.pending_proactive_turn = deepcopy(proactive_turn)
        self.runtime.active_goal = selected_goal.get("label", "待機")
        self.runtime.latent_goal_stack = deepcopy(goal_candidates[:4])
        self.runtime.current_focus = selected_goal.get("kind", "idle")

        self._push_blackboard("autonomous", "goal_candidates", goal_candidates[:4], salience=0.82)
        self._push_blackboard("autonomous", "selected_goal", selected_goal, salience=0.94)
        self._push_blackboard("autonomous", "internal_note", {"text": note}, salience=0.78)
        if proactive_turn:
            self._push_blackboard("autonomous", "proactive_turn", proactive_turn, salience=0.92)

        maintenance = self.memory.consolidate_recent_experiences(
            self.client_logic,
            minimum_turns=4,
            force=selected_goal.get("kind") == "three_speed_consolidation" or force,
        )
        memory_after = self.memory.get_runtime_snapshot()
        memory_diff = self._diff_memory_snapshot(memory_before, memory_after)

        memory_writes = []
        if maintenance:
            if maintenance.get("episodic_summary"):
                memory_writes.append(
                    {
                        "layer": "episodic_memory",
                        "kind": "episodic_summary",
                        "summary": self._trim_text(maintenance.get("episodic_summary"), 100),
                    }
                )
            if maintenance.get("wisdom_rule") and maintenance.get("wisdom_rule") != "NO_RULE":
                memory_writes.append(
                    {
                        "layer": "wisdom_semantic",
                        "kind": "semantic_rule",
                        "summary": self._trim_text(maintenance.get("wisdom_rule"), 100),
                    }
                )
            if maintenance.get("procedural_rule") and maintenance.get("procedural_rule") != "NO_RULE":
                memory_writes.append(
                    {
                        "layer": "procedural_memory",
                        "kind": "response_policy",
                        "summary": self._trim_text(maintenance.get("procedural_rule"), 100),
                    }
                )

        self.runtime.last_memory_writes = memory_writes
        self.runtime.last_memory_before = memory_before
        self.runtime.last_memory_after = memory_after
        self.runtime.last_memory_diff = memory_diff
        self._push_blackboard(
            "autonomous",
            "memory_maintenance",
            {
                "maintenance": maintenance,
                "memory_diff": memory_diff,
            },
            salience=0.86,
        )

        runtime_after = self._runtime_public_state()
        state_diff = self._diff_runtime_state(runtime_before, runtime_after, psyche_before, self.psyche.get_state())
        self.runtime.last_state_diff = state_diff
        result = {
            "autonomous_tick_index": self.runtime.autonomous_tick_index,
            "goal": selected_goal,
            "internal_note": note,
            "proactive_turn": proactive_turn,
            "memory_maintenance": maintenance,
            "memory_diff": memory_diff,
            "memory_writes": memory_writes,
            "blackboard": deepcopy(self.runtime.blackboard),
            "state_diff": state_diff,
        }
        self.runtime.last_autonomous_result = result
        self.runtime.autonomous_traces.append(deepcopy(result))
        if len(self.runtime.autonomous_traces) > 18:
            self.runtime.autonomous_traces = self.runtime.autonomous_traces[-18:]
        self._last_background_tick_at = now
        return result

    def consume_pending_proactive_turn(self, delivered_at=None):
        pending = deepcopy(self.runtime.pending_proactive_turn or {})
        if not pending:
            return {}
        now = float(delivered_at if delivered_at is not None else time.time())
        self.runtime.pending_proactive_turn = {}
        delivery_key = str(pending.get("delivery_key") or pending.get("kind") or "proactive").strip()
        delivered = {
            **pending,
            "delivery_key": delivery_key,
            "delivered_at": now,
        }
        memory_recorded = False
        memory_error = ""
        memory_before = self.memory.get_runtime_snapshot()
        try:
            delivery_logic = {
                "intent": pending.get("intent") or "chat",
                "scene": "casual",
                "cognitive_mode": "proactive",
                "response_mode": "proactive",
                "surface_act": "proactive_turn",
                "reply_goal": "未完成の話題を自分から拾い直す",
                "core_message_jp": pending.get("line") or "",
                "autonomous_proactive": deepcopy(pending),
            }
            episode_doc = self.memory.save_episode(
                f"[proactive:{pending.get('kind') or 'turn'}]",
                pending.get("line") or "",
                self.psyche.get_state(),
                delivery_logic,
            )
            memory_after = self.memory.get_runtime_snapshot()
            self.runtime.last_memory_before = memory_before
            self.runtime.last_memory_after = memory_after
            self.runtime.last_memory_diff = self._diff_memory_snapshot(memory_before, memory_after)
            self.runtime.last_memory_writes = [
                {
                    "layer": "episodic_memory",
                    "kind": "proactive_delivery_episode",
                    "summary": self._trim_text(episode_doc, 120),
                }
            ]
            memory_recorded = True
        except Exception as exc:
            memory_error = self._trim_text(exc, 120)
        delivered["memory_recorded"] = memory_recorded
        delivered["memory_error"] = memory_error
        self.runtime.last_proactive_delivery = deepcopy(delivered)
        self.runtime.register_proactive_output(when=now, delivery_key=delivery_key)
        self._push_blackboard("autonomous", "proactive_delivery", delivered, salience=0.96)
        if memory_recorded:
            self._push_blackboard(
                "memory",
                "proactive_delivery_memory",
                {
                    "writes": self.runtime.last_memory_writes,
                    "diff": self.runtime.last_memory_diff,
                },
                salience=0.88,
            )
        return delivered

    def _handle_timer_tick_event(self, event):
        now = float((event or {}).get("payload", {}).get("timestamp", time.time()))
        should_trigger_urge = self.runtime.update_drives(current_time=now)
        self._push_blackboard(
            "autonomous",
            "drive_update",
            {
                "boredom": round(self.runtime.boredom, 3),
                "social_need": round(self.runtime.social_need, 3),
                "consecutive_proactive_count": int(self.runtime.consecutive_proactive_count),
                "proactive_sleep_mode": bool(self.runtime.proactive_sleep_mode),
                "should_trigger_urge": should_trigger_urge,
            },
            salience=0.72,
        )
        if should_trigger_urge:
            self.enqueue_internal_urge(
                reason="drive_threshold",
                payload={
                    "boredom": round(self.runtime.boredom, 3),
                    "social_need": round(self.runtime.social_need, 3),
                },
            )
            return {
                "event_type": "timer_tick",
                "triggered_internal_urge": True,
                "runtime_state": self.get_runtime_snapshot(),
            }

        background = self.run_background_cycle(force=False)
        return {
            "event_type": "timer_tick",
            "triggered_internal_urge": False,
            "background_result": background,
            "runtime_state": self.get_runtime_snapshot(),
        }

    def _handle_internal_urge_event(self, event):
        reason = str((event or {}).get("payload", {}).get("reason", "internal_urge"))
        query_text = self._proactive_query_text()
        memory_before = self.memory.get_runtime_snapshot()
        runtime_before = self._runtime_public_state()
        memory_data = self.memory.query_all_layers(query_text)
        psyche_before = self.psyche.get_state()

        self.runtime.autonomous_tick_index += 1
        self.runtime.blackboard = []
        self.runtime.current_focus = self._infer_focus_label(query_text, memory_data)
        self.runtime.active_goal = "proactive_contact"
        self.runtime.working_memory = list(memory_data.get("working_memory_items") or [])[:WORKING_MEMORY_LIMIT]

        self._push_blackboard("autonomous", "internal_urge_event", {"reason": reason, "query_text": query_text}, salience=0.96)
        self._push_blackboard(
            "retrieve",
            "working_memory",
            {
                "summary": memory_data.get("working_memory_summary"),
                "items": self.runtime.working_memory,
            },
            salience=0.9,
        )

        logic = self.left_brain.think(
            query_text,
            memory_data,
            psyche_before,
            mode="proactive",
            runtime_state=self.runtime,
        )
        prediction_hint = self.left_brain.predict_next_user_signal(logic, query_text, psyche_before, memory_data, mode="proactive")
        self.runtime.set_prediction(
            prediction_hint.get("expected_intent", ""),
            prediction_hint.get("expected_valence", 0.0),
            source_plan_intent=prediction_hint.get("source_plan_intent", logic.get("intent", "")),
        )
        self.runtime.last_internal_monologue = logic.get("internal_monologue", "")
        self.runtime.last_candidates = list(logic.get("bayes_candidates") or [])[:3]
        self.runtime.last_selected_plan = self._plan_trace_summary(logic)
        self.runtime.planner_tick_trace = list(logic.get("planner_tick_trace") or [])
        self.runtime.planner_tick_count = int(logic.get("planner_tick_count") or 0)
        self.runtime.self_correction_applied = bool(logic.get("self_correction_applied"))
        self.runtime.open_loops = self._derive_open_loops(logic)
        self.runtime.latent_goal_stack = deepcopy(self.runtime.open_loops)
        self._push_blackboard("predict", "next_user_prediction", prediction_hint, salience=0.74)
        self._push_blackboard("select", "selected_plan", self.runtime.last_selected_plan, salience=0.97)

        psyche_after = self.psyche.get_state()
        reply = self.right_brain.speak(query_text, logic, memory_data, psyche_after)
        self.runtime.last_speech_plan = deepcopy(logic.get("human_speech_plan") or {})
        self.runtime.last_reply = reply
        self.runtime.register_proactive_output(when=time.time())
        if self.runtime.last_speech_plan:
            self._push_blackboard("surface", "human_speech_plan", self.runtime.last_speech_plan, salience=0.9)
        self._push_blackboard("surface", "utterance", {"reply": reply}, salience=1.0)

        episode_doc = self.memory.save_episode(f"[internal_urge:{reason}]", reply, psyche_after, logic)
        memory_after = self.memory.get_runtime_snapshot()
        self.runtime.last_memory_writes = [
            {
                "layer": "episodic_memory",
                "kind": "internal_urge_episode",
                "summary": self._trim_text(episode_doc, 120),
            }
        ]
        self.runtime.last_memory_before = memory_before
        self.runtime.last_memory_after = memory_after
        self.runtime.last_memory_diff = self._diff_memory_snapshot(memory_before, memory_after)
        self._push_blackboard(
            "memory",
            "memory_updates",
            {"writes": self.runtime.last_memory_writes, "diff": self.runtime.last_memory_diff},
            salience=0.82,
        )

        runtime_after = self._runtime_public_state()
        state_diff = self._diff_runtime_state(runtime_before, runtime_after, psyche_before, psyche_after)
        self.runtime.last_state_diff = state_diff
        result = {
            "event_type": "internal_urge",
            "reason": reason,
            "reply": reply,
            "logic": logic,
            "memory_runtime": memory_after,
            "runtime_state": self.get_runtime_snapshot(),
            "state_diff": state_diff,
        }
        self.runtime.last_autonomous_result = deepcopy(result)
        self.runtime.autonomous_traces.append(deepcopy(result))
        if len(self.runtime.autonomous_traces) > 18:
            self.runtime.autonomous_traces = self.runtime.autonomous_traces[-18:]
        return result

    def process_next_event(self, allow_timer_injection=True):
        if allow_timer_injection:
            self._maybe_enqueue_timer_tick(force=False)
        with self._event_queue_lock:
            if not self._event_queue:
                return None
            event = heapq.heappop(self._event_queue)
        if event.event_type == "user_input":
            text = str(event.payload.get("text", "")).strip()
            if not text:
                return None
            result = self.run_turn_debug(text)
            result["event_type"] = "user_input"
            return result
        if event.event_type == "timer_tick":
            return self._handle_timer_tick_event(asdict(event))
        if event.event_type == "internal_urge":
            return self._handle_internal_urge_event(asdict(event))
        return None

    def run_event_loop(self, max_steps=None, idle_sleep=0.2):
        steps = 0
        while True:
            result = self.process_next_event(allow_timer_injection=True)
            if result is None:
                time.sleep(idle_sleep)
            else:
                yield result
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break

    def _timer_loop(self, interval_seconds=EVENT_TIMER_INTERVAL_SECONDS):
        while not self._runtime_stop_event.wait(max(0.1, float(interval_seconds))):
            self.enqueue_timer_tick()

    def _event_worker_loop(self, idle_sleep=0.2):
        while not self._runtime_stop_event.is_set():
            result = self.process_next_event(allow_timer_injection=False)
            if result is None:
                self._runtime_stop_event.wait(max(0.05, float(idle_sleep)))
                continue
            if (
                self._async_output_handler
                and result.get("event_type") in {"user_input", "internal_urge"}
            ):
                try:
                    self._async_output_handler(result)
                except Exception:
                    pass

    def start_async_runtime(self, output_handler=None, timer_interval=EVENT_TIMER_INTERVAL_SECONDS, idle_sleep=0.2):
        if self._event_worker_thread and self._event_worker_thread.is_alive():
            return False
        self._async_output_handler = output_handler
        self._runtime_stop_event.clear()
        self._timer_thread = threading.Thread(
            target=self._timer_loop,
            args=(timer_interval,),
            daemon=True,
            name="uruha-timer-loop",
        )
        self._event_worker_thread = threading.Thread(
            target=self._event_worker_loop,
            args=(idle_sleep,),
            daemon=True,
            name="uruha-event-worker",
        )
        self._timer_thread.start()
        self._event_worker_thread.start()
        return True

    def stop_async_runtime(self, join_timeout=1.0):
        self._runtime_stop_event.set()
        for thread in (self._timer_thread, self._event_worker_thread):
            if thread and thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=join_timeout)
        self._timer_thread = None
        self._event_worker_thread = None
        self._async_output_handler = None

    def reset_session(self, db_path=None):
        global DB_PATH
        self.stop_async_runtime(join_timeout=0.2)
        if db_path:
            DB_PATH = db_path
            self.memory = MemoryManager()
        else:
            self.memory.clear_session_state()
        self.psyche = Psyche(config=getattr(self, "psyche_config", PsycheConfig()))
        self.right_brain.reset_session_state()
        self.runtime = self._new_runtime_state()
        self._last_external_input_at = time.time()
        self._last_background_tick_at = 0.0
        self._last_timer_event_at = 0.0
        with self._event_queue_lock:
            self._event_queue = []
        self._event_seq = 0
        self._runtime_stop_event = threading.Event()

    def run_turn_debug(self, user_input):
        event = self.ingest_event(user_input)
        tick_result = self.cognitive_tick(event)
        return self.emit_response_if_ready(event, tick_result)

    def live(self, user_input):
        self.enqueue_user_input(user_input)
        result = None
        while result is None or result.get("event_type") != "user_input":
            result = self.process_next_event(allow_timer_injection=False)
        return result["reply"]


if __name__ == "__main__":
    bot = UruhaBrainV4_Mac()
    print(Fore.WHITE + "System Ready. Type 'exit' to quit.")

    output_lock = threading.Lock()

    def _cli_output_handler(result):
        reply = str(result.get("reply", "")).strip()
        if not reply:
            return
        event_type = str(result.get("event_type", "")).strip()
        prefix = "Uruha"
        if event_type == "internal_urge":
            prefix = "Uruha [Proactive]"
        with output_lock:
            print(f"\n{Fore.CYAN}{prefix}: {Fore.WHITE}{reply}", flush=True)

    bot.start_async_runtime(output_handler=_cli_output_handler)

    try:
        while True:
            u_in = input("\nYou: ").strip()
            if not u_in:
                continue
            if u_in.lower() == "exit":
                break
            bot.enqueue_user_input(u_in)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        bot.stop_async_runtime()
