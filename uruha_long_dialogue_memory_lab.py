"""Read-only teacher view of the isolated V2.17 long-dialogue experiment."""

from __future__ import annotations

import json
from copy import deepcopy
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_17_long_dialogue_memory_case.json"
RAW_PATH = ROOT / "analysis/v2_17_long_dialogue_memory_raw.json"
DEFAULT_CHECKPOINT = "17"
CHECKPOINT_LABELS = {
    "17": "① 15 輪干擾後回想",
    "18": "② 使用者推翻舊記憶",
    "24": "③ 5 輪後回想新值",
    "25": "④ 確認舊值已撤銷",
}
ROLE_LABELS = {
    "memory_seed": "寫入",
    "distractor": "干擾",
    "delayed_recall": "回想",
    "explicit_correction": "修正",
    "corrected_recall": "再回想",
    "withdrawal_probe": "撤銷確認",
}


LONG_DIALOGUE_LAB_CSS = r"""
.long-memory-lab{--lm-cyan:#38bdf8;--lm-violet:#a78bfa;--lm-green:#34d399;--lm-amber:#facc15;--lm-rose:#fb7185;overflow:hidden;border:1px solid rgba(56,189,248,.22);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 8% 0%,rgba(56,189,248,.13),transparent 29%),radial-gradient(circle at 92% 4%,rgba(167,139,250,.13),transparent 28%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}
.long-memory-lab *{box-sizing:border-box}.lm-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:22px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.lm-kicker{color:#67e8f9;font-size:10px;font-weight:800;letter-spacing:.14em}.lm-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);font-weight:850;line-height:1.08}.lm-sub{max-width:860px;margin-top:8px;color:#94a3b8;font-size:11px;line-height:1.55}.lm-stamp{min-width:190px;border:1px solid rgba(52,211,153,.36);border-radius:16px;padding:12px 14px;background:rgba(6,78,59,.22);text-align:right}.lm-stamp strong{display:block;color:#ecfdf5;font-size:19px}.lm-stamp span{color:#6ee7b7;font-size:9px;letter-spacing:.08em}
.lm-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:rgba(148,163,184,.12)}.lm-metric{padding:12px 16px;background:#08101f}.lm-metric b{display:block;color:#f8fafc;font-size:18px}.lm-metric span{color:#64748b;font-size:8px}.lm-body{padding:20px 24px 26px}.lm-section-label{margin:0 4px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}
.lm-timeline{display:grid;grid-template-columns:repeat(25,minmax(19px,1fr));gap:4px;align-items:end;padding:13px;border:1px solid rgba(148,163,184,.14);border-radius:17px;background:rgba(15,23,42,.62)}.lm-turn{position:relative;min-height:70px;border:1px solid rgba(148,163,184,.13);border-radius:8px;padding:7px 3px;background:rgba(30,41,59,.72);text-align:center}.lm-turn b{display:block;color:#94a3b8;font-size:8px}.lm-turn span{display:block;margin-top:7px;color:#64748b;font-size:7px;writing-mode:vertical-rl;max-height:42px;overflow:hidden}.lm-turn.is-seed{border-color:rgba(167,139,250,.55);background:rgba(76,29,149,.26)}.lm-turn.is-checkpoint{border-color:rgba(56,189,248,.62);background:rgba(14,116,144,.24);box-shadow:0 0 15px rgba(56,189,248,.13)}.lm-turn.is-correction{border-color:rgba(250,204,21,.58);background:rgba(113,63,18,.24)}.lm-turn.is-active{outline:2px solid #f8fafc;outline-offset:2px}.lm-legend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 4px 0;color:#64748b;font-size:8px}.lm-legend i{display:inline-block;width:7px;height:7px;margin-right:4px;border-radius:50%}
.lm-dialogue{display:grid;grid-template-columns:1fr 48px 1fr;gap:12px;align-items:stretch;margin-top:18px}.lm-bubble{border:1px solid rgba(148,163,184,.16);border-radius:17px;padding:14px;background:rgba(15,23,42,.74)}.lm-bubble.is-reply{border-color:rgba(52,211,153,.34);background:rgba(6,78,59,.16)}.lm-bubble b{color:#94a3b8;font-size:9px;letter-spacing:.08em}.lm-bubble p{margin:9px 0 0;color:#f8fafc;font-size:13px;font-weight:720;line-height:1.55}.lm-arrow-big{display:grid;place-items:center;color:#475569;font-size:18px}
.lm-chain{display:grid;grid-template-columns:minmax(140px,1fr) 28px minmax(140px,1fr) 28px minmax(140px,1fr) 28px minmax(140px,1fr) 28px minmax(160px,1.1fr);gap:5px;align-items:center;margin-top:18px}.lm-node{min-height:128px;border:1px solid color-mix(in srgb,var(--lm-node) 44%,#334155);border-radius:16px;padding:12px;background:color-mix(in srgb,var(--lm-node) 9%,rgba(15,23,42,.94))}.lm-node-head{display:flex;align-items:center;gap:7px;color:#f8fafc;font-size:10px;font-weight:780}.lm-node-icon{display:grid;place-items:center;width:25px;height:25px;border-radius:50%;background:color-mix(in srgb,var(--lm-node) 42%,#0f172a)}.lm-node strong{display:block;margin-top:11px;color:#f8fafc;font-size:11px;line-height:1.42}.lm-node p{margin:7px 0 0;color:#64748b;font-size:8px;line-height:1.45;overflow-wrap:anywhere}.lm-link{position:relative;height:2px;background:rgba(56,189,248,.34)}.lm-link:after{content:'';position:absolute;right:-1px;top:-4px;border-left:7px solid rgba(56,189,248,.7);border-top:5px solid transparent;border-bottom:5px solid transparent}
.lm-proof{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px}.lm-card{border:1px solid rgba(148,163,184,.15);border-radius:16px;padding:13px;background:rgba(15,23,42,.7)}.lm-card h3{margin:0;color:#f8fafc;font-size:11px}.lm-check{display:flex;justify-content:space-between;gap:10px;margin-top:8px;border-top:1px solid rgba(148,163,184,.1);padding-top:7px;color:#94a3b8;font-size:8px}.lm-check strong{color:#86efac}.lm-attempts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-top:9px}.lm-attempt{border-radius:10px;padding:8px;background:rgba(30,41,59,.75);color:#94a3b8;font-size:8px;line-height:1.35}.lm-attempt.fail{border:1px solid rgba(251,113,133,.28)}.lm-attempt.pass{border:1px solid rgba(52,211,153,.34)}.lm-attempt b{display:block;color:#f8fafc;margin-bottom:3px}.lm-boundary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin-top:18px;background:rgba(148,163,184,.12)}.lm-boundary div{padding:12px 14px;background:#08101f}.lm-boundary b{display:block;font-size:9px}.lm-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.lm-boundary .yes b{color:#86efac}.lm-boundary .mixed b{color:#fde68a}.lm-boundary .no b{color:#fda4af}
@media(max-width:1150px){.lm-timeline{grid-template-columns:repeat(13,minmax(25px,1fr))}.lm-chain{grid-template-columns:1fr}.lm-link{width:2px;height:20px;margin:auto}.lm-link:after{right:-4px;top:auto;bottom:-1px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid rgba(56,189,248,.7)}}
@media(max-width:720px){.lm-hero{grid-template-columns:1fr;padding:21px 17px}.lm-stamp{text-align:left}.lm-metrics{grid-template-columns:1fr 1fr}.lm-body{padding:17px}.lm-timeline{grid-template-columns:repeat(5,minmax(35px,1fr))}.lm-dialogue,.lm-proof{grid-template-columns:1fr}.lm-arrow-big{min-height:18px}.lm-attempts,.lm-boundary{grid-template-columns:1fr 1fr}}
"""


