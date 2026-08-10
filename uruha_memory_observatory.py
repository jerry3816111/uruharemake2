"""Pure rendering helpers for the teacher-facing memory observatory."""

from __future__ import annotations

import hashlib
from html import escape


MEMORY_OBSERVATORY_CSS = r"""
.memory-observatory {
  position: relative;
  overflow: hidden;
  margin-bottom: 16px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 18px;
  padding: 18px;
  color: #e5f3ff;
  background:
    radial-gradient(circle at 18% 18%, rgba(34, 211, 238, 0.15), transparent 30%),
    radial-gradient(circle at 78% 22%, rgba(167, 139, 250, 0.18), transparent 34%),
    linear-gradient(145deg, #07101f 0%, #0b1224 48%, #11132b 100%);
  box-shadow: 0 18px 48px rgba(3, 7, 18, 0.28);
}
.memory-observatory::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.28;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: linear-gradient(to bottom, black, transparent 84%);
}
.memory-observatory-head,
.memory-stage-rail,
.memory-stream,
.memory-constellation,
.memory-write-lane,
.memory-legend { position: relative; z-index: 1; }
.memory-observatory-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}
.memory-eyebrow {
  color: #67e8f9;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.memory-title {
  margin-top: 3px;
  color: #f8fafc;
  font-size: 20px;
  font-weight: 800;
}
.memory-subtitle {
  max-width: 680px;
  margin-top: 5px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.55;
}
.memory-live {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(52, 211, 153, 0.35);
  border-radius: 999px;
  padding: 6px 10px;
  color: #a7f3d0;
  background: rgba(6, 78, 59, 0.28);
  font-size: 11px;
  font-weight: 700;
}
.memory-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 14px #34d399;
  animation: memory-live-pulse 1.7s ease-in-out infinite;
}
.memory-stage-rail {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.memory-stage {
  position: relative;
  min-height: 62px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(15, 23, 42, 0.72);
}
.memory-stage:not(:last-child)::after {
  content: "›";
  position: absolute;
  right: -9px;
  top: 18px;
  z-index: 3;
  color: #67e8f9;
  font-size: 22px;
  text-shadow: 0 0 12px rgba(34, 211, 238, 0.8);
}
.memory-stage-label { color: #94a3b8; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; }
.memory-stage-value { margin-top: 5px; color: #f8fafc; font-size: 17px; font-weight: 800; }
.memory-stage-note { margin-top: 2px; color: #64748b; font-size: 10px; }
.memory-stream {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  overflow: hidden;
  border: 1px solid rgba(34, 211, 238, 0.16);
  border-radius: 12px;
  padding: 7px 10px;
  background: linear-gradient(90deg, rgba(8, 47, 73, 0.36), rgba(30, 27, 75, 0.28));
}
.memory-stream-label {
  flex: none;
  color: #67e8f9;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
}
.memory-stream-chip {
  flex: none;
  max-width: 210px;
  overflow: hidden;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 999px;
  padding: 5px 9px;
  color: #dbeafe;
  background: rgba(30, 41, 59, 0.85);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
  animation: memory-chip-drift 3.6s ease-in-out infinite alternate;
  animation-delay: var(--memory-delay, 0s);
}
.memory-stream-chip strong { color: #67e8f9; }
.memory-section-label {
  margin: 15px 0 8px;
  color: #cbd5e1;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}
.memory-constellation {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
  gap: 10px;
}
.memory-node {
  position: relative;
  min-height: 112px;
  overflow: hidden;
  border: 1px solid rgba(100, 116, 139, 0.26);
  border-radius: 14px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.72);
  opacity: var(--memory-opacity, 0.8);
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}
.memory-node:hover { transform: translateY(-2px); border-color: rgba(125, 211, 252, 0.55); }
.memory-node::after {
  content: "";
  position: absolute;
  width: var(--memory-orb-size, 48px);
  height: var(--memory-orb-size, 48px);
  right: -18px;
  bottom: -22px;
  border-radius: 50%;
  background: var(--memory-color, #64748b);
  opacity: 0.12;
  filter: blur(2px);
}
.memory-node.is-selected { border-color: rgba(250, 204, 21, 0.58); box-shadow: inset 0 0 0 1px rgba(250, 204, 21, 0.12); }
.memory-node.is-passed { border-color: rgba(52, 211, 153, 0.7); box-shadow: 0 0 22px rgba(52, 211, 153, 0.14); }
.memory-node.is-passed::before {
  content: "";
  position: absolute;
  top: 9px;
  right: 9px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 12px #34d399;
  animation: memory-live-pulse 1.7s ease-in-out infinite;
}
.memory-node-source { color: var(--memory-color, #94a3b8); font-size: 10px; font-weight: 800; letter-spacing: 0.09em; text-transform: uppercase; }
.memory-node-text { position: relative; z-index: 1; margin-top: 7px; color: #e2e8f0; font-size: 12px; line-height: 1.45; }
.memory-node-meta { position: relative; z-index: 1; margin-top: 9px; color: #64748b; font-size: 9px; }
.memory-node-badges { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.memory-badge { border-radius: 999px; padding: 2px 6px; color: #cbd5e1; background: rgba(51, 65, 85, 0.72); font-size: 9px; }
.memory-badge.selected { color: #fde68a; background: rgba(113, 63, 18, 0.5); }
.memory-badge.passed { color: #a7f3d0; background: rgba(6, 78, 59, 0.5); }
.memory-write-lane { display: flex; flex-wrap: wrap; gap: 7px; }
.memory-write {
  border: 1px solid rgba(244, 114, 182, 0.38);
  border-radius: 10px;
  padding: 8px 10px;
  color: #fce7f3;
  background: rgba(131, 24, 67, 0.22);
  font-size: 10px;
}
.memory-legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; color: #94a3b8; font-size: 9px; }
.memory-legend-item { display: inline-flex; align-items: center; gap: 5px; }
.memory-legend-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--legend-color); box-shadow: 0 0 8px color-mix(in srgb, var(--legend-color) 70%, transparent); }
.memory-empty { padding: 18px; border: 1px dashed rgba(125, 211, 252, 0.25); border-radius: 12px; color: #94a3b8; text-align: center; font-size: 12px; }
@keyframes memory-live-pulse { 0%, 100% { opacity: 0.5; transform: scale(0.86); } 50% { opacity: 1; transform: scale(1.16); } }
@keyframes memory-chip-drift { from { transform: translateX(0); } to { transform: translateX(8px); } }
@media (max-width: 900px) {
  .memory-stage-rail { grid-template-columns: 1fr 1fr; }
  .memory-stage:not(:last-child)::after { display: none; }
  .memory-observatory-head { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  .memory-live-dot, .memory-stream-chip, .memory-node.is-passed::before { animation: none; }
}
"""


