"""Graphical, read-only view of V2.18–V2.22 memory remediation evidence."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_19_fifty_turn_memory_remediation_comparison.json"
V218_PATH = ROOT / "analysis/v2_18_fifty_turn_memory_comparison_raw.json"
V219_PATH = ROOT / "analysis/v2_19_fifty_turn_memory_remediation_raw.json"
V221_PATH = ROOT / "analysis/v2_21_relational_polarity_replay_raw.json"
V222_PATH = ROOT / "analysis/v2_22_stable_relational_source_replay_raw.json"
DEFAULT_CHECKPOINT = "50"
CHECKPOINT_LABELS = {
    "25": "① 舊值長距離回溯",
    "26": "② 明確更新必須承接",
    "48": "③ 新值長距離回溯",
    "49": "④ 舊值撤回確認",
    "50": "⑤ 人物綁定嚴格控制",
}
ROLE_LABELS = {
    "delayed_recall": "24 輪後回溯",
    "explicit_correction": "明確更新",
    "corrected_recall": "22 輪後回溯新值",
    "withdrawal_probe": "撤回舊值",
    "false_memory_control": "人物誤綁控制",
}


MEMORY_REPAIR_LAB_CSS = r"""
.repair-lab{--r-blue:#38bdf8;--r-green:#34d399;--r-amber:#fbbf24;--r-red:#fb7185;--r-violet:#a78bfa;overflow:hidden;border:1px solid rgba(56,189,248,.24);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 8% 0%,rgba(56,189,248,.13),transparent 30%),radial-gradient(circle at 94% 4%,rgba(251,113,133,.11),transparent 29%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.48)}
.repair-lab *{box-sizing:border-box}.rp-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.rp-kicker{color:#67e8f9;font-size:10px;font-weight:800;letter-spacing:.14em}.rp-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);font-weight:850;line-height:1.08}.rp-sub{max-width:900px;margin-top:8px;color:#94a3b8;font-size:11px;line-height:1.55}.rp-stamp{min-width:220px;border:1px solid rgba(251,191,36,.38);border-radius:16px;padding:12px 14px;background:rgba(113,63,18,.24);text-align:right}.rp-stamp strong{display:block;color:#fef3c7;font-size:18px}.rp-stamp span{color:#fcd34d;font-size:9px;letter-spacing:.07em}
.rp-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;background:rgba(148,163,184,.12)}.rp-metric{padding:12px 15px;background:#08101f}.rp-metric b{display:block;color:#f8fafc;font-size:18px}.rp-metric span{color:#64748b;font-size:8px;line-height:1.35}.rp-body{padding:20px 24px 26px}.rp-label{margin:0 4px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}
.rp-repairs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.rp-repair{border:1px solid rgba(148,163,184,.15);border-radius:15px;padding:12px;background:rgba(15,23,42,.72)}.rp-repair.pass{border-color:rgba(52,211,153,.34);background:rgba(6,78,59,.15)}.rp-repair.partial{border-color:rgba(251,191,36,.35);background:rgba(113,63,18,.13)}.rp-repair b{display:block;color:#f8fafc;font-size:11px}.rp-repair strong{display:block;margin-top:7px;color:#86efac;font-size:10px}.rp-repair.partial strong{color:#fde68a}.rp-repair span{display:block;margin-top:5px;color:#94a3b8;font-size:8px;line-height:1.45}
.rp-timeline{display:grid;grid-template-columns:repeat(25,minmax(18px,1fr));gap:3px;margin-top:17px;padding:11px;border:1px solid rgba(148,163,184,.14);border-radius:16px;background:rgba(15,23,42,.58)}.rp-turn{height:38px;border:1px solid rgba(148,163,184,.12);border-radius:7px;padding-top:6px;background:rgba(30,41,59,.7);text-align:center;color:#64748b;font-size:7px}.rp-turn b{display:block;color:#94a3b8;font-size:8px}.rp-turn.seed{background:rgba(76,29,149,.3);border-color:rgba(167,139,250,.5)}.rp-turn.relation{background:rgba(113,63,18,.24);border-color:rgba(251,191,36,.3)}.rp-turn.checkpoint{background:rgba(14,116,144,.24);border-color:rgba(56,189,248,.6)}.rp-turn.active{outline:2px solid #f8fafc;outline-offset:2px}
.rp-question{margin-top:15px;border:1px solid rgba(56,189,248,.28);border-radius:15px;padding:13px 15px;background:rgba(14,116,144,.12)}.rp-question b{color:#7dd3fc;font-size:9px}.rp-question p{margin:7px 0 0;color:#f8fafc;font-size:14px;font-weight:760}.rp-lanes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}.rp-lane{--lane:#94a3b8;border:1px solid color-mix(in srgb,var(--lane) 38%,#334155);border-radius:16px;padding:13px;background:color-mix(in srgb,var(--lane) 7%,rgba(15,23,42,.88))}.rp-lane.system{--lane:var(--r-blue)}.rp-lane.recent{--lane:var(--r-amber)}.rp-lane.full{--lane:var(--r-violet)}.rp-lane-head{display:flex;justify-content:space-between;gap:8px}.rp-lane-head b{color:#f8fafc;font-size:11px}.rp-verdict{border-radius:999px;padding:3px 7px;font-size:8px}.rp-verdict.pass{background:rgba(6,78,59,.4);color:#86efac}.rp-verdict.partial{background:rgba(113,63,18,.38);color:#fde68a}.rp-verdict.fail{background:rgba(127,29,29,.35);color:#fda4af}.rp-access{min-height:29px;margin-top:7px;color:#64748b;font-size:8px;line-height:1.4}.rp-reply{min-height:70px;margin-top:9px;border:1px solid rgba(148,163,184,.12);border-radius:11px;padding:10px;background:rgba(2,6,23,.5);color:#f8fafc;font-size:12px;font-weight:680;line-height:1.5}.rp-note{margin-top:8px;color:#94a3b8;font-size:8px;line-height:1.45}.rp-chain{display:grid;grid-template-columns:1fr 26px 1fr 26px 1fr 26px 1fr;gap:6px;align-items:center;margin-top:17px}.rp-node{min-height:98px;border:1px solid rgba(56,189,248,.24);border-radius:13px;padding:10px;background:rgba(14,116,144,.08)}.rp-node.warn{border-color:rgba(251,191,36,.35);background:rgba(113,63,18,.1)}.rp-node b{display:block;color:#7dd3fc;font-size:8px}.rp-node.warn b{color:#fcd34d}.rp-node strong{display:block;margin-top:7px;color:#f8fafc;font-size:10px;line-height:1.42;overflow-wrap:anywhere}.rp-node span{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.4}.rp-arrow{height:2px;background:rgba(56,189,248,.34)}
.rp-progress{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:17px}.rp-stage{border-top:2px solid rgba(148,163,184,.24);padding:10px 3px 0}.rp-stage b{color:#f8fafc;font-size:10px}.rp-stage p{min-height:44px;margin:6px 0 0;color:#94a3b8;font-size:8px;line-height:1.48}.rp-stage .answer{color:#e2e8f0;font-size:9px}.rp-analysis{display:grid;grid-template-columns:1.15fr .85fr;gap:11px;margin-top:17px}.rp-card{border:1px solid rgba(148,163,184,.15);border-radius:15px;padding:13px;background:rgba(15,23,42,.7)}.rp-card h3{margin:0;color:#f8fafc;font-size:11px}.rp-finding{margin-top:8px;padding-top:8px;border-top:1px solid rgba(148,163,184,.1);color:#94a3b8;font-size:8px;line-height:1.5}.rp-finding b{color:#f8fafc}.rp-cost{display:grid;grid-template-columns:105px 1fr auto;gap:7px;align-items:center;margin-top:8px;color:#94a3b8;font-size:8px}.rp-bar{height:7px;border-radius:999px;background:rgba(148,163,184,.12);overflow:hidden}.rp-bar i{display:block;height:100%;border-radius:999px;background:var(--r-blue)}.rp-boundary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin-top:17px;background:rgba(148,163,184,.12)}.rp-boundary div{padding:11px 13px;background:#08101f}.rp-boundary b{display:block;font-size:9px}.rp-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.rp-boundary .yes b{color:#86efac}.rp-boundary .mixed b{color:#fde68a}.rp-boundary .no b{color:#fda4af}
@media(max-width:1000px){.rp-metrics{grid-template-columns:repeat(3,1fr)}.rp-lanes,.rp-analysis{grid-template-columns:1fr}.rp-chain{grid-template-columns:1fr}.rp-arrow{width:2px;height:18px;margin:auto}.rp-timeline{grid-template-columns:repeat(10,minmax(24px,1fr))}}
@media(max-width:650px){.rp-hero{grid-template-columns:1fr;padding:20px 16px}.rp-stamp{text-align:left}.rp-metrics,.rp-repairs,.rp-progress,.rp-boundary{grid-template-columns:1fr}.rp-body{padding:16px}.rp-timeline{grid-template-columns:repeat(5,minmax(30px,1fr))}}
"""


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _text(value):
    return escape(str(value or ""))


def checkpoint_choices():
    return [(label, turn) for turn, label in CHECKPOINT_LABELS.items()]


def _comparison(raw, turn):
    return next(row for row in raw["comparisons"] if int(row["turn"]) == int(turn))


def _timeline(case, active):
    cells = []
    for row in case["turns"]:
        classes = ["rp-turn"]
        if row["role"] == "memory_seed":
            classes.append("seed")
        if row["role"] == "relational_distractor":
            classes.append("relation")
        if row["execution"] == "full_runtime_comparison":
            classes.append("checkpoint")
        if int(row["turn"]) == int(active):
            classes.append("active")
        cells.append(
            f'<div class="{" ".join(classes)}" title="{_text(row["role"])} · {_text(row["user"])}"><b>{row["turn"]}</b>{_text(row["role"][:3])}</div>'
        )
    return "".join(cells)


def _verdict(condition, turn):
    turn = int(turn)
    if condition == "uruha_memory":
        return "pass" if turn in {25, 26, 48, 49} else "partial"
    if condition == "plain_recent":
        return "partial" if turn in {26, 50} else "fail"
    return "pass" if turn in {25, 26, 48} else "partial"


def _lane(selected, condition):
    row = selected["conditions"][condition]
    labels = {
        "uruha_memory": ("UruhaBrain · 修正後", "system", "外部記憶＋profile＋可追溯 anchor"),
        "plain_recent": ("單純 LLM · 最近 8 輪", "recent", "來源離開視窗後只能依近期內容生成"),
        "plain_full": ("單純 LLM · 完整 50 輪", "full", "看得到完整原文，沒有結構化記憶 trace"),
    }
    label, css, access = labels[condition]
    verdict = _verdict(condition, selected["turn"])
    score = row.get("score") or {}
    note = {
        (25, "uruha_memory"): "從 profile 指回 T1；具來源且答對。",
        (25, "plain_recent"): "來源不在 8 輪內，生成了不存在的カフェラテ。",
        (25, "plain_full"): "完整原文中有 T1，因此正確回溯。",
        (26, "uruha_memory"): "明確更新不再被澄清策略蓋過，回答與 profile 同步。",
        (26, "plain_recent"): "看得到當輪更新，但日文略不自然。",
        (26, "plain_full"): "看得到當輪更新並直接承接。",
        (48, "uruha_memory"): "T26 已離開近期視窗，仍從 profile 回溯ほうじ茶。",
        (48, "plain_recent"): "錯猜成レモネード，且混入中文。",
        (48, "plain_full"): "完整 transcript 中有 T26，正確回溯。",
        (49, "uruha_memory"): "直接說麦茶是舊資訊；沒有復活舊值。",
        (49, "plain_recent"): "把已撤回的麦茶重新說成目前最愛。",
        (49, "plain_full"): "內容知道現在是ほうじ茶，但表面混入英文且過度道歉。",
        (50, "uruha_memory"): "正確否定使用者說過，但沒有穩定回溯 T41 的朋友來源。",
        (50, "plain_recent"): "否定レモネード後，又把已撤回的麦茶說成目前最愛。",
        (50, "plain_full"): "正確否定並給出ほうじ茶，但沒有指出朋友來源。",
    }.get((int(selected["turn"]), condition), "")
    return f"""
    <div class="rp-lane {css}">
      <div class="rp-lane-head"><b>{_text(label)}</b><span class="rp-verdict {verdict}">{verdict.upper()}</span></div>
      <div class="rp-access">{_text(access)}</div>
      <div class="rp-reply">{_text(row.get('reply'))}</div>
      <div class="rp-note">觀察：{_text(note)}<br>凍結 auto task={"✓" if score.get("task_pass") else "×"} · 日文={"✓" if score.get("visible_japanese_contract_pass") else "×"}</div>
    </div>
    """


def _trace_chain(selected, case):
    system = selected["conditions"]["uruha_memory"]
    anchor = system.get("memory_anchor") or {}
    turn = int(selected["turn"])
    if turn == 50:
        observed = next(row["user"] for row in case["turns"] if int(row["turn"]) == 41)
        selected_source = "T41 不在 recent 8；本輪 ranked retrieval 未選入"
        source_class = "warn"
    else:
        observed = (system.get("passed_target_rows") or [{}])[0].get("text") or system.get("profile_before")
        selected_source = (system.get("passed_target_rows") or [{}])[0].get("trace_id") or anchor.get("trace_id")
        source_class = ""
    return f"""
    <div class="rp-chain">
      <div class="rp-node"><b>1 · 對話中存在的事件</b><strong>{_text(observed)}</strong><span>可觀察證據，不是模型猜測</span></div><div class="rp-arrow"></div>
      <div class="rp-node {source_class}"><b>2 · 本輪送入決策的來源</b><strong>{_text(selected_source)}</strong><span>{"來源落在工作視窗之外" if turn == 50 else "source trace retained"}</span></div><div class="rp-arrow"></div>
      <div class="rp-node {source_class}"><b>3 · 決策錨點</b><strong>{_text(anchor.get('kind'))} → {_text(anchor.get('jp_anchor') or anchor.get('value'))}</strong><span>{_text(anchor.get('source_text'))}</span></div><div class="rp-arrow"></div>
      <div class="rp-node {source_class}"><b>4 · 最終回答</b><strong>{_text(system.get('reply'))}</strong><span>{"否定正確，但人物來源遺失" if turn == 50 else "回答與狀態一致"}</span></div>
    </div>
    """


def _repair_progress(v219, v221, v222, turn):
    before = _comparison(v219, turn)["conditions"]["uruha_memory"]["reply"]
    middle = _comparison(v221, turn)["conditions"]["uruha_memory"]["reply"]
    latest = _comparison(v222, turn)["conditions"]["uruha_memory"]["reply"]
    return f"""
    <div class="rp-progress">
      <div class="rp-stage"><b>V2.19 · 第一次新值測試</b><p class="answer">{_text(before)}</p><p>修正更新與 surface 後，T50 仍把疑問當成肯定。</p></div>
      <div class="rp-stage"><b>V2.21 · 否定方向保護</b><p class="answer">{_text(middle)}</p><p>不再捏造偏好；但沒找回朋友來源。</p></div>
      <div class="rp-stage"><b>V2.22 · 最新正式 replay</b><p class="answer">{_text(latest)}</p><p>穩定否定，仍未達人物來源嚴格 gate。</p></div>
    </div>
    """


def _cost_rows(summary):
    metrics = summary["conditions"]
    totals = {
        name: row.get("prompt_tokens", 0) + row.get("completion_tokens", 0)
        for name, row in metrics.items()
    }
    maximum = max(totals.values()) or 1
    labels = {"uruha_memory": "UruhaBrain", "plain_recent": "LLM · 8 輪", "plain_full": "LLM · 50 輪"}
    return "".join(
        f'<div class="rp-cost"><span>{labels[name]}</span><div class="rp-bar"><i style="width:{max(2, totals[name]/maximum*100):.1f}%"></i></div><b>{totals[name]} tok · {metrics[name].get("latency_seconds",0):.1f}s</b></div>'
        for name in ("uruha_memory", "plain_recent", "plain_full")
    )


def render_memory_repair_lab(checkpoint=DEFAULT_CHECKPOINT):
    checkpoint = str(checkpoint)
    if checkpoint not in CHECKPOINT_LABELS:
        checkpoint = DEFAULT_CHECKPOINT
    case = _load(CASE_PATH)
    v218 = _load(V218_PATH)
    v219 = _load(V219_PATH)
    v221 = _load(V221_PATH)
    v222 = _load(V222_PATH)
    selected = _comparison(v222, checkpoint)
    summary = v222["summary"]
    lanes = "".join(_lane(selected, name) for name in ("uruha_memory", "plain_recent", "plain_full"))
    return f"""
    <section class="repair-lab">
      <div class="rp-hero"><div><div class="rp-kicker">V2.18 → V2.22 · 50-TURN MEMORY REMEDIATION</div><h1 class="rp-title">三個錯誤修掉兩個，最後一個還在</h1><div class="rp-sub">這不是把失敗洗成全綠。T26 明確更新與 T48 記憶到回答已修復；T50 已從錯誤肯定進步到正確否定，但仍無法穩定把「朋友」來源送進決策。完整 transcript LLM 同樣達到 4/5，因此目前價值是狀態修正、日文穩定與錯誤可定位，不是回答品質全面勝出。</div></div><div class="rp-stamp"><strong>4 / 5 · GATE FAILED</strong><span>FIRST COMPLETE V2.22 RUN RETAINED</span></div></div>
      <div class="rp-metrics"><div class="rp-metric"><b>1/2 → 2/2</b><span>V2.18 → V2.22 有來源主要回溯</span></div><div class="rp-metric"><b>3/5 → 4/5</b><span>同新值案例 V2.19 → V2.22 strict task</span></div><div class="rp-metric"><b>0/2</b><span>最近 8 輪 LLM 主要回溯</span></div><div class="rp-metric"><b>2/2</b><span>完整 transcript LLM 主要回溯</span></div><div class="rp-metric"><b>5/5 · 3/5 · 4/5</b><span>日文：Uruha／recent／full</span></div></div>
      <div class="rp-body">
        <div class="rp-label">三個被 V2.18 定位的修復單元</div>
        <div class="rp-repairs"><div class="rp-repair pass"><b>① 明確事實 > 暫定澄清</b><strong>PASS · T26</strong><span>使用者直接更新ほうじ茶時，不再被低壓澄清問題搶走回答。</span></div><div class="rp-repair pass"><b>② 記憶錨點 > 語言修復指令</b><strong>PASS · T48</strong><span>正確 profile 值會回退成 grounded reply，不再輸出「日本語だけで…」。</span></div><div class="rp-repair partial"><b>③ 疑問句／人物來源綁定</b><strong>PARTIAL · T50</strong><span>不再把問題寫成偏好，也能正確否定；但 T41 朋友事件未穩定進入決策。</span></div></div>
        <div class="rp-timeline">{_timeline(case, checkpoint)}</div>
        <div class="rp-question"><b>CHECKPOINT T{selected['turn']} · {_text(ROLE_LABELS.get(selected['role'], selected['role']))}</b><p>{_text(selected['user'])}</p></div>
        <div class="rp-lanes">{lanes}</div>
        <div class="rp-label" style="margin-top:17px">URUHA INTERNAL FLOW · 證據在哪裡消失</div>
        {_trace_chain(selected, case)}
        <div class="rp-label" style="margin-top:17px">SAME-CASE REPAIR PATH · 只看修正造成的變化</div>
        {_repair_progress(v219, v221, v222, checkpoint)}
        <div class="rp-analysis"><div class="rp-card"><h3>比較結論</h3><div class="rp-finding"><b>相對最近 8 輪：</b>UruhaBrain 在 T25／T48 都能回溯來源，recent 組則分別猜成カフェラテ與レモネード，T49 還復活已撤回的麦茶。</div><div class="rp-finding"><b>相對完整 transcript：</b>兩者主要回溯都是 2/2、strict task 都是 4/5。不能說 Uruha 回答品質更好；Uruha 的差異是 profile 修正、來源 trace 與 5/5 日文。</div><div class="rp-finding"><b>仍失敗：</b>T50 的朋友事件在 T41，但 runtime recent window 只保留 T42–T49；排名檢索也未穩定選中 T41，所以只能安全否定，不能證明人物綁定。</div></div><div class="rp-card"><h3>五個 checkpoint 成本</h3>{_cost_rows(summary)}<div class="rp-finding">Uruha 約為完整 transcript 的 {((summary['conditions']['uruha_memory']['prompt_tokens']+summary['conditions']['uruha_memory']['completion_tokens'])/(summary['conditions']['plain_full']['prompt_tokens']+summary['conditions']['plain_full']['completion_tokens'])):.2f}× tokens、{(summary['conditions']['uruha_memory']['latency_seconds']/summary['conditions']['plain_full']['latency_seconds']):.2f}× latency。這是 full-system 非 token-parity 成本。</div></div></div>
        <div class="rp-boundary"><div class="yes"><b>已證明</b><span>新值 50 輪下，更新承接、兩次來源回溯、舊值撤回與日文輸出已穩定通過。</span></div><div class="mixed"><b>部分證明</b><span>false-memory 從錯誤肯定修到正確否定，但人物來源仍會因檢索視窗漏失。</span></div><div class="no"><b>尚未證明</b><span>全面優於完整上下文 LLM、獨立新記憶類型泛化、人類被理解感或成本優勢。</span></div></div>
      </div>
    </section>
    """
