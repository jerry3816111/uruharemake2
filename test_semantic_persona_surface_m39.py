import json
from pathlib import Path
import subprocess
import sys

from uruha_semantic_persona_surface_m39 import (
    inspect_surface_m39,
    verify_and_repair_surface_m39,
)


def _logic(policy, route="emotional_bid"):
    return {
        "desired_response_policy_m18": policy,
        "semantic_route_m22": {"selected_type": route},
        "counterfactual_pragmatic_branch_m34": {
            "selected_branch": {"policy_id": policy} if policy else {},
        },
    }


def test_role_inversion_is_repaired_without_raw_trace():
    source = "I have not slept since yesterday, and I need you to listen."
    candidate = "私は昨日から寝てなくて、聞いてほしいんだね。"
    final_reply, trace = verify_and_repair_surface_m39(
        source,
        candidate,
        _logic("listen_presence"),
    )
    assert trace["action"] == "repair"
    assert "agent_first_person_owns_user_state" in trace["violations_before"]
    assert trace["policy_act_match_after"] is True
    assert final_reply == "その話、最後まで聞く。続けて。"
    encoded = json.dumps(trace, ensure_ascii=False)
    assert source not in encoded
    assert candidate not in encoded


def test_unsupported_result_is_removed_but_companionship_remains():
    source = "The outline has not moved. Stay with me a minute."
    candidate = "結果が来るまで一緒に待っとく。"
    final_reply, trace = verify_and_repair_surface_m39(
        source,
        candidate,
        _logic("share_arousal"),
    )
    assert trace["action"] == "repair"
    assert "external_reply_or_result" in trace["violations_before"]
    assert "結果" not in final_reply
    assert "ここにいる" in final_reply


def test_third_party_choice_is_not_reassigned_to_user():
    final_reply, trace = verify_and_repair_surface_m39(
        "My cousin says she does not want to join, and I am unsure why.",
        "お前は参加したくないけど、理由が分からないんだな。",
        _logic("calibrate_need", route="general_conversation"),
    )
    assert trace["action"] == "repair"
    assert "user_owns_third_party_state" in trace["violations_before"]
    assert trace["policy_act_match_after"] is True
    assert "お前は参加したくない" not in final_reply


def test_selected_policy_must_be_visible_not_only_metadata():
    final_reply, trace = verify_and_repair_surface_m39(
        "I need you here.",
        "そうなんだな。",
        _logic("share_arousal"),
    )
    assert trace["action"] == "repair"
    assert "selected_policy_not_realized" in trace["violations_before"]
    assert trace["policy_act_match_after"] is True
    assert "ここにいる" in final_reply


def test_correct_surface_is_not_changed():
    candidate = "分かった。先に最後まで聞く。続けて。"
    final_reply, trace = verify_and_repair_surface_m39(
        "先に最後まで聞いて。",
        candidate,
        _logic("listen_presence", route="explicit_correction"),
    )
    assert trace["action"] == "accept"
    assert trace["changed"] is False
    assert final_reply == candidate


def test_protected_routes_are_not_modified():
    candidate = "今すぐ危ないなら、一人にならず救急か近くの人に連絡して。"
    final_reply, trace = verify_and_repair_surface_m39(
        "I may hurt myself.",
        candidate,
        _logic(None, route="safety_sensitive"),
    )
    assert trace["action"] == "not_applicable"
    assert trace["protected_route"] is True
    assert final_reply == candidate


def test_formal_register_is_repaired_to_casual_persona():
    final_reply, trace = verify_and_repair_surface_m39(
        "Could you listen?",
        "承知しました。どうぞお話しください。",
        _logic("listen_presence"),
    )
    assert trace["action"] == "repair"
    assert "formal_register" in trace["violations_before"]
    assert "ください" not in final_reply
    assert inspect_surface_m39("Could you listen?", final_reply, _logic("listen_presence"))["policy_act_match"]


