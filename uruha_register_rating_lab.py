"""Graphical blind-rating surface for the frozen M10.2 packet.

This module deliberately imports the blind packet only.  The condition key is
not loaded by, linked from, or rendered in the human collection surface.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from m10_3_register_human_eval import (
    DIMENSIONS,
    PACKET_SHA256,
    PREFERENCES,
    RUBRIC,
    pseudonymize_rater_id,
)


ROOT = Path(__file__).resolve().parent
PACKET_PATH = ROOT / "analysis/m10_2_behavior_preserving_register_blind_packet.json"
RATINGS_DIR = ROOT / "analysis/m10_3_register_ratings"
_WRITE_LOCK = threading.Lock()


RATING_LAB_CSS = """
.rating-shell{background:radial-gradient(circle at 12% 10%,#17263a 0,#070c16 46%,#05070d 100%);color:#eef6ff;border:1px solid #29364b;border-radius:22px;padding:24px;box-shadow:0 18px 55px rgba(0,0,0,.32)}
.rating-kicker{color:#58d5ff!important;font-size:11px;font-weight:800;letter-spacing:.16em}.rating-title{color:#f7fbff!important;font-size:31px;font-weight:850;line-height:1.17;margin:8px 0}.rating-boundary{color:#a9b7ca!important;font-size:13px;line-height:1.55}.rating-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:18px 0}.rating-candidate{background:#0b1321;border:1px solid #33445c;border-radius:16px;padding:18px;min-height:112px}.rating-candidate.a{border-top:3px solid #59c7ff}.rating-candidate.b{border-top:3px solid #ffcc66}.rating-letter{font-size:11px;font-weight:800;letter-spacing:.15em;color:#8da3bf!important}.rating-text{font-size:20px;font-weight:700;line-height:1.5;margin-top:9px;color:#fff!important}.rating-context{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:16px}.rating-context-card{background:#09101c;border:1px solid #26344a;border-radius:14px;padding:14px}.rating-context-card span{display:block;color:#7790ad!important;font-size:10px;letter-spacing:.12em;margin-bottom:6px}.rating-context-card b{color:#edf5ff!important;font-size:14px;line-height:1.5}.rating-rubric{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:16px}.rating-rubric div{border:1px solid #243349;border-radius:12px;padding:10px;background:#080f1a;color:#aebed1!important;font-size:11px;line-height:1.45}.rating-rubric strong{display:block;color:#f2f7ff!important;margin-bottom:4px}.rating-progress{border:1px solid #2a3850;border-radius:14px;padding:14px;background:#09111e}.rating-progress b{color:#edf5ff!important}.rating-progress-track{height:8px;background:#192437;border-radius:99px;overflow:hidden;margin:9px 0}.rating-progress-fill{height:100%;background:linear-gradient(90deg,#52d5ff,#74efb5)}.rating-warning{color:#ffcf72!important}.rating-ok{color:#72efb5!important}@media(max-width:900px){.rating-grid,.rating-context,.rating-rubric{grid-template-columns:1fr}}
"""


def _packet():
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def _items():
    return _packet().get("items") or []


def blind_item_choices():
    return [item["item_id"] for item in _items()]


DEFAULT_BLIND_ITEM_ID = blind_item_choices()[0]


def _item(item_id):
    for row in _items():
        if row["item_id"] == item_id:
            return row
    raise ValueError(f"unknown blind item: {item_id}")


def render_blind_rating_item(item_id):
    item = _item(item_id)
    rubric_html = "".join(
        f"<div><strong>{escape(dimension)}</strong>{escape(RUBRIC[dimension])}</div>"
        for dimension in DIMENSIONS
    )
    return f"""
    <section class="rating-shell">
      <div class="rating-kicker">M10.3 · BLINDED HUMAN RATING · {escape(item['item_id'])}</div>
      <div class="rating-title">只看 A／B，判斷自然度改善有沒有改壞原本行為</div>
      <div class="rating-boundary">候選來源與自動分類結果在評分期間完全隱藏。這裡收集的是人類判斷，不是系統自評；未滿三位完整獨立評分者前，狀態永遠是 pending。</div>
      <div class="rating-context">
        <div class="rating-context-card"><span>EVENT CONTEXT</span><b>{escape(item['event_context'])}</b></div>
        <div class="rating-context-card"><span>AUTHORIZED OBSERVABLE BEHAVIOR</span><b>{escape(item['authoritative_behavior'])}</b></div>
      </div>
      <div class="rating-grid">
        <div class="rating-candidate a"><div class="rating-letter">CANDIDATE A</div><div class="rating-text">{escape(item['candidates']['A'])}</div></div>
        <div class="rating-candidate b"><div class="rating-letter">CANDIDATE B</div><div class="rating-text">{escape(item['candidates']['B'])}</div></div>
      </div>
      <div class="rating-rubric">{rubric_html}</div>
    </section>
    """


def _rating_path(rater_hash):
    return RATINGS_DIR / f"ratings-{rater_hash[:20]}.jsonl"


def _audit_path(rater_hash):
    return RATINGS_DIR / f"{rater_hash[:20]}.audit.ndjson"


def _read_current_rows(rater_hash):
    path = _rating_path(rater_hash)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def collection_status():
    item_ids = set(blind_item_choices())
    complete = 0
    partial = 0
    if RATINGS_DIR.exists():
        for path in sorted(RATINGS_DIR.glob("ratings-*.jsonl")):
            try:
                rows = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except (OSError, json.JSONDecodeError):
                continue
            rated = {row.get("item_id") for row in rows}
            if rated == item_ids:
                complete += 1
            elif rated:
                partial += 1
    return {
        "complete_raters": complete,
        "partial_raters": partial,
        "formal_minimum": 3,
        "formal_minimum_met": complete >= 3,
    }


def render_rater_progress(raw_rater_id=""):
    try:
        rater_hash = pseudonymize_rater_id(raw_rater_id)
        rows = _read_current_rows(rater_hash)
        completed = len({row.get("item_id") for row in rows})
        rater_text = f"這位評分者：{completed}/18"
    except ValueError:
        completed = 0
        rater_text = "輸入至少 4 字元的匿名代號後開始"
    status = collection_status()
    width = min(100.0, completed / 18 * 100.0)
    global_class = "rating-ok" if status["formal_minimum_met"] else "rating-warning"
    return f"""
    <div class="rating-progress">
      <b>{escape(rater_text)}</b>
      <div class="rating-progress-track"><div class="rating-progress-fill" style="width:{width:.1f}%"></div></div>
      <span class="{global_class}">目前完整獨立評分者：{status['complete_raters']}/3；partial：{status['partial_raters']}。未滿門檻，不產生人類偏好結論。</span>
    </div>
    """


def save_blind_rating(
    raw_rater_id,
    item_id,
    semantic_a,
    semantic_b,
    behavior_a,
    behavior_b,
    natural_a,
    natural_b,
    boundary_a,
    boundary_b,
    preference,
    independent_attestation,
    key_unseen_attestation,
    notes,
):
    try:
        rater_hash = pseudonymize_rater_id(raw_rater_id)
        _item(item_id)
        if independent_attestation is not True or key_unseen_attestation is not True:
            raise ValueError("請確認你是獨立真人評分者，且未看過 A/B 答案 key")
        values = (
            semantic_a,
            semantic_b,
            behavior_a,
            behavior_b,
            natural_a,
            natural_b,
            boundary_a,
            boundary_b,
        )
        if any(not isinstance(value, (int, float)) or int(value) not in range(1, 6) for value in values):
            raise ValueError("A/B 四個維度都必須填 1–5")
        if preference not in PREFERENCES:
            raise ValueError("請選 A、B、tie 或 both_bad")
        record = {
            "schema": "m10_3_register_rating_v1",
            "rater_id_hash": rater_hash,
            "independent_human_attestation": True,
            "key_unseen_attestation": True,
            "packet_sha256": PACKET_SHA256,
            "item_id": item_id,
            "scores": {
                "semantic_preservation": {"A": int(semantic_a), "B": int(semantic_b)},
                "behavior_fit": {"A": int(behavior_a), "B": int(behavior_b)},
                "natural_casual_japanese": {"A": int(natural_a), "B": int(natural_b)},
                "non_overclaiming": {"A": int(boundary_a), "B": int(boundary_b)},
            },
            "preference": preference,
            "notes": str(notes or "")[:1000],
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        RATINGS_DIR.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK:
            current = {
                row["item_id"]: row
                for row in _read_current_rows(rater_hash)
                if row.get("rater_id_hash") == rater_hash
            }
            current[item_id] = record
            path = _rating_path(rater_hash)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(RATINGS_DIR),
                prefix="m10-3-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                for key in blind_item_choices():
                    if key in current:
                        handle.write(json.dumps(current[key], ensure_ascii=False) + "\n")
            os.replace(temp_name, path)
            with _audit_path(rater_hash).open("a", encoding="utf-8") as audit:
                audit.write(json.dumps(record, ensure_ascii=False) + "\n")
        completed = len(current)
        message = f"✅ 已保存 {item_id}；這位評分者完成 {completed}/18。資料只寫入隔離的人評目錄。"
        return message, render_rater_progress(raw_rater_id)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return f"❌ 未保存：{escape(str(exc))}", render_rater_progress(raw_rater_id)