SOURCE_META = {
    "profile": ("PROFILE", "◉", "#f472b6"),
    "episode": ("EPISODIC", "◌", "#a78bfa"),
    "recent_turn": ("RECENT", "↻", "#38bdf8"),
    "short_term": ("SHORT TERM", "◍", "#22d3ee"),
    "wisdom": ("SEMANTIC", "◇", "#f59e0b"),
    "procedural": ("PROCEDURAL", "⚙", "#34d399"),
    "knowledge": ("KNOWLEDGE", "◆", "#60a5fa"),
    "unknown": ("MEMORY", "·", "#94a3b8"),
}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _trim(value, limit=96):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _source_key(value):
    raw = str(value or "unknown").strip().lower()
    aliases = {
        "episodic": "episode",
        "episodic_memory": "episode",
        "recent": "recent_turn",
        "session": "recent_turn",
        "short_term_memory": "short_term",
        "semantic": "wisdom",
        "wisdom_semantic": "wisdom",
        "procedural_memory": "procedural",
        "knowledge_base": "knowledge",
        "user_profile": "profile",
    }
    normalized = aliases.get(raw, raw)
    return normalized if normalized in SOURCE_META else "unknown"


def _trace_id(row):
    trace_id = str((row or {}).get("trace_id") or "").strip()
    if trace_id:
        return trace_id
    payload = "\x1f".join(
        [
            str((row or {}).get("source") or "unknown"),
            str((row or {}).get("text") or ""),
            str((row or {}).get("channel") or ""),
        ]
    )
    return "visual:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def collect_memory_nodes(result, limit=12):
    """Merge provenance surfaces into one deterministic visual node list."""
    result = result or {}
    memory_data = result.get("memory_data") or {}
    provenance = memory_data.get("memory_provenance") or {}
    selected_ids = {str(value) for value in provenance.get("selected_working_memory_trace_ids") or []}
    passed_ids = {str(value) for value in provenance.get("passed_to_leftbrain_trace_ids") or []}
    merged = {}

    def add_rows(rows, default_channel):
        for index, raw in enumerate(rows or []):
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            row.setdefault("channel", default_channel)
            row.setdefault("rank", index + 1)
            row["trace_id"] = _trace_id(row)
            existing = merged.get(row["trace_id"], {})
            merged[row["trace_id"]] = {**existing, **row}

    add_rows(provenance.get("candidate_pool"), "candidate_pool")
    add_rows(provenance.get("retrieved_candidates"), "retrieved_candidate")
    add_rows(memory_data.get("working_memory_items"), "selected_working_memory")
    add_rows(provenance.get("passed_to_leftbrain"), "passed_to_leftbrain")

    nodes = []
    for row in merged.values():
        trace_id = row["trace_id"]
        selected = trace_id in selected_ids or bool(row.get("selected"))
        passed = trace_id in passed_ids
        source = _source_key(row.get("source"))
        score = _safe_float(row.get("score"), 0.0)
        strength = max(0.12, min(1.0, score / 5.0 if score > 1.0 else score))
        nodes.append(
            {
                **row,
                "source_key": source,
                "selected": selected,
                "passed": passed,
                "score": score,
                "strength": strength,
            }
        )

    nodes.sort(
        key=lambda row: (
            not row["passed"],
            not row["selected"],
            int(row.get("rank") or 9999),
            -row["score"],
            row["trace_id"],
        )
    )
    return nodes[: max(1, int(limit))]


