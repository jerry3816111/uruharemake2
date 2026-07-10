#!/usr/bin/env python3
"""Replay preference gates with a preferred-likelihood displacement guard."""

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_semantic_preference_v19 import build_report as build_original_gate
from project_paths import (
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_PREFERENCE_LIKELIHOOD_GATE_V21_REPORT_JSON_PATH,
    RIGHTBRAIN_PREFERENCE_LIKELIHOOD_GATE_V21_REPORT_MD_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
MAX_PREFERRED_LIKELIHOOD_DECREASE_RATE = 0.5
METHOD_REFERENCE = "https://proceedings.iclr.cc/paper_files/paper/2025/hash/3df38ca67befaed9c03b95ffee07d9f8-Abstract-Conference.html"


def preferred_likelihood_diagnostic(training_report):
    initial_rows = {
        row["id"]: row for row in training_report["initial_eval_preference"].get("rows", [])
    }
    final_rows = {
        row["id"]: row for row in training_report["final_eval_preference"].get("rows", [])
    }
    shared_ids = sorted(set(initial_rows) & set(final_rows))
    deltas = [
        final_rows[row_id]["chosen_average_log_prob"]
        - initial_rows[row_id]["chosen_average_log_prob"]
        for row_id in shared_ids
    ]
    return {
        "pair_count": len(deltas),
        "mean_chosen_average_log_prob_delta": statistics.fmean(deltas) if deltas else None,
        "preferred_likelihood_decreased_count": sum(delta < 0 for delta in deltas),
        "preferred_likelihood_decrease_rate": (
            sum(delta < 0 for delta in deltas) / len(deltas) if deltas else None
        ),
        "rows": [
            {"id": row_id, "chosen_average_log_prob_delta": delta}
            for row_id, delta in zip(shared_ids, deltas)
        ],
    }


def replay_training_report(label, training_report):
    original = build_original_gate(training_report)
    preferred = preferred_likelihood_diagnostic(training_report)
    evidence_available = preferred["pair_count"] == training_report["eval_pair_count"]
    mean_non_decreasing = (
        evidence_available
        and preferred["mean_chosen_average_log_prob_delta"] >= 0
    )
    majority_non_decreasing = (
        evidence_available
        and preferred["preferred_likelihood_decrease_rate"]
        <= MAX_PREFERRED_LIKELIHOOD_DECREASE_RATE
    )
    added_gates = {
        "preferred_likelihood_evidence_covers_all_unseen_pairs": evidence_available,
        "unseen_mean_preferred_log_prob_non_decreasing": mean_non_decreasing,
        "unseen_preferred_likelihood_decrease_rate_at_most_50pct": majority_non_decreasing,
    }
    gates = {**original["gates"], **added_gates}
    return {
        "label": label,
        "adapter_ref": training_report["output_adapter_ref"],
        "original_gate_authorized_holdout": original["authorize_actual_model_holdout"],
        "v21_gate_authorizes_holdout": all(gates.values()),
        "preferred_likelihood": preferred,
        "added_gates": added_gates,
        "all_gates": gates,
    }


def build_report(training_reports):
    replays = [
        replay_training_report(label, training_report)
        for label, training_report in training_reports
    ]
    changed_decisions = [
        replay
        for replay in replays
        if replay["original_gate_authorized_holdout"]
        != replay["v21_gate_authorizes_holdout"]
    ]
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_preference_likelihood_gate_v21_replay",
        "method_reference": METHOD_REFERENCE,
        "max_preferred_likelihood_decrease_rate": MAX_PREFERRED_LIKELIHOOD_DECREASE_RATE,
        "replays": replays,
        "changed_decision_labels": [row["label"] for row in changed_decisions],
        "decision_zh": (
            "加入 preferred-likelihood guard 後，V20 會在 actual-model holdout 前被攔下；"
            "這能抓到 margin 變好但正確回答本身機率下降的 likelihood displacement。"
        ),
        "policy_zh": (
            "V21 起，preference 訓練必須同時滿足：未見 pair 的 mean preferred log-prob 不下降，"
            "且至少一半 pair 的 preferred likelihood 不下降。這是本專案的保守前置 gate，"
            "只負責阻止不值得進入昂貴 runtime holdout 的 adapter。"
        ),
        "research_boundary": (
            "This threshold is a conservative local engineering gate calibrated on V19/V20, not a universal "
            "claim from the cited paper. Actual-model multi-seed evaluation remains mandatory for promotion."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# RightBrain V21 Preferred-Likelihood Gate",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| run | 原 gate | V21 gate | mean preferred delta | decrease rate |",
        "|---|---|---|---:|---:|",
    ]
    for replay in report["replays"]:
        preferred = replay["preferred_likelihood"]
        lines.append(
            f"| {replay['label']} | {'PASS' if replay['original_gate_authorized_holdout'] else 'FAIL'} | "
            f"{'PASS' if replay['v21_gate_authorizes_holdout'] else 'FAIL'} | "
            f"{preferred['mean_chosen_average_log_prob_delta']:+.6f} | "
            f"{preferred['preferred_likelihood_decrease_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## 新增 Gate",
            "",
            report["policy_zh"],
            "",
            f"研究邊界：{report['research_boundary']}",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--v19-training-report",
        default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_TRAINING_RUN_REPORT_PATH,
    )
    parser.add_argument(
        "--v20-training-report",
        default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
    )
    parser.add_argument(
        "--output-json",
        default=RIGHTBRAIN_PREFERENCE_LIKELIHOOD_GATE_V21_REPORT_JSON_PATH,
    )
    parser.add_argument(
        "--output-md",
        default=RIGHTBRAIN_PREFERENCE_LIKELIHOOD_GATE_V21_REPORT_MD_PATH,
    )
    args = parser.parse_args()
    report = build_report(
        [
            (
                "v19_deleted_clause_simpo",
                json.loads(Path(args.v19_training_report).read_text(encoding="utf-8")),
            ),
            (
                "v20_length_matched_simpo",
                json.loads(Path(args.v20_training_report).read_text(encoding="utf-8")),
            ),
        ]
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "changed_decision_labels": report["changed_decision_labels"],
                "decision_zh": report["decision_zh"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
