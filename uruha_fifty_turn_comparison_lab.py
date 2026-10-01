"""Read-only graphical view of the frozen V2.18 50-turn comparison."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_18_fifty_turn_memory_comparison.json"
RAW_PATH = ROOT / "analysis/v2_18_fifty_turn_memory_comparison_raw.json"
DEFAULT_CHECKPOINT = "48"
CHECKPOINT_LABELS = {
    "25": "① 24 輪後回溯舊值",
    "26": "② 使用者修正偏好",
    "48": "③ 22 輪後回溯新值",
    "49": "④ 確認舊值已撤回",
    "50": "⑤ 他人資訊誤綁控制",
}
CONDITION_LABELS = {
    "uruha_memory": "UruhaBrain · 外部記憶",
    "plain_recent": "單純 LLM · 最近 8 輪",
    "plain_full": "單純 LLM · 完整 50 輪",
}
ACCESS_LABELS = {
    "uruha_memory": "結構化 profile＋檢索記憶＋決策 trace",
    "plain_recent": "只看當下以前最近 8 輪，沒有外部記憶",
    "plain_full": "把當下以前的完整 transcript 全部送入模型",
}
POSTHOC_NOTES = {
    25: {
        "uruha_memory": "正確回溯 T1，且 trace 指到 favorites=coffee。",
        "plain_recent": "來源不在視窗內，卻含糊宣稱自己記得，沒有給出值。",
        "plain_full": "完整 transcript 中有 T1，因此直接答對。",
    },
    26: {
        "uruha_memory": "profile 已正確更新，但回覆錯用低壓澄清，沒有承接更新。",
        "plain_recent": "理解更新方向，但把カモミール拼錯。",
        "plain_full": "理解更新方向，最終表面混入多語與原文詞。",
    },
    48: {
        "uruha_memory": "記憶與 anchor 都正確；錯誤發生在 final surface，修復指令被當成回答。",
        "plain_recent": "T26 已離開視窗，模型自行猜成水。",
        "plain_full": "大致回溯到洋甘菊茶，但日文名稱生成錯誤，exact proxy 未通過。",
    },
    49: {
        "uruha_memory": "正確否定舊 coffee，且 profile 已保留 dislikes=coffee。",
        "plain_recent": "無修正來源，回答搖擺並混入英文與敬語。",
        "plain_full": "語意上知道已改，但飲料名稱與表面語言仍損壞。",
    },
    50: {
        "uruha_memory": "沒有把朋友的飲料寫成使用者偏好，但把疑問句錯當 current update，最後沒有回答問題。",
        "plain_recent": "說沒有紀錄後又建議喝它；來源不足且混入英文。",
        "plain_full": "成功區分朋友與使用者，但最終回答仍混入中英文。",
    },
}
POSTHOC_VERDICTS = {
    25: {"uruha_memory": "pass", "plain_recent": "fail", "plain_full": "pass"},
    26: {"uruha_memory": "fail", "plain_recent": "partial", "plain_full": "fail"},
    48: {"uruha_memory": "fail", "plain_recent": "fail", "plain_full": "partial"},
    49: {"uruha_memory": "pass", "plain_recent": "fail", "plain_full": "partial"},
    50: {"uruha_memory": "fail", "plain_recent": "partial", "plain_full": "partial"},
}


FIFTY_COMPARISON_CSS = r"""
.fifty-compare{--fc-blue:#38bdf8;--fc-green:#34d399;--fc-amber:#facc15;--fc-rose:#fb7185;--fc-violet:#a78bfa;overflow:hidden;border:1px solid rgba(56,189,248,.22);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 10% 0%,rgba(56,189,248,.12),transparent 28%),radial-gradient(circle at 92% 5%,rgba(251,113,133,.1),transparent 28%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.48)}
.fifty-compare *{box-sizing:border-box}.fc-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:22px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.fc-kicker{color:#67e8f9;font-size:10px;font-weight:800;letter-spacing:.14em}.fc-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);font-weight:850;line-height:1.08}.fc-sub{max-width:900px;margin-top:8px;color:#94a3b8;font-size:11px;line-height:1.55}.fc-stamp{min-width:210px;border:1px solid rgba(251,113,133,.4);border-radius:16px;padding:12px 14px;background:rgba(127,29,29,.2);text-align:right}.fc-stamp strong{display:block;color:#ffe4e6;font-size:18px}.fc-stamp span{color:#fda4af;font-size:9px;letter-spacing:.08em}
.fc-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:rgba(148,163,184,.12)}.fc-metric{padding:12px 16px;background:#08101f}.fc-metric b{display:block;color:#f8fafc;font-size:18px}.fc-metric span{color:#64748b;font-size:8px;line-height:1.35}.fc-body{padding:20px 24px 26px}.fc-label{margin:0 4px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}
.fc-timeline{display:grid;grid-template-columns:repeat(25,minmax(18px,1fr));gap:3px;padding:12px;border:1px solid rgba(148,163,184,.14);border-radius:17px;background:rgba(15,23,42,.62)}.fc-turn{height:42px;border:1px solid rgba(148,163,184,.12);border-radius:7px;padding-top:6px;background:rgba(30,41,59,.7);text-align:center;color:#64748b;font-size:7px}.fc-turn b{display:block;color:#94a3b8;font-size:8px}.fc-turn.seed{background:rgba(76,29,149,.3);border-color:rgba(167,139,250,.5)}.fc-turn.relation{background:rgba(113,63,18,.2);border-color:rgba(250,204,21,.25)}.fc-turn.checkpoint{background:rgba(14,116,144,.24);border-color:rgba(56,189,248,.62)}.fc-turn.active{outline:2px solid #f8fafc;outline-offset:2px}.fc-legend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 4px 0;color:#64748b;font-size:8px}.fc-legend i{display:inline-block;width:7px;height:7px;margin-right:4px;border-radius:50%}
.fc-question{margin-top:18px;border:1px solid rgba(56,189,248,.28);border-radius:16px;padding:14px 16px;background:rgba(14,116,144,.12)}.fc-question b{color:#7dd3fc;font-size:9px;letter-spacing:.08em}.fc-question p{margin:7px 0 0;color:#f8fafc;font-size:14px;font-weight:760}.fc-lanes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:14px}.fc-lane{--lane:#94a3b8;border:1px solid color-mix(in srgb,var(--lane) 38%,#334155);border-radius:17px;padding:14px;background:color-mix(in srgb,var(--lane) 7%,rgba(15,23,42,.88))}.fc-lane.uruha{--lane:var(--fc-blue)}.fc-lane.recent{--lane:var(--fc-amber)}.fc-lane.full{--lane:var(--fc-violet)}.fc-lane-head{display:flex;justify-content:space-between;gap:8px;align-items:center}.fc-lane-head b{color:#f8fafc;font-size:12px}.fc-result{border-radius:999px;padding:3px 7px;background:rgba(148,163,184,.12);color:#94a3b8;font-size:8px}.fc-result.pass{background:rgba(6,78,59,.4);color:#86efac}.fc-result.partial{background:rgba(113,63,18,.38);color:#fde68a}.fc-result.fail{background:rgba(127,29,29,.35);color:#fda4af}.fc-access{min-height:32px;margin-top:8px;color:#64748b;font-size:8px;line-height:1.45}.fc-reply{min-height:78px;margin-top:10px;border:1px solid rgba(148,163,184,.12);border-radius:12px;padding:11px;background:rgba(2,6,23,.5);color:#f8fafc;font-size:12px;font-weight:680;line-height:1.55}.fc-badges{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}.fc-badge{border:1px solid rgba(148,163,184,.15);border-radius:999px;padding:3px 6px;color:#94a3b8;font-size:7px}.fc-badge.good{border-color:rgba(52,211,153,.28);color:#86efac}.fc-badge.bad{border-color:rgba(251,113,133,.3);color:#fda4af}.fc-note{min-height:48px;margin-top:9px;padding-top:8px;border-top:1px solid rgba(148,163,184,.1);color:#94a3b8;font-size:8px;line-height:1.5}
.fc-trace{display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr;gap:7px;align-items:center;margin-top:18px}.fc-node{min-height:92px;border:1px solid rgba(56,189,248,.25);border-radius:14px;padding:11px;background:rgba(14,116,144,.09)}.fc-node b{display:block;color:#7dd3fc;font-size:9px}.fc-node strong{display:block;margin-top:8px;color:#f8fafc;font-size:11px;line-height:1.4;overflow-wrap:anywhere}.fc-node span{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.4}.fc-arrow{height:2px;background:rgba(56,189,248,.36)}
.fc-analysis{display:grid;grid-template-columns:1.2fr .8fr;gap:12px;margin-top:18px}.fc-card{border:1px solid rgba(148,163,184,.15);border-radius:16px;padding:14px;background:rgba(15,23,42,.7)}.fc-card h3{margin:0;color:#f8fafc;font-size:11px}.fc-finding{margin-top:9px;padding-top:8px;border-top:1px solid rgba(148,163,184,.1);color:#94a3b8;font-size:9px;line-height:1.5}.fc-finding b{color:#f8fafc}.fc-cost{display:grid;grid-template-columns:92px 1fr auto;gap:8px;align-items:center;margin-top:9px;color:#94a3b8;font-size:8px}.fc-bar{height:7px;border-radius:999px;background:rgba(148,163,184,.12);overflow:hidden}.fc-bar i{display:block;height:100%;border-radius:999px;background:var(--fc-blue)}.fc-boundary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin-top:18px;background:rgba(148,163,184,.12)}.fc-boundary div{padding:12px 14px;background:#08101f}.fc-boundary b{display:block;font-size:9px}.fc-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.fc-boundary .yes b{color:#86efac}.fc-boundary .mixed b{color:#fde68a}.fc-boundary .no b{color:#fda4af}
@media(max-width:950px){.fc-lanes,.fc-analysis{grid-template-columns:1fr}.fc-trace{grid-template-columns:1fr}.fc-arrow{width:2px;height:18px;margin:auto}.fc-timeline{grid-template-columns:repeat(10,minmax(24px,1fr))}}
@media(max-width:620px){.fc-hero{grid-template-columns:1fr;padding:21px 17px}.fc-stamp{text-align:left}.fc-metrics{grid-template-columns:1fr 1fr}.fc-body{padding:17px}.fc-timeline{grid-template-columns:repeat(5,minmax(30px,1fr))}.fc-boundary{grid-template-columns:1fr}}
"""


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _text(value):
    return escape(str(value or ""))


def checkpoint_choices():
    return [(label, turn) for turn, label in CHECKPOINT_LABELS.items()]


def _selected(raw, checkpoint):
    turn = int(checkpoint) if str(checkpoint).isdigit() else int(DEFAULT_CHECKPOINT)
    return next(row for row in raw["comparisons"] if int(row["turn"]) == turn)


def _timeline(case, active):
    cells = []
    for row in case["turns"]:
        classes = ["fc-turn"]
        if row["role"] == "memory_seed":
            classes.append("seed")
        if row["role"] == "relational_distractor":
            classes.append("relation")
        if row["role"] in CHECKPOINT_LABELS.values() or row["execution"] == "full_runtime_comparison":
            classes.append("checkpoint")
        if int(row["turn"]) == int(active):
            classes.append("active")
        cells.append(
            f'<div class="{" ".join(classes)}" title="{_text(row["role"])} · {_text(row["user"])}"><b>{row["turn"]}</b>{_text(row["role"][:3])}</div>'
        )
    return "".join(cells)


def _condition_lane(selected, condition):
    row = selected["conditions"][condition]
    score = row.get("score") or {}
    result_class = POSTHOC_VERDICTS.get(int(selected["turn"]), {}).get(condition, "fail")
    result_text = {
        "pass": "REVIEW PASS",
        "partial": "REVIEW PARTIAL",
        "fail": "REVIEW FAIL",
    }[result_class]
    badges = [
        ("當前值命中", score.get("expected_current_value_hit")),
        ("來源可用", score.get("source_evidence_available")),
        ("沒有復活舊值", not score.get("stale_value_revival")),
        ("日文契約", score.get("visible_japanese_contract_pass")),
    ]
    badge_html = "".join(
        f'<span class="fc-badge {"good" if passed else "bad"}">{_text(label)} {"✓" if passed else "×"}</span>'
        for label, passed in badges
    )
    badge_html += (
        f'<span class="fc-badge {"good" if score.get("task_pass") else "bad"}">'
        f'凍結 auto proxy {"✓" if score.get("task_pass") else "×"}</span>'
    )
    css_class = {"uruha_memory": "uruha", "plain_recent": "recent", "plain_full": "full"}[condition]
    note = POSTHOC_NOTES.get(int(selected["turn"]), {}).get(condition, "")
    compute = row.get("compute") or {}
    return f"""
    <div class="fc-lane {css_class}">
      <div class="fc-lane-head"><b>{_text(CONDITION_LABELS[condition])}</b><span class="fc-result {result_class}">{result_text}</span></div>
      <div class="fc-access">{_text(ACCESS_LABELS[condition])}</div>
      <div class="fc-reply">{_text(row.get('reply'))}</div>
      <div class="fc-badges">{badge_html}</div>
      <div class="fc-note">觀察：{_text(note)}<br>成本：{compute.get('prompt_tokens', 0)} prompt / {compute.get('completion_tokens', 0)} completion tokens · {row.get('elapsed_seconds', 0)} 秒</div>
    </div>
    """


def _system_trace(selected):
    system = selected["conditions"]["uruha_memory"]
    passed = (system.get("passed_target_rows") or [{}])[0]
    anchor = system.get("memory_anchor") or {}
    source = passed.get("text") or (system.get("profile_before") or {})
    reviewed = POSTHOC_VERDICTS.get(int(selected["turn"]), {}).get("uruha_memory", "fail")
    stage = "人工複核通過" if reviewed == "pass" else "人工複核：回答不完整或失敗"
    return f"""
    <div class="fc-trace">
      <div class="fc-node"><b>1 · 來源／目前狀態</b><strong>{_text(source)}</strong><span>source trace: {_text(passed.get('trace_id') or 'structured profile audit')}</span></div>
      <div class="fc-arrow"></div>
      <div class="fc-node"><b>2 · 決策錨點</b><strong>{_text(anchor.get('kind'))} → {_text(anchor.get('jp_anchor') or anchor.get('value'))}</strong><span>{_text(anchor.get('provenance_channel'))}</span></div>
      <div class="fc-arrow"></div>
      <div class="fc-node"><b>3 · 最終回答</b><strong>{_text(system.get('reply'))}</strong><span>{_text(stage)}</span></div>
    </div>
    """


def _cost_rows(summary):
    metrics = summary["conditions"]
    max_tokens = max(
        (row.get("prompt_tokens", 0) + row.get("completion_tokens", 0))
        for row in metrics.values()
    ) or 1
    rows = []
    for condition in CONDITION_LABELS:
        row = metrics[condition]
        total = row.get("prompt_tokens", 0) + row.get("completion_tokens", 0)
        width = max(2, round(total / max_tokens * 100, 1))
        rows.append(
            f'<div class="fc-cost"><span>{_text(CONDITION_LABELS[condition])}</span><div class="fc-bar"><i style="width:{width}%"></i></div><b>{total} tok · {row.get("latency_seconds", 0):.1f}s</b></div>'
        )
    return "".join(rows)


def render_fifty_turn_comparison(checkpoint=DEFAULT_CHECKPOINT):
    checkpoint = str(checkpoint)
    if checkpoint not in CHECKPOINT_LABELS:
        checkpoint = DEFAULT_CHECKPOINT
    case = _load(CASE_PATH)
    raw = _load(RAW_PATH)
    selected = _selected(raw, checkpoint)
    summary = raw["summary"]
    metrics = summary["conditions"]
    lanes = "".join(_condition_lane(selected, condition) for condition in CONDITION_LABELS)
    return f"""
    <section class="fifty-compare">
      <div class="fc-hero">
        <div><div class="fc-kicker">V2.18 · FROZEN 50-TURN ARCHITECTURE COMPARISON</div><h1 class="fc-title">記憶找對，不代表回答就答對</h1><div class="fc-sub">同一段 50 輪對話比較三種資訊條件。正式門檻失敗：UruhaBrain 在 T48 已把正確記憶送進決策，卻在最後表面化失去答案。這張圖把「記憶、決策、語言與成本」分開，不用一個總分掩蓋錯誤位置。</div></div>
        <div class="fc-stamp"><strong>FORMAL GATE FAILED</strong><span>FIRST RUN RETAINED · 0 RETUNING</span></div>
      </div>
      <div class="fc-metrics">
        <div class="fc-metric"><b>{metrics['uruha_memory']['primary_source_grounded_recall_count']}/2</b><span>UruhaBrain 有來源的主要回溯</span></div>
        <div class="fc-metric"><b>{metrics['plain_recent']['primary_source_grounded_recall_count']}/2</b><span>最近 8 輪 LLM 有來源回溯</span></div>
        <div class="fc-metric"><b>{metrics['plain_full']['primary_source_grounded_recall_count']}/2</b><span>完整 transcript LLM exact 回溯</span></div>
        <div class="fc-metric"><b>5/5 · 3/5 · 2/5</b><span>日文契約：Uruha／recent／full</span></div>
      </div>
      <div class="fc-body">
        <div class="fc-label">50-TURN SHARED TIMELINE · 紫=種子 · 黃=他人飲料干擾 · 藍=比較 checkpoint</div>
        <div class="fc-timeline">{_timeline(case, checkpoint)}</div>
        <div class="fc-legend"><span><i style="background:#a78bfa"></i>使用者記憶種子</span><span><i style="background:#facc15"></i>關係綁定干擾</span><span><i style="background:#38bdf8"></i>三組實際生成</span></div>
        <div class="fc-question"><b>USER · CHECKPOINT T{selected['turn']} · {_text(selected['role'])}</b><p>{_text(selected['user'])}</p></div>
        <div class="fc-lanes">{lanes}</div>
        <div class="fc-label" style="margin-top:18px">URUHA TRACE · 錯誤可以定位在哪一段</div>
        {_system_trace(selected)}
        <div class="fc-analysis">
          <div class="fc-card"><h3>這一次可以說什麼</h3><div class="fc-finding"><b>可說：</b>外部記憶在 T25 與 T48 都把正確 profile 值送進決策，且 T49 沒復活舊值；相對只看最近 8 輪，來源保存與錯誤定位更完整。</div><div class="fc-finding"><b>不可說：</b>回答品質優於單純 LLM。正式 Uruha gate 只有 1/2 主要回溯，完整 transcript LLM 也能從原文找回內容；目前沒有盲評。</div><div class="fc-finding"><b>真正診斷：</b>T48 是 surface failure，不是 memory retrieval failure；T50 還暴露疑問句被誤判為偏好斷言。</div></div>
          <div class="fc-card"><h3>五個 checkpoint 的實際成本</h3>{_cost_rows(summary)}<div class="fc-finding">這是 full-system 成本，不是 token-parity。UruhaBrain 的多階段 JSON 規劃使 completion tokens 與延遲明顯較高。</div></div>
        </div>
        <div class="fc-boundary"><div class="yes"><b>已證明</b><span>50 輪隔離執行、來源 trace、profile 修正、三條件真實輸出與資源紀錄。</span></div><div class="mixed"><b>混合證據</b><span>外部記憶比 8 輪視窗更能保留來源，但 end-to-end 回答尚不穩定。</span></div><div class="no"><b>尚未證明</b><span>全面優於 LLM、token 等成本公平優勢、人類被理解感、獨立 holdout 或通用長期記憶。</span></div></div>
      </div>
    </section>
    """
