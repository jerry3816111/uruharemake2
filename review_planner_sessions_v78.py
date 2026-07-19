#!/usr/bin/env python3
"""Local Gradio UI for six session-level provenance decisions."""

from __future__ import annotations

import os

import planner_supervision_session_review_v78 as v78
import planner_supervision_v76 as v76


def _paths():
    contract = v76.load_json(v78.CONTRACT_PATH)
    local = contract["local_paths"]
    return contract, {key: v78.ROOT / value for key, value in local.items()}


def _pending_units(queue_path, manifest_path):
    reviewed = {
        str(row.get("session_id"))
        for row in v76.load_jsonl(manifest_path)
        if row.get("session_id")
    }
    return [
        unit
        for unit in v76.load_jsonl(queue_path)
        if str(unit.get("source_session_id")) not in reviewed
    ]


def _choices(queue_path, manifest_path):
    choices = []
    for unit in _pending_units(queue_path, manifest_path):
        summary = unit["session_summary"]
        time_range = summary.get("timestamp_range") or ["", ""]
        label = f"{time_range[0][:10]} | {summary['candidate_count']} 筆候選"
        choices.append((label, unit["id"]))
    return choices


def _preview(review_unit_id, queue_path, manifest_path):
    unit = next(
        (
            row
            for row in _pending_units(queue_path, manifest_path)
            if row.get("id") == review_unit_id
        ),
        None,
    )
    if not unit:
        return {}, "所有 Session 都已判斷，或目前沒有待審資料。"
    return {
        "review_unit_id": unit["id"],
        "source_session_id": unit["source_session_id"],
        "candidate_count": unit["session_summary"]["candidate_count"],
        "time_range": unit["session_summary"]["timestamp_range"],
        "language_counts": unit["session_summary"]["language_counts"],
        "scenario_family_counts": unit["session_summary"]["scenario_family_counts"],
        "utterance_preview": unit["session_summary"]["utterance_preview"],
        "all_user_utterances": unit["session_summary"]["all_user_utterances"],
    }, "只判斷整段對話的來源，不用評分回答品質。"


def _submit(review_unit_id, decision, reviewer_id, consent, notes):
    import gradio as gr

    _, paths = _paths()
    try:
        row = v78.review_session(
            review_unit_id,
            decision,
            reviewer_id,
            consent_to_training=consent,
            notes=notes,
            candidate_path=paths["candidate_queue"],
            queue_path=paths["session_review_queue"],
            manifest_path=paths["session_manifest"],
        )
    except Exception as exc:
        return f"未寫入：{exc}", None, {}
    choices = _choices(paths["session_review_queue"], paths["session_manifest"])
    next_id = choices[0][1] if choices else None
    preview, _ = _preview(next_id, paths["session_review_queue"], paths["session_manifest"])
    status = "已認證為普通非測驗對話。" if row["benchmark_origin"] == "none" else "已隔離此 Session。"
    return status, gr.update(choices=choices, value=next_id), preview


def build_demo():
    import gradio as gr

    _, paths = _paths()
    choices = _choices(paths["session_review_queue"], paths["session_manifest"])
    initial = choices[0][1] if choices else None
    preview, status = _preview(initial, paths["session_review_queue"], paths["session_manifest"])
    with gr.Blocks(title="UruhaBrain Session Review V78") as demo:
        gr.Markdown(
            "# Session 來源確認\n"
            "總共最多 6 項。只判斷這整段是不是普通聊天；如果曾拿測驗題、壓力題或刻意測能力，請選隔離。"
        )
        unit = gr.Dropdown(choices=choices, value=initial, label="待確認 Session")
        payload = gr.JSON(value=preview, label="時間、數量、三個片段與完整使用者輸入")
        reviewer = gr.Textbox(label="Reviewer ID", value="jerry")
        consent = gr.Checkbox(label="我同意普通聊天 Session 可用於本機 planner 訓練")
        notes = gr.Textbox(label="備註（可空白）", lines=2)
        status_box = gr.Markdown(status)
        with gr.Row():
            certify = gr.Button("普通聊天，可用", variant="primary")
            quarantine = gr.Button("測驗或不確定，隔離")

        unit.change(
            lambda value: _preview(value, paths["session_review_queue"], paths["session_manifest"]),
            inputs=[unit],
            outputs=[payload, status_box],
        )
        certify.click(
            lambda *values: _submit(values[0], "certify_nonbenchmark", *values[1:]),
            inputs=[unit, reviewer, consent, notes],
            outputs=[status_box, unit, payload],
        )
        quarantine.click(
            lambda review_unit_id, reviewer_id, _consent, review_notes: _submit(
                review_unit_id, "quarantine", reviewer_id, False, review_notes
            ),
            inputs=[unit, reviewer, consent, notes],
            outputs=[status_box, unit, payload],
        )
    return demo


if __name__ == "__main__":
    port = int(os.environ.get("URUHA_SESSION_REVIEW_PORT", "7863"))
    build_demo().launch(server_name="127.0.0.1", server_port=port, share=False, show_error=True)
