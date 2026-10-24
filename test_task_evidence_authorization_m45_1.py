from copy import deepcopy
import subprocess
import sys

import pytest
from uruha_actionable_help_delivery_m45 import source_packet
from uruha_task_evidence_authorization_m45_1 import task_sources, deliver_with_task_evidence, LABEL
from test_actionable_help_delivery_m45 import help_logic, fake_calls
from uruha_actionable_help_eval_m45 import fixture


@pytest.mark.parametrize("text", ["Tell me what to do.", "給我一個方法。", "方法を教えて。",
                                 "You misunderstood; give me a method."])
def test_request_only_never_calls_model_or_delivers(text):
    def forbidden(*args):
        raise AssertionError("No task: model must not be called")
    reply, audit = deliver_with_task_evidence(text, "一個だけ決めよ。", help_logic(), source_packet(text), forbidden)
    assert audit["status"] == "awaiting_context" and not audit["delivered"]
    assert audit["model_calls_attempted"] == 0 and "どの作業" in reply
    assert audit[LABEL]["allowed_clause_count"] == 0


@pytest.mark.parametrize("text,content", [
    ("The drawer contains letters and receipts. Give me a method.", "The drawer contains letters and receipts."),
    ("抽屜裡都是信件，給我一個方法。", "抽屜裡都是信件，"),
    ("引き出しに手紙が散らばってる。方法を教えて。", "引き出しに手紙が散らばってる。")])
def test_content_is_exactly_anchored_and_not_a_task_whitelist(text, content):
    source = source_packet(text, turn_index=4)
    original = deepcopy(source)
    kept, gate = task_sources(source)
    assert len(kept) == 1 and kept[0]["text"] == content and source == original
    origin = kept[0]["origin"]
    assert text[origin["span_start"]:origin["span_start"]+origin["span_length"]] == content
    assert gate["excluded"] and text not in str(gate)


def test_linked_user_content_survives_but_assistant_never_becomes_evidence():
    sources = source_packet("You misunderstood; give me a method.",
        {"recent_turns": [{"user": "The drawer is cluttered.", "reply": "The secret safe is open."}]},
        {"status": "contradicted", "feedback_linked_to_previous_prediction": True,
         "explicit_target_policy": "solve_regulation"}, 2)
    kept, _ = task_sources(sources)
    assert len(kept) == 1 and kept[0]["kind"] == "linked_previous_user"
    assert "safe" not in str(kept) and kept[0]["origin"]["source_id"] == "prior:1"


def test_task_inside_request_is_conservatively_withheld_not_claimed_general_parser():
    kept, gate = task_sources(source_packet("Give me a method for organizing postcards."))
    assert kept == [] and gate["status"] == "no_independent_task_content"


def test_valid_task_still_reaches_original_two_call_action_checks():
    p, sources, _ = fixture()
    kept, _ = task_sources(sources)
    p["source_id"] = kept[0]["id"]
    reply, audit = deliver_with_task_evidence(sources[0]["text"], "一個だけ。", help_logic(), sources, fake_calls(p))
    assert audit["delivered"] and audit["model_calls_completed"] == 2
    assert reply == p["instruction_jp"] and audit["evidence"]["source_id"] == kept[0]["id"]


def test_nonhelp_and_protected_boundary_are_unchanged():
    for plan in (dict(help_logic(), desired_response_policy_m18="listen_presence"),
                 dict(help_logic(), semantic_route_m22={"selected_type": "safety_sensitive"})):
        reply, audit = deliver_with_task_evidence("Give me a method.", "ここにいる。", plan, [])
        assert reply == "ここにいる。" and audit["status"] == "not_applicable" and LABEL not in audit


def test_runtime_missing_task_cannot_gain_credit_on_following_confirmation():
    program = r'''
import uruha_web_ui_m45_1
import uruha_actionable_help_delivery_m45 as m
import uruha_adaptive_person_model as a
import uruha_semantic_persona_surface_m39 as s
from test_personhood_loop_v2_13 import _IsolatedContractBrain,_FakeRightBrain
class FakeRight(_FakeRightBrain):
    def enforce_user_visible_japanese(self, reply, logic, user_input='', **kwargs):
        reply,audit=s.verify_and_repair_surface_m39(user_input,reply,logic)
        logic['semantic_persona_surface_verifier_m39']=audit
        return reply
b=_IsolatedContractBrain(); b.right_brain=FakeRight()
def forbidden(*args): raise AssertionError('No model may invent an absent task')
m._native_json=forbidden
r=b.run_turn_debug('Give me one practical step I can take now.')
assert r['logic'][m.LABEL]['status']=='awaiting_context'
assert b.runtime.adaptive_person_model[m.STORE]['delivered'] is False
state,feedback=a.observe_next_turn(b.runtime.adaptive_person_model,'Yes, exactly.',2)
assert feedback['status']=='uncertain' and not feedback['atom_changes'],feedback
assert feedback[m.OUTCOME_LABEL]['outcome']=='not_scored_action_not_delivered'
print('isolated runtime missing-task and no-false-credit contract passed')
'''
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
