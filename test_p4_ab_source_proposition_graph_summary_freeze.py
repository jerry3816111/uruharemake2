from p4_ab_source_proposition_graph_summary_gate import load_contract, load_dataset
from uruha_memory_observatory import _graph_signal


def test_p4_ab_contract_is_bound_and_presentation_only():
    contract = load_contract()
    dataset = load_dataset(contract)
    assert dataset["status"] == "prospectively_frozen_before_implementation"
    assert len(dataset["cases"]) == 4
    assert contract["change_policy"] == {
        "visible_reply_change_allowed": False,
        "p4_z_logic_change_allowed": False,
        "trace_detail_change_allowed": False,
        "model_call_allowed": False,
        "memory_write_allowed": False,
        "raw_source_or_reply_in_summary_allowed": False,
    }


def test_p4_ab_before_evidence_is_bound_to_generic_field_counts():
    contract = load_contract()
    dataset = load_dataset(contract)
    assert contract["implementation_target"]["before_sha256"] == (
        "c95e756a6e8b03cbe79cef079f62bf2cecf93dd98cc3290a2ae178139e9c4b76"
    )
    recorded_before = [f"{len(row['payload'])} fields" for row in dataset["cases"]]
    assert recorded_before == ["18 fields"] * 4
    assert all(signal != row["expected_signal"] for signal, row in zip(recorded_before, dataset["cases"]))


def test_p4_ab_frozen_summaries_are_bounded_and_raw_free():
    dataset = load_dataset(load_contract())
    for row in dataset["cases"]:
        assert len(row["expected_signal"]) <= 42
        assert "digest-" not in row["expected_signal"]
        assert "source" not in row["expected_signal"].lower()
        assert "reply" not in row["expected_signal"].lower()


def test_p4_ab_unrelated_control_preserves_existing_generic_behavior():
    dataset = load_dataset(load_contract())
    control = dataset["unrelated_control"]
    assert _graph_signal(control["payload"]) == control["expected_signal"]
