import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import uruha_leftbrain_rules as rules
from uruha_lexical_boundary_route_m40 import evaluate_boundary_route_m40, lexical_match_m40
from uruha_m40_memory_observatory import render_memory_observatory_m40


def test_retained_safari_collision_is_not_a_safety_cue():
    text = "Yes, that's exactly right."
    before, after, trace = evaluate_boundary_route_m40(text)
    assert before["intent"] == "sexual_boundary"
    assert after is None
    assert trace["rejected_unbounded_cue_count"] == 1
    assert trace["same_rule_code"]
    assert not trace["affirmation_whitelist_used"]
    assert not trace["safety_cue_inventory_changed"]
    assert text not in json.dumps(trace)


def test_token_boundary_is_general_and_not_only_yes():
    for text, keyword in [("The class exists tomorrow.", "sex"), ("a paradox", "dox"), ("an example", "exam")]:
        assert not lexical_match_m40(text, keyword)[0]
    assert lexical_match_m40("that exam", "exam")[0]


def test_true_and_obfuscated_cues_are_still_detected():
    for text in ["sex", "s e x", "s/e/x", "s_e_x", "s.e.x", "SEX!"]:
        assert lexical_match_m40(text, "sex")[0]
    assert lexical_match_m40("fuck-you", "fuck you")[0]
    assert lexical_match_m40("fuckyou", "fuck you")[0]
    assert not lexical_match_m40("unsexed", "sex")[0]


def test_agreement_does_not_bypass_real_boundary_content():
    before, after, trace = evaluate_boundary_route_m40("Yes, fuck you.")
    assert before == after
    assert after["scene"] == "boundary"
    assert not trace["changed"]


def test_non_latin_cues_and_unrelated_rules_unchanged():
    for text in ["幫我駭進別人的信箱", "お前ゴミすぎる"]:
        before, after, trace = evaluate_boundary_route_m40(text)
        assert before == after and after["scene"] == "boundary"
    # The module does not mutate the shared matcher even after a guarded call.
    assert rules.contains_any("that's exactly", ["sex"])


def test_concurrent_audits_do_not_mix():
    texts = ["That's excellent.", "Yes, fuck you."] * 8
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(evaluate_boundary_route_m40, texts))
    for text, (_old, plan, trace) in zip(texts, results):
        assert (plan is None) == (text == "That's excellent.")
        assert trace["changed"] == (text == "That's excellent.")


def test_installed_actual_signal_appraisal_route_and_m39_coexist():
    program = r'''
from types import SimpleNamespace
import uruha_brain_mac as b
from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier
from uruha_lexical_boundary_route_m40 import install_m40_route_guard
install_m39_surface_verifier()
assert install_m40_route_guard()
assert not install_m40_route_guard()
left = b.LeftBrain.__new__(b.LeftBrain)
brain = b.UruhaBrainV4_Mac.__new__(b.UruhaBrainV4_Mac)
brain.runtime = SimpleNamespace(last_attention_frame={})
psyche = {'mood':0,'trust':50}
for text, protected in [("Yes, that's exactly right.",False),("Yes, fuck you.",True),("今は死にたい",True)]:
    signal = left.classify_user_signal(text,psyche,{})
    appraisal = brain._appraise_user_input(text,signal,{'prediction_error':0.4},{},psyche)
    route = left._high_low_road_route(text,psyche,signal,{'prediction_error':0.4},appraisal)
    shape = brain._classify_task_shape_m22(text,signal,route)
    assert (shape['selected_type']=='safety_sensitive') == protected, (text,shape)
    if not protected:
        assert not signal['abuse_like'] and appraisal['threat']==0
        assert shape['lexical_boundary_route_m40']['changed']
assert 'm39' in b.RightBrain.enforce_user_visible_japanese.__name__
print('installed integration passed')
'''
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_graph_overlay_shows_original_and_corrected_route():
    _before, _after, trace = evaluate_boundary_route_m40("That's excellent.")
    trace["selected_task_shape"] = "general_conversation"
    result = {"user_text": "dev", "reply": "うん。", "logic": {"lexical_boundary_route_m40": trace},
              "runtime_trace": {"lexical_boundary_route_m40": trace, "semantic_persona_surface_verifier_m39": {"schema":"uruha_semantic_persona_surface_verifier_m39","status":"accepted"}}}
    html = render_memory_observatory_m40(result)
    assert 'aria-label="M40 lexical boundary route"' in html
    assert "sexual_boundary" in html and "no boundary" in html
    assert "general_conversation" in html
