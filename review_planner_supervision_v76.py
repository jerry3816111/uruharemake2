#!/usr/bin/env python3
"""Local Gradio UI for strict planner-plan review."""

from __future__ import annotations

import json
import os

from planner_supervision_v76 import CONTRACT_PATH, ROOT, load_json, load_jsonl, review_candidate


def _paths():
    contract = load_json(CONTRACT_PATH)
    local = contract["local_paths"]
    return contract, {key: ROOT / value for key, value in local.items()}


def _reviewed_ids(review_path):
    return {str(row.get("candidate_id")) for row in load_jsonl(review_path) if row.get("candidate_id")}


def _candidate_rows(candidate_path, review_path):
    reviewed = _reviewed_ids(review_path)
    return [row for row in load_jsonl(candidate_path) if str(row.get("id")) not in reviewed]


def _choices(candidate_path, review_path):
    return [
        (f"{row.get('scenario_family')} | {row.get('input', {}).get('user_utterance', '')[:48]}", row["id"])
        for row in _candidate_rows(candidate_path, review_path)
    ]


def _preview(candidate_id, candidate_path, review_path):
    row = next((item for item in _candidate_rows(candidate_path, review_path) if item.get("id") == candidate_id), None)
    if not row:
        return {}, "尚無未審候選。", None
    compact = {
        "candidate_id": row["id"],
        "source_session_id": row.get("source_session_id"),
        "user_utterance": row.get("input", {}).get("user_utterance"),
        "recent_dialogue": row.get("input", {}).get("recent_dialogue"),
        "working_memory": row.get("input", {}).get("working_memory"),
        "psyche_state": row.get("input", {}).get("psyche_state"),
        "suggested_scenario_family": row.get("scenario_family"),
        "target_plan": row.get("target_plan"),
    }
    return compact, "請判斷這個思考計畫是否合理；不是評分最後句子好不好。", row.get("scenario_family")


def _submit(candidate_id, decision, scenario_family, reviewer_id, certify, consent, notes):
    import gradio as gr

    contract, paths = _paths()
    try:
        result = review_candidate(
            candidate_id,
            decision,
            reviewer_id,
            scenario_family,
            notes=notes,
            certify_non_benchmark=certify,
            consent_to_training=consent,
            candidate_path=paths["candidate_queue"],
            manifest_path=paths["session_manifest"],
            review_path=paths["review_log"],
            strict_annotation_path=paths["strict_annotations"],
            contract=contract,
        )
    except Exception as exc:
        return f"未寫入：{exc}", None, {}, scenario_family
    choices = _choices(paths["candidate_queue"], paths["review_log"])
    next_id = choices[0][1] if choices else None
    preview, _, next_family = _preview(next_id, paths["candidate_queue"], paths["review_log"])
    status = "已接受並寫入嚴格資料。" if result["accepted_row"] else "已拒絕；沒有寫入訓練資料。"
    return status, gr.update(choices=choices, value=next_id), preview, next_family or scenario_family


def build_demo():
    import gradio as gr

    contract, paths = _paths()
    choices = _choices(paths["candidate_queue"], paths["review_log"])
    initial = choices[0][1] if choices else None
    preview, status, family = _preview(initial, paths["candidate_queue"], paths["review_log"])

    with gr.Blocks(title="UruhaBrain Planner Review V76") as demo:
        gr.Markdown(
            "# Planner Review V76\n"
            "只判斷左腦思考計畫是否合理。接受前必須確認整個 session 不是 benchmark/holdout，並同意用於本機訓練。"
        )
        candidate = gr.Dropdown(choices=choices, value=initial, label="待審候選")
        payload = gr.JSON(value=preview, label="原始發話、有限上下文與完整計畫")
        family_input = gr.Dropdown(
            choices=contract["scenario_families"], value=family or "ordinary_direct", label="能力分類"
        )
        reviewer = gr.Textbox(label="Reviewer ID", value="jerry")
        certify = gr.Checkbox(label="我確認此 session 不是 benchmark 或 holdout")
        consent = gr.Checkbox(label="我同意此 session 可用於本機 planner 訓練")
        notes = gr.Textbox(label="備註", lines=2)
        status_box = gr.Markdown(status)
        with gr.Row():
            accept = gr.Button("接受計畫", variant="primary")
            reject = gr.Button("拒絕計畫")

        def load_selected(candidate_id):
            payload_value, status_value, family_value = _preview(
                candidate_id, paths["candidate_queue"], paths["review_log"]
            )
            return payload_value, status_value, family_value or "ordinary_direct"

        candidate.change(load_selected, inputs=[candidate], outputs=[payload, status_box, family_input])
        accept.click(
            lambda *values: _submit(values[0], "accept", *values[1:]),
            inputs=[candidate, family_input, reviewer, certify, consent, notes],
            outputs=[status_box, candidate, payload, family_input],
        )
        reject.click(
            lambda *values: _submit(values[0], "reject", *values[1:]),
            inputs=[candidate, family_input, reviewer, certify, consent, notes],
            outputs=[status_box, candidate, payload, family_input],
        )
    return demo


if __name__ == "__main__":
    port = int(os.environ.get("URUHA_PLANNER_REVIEW_PORT", "7862"))
    build_demo().launch(server_name="127.0.0.1", server_port=port, share=False, show_error=True)
