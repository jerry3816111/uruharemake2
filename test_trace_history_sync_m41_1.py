from copy import deepcopy
import subprocess
import sys
from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1


def test_same_cycle_mirror_and_only_that_mirror_updated():
    result={"reply":" unchanged ","logic":{"policy":"kept"},
            "runtime_trace":{"cycle_index":3,"blackboard":[{"label":"current"}]},
            "runtime_state":{"recent_turn_traces":[{"cycle_index":2,"blackboard":["keep"]},{"cycle_index":3,"blackboard":[]}]}}
    before=deepcopy(result)
    audit=sync_current_history_m41_1(result)
    assert audit['history_rewritten_count']==1
    assert result['runtime_state']['recent_turn_traces'][-1]==result['runtime_trace']
    assert result['runtime_state']['recent_turn_traces'][0]==before['runtime_state']['recent_turn_traces'][0]
    assert result['reply']==before['reply'] and result['logic']==before['logic']


def test_no_matching_cycle_does_not_overwrite_or_invent_history():
    result={'runtime_trace':{'cycle_index':8,'blackboard':[]},'runtime_state':{'recent_turn_traces':[{'cycle_index':7,'blackboard':['old']}]}}
    old=deepcopy(result['runtime_state']['recent_turn_traces'])
    assert sync_current_history_m41_1(result)['history_rewritten_count']==0
    assert result['runtime_state']['recent_turn_traces']==old


def test_installed_real_final_snapshot_mirrors_latest_trace_including_latency():
    code=r'''
import uruha_brain_mac as b
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_trace_finalization_m41 import install_m41_trace_finalizer
from uruha_trace_history_sync_m41_1 import install_m41_1_history_sync
install_m41_trace_finalizer(); install_m41_1_history_sync()
brain=_IsolatedContractBrain()
result=brain.run_turn_debug('A separate history consistency contract.')
assert result['runtime_trace']==result['runtime_state']['recent_turn_traces'][-1]
assert result['runtime_trace']==brain.runtime.turn_traces[-1]
assert result['runtime_trace']['blackboard']==result['runtime_state']['blackboard']
assert any(x['label']=='runtime_latency_m18' for x in result['runtime_trace']['blackboard'])
print('complete final snapshot mirror passed')
'''
    done=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert done.returncode==0,done.stdout+done.stderr
