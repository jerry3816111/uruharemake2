"""Pure rendering helpers for the teacher-facing memory observatory."""

from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path


M30_FIDELITY_RESULT_PATH = (
    Path(__file__).resolve().parent
    / "analysis/m30_cross_lingual_literal_fidelity_raw_2026-08-25.json"
)
M32_COMMIT_RESULT_PATH = (
    Path(__file__).resolve().parent
    / "analysis/m32_semantic_commit_routing_reserve_raw_2026-08-25.json"
)
M33_SOURCE_ATOM_RESULT_PATH = (
    Path(__file__).resolve().parent
    / "analysis/m33_source_anchored_semantic_atom_reserve_raw_2026-08-25.json"
)
M34_PRAGMATIC_BRANCH_RESULT_PATH = (
    Path(__file__).resolve().parent
    / "analysis/m34_counterfactual_pragmatic_branch_reserve_raw_2026-08-25.json"
)
M35_SAME_MODEL_RESULT_PATH = (
    Path(__file__).resolve().parent
    / "analysis/m35_same_model_longitudinal_pragmatic_reserve_raw_2026-08-25.json"
)
M36_COMPOSITIONAL_RESULT_PATH = (
    Path(__file__).resolve().parent
    / "analysis/m36_compositional_multilingual_pragmatic_reserve_raw_2026-08-25.json"
)


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

