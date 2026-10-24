"""Zero-model-call prospective freeze checks for the P4 topology comparison."""

from collections import Counter
from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import pytest

import p4_action_transaction_scoring as tx
import uruha_task_evidence_authorization_m45_1 as task_gate
import uruha_actionable_help_delivery_m45 as m45
import uruha_semantic_persona_surface_m39 as m39


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs/p4_action_transaction_v1.json"
EXPOSED_P4_DATASETS = (
    "datasets/p4_m46_decision_interface_v1.json",
    "datasets/p4_m46_reviewer_necessity_v1.json",
    "datasets/p4_be_role_value_prompt_v1.json",
    "datasets/p4_bd_role_aware_evidence_v1.json",
    "datasets/p4_bc_raw_dialogue_typed_spec_v1.json",
    "datasets/p4_ba_stage_model_allocation_v1.json",
    "datasets/p4_az_real_previous_turn_ellipsis_to_action_delivery_v1.json",
    "datasets/p4_az_previous_turn_cjk_ellipsis_authority_v1.json",
)


def _load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def _contract():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    sources = _load(config["dataset"]["sources"]["path"])
    gold = _load(config["dataset"]["gold"]["path"])
    return config, sources, gold


def _ordered_gold(sources, gold):
    cases = sources["cases"]
    indexed = gold["gold_by_case_id"]
    assert set(indexed) == {case["case_id"] for case in cases}
    return [indexed[case["case_id"]] for case in cases]


def _prior_source_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "raw_user_input", "source_span", "span"} and isinstance(item, str):
                yield item
            yield from _prior_source_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _prior_source_strings(item)


def test_model_freeze_binds_dependencies_resources_and_gate():
    config, _, _ = _contract()
    assert config["version"] == "1.0.1"
    assert config["status"] == "prospectively_amended_after_prewarm_only_zero_scored_calls"
    assert config["execution"]["raw_result_path"] == (
        "analysis/p4_action_transaction_v1_amend1_raw_2026-10-01.json")
    assert config["single_variable"] == "decision_topology_two_candidates_two_calls_vs_one_source_bound_transaction"
    for record in [config["plan"], config["dataset"]["sources"],
                   config["dataset"]["gold"], *config["hash_bound_dependencies"].values()]:
        assert _sha(record["path"]) == record["sha256"]
    assert config["model"] == "qwen3.5:9b"
    assert config["model_digest"] == "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    assert config["hardware"] == "Apple M2 Pro 12-core 32GB"
    common = config["controlled_constants"]
    assert (common["temperature"], common["num_ctx"], common["retry_count"]) == (0, 4096, 0)
    assert common["stream"] is common["think"] is False
    assert version("jsonschema") == common["offline_jsonschema_version"]
    assert common["prewarm_once_before_scoring"] is True
    assert common["prewarm_counted_as_case_latency"] is False
    assert config["arms"]["A"]["generator"] == {"seed": 20260830, "num_predict": 360}
    assert config["arms"]["A"]["reviewer"] == {"seed": 20260829, "num_predict": 320}
    assert config["arms"]["B"]["transaction"]["seed"] == 20260830
    assert 0 < config["arms"]["B"]["transaction"]["num_predict"] <= 680
    assert config["execution"]["maximum_scored_calls"] == 54
    assert config["execution"]["generation_reads_gold"] is False
    assert config["execution"]["A_observation_recomputed_from_raw_stages"] is True
    assert config["execution"]["B_observation_recomputed_from_raw_json"] is True
    assert config["execution"]["B_observation_requires_raw_stage_and_transport_record"] is True
    assert config["execution"]["all_18_by_2_raw_observations_bound_to_one_commit"] is True
    assert config["execution"]["A_legacy_reason_proxy_separate_from_common_abstain_gate"] is True
    assert config["execution"]["blind_adjudication_requires_raw_commit_and_digest_binding"] is True
    assert config["execution"]["formal_score_requires_frozen_case_order_and_source_gold_digests"] is True
    assert config["execution"]["fixed_component_policy_fixture"] == tx.FIXED_COMPONENT_LOGIC
    assert config["execution"]["product_policy_route_for_these_cases_verified"] is False
    assert config["execution"]["m45_1_excluded_clause_count_on_18_cases"] == 0
    assert config["execution"]["raw_outputs_locked_before_gold_scoring"] is True
    assert config["execution"]["product_runtime_changed"] is False
    gates = config["preregistered_gates"]
    assert gates["valid_action_delivered"] == 9
    assert gates["invalid_abstained"] == 9
    assert gates["invalid_false_action"] == 0
    assert gates["B_invalid_reason_source_bound"] == 9
    assert gates["parse_source_token_complete"] == 18
    assert gates["retry_count"] == 0
    assert gates["each_full_turn_max_seconds"] == 20
    assert gates["B_product_eligible_from_component_only"] is False


