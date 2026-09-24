import p4_aj_japanese_morphology_gate as gate


def test_frozen_dataset_and_predecessors_are_bound():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    assert len(dataset["development_cases"]) == 1
    assert len(dataset["fresh_positive_cases"]) == 6
    assert len(dataset["fresh_control_cases"]) == 8


def test_failure_policy_keeps_cases_fixed_and_real_product_blocked():
    policy = gate.load_contract()["failure_policy"]
    assert policy["case_change_allowed"] is False
    assert policy["real_product_authorized"] is False