MEMORY_OBSERVATORY_CSS += r"""
.brain-graph-shell {
  position: relative;
  z-index: 1;
}
.brain-graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 10px;
  color: #94a3b8;
  font-size: 10px;
}
.brain-graph-toolbar strong { color: #e2e8f0; font-size: 12px; }
.brain-graph-legend { display: flex; flex-wrap: wrap; gap: 10px; }
.brain-graph-legend span { display: inline-flex; align-items: center; gap: 5px; }
.brain-graph-legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--legend-color, #64748b);
  box-shadow: 0 0 10px color-mix(in srgb, var(--legend-color, #64748b) 62%, transparent);
}
.brain-graph-scroll {
  position: relative;
  overflow: auto;
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 14px;
  background:
    radial-gradient(circle at 50% 42%, rgba(59, 130, 246, 0.08), transparent 40%),
    rgba(2, 6, 23, 0.42);
}
.brain-graph-canvas {
  position: relative;
  min-height: 520px;
  isolation: isolate;
}
.brain-stage-lane {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 154px;
  border-right: 1px solid rgba(148, 163, 184, 0.08);
  background: linear-gradient(to bottom, rgba(30, 41, 59, 0.16), transparent 70%);
  pointer-events: none;
}
.brain-stage-lane-label {
  position: absolute;
  top: 12px;
  left: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.brain-stage-lane-label b {
  display: inline-grid;
  place-items: center;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  color: #dbeafe;
  background: rgba(51, 65, 85, 0.72);
  font-size: 10px;
}
.brain-edge-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.brain-edge {
  fill: none;
  stroke: rgba(100, 116, 139, 0.36);
  stroke-width: 1.4;
  vector-effect: non-scaling-stroke;
}
.brain-edge.is-main { stroke: rgba(56, 189, 248, 0.62); stroke-width: 1.8; }
.brain-edge.is-selected { stroke: rgba(250, 204, 21, 0.72); stroke-width: 2; }
.brain-edge.is-active {
  stroke: rgba(52, 211, 153, 0.86);
  stroke-width: 2.2;
  stroke-dasharray: 7 7;
  animation: brain-edge-flow 1.25s linear infinite;
  filter: drop-shadow(0 0 4px rgba(52, 211, 153, 0.48));
}
.brain-node {
  position: absolute;
  left: var(--node-x);
  top: var(--node-y);
  z-index: 3;
  width: 132px;
  color: #e2e8f0;
}
.brain-node[open] { z-index: 20; }
.brain-node > summary {
  position: relative;
  display: grid;
  grid-template-columns: 28px 1fr;
  grid-template-rows: auto auto;
  column-gap: 8px;
  align-items: center;
  min-height: 58px;
  box-sizing: border-box;
  border: 1px solid color-mix(in srgb, var(--node-color) 48%, #334155);
  border-radius: 17px;
  padding: 8px 9px;
  cursor: pointer;
  list-style: none;
  background: color-mix(in srgb, var(--node-color) 11%, rgba(15, 23, 42, 0.96));
  box-shadow: 0 7px 22px rgba(2, 6, 23, 0.32);
  transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
}
.brain-node > summary::-webkit-details-marker { display: none; }
.brain-node > summary:hover {
  transform: translateY(-2px) scale(1.015);
  border-color: color-mix(in srgb, var(--node-color) 80%, white);
  box-shadow: 0 10px 28px rgba(2, 6, 23, 0.46), 0 0 15px color-mix(in srgb, var(--node-color) 24%, transparent);
}
.brain-node.is-selected > summary { box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.28), 0 8px 24px rgba(2, 6, 23, 0.4); }
.brain-node.is-active > summary { box-shadow: 0 0 0 2px rgba(52, 211, 153, 0.36), 0 0 24px rgba(52, 211, 153, 0.18); }
.brain-node.is-write > summary { border-radius: 9px 22px 22px 9px; }
.brain-node-icon {
  grid-row: 1 / span 2;
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  border-radius: 50%;
  color: #f8fafc;
  background: color-mix(in srgb, var(--node-color) 45%, rgba(15, 23, 42, 0.9));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--node-color) 72%, transparent), 0 0 12px color-mix(in srgb, var(--node-color) 24%, transparent);
  font-size: 13px;
}
.brain-node-label {
  overflow: hidden;
  color: #f8fafc;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.brain-node-signal {
  overflow: hidden;
  color: #94a3b8;
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.brain-node-pulse {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--node-color);
  box-shadow: 0 0 10px var(--node-color);
}
.brain-node.is-active .brain-node-pulse { animation: memory-live-pulse 1.25s ease-in-out infinite; }
.brain-node-inspector {
  position: absolute;
  left: 0;
  top: 67px;
  z-index: 30;
  width: min(390px, calc(100vw - 90px));
  max-height: 280px;
  overflow: auto;
  box-sizing: border-box;
  border: 1px solid color-mix(in srgb, var(--node-color) 44%, #475569);
  border-radius: 12px;
  padding: 11px;
  color: #dbeafe;
  background: rgba(2, 6, 23, 0.98);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.58);
}
.brain-node-inspector-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  color: #93c5fd;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.brain-node-inspector pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: #e2e8f0;
  font-size: 10px;
  line-height: 1.45;
}
.brain-node-inspector-foot {
  margin-top: 8px;
  color: #64748b;
  font-size: 8px;
  overflow-wrap: anywhere;
}
.brain-graph-empty {
  position: absolute;
  inset: 72px 24px 24px;
  display: grid;
  place-items: center;
  color: #64748b;
  font-size: 11px;
}
@keyframes brain-edge-flow { to { stroke-dashoffset: -28; } }
@media (prefers-reduced-motion: reduce) {
  .brain-edge.is-active, .brain-node.is-active .brain-node-pulse { animation: none; }
}
.brain-comparison {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(190px, .72fr) minmax(360px, 1.4fr);
  gap: 10px;
  margin: 0 0 14px;
}
.brain-comparison-card {
  border: 1px solid rgba(148, 163, 184, .2);
  border-radius: 13px;
  padding: 10px 12px;
  background: rgba(15, 23, 42, .66);
}
.brain-comparison-card.is-uruha {
  border-color: rgba(52, 211, 153, .42);
  background: linear-gradient(120deg, rgba(6, 78, 59, .32), rgba(30, 41, 59, .72));
  box-shadow: inset 0 0 24px rgba(52, 211, 153, .06);
}
.brain-comparison-label { color: #94a3b8; font-size: 9px; font-weight: 800; letter-spacing: .09em; }
.brain-comparison-lineage { margin-top: 4px; color: #64748b; font-size: 8px; line-height: 1.45; }
.brain-comparison-flow { margin-top: 5px; color: #e2e8f0; font-size: 11px; font-weight: 800; line-height: 1.5; }
.brain-comparison-card.is-uruha .brain-comparison-flow { color: #a7f3d0; }
.brain-comparison-note { margin-top: 4px; color: #64748b; font-size: 9px; }
.fidelity-strip {
  position: relative;
  z-index: 1;
  margin: 10px 0 12px;
  border: 1px solid rgba(248, 113, 113, .35);
  border-radius: 12px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(127, 29, 29, .18), rgba(15, 23, 42, .82));
}
.fidelity-strip-head { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.fidelity-strip-title { color:#fecaca; font-size:10px; font-weight:900; letter-spacing:.08em; }
.fidelity-strip-decision { color:#fca5a5; font-size:10px; font-weight:900; }
.fidelity-strip.is-pass { border-color:rgba(52, 211, 153, .48); background:linear-gradient(135deg, rgba(6, 95, 70, .28), rgba(15, 23, 42, .82)); }
.fidelity-strip.is-pass .fidelity-strip-title { color:#a7f3d0; }
.fidelity-strip.is-pass .fidelity-strip-decision { color:#6ee7b7; }
.fidelity-grid { display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-top:8px; }
.fidelity-metric { border:1px solid rgba(148,163,184,.16); border-radius:9px; padding:7px 8px; background:rgba(15,23,42,.55); }
.fidelity-metric b { display:block; color:#f8fafc; font-size:14px; }
.fidelity-metric span { color:#94a3b8; font-size:9px; }
.fidelity-note { margin-top:7px; color:#cbd5e1; font-size:9px; line-height:1.45; }
.brain-edge.is-understanding { stroke: rgba(167, 139, 250, .82); stroke-width: 2.2; }
.brain-edge.is-pragmatic { stroke: rgba(45, 212, 191, .86); stroke-width: 2.2; }
.brain-edge.is-personhood { stroke: rgba(244, 114, 182, .84); stroke-width: 2.4; }
.brain-edge.is-learning { stroke: rgba(249, 115, 22, .9); stroke-width: 2.3; stroke-dasharray: 7 5; }
@media (max-width: 900px) { .brain-comparison { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .fidelity-grid { grid-template-columns:repeat(2, 1fr); } }
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


def _load_m30_fidelity_summary():
    try:
        payload = json.loads(M30_FIDELITY_RESULT_PATH.read_text(encoding="utf-8"))
        metrics = payload.get("metrics") or {}
        counts = metrics.get("outcome_counts") or {}
        languages = metrics.get("by_language") or {}
        return {
            "available": True,
            "decision": str(payload.get("decision") or "unavailable"),
            "faithful": int(_safe_float(counts.get("faithful_authority"), 0)),
            "valid": int(_safe_float(metrics.get("valid_count"), 0)),
            "false_authority": int(_safe_float(counts.get("false_authority"), 0)),
            "false_reject": int(_safe_float(counts.get("false_reject"), 0)),
            "true_abstention": int(_safe_float(counts.get("true_abstention"), 0)),
            "incomplete": int(_safe_float(metrics.get("incomplete_count"), 0)),
            "faithful_rate": _safe_float(metrics.get("overall_faithful_valid_rate"), 0),
            "negation_accuracy": _safe_float(metrics.get("negation_polarity_accuracy"), 0),
            "median_seconds": _safe_float(metrics.get("median_projection_seconds"), 0),
            "language_rates": {
                language: _safe_float(
                    (languages.get(language) or {}).get("faithful_rate"), 0
                )
                for language in ("zh", "en", "ja")
            },
        }
    except Exception:
        return {"available": False, "decision": "result_unavailable"}


def _load_m32_commit_summary():
    try:
        payload = json.loads(M32_COMMIT_RESULT_PATH.read_text(encoding="utf-8"))
        metrics = payload.get("metrics") or {}
        counts = metrics.get("outcome_counts") or {}
        languages = metrics.get("by_language") or {}
        return {
            "available": True,
            "decision": str(payload.get("decision") or "unavailable"),
            "faithful": int(_safe_float(counts.get("faithful_authority"), 0)),
            "valid": int(_safe_float(metrics.get("valid_count"), 0)),
            "false_authority": int(_safe_float(counts.get("false_authority"), 0)),
            "false_reject": int(_safe_float(counts.get("false_reject"), 0)),
            "true_abstention": int(_safe_float(counts.get("true_abstention"), 0)),
            "incomplete": int(_safe_float(metrics.get("incomplete_count"), 0)),
            "faithful_rate": _safe_float(metrics.get("overall_faithful_valid_rate"), 0),
            "fresh_rate": _safe_float(metrics.get("fresh_session_faithful_rate"), 0),
            "ordinary_negation_rate": _safe_float(
                metrics.get("ordinary_negation_faithful_rate"), 0
            ),
            "negation_accuracy": _safe_float(metrics.get("negation_polarity_accuracy"), 0),
            "median_seconds": _safe_float(metrics.get("median_total_seconds"), 0),
            "p95_seconds": _safe_float(metrics.get("p95_total_seconds"), 0),
            "language_rates": {
                language: _safe_float(
                    (languages.get(language) or {}).get("faithful_rate"), 0
                )
                for language in ("zh", "en", "ja")
            },
        }
    except Exception:
        return {"available": False, "decision": "result_unavailable"}


def _load_m33_source_atom_summary():
    try:
        payload = json.loads(M33_SOURCE_ATOM_RESULT_PATH.read_text(encoding="utf-8"))
        metrics = payload.get("metrics") or {}
        counts = metrics.get("outcome_counts") or {}
        languages = metrics.get("by_language") or {}
        return {
            "available": True,
            "decision": str(payload.get("decision") or "unavailable"),
            "faithful": int(_safe_float(counts.get("faithful_authority"), 0)),
            "valid": int(_safe_float(metrics.get("valid_count"), 0)),
            "false_authority": int(_safe_float(counts.get("false_authority"), 0)),
            "false_reject": int(_safe_float(counts.get("false_reject"), 0)),
            "true_abstention": int(_safe_float(counts.get("true_abstention"), 0)),
            "incomplete": int(_safe_float(metrics.get("incomplete_count"), 0)),
            "faithful_rate": _safe_float(metrics.get("overall_faithful_valid_rate"), 0),
            "fresh_rate": _safe_float(metrics.get("fresh_session_faithful_rate"), 0),
            "direct_japanese_rate": _safe_float(metrics.get("direct_japanese_faithful_rate"), 0),
            "change_rate": _safe_float(metrics.get("change_operator_faithful_rate"), 0),
            "quantity_rate": _safe_float(metrics.get("negated_or_limited_quantity_faithful_rate"), 0),
            "atom_coverage": _safe_float(metrics.get("required_source_atom_trace_coverage"), 0),
            "conflict_repairs": int(_safe_float(metrics.get("m33_conflict_repair_count"), 0)),
            "median_seconds": _safe_float(metrics.get("median_total_seconds"), 0),
            "p95_seconds": _safe_float(metrics.get("p95_total_seconds"), 0),
            "language_rates": {
                language: _safe_float(
                    (languages.get(language) or {}).get("faithful_rate"), 0
                )
                for language in ("zh", "en", "ja")
            },
        }
    except Exception:
        return {"available": False, "decision": "result_unavailable"}


def _load_m34_pragmatic_branch_summary():
    try:
        payload = json.loads(
            M34_PRAGMATIC_BRANCH_RESULT_PATH.read_text(encoding="utf-8")
        )
        metrics = payload.get("metrics") or {}
        return {
            "available": True,
            "decision": str(payload.get("decision") or "unavailable"),
            "case_count": int(_safe_float(metrics.get("case_count"), 0)),
            "pair_count": int(_safe_float(metrics.get("pair_count"), 0)),
            "policy_accuracy": _safe_float(
                metrics.get("selected_policy_accuracy"), 0
            ),
            "pair_divergence": _safe_float(
                metrics.get("counterfactual_pair_divergence_rate"), 0
            ),
            "outcome_accuracy": _safe_float(
                metrics.get("previous_outcome_verification_accuracy"), 0
            ),
            "revision_accuracy": _safe_float(
                metrics.get("contradiction_replacement_accuracy"), 0
            ),
            "trace_coverage": _safe_float(
                metrics.get("verified_context_evidence_trace_coverage"), 0
            ),
            "prediction_coverage": _safe_float(
                metrics.get("observable_prediction_trace_coverage"), 0
            ),
            "visible_japanese": _safe_float(
                metrics.get("visible_japanese_rate"), 0
            ),
            "unsafe_fact_writes": int(
                _safe_float(metrics.get("unverified_mental_fact_write_count"), 0)
            ),
            "median_seconds": _safe_float(metrics.get("median_case_seconds"), 0),
            "p95_seconds": _safe_float(metrics.get("p95_case_seconds"), 0),
        }
    except Exception:
        return {"available": False, "decision": "result_unavailable"}


def _load_m35_same_model_summary():
    try:
        payload = json.loads(M35_SAME_MODEL_RESULT_PATH.read_text(encoding="utf-8"))
        metrics = payload.get("metrics") or {}
        return {
            "available": True,
            "decision": str(payload.get("decision") or "unavailable"),
            "baseline_accuracy": _safe_float(
                metrics.get("baseline_current_policy_accuracy"), 0
            ),
            "system_accuracy": _safe_float(
                metrics.get("system_current_policy_accuracy"), 0
            ),
            "accuracy_delta": _safe_float(
                metrics.get("system_minus_baseline_current_policy_accuracy"), 0
            ),
            "mechanism_accuracy": _safe_float(
                metrics.get("system_mechanism_current_policy_accuracy"), 0
            ),
            "system_pair_divergence": _safe_float(
                metrics.get("system_pair_divergence_rate"), 0
            ),
            "baseline_pair_invariance": _safe_float(
                metrics.get("baseline_pair_policy_invariance_rate"), 0
            ),
            "system_surface": _safe_float(
                metrics.get("system_current_surface_proxy_match_rate"), 0
            ),
            "prompt_ratio": _safe_float(
                metrics.get("system_to_baseline_scored_prompt_token_ratio"), 0
            ),
            "completion_ratio": _safe_float(
                metrics.get("system_to_baseline_completion_token_ratio"), 0
            ),
            "latency_ratio": _safe_float(
                metrics.get("system_to_baseline_latency_ratio"), 0
            ),
            "failed_gate_count": sum(
                not bool(value) for value in (payload.get("gate_results") or {}).values()
            ),
        }
    except Exception:
        return {"available": False, "decision": "result_unavailable"}


def _load_m36_compositional_summary():
    """Read only the immutable M36 result needed by the presentation strip."""
    try:
        payload = json.loads(
            M36_COMPOSITIONAL_RESULT_PATH.read_text(encoding="utf-8")
        )
        metrics = payload.get("metrics") or {}
        return {
            "available": True,
            "decision": str(payload.get("decision") or "unavailable"),
            "case_count": int(_safe_float(metrics.get("case_count"), 0)),
            "baseline_accuracy": _safe_float(
                metrics.get("baseline_current_policy_accuracy"), 0
            ),
            "system_accuracy": _safe_float(
                metrics.get("system_current_policy_accuracy"), 0
            ),
            "accuracy_delta": _safe_float(
                metrics.get("system_minus_baseline_current_policy_accuracy"), 0
            ),
            "mechanism_accuracy": _safe_float(
                metrics.get("system_mechanism_current_policy_accuracy"), 0
            ),
            "outcome_accuracy": _safe_float(
                metrics.get("system_mechanism_feedback_outcome_accuracy"), 0
            ),
            "feedback_policy_accuracy": _safe_float(
                metrics.get("system_feedback_policy_accuracy"), 0
            ),
            "revision_accuracy": _safe_float(
                metrics.get("system_contradiction_revision_accuracy"), 0
            ),
            "system_pair_divergence": _safe_float(
                metrics.get("system_pair_divergence_rate"), 0
            ),
            "current_surface": _safe_float(
                metrics.get("system_current_surface_proxy_match_rate"), 0
            ),
            "feedback_surface": _safe_float(
                metrics.get("system_feedback_surface_proxy_match_rate"), 0
            ),
            "prompt_ratio": _safe_float(
                metrics.get("system_to_baseline_scored_prompt_token_ratio"), 0
            ),
            "latency_ratio": _safe_float(
                metrics.get("system_to_baseline_latency_ratio"), 0
            ),
            "annotation_pass_rate": _safe_float(
                metrics.get("annotation_integrity_pass_rate"), 0
            ),
            "annotation_error_count": int(
                _safe_float(metrics.get("annotation_integrity_error_count"), 0)
            ),
            "feedback_scored_count": int(
                _safe_float(metrics.get("feedback_policy_scored_case_count"), 0)
            ),
            "failed_gate_count": sum(
                not bool(value) for value in (payload.get("gate_results") or {}).values()
            ),
            "human_evidence": bool(
                payload.get("human_felt_understanding_evidence_available")
            ),
        }
    except Exception:
        return {"available": False, "decision": "result_unavailable"}


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


GRAPH_LANES = [
    ("input", "INPUT", "◎", "#38bdf8"),
    ("memory", "MEMORY", "◉", "#a78bfa"),
    ("pragmatics", "PRAGMATICS", "≋", "#2dd4bf"),
    ("other_model", "OTHER MODEL", "◒", "#c084fc"),
    ("hypothesis", "HYPOTHESIS", "◐", "#c084fc"),
    ("evidence", "EVIDENCE", "⌁", "#a78bfa"),
    ("predict", "PREDICTION", "↗", "#2dd4bf"),
    ("verify", "VERIFICATION", "✓", "#fb7185"),
    ("calibrate", "CALIBRATION", "±", "#f97316"),
    ("self", "SELF STATE", "◉", "#60a5fa"),
    ("relationship", "RELATIONSHIP", "∞", "#f472b6"),
    ("appraise", "PERSONA APPRAISAL", "⌬", "#818cf8"),
    ("validate", "VALIDATION", "?", "#fb7185"),
    ("select", "DECISION", "◆", "#facc15"),
    ("surface", "SURFACE", "◈", "#60a5fa"),
    ("learn", "LEARNING", "↶", "#f97316"),
    ("write", "WRITEBACK", "↺", "#f472b6"),
]
GRAPH_LANE_INDEX = {key: index for index, (key, *_rest) in enumerate(GRAPH_LANES)}
GRAPH_KIND_META = {key: (label, icon, color) for key, label, icon, color in GRAPH_LANES}


def _graph_kind(stage, label=""):
    stage = str(stage or "").strip().lower()
    label = str(label or "").strip().lower()
    if stage in {"retrieve", "memory"} or "memory" in label:
        return "memory" if stage == "retrieve" else "write"
    if stage in {"ingest", "input"}:
        return "input"
    if stage in {"attention", "perception", "pragmatics"}:
        return "pragmatics"
    if stage == "other_model":
        return "other_model"
    if stage == "hypothesis":
        return "hypothesis"
    if stage == "evidence":
        return "evidence"
    if stage == "predict":
        return "predict"
    if stage == "verify":
        return "verify"
    if stage in {"calibrate", "observe"}:
        return "calibrate"
    if stage == "self":
        return "self"
    if stage == "relationship":
        return "relationship"
    if stage in {"route", "reason", "appraise"}:
        return "appraise"
    if stage == "validate":
        return "validate"
    if stage in {"select", "plan"}:
        return "select"
    if stage == "surface":
        return "surface"
    if stage == "learn":
        return "learn"
    if stage in {"write", "writeback", "autonomous"}:
        return "write"
    # Unknown runtime stages must remain renderable.  Older code returned a
    # non-existent ``reason`` lane here, which let a successful brain turn fail
    # only when the Safari graph was being built.
    return "appraise"


M24_NODE_DETAIL_BUDGET_BYTES = 2200
M24_GRAPH_DETAIL_BUDGET_BYTES = 160000


def _json_bytes(value):
    try:
        return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return len(str(value or "").encode("utf-8"))


def _bounded_graph_value_m24(value, depth=0):
    """Create a deterministic preview without eagerly rendering a whole trace."""
    if depth >= 4:
        if isinstance(value, dict):
            return {"__m24_omitted__": f"dict:{len(value)}"}
        if isinstance(value, list):
            return {"__m24_omitted__": f"list:{len(value)}"}
    if isinstance(value, dict):
        keys = list(value.keys())
        retained = keys[:36]
        preview = {
            str(key): _bounded_graph_value_m24(value.get(key), depth + 1)
            for key in retained
        }
        if len(keys) > len(retained):
            preview["__m24_omitted_keys__"] = len(keys) - len(retained)
        return preview
    if isinstance(value, list):
        retained = value[:12]
        preview = [_bounded_graph_value_m24(item, depth + 1) for item in retained]
        if len(value) > len(retained):
            preview.append({"__m24_omitted_items__": len(value) - len(retained)})
        return preview
    if isinstance(value, str) and len(value) > 520:
        return value[:480] + f"… [M24 omitted {len(value) - 480} chars]"
    return value


def _graph_detail(payload):
    original_bytes = _json_bytes(payload)
    bounded = _bounded_graph_value_m24(payload)
    try:
        rendered = json.dumps(bounded, ensure_ascii=False, indent=2, default=str)
    except Exception:
        rendered = str(bounded or "")
    rendered_bytes = len(rendered.encode("utf-8"))
    if (
        original_bytes <= M24_NODE_DETAIL_BUDGET_BYTES
        and rendered_bytes <= M24_NODE_DETAIL_BUDGET_BYTES
    ):
        return rendered
    identity_keys = (
        "schema",
        "status",
        "selected_type",
        "selected_mode",
        "selected_policy",
        "authority",
        "surface_status",
        "reason",
    )
    identity = {
        key: payload.get(key)
        for key in identity_keys
        if isinstance(payload, dict) and payload.get(key) not in (None, "", [], {})
    }
    preview_budget = max(480, M24_NODE_DETAIL_BUDGET_BYTES - 760)
    preview_text = rendered.encode("utf-8")[:preview_budget].decode(
        "utf-8",
        errors="ignore",
    )
    return json.dumps(
        {
            **identity,
            "m24_progressive_detail": {
                "status": "bounded_preview",
                "original_bytes": original_bytes,
                "node_budget_bytes": M24_NODE_DETAIL_BUDGET_BYTES,
                "full_trace_retained_in": "local_web_jsonl",
            },
            "preview": preview_text,
        },
        ensure_ascii=False,
        indent=2,
    )


def _graph_signal(payload):
    if isinstance(payload, dict):
        schema = str(payload.get("schema") or "")
        if schema == "uruha_user_mental_state_hypothesis_v2_12":
            inferred = payload.get("inferred") or {}
            intent = (inferred.get("possible_intent") or {}).get("value")
            return _trim(intent or "暫定使用者模型", 42)
        if schema == "uruha_hypothesis_verification_v2_12":
            return _trim(f"{payload.get('status', 'unknown')} · {payload.get('summary', '')}", 42)
        if schema == "uruha_hypothesis_calibration_v2_12":
            return _trim(
                f"{payload.get('last_verification_status', 'none')} · confidence {payload.get('last_adjustment', 0):+}",
                42,
            )
        if schema == "uruha_next_user_action_prediction_v2_12":
            return _trim(payload.get("next_user_action") or payload.get("expected_feature"), 42)
        if schema == "uruha_human_pragmatic_understanding_v2_13":
            acoustic = payload.get("acoustic_evidence") or {}
            return _trim(
                f"{payload.get('pragmatic_label', 'unknown')} · audio {acoustic.get('availability', 'unknown')}",
                42,
            )
        if schema == "uruha_pragmatic_verification_v2_13":
            return _trim(f"{payload.get('status', 'unknown')} · pragmatic outcome", 42)
        if schema == "uruha_longitudinal_other_model_v2_13":
            summary = payload.get("summary") or {}
            layers = summary.get("layers") or {}
            return _trim(
                " · ".join(
                    f"{name} {int((layers.get(name) or {}).get('active', 0))}"
                    for name in ("stable", "situational", "provisional")
                ),
                42,
            )
        if schema == "uruha_typed_prediction_calibration_v2_13":
            return _trim(
                f"samples {payload.get('sample_count', 0)} · best {payload.get('most_reliable') or 'insufficient'}",
                42,
            )
        if schema == "uruha_active_validation_strategy_v2_13":
            pending = payload.get("pending") or {}
            return _trim(
                "主動確認 · " + str(pending.get("kind") or "none")
                if payload.get("changed_plan")
                else "模型已參與規劃 · 不需追加確認",
                42,
            )
        if schema == "uruha_longitudinal_other_model_update_v2_13":
            return _trim(
                f"revision {len(payload.get('revisions') or []) + len(payload.get('pragmatic_revisions') or [])} · decay {len(payload.get('decay_events') or [])}",
                42,
            )
        if schema in {
            "uruha_desired_response_feedback_update_m16",
            "uruha_desired_response_feedback_update_m17",
            "uruha_desired_response_feedback_update_m18",
        }:
            context_scope = payload.get("context_scope") or {}
            if not isinstance(context_scope, dict):
                context_scope = {}
            return _trim(
                f"{payload.get('status', 'unknown')} · {payload.get('previous_policy_id') or 'no previous policy'} · {context_scope.get('domain') or 'unscoped'}",
                42,
            )
        if schema in {"uruha_adaptive_context_scope_m17", "uruha_adaptive_context_scope_m18"}:
            return _trim(
                f"{payload.get('domain', 'general')} · {payload.get('interaction_kind', 'ordinary')} · {payload.get('relationship_band', 'unspecified')}",
                42,
            )
        if schema == "uruha_adaptive_scope_hierarchy_m18":
            return _trim(
                f"{payload.get('status', 'none')} · used {len(payload.get('used') or [])} · blocked {payload.get('negative_transfer_gate_count', 0)}",
                42,
            )
        if schema in {
            "uruha_desired_response_state_m16",
            "uruha_desired_response_state_m17",
            "uruha_desired_response_state_m18",
        }:
            context_scope = payload.get("context_scope") or {}
            if not isinstance(context_scope, dict):
                context_scope = {}
            return _trim(
                f"{context_scope.get('domain') or 'unscoped'} · learned {len(payload.get('learned_atoms_used') or [])} · rejected {len(payload.get('learned_atoms_rejected') or [])}",
                42,
            )
        if schema in {
            "uruha_desired_response_candidates_m16",
            "uruha_desired_response_candidates_m17",
            "uruha_desired_response_candidates_m18",
        }:
            candidates = payload.get("candidates") or []
            selected = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
            return _trim(
                f"{selected.get('policy_id') or payload.get('status', 'inactive')} · margin {payload.get('utility_margin')}",
                42,
            )
        if schema in {
            "uruha_desired_response_decision_m16",
            "uruha_desired_response_decision_m17",
            "uruha_desired_response_decision_m18",
        }:
            selected = payload.get("selected") or {}
            if not isinstance(selected, dict):
                selected = {}
            return _trim(
                f"{selected.get('policy_id') or payload.get('status', 'inactive')} · desired response",
                42,
            )
        if schema == "uruha_composable_response_dimensions_m18":
            dimensions = payload.get("response_dimensions") or payload
            values = dimensions.get("values") or {}
            top = sorted(values.items(), key=lambda row: -float(row[1] or 0.0))[:2]
            return _trim(
                " · ".join(f"{name} {float(value):.2f}" for name, value in top)
                or "dimension vector inactive",
                42,
            )
        if schema in {
            "uruha_adaptive_person_persistence_m16",
            "uruha_adaptive_person_persistence_m17",
            "uruha_adaptive_person_persistence_m18",
        }:
            return _trim(
                f"{payload.get('status', 'unknown')} · revisions {payload.get('revision_count', 0)} · no raw text",
                42,
            )
        if schema in {
            "uruha_adaptive_person_surface_commitment_m16",
            "uruha_adaptive_person_surface_commitment_m17",
            "uruha_adaptive_person_surface_commitment_m18",
        }:
            return _trim(
                f"{payload.get('policy_id') or 'inactive'} · visible {str(bool(payload.get('policy_performed'))).lower()}",
                42,
            )
        if schema == "uruha_current_turn_semantic_commit_m48":
            return _trim(
                f"{payload.get('scope_domain', 'unknown')} · preserve {str(bool(payload.get('current_turn_semantics_preserved'))).lower()}",
                42,
            )
        if schema == "uruha_semantic_preserving_japanese_repair_m49":
            return _trim(
                f"{payload.get('status', 'unknown')} · authority {str(bool(payload.get('surface_authority'))).lower()}",
                42,
            )
        if schema == "uruha_human_priority_scheduler_m19":
            return _trim(
                f"{payload.get('last_decision', 'waiting')} · humans {payload.get('human_waiters', 0)}",
                42,
            )
        if schema == "uruha_correction_aware_surface_m20":
            return _trim(
                f"revoke {payload.get('revoked_previous_policy') or 'none'} · repair {payload.get('selected_repair_policy') or payload.get('explicit_target_policy') or 'none'}",
                42,
            )
        if schema == "uruha_lightweight_surface_delivery_m20":
            return _trim(
                f"chunks {payload.get('stream_chunk_count', 0)} · full graph {payload.get('full_payload_update_count', 0)}",
                42,
            )
        if schema == "uruha_bounded_slow_path_planner_m21":
            stages = payload.get("stage_seconds") or {}
            return _trim(
                f"{payload.get('route', 'unknown')} · {stages.get('cognitive_total', payload.get('planner_seconds', 0))}s · budget {str(bool(payload.get('budget_met'))).lower()}",
                42,
            )
        if schema == "uruha_semantic_route_taxonomy_m22":
            return _trim(
                f"{payload.get('selected_type', 'unknown')} → {payload.get('performed_route', payload.get('recommended_route', 'pending'))} · {payload.get('contract_status', 'pending')}",
                42,
            )
        if schema == "uruha_desired_response_mode_m23":
            return _trim(
                f"{payload.get('selected_mode') or 'inactive'} · {payload.get('authority', 'none')} · {payload.get('surface_status', 'pending')}",
                42,
            )
        if schema == "uruha_cross_lingual_explicit_desired_response_m25":
            return _trim(
                f"{payload.get('selected_mode') or 'none'} · {payload.get('authority', 'none')} · {payload.get('surface_status', payload.get('status', 'pending'))}",
                42,
            )
        if schema == "uruha_compositional_multilingual_pragmatic_cue_m36":
            return _trim(
                f"{payload.get('status', 'not_applied')} · cues {payload.get('compositional_match_count', 0)} · linked {str(bool(payload.get('feedback_linked_to_previous_prediction'))).lower()}",
                42,
            )
        if schema == "uruha_pragmatic_trigger_relation_m37":
            return _trim(
                f"{payload.get('trigger_predicate') or 'no trigger'} → {payload.get('selected_policy') or 'no policy'} · {payload.get('status', 'not_applied')}",
                42,
            )
        if schema == "uruha_outcome_calibrated_implicit_response_distribution_m26":
            return _trim(
                f"{payload.get('implicit_top_mode') or 'inactive'} · p {float(payload.get('top_probability') or 0.0):.2f} · {payload.get('status', 'pending')}",
                42,
            )
        if schema == "uruha_implicit_response_outcome_update_m26":
            return _trim(
                f"{payload.get('status', 'unknown')} · reliability {float(payload.get('scoped_reliability_before') or 0.5):.2f}→{float(payload.get('scoped_reliability_after') or 0.5):.2f}",
                42,
            )
        if schema == "uruha_causal_outcome_calibration_ledger_m27":
            return _trim(
                f"{payload.get('result_status') or payload.get('status', 'unknown')} · causal {str(bool(payload.get('feedback_linked_to_prediction'))).lower()}",
                42,
            )
        if schema == "uruha_causal_outcome_calibration_summary_m27":
            risk = payload.get("selective_risk")
            risk_text = "unavailable" if risk is None else f"{float(risk):.2f}"
            return _trim(
                f"n {payload.get('effective_decisive_executed_samples', 0)}/{payload.get('minimum_decisive_executed_samples', 0)} · risk {risk_text}",
                42,
            )
        if schema == "uruha_feedback_topic_transition_m28":
            return _trim(
                f"{payload.get('status', 'not_applied')} · {payload.get('topic_kind') or 'ordinary'}",
                42,
            )
        if schema == "uruha_generalized_literal_topic_projection_m29":
            return _trim(
                f"{payload.get('status', 'not_applied')} · {payload.get('subject_jp') or 'no subject'}",
                42,
            )
        if schema == "uruha_semantic_authorization_m31":
            return _trim(
                f"{payload.get('status', 'not_applied')} · {payload.get('source_polarity') or 'unknown'}",
                42,
            )
        if schema == "uruha_deterministic_semantic_commit_m32":
            return _trim(
                f"{payload.get('status', 'not_applied')} · {payload.get('repair_kind') or 'no override'} · {payload.get('surface_status', 'pending')}",
                42,
            )
        if schema == "uruha_source_semantic_atom_ledger_m33":
            return _trim(
                f"{payload.get('status', 'not_applied')} · {payload.get('family') or 'no family'} · atoms {payload.get('atom_count', 0)}",
                42,
            )
        if schema == "uruha_source_atom_verification_m33":
            return _trim(
                f"{payload.get('status', 'not_applied')} · conflicts {payload.get('conflict_atom_count', 0)}",
                42,
            )
        if schema == "uruha_source_anchored_semantic_commit_m33":
            return _trim(
                f"{payload.get('status', 'not_applied')} · {payload.get('repair_kind') or 'no commit'} · {payload.get('surface_status', 'pending')}",
                42,
            )
        if schema == "uruha_counterfactual_pragmatic_branch_ledger_m34":
            selected = payload.get("selected_branch") or {}
            return _trim(
                f"{selected.get('mode') or 'none'} · {selected.get('authority_basis') or 'no authority'} · {payload.get('surface_status', 'pending')}",
                42,
            )
        if schema == "uruha_pragmatic_branch_prediction_m34":
            return _trim(
                f"{payload.get('selected_policy_id') or 'none'} · verify {payload.get('verification_window', 'unavailable')}",
                42,
            )
        if schema == "uruha_pragmatic_branch_verification_m34":
            return _trim(
                f"{payload.get('status', 'not_available')} · previous {payload.get('previous_policy_id') or 'none'}",
                42,
            )
        if schema == "uruha_pragmatic_branch_revision_m34":
            return _trim(
                f"{payload.get('status', 'no_revision')} · {payload.get('revoked_policy_id') or 'none'}→{payload.get('replacement_policy_id') or 'none'}",
                42,
            )
        if schema == "uruha_pragmatic_branch_surface_m34":
            return _trim(
                f"{payload.get('selected_policy_id') or 'none'} · {payload.get('status', 'pending')}",
                42,
            )
        if schema in {"uruha_runtime_latency_m17", "uruha_runtime_latency_m18", "uruha_runtime_latency_m19"}:
            if schema == "uruha_runtime_latency_m19":
                return _trim(
                    f"queue {payload.get('frontend_queue_wait_seconds', 0)}s · brain {payload.get('brain_work_seconds', 0)}s · surface {payload.get('surface_stream_seconds', 0)}s",
                    42,
                )
            return _trim(
                f"wait {payload.get('user_wait_seconds', payload.get('brain_turn_seconds', 0))}s · cognition {payload.get('cognition_seconds', 0)}s · target {str(bool(payload.get('target_met'))).lower()}",
                42,
            )
        if payload.get("persona_stance") and "trust" in payload:
            return _trim(f"mood {payload.get('mood')} · trust {payload.get('trust')}", 42)
        if payload.get("phase") and "trust_score" in payload:
            return _trim(f"{payload.get('phase')} · trust {payload.get('trust_score')}", 42)
        if payload.get("pragmatic_label") and payload.get("evaluation_rule"):
            return _trim(f"人格評估 · {payload.get('pragmatic_label')}", 42)
        if payload.get("other_model_used") is not None and payload.get("intent"):
            return _trim(f"{payload.get('intent')} · other/self/persona used", 42)
        if payload.get("verification_status") and payload.get("relationship_learning"):
            return _trim(
                f"{payload.get('verification_status')} · pragmatic {payload.get('pragmatic_verification_status')}",
                42,
            )
        if payload.get("hypothesis_id") and any(key in payload for key in ("known", "evidence", "unknown")):
            return _trim(
                f"證據 {len(payload.get('evidence') or [])} · 未知 {len(payload.get('unknown') or [])}",
                42,
            )
        for key in (
            "actual_intent",
            "route",
            "intent",
            "focus",
            "goal",
            "selected_intent",
            "candidate_label",
            "response_mode",
            "reply_goal",
            "expected_intent",
            "summary",
            "text",
        ):
            if payload.get(key) not in (None, "", [], {}):
                return _trim(payload.get(key), 38)
        return f"{len(payload)} fields"
    if isinstance(payload, list):
        return f"{len(payload)} items"
    return _trim(payload, 38) or "runtime event"


def collect_cognitive_graph(result):
    """Build a deterministic runtime graph for the visual observatory."""
    result = result or {}
    runtime_trace = result.get("runtime_trace") or {}
    blackboard = list(runtime_trace.get("blackboard") or [])
    state_diff = runtime_trace.get("state_diff") or {}
    graph_nodes = []
    graph_edges = []

    def add_node(node_id, kind, label, signal, detail, **extra):
        graph_nodes.append(
            {
                "id": str(node_id),
                "kind": kind,
                "layer": GRAPH_LANE_INDEX[kind],
                "label": _trim(label, 38) or "node",
                "signal": _trim(signal, 42) or "runtime event",
                "detail": str(detail or ""),
                **extra,
            }
        )

    user_text = result.get("user_text") or "等待輸入"
    add_node("turn-input", "input", "USER SIGNAL", user_text, user_text, active=bool(result))

    blackboard_ids = []
    for index, item in enumerate(blackboard):
        if not isinstance(item, dict):
            continue
        node_id = f"runtime-{index}"
        kind = _graph_kind(item.get("stage"), item.get("label"))
        payload = item.get("payload")
        add_node(
            node_id,
            kind,
            item.get("label") or item.get("stage") or "runtime",
            _graph_signal(payload),
            _graph_detail(payload),
            active=True,
            salience=_safe_float(item.get("salience"), 0.0),
            trace_id=f"blackboard:{index}:{item.get('stage')}:{item.get('label')}",
        )
        blackboard_ids.append(node_id)

    memory_node_ids = []
    for index, memory in enumerate(collect_memory_nodes(result)):
        node_id = f"memory-{index}"
        label, _icon, _color = SOURCE_META[memory["source_key"]]
        add_node(
            node_id,
            "memory",
            label,
            memory.get("text") or "memory",
            _graph_detail(memory),
            memory=True,
            selected=bool(memory.get("selected")),
            active=bool(memory.get("passed")),
            score=_safe_float(memory.get("score"), 0.0),
            source_key=memory["source_key"],
            trace_id=memory.get("trace_id"),
        )
        memory_node_ids.append(node_id)

    state_node_ids = []
    state_specs = [
        ("psyche", "mood", "MOOD Δ"),
        ("psyche", "trust", "TRUST Δ"),
        ("focus", None, "FOCUS Δ"),
        ("goal", None, "GOAL Δ"),
    ]
    for section, field, label in state_specs:
        payload = state_diff.get(section) or {}
        if not isinstance(payload, dict) or not payload:
            continue
        if field:
            before = payload.get(f"{field}_before")
            after = payload.get(f"{field}_after")
        else:
            before = payload.get("before")
            after = payload.get("after")
        if before is None and after is None:
            continue
        node_id = f"state-{section}-{field or 'value'}"
        add_node(
            node_id,
            "select",
            label,
            f"{before if before not in (None, '') else '∅'} → {after if after not in (None, '') else '∅'}",
            _graph_detail(payload),
            active=before != after,
            state=True,
            trace_id=node_id,
        )
        state_node_ids.append(node_id)

    write_node_ids = []
    for index, row in enumerate(runtime_trace.get("memory_writes") or []):
        if not isinstance(row, dict):
            continue
        node_id = f"write-{index}"
        add_node(
            node_id,
            "write",
            row.get("layer") or "WRITEBACK",
            row.get("summary") or row.get("kind") or "memory write",
            _graph_detail(row),
            active=True,
            write=True,
            trace_id=f"write:{index}:{row.get('layer')}",
        )
        write_node_ids.append(node_id)

    reply = result.get("reply") or ""
    if not reply:
        for item in reversed(blackboard):
            if item.get("label") == "utterance":
                reply = _graph_signal(item.get("payload"))
                break
    add_node("turn-output", "surface", "UTTERANCE", reply or "等待輸出", reply or "等待輸出", active=bool(reply))

    def add_edge(source, target, edge_class=""):
        if source and target and source != target:
            graph_edges.append({"source": source, "target": target, "class": edge_class})

    if blackboard_ids:
        add_edge("turn-input", blackboard_ids[0], "is-main")
        for source, target in zip(blackboard_ids, blackboard_ids[1:]):
            add_edge(source, target, "is-main")
        add_edge(blackboard_ids[-1], "turn-output", "is-main")
    else:
        add_edge("turn-input", "turn-output", "is-main")

    retrieval_id = next((node["id"] for node in graph_nodes if node["id"].startswith("runtime-") and node["kind"] == "memory"), "turn-input")
    attention_id = next((node["id"] for node in graph_nodes if node["id"].startswith("runtime-") and node["label"] == "attention_frame"), None)
    decision_id = next((node["id"] for node in graph_nodes if node["id"].startswith("runtime-") and node["label"] == "selected_plan"), None)
    hypothesis_id = next((node["id"] for node in graph_nodes if node.get("label") == "user_mental_state_hypothesis"), None)
    evidence_id = next((node["id"] for node in graph_nodes if node.get("label") == "hypothesis_evidence"), None)
    next_prediction_id = next((node["id"] for node in graph_nodes if node.get("label") == "next_user_prediction_v2_12"), None)
    verification_id = next((node["id"] for node in graph_nodes if node.get("label") == "hypothesis_outcome_verification"), None)
    calibration_id = next((node["id"] for node in graph_nodes if node.get("label") == "hypothesis_calibration_update"), None)
    pragmatic_id = next((node["id"] for node in graph_nodes if node.get("label") == "human_pragmatic_understanding_v2_13"), None)
    pragmatic_verification_id = next((node["id"] for node in graph_nodes if node.get("label") == "pragmatic_outcome_verification_v2_13"), None)
    other_model_id = next((node["id"] for node in graph_nodes if node.get("label") == "persistent_other_model_v2_13"), None)
    typed_calibration_id = next((node["id"] for node in graph_nodes if node.get("label") == "typed_calibration_v2_13"), None)
    self_state_id = next((node["id"] for node in graph_nodes if node.get("label") == "personhood_self_state_v2_13"), None)
    relationship_id = next((node["id"] for node in graph_nodes if node.get("label") == "personhood_relationship_state_v2_13"), None)
    persona_appraisal_id = next((node["id"] for node in graph_nodes if node.get("label") == "personhood_persona_appraisal_v2_13"), None)
    active_validation_id = next((node["id"] for node in graph_nodes if node.get("label") == "active_validation_strategy_v2_13"), None)
    action_choice_id = next((node["id"] for node in graph_nodes if node.get("label") == "personhood_action_choice_v2_13"), None)
    learning_id = next((node["id"] for node in graph_nodes if node.get("label") == "personhood_outcome_learning_v2_13"), None)
    def node_id_for(*labels):
        return next(
            (node["id"] for node in graph_nodes if node.get("label") in labels),
            None,
        )

    adaptive_feedback_id = node_id_for(
        "adaptive_person_feedback_update_m18",
        "adaptive_person_feedback_update_m17",
        "adaptive_person_feedback_update_m16",
    )
    adaptive_scope_id = node_id_for("adaptive_context_scope_m18", "adaptive_context_scope_m17")
    adaptive_hierarchy_id = node_id_for("adaptive_scope_hierarchy_m18")
    desired_state_id = node_id_for("desired_response_state_m18", "desired_response_state_m17", "desired_response_state_m16")
    desired_candidates_id = node_id_for("desired_response_candidates_m18", "desired_response_candidates_m17", "desired_response_candidates_m16")
    response_dimensions_id = node_id_for("adaptive_response_dimensions_m18")
    desired_prediction_id = node_id_for("desired_response_prediction_m18", "desired_response_prediction_m17", "desired_response_prediction_m16")
    adaptive_persistence_id = node_id_for("adaptive_person_persistence_m18", "adaptive_person_persistence_m17", "adaptive_person_persistence_m16")
    adaptive_surface_id = node_id_for("adaptive_person_surface_commitment_m18", "adaptive_person_surface_commitment_m17", "adaptive_person_surface_commitment_m16")
    current_semantic_commit_m48_id = node_id_for(
        "current_turn_semantic_commit_m48"
    )
    semantic_japanese_repair_m49_id = node_id_for(
        "japanese_semantic_repair_m49"
    )
    explicit_conversation_act_p3_b50_id = node_id_for(
        "explicit_conversation_act_p3_b50"
    )
    visible_language_guard_id = node_id_for("visible_language_guard")
    correction_id = node_id_for("correction_aware_surface_m20")
    correction_surface_id = node_id_for("correction_surface_commit_m20")
    surface_delivery_id = node_id_for("surface_delivery_m20")
    bounded_planner_id = node_id_for("bounded_slow_path_planner_m21")
    semantic_route_id = node_id_for(
        "semantic_route_classifier_m22",
        "semantic_route_outcome_m22",
    )
    desired_mode_id = node_id_for("desired_response_mode_m23")
    desired_mode_surface_id = node_id_for("desired_response_surface_contract_m23")
    explicit_mode_id = node_id_for("explicit_desired_response_m25")
    explicit_mode_surface_id = node_id_for(
        "explicit_desired_response_surface_m25"
    )
    compositional_pragmatic_m36_id = node_id_for(
        "compositional_pragmatic_cue_m36"
    )
    pragmatic_trigger_relation_m37_id = node_id_for(
        "pragmatic_trigger_relation_m37"
    )
    implicit_distribution_id = node_id_for(
        "implicit_response_distribution_m26"
    )
    implicit_outcome_id = node_id_for(
        "implicit_desired_response_outcome_m26"
    )
    causal_outcome_resolution_id = node_id_for(
        "causal_outcome_resolution_m27"
    )
    causal_calibration_ledger_id = node_id_for(
        "causal_outcome_calibration_ledger_m27"
    )
    feedback_topic_transition_id = node_id_for(
        "feedback_topic_transition_m28"
    )
    feedback_topic_surface_id = node_id_for(
        "feedback_topic_surface_m28"
    )
    literal_topic_projection_id = node_id_for(
        "literal_topic_projection_m29"
    )
    literal_topic_surface_id = node_id_for(
        "literal_topic_surface_m29"
    )
    semantic_authorization_id = node_id_for(
        "semantic_authorization_m31"
    )
    semantic_authorized_surface_id = node_id_for(
        "semantic_authorized_surface_m31"
    )
    semantic_commit_id = node_id_for(
        "semantic_commit_repair_m32"
    )
    semantic_commit_surface_id = node_id_for(
        "semantic_commit_surface_m32"
    )
    source_atoms_id = node_id_for("source_semantic_atoms_m33")
    atom_verification_id = node_id_for("semantic_atom_verification_m33")
    source_anchored_commit_id = node_id_for(
        "source_anchored_semantic_commit_m33"
    )
    source_anchored_surface_id = node_id_for(
        "source_anchored_semantic_surface_m33"
    )
    pragmatic_branch_id = node_id_for("pragmatic_branch_ledger_m34")
    pragmatic_branch_prediction_id = node_id_for(
        "pragmatic_branch_prediction_m34"
    )
    pragmatic_branch_verification_id = node_id_for(
        "pragmatic_branch_verification_m34"
    )
    pragmatic_branch_revision_id = node_id_for(
        "pragmatic_branch_revision_m34"
    )
    pragmatic_branch_surface_id = node_id_for("pragmatic_branch_surface_m34")
    add_edge(verification_id, calibration_id, "is-understanding")
    add_edge(calibration_id, hypothesis_id, "is-understanding")
    add_edge(hypothesis_id, evidence_id, "is-understanding")
    add_edge(evidence_id, next_prediction_id, "is-understanding")
    add_edge(next_prediction_id, decision_id, "is-understanding")
    add_edge("turn-input", pragmatic_id, "is-pragmatic")
    add_edge(pragmatic_id, other_model_id, "is-pragmatic")
    add_edge(pragmatic_id, hypothesis_id, "is-pragmatic")
    add_edge(pragmatic_verification_id, typed_calibration_id, "is-pragmatic")
    add_edge(other_model_id, self_state_id, "is-personhood")
    add_edge(other_model_id, relationship_id, "is-personhood")
    add_edge(self_state_id, persona_appraisal_id, "is-personhood")
    add_edge(relationship_id, persona_appraisal_id, "is-personhood")
    add_edge(pragmatic_id, persona_appraisal_id, "is-personhood")
    add_edge(persona_appraisal_id, active_validation_id, "is-personhood")
    add_edge(active_validation_id, action_choice_id or decision_id, "is-personhood")
    add_edge(action_choice_id or decision_id, "turn-output", "is-personhood")
    add_edge("turn-output", learning_id, "is-learning")
    add_edge(learning_id, other_model_id, "is-learning")
    add_edge("turn-input", adaptive_feedback_id, "is-learning")
    add_edge(adaptive_feedback_id, adaptive_scope_id or desired_state_id, "is-learning")
    add_edge(adaptive_feedback_id, correction_id, "is-learning")
    add_edge(adaptive_scope_id, adaptive_hierarchy_id or desired_state_id, "is-understanding")
    add_edge(adaptive_hierarchy_id, desired_state_id, "is-understanding")
    add_edge(other_model_id, desired_state_id, "is-personhood")
    add_edge(desired_state_id, desired_candidates_id, "is-understanding")
    add_edge(desired_candidates_id, response_dimensions_id, "is-understanding")
    add_edge(response_dimensions_id, desired_prediction_id, "is-understanding")
    add_edge(desired_candidates_id, desired_prediction_id, "is-understanding")
    add_edge(desired_candidates_id or adaptive_hierarchy_id, semantic_route_id or bounded_planner_id, "is-understanding")
    add_edge(desired_candidates_id, desired_mode_id, "is-understanding")
    add_edge(desired_candidates_id, implicit_distribution_id, "is-understanding")
    add_edge(adaptive_feedback_id, implicit_outcome_id, "is-learning")
    add_edge(implicit_outcome_id, implicit_distribution_id, "is-learning")
    add_edge(implicit_outcome_id, causal_outcome_resolution_id, "is-learning")
    add_edge(causal_outcome_resolution_id, causal_calibration_ledger_id, "is-learning")
    add_edge(implicit_distribution_id, causal_calibration_ledger_id, "is-learning")
    add_edge(causal_calibration_ledger_id, adaptive_persistence_id, "is-learning")
    add_edge("turn-input", feedback_topic_transition_id, "is-pragmatic")
    add_edge(adaptive_feedback_id, feedback_topic_transition_id, "is-learning")
    add_edge(causal_outcome_resolution_id, feedback_topic_transition_id, "is-learning")
    add_edge(feedback_topic_transition_id, feedback_topic_surface_id, "is-personhood")
    add_edge(feedback_topic_surface_id, "turn-output", "is-personhood")
    add_edge("turn-input", literal_topic_projection_id, "is-pragmatic")
    add_edge(feedback_topic_transition_id, literal_topic_projection_id, "is-understanding")
    add_edge(literal_topic_projection_id, semantic_authorization_id, "is-understanding")
    add_edge(semantic_authorization_id, semantic_commit_id, "is-understanding")
    add_edge(semantic_commit_id, semantic_commit_surface_id, "is-personhood")
    add_edge(semantic_commit_surface_id, "turn-output", "is-personhood")
    add_edge("turn-input", source_atoms_id, "is-pragmatic")
    add_edge(source_atoms_id, atom_verification_id, "is-understanding")
    add_edge(semantic_authorization_id, atom_verification_id, "is-understanding")
    add_edge(semantic_commit_id, atom_verification_id, "is-understanding")
    add_edge(atom_verification_id, source_anchored_commit_id, "is-understanding")
    add_edge(source_anchored_commit_id, source_anchored_surface_id, "is-personhood")
    add_edge(source_anchored_surface_id, "turn-output", "is-personhood")
    add_edge(pragmatic_id, pragmatic_branch_id, "is-understanding")
    add_edge(desired_candidates_id, pragmatic_branch_id, "is-understanding")
    add_edge(implicit_distribution_id, pragmatic_branch_id, "is-understanding")
    add_edge(source_atoms_id, pragmatic_branch_id, "is-pragmatic")
    add_edge(pragmatic_branch_id, pragmatic_branch_prediction_id, "is-understanding")
    add_edge(adaptive_feedback_id, pragmatic_branch_verification_id, "is-learning")
    add_edge(pragmatic_branch_verification_id, pragmatic_branch_revision_id, "is-learning")
    add_edge(pragmatic_branch_revision_id, pragmatic_branch_id, "is-learning")
    add_edge(pragmatic_branch_prediction_id, pragmatic_branch_surface_id, "is-personhood")
    add_edge(pragmatic_branch_surface_id, "turn-output", "is-personhood")
    add_edge(semantic_authorization_id, semantic_authorized_surface_id, "is-personhood")
    add_edge(semantic_authorized_surface_id, "turn-output", "is-personhood")
    add_edge(literal_topic_projection_id, literal_topic_surface_id, "is-personhood")
    add_edge(literal_topic_surface_id, "turn-output", "is-personhood")
    add_edge(implicit_distribution_id, desired_mode_id, "is-understanding")
    add_edge("turn-input", explicit_mode_id, "is-understanding")
    add_edge("turn-input", compositional_pragmatic_m36_id, "is-pragmatic")
    add_edge(adaptive_feedback_id, compositional_pragmatic_m36_id, "is-learning")
    add_edge(compositional_pragmatic_m36_id, explicit_mode_id, "is-understanding")
    add_edge(compositional_pragmatic_m36_id, pragmatic_branch_id, "is-understanding")
    add_edge("turn-input", pragmatic_trigger_relation_m37_id, "is-pragmatic")
    add_edge(explicit_mode_id, pragmatic_trigger_relation_m37_id, "is-understanding")
    add_edge(adaptive_feedback_id, pragmatic_trigger_relation_m37_id, "is-learning")
    add_edge(adaptive_persistence_id, pragmatic_trigger_relation_m37_id, "is-learning")
    add_edge(pragmatic_trigger_relation_m37_id, pragmatic_branch_id, "is-understanding")
    add_edge(explicit_mode_id, desired_mode_id, "is-understanding")
    add_edge(semantic_route_id, desired_mode_id, "is-understanding")
    add_edge(semantic_route_id, bounded_planner_id, "is-understanding")
    add_edge(bounded_planner_id, action_choice_id or decision_id, "is-active")
    add_edge(desired_prediction_id, action_choice_id or decision_id, "is-personhood")
    add_edge(correction_id, desired_prediction_id, "is-understanding")
    add_edge(action_choice_id or decision_id, current_semantic_commit_m48_id or adaptive_surface_id, "is-personhood")
    add_edge(current_semantic_commit_m48_id, adaptive_surface_id, "is-understanding")
    add_edge(
        current_semantic_commit_m48_id or adaptive_surface_id,
        explicit_conversation_act_p3_b50_id
        or semantic_japanese_repair_m49_id,
        "is-understanding",
    )
    add_edge(
        explicit_conversation_act_p3_b50_id,
        semantic_japanese_repair_m49_id or visible_language_guard_id,
        "is-understanding",
    )
    add_edge(
        semantic_japanese_repair_m49_id
        or explicit_conversation_act_p3_b50_id,
        visible_language_guard_id or "turn-output",
        "is-understanding",
    )
    add_edge(
        explicit_mode_id,
        explicit_conversation_act_p3_b50_id,
        "is-pragmatic",
    )
    add_edge(visible_language_guard_id, "turn-output", "is-personhood")
    add_edge(adaptive_surface_id, correction_surface_id or "turn-output", "is-personhood")
    add_edge(desired_mode_id, desired_mode_surface_id, "is-personhood")
    add_edge(desired_mode_surface_id, "turn-output", "is-personhood")
    add_edge(explicit_mode_id, explicit_mode_surface_id, "is-personhood")
    add_edge(explicit_mode_surface_id, "turn-output", "is-personhood")
    add_edge(correction_surface_id, "turn-output", "is-personhood")
    add_edge("turn-output", surface_delivery_id, "is-active")
    add_edge(desired_prediction_id, adaptive_persistence_id, "is-learning")
    add_edge(adaptive_persistence_id, desired_state_id, "is-learning")
    memory_by_id = {node["id"]: node for node in graph_nodes if node.get("memory")}
    for memory_id in memory_node_ids:
        memory = memory_by_id[memory_id]
        add_edge(retrieval_id, memory_id, "")
        if memory.get("selected"):
            add_edge(memory_id, attention_id or decision_id, "is-selected")
        if memory.get("active"):
            add_edge(memory_id, decision_id or "turn-output", "is-active")

    for state_id in state_node_ids:
        add_edge(decision_id or "turn-input", state_id, "is-selected")
    for write_id in write_node_ids:
        add_edge("turn-output", write_id, "is-active")

    layer_rows = {index: [] for index in range(len(GRAPH_LANES))}
    for node in graph_nodes:
        layer_rows[node["layer"]].append(node)
    max_rows = max((len(rows) for rows in layer_rows.values()), default=1)
    width = len(GRAPH_LANES) * 170
    height = max(520, 104 + max_rows * 92)
    usable_height = height - 92
    for layer, rows in layer_rows.items():
        if not rows:
            continue
        step = usable_height / len(rows)
        for row_index, node in enumerate(rows):
            node["x"] = layer * 170 + 18
            node["y"] = 51 + step * row_index + max(0.0, (step - 58) / 2.0)

    unique_edges = []
    seen_edges = set()
    for edge in graph_edges:
        key = (edge["source"], edge["target"], edge["class"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)
    detail_bytes = sum(
        len(str(node.get("detail") or "").encode("utf-8"))
        for node in graph_nodes
    )
    return {
        "nodes": graph_nodes,
        "edges": unique_edges,
        "width": width,
        "height": height,
        "payload_budget_m24": {
            "schema": "uruha_progressive_runtime_graph_m24",
            "node_count": len(graph_nodes),
            "edge_count": len(unique_edges),
            "rendered_detail_bytes": detail_bytes,
            "detail_budget_bytes": M24_GRAPH_DETAIL_BUDGET_BYTES,
            "largest_node_detail_bytes": max(
                (
                    len(str(node.get("detail") or "").encode("utf-8"))
                    for node in graph_nodes
                ),
                default=0,
            ),
            "per_node_budget_bytes": M24_NODE_DETAIL_BUDGET_BYTES,
            "budget_met": detail_bytes <= M24_GRAPH_DETAIL_BUDGET_BYTES,
            "full_trace_retained_in": "local_web_jsonl",
        },
    }


def _graph_node_html(node):
    label, icon, color = GRAPH_KIND_META[node["kind"]]
    if node.get("memory"):
        source_label, source_icon, source_color = SOURCE_META[node.get("source_key") or "unknown"]
        label, icon, color = source_label, source_icon, source_color
    classes = ["brain-node"]
    if node.get("selected"):
        classes.append("is-selected")
    if node.get("active"):
        classes.append("is-active")
    if node.get("write"):
        classes.append("is-write")
    trace_id = str(node.get("trace_id") or node["id"])
    metric = ""
    if node.get("salience") is not None:
        metric = f"salience {node['salience']:.2f}"
    elif node.get("score") is not None:
        metric = f"score {node['score']:.3f}"
    else:
        metric = label
    return (
        f'<details class="{" ".join(classes)}" style="--node-x:{node["x"]:.1f}px;--node-y:{node["y"]:.1f}px;--node-color:{color};">'
        f'<summary aria-label="{escape(node["label"], quote=True)}：點擊查看內容">'
        f'<span class="brain-node-icon">{escape(icon)}</span>'
        f'<span class="brain-node-label">{escape(node["label"])}</span>'
        f'<span class="brain-node-signal">{escape(node["signal"])}</span>'
        '<span class="brain-node-pulse"></span>'
        "</summary>"
        '<div class="brain-node-inspector">'
        f'<div class="brain-node-inspector-head"><span>{escape(label)}</span><span>{escape(metric)}</span></div>'
        f'<pre>{escape(node["detail"])}</pre>'
        f'<div class="brain-node-inspector-foot">trace · {escape(trace_id)}</div>'
        "</div></details>"
    )


def _graph_edges_html(graph):
    by_id = {node["id"]: node for node in graph["nodes"]}
    paths = []
    for edge in graph["edges"]:
        source = by_id.get(edge["source"])
        target = by_id.get(edge["target"])
        if not source or not target:
            continue
        x1 = source["x"] + 132
        y1 = source["y"] + 29
        x2 = target["x"]
        y2 = target["y"] + 29
        if x2 <= x1:
            control_x = max(x1, x2) + 42
            path = f"M{x1:.1f},{y1:.1f} C{control_x:.1f},{y1:.1f} {control_x:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
        else:
            middle = (x1 + x2) / 2.0
            path = f"M{x1:.1f},{y1:.1f} C{middle:.1f},{y1:.1f} {middle:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
        paths.append(f'<path class="brain-edge {escape(edge["class"], quote=True)}" d="{path}" marker-end="url(#brain-arrow)"/>')
    return "".join(paths)


def render_memory_observatory(result):
    """Render a progressive runtime graph; full evidence stays in local JSONL."""
    result = result or {}
    graph = collect_cognitive_graph(result)
    graph_budget = graph.get("payload_budget_m24") or {}
    graph_detail_bytes = int(graph_budget.get("rendered_detail_bytes") or 0)
    graph_detail_budget = int(graph_budget.get("detail_budget_bytes") or 0)
    graph_largest_detail = int(graph_budget.get("largest_node_detail_bytes") or 0)
    graph_budget_status = "met" if graph_budget.get("budget_met") else "exceeded"
    runtime_trace = result.get("runtime_trace") or {}
    latency = runtime_trace.get("runtime_latency_m19") or {}
    if not latency:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("schema") == "uruha_runtime_latency_m19":
                latency = payload
                break
    queue_seconds = _safe_float(latency.get("frontend_queue_wait_seconds"), 0.0)
    lock_seconds = _safe_float(latency.get("runtime_lock_wait_seconds"), 0.0)
    brain_seconds = _safe_float(latency.get("brain_work_seconds"), 0.0)
    surface_seconds = _safe_float(latency.get("surface_stream_seconds"), 0.0)
    surface_delivery = runtime_trace.get("surface_delivery_m20") or {}
    if not surface_delivery:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("schema") == "uruha_lightweight_surface_delivery_m20":
                surface_delivery = payload
                break
    stream_chunks = int(_safe_float(surface_delivery.get("stream_chunk_count"), 0))
    full_payload_updates = int(
        _safe_float(surface_delivery.get("full_payload_update_count"), 0)
    )
    bounded_planner = runtime_trace.get("bounded_slow_path_m21") or {}
    if not bounded_planner:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("schema") == "uruha_bounded_slow_path_planner_m21":
                bounded_planner = payload
                break
    bounded_stages = bounded_planner.get("stage_seconds") or {}
    bounded_route = str(bounded_planner.get("route") or "waiting")
    bounded_budget = _safe_float(bounded_planner.get("budget_seconds"), 0.0)
    bounded_total = _safe_float(
        bounded_stages.get("cognitive_total"),
        bounded_planner.get("planner_seconds", 0.0),
    )
    bounded_model = "used" if bounded_planner.get("model_call_attempted") else "skipped"
    semantic_route = runtime_trace.get("semantic_route_m22") or {}
    if not semantic_route:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("schema") == "uruha_semantic_route_taxonomy_m22":
                semantic_route = payload
                if payload.get("contract_status") != "pending":
                    break
    semantic_type = str(semantic_route.get("selected_type") or "waiting")
    semantic_performed = str(
        semantic_route.get("performed_route")
        or semantic_route.get("recommended_route")
        or "pending"
    )
    semantic_contract = str(semantic_route.get("contract_status") or "pending")
    semantic_confidence = _safe_float(semantic_route.get("confidence"), 0.0)
    semantic_overlaps = len(semantic_route.get("overlap_types") or [])
    semantic_negations = len(semantic_route.get("negated_types") or [])
    desired_mode = runtime_trace.get("desired_response_mode_m23") or {}
    if not desired_mode:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("schema") == "uruha_desired_response_mode_m23":
                desired_mode = payload
                if payload.get("surface_status") != "pending":
                    break
    selected_mode = str(desired_mode.get("selected_mode") or "inactive")
    mode_authority = str(desired_mode.get("authority") or "not_applicable")
    mode_uncertainty = _safe_float(desired_mode.get("uncertainty"), 0.0)
    mode_uncertainty_band = str(desired_mode.get("uncertainty_band") or "unknown")
    mode_surface_status = str(desired_mode.get("surface_status") or "not_applicable")
    mode_alternatives = len(desired_mode.get("alternatives") or [])
    explicit_m25 = runtime_trace.get("explicit_desired_response_m25") or {}
    if not explicit_m25:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema")
                == "uruha_cross_lingual_explicit_desired_response_m25"
            ):
                explicit_m25 = payload
                if payload.get("surface_status") in {"matched", "mismatch"}:
                    break
    explicit_m25_mode = str(explicit_m25.get("selected_mode") or "not_detected")
    explicit_m25_languages = "/".join(explicit_m25.get("matched_languages") or []) or "none"
    explicit_m25_negated = len(explicit_m25.get("negated_policies") or [])
    explicit_m25_surface = str(explicit_m25.get("surface_status") or "not_applicable")
    implicit_m26 = runtime_trace.get("implicit_desired_response_m26") or {}
    if not implicit_m26:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema")
                == "uruha_outcome_calibrated_implicit_response_distribution_m26"
            ):
                implicit_m26 = payload
                break
    implicit_m26_mode = str(implicit_m26.get("implicit_top_mode") or "inactive")
    implicit_m26_status = str(implicit_m26.get("status") or "not_applied")
    implicit_m26_probability = _safe_float(implicit_m26.get("top_probability"), 0.0)
    implicit_m26_margin = _safe_float(implicit_m26.get("probability_margin"), 0.0)
    implicit_m26_evidence = _safe_float(implicit_m26.get("evidence_quality"), 0.0)
    implicit_m26_outcome = str(
        (implicit_m26.get("outcome_update") or {}).get("status") or "not_available"
    )
    calibration_m27 = runtime_trace.get("causal_outcome_calibration_m27") or {}
    if not calibration_m27:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema")
                == "uruha_causal_outcome_calibration_summary_m27"
            ):
                calibration_m27 = payload
                break
    calibration_m27_status = str(
        calibration_m27.get("status") or "insufficient_evidence"
    )
    calibration_m27_n = int(
        _safe_float(
            calibration_m27.get("effective_decisive_executed_samples"), 0
        )
    )
    calibration_m27_minimum = int(
        _safe_float(calibration_m27.get("minimum_decisive_executed_samples"), 8)
    )
    calibration_m27_coverage = _safe_float(calibration_m27.get("coverage"), 0.0)
    calibration_m27_risk_value = calibration_m27.get("selective_risk")
    calibration_m27_risk = (
        "unavailable"
        if calibration_m27_risk_value is None
        else f"{_safe_float(calibration_m27_risk_value, 0.0):.2f}"
    )
    calibration_m27_unknown = int(
        _safe_float(calibration_m27.get("unknown_or_unlinked_count"), 0)
    )
    transition_m28 = runtime_trace.get("feedback_topic_transition_m28") or {}
    if not transition_m28:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema") == "uruha_feedback_topic_transition_m28"
            ):
                transition_m28 = payload
                break
    transition_m28_status = str(transition_m28.get("status") or "not_applied")
    transition_m28_act = str(
        transition_m28.get("current_turn_act") or "ordinary_current_content"
    )
    transition_m28_topic = str(transition_m28.get("topic_kind") or "ordinary")
    transition_m28_surface = str(
        transition_m28.get("surface_status") or "not_applicable"
    )
    projection_m29 = runtime_trace.get("literal_topic_projection_m29") or {}
    if not projection_m29:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema")
                == "uruha_generalized_literal_topic_projection_m29"
            ):
                projection_m29 = payload
                break
    projection_m29_status = str(projection_m29.get("status") or "not_applied")
    projection_m29_subject = str(projection_m29.get("subject_jp") or "unavailable")
    projection_m29_predicate = str(projection_m29.get("predicate_jp") or "unavailable")
    projection_m29_polarity = str(projection_m29.get("polarity") or "unknown")
    projection_m29_anchors = int(
        _safe_float(projection_m29.get("visible_anchor_count"), 0)
    )
    projection_m29_surface = str(
        projection_m29.get("surface_status") or "not_applicable"
    )
    authorization_m31 = runtime_trace.get("semantic_authorization_m31") or {}
    if not authorization_m31:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema") == "uruha_semantic_authorization_m31"
            ):
                authorization_m31 = payload
                break
    authorization_m31_status = str(
        authorization_m31.get("status") or "not_applied"
    )
    authorization_m31_polarity = str(
        authorization_m31.get("source_polarity") or "unknown"
    )
    authorization_m31_surface = str(
        authorization_m31.get("surface_status") or "not_applicable"
    )
    authorization_m31_confidence = _safe_float(
        authorization_m31.get("confidence"), 0.0
    )
    authorization_m31_errors = len(authorization_m31.get("error_tags") or [])
    semantic_commit_m32 = runtime_trace.get("semantic_commit_repair_m32") or {}
    if not semantic_commit_m32:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema")
                == "uruha_deterministic_semantic_commit_m32"
            ):
                semantic_commit_m32 = payload
                break
    semantic_commit_m32_status = str(
        semantic_commit_m32.get("status") or "not_applied"
    )
    semantic_commit_m32_kind = str(
        semantic_commit_m32.get("repair_kind") or "none"
    )
    semantic_commit_m32_surface = str(
        semantic_commit_m32.get("surface_status") or "not_applicable"
    )
    semantic_commit_m32_authority = bool(
        semantic_commit_m32.get("surface_authority")
    )
    semantic_commit_m32_anchors = int(
        _safe_float(semantic_commit_m32.get("visible_anchor_count"), 0)
    )
    semantic_commit_m32_failures = len(
        semantic_commit_m32.get("rejection_checks_m31") or []
    )
    source_atoms_m33 = runtime_trace.get("source_semantic_atoms_m33") or {}
    atom_verification_m33 = runtime_trace.get("semantic_atom_verification_m33") or {}
    source_commit_m33 = runtime_trace.get(
        "source_anchored_semantic_commit_m33"
    ) or {}
    if not source_commit_m33:
        for row in reversed(runtime_trace.get("blackboard") or []):
            payload = row.get("payload") or {}
            if (
                isinstance(payload, dict)
                and payload.get("schema")
                == "uruha_source_anchored_semantic_commit_m33"
            ):
                source_commit_m33 = payload
                break
    source_atoms_m33_status = str(
        source_atoms_m33.get("status") or "not_applied"
    )
    source_atoms_m33_family = str(source_atoms_m33.get("family") or "none")
    source_atoms_m33_count = int(
        _safe_float(source_atoms_m33.get("atom_count"), 0)
    )
    atom_verification_m33_status = str(
        atom_verification_m33.get("status") or "not_applied"
    )
    atom_verification_m33_conflicts = int(
        _safe_float(atom_verification_m33.get("conflict_atom_count"), 0)
    )
    source_commit_m33_status = str(
        source_commit_m33.get("status") or "not_applied"
    )
    source_commit_m33_kind = str(
        source_commit_m33.get("repair_kind") or "none"
    )
    source_commit_m33_surface = str(
        source_commit_m33.get("surface_status") or "not_applicable"
    )
    source_commit_m33_coverage = _safe_float(
        source_commit_m33.get("source_atom_trace_coverage"), 0.0
    )
    pragmatic_branch_m34 = runtime_trace.get(
        "counterfactual_pragmatic_branch_m34"
    ) or {}
    selected_branch_m34 = pragmatic_branch_m34.get("selected_branch") or {}
    alternative_branch_m34 = pragmatic_branch_m34.get("bounded_alternative") or {}
    branch_verification_m34 = pragmatic_branch_m34.get(
        "previous_branch_verification"
    ) or {}
    branch_revision_m34 = pragmatic_branch_m34.get("revision") or {}
    branch_m34_policy = str(selected_branch_m34.get("policy_id") or "none")
    branch_m34_mode = str(selected_branch_m34.get("mode") or "none")
    branch_m34_authority = str(
        selected_branch_m34.get("authority_basis") or "not_applicable"
    )
    branch_m34_alternative = str(
        alternative_branch_m34.get("policy_id") or "none"
    )
    branch_m34_previous = str(
        branch_verification_m34.get("status") or "not_available"
    )
    branch_m34_revision = str(
        branch_revision_m34.get("status") or "no_revision"
    )
    branch_m34_revision_transition = (
        f'{branch_revision_m34.get("revoked_policy_id") or "none"}'
        f'→{branch_revision_m34.get("replacement_policy_id") or "none"}'
    )
    compositional_m36 = runtime_trace.get(
        "compositional_pragmatic_cue_m36"
    ) or {}
    compositional_m36_status = str(
        compositional_m36.get("status") or "not_applied"
    )
    compositional_m36_cues = int(
        _safe_float(compositional_m36.get("compositional_match_count"), 0)
    )
    compositional_m36_arousal = bool(
        compositional_m36.get("compositional_arousal_detected")
    )
    compositional_m36_replacement = bool(
        compositional_m36.get("valid_explicit_replacement")
    )
    compositional_m36_linked = bool(
        compositional_m36.get("feedback_linked_to_previous_prediction")
    )
    pragmatic_trigger_relation_m37 = runtime_trace.get(
        "pragmatic_trigger_relation_m37"
    ) or {}
    trigger_relation_m37_status = str(
        pragmatic_trigger_relation_m37.get("status") or "not_applied"
    )
    trigger_relation_m37_predicate = str(
        pragmatic_trigger_relation_m37.get("trigger_predicate") or "none"
    )
    trigger_relation_m37_policy = str(
        pragmatic_trigger_relation_m37.get("selected_policy") or "none"
    )
    trigger_relation_m37_count = int(
        _safe_float(
            pragmatic_trigger_relation_m37.get("persisted_relation_count"),
            0,
        )
    )
    trigger_relation_m37_authoritative = bool(
        pragmatic_trigger_relation_m37.get("authoritative")
    )
    compositional_result_m36 = _load_m36_compositional_summary()
    if compositional_result_m36.get("available"):
        compositional_result_m36_passed = (
            compositional_result_m36.get("decision") == "pass_all_frozen_gates"
        )
        compositional_result_m36_html = (
            f'<div class="fidelity-strip {"is-pass" if compositional_result_m36_passed else ""}" aria-label="M36 多語組合語用封存對照">'
            '<div class="fidelity-strip-head">'
            '<div class="fidelity-strip-title">M36 · COMPOSITIONAL MULTILINGUAL PRAGMATIC COMPARISON</div>'
            f'<div class="fidelity-strip-decision">FROZEN GATE · {"PASS" if compositional_result_m36_passed else "FAIL"}</div></div>'
            '<div class="fidelity-grid">'
            f'<div class="fidelity-metric"><b>{compositional_result_m36["baseline_accuracy"]:.0%}</b><span>只看當輪 baseline</span></div>'
            f'<div class="fidelity-metric"><b>{compositional_result_m36["system_accuracy"]:.0%}</b><span>跨輪語用系統</span></div>'
            f'<div class="fidelity-metric"><b>+{compositional_result_m36["accuracy_delta"]*100:.2f}pp</b><span>同模型 · 同 prompt token</span></div>'
            f'<div class="fidelity-metric"><b>{compositional_result_m36["feedback_policy_accuracy"]:.0%}</b><span>{compositional_result_m36["feedback_scored_count"]} 個有效否定標註的替換策略</span></div>'
            '</div>'
            f'<div class="fidelity-note">12/12 annotation integrity · errors {compositional_result_m36["annotation_error_count"]}；mechanism current {compositional_result_m36["mechanism_accuracy"]:.0%} · next-turn outcome {compositional_result_m36["outcome_accuracy"]:.0%} · pair divergence {compositional_result_m36["system_pair_divergence"]:.0%} · full revision {compositional_result_m36["revision_accuracy"]:.0%}；current／feedback surface proxy {compositional_result_m36["current_surface"]:.0%}／{compositional_result_m36["feedback_surface"]:.0%}；prompt ratio {compositional_result_m36["prompt_ratio"]:.3f} · latency {compositional_result_m36["latency_ratio"]:.3f}；failed gates {compositional_result_m36["failed_gate_count"]}。這是受控 proxy，human felt-understanding evidence {"available" if compositional_result_m36["human_evidence"] else "not available"}，紅色 FAIL 不因 +66.66pp 而隱藏。</div>'
            '</div>'
        )
    else:
        compositional_result_m36_html = (
            '<div class="fidelity-strip" aria-label="M36 多語組合語用封存對照">'
            '<div class="fidelity-strip-title">M36 · SEALED RESULT UNAVAILABLE</div>'
            '</div>'
        )
    same_model_result_m35 = _load_m35_same_model_summary()
    if same_model_result_m35.get("available"):
        same_model_result_m35_passed = (
            same_model_result_m35.get("decision") == "pass_all_frozen_gates"
        )
        same_model_result_m35_html = (
            f'<div class="fidelity-strip {"is-pass" if same_model_result_m35_passed else ""}" aria-label="M35 同模型跨輪語用對照">'
            '<div class="fidelity-strip-head">'
            '<div class="fidelity-strip-title">M35 · SAME-MODEL LONGITUDINAL PRAGMATIC COMPARISON</div>'
            f'<div class="fidelity-strip-decision">FROZEN GATE · {"PASS" if same_model_result_m35_passed else "FAIL"}</div></div>'
            '<div class="fidelity-grid">'
            f'<div class="fidelity-metric"><b>{same_model_result_m35["baseline_accuracy"]:.0%}</b><span>current-turn-only baseline</span></div>'
            f'<div class="fidelity-metric"><b>{same_model_result_m35["system_accuracy"]:.0%}</b><span>M34 longitudinal system</span></div>'
            f'<div class="fidelity-metric"><b>+{same_model_result_m35["accuracy_delta"]*100:.0f}pp</b><span>當輪 branch 差距</span></div>'
            f'<div class="fidelity-metric"><b>{same_model_result_m35["system_pair_divergence"]:.0%}</b><span>同句 pair 正確分流</span></div>'
            '</div>'
            f'<div class="fidelity-note">同一 qwen3.5:9b；baseline pair invariance {same_model_result_m35["baseline_pair_invariance"]:.0%}；M34 mechanism {same_model_result_m35["mechanism_accuracy"]:.0%}；system surface proxy {same_model_result_m35["system_surface"]:.0%}；prompt token ratio {same_model_result_m35["prompt_ratio"]:.3f} · completion {same_model_result_m35["completion_ratio"]:.3f} · latency {same_model_result_m35["latency_ratio"]:.3f}；failed gates {same_model_result_m35["failed_gate_count"]}。正式 feedback 指標另因 2 個 frozen target 標註錯誤而不得作主張；+50pp 只是不含人評的當輪 controlled proxy。</div>'
            '</div>'
        )
    else:
        same_model_result_m35_html = (
            '<div class="fidelity-strip" aria-label="M35 同模型跨輪語用對照">'
            '<div class="fidelity-strip-title">M35 · SEALED RESULT UNAVAILABLE</div>'
            '</div>'
        )
    pragmatic_result_m34 = _load_m34_pragmatic_branch_summary()
    if pragmatic_result_m34.get("available"):
        pragmatic_result_m34_passed = (
            pragmatic_result_m34.get("decision") == "pass_all_frozen_gates"
        )
        pragmatic_result_m34_html = (
            f'<div class="fidelity-strip {"is-pass" if pragmatic_result_m34_passed else ""}" aria-label="M34 反事實語用分支封存評測">'
            '<div class="fidelity-strip-head">'
            '<div class="fidelity-strip-title">M34 · COUNTERFACTUAL PRAGMATIC BRANCH SEALED RESERVE</div>'
            f'<div class="fidelity-strip-decision">FROZEN GATE · {"PASS" if pragmatic_result_m34_passed else "FAIL"}</div></div>'
            '<div class="fidelity-grid">'
            f'<div class="fidelity-metric"><b>{pragmatic_result_m34["case_count"]}/{pragmatic_result_m34["case_count"]}</b><span>分支選擇 · {pragmatic_result_m34["policy_accuracy"]:.0%}</span></div>'
            f'<div class="fidelity-metric"><b>{pragmatic_result_m34["pair_count"]}/{pragmatic_result_m34["pair_count"]}</b><span>同句反事實分流 · {pragmatic_result_m34["pair_divergence"]:.0%}</span></div>'
            f'<div class="fidelity-metric"><b>{pragmatic_result_m34["outcome_accuracy"]:.0%}</b><span>下一輪驗證</span></div>'
            f'<div class="fidelity-metric"><b>{pragmatic_result_m34["revision_accuracy"]:.0%}</b><span>否定後換分支</span></div>'
            '</div>'
            f'<div class="fidelity-note">evidence trace {pragmatic_result_m34["trace_coverage"]:.0%} · observable prediction {pragmatic_result_m34["prediction_coverage"]:.0%} · visible Japanese {pragmatic_result_m34["visible_japanese"]:.0%} · unverified mental-fact writes {pragmatic_result_m34["unsafe_fact_writes"]} · median {pragmatic_result_m34["median_seconds"]:.3f}s · p95 {pragmatic_result_m34["p95_seconds"]:.3f}s。只證明受控情境敏感、可追溯預測與修正，不代表私密意圖真值、人類偏好或同模型優勢。</div>'
            '</div>'
        )
    else:
        pragmatic_result_m34_html = (
            '<div class="fidelity-strip" aria-label="M34 反事實語用分支封存評測">'
            '<div class="fidelity-strip-title">M34 · SEALED RESULT UNAVAILABLE</div>'
            '</div>'
        )
    fidelity_m33 = _load_m33_source_atom_summary()
    if fidelity_m33.get("available"):
        language_rates_m33 = fidelity_m33["language_rates"]
        fidelity_m33_html = (
            '<div class="fidelity-strip is-pass" aria-label="M33 來源語意原子封存評測">'
            '<div class="fidelity-strip-head">'
            '<div class="fidelity-strip-title">M33 · SOURCE-ANCHORED SEMANTIC ATOM SEALED RESERVE</div>'
            '<div class="fidelity-strip-decision">FROZEN GATE · PASS</div></div>'
            '<div class="fidelity-grid">'
            f'<div class="fidelity-metric"><b>{fidelity_m33["faithful"]}/{fidelity_m33["valid"]}</b><span>忠實接管 · {fidelity_m33["faithful_rate"]:.0%}</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m33["false_authority"]}</b><span>錯誤接管</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m33["false_reject"]}</b><span>錯誤拒絕</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m33["true_abstention"]}/{fidelity_m33["incomplete"]}</b><span>不完整句安全拒絕</span></div>'
            '</div>'
            f'<div class="fidelity-note">zh {language_rates_m33["zh"]:.0%} · en {language_rates_m33["en"]:.0%} · ja {language_rates_m33["ja"]:.0%}；fresh {fidelity_m33["fresh_rate"]:.0%}；direct Japanese {fidelity_m33["direct_japanese_rate"]:.0%}；change {fidelity_m33["change_rate"]:.0%}；negated／limited quantity {fidelity_m33["quantity_rate"]:.0%}；atom trace {fidelity_m33["atom_coverage"]:.0%}；source conflict repairs {fidelity_m33["conflict_repairs"]}；median {fidelity_m33["median_seconds"]:.2f}s · p95 {fidelity_m33["p95_seconds"]:.2f}s。只證明 5 類 bounded construction 的來源約束，不代表 open-domain semantics 或人類理解。</div>'
            '</div>'
        )
    else:
        fidelity_m33_html = (
            '<div class="fidelity-strip" aria-label="M33 來源語意原子封存評測">'
            '<div class="fidelity-strip-title">M33 · SEALED RESULT UNAVAILABLE</div>'
            '</div>'
        )
    fidelity_m32 = _load_m32_commit_summary()
    if fidelity_m32.get("available"):
        language_rates_m32 = fidelity_m32["language_rates"]
        fidelity_m32_html = (
            '<div class="fidelity-strip" aria-label="M32 語意提交與新對話路由密封評測">'
            '<div class="fidelity-strip-head">'
            '<div class="fidelity-strip-title">M32 · SEMANTIC COMMIT &amp; FRESH ROUTING SEALED RESERVE</div>'
            '<div class="fidelity-strip-decision">FROZEN GATE · FAIL</div></div>'
            '<div class="fidelity-grid">'
            f'<div class="fidelity-metric"><b>{fidelity_m32["faithful"]}/{fidelity_m32["valid"]}</b><span>忠實接管 · {fidelity_m32["faithful_rate"]:.0%}</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m32["false_authority"]}</b><span>錯誤接管 · semantic atom loss</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m32["false_reject"]}</b><span>錯誤拒絕 · answerable but blocked</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m32["true_abstention"]}/{fidelity_m32["incomplete"]}</b><span>不完整句正確拒絕</span></div>'
            '</div>'
            f'<div class="fidelity-note">zh {language_rates_m32["zh"]:.0%} · en {language_rates_m32["en"]:.0%} · ja {language_rates_m32["ja"]:.0%}；fresh session {fidelity_m32["fresh_rate"]:.0%}；ordinary negation {fidelity_m32["ordinary_negation_rate"]:.0%}；polarity {fidelity_m32["negation_accuracy"]:.0%}；median {fidelity_m32["median_seconds"]:.2f}s · p95 {fidelity_m32["p95_seconds"]:.2f}s。M32 修復了表面提交與路由，但來源→canonical semantics 仍會丟失時間、物件或 change operator；下一步 M33 使用 source-anchored semantic atom ledger。</div>'
            '</div>'
        )
    else:
        fidelity_m32_html = (
            '<div class="fidelity-strip" aria-label="M32 語意提交密封評測">'
            '<div class="fidelity-strip-title">M32 · SEALED RESULT UNAVAILABLE</div>'
            '</div>'
        )
    fidelity_m30 = _load_m30_fidelity_summary()
    if fidelity_m30.get("available"):
        language_rates = fidelity_m30["language_rates"]
        fidelity_html = (
            '<div class="fidelity-strip" aria-label="M30 跨語語義忠實度凍結評測">'
            '<div class="fidelity-strip-head">'
            '<div class="fidelity-strip-title">M30 · CROSS-LINGUAL SEMANTIC FIDELITY HOLDOUT</div>'
            '<div class="fidelity-strip-decision">FROZEN GATE · FAIL</div></div>'
            '<div class="fidelity-grid">'
            f'<div class="fidelity-metric"><b>{fidelity_m30["faithful"]}/{fidelity_m30["valid"]}</b><span>忠實接管 · {fidelity_m30["faithful_rate"]:.0%}</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m30["false_authority"]}</b><span>錯誤接管 · fluent but wrong</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m30["false_reject"]}</b><span>錯誤拒絕 · answerable but blocked</span></div>'
            f'<div class="fidelity-metric"><b>{fidelity_m30["true_abstention"]}/{fidelity_m30["incomplete"]}</b><span>不完整句正確拒絕</span></div>'
            '</div>'
            f'<div class="fidelity-note">zh {language_rates["zh"]:.0%} · en {language_rates["en"]:.0%} · ja {language_rates["ja"]:.0%}；否定 polarity {fidelity_m30["negation_accuracy"]:.0%}；median {fidelity_m30["median_seconds"]:.2f}s。M29 可展示但尚不可稱 reliable generalized semantics；M30 結果凍結，修正需用新 reserve 確認。</div>'
            '</div>'
        )
    else:
        fidelity_html = (
            '<div class="fidelity-strip" aria-label="M30 跨語語義忠實度凍結評測">'
            '<div class="fidelity-strip-title">M30 · FIDELITY RESULT UNAVAILABLE</div>'
            '</div>'
        )
    timing_flow = (
        f"前端等待 {queue_seconds:.3f}s → 大腦鎖等待 {lock_seconds:.3f}s → "
        f"腦內運算 {brain_seconds:.3f}s → 畫面輸出 {surface_seconds:.3f}s"
    )
    lanes = "".join(
        (
            f'<div class="brain-stage-lane" style="left:{index * 170}px">'
            f'<div class="brain-stage-lane-label"><b>{escape(icon)}</b>{escape(label)}</div>'
            "</div>"
        )
        for index, (_key, label, icon, _color) in enumerate(GRAPH_LANES)
    )
    nodes_html = "".join(_graph_node_html(node) for node in graph["nodes"])
    empty_html = "" if result else '<div class="brain-graph-empty">送出訊息後，節點與流向會在這裡亮起。</div>'
    return (
        '<section class="memory-observatory" aria-label="認知與記憶節點圖">'
        '<div class="memory-observatory-head">'
        '<div><div class="memory-eyebrow">Progressive Runtime Node Graph · M24</div>'
        '<div class="memory-title">內部流程與內容變化</div>'
        '<div class="memory-subtitle">節點是實際 runtime 事件；連線是資料流。畫面先顯示可追溯摘要，點節點看受限預覽；完整證據保留於本機 trace。</div></div>'
        '<div class="memory-live"><span class="memory-live-dot"></span>LOCAL TRACE · LIVE</div>'
        "</div>"
        '<div class="brain-comparison" aria-label="直接生成與 UruhaBrain M34 counterfactual pragmatic branch 差異">'
        '<div class="brain-comparison-card"><div class="brain-comparison-label">DIRECT GENERATION PATH / UNBOUNDED GENERAL PLANNER · RETAINED M19 FAILURE</div>'
        '<div class="brain-comparison-flow">當輪輸入 → 當輪回答；簡單訊息 → 通用模型規劃 → 等待全部完成 → 才能顯示回覆</div>'
        '<div class="brain-comparison-note">M19 保留的真實反例是腦內運算 57.404 秒；排隊已修好，但慢路徑本身仍讓真人等待。</div></div>'
        '<div class="brain-comparison-card is-uruha"><div class="brain-comparison-label">PRAGMATIC TRIGGER-RELATION NORMALIZATION · M37 / COMPOSITIONAL MULTILINGUAL PRAGMATIC CUES · M36 / COUNTERFACTUAL PRAGMATIC BRANCH LEDGER · M34 / SOURCE-ANCHORED SEMANTIC ATOM LEDGER · M33 / COMPLETE SEMANTIC COMMIT · M32 / SOURCE-FIRST SEMANTIC AUTHORIZATION · M31 / GENERALIZED LITERAL-TOPIC GROUNDING &amp; TRANSLATION · M29</div>'
        '<div class="brain-comparison-lineage">FEEDBACK ACKNOWLEDGEMENT &amp; TOPIC-SHIFT CONTINUITY · M28 / CAUSAL OUTCOME CALIBRATION LEDGER · M27 / OUTCOME-CALIBRATED IMPLICIT DESIRED RESPONSE · M26 / CROSS-LINGUAL EXPLICIT DESIRED RESPONSE · M25 / PROGRESSIVE RUNTIME NODE GRAPH · M24 / DESIRED RESPONSE MODE · M23 / TYPED SEMANTIC ROUTER · M22 / BOUNDED SLOW-PATH PLANNER · M21 / CORRECTION-AWARE SURFACE COMMIT · M20 / HUMAN-PRIORITY COGNITIVE SCHEDULER · M19 / HIERARCHICAL ADAPTIVE MODEL · M18</div>'
        '<div class="brain-comparison-lineage">保留的因果契約：M18 以 scope gate 做負遷移檢查；M20 在反駁後撤銷舊假設；回覆先用輕量串流 3 段，再交付完整 cognition/graph payload 1 次。</div>'
        '<div class="brain-comparison-flow">observable trigger + requested response separated → next-turn verification → typed raw-free relation → morphology／bounded-paraphrase match → branch selection → natural Japanese surface</div>'
        f'<div class="brain-comparison-note">M37 {escape(trigger_relation_m37_status)} · {escape(trigger_relation_m37_predicate)} → {escape(trigger_relation_m37_policy)} · verified relations {trigger_relation_m37_count} · authority {str(trigger_relation_m37_authoritative).lower()}；M36 {escape(compositional_m36_status)} · composed cues {compositional_m36_cues} · arousal {str(compositional_m36_arousal).lower()} · valid replacement {str(compositional_m36_replacement).lower()} · linked {str(compositional_m36_linked).lower()}；M34 selected {escape(branch_m34_policy)}／{escape(branch_m34_mode)} · authority {escape(branch_m34_authority)} · alternative {escape(branch_m34_alternative)} · previous outcome {escape(branch_m34_previous)} · revision {escape(branch_m34_revision)} {escape(branch_m34_revision_transition)} · surface {escape(str(pragmatic_branch_m34.get("surface_status") or "not_applicable"))}；M33 source {escape(source_atoms_m33_status)} · family {escape(source_atoms_m33_family)} · atoms {source_atoms_m33_count} → verification {escape(atom_verification_m33_status)} · conflicts {atom_verification_m33_conflicts} → commit {escape(source_commit_m33_status)} · kind {escape(source_commit_m33_kind)} · trace coverage {source_commit_m33_coverage:.0%} · surface {escape(source_commit_m33_surface)}；M32 {escape(semantic_commit_m32_status)} · authority {str(semantic_commit_m32_authority).lower()} · kind {escape(semantic_commit_m32_kind)} · inherited failed checks {semantic_commit_m32_failures} · visible anchors {semantic_commit_m32_anchors} · surface {escape(semantic_commit_m32_surface)}；M31 {escape(authorization_m31_status)} · polarity {escape(authorization_m31_polarity)} · confidence {authorization_m31_confidence:.2f} · errors {authorization_m31_errors} · surface {escape(authorization_m31_surface)}；M29 candidate gate {escape(projection_m29_status)} · subject {escape(projection_m29_subject)} · predicate {escape(projection_m29_predicate)} · polarity {escape(projection_m29_polarity)} · visible anchors {projection_m29_anchors} · surface {escape(projection_m29_surface)}；M28 {escape(transition_m28_status)} · act {escape(transition_m28_act)} · topic {escape(transition_m28_topic)} · surface {escape(transition_m28_surface)} · M27 outcome preserved；M27 ledger {escape(calibration_m27_status)} · effective n {calibration_m27_n}/{calibration_m27_minimum} · coverage {calibration_m27_coverage:.2f} · selective risk {escape(calibration_m27_risk)} · unknown/unlinked excluded {calibration_m27_unknown} · automatic tuning false；M26 implicit {escape(implicit_m26_mode)} · p {implicit_m26_probability:.2f} · margin {implicit_m26_margin:.2f} · evidence {implicit_m26_evidence:.2f} · gate {escape(implicit_m26_status)} · previous outcome {escape(implicit_m26_outcome)}（操作性信念，尚非外部人評校準機率）；M25 explicit {escape(explicit_m25_mode)} · languages {escape(explicit_m25_languages)} · negated {explicit_m25_negated} · surface {escape(explicit_m25_surface)}；M23 mode {escape(selected_mode)} · authority {escape(mode_authority)} · uncertainty {mode_uncertainty:.2f} ({escape(mode_uncertainty_band)}) · alternatives {mode_alternatives} · surface {escape(mode_surface_status)}；type {escape(semantic_type)} → {escape(semantic_performed)} · contract {escape(semantic_contract)} · confidence {semantic_confidence:.2f} · overlaps {semantic_overlaps} · negations {semantic_negations}；persona dimensions 關心・直接・幽默・傾聽・行動・距離；route {escape(bounded_route)} · cognition {bounded_total:.3f}s / budget {bounded_budget:.1f}s · general model {bounded_model}。{escape(timing_flow)}；PROGRESSIVE GRAPH · M24 為 {len(graph["nodes"])} 節點保留因果路徑，瀏覽器 detail {graph_detail_bytes:,}/{graph_detail_budget:,} bytes（largest {graph_largest_detail:,} · {graph_budget_status}），完整 trace 留在 local JSONL。</div></div></div>'
        f'{compositional_result_m36_html}'
        f'{same_model_result_m35_html}'
        f'{pragmatic_result_m34_html}'
        f'{fidelity_m33_html}'
        f'{fidelity_m32_html}'
        f'{fidelity_html}'
        '<div class="brain-graph-shell">'
        '<div class="brain-graph-toolbar"><strong>M37 · Trigger → verified response relation → paraphrase match → branch → Japanese surface</strong>'
        '<div class="brain-graph-legend">'
        '<span><i style="--legend-color:#64748b"></i>候選</span>'
        '<span><i style="--legend-color:#facc15"></i>工作記憶</span>'
        '<span><i style="--legend-color:#34d399"></i>實際傳入</span>'
        '<span><i style="--legend-color:#f472b6"></i>寫回</span>'
        "</div></div>"
        '<div class="brain-graph-scroll">'
        f'<div class="brain-graph-canvas" style="width:{graph["width"]}px;height:{graph["height"]}px">'
        f"{lanes}"
        f'<svg class="brain-edge-layer" viewBox="0 0 {graph["width"]} {graph["height"]}" aria-hidden="true">'
        '<defs><marker id="brain-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker></defs>'
        f'{_graph_edges_html(graph)}</svg>{nodes_html}{empty_html}'
        "</div></div></div></section>"
    )
