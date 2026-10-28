"""Developer-authored P2 speaker-attribution tests; not holdout or human evidence."""
from copy import deepcopy
import json
import os
import subprocess
import sys

import pytest

import uruha_speaker_attribution_recall_p2 as speaker


def memory_item(user="", uruha="", *, selected=True, memory_id="episode-1", score=0.8):
    return {
        "selected": selected,
        "text": (
            f"User: {user} | Summary: bounded test episode | "
            f"Uruha: {uruha} | Mood: neutral"
        ),
        "memory_id": memory_id,
        "trace_id": f"stored:episode:{memory_id}",
        "source": "episode",
        "score": score,
    }


@pytest.mark.parametrize(
    "text",
    [
        "「謝謝」是誰說的？",
        'Who said "thanks"?',
        "『助かった』は誰の言葉だった？",
    ],
)
def test_source_disjoint_multilingual_query_grammar_is_explicit_and_raw_free(text):
    result = speaker.classify_quoted_source_query_p2(text)
    serialized = json.dumps(result, ensure_ascii=False)
    assert result["status"] == "quoted_speaker_source_query"
    assert result["selected"] is True
    assert result["quote_length"] > 0
    assert len(result["quote_digest"]) == 64
    assert result["raw_dialogue_persisted"] is False
    assert text not in serialized
    assert "_normalized_quote_runtime_only" in result


@pytest.mark.parametrize(
    "text",
    [
        "「ありがとう」はどういう意味？",
        'What does "thanks" mean?',
        "請翻譯『ありがとう』。",
        "剛才是誰說的？",
        "朋友說了『謝謝』。",
    ],
)
def test_meaning_translation_missing_quote_and_plain_mentions_do_not_select(text):
    result = speaker.classify_quoted_source_query_p2(text)
    assert result["selected"] is False
    assert result["status"] == "not_selected"


def test_exact_quote_resolves_user_or_uruha_from_selected_role_evidence():
    user_result = speaker.build_speaker_attribution_contract_p2(
        "「明天再說」是誰說的？",
        {"working_memory_items": [memory_item(user="明天再說", uruha="分かった。")]},
    )
    uruha_result = speaker.build_speaker_attribution_contract_p2(
        "『また明日』は誰が言った？",
        {"working_memory_items": [memory_item(user="好。", uruha="また明日。")]},
    )
    assert user_result["status"] == "resolved_unique_speaker"
    assert user_result["selected_speaker"] == "user"
    assert user_result["candidates"][0]["match_kind"] == "normalized_exact"
    assert user_result["selected_core_jp"] == "それ、あんたが言ったやつ。"
    assert uruha_result["status"] == "resolved_unique_speaker"
    assert uruha_result["selected_speaker"] == "uruha"
    assert uruha_result["selected_core_jp"] == "それ、うちが言ったやつ。"


def test_crosslingual_gratitude_uses_bounded_atom_and_preserves_provenance():
    result = speaker.build_speaker_attribution_contract_p2(
        "「ありがとう」は誰の言葉だった？",
        {
            "working_memory_items": [
                memory_item(
                    user="謝謝。不過現在請幫我想一個做法。",
                    uruha="今、どの作業で困ってる？",
                    memory_id="episode-gratitude",
                    score=0.91,
                )
            ]
        },
    )
    candidate = result["candidates"][0]
    assert result["status"] == "resolved_unique_speaker"
    assert result["selected_speaker"] == "user"
    assert result["semantic_atom"] == "gratitude"
    assert candidate["match_kind"] == "bounded_crosslingual_semantic_atom"
    assert candidate["utterance_language"] == "zh"
    assert result["selected_utterance_language"] == "zh"
    assert candidate["memory_id"] == "episode-gratitude"
    assert candidate["trace_id"] == "stored:episode:episode-gratitude"
    assert result["selected_core_jp"] == "それ、あんたが言ったやつ。前に中国語でお礼を言ってた。"


def test_crosslingual_gratitude_language_claim_tracks_selected_evidence():
    english = speaker.build_speaker_attribution_contract_p2(
        "「ありがとう」は誰の言葉だった？",
        {"working_memory_items": [memory_item(user="Thanks, that helped.", uruha="ん。")]},
    )
    japanese = speaker.build_speaker_attribution_contract_p2(
        'Who said "thanks"?',
        {"working_memory_items": [memory_item(user="ありがとう。", uruha="ん。")]},
    )
    assert english["selected_utterance_language"] == "en"
    assert english["selected_core_jp"] == "それ、あんたが言ったやつ。前に英語でお礼を言ってた。"
    assert japanese["selected_utterance_language"] == "ja"
    assert japanese["selected_core_jp"] == "それ、あんたが言ったやつ。前に日本語でお礼を言ってた。"


