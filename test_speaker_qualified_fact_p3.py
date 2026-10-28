"""Developer regressions for bounded speaker-qualified fact recall."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import uruha_speaker_qualified_fact_p3 as fact


def memory_item(user, *, memory_id="episode-1", score=0.9, selected=True):
    return {
        "selected": selected,
        "text": f"User: {user} | Summary: bounded test | Uruha: うん。 | Mood: neutral",
        "memory_id": memory_id,
        "trace_id": f"stored:episode:{memory_id}",
        "source": "episode",
        "score": score,
    }


@pytest.mark.parametrize(
    ("text", "fact_kind"),
    [
        ("What kind of cups did I say I prefer?", "first_person_preference_recall"),
        ("我之前說我喜歡哪種茶？", "first_person_preference_recall"),
        ("前にどんなマグカップが好きって言ったっけ？", "first_person_preference_recall"),
    ],
)
def test_explicit_multilingual_fact_acts_are_classified_without_raw_text(text, fact_kind):
    result = fact.classify_speaker_qualified_fact_p3(text)
    serialized = json.dumps(result, ensure_ascii=False)
    assert result["selected"] is True
    assert result["fact_kind"] == fact_kind
    assert result["raw_dialogue_persisted"] is False
    assert text not in serialized


@pytest.mark.parametrize(
    "text",
    [
        "What does 'prefer' mean?",
        "Translate: what kind of cups?",
        "Mina said she prefers blue mugs.",
        "Which cups does Mina prefer?",
        "我朋友喜歡哪種茶？",
        "ミナはどんなマグカップが好き？",
        "The market plan was Mina's, not mine.",
        "夜市計畫是朋友的，不是我的。",
        "旅行の予定は友達の予定で、私のじゃない。",
        "That one was nice.",
    ],
)
def test_metalinguistic_third_party_and_implicit_inputs_do_not_select(text):
    result = fact.classify_speaker_qualified_fact_p3(text)
    assert result["selected"] is False
    assert result["status"] == "not_selected"


@pytest.mark.parametrize(
    ("query", "user_memory", "expected"),
    [
        (
            "What kind of coffee did I say I prefer?",
            "Rin likes milk tea. I said I prefer black coffee.",
            "あんたが好みって言ってたのはブラックコーヒー。",
        ),
        (
            "我之前說我喜歡哪種茶？",
            "朋友喜歡奶茶。我說我喜歡無糖茶。",
            "あんたが好みって言ってたのは無糖のお茶。",
        ),
        (
            "前にどんなマグカップが好きって言ったっけ？",
            "友達は青いコップが好き。私は陶器のマグカップが好き。",
            "あんたが好みって言ってたのは陶器のマグカップ。",
        ),
    ],
)
def test_unique_first_person_preference_uses_only_selected_speaker_evidence(query, user_memory, expected):
    contract = fact.build_speaker_qualified_fact_contract_p3(
        query,
        {"working_memory_items": [memory_item(user_memory)]},
    )
    assert contract["status"] == "resolved_unique_user_preference"
    assert contract["selected_speaker"] == "user"
    assert contract["selected_core_jp"] == expected
    assert contract["candidates"][0]["trace_id"] == "stored:episode:episode-1"
    assert contract["fact_memory_write_count"] == 0
    serialized = json.dumps(contract, ensure_ascii=False)
    assert user_memory not in serialized
    assert query not in serialized


def test_missing_third_party_only_and_unselected_evidence_abstain_without_guessing():
    third_party = fact.build_speaker_qualified_fact_contract_p3(
        "What kind of coffee did I say I prefer?",
        {"working_memory_items": [memory_item("Mina said she prefers black coffee.")]},
    )
    unselected = fact.build_speaker_qualified_fact_contract_p3(
        "What kind of coffee did I say I prefer?",
        {"working_memory_items": [memory_item("I said I prefer black coffee.", selected=False)]},
    )
    japanese_third_party = fact.build_speaker_qualified_fact_contract_p3(
        "前にどんなマグカップが好きって言ったっけ？",
        {"working_memory_items": [memory_item("ミナは陶器のマグカップが好き。")]},
    )
    for contract in (third_party, unselected, japanese_third_party):
        assert contract["status"] == "not_found_in_selected_memory"
        assert contract["selected_speaker"] is None
        assert contract["candidate_count"] == 0
        assert contract["selected_core_jp"] == "その好み、今の記憶からは確認できない。"


def test_multiple_matching_user_preferences_abstain_and_unsupported_value_is_not_echoed():
    ambiguous = fact.build_speaker_qualified_fact_contract_p3(
        "What kind of tea did I say I prefer?",
        {
            "working_memory_items": [
                memory_item("I said I prefer herbal tea.", memory_id="a", score=0.9),
                memory_item("I said I prefer black tea.", memory_id="b", score=0.8),
            ]
        },
    )
    unsupported = fact.build_speaker_qualified_fact_contract_p3(
        "What kind of juice did I say I prefer?",
        {"working_memory_items": [memory_item("I said I prefer cloudberry juice.")]},
    )
    assert ambiguous["status"] == "ambiguous_multiple_user_preferences"
    assert ambiguous["selected_core_jp"] == "候補が二つある。どっちの好みの話？"
    assert unsupported["status"] == "unsupported_value_localization"
    assert "cloudberry" not in json.dumps(unsupported, ensure_ascii=False)


def test_rule_plan_delegates_nonmatch_and_visible_authority_never_overrides_safety():
    original_plan, original_guard = fact._ORIGINAL_RULE_PLAN, fact._ORIGINAL_VISIBLE_GUARD
    sentinel = {"intent": "legacy", "core_message_jp": "そのまま。"}

    def legacy_plan(_self, _text, _psyche, _memory=None):
        return deepcopy(sentinel)

    def legacy_guard(_self, reply, logic, **_kwargs):
        logic["visible_language_guard"] = {"final_reply": reply}
        return reply

    contract = fact.build_speaker_qualified_fact_contract_p3(
        "What kind of coffee did I say I prefer?",
        {"working_memory_items": [memory_item("I said I prefer black coffee.")]},
    )
    try:
        fact._ORIGINAL_RULE_PLAN = legacy_plan
        fact._ORIGINAL_VISIBLE_GUARD = legacy_guard
        planned = fact.rule_plan_with_speaker_qualified_fact_p3(
            object(),
            "What kind of coffee did I say I prefer?",
            {},
            {"working_memory_items": [memory_item("I said I prefer black coffee.")]},
        )
        delegated = fact.rule_plan_with_speaker_qualified_fact_p3(object(), "今日は雨。", {}, {})
        logic = {"memory_recall_contract": deepcopy(contract)}
        visible = fact.visible_guard_with_speaker_qualified_fact_p3(object(), "壊れた候補。", logic)
        protected = {
            "memory_recall_contract": deepcopy(contract),
            "semantic_route_m22": {"selected_type": "safety_sensitive"},
        }
        protected_visible = fact.visible_guard_with_speaker_qualified_fact_p3(
            object(), "安全側の返答。", protected
        )
    finally:
        fact._ORIGINAL_RULE_PLAN = original_plan
        fact._ORIGINAL_VISIBLE_GUARD = original_guard
    assert planned["intent"] == "speaker_qualified_fact_recall"
    assert planned["core_message_jp"] == contract["selected_core_jp"]
    assert delegated == sentinel
    assert visible == contract["selected_core_jp"]
    assert logic["memory_recall_contract"]["final_visible_surface_matches_contract"] is True
    assert protected_visible == "安全側の返答。"


def test_graph_node_is_idempotent_ordered_and_raw_free():
    contract = fact.build_speaker_qualified_fact_contract_p3(
        "What kind of coffee did I say I prefer?",
        {"working_memory_items": [memory_item("I said I prefer black coffee.")]},
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
    fact.materialize_speaker_qualified_fact_p3(result)
    fact.materialize_speaker_qualified_fact_p3(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(fact.LABEL) == 1
    assert labels.index("working_memory") < labels.index(fact.LABEL) < labels.index("selected_plan")
    assert "I said I prefer" not in json.dumps(result["runtime_trace"][fact.LABEL], ensure_ascii=False)


def test_product_install_path_routes_selected_fact_to_japanese_surface_and_graph(tmp_path):
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P3_FACT_ROOT"])
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
import uruha_speaker_qualified_fact_p3 as fact
class Memory(_FakeMemory):
    def query_all_layers(self, text):
        result=super().query_all_layers(text)
        result["working_memory_items"]=[{
            "selected": True,
            "text": "User: Taro said he likes red bowls. I said I prefer black coffee. | Summary: bounded | Uruha: うん。 | Mood: neutral",
            "memory_id": "episode-source-disjoint",
            "trace_id": "stored:episode:episode-source-disjoint",
            "source": "episode",
            "score": 0.93,
        }]
        return result
b=_IsolatedContractBrain()
b.memory=Memory()
b.left_brain=LeftBrain(None)
b.right_brain=RightBrain(load_model=False)
b.right_brain.speak=lambda user_input, logic, memory_data, psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
result=b.run_turn_debug("What kind of coffee did I say I prefer?")
contract=result["logic"]["memory_recall_contract"]
assert result["reply"]=="あんたが好みって言ってたのはブラックコーヒー。",result["reply"]
assert contract["status"]=="resolved_unique_user_preference",contract
assert contract["final_visible_surface_matches_contract"] is True,contract
assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
graph=collect_cognitive_graph(result)
nodes=[node for node in graph["nodes"] if node["label"]==fact.LABEL]
assert len(nodes)==1,nodes
assert any(edge["source"]==nodes[0]["id"] or edge["target"]==nodes[0]["id"] for edge in graph["edges"])
assert "I said I prefer" not in json.dumps(nodes[0],ensure_ascii=False)
owner=b.run_turn_debug("The hiking plan was Taro's, not mine—keep that straight.")
assert owner["reply"]=="ハイキング計画はタロウのもので、うちのものではないんだね。",owner["reply"]
assert owner["logic"].get("memory_recall_contract") is None
assert owner["logic"]["bounded_slow_path_m21"]["route"]=="semantic_commit_repair_m32"
assert owner["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
assert not fact.install_speaker_qualified_fact_p3()
print(json.dumps({"recall":result["reply"],"owner":owner["reply"],"node":nodes[0]["label"]},ensure_ascii=False))
'''
    env = {**os.environ, "P3_FACT_ROOT": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent,
        timeout=90,
    )
    assert fact.LABEL in completed.stdout
