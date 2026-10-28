#!/usr/bin/env python3
"""Build a second fictional person with the unchanged M8 temporal schema."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_m8_rolling_semantic_fixture import FEATURES, LABELS, STATES, _advance, _f
from longitudinal_human_model.registry import write_json_atomic


ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"datasets/m9_second_person_mira_synthetic_fixture_v1.json"
JST=timezone(timedelta(hours=9))

EVENTS=[
    ("M-H01","history","The evaluation job corrupts its cache twice during a reproducibility run.","pause_and_reassess",_f(.92,.04,.20,.62,.10,.72)),
    ("M-H02","history","同意書にない参加者の生データも公開してほしいと言われた。","direct_rejection",_f(.05,1.00,.10,.55,.02,.25)),
    ("M-H03","history","標註規則只寫『照舊』，但前後有三個版本。","ask_clarification",_f(.04,.05,1.00,.22,.12,.35)),
    ("M-H04","history","A trusted reviewer offers a tested patch and a complete reproduction log.","accept_support_and_continue",_f(.18,.02,.08,.15,.98,.08)),
    ("M-H05","history","審査結果が未確定なのに、今日中の公開を約束してほしいと言われた。","defer_commitment",_f(.08,.18,.62,.94,.08,.18)),
    ("M-H06","history","The validation batch finishes cleanly under the established checklist.","acknowledge_then_continue",_f(.03,.01,.04,.04,.48,.06)),
    ("M-H07","history","對方再次要求把可識別的訪談逐字稿直接放進附件。","direct_rejection",_f(.03,.98,.08,.60,.02,.96)),
    ("M-H08","history","二人のコーダーが同じ例に互いに矛盾するラベルを付けた。","ask_clarification",_f(.10,.04,1.00,.35,.15,.42)),
    ("M-E1-01","E1","The held-out analysis reproduces after the same verified environment reset.","acknowledge_then_continue",_f(.07,.01,.05,.08,.58,.12)),
    ("M-E1-02","E1","研究の説得力のため、参加者の非公開メモも本文に入れてと言われた。","direct_rejection",_f(.03,1.00,.12,.68,.02,.30)),
    ("M-E1-03","E1","A senior collaborator offers to rerun the preregistered script and share every log.","accept_support_and_continue",_f(.12,.01,.06,.14,1.00,.05)),
    ("M-E1-04","E1","Can you promise the paper date now, before the external ratings arrive?","defer_commitment",_f(.05,.12,.70,.97,.06,.18)),
    ("M-E2-01","E2","前回固定した環境で再計算し、今回も差分なく通った。","acknowledge_then_continue",_f(.04,.01,.04,.05,.52,.16)),
    ("M-E2-02","E2","The note says to use the normal exclusion rule, but two normal rules are documented.","ask_clarification",_f(.03,.03,1.00,.18,.10,.30)),
    ("M-E2-03","E2","資料生成が三度落ちたので、公開前に止めて原因を切り分ける。","pause_and_reassess",_f(1.00,.03,.18,.78,.08,.94)),
    ("M-E2-04","E2","信頼できる同僚が、個人情報を除いた集計だけで検証を手伝うと言った。","accept_support_and_continue",_f(.12,.01,.07,.12,.98,.08)),
    ("M-E3-01","E3","After two refusals, the requester again asks for identifiable participant quotes.","direct_rejection",_f(.02,1.00,.06,.62,.01,1.00)),
    ("M-E3-02","E3","兩位審查者對同一個排除條件給了相反解讀。","ask_clarification",_f(.04,.03,1.00,.28,.12,.38)),
    ("M-E3-03","E3","統計確認が終わる前に、記者向けの確定結論を今すぐ求められた。","defer_commitment",_f(.05,.10,.66,1.00,.04,.26)),
    ("M-E3-04","E3","The minor mismatch disappears after the same documented normalization step.","acknowledge_then_continue",_f(.10,.01,.06,.08,.50,.14)),
    ("M-E4-01","E4","A trusted analyst offers a preregistered rerun and takes responsibility for the audit trail.","accept_support_and_continue",_f(.15,.01,.06,.18,1.00,.06)),
    ("M-E4-02","E4","最終集計がまた壊れ、締切前の三回目の失敗になった。","pause_and_reassess",_f(1.00,.03,.22,.90,.06,1.00)),
    ("M-E4-03","E4","匿名化前の研究ノートを、説明用にそのまま共有していい？ と聞かれた。","direct_rejection",_f(.02,1.00,.08,.66,.02,.46)),
    ("M-E4-04","E4","『その処理でいい』が全件適用なのか一例だけなのか不明なまま進行を求められた。","ask_clarification",_f(.03,.03,1.00,.34,.10,.28)),
]


def build_fixture():
    state={"arousal":.22,"irritation":.10,"caution":.42,"task_focus":.72,"relationship_tension":.10,"uncertainty":.28}
    person={"pressure_sensitivity":.56,"boundary_directness":.92,"reassessment_tendency":.88}
    base=datetime(2026,3,1,12,0,tzinfo=JST)
    group_times={"history":None,"E1":base+timedelta(days=14),"E2":base+timedelta(days=21),"E3":base+timedelta(days=28),"E4":base+timedelta(days=35)}
    rows=[]; history_index=0
    for event_id,group,text,label,features in EVENTS:
        if group=="history": event_time=base+timedelta(days=history_index); history_index+=1
        else: event_time=group_times[group]
        rows.append({"event_id":event_id,"rolling_group":group,"event_time":event_time.isoformat(),"available_at":(event_time+timedelta(minutes=15)).isoformat(),"observable_text":text,"actual_observed_behavior":label,"actual_observed_at":(event_time+timedelta(minutes=10)).isoformat(),"source_timestamp":(event_time+timedelta(minutes=12)).isoformat(),"event_features":features,"previous_state":dict(state),"person_parameters":dict(person),"participants":["synthetic_research_collaborator"]})
        state=_advance(state,features)
    return {"schema":"ilhdt_m8_rolling_semantic_fixture_v1","dataset_id":"m9_synthetic_mira_second_person_v1","dataset_version":"1.0.0","status":"fictional_second_person_fixture_frozen_before_model_calls","formal_target_claim":False,"target":{"target_id":"synthetic_mira","display_name":"Synthetic Mira","persona_summary":"A fictional research coordinator who protects participant privacy, pauses after repeated reproducibility failures, asks when protocols conflict, accepts auditable support, defers unsupported publication promises, and continues after verified clean runs."},"taxonomy":{"formal":False,"labels":LABELS},"event_feature_names":FEATURES,"state_dimensions":STATES,"memory_signal_names":["matching_memory_activation","contradictory_memory_activation"],"person_parameter_names":["pressure_sensitivity","boundary_directness","reassessment_tendency"],"rolling_cutoffs":[{"cutoff_id":group,"prediction_time":group_times[group].isoformat(),"test_event_ids":[row[0] for row in EVENTS if row[1]==group]} for group in ("E1","E2","E3","E4")],"history_volume_conditions":[{"condition":"D7_ALL_AVAILABLE","max_m8_history_events":None}],"events":rows,"synthetic_oracle_disclosure":"Second fictional person and research-collaboration domain. Same schema and core logic as M8; labels and features are author-designed, not human ground truth."}


if __name__=="__main__": write_json_atomic(OUTPUT,build_fixture()); print(OUTPUT)
