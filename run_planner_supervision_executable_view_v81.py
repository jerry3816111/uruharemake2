#!/usr/bin/env python3
"""Run the frozen V81 matched executable-view proxy review locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import planner_supervision_executable_view_v81 as v81
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v81_executable_view_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v81_executable_view.json"


def main():
    if REPORT_PATH.exists():
        existing = v76.load_json(REPORT_PATH)
        if existing.get("schema") == "uruha_planner_executable_view_abort_v81":
            raise SystemExit("V81 is permanently closed after an interrupted formal run")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    contract = v76.load_json(CONTRACT_PATH)
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    if paths["raw_results"].exists() and not (args.overwrite or args.resume):
        raise SystemExit("V81 raw result exists; pass --resume or --overwrite")

    packets = v81.build_packets(
        v76.load_jsonl(paths["candidate_queue"]),
        v76.load_jsonl(paths["session_manifest"]),
        v76.load_jsonl(paths["v79_pilot_queue"]),
        contract,
    )
    if len(packets) != int(contract["selection"]["fresh_count"]):
        raise SystemExit("V81 packet count differs from frozen contract")
    v76.write_jsonl(paths["packet_queue"], packets)

    installed = v81.installed_model_digests()
    for judge in contract["judges"]:
        if installed.get(judge["model"]) != judge["digest"]:
            raise SystemExit(f"V81 model digest mismatch: {judge['model']}")

    rows = v76.load_jsonl(paths["raw_results"]) if args.resume else []
    sequence = v81.validate_resume_prefix(packets, rows, contract, installed)
    if len(sequence) != int(contract["inference"]["expected_attempt_count"]):
        raise SystemExit("V81 run sequence differs from frozen call budget")
    total = len(sequence)
    for judge, packet, condition, variant in sequence[len(rows) :]:
        print(
            f"[{len(rows) + 1}/{total}] {judge['model']} fresh={packet['fresh_index']} "
            f"condition={condition} variant={variant}",
            flush=True,
        )
        row = v81.run_judgment(
            packet,
            contract,
            judge,
            installed[judge["model"]],
            condition,
            variant,
        )
        rows.append(row)
        v76.write_jsonl(paths["raw_results"], rows)
    print(json.dumps({"attempt_count": len(rows), "raw_path": str(paths["raw_results"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
