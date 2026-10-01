from copy import deepcopy
import json
import subprocess
import sys

from uruha_trace_finalization_m41 import materialize_current_trace_m41, SOURCES_M41
from uruha_memory_observatory import collect_cognitive_graph
from uruha_m41_memory_observatory import render_memory_observatory_m41


def fixture():
    return {"reply":"分かった。", "logic":{label:{"schema":schema,"raw_dialogue_persisted":False,"status":"dev_current"}
                  for label,schema,_stage,_anchor in SOURCES_M41},
            "route_info":{"route":"high_road"},"memory_data":{"sentinel":"unchanged"},
            "runtime_state":{"blackboard":[]},
            "runtime_trace":{"cycle_index":7,"blackboard":[
                {"stage":"route","label":"semantic_route_classifier_m22","payload":{}},
                {"stage":"surface","label":"utterance","payload":{"reply":"分かった。"}}],
                "memory_writes":[{"unchanged":True}]}}


def test_missing_nodes_materialize_exact_current_source_before_anchors():
    result = fixture()
    trace = materialize_current_trace_m41(result)
    rows = result["runtime_trace"]["blackboard"]
    labels = [r["label"] for r in rows]
    assert trace["materialized_node_count"] == 2
    for label,_schema,_stage,anchor in SOURCES_M41:
        assert labels.count(label) == 1
        assert labels.index(label) < labels.index(anchor)
        assert rows[labels.index(label)]["payload"] == result["logic"][label]
    assert result["runtime_state"]["blackboard"] == rows


def test_repeated_finalization_has_no_duplicate_and_repairs_stale_payload():
    result = fixture()
    result["runtime_trace"]["blackboard"] += [{"label":"lexical_boundary_route_m40","payload":{"status":"stale"}}]*2
    materialize_current_trace_m41(result)
    rows = deepcopy(result["runtime_trace"]["blackboard"])
    materialize_current_trace_m41(result)
    assert rows == result["runtime_trace"]["blackboard"]
    assert "stale" not in json.dumps(rows)


def test_missing_and_invalid_sources_do_not_create_execution():
    result = fixture()
    result["logic"] = {"lexical_boundary_route_m40":{"schema":"wrong","raw_dialogue_persisted":False}}
    result["runtime_trace"]["blackboard"].append({"label":"semantic_persona_surface_verifier_m39","payload":{"stale":True}})
    trace = materialize_current_trace_m41(result)
    assert trace["materialized_node_count"] == 0
    assert not any(r["label"] in {s[0] for s in SOURCES_M41} for r in result["runtime_trace"]["blackboard"])


def test_nontrace_cognition_reply_and_memory_are_byte_unchanged():
    result = fixture()
    before = deepcopy(result)
    materialize_current_trace_m41(result)
    for key in ["reply","logic","route_info","memory_data"]:
        assert result[key] == before[key]
    assert result["runtime_trace"]["memory_writes"] == before["runtime_trace"]["memory_writes"]


def test_actual_graph_collector_contains_both_nodes_and_edges():
    result = fixture()
    materialize_current_trace_m41(result)
    graph = collect_cognitive_graph(result)
    by_label = {n["label"]:n for n in graph["nodes"]}
    for label,_schema,_stage,_anchor in SOURCES_M41:
        assert label in by_label
        node_id = by_label[label]["id"]
        assert any(e.get("source")==node_id or e.get("target")==node_id for e in graph["edges"])
    html = render_memory_observatory_m41(result)
    assert 'aria-label="M41 trace delivery integrity"' in html
    assert '2/2' in html


def test_real_run_turn_debug_last_snapshot_reproduces_loss_then_preserves_nodes():
    program = r'''
from copy import deepcopy
import uruha_brain_mac as b
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier
from uruha_lexical_boundary_route_m40 import install_m40_route_guard
from uruha_trace_finalization_m41 import install_m41_trace_finalizer,SOURCES_M41
install_m39_surface_verifier(); install_m40_route_guard()
original_emit = b.UruhaBrainV4_Mac.emit_response_if_ready
def with_contract_evidence(self,event,tick):
    result=original_emit(self,event,tick)
    for label,schema,stage,anchor in SOURCES_M41:
        payload={'schema':schema,'raw_dialogue_persisted':False,'status':'current_contract_event'}
        result['logic'][label]=payload
        result['runtime_trace']['blackboard'].append({'label':label,'stage':stage,'payload':deepcopy(payload)})
    return result
b.UruhaBrainV4_Mac.emit_response_if_ready=with_contract_evidence
before=_IsolatedContractBrain().run_turn_debug('A small current-turn contract message.')
labels_before={x['label'] for x in before['runtime_trace']['blackboard']}
assert not any(label in labels_before for label,*_ in SOURCES_M41)
assert install_m41_trace_finalizer()
brain=_IsolatedContractBrain()
after=brain.run_turn_debug('A small current-turn contract message.')
for label,*_ in SOURCES_M41:
    for rows in [after['runtime_trace']['blackboard'],brain.runtime.blackboard,brain.runtime.turn_traces[-1]['blackboard'],after['runtime_state']['blackboard']]:
        matches=[x for x in rows if x['label']==label]
        assert len(matches)==1 and matches[0]['payload']==after['logic'][label]
assert after['reply']==before['reply']
print('real final snapshot regression passed; generated surface is a contract fixture')
'''
    done = subprocess.run([sys.executable,"-c",program],text=True,capture_output=True)
    assert done.returncode == 0, done.stdout+done.stderr
