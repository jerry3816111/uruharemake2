#!/usr/bin/env python3
"""Run the frozen V80 proxy judges locally through Ollama."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import planner_supervision_proxy_review_v80 as v80
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v80_proxy_review_contract.json"
V79_CONTRACT_PATH = ROOT / "configs/planner_supervision_v79_pilot_review_contract.json"


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    contract = v76.load_json(CONTRACT_PATH)
    v79_contract = v76.load_json(V79_CONTRACT_PATH)
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    if paths["raw_results"].exists() and not (args.overwrite or args.resume):
        raise SystemExit("raw result exists; pass --resume or --overwrite")
    packets = v80.build_packets(
        v76.load_jsonl(paths["candidate_queue"]),
        v76.load_jsonl(paths["session_manifest"]),
        v76.load_jsonl(paths["pilot_queue"]),
        v79_contract,
    )
    if len(packets) != contract["inference"]["expected_packet_count"]:
        raise SystemExit("packet count differs from frozen contract")
    v76.write_jsonl(paths["packet_queue"], packets)
    installed = v80.installed_model_digests()
    for judge in contract["judges"]:
        if installed.get(judge["model"]) != judge["digest"]:
            raise SystemExit(f"model digest mismatch: {judge['model']}")

    rows = v76.load_jsonl(paths["raw_results"]) if args.resume else []
    sequence = v80.validate_resume_prefix(packets, rows, contract, installed)
    total = len(sequence)
    for judge, packet in sequence[len(rows):]:
        print(f"[{len(rows) + 1}/{total}] {judge['model']} pilot={packet['pilot_index']}", flush=True)
        row = v80.run_judgment(packet, contract, judge, installed[judge["model"]])
        rows.append(row)
        v76.write_jsonl(paths["raw_results"], rows)
    print(json.dumps({"attempt_count": len(rows), "raw_path": str(paths["raw_results"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