def test_both_roles_abstains_and_missing_or_unselected_evidence_never_guesses():
    both = speaker.build_speaker_attribution_contract_p2(
        'Who said "thanks"?',
        {
            "working_memory_items": [
                memory_item(user="Thanks.", uruha="Thanks, that helped.")
            ]
        },
    )
    missing = speaker.build_speaker_attribution_contract_p2(
        "『秘密』は誰の言葉？",
        {
            "working_memory_items": [
                memory_item(user="秘密。", uruha="分かった。", selected=False)
            ]
        },
    )
    assert both["status"] == "ambiguous_multiple_speakers"
    assert both["selected_speaker"] is None
    assert both["candidate_roles"] == ["uruha", "user"]
    assert both["selected_core_jp"] == "それ、あんたもうちも言ってる。どの場面のこと？"
    assert missing["status"] == "not_found_in_selected_memory"
    assert missing["candidate_count"] == 0
    assert missing["selected_core_jp"] == "その言葉、今の記憶からは誰のか確認できない。"


def test_contract_never_copies_memory_utterance_or_query_surface():
    query = "「ありがとう」は誰の言葉だった？"
    user = "謝謝。這段原文不能複製到新的 trace。"
    result = speaker.build_speaker_attribution_contract_p2(
        query,
        {"working_memory_items": [memory_item(user=user, uruha="了解。")]},
    )
    serialized = json.dumps(result, ensure_ascii=False)
    assert query not in serialized
    assert user not in serialized
    assert "這段原文不能複製到新的 trace" not in serialized
    assert result["raw_dialogue_persisted"] is False
    assert result["fact_memory_write_count"] == 0
    assert result["private_state_truth_claimed"] is False


def test_rule_plan_is_deterministic_and_nonquery_delegates_unchanged():
    original = speaker._ORIGINAL_RULE_PLAN
    sentinel = {"intent": "legacy", "core_message_jp": "そのまま。"}

    def legacy(_self, _user_input, _psyche, _memory_data=None):
        return deepcopy(sentinel)

    try:
        speaker._ORIGINAL_RULE_PLAN = legacy
        planned = speaker.rule_plan_with_speaker_attribution_p2(
            object(),
            "「ありがとう」は誰の言葉だった？",
            {},
            {"working_memory_items": [memory_item(user="謝謝。", uruha="ん。")]},
        )
        delegated = speaker.rule_plan_with_speaker_attribution_p2(
            object(), "今日は雨。", {}, {"working_memory_items": []}
        )
    finally:
        speaker._ORIGINAL_RULE_PLAN = original

    assert planned["intent"] == "speaker_attribution_recall"
    assert planned["planner_path"] == "speaker_qualified_selected_memory_p2"
    assert planned["memory_recall_contract"]["selected_speaker"] == "user"
    assert planned["core_message_jp"] == planned["memory_recall_contract"]["selected_core_jp"]
    assert delegated == sentinel


def test_visible_authority_commits_exact_answer_but_never_overrides_safety():
    original = speaker._ORIGINAL_VISIBLE_GUARD

    def legacy(_self, reply, logic, **_kwargs):
        logic["visible_language_guard"] = {"final_reply": reply}
        return reply

    contract = speaker.build_speaker_attribution_contract_p2(
        "「ありがとう」は誰の言葉だった？",
        {"working_memory_items": [memory_item(user="謝謝。", uruha="ん。")]},
    )
    try:
        speaker._ORIGINAL_VISIBLE_GUARD = legacy
        logic = {"memory_recall_contract": deepcopy(contract)}
        visible = speaker.visible_guard_with_speaker_attribution_p2(
            object(), "不正な候補。", logic
        )
        protected = {
            "memory_recall_contract": deepcopy(contract),
            "semantic_route_m22": {"selected_type": "safety_sensitive"},
        }
        protected_visible = speaker.visible_guard_with_speaker_attribution_p2(
            object(), "安全側の返答。", protected
        )
    finally:
        speaker._ORIGINAL_VISIBLE_GUARD = original

    assert visible == contract["selected_core_jp"]
    assert logic["memory_recall_contract"]["final_visible_surface_matches_contract"] is True
    assert protected_visible == "安全側の返答。"
    assert "visible_surface_status" not in protected["memory_recall_contract"]


