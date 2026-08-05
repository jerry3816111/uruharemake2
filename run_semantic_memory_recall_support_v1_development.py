#!/usr/bin/env python3
"""Run the preregistered semantic recall-support development experiment."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import memory_item_causal_intervention_v1 as experiment
import run_high_confidence_memory_recall_v1_development as recall_v1_runner
import run_memory_item_causal_intervention_v1 as baseline_runner
import run_rightbrain_pipeline_shadow_v61 as v61
import uruha_memory_runtime as umr


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/semantic_memory_recall_support_v1_preregistration.json"
BASE_PREREG = ROOT / "configs/memory_item_causal_intervention_v1_preregistration.json"
CASES = ROOT / "configs/memory_item_causal_intervention_v1_cases.json"
OUTPUT_DIR = ROOT / "analysis/local_semantic_memory_recall_support_v1_development"
RAW = OUTPUT_DIR / "raw.jsonl"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def run_preflight():
    tests = [
        "test_semantic_memory_recall_support_v1.py",
        "test_semantic_memory_recall_support_v1_preregistration.py",
        "test_high_confidence_memory_recall_v1.py",
    ]
    completed = subprocess.run(
        [os.environ.get("PYTHON", os.sys.executable), "-m", "unittest", "-q", *tests],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "URUHA_SKIP_AUTO_VENV": "1",
            "TOKENIZERS_PARALLELISM": "false",
        },
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    return {
        "passed": completed.returncode == 0,
        "observed_test_count": int(match.group(1)) if match else None,
        "returncode": completed.returncode,
        "tests": tests,
    }


def boundary_probes():
    def item(text, score, suffix):
        return {
            "source": "episode",
            "collection_name": "episode",
            "memory_id": suffix,
            "trace_id": f"stored:episode:{suffix}",
            "text": text,
            "score": score,
        }

    def memory_data(*items):
        return {"working_memory_items": list(items)}

    probes = {
        "sensitive": umr.select_high_confidence_recall_item(
            "前に話したパスワード、覚えてる？",
            memory_data(item("パスワードはsample-secretだと言った。", 0.95, "sensitive")),
        ),
        "non_recall": umr.select_high_confidence_recall_item(
            "今日は観葉植物に水をあげた。",
            memory_data(item("観葉植物の呼び名はアオバ。", 0.95, "non-recall")),
        ),
        "ambiguous": umr.select_high_confidence_recall_item(
            "前に決めた待ち合わせ場所、どこだっけ？",
            memory_data(
                item("待ち合わせ場所は北口に決めた。", 0.83, "north"),
                item("待ち合わせ場所は東口に決めた。", 0.76, "east"),
            ),
        ),
    }
    return {
        name: {
            "status": result.get("status"),
            "selected": bool(result.get("selected")),
        }
        for name, result in probes.items()
    }


def run_condition(bot, case, condition, call_log):
    row = recall_v1_runner.run_condition(bot, case, condition, call_log)
    row["schema"] = "uruha_semantic_memory_recall_support_development_raw_v1"
    return row


def main():
    prereg = load_json(PREREG)
    base_prereg = load_json(BASE_PREREG)
    preflight = run_preflight()
    if not preflight["passed"]:
        raise SystemExit(f"semantic recall support preflight failed: {preflight}")
    model = base_prereg["model"]
    if baseline_runner.installed_model_digest(model["ollama_tag"]) != model["digest"]:
        raise SystemExit("required qwen2.5:7b model missing or drifted")

    cases = experiment.load_cases(CASES)
    sequence = experiment.expected_sequence(cases)
    expected = prereg["development_gates"]["expected_decision_run_count"]
    if len(sequence) != expected:
        raise SystemExit("development condition count drift")

    rows = []
    with v61._isolated_brain(base_prereg) as (bot, call_log, isolation):
        call_log.clear()
        baseline_runner.install_audited_client(
            bot,
            base_prereg["generation"]["seed"],
            call_log,
        )
        for index, (case, condition) in enumerate(sequence, start=1):
            print(f"[{index}/{expected}] {case['id']} {condition}", flush=True)
            rows.append(run_condition(bot, case, condition, call_log))
            write_jsonl(RAW, rows)

    metadata = {
        "schema": "uruha_semantic_memory_recall_support_development_run_v1",
        "row_count": len(rows),
        "branch": v61._git("branch", "--show-current"),
        "commit": v61._git("rev-parse", "HEAD"),
        "preflight": preflight,
        "boundary_probes": boundary_probes(),
        "isolation": isolation,
        "raw_path": str(RAW),
    }
    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