def _node_html(node):
    label, icon, color = SOURCE_META[node["source_key"]]
    state_classes = ["memory-node"]
    if node["selected"]:
        state_classes.append("is-selected")
    if node["passed"]:
        state_classes.append("is-passed")
    if not node["selected"] and not node["passed"]:
        state_classes.append("is-candidate")

    badges = [f'<span class="memory-badge">rank {int(node.get("rank") or 0) or "-"}</span>']
    if node["selected"]:
        badges.append('<span class="memory-badge selected">工作記憶</span>')
    if node["passed"]:
        badges.append('<span class="memory-badge passed">流向決策</span>')
    channel = _trim(node.get("channel") or "candidate", 28)
    trace = _trim(node.get("trace_id"), 34)
    text = _trim(node.get("text") or "（無文字內容）", 112)
    orb_size = 34.0 + node["strength"] * 46.0
    node_opacity = 0.68 + node["strength"] * 0.32
    return (
        f'<article class="{" ".join(state_classes)}" '
        f'style="--memory-color:{color};--memory-strength:{node["strength"]:.3f};'
        f'--memory-orb-size:{orb_size:.1f}px;--memory-opacity:{node_opacity:.3f};" '
        f'data-trace-id="{escape(str(node.get("trace_id") or ""), quote=True)}">'
        f'<div class="memory-node-source">{icon} {label}</div>'
        f'<div class="memory-node-text">{escape(text)}</div>'
        f'<div class="memory-node-badges">{"".join(badges)}</div>'
        f'<div class="memory-node-meta">score={node["score"]:.3f} · {escape(channel)}<br>{escape(trace)}</div>'
        "</article>"
    )


