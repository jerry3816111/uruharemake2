"""One-shot typed-feedback comparison, distinct from model or human evaluation."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import time

from uruha_supported_feedback_closure_m43 import (
    _BASE_BUILD, _BASE_APPLY, LABEL_M43, build_feedback_closure_m43,
    apply_feedback_closure_m43, close_linked_validation_m43,
)

ROOT = Path(__file__).resolve().parent
CATEGORIES = {"pure_support","support_with_new_content","ordinary_statement","quotation_or_negation",
              "unverified","protected","unresolved_question"}


def validate_reserve_m43(dataset):
    cases=dataset.get("cases") or []
    if not cases or len({c.get("id") for c in cases})!=len(cases) or len({c.get("input") for c in cases})!=len(cases):
        raise ValueError("empty or duplicate cases")
    if {c.get("category") for c in cases}!=CATEGORIES:
        raise ValueError("category coverage mismatch")
    for c in cases:
        if (not c.get("id") or not c.get("input") or c.get("language") not in {"zh","en","ja"}
                or c.get("feedback") not in {"supported_linked","uncertain_linked","supported_unlinked"}
                or c.get("plan") not in {"normal","crisis","factual_memory"}
                or c.get("pending") not in {"linked","none","unrelated"}
                or not isinstance(c.get("expected_authority"),bool) or not isinstance(c.get("expected_closed"),bool)):
            raise ValueError("invalid case")
    return {"case_count":len(cases),"category_counts":dict(Counter(c["category"] for c in cases)),
            "language_counts":dict(Counter(c["language"] for c in cases))}


def controlled_inputs_m43(case):
    feedback={"status":"uncertain" if case["feedback"]=="uncertain_linked" else "supported",
              "previous_prediction_id":"controlled-prediction-1","previous_policy_id":"calibrate_need",
              "feedback_linked_to_previous_prediction":case["feedback"]!="supported_unlinked",
              "causal_outcome_calibration_m27":{"status":"resolved_unknown_excluded" if case["feedback"]=="uncertain_linked" else "resolved_decisive"}}
    plan={"intent":"chat","scene":"casual","core_message_jp":"うん。"}
    if case["plan"]=="crisis":
        plan.update(intent="crisis_support",scene="crisis",core_message_jp="一人で抱えないで。")
    elif case["plan"]=="factual_memory":
        plan.update(intent="recall_fact",memory_recall_contract={"grounded":True},core_message_jp="青だったよ。")
    pending=None if case["pending"]=="none" else {
        "validation_id":"controlled-val-1","model_item_id":"controlled-unknown-1","status":"pending",
        "asked_turn":1,"response_binding_verified_m43":True,
        "response_prediction_id_m43":"controlled-prediction-1" if case["pending"]=="linked" else "unrelated-prediction"}
    model={"active_validation":{"pending":pending,"history":[]},
           "layers":{"stable":[],"provisional":[{"value":"unknown","confidence":0.3}]}}
    return feedback,plan,model


def evaluate_reserve_m43(dataset,protocol):
    validation=validate_reserve_m43(dataset)
    rows=[]
    for case in dataset["cases"]:
        feedback,plan,model=controlled_inputs_m43(case)
        feedback_before=deepcopy(feedback)
        _,old=_BASE_APPLY(plan,_BASE_BUILD(case["input"],feedback,{}))
        start=time.perf_counter()
        new_plan,new=apply_feedback_closure_m43(plan,build_feedback_closure_m43(case["input"],feedback,{}))
        trace=new[LABEL_M43]
        state,audit=close_linked_validation_m43(model,trace,2)
        elapsed=time.perf_counter()-start
        baseline=bool(old.get("surface_authority") and old.get("plan_applied"))
        system=bool(trace.get("authoritative"))
        rows.append({**case,"baseline_authority":baseline,"system_authority":system,
                     "baseline_correct":baseline==case["expected_authority"],
                     "system_correct":system==case["expected_authority"],
                     "system_closed":bool(audit["closed_count"]),"closure_correct":bool(audit["closed_count"])==case["expected_closed"],
                     "pending_preserved":state["active_validation"]["pending"]==model["active_validation"]["pending"],
                     "upstream_unchanged":feedback==feedback_before,"model_facts_unchanged":state["layers"]==model["layers"],
                     "plan_fields_preserved":all(new_plan[k]==v for k,v in plan.items()),
                     "trace":trace,"validation":audit,"added_seconds":elapsed,
                     "raw_trace_contains_input":case["input"] in json.dumps(trace,ensure_ascii=False)})
    rate=lambda rr,f:sum(bool(f(r)) for r in rr)/len(rr) if rr else 0.0
    subset=lambda key,value:[r for r in rows if r[key]==value]
    latency=sorted(r["added_seconds"] for r in rows)
    metrics={
        "case_count":len(rows),"baseline_authority_accuracy":rate(rows,lambda r:r["baseline_correct"]),
        "authority_accuracy":rate(rows,lambda r:r["system_correct"]),
        "pure_support_recall":rate(subset("category","pure_support"),lambda r:r["system_authority"]),
        "non_support_false_authority":rate(subset("expected_authority",False),lambda r:r["system_authority"]),
        "precise_pending_closure_accuracy":rate(rows,lambda r:r["closure_correct"]),
        "unrelated_pending_preservation":rate(subset("pending","unrelated"),lambda r:r["pending_preserved"]),
        "upstream_outcome_invariance":rate(rows,lambda r:r["upstream_unchanged"]),
        "protected_plan_invariance":rate(subset("category","protected"),lambda r:r["plan_fields_preserved"]),
        "raw_trace_write_count":sum(r["raw_trace_contains_input"] or r["trace"]["raw_dialogue_persisted"] for r in rows),
        "mental_fact_write_count":sum(r["trace"]["mental_fact_write_count"] or not r["model_facts_unchanged"] for r in rows),
        "model_call_count":sum(r["trace"]["model_call_count"] for r in rows),
        "median_added_seconds":statistics.median(latency),
        "p95_added_seconds":latency[min(len(latency)-1,int(len(latency)*0.95))],
    }
    gates={}
    for key,threshold in protocol["gates"].items():
        name,direction=key.rsplit("_",1);value=metrics[name]
        gates[key]={"observed":value,"threshold":threshold,"passed":value>=threshold if direction=="min" else value<=threshold}
    return {"schema":"uruha_m43_supported_feedback_result_v1","validation":validation,"metrics":metrics,"gates":gates,
            "decision":"pass_all_frozen_gates" if all(g["passed"] for g in gates.values()) else "fail_one_or_more_frozen_gates",
            "rows":rows,"evidence_type":"researcher-authored controlled typed-feedback mechanism, not independent holdout",
            "claim_boundary":protocol["evidence_boundary"]}


def frozen_integrity_m43(path):
    freeze=json.loads(Path(path).read_text())
    bad=[p for p,h in freeze["frozen_files"].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if bad:
        raise RuntimeError(f"frozen file mismatch: {bad}")
    return len(freeze["frozen_files"])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--freeze",required=True);parser.add_argument("--output",required=True)
    args=parser.parse_args()
    if Path(args.output).exists():
        raise FileExistsError("Refusing formal evidence overwrite/rerun")
    count=frozen_integrity_m43(args.freeze)
    dataset=ROOT/"datasets/m43_supported_feedback_closure_reserve_v1.json"
    protocol=ROOT/"research/m43_supported_feedback_closure_protocol_v1.json"
    result=evaluate_reserve_m43(json.loads(dataset.read_text()),json.loads(protocol.read_text()))
    result["provenance"]={"formal_run_index":1,"frozen_file_count_verified":count,
                          "dataset_sha256":hashlib.sha256(dataset.read_bytes()).hexdigest(),
                          "protocol_sha256":hashlib.sha256(protocol.read_bytes()).hexdigest(),
                          "implementation_freeze_sha256":hashlib.sha256(Path(args.freeze).read_bytes()).hexdigest()}
    with Path(args.output).open("x",encoding="utf-8") as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write("\n")
    print(json.dumps({"decision":result["decision"],"metrics":result["metrics"]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