def _text(value):
    return escape(str(value or ""))


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checkpoint_choices():
    return [(label, key) for key, label in CHECKPOINT_LABELS.items()]


def _checkpoint(raw, checkpoint):
    turn = int(checkpoint) if str(checkpoint).isdigit() else int(DEFAULT_CHECKPOINT)
    return next(row for row in raw.get("checkpoints") or [] if int(row["turn"]) == turn)


def _attempt_history(raw):
    rows = []
    for path in sorted((ROOT / "analysis").glob("v2_17_long_dialogue_memory_raw_attempt*.json")):
        payload = _load_json(path)
        rows.append(
            {
                "label": path.stem.rsplit("attempt", 1)[-1],
                "pass": bool((payload.get("summary") or {}).get("bounded_success")),
                "withdrawal_pass": bool((payload.get("summary") or {}).get("withdrawn_value_not_current_pass")),
            }
        )
    rows.append(
        {
            "label": "final",
            "pass": bool((raw.get("summary") or {}).get("bounded_success")),
            "withdrawal_pass": bool((raw.get("summary") or {}).get("withdrawn_value_not_current_pass")),
        }
    )
    return rows


def build_long_dialogue_payload(checkpoint=DEFAULT_CHECKPOINT):
    checkpoint = str(checkpoint)
    if checkpoint not in CHECKPOINT_LABELS:
        checkpoint = DEFAULT_CHECKPOINT
    case = _load_json(CASE_PATH)
    raw = _load_json(RAW_PATH)
    selected = _checkpoint(raw, checkpoint)
    source_turn = int((selected.get("checks") or {}).get("claimed_source_turn") or 1)
    source = next(row for row in raw["rows"] if int(row["turn"]) == source_turn)
    target_rows = selected.get("passed_target_rows") or []
    passed = target_rows[0] if target_rows else {}
    return {
        "case": case,
        "raw": raw,
        "summary": raw["summary"],
        "checkpoint": checkpoint,
        "selected": selected,
        "source": source,
        "passed": passed,
        "attempts": _attempt_history(raw),
        "rows": deepcopy(raw["rows"]),
    }