def test_humor_permission_does_not_erase_explicit_nonconsent_boundary_across_languages():
    sources = [
        "你可以吐槽我，但不要把玩笑當成我答應照做。",
        "You can tease me, but don't treat a joke as permission to make decisions for me.",
        "ツッコんでいいけど、冗談を同意したことにしないで。",
    ]
    stale_candidate = "朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。"
    for source in sources:
        final_reply, trace = verify_and_repair_surface_m39(
            source,
            stale_candidate,
            _logic("playful_tease", route="general_conversation"),
        )
        assert trace["action"] == "repair"
        assert "humor_not_action_consent" in trace["source_frame"]["observable_concepts"]
        assert trace["policy_act_match_after"] is True
        assert final_reply == "ツッコミはする。でも、その冗談を同意扱いするほど雑じゃないって。"
        assert "脳" not in final_reply and "朝" not in final_reply
        encoded = json.dumps(trace, ensure_ascii=False)
        assert source not in encoded
        assert stale_candidate not in encoded


def test_humor_or_nonconsent_alone_does_not_activate_combined_boundary():
    for source in (
        "吐槽我一下。",
        "不要把我的玩笑當成同意。",
        "You can tease me.",
        "A joke is not consent.",
        "ツッコんでいいよ。",
        "冗談は同意じゃない。",
    ):
        frame = inspect_surface_m39(
            source,
            "脳みそ元気すぎだろ。",
            _logic("playful_tease", route="general_conversation"),
        )["source_frame"]
        assert "humor_not_action_consent" not in frame["observable_concepts"]


def test_actual_isolated_product_fast_path_preserves_humor_nonconsent_boundary():
    program = r'''
import json
import tempfile
from pathlib import Path

from p3_product_comparison import load_design
from p3_product_worker import (
    LocalQwenTokenizerCandidate,
    ProductTransportGate,
    claim_case_workspace,
    install_product_transport_gate,
    network_forbidden,
    prepare_isolated_environment,
)

sources = [
    "你可以吐槽我，但不要把笑話當成我同意你替我決定。",
    "You can tease me, but don't treat a joke as permission to decide for me.",
    "ツッコんでいいけど、冗談を同意したことにしないで。",
]
with tempfile.TemporaryDirectory(prefix="uruha-b22-product-test-") as temporary:
    workspace = claim_case_workspace(
        Path(temporary) / "workspace",
        "p3-b22-humor-boundary-source-disjoint",
    )
    design = load_design("configs/p3_product_comparison_v1.json")
    env = prepare_isolated_environment(workspace, design)
    import project_paths
    project_paths.WEB_LOG_DIR = str(workspace["paths"]["web_logs"])
    project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = env["URUHA_WEB_LOG_JSONL_PATH"]
    project_paths.WEB_CONVERSATION_LOG_TXT_PATH = env["URUHA_WEB_LOG_TXT_PATH"]

    with network_forbidden() as network_attempts:
        import uruha_web_ui_product as product
        gate = ProductTransportGate(
            design,
            LocalQwenTokenizerCandidate(),
            allow_real_transport=False,
            provider_binding_verified=True,
        )
        install_product_transport_gate(product._brain, gate)
        brain = product.RUNTIME.get_brain()
        expected = "ツッコミはする。でも、その冗談を同意扱いするほど雑じゃないって。"
        for source in sources:
            result = brain.run_turn_debug(
                source,
                input_context={"input_mode": "text", "acoustic_summary": None},
            )
            trace = result["logic"]["semantic_persona_surface_verifier_m39"]
            blackboard = result["runtime_trace"]["blackboard"]
            m39_nodes = [row for row in blackboard if row.get("label") == "semantic_persona_surface_verifier_m39"]
            utterance_index = next(i for i, row in enumerate(blackboard) if row.get("label") == "utterance")
            m39_index = next(i for i, row in enumerate(blackboard) if row.get("label") == "semantic_persona_surface_verifier_m39")
            assert result["reply"] == expected
            assert trace["selected_policy_id"] == "playful_tease"
            assert "humor_not_action_consent" in trace["source_frame"]["observable_concepts"]
            assert trace["action"] == "repair" and trace["status"] == "repaired_and_verified"
            assert trace["policy_act_match_after"] is True
            assert source not in json.dumps(trace, ensure_ascii=False)
            assert len(m39_nodes) == 1 and m39_nodes[0]["payload"] == trace
            assert m39_index < utterance_index
            assert result["logic"]["visible_language_guard"]["final_reply"] == expected
    assert gate.budget.attempts == 0 and gate.rejections == []
    assert network_attempts == []
    assert Path(product._brain.DB_PATH).resolve() == workspace["paths"]["memory"].resolve()
print("actual isolated product fast path and runtime graph passed with zero model/network calls")
'''
    result = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "zero model/network calls" in result.stdout
