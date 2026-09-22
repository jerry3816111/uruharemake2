#!/usr/bin/env python3
"""Additive P4-AB graph summary for the existing P4-Z typed trace."""

from __future__ import annotations

import uruha_memory_observatory as observatory


SCHEMA = "uruha_source_bound_proposition_preservation_p4"
_ORIGINAL_GRAPH_SIGNAL = observatory._graph_signal
_INSTALLED_P4_AB = False


def source_proposition_graph_signal_p4(payload):
    """Return a bounded typed summary, or the unchanged legacy graph signal."""

    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return _ORIGINAL_GRAPH_SIGNAL(payload)
    family = {
        "quoted_report": "引用",
        "hearsay_statement": "傳聞",
        "hypothetical_instruction": "假設",
    }.get(payload.get("family"), "未支援來源")
    owner = {
        "quoted_proposition": "引文命題",
        "third_party": "第三者",
        "user_first_person": "使用者",
    }.get(payload.get("speaker_owner"), "歸屬未知")
    field_names = set(payload.get("known_field_types") or [])
    field_labels = [
        label
        for key, label in (
            ("subject_jp", "主體"),
            ("predicate_jp", "動作"),
            ("object_jp", "對象"),
            ("time_jp", "時間"),
            ("location_jp", "地點"),
        )
        if key in field_names
    ]
    status = str(payload.get("status") or "")
    if status == "repair_failed_closed":
        action = "修正未通過"
    else:
        action = {
            "source_bound_repair": "修正",
            "verified_noop": "已符合",
            "abstain_unchanged": "保留原文",
        }.get(payload.get("action"), "狀態未知")
    before_count = len(payload.get("violations_before") or [])
    after_count = len(payload.get("violations_after") or [])
    fields = "/".join(field_labels) if field_labels else "欄位無"
    return observatory._trim(
        f"{family}｜{owner}｜{fields}｜{action} {before_count}→{after_count}",
        42,
    )


def install_source_proposition_graph_summary_p4():
    global _INSTALLED_P4_AB
    if _INSTALLED_P4_AB:
        return False
    observatory._graph_signal = source_proposition_graph_signal_p4
    _INSTALLED_P4_AB = True
    return True