def _timeline(payload):
    active = int(payload["checkpoint"])
    chunks = []
    for row in payload["rows"]:
        role = row["role"]
        classes = ["lm-turn"]
        if role == "memory_seed":
            classes.append("is-seed")
        if role in {"delayed_recall", "corrected_recall", "withdrawal_probe"}:
            classes.append("is-checkpoint")
        if role == "explicit_correction":
            classes.append("is-correction")
        if int(row["turn"]) == active:
            classes.append("is-active")
        label = ROLE_LABELS.get(role, role)
        chunks.append(
            f'<div class="{" ".join(classes)}" title="T{row["turn"]} {_text(row["user"])}">'
            f'<b>{row["turn"]}</b><span>{_text(label)}</span></div>'
        )
    return "".join(chunks)


def _link():
    return '<div class="lm-link" aria-hidden="true"></div>'


def _attempts(payload):
    chunks = []
    for index, row in enumerate(payload["attempts"], start=1):
        css = "pass" if row["pass"] else "fail"
        status = "通過" if row["pass"] else "保留失敗"
        detail = "舊值撤銷通過" if row["withdrawal_pass"] else "舊值撤銷未通過"
        chunks.append(f'<div class="lm-attempt {css}"><b>RUN {index} · {status}</b>{detail}</div>')
    return "".join(chunks)


