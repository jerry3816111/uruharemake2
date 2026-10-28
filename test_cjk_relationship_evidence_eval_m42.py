from copy import deepcopy
import pytest
from uruha_cjk_relationship_evidence_eval_m42 import validate_reserve_m42,CATEGORIES


def fixture():
    return {"cases":[{"id":f"dev{i}","input":f"dev text {i}","language":"ja","category":c,
                     "expected_intent":None,"expected_authorization":"uncertain"}
                    for i,c in enumerate(sorted(CATEGORIES))]}


def test_reserve_validation_is_contract_only_not_formal_run():
    assert validate_reserve_m42(fixture())["case_count"] == 8
    for mode in ["duplicate","category","language","uncertainty"]:
        data=fixture()
        if mode=="duplicate":
            data["cases"].append(deepcopy(data["cases"][0]))
        elif mode=="category":
            data["cases"].pop()
        elif mode=="language":
            data["cases"][0]["language"]="unknown"
        else:
            next(x for x in data["cases"] if x["category"]=="ambiguous").pop("expected_authorization")
        with pytest.raises(ValueError):
            validate_reserve_m42(data)