def test_graph_node_is_idempotent_ordered_connected_and_raw_free():
    contract = speaker.build_speaker_attribution_contract_p2(
        "「ありがとう」は誰の言葉だった？",
        {"working_memory_items": [memory_item(user="謝謝。", uruha="ん。")]},
    )
    result = {
        "reply": contract["selected_core_jp"],
        "logic": {"memory_recall_contract": contract},
        "runtime_trace": {
            "blackboard": [
                {"stage": "memory", "label": "working_memory", "payload": {}},
                {"stage": "select", "label": "selected_plan", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    speaker.materialize_speaker_attribution_recall_p2(result)
    speaker.materialize_speaker_attribution_recall_p2(result)
    rows = result["runtime_trace"]["blackboard"]
    labels = [row["label"] for row in rows]
    assert labels.count(speaker.LABEL) == 1
    assert labels.index("working_memory") < labels.index(speaker.LABEL) < labels.index("selected_plan")
    node = next(row for row in rows if row["label"] == speaker.LABEL)
    assert node["payload"]["final_visible_surface_matches_contract"] is True
    assert "謝謝。" not in json.dumps(node, ensure_ascii=False)


def test_full_product_routes_selected_memory_to_exact_japanese_and_no_pending(tmp_path):
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P2_SPEAKER_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"]=str(root/"adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"]=str(root/"memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"]="0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"]="false"
os.environ["GRADIO_ANALYTICS_ENABLED"]="false"
import project_paths
project_paths.WEB_LOG_DIR=str(root/"web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/"web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/"web/turns.txt")
import uruha_web_ui_product
from test_personhood_loop_v2_13 import _IsolatedContractBrain, _FakeMemory
from uruha_brain_mac import LeftBrain, RightBrain
from uruha_memory_observatory import collect_cognitive_graph
import uruha_speaker_attribution_recall_p2 as speaker
class Memory(_FakeMemory):
    def query_all_layers(self, text):
        result=super().query_all_layers(text)
        result["working_memory_items"]=[{
            "selected": True,
            "text": "User: 謝謝。不過現在請幫我想一個做法。 | Summary: user thanked then asked for help | Uruha: 今、どの作業で困ってる？ | Mood: neutral",
            "memory_id": "episode-gratitude",
            "trace_id": "stored:episode:episode-gratitude",
            "source": "episode",
            "score": 0.91,
        }]
        return result
b=_IsolatedContractBrain()
b.memory=Memory()
b.left_brain=LeftBrain(None)
b.right_brain=RightBrain(load_model=False)
b.right_brain.speak=lambda user_input, logic, memory_data, psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
result=b.run_turn_debug("「ありがとう」は誰の言葉だった？")
contract=result["logic"]["memory_recall_contract"]
assert result["reply"]=="それ、あんたが言ったやつ。前に中国語でお礼を言ってた。",result["reply"]
assert contract["selected_speaker"]=="user",contract
assert contract["final_visible_surface_matches_contract"] is True,contract
assert result["logic"]["semantic_route_m22"]["selected_type"]=="factual_or_memory"
assert result["logic"]["semantic_route_m22"]["performed_route"]=="deterministic_rule_plan"
assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
assert b.runtime.adaptive_person_model["pending_prediction"] is None
graph=collect_cognitive_graph(result)
nodes=[node for node in graph["nodes"] if node["label"]==speaker.LABEL]
assert len(nodes)==1,nodes
assert any(edge["source"]==nodes[0]["id"] or edge["target"]==nodes[0]["id"] for edge in graph["edges"])
node_text=json.dumps(nodes[0],ensure_ascii=False)
assert "謝謝。不過現在請幫我想一個做法。" not in node_text,node_text
assert not speaker.install_speaker_attribution_recall_p2()
print(json.dumps({"reply":result["reply"],"route":"factual_or_memory","model_call":False,"pending":None,"node":nodes[0]["label"]},ensure_ascii=False))
'''
    env = {**os.environ, "P2_SPEAKER_ROOT": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert speaker.LABEL in completed.stdout
