"""P4-BD pre-call contract tests. No model or product-runtime requests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import p4_bd_role_aware_scoring as scoring
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_bd_role_aware_evidence_v1.json"


def _load():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    candidates = json.loads((ROOT / contract["annotation_candidate_projection"]["path"]).read_text(encoding="utf-8"))
    proxy = json.loads((ROOT / contract["annotation_proxy_decisions"]["path"]).read_text(encoding="utf-8"))
    return contract, dataset, candidates, proxy


def test_p4_bd_inputs_and_old_prompt_compiler_runner_are_hash_bound():
    contract, dataset, candidates, proxy = _load()
    for label in (
        "dataset", "annotation_candidate_projection", "annotation_proxy_decisions",
        "span_scorer", "prompt", "downstream_compiler", "read_only_p4_bc_runner",
    ):
        record = contract[label]
        assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
    assert contract["status"] == "prospectively_frozen_before_model_execution"
    assert dataset["status"] == "sealed_before_model_execution"
    assert candidates["status"] == "sealed_before_model_execution"
    assert proxy["status"] == "pre_freeze_development_review"
    assert dataset["development_only"] is True
    assert dataset["reuse_policy"]["may_be_called_holdout"] is False


def test_p4_bd_new_cases_preserve_six_templates_three_languages_and_eight_controls():
    contract, dataset, _candidates, _proxy = _load()
    positives = dataset["positive_cases"]
    controls = dataset["control_cases"]
    assert len(positives) == 6
    assert len(controls) == 8
    assert {row["language"] for row in positives} == {"zh-TW", "en", "ja"}
    assert {row["expected_spec"]["template_id"] for row in positives} == set(compiler.TEMPLATE_CONTRACTS)
    assert {row["expected_unavailable_reason"] for row in controls} == set(dataset["reason_vocabulary"])
    assert len({row["source"]["text"] for row in positives + controls}) == 14
    exposed = set()
    for name in ("p4_bb_typed_action_compiler_v1.json", "p4_bc_raw_dialogue_typed_spec_v1.json"):
        old = json.loads((ROOT / "datasets" / name).read_text(encoding="utf-8"))
        exposed.update(row["source"]["text"] for row in old["positive_cases"])
        exposed.update(row["source"]["text"] for row in old.get("control_cases", []) if "source" in row)
    assert {row["source"]["text"] for row in positives + controls}.isdisjoint(exposed)
    assert contract["models"] == ["qwen3.5:9b", "qwen3.5:4b"]


def test_p4_bd_role_annotations_are_exact_consensus_and_hard_negative_mutants_compile_but_fail_score():
    _contract, dataset, candidates, proxy = _load()
    by_candidate = {(row["case_id"], row["role"]): row for row in candidates["rows"]}
    by_proxy = {(row["case_id"], row["role"]): row for row in proxy["rows"]}
    assert len(by_candidate) == len(by_proxy) == 18
    compiled_negatives = 0
    multi_accept_roles = 0
    for case in dataset["positive_cases"]:
        source = case["source"]
        gold = case["expected_spec"]
        assert gold["source_id"] == source["id"]
        assert gold["source_span"] == source["text"]
        assert [atom["role"] for atom in gold["evidence_atoms"]] == {
            "blank_work_three_headings": ["task_object", "state", "request"],
            "binary_rule_two_piles": ["task_object", "rule", "completion"],
            "extract_one_by_named_rule": ["task_object", "selection_rule", "completion"],
            "verify_one_named_condition": ["task_object", "condition", "limit"],
            "close_one_named_obstacle": ["task_object", "obstacle", "limit"],
            "write_one_atomic_value": ["task_object", "value", "limit"],
        }[gold["template_id"]]
        plan, trace = compiler.compile_typed_action_p4_bb(source, gold)
        assert plan is not None and trace["status"] == "compiled"
        assert scoring.score_packet(case, gold, gold["evidence_atoms"])["role_aware_packet_exact"]
        for index, atom in enumerate(gold["evidence_atoms"]):
            role = atom["role"]
            annotation = case["role_annotations"][role]
            projection = by_candidate[(case["case_id"], role)]
            decision = by_proxy[(case["case_id"], role)]
            assert projection["source"] == source["text"]
            id_to_text = {row["id"]: row["text"] for row in projection["candidates"]}
            assert set(id_to_text) == {"A", "B", "C"}
            assert set(id_to_text.values()) == {
                annotation["rule_a_minimal"], annotation["rule_b_context"], annotation["hard_negative"]
            }
            consensus_ids = set(decision["minimal_accept"]) & set(decision["counterfactual_accept"])
            assert consensus_ids == set(decision["consensus_accept"])
            assert set(annotation["accepted_exact_spans"]) == {id_to_text[key] for key in consensus_ids}
            assert 1 <= len(annotation["accepted_exact_spans"]) <= 2
            assert atom["text"] in annotation["accepted_exact_spans"]
            assert annotation["rule_a_minimal"] in annotation["rule_b_context"]
            assert annotation["hard_negative"] not in annotation["accepted_exact_spans"]
            assert all(value in source["text"] for value in id_to_text.values())
            multi_accept_roles += len(annotation["accepted_exact_spans"]) == 2
            mutant = deepcopy(gold)
            mutant["evidence_atoms"][index]["text"] = annotation["hard_negative"]
            mutant_plan, mutant_trace = compiler.compile_typed_action_p4_bb(source, mutant)
            assert mutant_plan is not None and mutant_trace["status"] == "compiled"
            assert not scoring.score_packet(case, mutant, mutant["evidence_atoms"])["role_aware_packet_exact"]
            compiled_negatives += 1
    assert compiled_negatives == 18
    assert multi_accept_roles == 8


def test_p4_bd_proxy_counts_and_all_non_span_cost_gates_remain_frozen():
    contract, _dataset, _candidates, proxy = _load()
    labels = 0
    agreements = 0
    full_roles = 0
    disputed = []
    for row in proxy["rows"]:
        full_roles += row["minimal_accept"] == row["counterfactual_accept"]
        for candidate_id in "ABC":
            labels += 1
            same = (candidate_id in row["minimal_accept"]) == (candidate_id in row["counterfactual_accept"])
            agreements += same
            if not same:
                disputed.append(f"{row['case_id']}:{row['role']}:{candidate_id}")
    assert (labels, agreements, full_roles) == (54, 48, 12)
    assert disputed == proxy["disagreements"]
    assert contract["role_aware_scoring"]["hard_negative_mutants_must_fail"] == 18
    assert contract["role_aware_scoring"]["strict_single_gold_exact_reported_alongside"] is True
    assert contract["role_aware_scoring"]["strict_single_gold_exact_is_eligibility_gate"] is False
    constants = contract["controlled_constants"]
    assert (constants["temperature"], constants["seed"], constants["num_ctx"], constants["num_predict"]) == (0, 20260927, 4096, 480)
    assert constants["retry_count"] == 0
    assert contract["execution"]["max_scored_calls"] == 28
    assert contract["execution"]["single_call_latency_target_seconds"] == 20
    gates = contract["formal_gates_per_model"]
    assert gates["positive_role_aware_packet_count"] == 6
    assert gates["positive_role_aware_evidence_count"] == 6
    assert gates["positive_non_span_exact_count"] == 6
    assert gates["positive_downstream_compiled_count"] == 6
    assert gates["control_unavailable_count"] == gates["control_reason_exact_count"] == 8
    assert gates["maximum_call_seconds"] == 20
