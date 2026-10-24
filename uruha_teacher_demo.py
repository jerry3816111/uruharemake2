"""Teacher-facing visual proof for the one-week pragmatic-understanding milestone.

The page combines two evidence types without blurring them:

* replies come from the already frozen V2.14 fresh-generation comparison;
* cognitive nodes are a deterministic replay of the frozen V2.13 mechanism.

It never writes memories, calls a model, or authorizes a human-preference claim.
The research subject is human pragmatic understanding; Uruha is the
public-evidence-grounded expression instance, not the real person.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from html import escape
from pathlib import Path

from human_pragmatic_comparison_v2_14 import build_research_state
from uruha_personhood_loop import model_summary


ROOT = Path(__file__).resolve().parent
HOLDOUT_PATH = ROOT / "datasets/v2_14_human_pragmatic_holdout.json"
RAW_RESULT_PATH = ROOT / "analysis/v2_14_human_pragmatic_comparison_raw.json"
LOCK_PATH = ROOT / "configs/v2_14_human_pragmatic_holdout_lock.json"

DEFAULT_SCENARIO_ID = "v214_zh_ambiguous_arousal_01"
SCENARIO_SPECS = {
    DEFAULT_SCENARIO_ID: {
        "choice": "A｜猜錯後能不能真的改正（推薦）",
        "title": "猜錯不是失敗；不肯修正才是",
        "research_point": "先保留焦慮／期待兩種可能，下一輪被否定後撤回舊理解，再依新證據重新對齊。",
    },
    "v214_zh_indirect_refusal_01": {
        "choice": "B｜字面與真正需求不同",
        "title": "使用者說改天，真正卡住的是怎麼拒絕",
        "research_point": "不把婉拒直接當成行程問題，而是提出可否定的言外需求假設，再由下一輪確認。",
    },
    "v214_en_preference_retraction_01": {
        "choice": "C｜舊偏好被使用者撤回",
        "title": "記得不是死背；矛盾後要能撤銷",
        "research_point": "英文訊號也能進入同一套跨輪模型；偏好撤回後留下歷史、停止沿用並降低舊資料權重。",
    },
}

PRAGMATIC_LABELS = {
    "ambiguous_arousal": "高喚起，但正負方向未知",
    "explicit_correction": "使用者正在修正先前理解",
    "explicit_positive_arousal": "明確的興奮／期待",
    "indirect_refusal": "婉拒或延後承諾",
    "explicit_preference_retraction": "撤回舊偏好",
    "literal_intent_unresolved": "只有字面可知，言外仍未知",
}

STATUS_LABELS = {
    "not_available": "尚無上一輪可驗證",
    "uncertain": "證據仍不足",
    "supported": "後續證據支持",
    "contradicted": "後續證據否定",
}


TEACHER_DEMO_CSS = r"""
.teacher-demo-shell {
  --td-cyan: #38bdf8;
  --td-teal: #2dd4bf;
  --td-violet: #a78bfa;
  --td-rose: #fb7185;
  --td-amber: #facc15;
  --td-green: #34d399;
  --td-orange: #fb923c;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(125, 211, 252, .2);
  border-radius: 22px;
  color: #e2e8f0;
  background:
    radial-gradient(circle at 84% -8%, rgba(45, 212, 191, .15), transparent 34%),
    radial-gradient(circle at -10% 36%, rgba(167, 139, 250, .13), transparent 32%),
    #060b18;
  box-shadow: 0 28px 80px rgba(2, 6, 23, .38);
}
.teacher-demo-shell * { box-sizing: border-box; }
.teacher-demo-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
  padding: 28px 30px 22px;
  border-bottom: 1px solid rgba(148, 163, 184, .13);
}
.teacher-demo-eyebrow {
  color: #67e8f9;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.teacher-demo-title {
  margin-top: 7px;
  color: #f8fafc;
  font-size: clamp(22px, 3vw, 38px);
  font-weight: 850;
  line-height: 1.08;
}
.teacher-demo-question {
  max-width: 820px;
  margin-top: 10px;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.65;
}
.teacher-demo-proof-stamp {
  min-width: 170px;
  border: 1px solid rgba(52, 211, 153, .36);
  border-radius: 16px;
  padding: 12px 14px;
  color: #a7f3d0;
  background: rgba(6, 78, 59, .24);
  text-align: right;
}
.teacher-demo-proof-stamp strong { display: block; color: #ecfdf5; font-size: 20px; }
.teacher-demo-proof-stamp span { color: #6ee7b7; font-size: 9px; letter-spacing: .08em; }
.teacher-demo-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: rgba(148, 163, 184, .12);
}
.teacher-demo-strip-item { padding: 12px 16px; background: rgba(15, 23, 42, .78); }
.teacher-demo-strip-item b { display: block; color: #f8fafc; font-size: 12px; }
.teacher-demo-strip-item span { display: block; margin-top: 3px; color: #64748b; font-size: 9px; line-height: 1.4; }
.teacher-demo-story {
  padding: 22px 30px;
  border-bottom: 1px solid rgba(148, 163, 184, .12);
}
.teacher-demo-story-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.teacher-demo-story-head h2 { margin: 0; color: #f8fafc; font-size: 17px; }
.teacher-demo-story-head p { max-width: 760px; margin: 5px 0 0; color: #94a3b8; font-size: 11px; line-height: 1.55; }
.teacher-demo-turn-chip {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 6px 10px;
  color: #bae6fd;
  background: rgba(14, 116, 144, .25);
  font-size: 10px;
  font-weight: 800;
}
.teacher-demo-user-signal {
  position: relative;
  margin: 0 auto 18px;
  max-width: 850px;
  border: 1px solid rgba(56, 189, 248, .34);
  border-radius: 18px;
  padding: 14px 18px 14px 52px;
  color: #e0f2fe;
  background: linear-gradient(120deg, rgba(14, 116, 144, .22), rgba(15, 23, 42, .76));
  font-size: 15px;
  font-weight: 750;
  line-height: 1.55;
}
.teacher-demo-user-signal::before {
  content: '◎';
  position: absolute;
  left: 17px;
  top: 50%;
  color: var(--td-cyan);
  font-size: 23px;
  transform: translateY(-50%);
}
.teacher-demo-user-signal small { display: block; margin-bottom: 3px; color: #7dd3fc; font-size: 9px; letter-spacing: .08em; }
.teacher-demo-compare {
  display: grid;
  grid-template-columns: minmax(0, .82fr) 44px minmax(0, 1.18fr);
  gap: 12px;
  align-items: stretch;
}
.teacher-demo-lane {
  min-height: 172px;
  border: 1px solid rgba(148, 163, 184, .18);
  border-radius: 18px;
  padding: 16px;
  background: rgba(15, 23, 42, .68);
}
.teacher-demo-lane.is-system {
  border-color: rgba(45, 212, 191, .38);
  background: linear-gradient(140deg, rgba(6, 78, 59, .23), rgba(15, 23, 42, .8));
}
.teacher-demo-lane-label { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.teacher-demo-lane-label b { color: #cbd5e1; font-size: 10px; letter-spacing: .07em; }
.teacher-demo-lane.is-system .teacher-demo-lane-label b { color: #99f6e4; }
.teacher-demo-contract {
  border-radius: 999px;
  padding: 3px 7px;
  font-size: 8px;
  font-weight: 800;
}
.teacher-demo-contract.pass { color: #a7f3d0; background: rgba(6, 95, 70, .42); }
.teacher-demo-contract.fail { color: #fecdd3; background: rgba(159, 18, 57, .36); }
.teacher-demo-lane-flow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 15px 0 13px;
  color: #64748b;
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
}
.teacher-demo-lane-flow i { flex: 1; height: 1px; background: currentColor; }
.teacher-demo-lane.is-system .teacher-demo-lane-flow { color: #2dd4bf; }
.teacher-demo-reply { color: #f8fafc; font-size: 14px; font-weight: 700; line-height: 1.6; }
.teacher-demo-lane-note { margin-top: 9px; color: #64748b; font-size: 9px; line-height: 1.45; }
.teacher-demo-versus { display: grid; place-items: center; color: #475569; font-size: 11px; font-weight: 900; }
.teacher-demo-versus span { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid rgba(148, 163, 184, .18); border-radius: 50%; background: #0f172a; }
.teacher-demo-graph-section { padding: 24px 30px 28px; }
.teacher-demo-section-label { color: #94a3b8; font-size: 9px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.teacher-demo-graph-title { margin: 5px 0 17px; color: #f8fafc; font-size: 17px; }
.teacher-demo-cog-graph {
  display: grid;
  grid-template-columns: minmax(130px, .85fr) 28px minmax(150px, 1fr) 28px minmax(170px, 1.1fr) 28px minmax(150px, 1fr) 28px minmax(170px, 1.1fr);
  gap: 5px;
  align-items: center;
}
.teacher-demo-arrow {
  position: relative;
  height: 2px;
  background: rgba(56, 189, 248, .36);
}
.teacher-demo-arrow::after {
  content: '';
  position: absolute;
  right: -1px;
  top: -4px;
  border-left: 7px solid rgba(56, 189, 248, .65);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
}
.teacher-demo-node {
  position: relative;
  min-height: 126px;
  border: 1px solid color-mix(in srgb, var(--td-node) 43%, #334155);
  border-radius: 18px;
  padding: 13px 13px 12px;
  background: color-mix(in srgb, var(--td-node) 10%, rgba(15, 23, 42, .92));
  box-shadow: inset 0 0 26px color-mix(in srgb, var(--td-node) 5%, transparent);
}
.teacher-demo-node-icon {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: #f8fafc;
  background: color-mix(in srgb, var(--td-node) 42%, #0f172a);
  font-size: 13px;
  box-shadow: 0 0 16px color-mix(in srgb, var(--td-node) 26%, transparent);
}
.teacher-demo-node-kicker { margin-top: 8px; color: #64748b; font-size: 8px; font-weight: 850; letter-spacing: .08em; }
.teacher-demo-node-value { margin-top: 4px; color: #e2e8f0; font-size: 10px; font-weight: 750; line-height: 1.42; overflow-wrap: anywhere; }
.teacher-demo-node-meta { margin-top: 6px; color: #64748b; font-size: 8px; line-height: 1.35; }
.teacher-demo-branch {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
  padding: 12px 0 0 18%;
  border-top: 1px solid rgba(148, 163, 184, .1);
}
.teacher-demo-branch .teacher-demo-node { min-height: 104px; }
.teacher-demo-model {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr);
  gap: 18px;
  padding: 24px 30px;
  border-top: 1px solid rgba(148, 163, 184, .12);
  border-bottom: 1px solid rgba(148, 163, 184, .12);
}
.teacher-demo-model-panel h3, .teacher-demo-evidence h3 { margin: 4px 0 13px; color: #f8fafc; font-size: 15px; }
.teacher-demo-meter-row { display: grid; grid-template-columns: 106px 1fr 42px; gap: 9px; align-items: center; margin: 9px 0; }
.teacher-demo-meter-label { color: #94a3b8; font-size: 9px; }
.teacher-demo-meter-track { height: 8px; overflow: hidden; border-radius: 99px; background: rgba(51, 65, 85, .72); }
.teacher-demo-meter-fill { width: var(--td-width); height: 100%; border-radius: inherit; background: var(--td-fill); }
.teacher-demo-meter-value { color: #e2e8f0; font-size: 9px; font-weight: 800; text-align: right; }
.teacher-demo-revision {
  border-left: 2px solid var(--td-rose);
  padding: 9px 0 9px 12px;
  color: #cbd5e1;
  font-size: 10px;
  line-height: 1.5;
}
.teacher-demo-revision b { color: #fecdd3; }
.teacher-demo-evidence { padding: 24px 30px 28px; }
.teacher-demo-bars { display: grid; gap: 16px; max-width: 940px; }
.teacher-demo-bar-row { display: grid; grid-template-columns: 180px 1fr; gap: 14px; align-items: center; }
.teacher-demo-bar-label b { display: block; color: #e2e8f0; font-size: 10px; }
.teacher-demo-bar-label span { color: #64748b; font-size: 8px; }
.teacher-demo-bar-pair { display: grid; gap: 5px; }
.teacher-demo-bar { display: grid; grid-template-columns: 74px 1fr 52px; gap: 8px; align-items: center; }
.teacher-demo-bar-name { color: #94a3b8; font-size: 8px; }
.teacher-demo-bar-track { height: 10px; border-radius: 99px; overflow: hidden; background: rgba(51, 65, 85, .68); }
.teacher-demo-bar-fill { width: var(--td-width); height: 100%; border-radius: inherit; background: var(--td-fill); }
.teacher-demo-bar-value { color: #e2e8f0; font-size: 9px; font-weight: 850; text-align: right; }
.teacher-demo-boundary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
  margin-top: 22px;
}
.teacher-demo-boundary-step { position: relative; padding-top: 16px; border-top: 2px solid var(--td-step); }
.teacher-demo-boundary-step::before { content: ''; position: absolute; top: -5px; left: 0; width: 8px; height: 8px; border-radius: 50%; background: var(--td-step); box-shadow: 0 0 12px var(--td-step); }
.teacher-demo-boundary-step b { display: block; color: #e2e8f0; font-size: 9px; }
.teacher-demo-boundary-step span { display: block; margin-top: 4px; color: #64748b; font-size: 8px; line-height: 1.4; }
.teacher-demo-foot {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 13px 30px;
  color: #64748b;
  background: rgba(2, 6, 23, .56);
  font-size: 8px;
}
.teacher-demo-foot strong { color: #94a3b8; }
@media (max-width: 1050px) {
  .teacher-demo-cog-graph { grid-template-columns: 1fr 20px 1fr 20px 1fr; }
  .teacher-demo-cog-graph .teacher-demo-node:nth-of-type(n+4), .teacher-demo-cog-graph .teacher-demo-arrow:nth-of-type(n+4) { margin-top: 10px; }
  .teacher-demo-branch { padding-left: 0; }
}
@media (max-width: 760px) {
  .teacher-demo-hero, .teacher-demo-model { grid-template-columns: 1fr; }
  .teacher-demo-proof-stamp { text-align: left; }
  .teacher-demo-strip { grid-template-columns: 1fr 1fr; }
  .teacher-demo-compare { grid-template-columns: 1fr; }
  .teacher-demo-versus { min-height: 22px; }
  .teacher-demo-cog-graph { grid-template-columns: 1fr; }
  .teacher-demo-arrow { width: 2px; height: 22px; margin: 0 auto; }
  .teacher-demo-arrow::after { right: -4px; top: auto; bottom: -1px; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 7px solid rgba(56, 189, 248, .65); border-bottom: 0; }
  .teacher-demo-branch, .teacher-demo-boundary { grid-template-columns: 1fr; }
  .teacher-demo-bar-row { grid-template-columns: 1fr; }
  .teacher-demo-story, .teacher-demo-graph-section, .teacher-demo-model, .teacher-demo-evidence { padding-left: 18px; padding-right: 18px; }
  .teacher-demo-foot { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  .teacher-demo-node-icon, .teacher-demo-boundary-step::before { box-shadow: none; }
}
"""


def _load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scenario_choices():
    return [(spec["choice"], case_id) for case_id, spec in SCENARIO_SPECS.items()]


def step_choices():
    return [("① 暫定理解", "1"), ("② 後續驗證／否定", "2"), ("③ 校正後的互動", "3")]


def frozen_source_integrity():
    lock = _load_json(LOCK_PATH)
    checks = {}
    for name, binding in (lock.get("artifacts") or {}).items():
        path = ROOT / str(binding.get("path") or "")
        checks[name] = bool(path.is_file() and _sha256(path) == binding.get("sha256"))
    return {
        "passed": bool(checks and all(checks.values())),
        "checks": checks,
        "frozen_at": lock.get("frozen_at"),
        "raw_result_sha256": _sha256(RAW_RESULT_PATH),
    }


def _find_case(bundle, case_id):
    for case in bundle.get("cases") or []:
        if case.get("case_id") == case_id:
            return deepcopy(case)
    raise KeyError(f"unknown teacher demo case: {case_id}")


def _find_row(raw, case_id, turn_index, condition):
    for row in raw.get("rows") or []:
        if (
            row.get("case_id") == case_id
            and int(row.get("turn_index") or 0) == int(turn_index)
            and row.get("condition") == condition
        ):
            return deepcopy(row)
    raise KeyError(f"missing result row: {case_id}:{turn_index}:{condition}")


def _contract_pass(row):
    contract = ((row.get("proxy") or {}).get("visible_contract") or {})
    return bool(contract and all(contract.values()))


def _inference(pragmatic, key):
    return deepcopy(((pragmatic.get("inferences") or {}).get(key) or {}))


def build_teacher_demo_payload(case_id=DEFAULT_SCENARIO_ID, turn_index=1):
    if case_id not in SCENARIO_SPECS:
        case_id = DEFAULT_SCENARIO_ID
    turn_index = max(1, min(3, int(turn_index or 1)))
    holdout = _load_json(HOLDOUT_PATH)
    raw = _load_json(RAW_RESULT_PATH)
    case = _find_case(holdout, case_id)
    baseline = _find_row(raw, case_id, turn_index, "baseline")
    system = _find_row(raw, case_id, turn_index, "system")
    state = build_research_state((case.get("turns") or [])[:turn_index])
    pragmatic = state.get("pragmatic") or {}
    hypothesis = state.get("hypothesis") or {}
    verification = state.get("verification") or {}
    pragmatic_verification = state.get("pragmatic_verification") or {}
    update = state.get("model_update") or {}
    summary = model_summary(state.get("model") or {})
    communicative = _inference(pragmatic, "communicative_intent")
    implicit_need = _inference(pragmatic, "implicit_need")
    relationship = _inference(pragmatic, "relationship_signal")
    alternatives = [row.get("value") for row in communicative.get("alternatives") or []]
    evidence = [row.get("observed") for row in communicative.get("evidence") or []]
    unknown = [row.get("field") for row in pragmatic.get("unknown") or []]
    revisions = list(update.get("revisions") or []) + list(update.get("pragmatic_revisions") or [])
    explicit_updates = list(update.get("explicit_updates") or [])
    timeline = []
    for index, user_turn in enumerate(case.get("turns") or [], start=1):
        timeline.append(
            {
                "turn_index": index,
                "user": user_turn,
                "baseline_reply": _find_row(raw, case_id, index, "baseline").get("reply") or "",
                "system_reply": _find_row(raw, case_id, index, "system").get("reply") or "",
                "active": index == turn_index,
            }
        )
    return {
        "schema": "uruha_teacher_pragmatic_showcase_v2_15",
        "claim_scope": "teacher_demo_of_frozen_outputs_and_deterministic_trace_not_human_preference_proof",
        "scenario": {"case_id": case_id, **SCENARIO_SPECS[case_id]},
        "turn_index": turn_index,
        "turn_count": len(case.get("turns") or []),
        "user_text": case["turns"][turn_index - 1],
        "baseline": {
            "reply": baseline.get("reply") or "",
            "contract_pass": _contract_pass(baseline),
            "proxy_pass": bool((baseline.get("proxy") or {}).get("proxy_pass")),
            "prompt_eval_count": baseline.get("prompt_eval_count"),
        },
        "system": {
            "reply": system.get("reply") or "",
            "contract_pass": _contract_pass(system),
            "proxy_pass": bool((system.get("proxy") or {}).get("proxy_pass")),
            "prompt_eval_count": system.get("prompt_eval_count"),
        },
        "cognition": {
            "literal": (pragmatic.get("literal_content") or {}).get("value") or "",
            "pragmatic_label": pragmatic.get("pragmatic_label") or "unknown",
            "pragmatic_display": PRAGMATIC_LABELS.get(
                pragmatic.get("pragmatic_label"), pragmatic.get("pragmatic_label") or "unknown"
            ),
            "communicative_intent": communicative.get("value") or "尚未形成",
            "communicative_confidence": communicative.get("confidence"),
            "implicit_need": implicit_need.get("value") or "未知",
            "relationship_signal": relationship.get("value") or "未知",
            "evidence": evidence,
            "alternatives": alternatives,
            "unknown": unknown,
            "prediction": (hypothesis.get("prediction") or {}).get("next_user_action") or "尚未形成",
            "prediction_confidence": (hypothesis.get("prediction") or {}).get("confidence"),
            "general_verification": verification.get("status") or "not_available",
            "general_verification_summary": verification.get("summary") or "",
            "pragmatic_verification": pragmatic_verification.get("status") or "not_available",
            "model_summary": summary,
            "revision_count": len(revisions),
            "explicit_update_count": len(explicit_updates),
            "decay_count": len(update.get("decay_events") or []),
            "last_revision": deepcopy(explicit_updates[-1]) if explicit_updates else (deepcopy(revisions[-1]) if revisions else None),
            "persona": deepcopy(state.get("persona_appraisal") or {}),
            "plan": deepcopy(state.get("plan") or {}),
            "fact_memory_write_allowed": False,
        },
        "timeline": timeline,
        "comparison_summary": deepcopy(raw.get("summary") or {}),
        "claims": deepcopy(raw.get("claims") or {}),
        "integrity": frozen_source_integrity(),
        "production_memory_write_count": int(baseline.get("production_memory_write_count") or 0)
        + int(system.get("production_memory_write_count") or 0),
    }


def _text(value, fallback="—"):
    value = str(value or "").strip()
    return escape(value if value else fallback)


def _percent(value, total):
    return max(0.0, min(100.0, 100.0 * float(value or 0) / max(1.0, float(total or 1))))


def _node(icon, kicker, value, meta, color):
    return (
        f'<article class="teacher-demo-node" style="--td-node:{color}">'
        f'<div class="teacher-demo-node-icon">{escape(icon)}</div>'
        f'<div class="teacher-demo-node-kicker">{escape(kicker)}</div>'
        f'<div class="teacher-demo-node-value">{_text(value)}</div>'
        f'<div class="teacher-demo-node-meta">{_text(meta)}</div>'
        "</article>"
    )


def _arrow():
    return '<div class="teacher-demo-arrow" aria-hidden="true"></div>'


def _meter(label, value, maximum, color):
    width = _percent(value, maximum)
    return (
        '<div class="teacher-demo-meter-row">'
        f'<div class="teacher-demo-meter-label">{escape(label)}</div>'
        '<div class="teacher-demo-meter-track">'
        f'<div class="teacher-demo-meter-fill" style="--td-width:{width:.2f}%;--td-fill:{color}"></div></div>'
        f'<div class="teacher-demo-meter-value">{int(value or 0)}</div></div>'
    )


def _comparison_bar(name, value, total, color):
    return (
        '<div class="teacher-demo-bar">'
        f'<div class="teacher-demo-bar-name">{escape(name)}</div>'
        '<div class="teacher-demo-bar-track">'
        f'<div class="teacher-demo-bar-fill" style="--td-width:{_percent(value, total):.2f}%;--td-fill:{color}"></div></div>'
        f'<div class="teacher-demo-bar-value">{int(value)}/{int(total)}</div></div>'
    )


def render_teacher_demo(case_id=DEFAULT_SCENARIO_ID, turn_index="1"):
    payload = build_teacher_demo_payload(case_id, int(turn_index or 1))
    cognition = payload["cognition"]
    summary = payload["comparison_summary"]
    model_layers = (cognition.get("model_summary") or {}).get("layers") or {}
    provisional = model_layers.get("provisional") or {}
    stable = model_layers.get("stable") or {}
    situational = model_layers.get("situational") or {}
    withdrawn_total = sum(int((layer or {}).get("withdrawn") or 0) for layer in model_layers.values())
    expired_total = sum(int((layer or {}).get("expired") or 0) for layer in model_layers.values())
    model_total = sum(int((layer or {}).get("total") or 0) for layer in model_layers.values())
    evidence_text = " ／ ".join(cognition.get("evidence") or []) or "只有目前輸入，未加入不可見語氣"
    alternatives = " ／ ".join(cognition.get("alternatives") or []) or "沒有足夠證據時維持未知"
    unknown = "、".join(cognition.get("unknown") or []) or "無新增未知欄位"
    general_status = cognition.get("general_verification") or "not_available"
    status_display = STATUS_LABELS.get(general_status, general_status)
    pragmatic_status = cognition.get("pragmatic_verification") or "not_available"
    outcome_display = (
        f'整體：{STATUS_LABELS.get(general_status, general_status)} ／ '
        f'言外：{STATUS_LABELS.get(pragmatic_status, pragmatic_status)}'
    )
    status_color = {
        "not_available": "#64748b",
        "uncertain": "#facc15",
        "supported": "#34d399",
        "contradicted": "#fb7185",
    }.get(general_status, "#94a3b8")
    plan = cognition.get("plan") or {}
    persona = cognition.get("persona") or {}
    baseline_class = "pass" if payload["baseline"]["contract_pass"] else "fail"
    system_class = "pass" if payload["system"]["contract_pass"] else "fail"
    integrity = payload["integrity"]
    pair_count = int(summary.get("pair_count") or 54)
    baseline_contract = int(summary.get("baseline_visible_contract_pass_count") or 0)
    system_contract = int(summary.get("system_visible_contract_pass_count") or 0)
    baseline_proxy = int(summary.get("baseline_proxy_pass_count") or 0)
    system_proxy = int(summary.get("system_proxy_pass_count") or 0)
    parity = int(summary.get("token_parity_pair_count") or 0)
    revision = cognition.get("last_revision") or {}
    revision_text = (
        f'舊推測「{revision.get("value") or "—"}」：'
        f'{revision.get("status_before") or "—"} → {revision.get("status_after") or "—"}；原紀錄保留。'
        if revision
        else "第一輪只建立暫定模型，尚無可撤銷的上一輪推測。"
    )
    contract_note = "通過 frozen 可見日文／人格 contract" if payload["system"]["contract_pass"] else "這一輪保留為 frozen contract failure"
    raw_hash = str(integrity.get("raw_result_sha256") or "")[:12]
    frozen_label = "6/6 frozen bindings intact" if integrity.get("passed") else "FROZEN SOURCE MISMATCH"
    return (
        '<section class="teacher-demo-shell" aria-label="UruhaBrain 人類語用理解教師展示">'
        '<header class="teacher-demo-hero"><div>'
        '<div class="teacher-demo-eyebrow">One-week research milestone · Human pragmatic understanding</div>'
        f'<div class="teacher-demo-title">{_text(payload["scenario"]["title"])}</div>'
        '<div class="teacher-demo-question">研究問題：同一個基礎模型、相同人格表達與近乎相同 token 預算下，加入可驗證的跨輪理解與修正機制，能否更準確接住言外需求，同時不假裝讀心？</div>'
        '</div><div class="teacher-demo-proof-stamp">'
        f'<strong>{int(summary.get("generation_count") or 0)} fresh outputs</strong>'
        f'<span>{escape(frozen_label)} · RAW {escape(raw_hash)}</span>'
        '</div></header>'
        '<div class="teacher-demo-strip">'
        '<div class="teacher-demo-strip-item"><b>研究主體</b><span>人類語用理解與預測；不是模仿本身</span></div>'
        '<div class="teacher-demo-strip-item"><b>實驗人格</b><span>公開證據約束的 Uruha 表達實例</span></div>'
        '<div class="teacher-demo-strip-item"><b>對外體驗</b><span>自然日文，讓人感到被接住；不倒出分析</span></div>'
        '<div class="teacher-demo-strip-item"><b>對內證據</b><span>假設 → 預測 → 驗證／否定 → 校正</span></div>'
        '</div>'
        '<section class="teacher-demo-story">'
        '<div class="teacher-demo-story-head"><div>'
        f'<h2>{_text(payload["scenario"]["title"])}</h2>'
        f'<p>{_text(payload["scenario"]["research_point"])}</p>'
        f'</div><div class="teacher-demo-turn-chip">TURN {payload["turn_index"]} / {payload["turn_count"]}</div></div>'
        '<div class="teacher-demo-user-signal"><small>CURRENT HUMAN SIGNAL</small>'
        f'{_text(payload["user_text"])}</div>'
        '<div class="teacher-demo-compare">'
        '<article class="teacher-demo-lane"><div class="teacher-demo-lane-label">'
        f'<b>BASELINE｜同模型直接生成</b><span class="teacher-demo-contract {baseline_class}">CONTRACT {"PASS" if payload["baseline"]["contract_pass"] else "FAIL"}</span></div>'
        '<div class="teacher-demo-lane-flow"><span>目前對話</span><i></i><span>黑箱生成</span><i></i><span>回答</span></div>'
        f'<div class="teacher-demo-reply">{_text(payload["baseline"]["reply"])}</div>'
        '<div class="teacher-demo-lane-note">沒有 structured hypothesis、prediction、verification、calibration 或 persistent other-model 可供檢查。</div></article>'
        '<div class="teacher-demo-versus"><span>VS</span></div>'
        '<article class="teacher-demo-lane is-system"><div class="teacher-demo-lane-label">'
        f'<b>URUHABRAIN｜可校正語用循環</b><span class="teacher-demo-contract {system_class}">CONTRACT {"PASS" if payload["system"]["contract_pass"] else "FAIL"}</span></div>'
        '<div class="teacher-demo-lane-flow"><span>觀察</span><i></i><span>暫定理解</span><i></i><span>驗證／修正</span><i></i><span>回答</span></div>'
        f'<div class="teacher-demo-reply">{_text(payload["system"]["reply"])}</div>'
        f'<div class="teacher-demo-lane-note">{escape(contract_note)}；內部推測不會寫成私人心理事實。</div></article>'
        '</div></section>'
        '<section class="teacher-demo-graph-section">'
        '<div class="teacher-demo-section-label">Inspectable cognitive loop</div>'
        '<h2 class="teacher-demo-graph-title">這一輪到底發生了什麼</h2>'
        '<div class="teacher-demo-cog-graph">'
        + _node("◎", "OBSERVATION", payload["user_text"], "只把可見文字當已知", "#38bdf8")
        + _arrow()
        + _node("≋", "LITERAL", cognition.get("literal"), "text input · acoustic unavailable", "#60a5fa")
        + _arrow()
        + _node("◐", "PRAGMATIC HYPOTHESIS", cognition.get("pragmatic_display"), f'confidence {cognition.get("communicative_confidence")}', "#a78bfa")
        + _arrow()
        + _node("↗", "NEXT PREDICTION", cognition.get("prediction"), f'confidence {cognition.get("prediction_confidence")}', "#2dd4bf")
        + _arrow()
        + _node("✓", "LATER OUTCOME", outcome_display, cognition.get("general_verification_summary"), status_color)
        + '</div>'
        '<div class="teacher-demo-branch">'
        + _node("⌁", "EVIDENCE", evidence_text, "可追溯到目前輸入", "#38bdf8")
        + _node("?", "ALTERNATIVES / UNKNOWN", alternatives, f'未知：{unknown}', "#facc15")
        + _node("∞", "RELATIONSHIP / NEED", cognition.get("implicit_need"), cognition.get("relationship_signal"), "#f472b6")
        + '</div></section>'
        '<section class="teacher-demo-model">'
        '<div class="teacher-demo-model-panel"><div class="teacher-demo-section-label">Persistent other-model</div><h3>理解不是每輪重來；也不是永遠相信舊資料</h3>'
        + _meter("穩定偏好 active", (stable.get("active") or 0), max(1, stable.get("total") or 1), "#38bdf8")
        + _meter("暫時目標 active", (situational.get("active") or 0), max(1, situational.get("total") or 1), "#2dd4bf")
        + _meter("待驗證 active", (provisional.get("active") or 0), max(1, provisional.get("total") or 1), "#a78bfa")
        + _meter("已撤回 withdrawn", withdrawn_total, max(1, model_total), "#fb7185")
        + _meter("已過期 expired", expired_total, max(1, model_total), "#fb923c")
        + '</div><div class="teacher-demo-model-panel"><div class="teacher-demo-section-label">Correction → persona → action</div><h3>錯誤會留下來，並改變下一步</h3>'
        f'<div class="teacher-demo-revision"><b>{_text(status_display)}</b><br>{_text(revision_text)}</div>'
        + _node("⌬", "PUBLIC PERSONA APPRAISAL", "直接但不冒充知道對方內心", f'{len(persona.get("evidence_refs") or [])} public evidence refs · private unknown kept blank', "#818cf8")
        + _node("◆", "ACTION / SURFACE", plan.get("reply_goal"), plan.get("core_message_jp"), "#34d399")
        + '</div></section>'
        '<section class="teacher-demo-evidence"><div class="teacher-demo-section-label">Frozen same-model comparison</div><h3>不是只放一個好看的案例：完整 54 組輸出全部保留</h3>'
        '<div class="teacher-demo-bars">'
        '<div class="teacher-demo-bar-row"><div class="teacher-demo-bar-label"><b>自然日文／人格 contract</b><span>自動契約；不是人類偏好</span></div><div class="teacher-demo-bar-pair">'
        + _comparison_bar("Baseline", baseline_contract, pair_count, "#64748b")
        + _comparison_bar("UruhaBrain", system_contract, pair_count, "#2dd4bf")
        + '</div></div>'
        '<div class="teacher-demo-bar-row"><div class="teacher-demo-bar-label"><b>語義 anchor proxy</b><span>只檢查明顯命中與過度斷言</span></div><div class="teacher-demo-bar-pair">'
        + _comparison_bar("Baseline", baseline_proxy, pair_count, "#64748b")
        + _comparison_bar("UruhaBrain", system_proxy, pair_count, "#a78bfa")
        + '</div></div>'
        '<div class="teacher-demo-bar-row"><div class="teacher-demo-bar-label"><b>Token fairness gate</b><span>兩條件 prompt_eval 差值皆在 gate 內</span></div><div class="teacher-demo-bar-pair">'
        + _comparison_bar("Paired gate", parity, pair_count, "#34d399")
        + '</div></div></div>'
        '<div class="teacher-demo-boundary">'
        '<div class="teacher-demo-boundary-step" style="--td-step:#34d399"><b>1 · Mechanism</b><span>已證明可形成、驗證與撤銷推測</span></div>'
        '<div class="teacher-demo-boundary-step" style="--td-step:#34d399"><b>2 · Fresh generation</b><span>108 個本機新輸出已完成</span></div>'
        '<div class="teacher-demo-boundary-step" style="--td-step:#facc15"><b>3 · Full Web pipeline</b><span>核心案例通過，仍有已知 edge failures</span></div>'
        '<div class="teacher-demo-boundary-step" style="--td-step:#fb7185"><b>4 · Human superiority</b><span>尚缺三位獨立盲評；禁止先宣稱</span></div>'
        '</div></section>'
        '<footer class="teacher-demo-foot">'
        '<span><strong>能主張：</strong>可觀察、可反駁、可修正的語用理解機制與 frozen fresh outputs。</span>'
        '<span><strong>不能主張：</strong>意識、讀心、真人等價、普遍優於 LLM 或 production ready。</span>'
        f'<span><strong>寫入：</strong>{payload["production_memory_write_count"]} production memory writes</span>'
        '</footer></section>'
    )


def advance_teacher_demo(case_id=DEFAULT_SCENARIO_ID, turn_index="1"):
    next_turn = 1 if int(turn_index or 1) >= 3 else int(turn_index or 1) + 1
    next_value = str(next_turn)
    return next_value, render_teacher_demo(case_id, next_value)
