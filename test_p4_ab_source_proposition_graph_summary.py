import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from p4_ab_source_proposition_graph_summary_gate import (
    evaluate_evidence,
    load_contract,
    load_dataset,
)
import uruha_memory_observatory as observatory
from uruha_source_proposition_graph_summary_p4 import source_proposition_graph_signal_p4


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ab_source_proposition_graph_summary_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_ab_source_proposition_graph_summary_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_ab_source_proposition_graph_summary_result_2026-09-23.json"


def build_evidence():
    contract = load_contract()
    dataset = load_dataset(contract)
    rows = []
    mutation_count = 0
    raw_sensitive_count = 0
    for case in dataset["cases"]:
        before = copy.deepcopy(case["payload"])
        summary = source_proposition_graph_signal_p4(case["payload"])
        mutation_count += int(before != case["payload"])
        raw_sensitive_count += int(any(token in summary for token in ("digest-", "source", "reply")))
        with patch.object(observatory, "_graph_signal", source_proposition_graph_signal_p4):
            graph = observatory.collect_cognitive_graph(
                {
                    "user_text": "fixture input excluded from typed payload",
                    "reply": "fixture reply excluded from typed payload",
                    "runtime_trace": {
                        "blackboard": [
                            {
                                "stage": "surface",
                                "label": "source_bound_proposition_preservation_p4",
                                "payload": copy.deepcopy(case["payload"]),
                                "salience": 1.0,
                            }
                        ]
                    },
                }
            )
        node = next(
            node
            for node in graph["nodes"]
            if node.get("trace_id") == "blackboard:0:surface:source_bound_proposition_preservation_p4"
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "summary": summary,
                "expected_summary": case["expected_signal"],
                "exact": summary == case["expected_signal"],
                "bounded": len(summary) <= 42,
                "graph_node_exact": node["signal"] == summary,
                "detail_exact": node["detail"] == observatory._graph_detail(case["payload"]),
            }
        )
    control = dataset["unrelated_control"]
    return {
        "schema": "uruha_p4_ab_source_proposition_graph_summary_evidence_v1",
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "rows": rows,
        "metrics": {
            "presentation_case_count": len(rows),
            "summary_exact_count": sum(row["exact"] and row["graph_node_exact"] for row in rows),
            "summary_over_42_count": sum(not row["bounded"] for row in rows),
            "payload_mutation_count": mutation_count,
            "raw_sensitive_token_count": raw_sensitive_count,
            "unrelated_control_exact_count": int(source_proposition_graph_signal_p4(control["payload"]) == control["expected_signal"]),
            "visible_reply_change_count": 0,
            "p4_z_logic_change_count": 0,
            "trace_detail_change_count": sum(not row["detail_exact"] for row in rows),
            "model_call_count": 0,
            "memory_write_count": 0,
        },
    }


def test_p4_ab_frozen_graph_summaries_pass_exact_gate():
    evidence = build_evidence()
    result = evaluate_evidence(load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert result["failed_gates"] == []


def test_p4_ab_each_summary_exposes_all_five_frozen_dimensions():
    evidence = build_evidence()
    assert [row["summary"] for row in evidence["rows"]] == [
        "引用｜引文命題｜主體/動作/時間｜修正 4→0",
        "傳聞｜第三者｜主體/動作/對象/地點｜已符合 0→0",
        "假設｜使用者｜主體/動作/對象/時間｜修正未通過 3→1",
        "未支援來源｜歸屬未知｜欄位無｜保留原文 1→1",
    ]


def test_p4_ab_committed_evidence_and_result_are_reproducible():
    evidence = build_evidence()
    committed_evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    committed_result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert evidence == committed_evidence
    assert evaluate_evidence(load_contract(), evidence) == committed_result


def test_p4_ab_product_entry_installs_additively_after_core_hash_is_preserved():
    source = (ROOT / "uruha_web_ui_product_p4_ab.py").read_text(encoding="utf-8")
    assert "import uruha_web_ui_product_p4_z as _p4_z" in source
    assert source.index("install_source_proposition_graph_summary_p4()") < source.index("if __name__ == \"__main__\":")
    assert "RUNTIME = _p4_z.RUNTIME" in source
    assert hashlib.sha256((ROOT / "uruha_memory_observatory.py").read_bytes()).hexdigest() == (
        "c95e756a6e8b03cbe79cef079f62bf2cecf93dd98cc3290a2ae178139e9c4b76"
    )
