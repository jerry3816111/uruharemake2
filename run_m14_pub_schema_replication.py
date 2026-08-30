#!/usr/bin/env python3
"""Run the M14 schema-enforced replication on disjoint PUB cases."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib import error, request

from longitudinal_human_model.pub_pragmatics import (
    CONDITIONS,
    audit_payload_contract,
    build_prompt,
    deterministic_case_ids,
    json_schema_for_condition,
    materialize_case,
    option_permutation,
    paired_accuracy_comparison,
    parse_answer_index,
    summarize_rows,
)
from longitudinal_human_model.registry import git_snapshot, load_json, runtime_snapshot, sha256_file, write_json_atomic
from run_m13_pub_pragmatics import prepare_sources, render_dashboard


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs/m14_pub_schema_replication_preregistration.json"
MANIFEST_PATH = ROOT / "configs/m14_pub_schema_replication_case_manifest.json"
PROBE_PATH = ROOT / "analysis/local_m14_pub_schema_replication/contract_probe.json"
CHECKPOINT_PATH = ROOT / "analysis/local_m14_pub_schema_replication/checkpoint.json"
RAW_PATH = ROOT / "analysis/m14_pub_schema_replication_raw_result.json"
RESULT_PATH = ROOT / "analysis/m14_pub_schema_replication_result.json"
REPORT_PATH = ROOT / "analysis/m14_pub_schema_replication_report_2026-08-17.md"
DASHBOARD_PATH = ROOT / "analysis/m14_pub_schema_replication_dashboard_2026-08-17.html"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SchemaProvider:
    def __init__(self, endpoint: str, timeout: int = 240):
        self.endpoint = endpoint
        self.timeout = timeout

    def __call__(self, *, model: str, prompt: str, options: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        payload = {"model": model, "prompt": prompt, "stream": False, "think": False, "format": schema, "options": options}
        req = request.Request(self.endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        started = time.perf_counter()
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode())
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama schema request failed: {exc}") from exc
        return {
            "text": body["response"],
            "latency_seconds": time.perf_counter() - started,
            "prompt_tokens": int(body.get("prompt_eval_count") or 0),
            "completion_tokens": int(body.get("eval_count") or 0),
            "model_reported": body.get("model"),
        }


def source_protocol(config: dict[str, Any]) -> dict[str, Any]:
    binding = config["source_protocol"]
    path = ROOT / binding["path"]
    if sha256_file(path) != binding["sha256"]:
        raise ValueError("M14 source protocol hash drift")
    predecessor = config["predecessor"]
    if sha256_file(ROOT / predecessor["result_lock_path"]) != predecessor["result_lock_sha256"]:
        raise ValueError("M13 result lock hash drift")
    return load_json(path)


def prepare_manifest() -> dict[str, Any]:
    config = load_json(CONFIG_PATH)
    protocol = source_protocol(config)
    rows = prepare_sources(protocol)
    sampling = config["sampling"]
    m13 = load_json(ROOT / "configs/m13_pub_pragmatics_case_manifest.json")
    consumed = {case["sample_id"] for case in m13["cases"]}
    cases = []
    for task in protocol["dataset"]["tasks"]:
        task_id = int(task["task_id"])
        by_id = {str(row["id"]): row for row in rows[task_id]}
        ids = deterministic_case_ids(
            rows[task_id], task_id=task_id, count=int(sampling["items_per_task"]),
            seed=sampling["seed"], excluded_ids=set(sampling["excluded_ids"]),
            offset=int(sampling["rank_offset_per_task"]),
        )
        for item_id in ids:
            row = by_id[item_id]
            cases.append({
                "sample_id": f"PUB-T{task_id}-{item_id}", "task_id": task_id,
                "phenomenon": task["phenomenon"], "task_name": task["task_name"],
                "item_id": item_id, "option_count": len(row["options"]),
                "option_permutation": option_permutation(len(row["options"]), task_id=task_id, item_id=item_id, seed=sampling["seed"]),
            })
    overlap = sorted({case["sample_id"] for case in cases} & consumed)
    if overlap:
        raise ValueError(f"M14 overlaps M13: {overlap}")
    manifest = {
        "schema_version": "m14-pub-schema-replication-manifest-v1",
        "case_count": len(cases), "rank_offset_per_task": sampling["rank_offset_per_task"],
        "overlap_with_m13": 0, "answer_content_in_manifest": False, "cases": cases,
    }
    write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def call_row(provider: SchemaProvider, config: dict[str, Any], case: dict[str, Any], condition: str) -> dict[str, Any]:
    prompt = build_prompt(case, condition)
    response = provider(model=config["model"], prompt=prompt, options=config["generation"]["options"], schema=json_schema_for_condition(condition, len(case["options"])))
    parsed = parse_answer_index(response["text"], len(case["options"]))
    audit = audit_payload_contract(condition, parsed.get("payload"))
    index = parsed["answer_index"]
    return {
        "sample_id": case["sample_id"], "task_id": case["task_id"], "phenomenon": case["phenomenon"], "task_name": case["task_name"], "item_id": case["item_id"],
        "condition": condition, "pretext": case["pretext"], "options": case["options"], "correct_index": case["correct_index"], "correct_answer": case["correct_answer"],
        "predicted_index": index, "predicted_answer": case["options"][index] if index is not None else None,
        "correct": index == case["correct_index"], "parse_valid": parsed["valid"], "parse_error": parsed["error"], "parsed_payload": parsed.get("payload"),
        "schema_contract_valid": audit["valid"], "schema_contract_audit": audit, "raw_response": response["text"],
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt_tokens": response["prompt_tokens"], "completion_tokens": response["completion_tokens"],
        "latency_seconds": round(response["latency_seconds"], 6), "model_reported": response["model_reported"],
    }


def probe() -> dict[str, Any]:
    config = load_json(CONFIG_PATH); protocol = source_protocol(config); rows = prepare_sources(protocol)
    probe_spec = config["contract_probe"]
    manifest_case = {
        "sample_id": "M14-CONTRACT-PROBE", "task_id": probe_spec["task_id"], "phenomenon": "implicature", "task_name": "indirect-answer interpretation",
        "item_id": probe_spec["item_id"], "option_count": len(rows[2][0]["options"]), "option_permutation": list(range(len(rows[2][0]["options"]))),
    }
    case = materialize_case(manifest_case, rows); provider = SchemaProvider(config["generation"]["endpoint"])
    result_rows = [call_row(provider, config, case, condition) for condition in CONDITIONS]
    result = {"schema_version": "m14-contract-probe-v1", "created_at": now(), "formal_score_excluded": True, "rows": result_rows, "passed": all(row["parse_valid"] and row["schema_contract_valid"] for row in result_rows)}
    write_json_atomic(PROBE_PATH, result)
    if not result["passed"]:
        raise ValueError("M14 contract probe failed")
    return result


def condition_order(sample_id: str) -> list[str]:
    offset = int(hashlib.sha256(sample_id.encode()).hexdigest()[:8], 16) % 3
    return list(CONDITIONS[offset:] + CONDITIONS[:offset])


def run() -> dict[str, Any]:
    config = load_json(CONFIG_PATH); protocol = source_protocol(config); task_rows = prepare_sources(protocol)
    if not PROBE_PATH.is_file() or not load_json(PROBE_PATH).get("passed"):
        raise ValueError("passing M14 contract probe required")
    manifest = load_json(MANIFEST_PATH)
    if sha256_file(MANIFEST_PATH) != config["case_manifest"]["sha256"]:
        raise ValueError("M14 case manifest hash drift")
    cases = [materialize_case(case, task_rows) for case in manifest["cases"]]
    bindings = {"config_sha256": sha256_file(CONFIG_PATH), "manifest_sha256": sha256_file(MANIFEST_PATH), "probe_sha256": sha256_file(PROBE_PATH)}
    if CHECKPOINT_PATH.is_file():
        checkpoint = load_json(CHECKPOINT_PATH)
        if any(checkpoint.get(key) != value for key, value in bindings.items()):
            raise ValueError("M14 checkpoint binding drift")
    else:
        checkpoint = {"schema_version": "m14-pub-raw-v1", "status": "running", "started_at": now(), **bindings, "rows": []}
    completed = {(row["sample_id"], row["condition"]) for row in checkpoint["rows"]}; provider = SchemaProvider(config["generation"]["endpoint"]); total = len(cases) * 3
    for case in cases:
        for condition in condition_order(case["sample_id"]):
            if (case["sample_id"], condition) in completed: continue
            row = call_row(provider, config, case, condition); checkpoint["rows"].append(row); completed.add((case["sample_id"], condition)); checkpoint["updated_at"] = now(); write_json_atomic(CHECKPOINT_PATH, checkpoint)
            print(f"M14 {len(completed)}/{total} {case['sample_id']} {condition} correct={row['correct']} schema={row['schema_contract_valid']}", flush=True)
    checkpoint.update({"status": "complete", "completed_at": now(), "model": config["model"], "runtime": runtime_snapshot(), "git": git_snapshot(ROOT), "production_memory_writes": 0})
    write_json_atomic(CHECKPOINT_PATH, checkpoint); write_json_atomic(RAW_PATH, checkpoint); return checkpoint


def analyze(bootstrap_repetitions: int = 20_000) -> dict[str, Any]:
    config = load_json(CONFIG_PATH); manifest = load_json(MANIFEST_PATH); raw = load_json(RAW_PATH); rows = raw["rows"]
    if raw.get("status") != "complete" or len(rows) != 192: raise ValueError("M14 raw result incomplete")
    summary = summarize_rows(rows)
    comparisons = {
        "ours_vs_generic": paired_accuracy_comparison(rows, candidate="OURS_PRAGMATIC_LOOP", baseline="B1_GENERIC_DELIBERATION", bootstrap_repetitions=bootstrap_repetitions, seed=20260819),
        "ours_vs_direct": paired_accuracy_comparison(rows, candidate="OURS_PRAGMATIC_LOOP", baseline="B0_DIRECT", bootstrap_repetitions=bootstrap_repetitions, seed=20260820),
    }
    task_deltas = {task: round(summary["OURS_PRAGMATIC_LOOP"]["by_task"][task]["accuracy"] - summary["B1_GENERIC_DELIBERATION"]["by_task"][task]["accuracy"], 6) for task in summary["OURS_PRAGMATIC_LOOP"]["by_task"]}
    gate = config["success_gate"]
    hypotheses = {
        "H1_answer_parse": all(summary[c]["parse_rate"] == gate["all_conditions_answer_parse_rate"] for c in CONDITIONS),
        "H2_full_schema": all(summary[c]["schema_contract_rate"] == gate["all_conditions_full_schema_rate"] for c in CONDITIONS),
        "H3_primary_gain": comparisons["ours_vs_generic"]["accuracy_delta"] >= gate["primary_accuracy_delta_minimum"] and comparisons["ours_vs_generic"]["exact_mcnemar_pvalue"] <= gate["primary_exact_mcnemar_p_maximum"],
        "H4_no_large_task_regression": min(task_deltas.values()) >= -gate["maximum_allowed_per_task_accuracy_regression"],
    }
    passed = all(hypotheses.values()); by={(r["sample_id"],r["condition"]):r for r in rows}; discord=[]
    for sid in sorted({r["sample_id"] for r in rows}):
        o,g=by[sid,"OURS_PRAGMATIC_LOOP"],by[sid,"B1_GENERIC_DELIBERATION"]
        if o["correct"] != g["correct"]: discord.append({"sample_id":sid,"task_id":o["task_id"],"ours_correct":o["correct"],"generic_correct":g["correct"],"ours_schema_contract_valid":o["schema_contract_valid"]})
    predecessor = load_json(ROOT / config["predecessor"]["result_lock_path"])
    cross_split = {
        "m13_ours_minus_generic_accuracy": predecessor["ours_minus_generic_accuracy"],
        "m13_ours_schema_contract_rate": predecessor["ours_schema_contract_rate"],
        "m14_ours_minus_generic_accuracy": comparisons["ours_vs_generic"]["accuracy_delta"],
        "m14_ours_schema_contract_rate": summary["OURS_PRAGMATIC_LOOP"]["schema_contract_rate"],
        "effect_direction_replicated": (
            predecessor["ours_minus_generic_accuracy"]
            * comparisons["ours_vs_generic"]["accuracy_delta"]
            > 0
        ),
        "pooled_effect_reported": False,
        "reason": "M13 did not instantiate the full Ours schema reliably, so pooling it with schema-enforced M14 would conflate implementation fidelity with sample effects.",
    }
    result = {
        "schema_version":"m14-pub-schema-replication-result-v1", "created_at":now(), "decision":"pass_schema_enforced_pragmatic_gain" if passed else "fail_schema_enforced_pragmatic_gain", "gate_passed":passed, "hypotheses":hypotheses,
        "summary":summary,"comparisons":comparisons,"task_accuracy_delta_ours_minus_generic":task_deltas,
        "posthoc_implementation_fidelity_audit":{"status":"preregistered_full_schema_gate","ours_schema_complete_count":sum(r["schema_contract_valid"] for r in rows if r["condition"]=="OURS_PRAGMATIC_LOOP"),"ours_schema_total":64,"ours_schema_contract_rate":summary["OURS_PRAGMATIC_LOOP"]["schema_contract_rate"]},
        "discordant_cases_ours_vs_generic":discord,"config_sha256":sha256_file(CONFIG_PATH),"manifest_sha256":sha256_file(MANIFEST_PATH),"probe_sha256":sha256_file(PROBE_PATH),"raw_result_sha256":sha256_file(RAW_PATH),"case_count":manifest["case_count"],"rows":rows,
        "cross_split_stability": cross_split,
        "claim_authorized":"schema enforcement establishes implementation fidelity; pragmatic superiority is supported on this replication" if passed else "schema enforcement establishes implementation fidelity only; no pragmatic superiority claim",
        "claim_not_authorized":["pretraining-uncontaminated generalization","longitudinal person understanding","human felt-understanding preference","Uruha fidelity","human-brain equivalence"],"evidence_boundary":config["evidence_boundary"],
    }
    write_json_atomic(RESULT_PATH,result); REPORT_PATH.write_text(render_report(result),encoding="utf-8"); DASHBOARD_PATH.write_text(render_dashboard(result,stage="M14"),encoding="utf-8"); return result


def pct(x: float) -> str: return f"{x*100:.1f}%"


def render_report(r: dict[str, Any]) -> str:
    s=r["summary"]; p=r["comparisons"]["ours_vs_generic"]; lines=["# M14 Schema-enforced PUB Replication","",f"**Decision: `{r['decision']}`**","","| Condition | Accuracy | Answer parse | Full schema | Prompt tokens | Completion tokens | Latency |","|---|---:|---:|---:|---:|---:|---:|"]
    for c in CONDITIONS:
        x=s[c]; lines.append(f"| {c} | {pct(x['accuracy'])} | {pct(x['parse_rate'])} | {pct(x['schema_contract_rate'])} | {x['prompt_tokens']:,} | {x['completion_tokens']:,} | {x['latency_seconds']:.1f}s |")
    lines += ["",f"Primary Ours−Generic: `{p['accuracy_delta']:+.3f}`, 95% CI `[{p['bootstrap_95_ci'][0]:+.3f}, {p['bootstrap_95_ci'][1]:+.3f}]`, McNemar `p={p['exact_mcnemar_pvalue']:.4f}`, wins/ties/losses `{p['candidate_wins']}/{p['ties']}/{p['baseline_wins']}`.","",f"Secondary Ours−Direct: `{r['comparisons']['ours_vs_direct']['accuracy_delta']:+.3f}`, 95% CI `[{r['comparisons']['ours_vs_direct']['bootstrap_95_ci'][0]:+.3f}, {r['comparisons']['ours_vs_direct']['bootstrap_95_ci'][1]:+.3f}]`, McNemar `p={r['comparisons']['ours_vs_direct']['exact_mcnemar_pvalue']:.4f}`.","","## Task-level accuracy",""]
    lines += ["| Task | Direct | Generic | Ours | Ours - Generic |","|---|---:|---:|---:|---:|"]
    for task in sorted(r["task_accuracy_delta_ours_minus_generic"]):
        lines.append(f"| T{task} | {pct(s['B0_DIRECT']['by_task'][task]['accuracy'])} | {pct(s['B1_GENERIC_DELIBERATION']['by_task'][task]['accuracy'])} | {pct(s['OURS_PRAGMATIC_LOOP']['by_task'][task]['accuracy'])} | {r['task_accuracy_delta_ours_minus_generic'][task]:+.3f} |")
    cross=r["cross_split_stability"]
    lines += ["","## Cross-split stability","",f"M13 Ours−Generic was `{cross['m13_ours_minus_generic_accuracy']:+.3f}` with only `{cross['m13_ours_schema_contract_rate']*100:.1f}%` complete schemas; M14 is `{cross['m14_ours_minus_generic_accuracy']:+.3f}` with `{cross['m14_ours_schema_contract_rate']*100:.1f}%` complete schemas. Direction replicated: `{cross['effect_direction_replicated']}`.","",cross["reason"],"","## Locked gates",""]
    lines += [f"- `{k}`: {'PASS' if v else 'FAIL'}" for k,v in r["hypotheses"].items()]
    lines += ["","## Interpretation","",r["claim_authorized"]+".","",r["evidence_boundary"],"","## Reproducibility","",f"- Config SHA: `{r['config_sha256']}`",f"- Manifest SHA: `{r['manifest_sha256']}`",f"- Probe SHA: `{r['probe_sha256']}`",f"- Raw SHA: `{r['raw_result_sha256']}`","- Production memory writes: `0`"]
    return "\n".join(lines)+"\n"


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--prepare",action="store_true"); ap.add_argument("--probe",action="store_true"); ap.add_argument("--run",action="store_true"); ap.add_argument("--analyze",action="store_true"); ap.add_argument("--all",action="store_true"); a=ap.parse_args()
    if not any((a.prepare,a.probe,a.run,a.analyze,a.all)): ap.error("choose an action")
    if a.prepare or a.all: print("manifest",prepare_manifest()["case_count"],sha256_file(MANIFEST_PATH))
    if a.probe or a.all: print("probe",probe()["passed"],sha256_file(PROBE_PATH))
    if a.run or a.all: print("rows",len(run()["rows"]))
    if a.analyze or a.all: print("decision",analyze()["decision"])


if __name__ == "__main__": main()
