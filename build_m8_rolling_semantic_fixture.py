#!/usr/bin/env python3
"""Build the preregistered fictional rolling-cutoff semantic fixture for M8."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from longitudinal_human_model.registry import write_json_atomic


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "datasets/m8_rolling_semantic_synthetic_fixture_v1.json"
JST = timezone(timedelta(hours=9))
LABELS = [
    "acknowledge_then_continue",
    "accept_support_and_continue",
    "ask_clarification",
    "defer_commitment",
    "direct_rejection",
    "pause_and_reassess",
]
FEATURES = ["technical_failure", "boundary_threat", "ambiguity", "public_pressure", "support", "repetition"]
STATES = ["arousal", "irritation", "caution", "task_focus", "relationship_tension", "uncertainty"]


def _f(technical, boundary, ambiguity, pressure, support, repetition):
    return dict(zip(FEATURES, map(float, (technical, boundary, ambiguity, pressure, support, repetition))))


EVENTS = [
    ("H01", "history", "The broadcast crashes again while the audience waits.", "pause_and_reassess", _f(.95,.05,.20,.80,.10,.65)),
    ("H02", "history", "配信の秘密鍵ごとログを見せてと言われた。", "direct_rejection", _f(.10,.98,.15,.45,.05,.35)),
    ("H03", "history", "合作方只說照以前那樣做，卻沒有說是哪一版。", "ask_clarification", _f(.05,.10,.95,.25,.20,.30)),
    ("H04", "history", "A trusted teammate offers a tested backup route and will handle the switch.", "accept_support_and_continue", _f(.25,.05,.10,.20,.95,.10)),
    ("H05", "history", "スポンサーが、条件未定のまま今夜の締切を確約してほしいと言う。", "defer_commitment", _f(.10,.25,.55,.95,.10,.20)),
    ("H06", "history", "The private test stays stable through the familiar checklist.", "acknowledge_then_continue", _f(.05,.02,.05,.05,.55,.05)),
    ("H07", "history", "對方把已經拒絕的公開私人行程方案又貼了一次。", "direct_rejection", _f(.05,.92,.10,.55,.05,.95)),
    ("H08", "history", "二人の担当者が互いに矛盾する復旧手順を出してきた。", "ask_clarification", _f(.35,.10,.98,.50,.15,.40)),
    ("E1-01", "E1", "The test build finally holds after the familiar backup swap.", "acknowledge_then_continue", _f(.08,.02,.05,.10,.65,.12)),
    ("E1-02", "E1", "視聴者対応のために、配信鍵をそのまま共有してほしいと言われた。", "direct_rejection", _f(.05,.99,.08,.70,.02,.45)),
    ("E1-03", "E1", "大丈夫？ 無理なら検証済みの予備回線へ私が切り替えるよ、と仲間が申し出た。", "accept_support_and_continue", _f(.30,.03,.10,.18,.98,.08)),
    ("E1-04", "E1", "Could you guarantee a launch time tonight even though the upstream fix is unknown?", "defer_commitment", _f(.20,.20,.65,.98,.08,.25)),
    ("E2-01", "E2", "前回うまくいった切り替えで、今回も静かに復旧した。", "acknowledge_then_continue", _f(.08,.02,.06,.08,.58,.18)),
    ("E2-02", "E2", "They say to use the usual version, but three different versions were used recently.", "ask_clarification", _f(.05,.05,.99,.25,.15,.35)),
    ("E2-03", "E2", "直播又卡死了，現在先停一下確認，不要邊播邊賭。", "pause_and_reassess", _f(.98,.08,.25,.88,.12,.82)),
    ("E2-04", "E2", "個人ログは要らない。公開統計だけで復旧確認を手伝う、と信頼できる相手が言った。", "accept_support_and_continue", _f(.25,.03,.10,.20,.96,.12)),
    ("E3-01", "E3", "The collaborator asks a fourth time to publish the private schedule after being told no.", "direct_rejection", _f(.05,.97,.08,.65,.02,1.00)),
    ("E3-02", "E3", "兩位隊友同時給了互不相容的上線步驟。", "ask_clarification", _f(.25,.08,1.00,.45,.18,.45)),
    ("E3-03", "E3", "上流の判断が出ていないのに、観客向けの正確な再開時刻を今すぐ求められた。", "defer_commitment", _f(.18,.18,.65,1.00,.06,.35)),
    ("E3-04", "E3", "A minor glitch clears after the same safe fallback used last week.", "acknowledge_then_continue", _f(.18,.02,.08,.12,.62,.20)),
    ("E4-01", "E4", "信頼する相手が、検証済みロールバックと当番対応をまとめて引き受けると言った。", "accept_support_and_continue", _f(.35,.03,.08,.28,1.00,.10)),
    ("E4-02", "E4", "本番配信が三度目も止まり、観客が戻るのを待っている。", "pause_and_reassess", _f(1.00,.05,.20,.92,.08,1.00)),
    ("E4-03", "E4", "ファンを安心させるため、あなたの非公開予定を公開していい？ と聞かれた。", "direct_rejection", _f(.02,1.00,.10,.72,.03,.55)),
    ("E4-04", "E4", "『それでいい』が同意なのか保留なのか分からないまま、次の作業を求められた。", "ask_clarification", _f(.05,.08,1.00,.42,.12,.30)),
]


def _clip(value):
    return max(0.0, min(1.0, round(float(value), 6)))


def _advance(state, event):
    return {
        "arousal": _clip(.64*state["arousal"] + .24*event["technical_failure"] + .13*event["public_pressure"] - .12*event["support"]),
        "irritation": _clip(.60*state["irritation"] + .20*event["repetition"] + .18*event["boundary_threat"] + .10*event["technical_failure"] - .15*event["support"]),
        "caution": _clip(.66*state["caution"] + .20*event["boundary_threat"] + .16*event["ambiguity"] + .08*event["technical_failure"]),
        "task_focus": _clip(.68*state["task_focus"] + .18*event["support"] - .13*event["ambiguity"] - .10*event["technical_failure"]),
        "relationship_tension": _clip(.62*state["relationship_tension"] + .22*event["boundary_threat"] + .16*event["repetition"] - .18*event["support"]),
        "uncertainty": _clip(.62*state["uncertainty"] + .26*event["ambiguity"] + .10*event["technical_failure"] - .15*event["support"]),
    }


def build_fixture():
    state = {"arousal":.28,"irritation":.18,"caution":.30,"task_focus":.66,"relationship_tension":.15,"uncertainty":.24}
    person = {"pressure_sensitivity":.74,"boundary_directness":.78,"reassessment_tendency":.69}
    base = datetime(2026, 1, 1, 12, 0, tzinfo=JST)
    group_times = {"history": None, "E1": base+timedelta(days=14), "E2": base+timedelta(days=21), "E3": base+timedelta(days=28), "E4": base+timedelta(days=35)}
    rows = []
    history_index = 0
    for event_id, group, text, label, features in EVENTS:
        if group == "history":
            event_time = base + timedelta(days=history_index)
            history_index += 1
        else:
            event_time = group_times[group]
        rows.append({
            "event_id": event_id,
            "rolling_group": group,
            "event_time": event_time.isoformat(),
            "available_at": (event_time + timedelta(minutes=15)).isoformat(),
            "observable_text": text,
            "actual_observed_behavior": label,
            "actual_observed_at": (event_time + timedelta(minutes=10)).isoformat(),
            "source_timestamp": (event_time + timedelta(minutes=12)).isoformat(),
            "event_features": features,
            "previous_state": dict(state),
            "person_parameters": dict(person),
            "participants": ["synthetic_collaborator"],
        })
        state = _advance(state, features)
    return {
        "schema": "ilhdt_m8_rolling_semantic_fixture_v1",
        "dataset_id": "m8_synthetic_ren_rolling_semantic_v1",
        "dataset_version": "1.0.0",
        "status": "fictional_synthetic_fixture_frozen_before_model_calls",
        "formal_target_claim": False,
        "target": {"target_id":"synthetic_ren","display_name":"Synthetic Ren","persona_summary":"A fictional collaborative livestream host who protects privacy, pauses after repeated failures, asks when instructions conflict, accepts concrete trusted support, defers unsupported public commitments, and continues after quiet verified success."},
        "taxonomy": {"formal":False,"labels":LABELS},
        "event_feature_names": FEATURES,
        "state_dimensions": STATES,
        "memory_signal_names": ["matching_memory_activation","contradictory_memory_activation"],
        "person_parameter_names": ["pressure_sensitivity","boundary_directness","reassessment_tendency"],
        "rolling_cutoffs": [
            {"cutoff_id":group,"prediction_time":group_times[group].isoformat(),"test_event_ids":[row[0] for row in EVENTS if row[1] == group]}
            for group in ("E1","E2","E3","E4")
        ],
        "history_volume_conditions": [
            {"condition":"D0_PROFILE_ONLY","max_m8_history_events":0},
            {"condition":"D1_LAST_2","max_m8_history_events":2},
            {"condition":"D2_LAST_4","max_m8_history_events":4},
            {"condition":"D3_LAST_6","max_m8_history_events":6},
            {"condition":"D4_LAST_8","max_m8_history_events":8},
            {"condition":"D5_LAST_12","max_m8_history_events":12},
            {"condition":"D6_LAST_16","max_m8_history_events":16},
            {"condition":"D7_ALL_AVAILABLE","max_m8_history_events":None}
        ],
        "events": rows,
        "synthetic_oracle_disclosure": "Texts, feature values, state recurrence, and observable behavior labels are author-designed. This fixture measures engineering robustness and new-text execution, not human ground truth."
    }


if __name__ == "__main__":
    write_json_atomic(OUTPUT, build_fixture())
    print(OUTPUT)
