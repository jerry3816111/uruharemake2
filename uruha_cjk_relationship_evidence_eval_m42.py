"""One-shot deterministic evidence-gate comparison; never a model/human win."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from uruha_cjk_relationship_evidence_m42 import evaluate_relationship_route_m42

ROOT = Path(__file__).resolve().parent
CATEGORIES = {"compound","third_party_report","quoted_report","negated_request",
              "direct_request","mixed_request","ambiguous","unrelated_preserved"}


def validate_reserve_m42(dataset):
    cases = dataset.get("cases") or []
    if not cases:
        raise ValueError("empty cases")
    if len({c.get("id") for c in cases}) != len(cases) or len({c.get("input") for c in cases}) != len(cases):
        raise ValueError("duplicate case")
    if {c.get("category") for c in cases} != CATEGORIES:
        raise ValueError("category coverage mismatch")
    for c in cases:
        if not c.get("id") or not c.get("input") or c.get("language") not in {"zh","ja","en"} or "expected_intent" not in c:
            raise ValueError("invalid case")
        if c["category"] == "ambiguous" and c.get("expected_authorization") != "uncertain":
            raise ValueError("missing uncertainty label")
    return {"case_count":len(cases),"category_counts":dict(Counter(c["category"] for c in cases)),
            "language_counts":dict(Counter(c["language"] for c in cases))}


def evaluate_reserve_m42(dataset,protocol):
    validation = validate_reserve_m42(dataset)
    rows = []
    for case in dataset["cases"]:
        old,new,trace,_ = evaluate_relationship_route_m42(case["input"])
        before,after = (old or {}).get("intent"),(new or {}).get("intent")
        rows.append({**case,"baseline_intent":before,"system_intent":after,
                     "baseline_correct":before==case["expected_intent"],
                     "system_correct":after==case["expected_intent"],
                     "plan_unchanged":old==new,"trace":trace,
                     "raw_trace_contains_input":case["input"] in json.dumps(trace,ensure_ascii=False)})
    subset = lambda names:[r for r in rows if r["category"] in names]
    rate = lambda rr,f:sum(bool(f(r)) for r in rr)/len(rr) if rr else 0.0
    benign = subset({"compound","third_party_report","quoted_report","negated_request"})
    lat = sorted(r["trace"]["added_seconds"] for r in rows)
    metrics = {
        "case_count":len(rows),
        "baseline_intent_accuracy":rate(rows,lambda r:r["baseline_correct"]),
        "system_intent_accuracy":rate(rows,lambda r:r["system_correct"]),
        "benign_false_boundary_rate":rate(benign,lambda r:r["system_intent"]=="marriage_boundary"),
        "direct_request_recall":rate(subset({"direct_request"}),lambda r:r["system_correct"]),
        "mixed_request_recall":rate(subset({"mixed_request"}),lambda r:r["system_correct"]),
        "ambiguous_uncertainty_accuracy":rate(subset({"ambiguous"}),lambda r:r["system_correct"] and r["trace"]["authorization"]=="uncertain"),
        "unrelated_noninterference":rate(subset({"unrelated_preserved"}),lambda r:r["plan_unchanged"]),
        "raw_trace_write_count":sum(r["raw_trace_contains_input"] or r["trace"]["raw_dialogue_persisted"] for r in rows),
        "mental_fact_write_count":sum(r["trace"]["mental_fact_write_count"] for r in rows),
        "model_call_count":sum(r["trace"]["model_call_count"] for r in rows),
        "median_added_seconds":statistics.median(lat),
        "p95_added_seconds":lat[min(len(lat)-1,int(len(lat)*0.95))],
    }
    gates = {}
    for key,threshold in protocol["gates"].items():
        metric,direction = key.rsplit("_",1)
        value = metrics[metric]
        gates[key] = {"observed":value,"threshold":threshold,"passed":value>=threshold if direction=="min" else value<=threshold}
    return {"schema":"uruha_m42_relationship_evidence_result_v1","validation":validation,
            "decision":"pass_all_frozen_gates" if all(g["passed"] for g in gates.values()) else "fail_one_or_more_frozen_gates",
            "metrics":metrics,"gates":gates,"rows":rows,
            "evidence_type":"researcher-authored deterministic mechanism comparison, not independent holdout or human-rated generation",
            "claim_boundary":protocol["evidence_boundary"]}


def frozen_integrity_m42(path):
    freeze = json.loads(Path(path).read_text())
    bad = [p for p,h in freeze["frozen_files"].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if bad:
        raise RuntimeError(f"frozen file mismatch: {bad}")
    return len(freeze["frozen_files"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze",required=True)
    parser.add_argument("--output",required=True)
    args = parser.parse_args()
    if Path(args.output).exists():
        raise FileExistsError("Refusing formal evidence overwrite/rerun")
    count = frozen_integrity_m42(args.freeze)
    dataset = ROOT/"datasets/m42_cjk_relationship_evidence_reserve_v1.json"
    protocol = ROOT/"research/m42_cjk_relationship_evidence_protocol_v1.json"
    result = evaluate_reserve_m42(json.loads(dataset.read_text()),json.loads(protocol.read_text()))
    result["provenance"] = {"formal_run_index":1,"frozen_file_count_verified":count,
                            "dataset_sha256":hashlib.sha256(dataset.read_bytes()).hexdigest(),
                            "protocol_sha256":hashlib.sha256(protocol.read_bytes()).hexdigest(),
                            "implementation_freeze_sha256":hashlib.sha256(Path(args.freeze).read_bytes()).hexdigest()}
    with Path(args.output).open("x",encoding="utf-8") as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2)
        handle.write("\n")
    print(json.dumps({"decision":result["decision"],"metrics":result["metrics"]},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
