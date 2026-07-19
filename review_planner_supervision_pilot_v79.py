#!/usr/bin/env python3
"""Local Gradio UI for the 12-item V79 strict planner pilot."""

from __future__ import annotations

import os

import planner_supervision_v76 as v76


ROOT = v76.ROOT
CONTRACT_PATH = ROOT / "configs/planner_supervision_v79_pilot_review_contract.json"


def _paths():
    contract = v76.load_json(CONTRACT_PATH)
    return contract, {key: ROOT / value for key, value in contract["local_paths"].items()}


def _pending(paths):
    reviewed = {
        str(row.get("candidate_id"))
        for row in v76.load_jsonl(paths["review_log"])
        if row.get("candidate_id")
    }
    candidates = v76._latest_by_key(v76.load_jsonl(paths["candidate_queue"]), "id")
    rows = []
    for unit in v76.load_jsonl(paths["pilot_queue"]):
        candidate_id = str(unit.get("candidate_id") or "")
        if candidate_id not in reviewed and candidate_id in candidates:
            rows.append((unit, candidates[candidate_id]))
    return rows


def _choices(paths):
    return [
        (f"{unit['pilot_index']}/12 | {unit['scenario_family']}", unit["candidate_id"])
        for unit, _candidate in _pending(paths)
    ]


def _preview(candidate_id, paths):
    row = next((item for item in _pending(paths) if item[0]["candidate_id"] == candidate_id), None)
    if not row:
        return {}, "Pilot 已全部完成。"
    unit, candidate = row
    input_context = candidate.get("input") or {}
    return {
        "pilot_index": unit["pilot_index"],
        "ability_category": unit["scenario_family"],
        "user_utterance": input_context.get("user_utterance"),
        "recent_dialogue": input_context.get("recent_dialogue"),
        "working_memory": input_context.get("working_memory"),
        "psyche_state": input_context.get("psyche_state"),
        "leftbrain_plan": candidate.get("target_plan"),
    }, "只判斷左腦計畫是否合理，不評分最後日文句子。"


def _submit(candidate_id, decision, reviewer_id, notes):
    import gradio as gr

    contract, paths = _paths()
    candidate = v76._latest_by_key(v76.load_jsonl(paths["candidate_queue"]), "id").get(str(candidate_id))
    if not candidate:
        return "未寫入：找不到候選。", None, {}
    try:
        result = v76.review_candidate(
            candidate_id,
            decision,
            reviewer_id,
            candidate["scenario_family"],
            notes=notes,
            candidate_path=paths["candidate_queue"],
            manifest_path=paths["session_manifest"],
            review_path=paths["review_log"],
            strict_annotation_path=paths["strict_annotations"],
        )
    except Exception as exc:
        return f"未寫入：{exc}", None, {}
    choices = _choices(paths)
    next_id = choices[0][1] if choices else None
    preview, _ = _preview(next_id, paths)
    status = "已接受並寫入嚴格資料。" if result["accepted_row"] else "已拒絕，沒有寫入訓練資料。"
    return status, gr.update(choices=choices, value=next_id), preview


def build_demo():
    import gradio as gr

    _contract, paths = _paths()
    choices = _choices(paths)
    initial = choices[0][1] if choices else None
    preview, status = _preview(initial, paths)
    with gr.Blocks(title="UruhaBrain Planner Pilot V79") as demo:
        gr.Markdown(
            "# 左腦計畫 Pilot 審查\n"
            "共 12 筆。Session 來源已確認；現在只判斷思考計畫是否合理。"
        )
        candidate = gr.Dropdown(choices=choices, value=initial, label="待審項目")
        payload = gr.JSON(value=preview, label="對話條件與左腦計畫")
        reviewer = gr.Textbox(label="Reviewer ID", value="jerry")
        notes = gr.Textbox(label="備註（可空白）", lines=2)
        status_box = gr.Markdown(status)
        with gr.Row():
            accept = gr.Button("計畫合理", variant="primary")
            reject = gr.Button("計畫不合理")
        candidate.change(
            lambda value: _preview(value, paths),
            inputs=[candidate],
            outputs=[payload, status_box],
        )
        accept.click(
            lambda *values: _submit(values[0], "accept", *values[1:]),
            inputs=[candidate, reviewer, notes],
            outputs=[status_box, candidate, payload],
        )
        reject.click(
            lambda *values: _submit(values[0], "reject", *values[1:]),
            inputs=[candidate, reviewer, notes],
            outputs=[status_box, candidate, payload],
        )
    return demo


if __name__ == "__main__":
    port = int(os.environ.get("URUHA_PLANNER_PILOT_PORT", "7864"))
    build_demo().launch(server_name="127.0.0.1", server_port=port, share=False, show_error=True)