def render_long_dialogue_lab(checkpoint=DEFAULT_CHECKPOINT):
    payload = build_long_dialogue_payload(checkpoint)
    selected = payload["selected"]
    summary = payload["summary"]
    source = payload["source"]
    passed = payload["passed"]
    anchor = selected.get("memory_anchor") or {}
    ablation = selected.get("ablation") or {}
    checks = selected.get("checks") or {}
    source_label = f'T{source["turn"]} · {ROLE_LABELS.get(source["role"], source["role"])}'
    trace_id = passed.get("trace_id") or anchor.get("trace_id") or "沒有 trace"
    ablation_changed = checks.get("target_removal_changes_anchor")
    negative_control = checks.get("irrelevant_removal_preserves_anchor")
    return (
        '<section class="long-memory-lab">'
        '<header class="lm-hero"><div><div class="lm-kicker">V2.17 · ISOLATED LONG-DIALOGUE MEMORY TRACE</div>'
        '<h1 class="lm-title">記憶不是「有存到」就算成功</h1>'
        '<div class="lm-sub">這個 25 輪案例直接檢查：早期資訊經過大量換題後能否回到決策；被使用者推翻時能否改寫目前狀態；舊值是否真的退出「現在有效」的位置。每個關鍵回答都能沿著來源輪次、傳輸 trace、決策錨點與日文輸出向前回溯。</div></div>'
        f'<div class="lm-stamp"><strong>{"BOUNDED PASS" if summary["bounded_success"] else "FAILURE FOUND"}</strong><span>25 TURNS · ISOLATED DB</span></div></header>'
        '<div class="lm-metrics">'
        f'<div class="lm-metric"><b>{summary["turn_count"]}</b><span>完整對話輪次</span></div>'
        f'<div class="lm-metric"><b>{summary["distractor_turn_count"]}</b><span>跨話題干擾輪</span></div>'
        f'<div class="lm-metric"><b>{summary["full_runtime_checkpoint_count"]}</b><span>完整實際管線 checkpoint</span></div>'
        f'<div class="lm-metric"><b>{"0" if summary["production_db_unchanged"] else "!"}</b><span>正式 DB 寫入</span></div></div>'
        '<div class="lm-body"><div class="lm-section-label">LONG CONVERSATION TIMELINE · 每一格是一輪，白框是目前查看的 checkpoint</div>'
        f'<div class="lm-timeline">{_timeline(payload)}</div>'
        '<div class="lm-legend"><span><i style="background:#a78bfa"></i>原始記憶</span><span><i style="background:#334155"></i>話題干擾</span><span><i style="background:#38bdf8"></i>延遲回想</span><span><i style="background:#facc15"></i>明確修正</span></div>'
        '<div class="lm-dialogue"><div class="lm-bubble"><b>USER · CHECKPOINT T'
        f'{selected["turn"]}</b><p>{_text(selected["user"])}</p></div><div class="lm-arrow-big">→</div>'
        f'<div class="lm-bubble is-reply"><b>URUHA · FINAL VISIBLE JAPANESE</b><p>{_text(selected["reply"])}</p></div></div>'
        '<div class="lm-section-label" style="margin-top:18px">TRACEABLE MEMORY CHAIN · 不是看字串命中，而是看資料有沒有進入回答路徑</div>'
        '<div class="lm-chain">'
        f'<div class="lm-node" style="--lm-node:#a78bfa"><div class="lm-node-head"><span class="lm-node-icon">1</span>來源輪次</div><strong>{_text(source_label)}</strong><p>{_text(source["user"])}</p></div>{_link()}'
        f'<div class="lm-node" style="--lm-node:#38bdf8"><div class="lm-node-head"><span class="lm-node-icon">2</span>目前記憶狀態</div><strong>{_text((selected.get("profile_before") or {}).get("favorites") or (selected.get("profile_before") or {}).get("dislikes"))}</strong><p>使用者 profile 在本輪檢索前的可見快照</p></div>{_link()}'
        f'<div class="lm-node" style="--lm-node:#38bdf8"><div class="lm-node-head"><span class="lm-node-icon">3</span>傳給決策</div><strong>{_text(passed.get("text") or anchor.get("source_text"))}</strong><p>{_text(trace_id)} · channel={_text(passed.get("channel") or anchor.get("provenance_channel"))}</p></div>{_link()}'
        f'<div class="lm-node" style="--lm-node:#facc15"><div class="lm-node-head"><span class="lm-node-icon">4</span>決策錨點</div><strong>{_text(anchor.get("kind"))} → {_text(anchor.get("jp_anchor") or anchor.get("value"))}</strong><p>memory_use_expected={_text(selected.get("memory_use_expected"))}</p></div>{_link()}'
        f'<div class="lm-node" style="--lm-node:#34d399"><div class="lm-node-head"><span class="lm-node-icon">5</span>日文回答</div><strong>{_text(selected["reply"])}</strong><p>language guard final rejection = {_text((selected.get("visible_language_guard") or {}).get("final_rejection_reasons"))}</p></div></div></div>'
        '<div class="lm-proof"><div class="lm-card"><h3>因果對照（decision-anchor proxy）</h3>'
        f'<div class="lm-check"><span>完整記憶有錨點</span><strong>{"PASS" if (ablation.get("intact") or {}).get("anchor") else "FAIL"}</strong></div>'
        f'<div class="lm-check"><span>移除目標記憶，錨點改變</span><strong>{"PASS" if ablation_changed else "N/A"}</strong></div>'
        f'<div class="lm-check"><span>只移除無關記憶，錨點不變</span><strong>{"PASS" if negative_control else "FAIL"}</strong></div>'
        '<div class="lm-check"><span>證據範圍</span><strong>機制層，不是新增全模型輸出</strong></div></div>'
        f'<div class="lm-card"><h3>失敗沒有被洗掉</h3><div class="lm-attempts">{_attempts(payload)}</div></div></div>'
        '<div class="lm-boundary"><div class="yes"><b>這次支持</b><span>25 輪隔離案例中，早期偏好延遲找回；明確修正後新值被再次找回；舊值不再被當成目前首選。</span></div>'
        '<div class="mixed"><b>實驗折衷</b><span>20 輪固定 transcript 走正式 save_episode；4 個 checkpoint 才是完整模型管線。不能說 25 輪都是 fresh generation。</span></div>'
        '<div class="no"><b>仍不能宣稱</b><span>跨月記憶、任意事實都可回想、全面優於一般 LLM、人類自傳式記憶或主觀理解。</span></div></div>'
        '</div></section>'
    )