def test_prewarm_only_amendment_changes_no_case_gold_model_or_gate():
    config, _, _ = _contract()
    old = json.loads(subprocess.check_output(
        ["git", "show", "8b5e7a8972b27402342596d5fe18064795b7a452:"
         "configs/p4_action_transaction_v1.json"], cwd=ROOT))
    amendment = config["prewarm_amendment"]
    assert amendment == {
        "prior_failure_commit": "216f16b535bac5fbcfb73532facf61951a756b67",
        "prior_raw_path": "analysis/p4_action_transaction_v1_raw_2026-09-30.json",
        "prior_scored_calls": 0,
        "allowed_change": "accept_complete_load_only_prewarm_without_duration_pair_and_use_new_raw_path",
    }
    prior_raw = ROOT / amendment["prior_raw_path"]
    assert hashlib.sha256(prior_raw.read_bytes()).hexdigest() == (
        "6700d9a14a5a46fcdf08d9bc788c754ae54c1626ebf7141cecf940128b3da11b")
    failure = json.loads(prior_raw.read_text(encoding="utf-8"))
    assert failure["status"] == "prewarm_failed_no_scored_calls"
    assert failure["scored_calls_started"] == 0 and failure["cases"] == []
    assert failure["prewarm"]["ollama_response"]["done_reason"] == "load"
    assert "total_duration" not in failure["prewarm"]["ollama_response"]
    old_comparable = deepcopy(old)
    new_comparable = deepcopy(config)
    for candidate in (old_comparable, new_comparable):
        candidate.pop("version")
        candidate.pop("status")
        candidate.pop("prewarm_amendment", None)
        candidate["plan"].pop("sha256")
        candidate["execution"].pop("raw_result_path")
    assert new_comparable == old_comparable


def test_new_cases_are_balanced_independent_gold_and_authorized_sources():
    config, sources, gold = _contract()
    cases = sources["cases"]
    labels = _ordered_gold(sources, gold)
    assert sources["case_count"] == gold["case_count"] == len(cases) == len(labels) == 18
    assert [row["case_id"] for row in cases] == config["dataset"]["case_order"]
    assert [row["case_id"] for row in labels] == config["dataset"]["case_order"]
    assert len({row["case_id"] for row in cases}) == 18
    assert len({row["sources"][0]["text"] for row in cases}) == 18
    assert Counter(row["language"] for row in cases) == {"zh-TW": 6, "en": 6, "ja": 6}
    assert Counter((case["language"], label["decision"])
                   for case, label in zip(cases, labels)) == {
        (language, decision): 3
        for language in ("zh-TW", "en", "ja") for decision in ("action", "abstain")
    }
    assert "Developer-authored" in sources["annotation_provenance"]
    assert "Developer-authored" in gold["annotation_provenance"]
    assert "not an independent human" in gold["annotation_provenance"]
    excluded_total = 0
    for case, label in zip(cases, labels):
        assert len(case["sources"]) == 1
        original = case["sources"][0]
        assert original["kind"] == "current_user"
        assert 0 < len(original["text"]) <= 2000
        filtered, gate = task_gate.task_sources(case["sources"])
        assert filtered and gate["status"] == "content_available"
        prepared = tx.prepare_source_case(case)
        assert prepared["sources"] == filtered
        assert prepared["raw_user_input"] == original["text"]
        assert prepared["source_gate"] == gate
        excluded_total += len(gate["excluded"])
        assert prepared["policy_fixed_not_product_routed"] is True
        assert m39._selected_policy_m39(prepared["logic"]) == "solve_regulation"
        assert m45._protected(prepared["logic"]) is False
        assert label["case_id"] == case["case_id"]
        assert label["rationale_zh"] and label["content_notes_zh"] and label["japanese_notes_zh"]
        ids = {row["id"] for row in filtered}
        assert set(label["acceptable_task_source_ids"]).issubset(ids)
        for quote in label["task_target_quotes"]:
            assert any(quote and row["id"] in label["acceptable_task_source_ids"]
                       and quote in row["text"] for row in filtered)
        forbidden = label["forbidden"]
        if forbidden is not None:
            source = next(row for row in filtered if row["id"] == forbidden["source_id"])
            assert all(quote and quote in source["text"] for quote in forbidden["quotes"])
        if label["decision"] == "action":
            assert label["acceptable_task_source_ids"] and label["task_target_quotes"]
            assert label["expected_reason_code"] == "none"
        else:
            assert label["expected_reason_code"] in set(tx.REASON_CODES) - {"none"}
            assert label["actor_expected"] is None
    assert excluded_total == config["execution"]["m45_1_excluded_clause_count_on_18_cases"]


def test_generation_payload_and_prompt_cannot_include_gold_or_case_metadata():
    _, sources, gold = _contract()
    for case, label in zip(sources["cases"], _ordered_gold(sources, gold)):
        filtered = tx.prepare_source_case(case)["sources"]
        payload = tx.transaction_payload(filtered)
        schema = tx.transaction_schema(filtered)
        assert set(payload) == {"user_sources"}
        assert payload["user_sources"] == [
            {"id": row["id"], "kind": row["kind"], "text": row["text"]}
            for row in filtered
        ]
        assert set(schema["properties"]) == set(tx.TRANSACTION_FIELDS)
        serialized = json.dumps(payload, ensure_ascii=False)
        assert case["case_id"] not in serialized
        assert "rationale_zh" not in serialized and "expected_reason_code" not in serialized
        assert label["content_notes_zh"] not in serialized
        assert case["sources"][0]["text"] not in tx.TRANSACTION_SYSTEM


def test_new_full_sources_are_not_exact_replays_of_exposed_p4_sources():
    _, sources, _ = _contract()
    exposed = set()
    for path in EXPOSED_P4_DATASETS:
        exposed.update(_prior_source_strings(_load(path)))
    assert all(case["sources"][0]["text"] not in exposed
               for case in sources["cases"])


def test_product_source_overlay_cannot_silently_change_frozen_clause_ids(monkeypatch):
    _, sources, _ = _contract()
    original = task_gate.task_sources

    def patched(sources):
        return original(sources)

    monkeypatch.setattr(task_gate, "task_sources", patched)
    with pytest.raises(RuntimeError, match="isolated M45.1"):
        tx.prepare_source_case(sources["cases"][0])
