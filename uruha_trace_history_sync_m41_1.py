"""M41.1: synchronize the same-cycle history mirror after final trace delivery.

The first frozen M41 Safari run retained a stale recent_turn_traces[-1] copy.
Keep that evidence. Only repair this trace mirror; never alter prior cycles,
reply, branch, appraisal, user model or factual memory.
"""
from copy import deepcopy

_INSTALLED_M41_1 = False


def sync_current_history_m41_1(result):
    current = result.get("runtime_trace") or {}
    snapshot = result.get("runtime_state")
    cycle = current.get("cycle_index")
    history = (snapshot or {}).get("recent_turn_traces") or []
    matched = bool(cycle is not None and history and history[-1].get("cycle_index") == cycle)
    audit = {"schema":"uruha_same_cycle_history_sync_m41_1",
             "status":"same_cycle_mirror_synchronized" if matched else "no_matching_history_mirror",
             "cycle_index":cycle,"history_rewritten_count":int(matched),
             "prior_cycles_changed":False,"reply_or_memory_changed":False}
    current["snapshot_history_sync_m41_1"] = audit
    if isinstance(snapshot, dict):
        snapshot["blackboard"] = deepcopy(current.get("blackboard") or [])
        if matched:
            # Do not blindly copy over earlier entries or fabricate a missing
            # history row. Match the current cycle before replacing the mirror.
            snapshot["recent_turn_traces"] = list(history[:-1]) + [deepcopy(current)]
    return audit


def install_m41_1_history_sync():
    global _INSTALLED_M41_1
    if _INSTALLED_M41_1:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac
    original_emit = UruhaBrainV4_Mac.emit_response_if_ready
    original_run = UruhaBrainV4_Mac.run_turn_debug

    def finish(self, result):
        sync_current_history_m41_1(result)
        current = result.get("runtime_trace") or {}
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == current.get("cycle_index"):
            self.runtime.turn_traces[-1] = deepcopy(current)
        return result

    def emit(self, event, tick_result):
        return finish(self, original_emit(self,event,tick_result))

    def run(self, user_input, input_context=None):
        return finish(self, original_run(self,user_input,input_context=input_context))

    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED_M41_1 = True
    return True