def render_memory_observatory(result):
    """Render the live memory path without exposing unescaped runtime text."""
    result = result or {}
    memory_data = result.get("memory_data") or {}
    provenance = memory_data.get("memory_provenance") or {}
    runtime_trace = result.get("runtime_trace") or {}
    nodes = collect_memory_nodes(result)
    selected_ids = {str(value) for value in provenance.get("selected_working_memory_trace_ids") or []}
    passed_ids = {str(value) for value in provenance.get("passed_to_leftbrain_trace_ids") or []}
    writes = list(runtime_trace.get("memory_writes") or [])

    retrieved_count = int(provenance.get("retrieved_candidate_count") or 0)
    candidate_count = int(provenance.get("candidate_count") or len(nodes))
    selected_count = len(selected_ids)
    passed_count = len(passed_ids)
    stage_rows = [
        ("01 · Retrieval", retrieved_count, "檢索池"),
        ("02 · Attention", candidate_count, "排序候選"),
        ("03 · Working", selected_count, "工作記憶"),
        ("04 · Decision", passed_count, "送入規劃"),
        ("05 · Writeback", len(writes), "本輪寫入"),
    ]
    stages = "".join(
        (
            '<div class="memory-stage">'
            f'<div class="memory-stage-label">{escape(label)}</div>'
            f'<div class="memory-stage-value">{value}</div>'
            f'<div class="memory-stage-note">{escape(note)}</div>'
            "</div>"
        )
        for label, value, note in stage_rows
    )

    flowing = [node for node in nodes if node["passed"] or node["selected"]][:6]
    if flowing:
        stream = "".join(
            (
                f'<span class="memory-stream-chip" style="--memory-delay:-{index * 0.42:.2f}s">'
                f'<strong>{escape(SOURCE_META[node["source_key"]][0])}</strong> '
                f'{escape(_trim(node.get("text"), 56))}</span>'
            )
            for index, node in enumerate(flowing)
        )
    else:
        stream = '<span class="memory-stream-chip">等待輸入後顯示正在流動的記憶</span>'

    if nodes:
        constellation = "".join(_node_html(node) for node in nodes)
    else:
        constellation = '<div class="memory-empty">尚無記憶節點。送出訊息後，候選、工作記憶與決策路徑會在這裡亮起。</div>'

    if writes:
        write_lane = "".join(
            (
                '<span class="memory-write">'
                f'{escape(str(row.get("layer") or "memory"))} · '
                f'{escape(_trim(row.get("summary") or row.get("kind") or "write", 72))}'
                "</span>"
            )
            for row in writes[:6]
            if isinstance(row, dict)
        )
    else:
        write_lane = '<span class="memory-write">本輪尚無回寫</span>'

    return (
        '<section class="memory-observatory" aria-label="記憶觀測台">'
        '<div class="memory-observatory-head">'
        '<div><div class="memory-eyebrow">Memory Observatory</div>'
        '<div class="memory-title">記憶正在怎麼影響這一輪</div>'
        '<div class="memory-subtitle">每個節點代表一筆可追溯記憶；黃色是進入工作記憶，綠色發光表示已傳入決策模組。</div></div>'
        '<div class="memory-live"><span class="memory-live-dot"></span>LOCAL TRACE · LIVE</div>'
        "</div>"
        f'<div class="memory-stage-rail">{stages}</div>'
        '<div class="memory-stream"><span class="memory-stream-label">FLOWING NOW</span>'
        f"{stream}</div>"
        '<div class="memory-section-label">Memory constellation · 記憶星圖</div>'
        f'<div class="memory-constellation">{constellation}</div>'
        '<div class="memory-section-label">Writeback · 經驗回寫</div>'
        f'<div class="memory-write-lane">{write_lane}</div>'
        '<div class="memory-legend">'
        '<span class="memory-legend-item"><span class="memory-legend-dot" style="--legend-color:#64748b"></span>候選記憶</span>'
        '<span class="memory-legend-item"><span class="memory-legend-dot" style="--legend-color:#facc15"></span>進入工作記憶</span>'
        '<span class="memory-legend-item"><span class="memory-legend-dot" style="--legend-color:#34d399"></span>已傳入決策</span>'
        '<span class="memory-legend-item"><span class="memory-legend-dot" style="--legend-color:#f472b6"></span>本輪回寫</span>'
        "</div></section>"
    )
