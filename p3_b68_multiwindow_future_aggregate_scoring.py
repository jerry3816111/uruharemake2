"""B68 all-at-once future unlock and aggregate proxy scoring."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from typing import Any

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56
import p3_b61_native_subtitle_cutoff_extractor as b61
import p3_b66_future_outcome_unlock_scoring as b66
import p3_b67_same_source_multiwindow_predictions as b67
import p3_b68_future_batch_reader as future_reader


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b68_multiwindow_future_aggregate_scoring_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b68_multiwindow_future_aggregate_scoring_implementation_freeze_2026-09-20.json"


class B68Error(RuntimeError):
    def __init__(self, stage: str, category: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.category = category


def canonical_json(value: Any) -> str:
    return b55_v1.canonical_json(value)


def sha256_bytes(payload: bytes) -> str:
    return b55_v1.sha256_bytes(payload)


def sha256_file(path: str | Path) -> str:
    return b55_v1.sha256_file(path)


def load_json(path: str | Path) -> dict[str, Any]:
    return b55_v1.load_json(path)


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def expected_rows() -> list[dict[str, Any]]:
    return [
        {"row_id": "r0600", "future_milliseconds": [781000, 841000]},
        {"row_id": "r1200", "future_milliseconds": [1381000, 1441000]},
        {"row_id": "r1800", "future_milliseconds": [1981000, 2041000]},
        {"row_id": "r2400", "future_milliseconds": [2581000, 2641000]},
    ]


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b68_multiwindow_future_aggregate_scoring_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_after_complete_b67_predictions_before_any_replication_future_access":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str(binding.get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    prediction_binding = (contract.get("bindings") or {}).get("b67_saved_predictions") or {}
    if prediction_binding:
        predictions = load_json(Path(root) / prediction_binding["path"])
        if b67.validate_result(predictions) != {"valid": True, "errors": []} or predictions.get("result_hash") != "f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82":
            errors.append("prediction_identity")
        if predictions.get("prediction_side_future_access_count") != 0:
            errors.append("prior_future_access")
    source = contract.get("source") or {}
    if source.get("source_id") != "youtube_4y5GiQpgJgo" or source.get("rows") != expected_rows():
        errors.append("rows")
    if source.get("include_rule") != "cue_start_gte_future_start_and_cue_end_lte_future_end" or source.get("minimum_future_cues_each_row") != 1 or source.get("unlock_all_rows_together") is not True:
        errors.append("source_boundary")
    private = contract.get("private_acquisition") or {}
    if private != {
        "native_downloader_process_invocation_count_max": 1,
        "retry_or_fallback_allowed": False,
        "cookies_login_paid_api_or_account_access_allowed": False,
        "private_full_caption_deleted_before_public_scoring": True,
        "raw_full_caption_or_context_cue_persistence_allowed": False,
    }:
        errors.append("private")
    public = contract.get("public_future_batch") or {}
    if public != {
        "root": "external_data/p3_b68_public_future_batch",
        "artifact_schema": "uruha_p3_b68_public_future_row_v1",
        "manifest_schema": "uruha_p3_b68_public_future_row_manifest_v1",
        "artifact_count_exact": 4,
        "fresh_reader_process_count": 1,
    }:
        errors.append("public")
    scoring = contract.get("scoring") or {}
    for field in (
        "reuse_b66_first_three_cues_within_twelve_seconds",
        "reuse_b66_proxy_marker_order_without_change",
        "reuse_b66_per_row_metrics_and_winner_rule_without_change",
    ):
        if scoring.get(field) is not True:
            errors.append(f"scoring:{field}")
    if scoring.get("model_human_or_llm_judge_call_count_required") != 0 or scoring.get("prediction_mutation_count_required") != 0:
        errors.append("scoring_calls")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b68_replication_future_access":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / artifact["path"]
        if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
            errors.append(name)
    if errors:
        raise B68Error("freeze", "freeze", ";".join(errors))
    return {"valid": True, "future_outcome_access_count_at_freeze": freeze.get("future_outcome_access_count_at_freeze")}


def extract_future_batch(raw_caption: bytes, contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    try:
        document = json.loads(raw_caption)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B68Error("projection", "caption_json", "caption JSON") from exc
    events = document.get("events") if isinstance(document, dict) else None
    if not isinstance(events, list):
        raise B68Error("projection", "caption_json", "caption events")
    artifacts = []
    for row in contract["source"]["rows"]:
        start_limit, end_limit = row["future_milliseconds"]
        cues = []
        for event in events:
            if not isinstance(event, dict):
                continue
            start, duration, segments = event.get("tStartMs"), event.get("dDurationMs"), event.get("segs")
            if not isinstance(start, (int, float)) or not isinstance(duration, (int, float)) or not isinstance(segments, list):
                continue
            end = start + duration
            if start < start_limit or end > end_limit or end < start:
                continue
            text = " ".join("".join(segment.get("utf8", "") for segment in segments if isinstance(segment, dict)).split())
            if text:
                cues.append({"start_seconds": round(start / 1000.0, 3), "end_seconds": round(end / 1000.0, 3), "text": text})
        cues.sort(key=lambda cue: (cue["start_seconds"], cue["end_seconds"]))
        if not cues:
            raise B68Error("projection", "no_future_cues", row["row_id"])
        artifacts.append({
            "schema": contract["public_future_batch"]["artifact_schema"], "version": "1.0.0",
            "source_id": contract["source"]["source_id"], "row_id": row["row_id"],
            "future_seconds": [start_limit / 1000.0, end_limit / 1000.0],
            "language_code": "ja", "track_type": "automatic", "format": "json3", "cues": cues,
        })
    return artifacts


def _exclusive_bytes(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def publish_batch(artifacts: list[dict[str, Any]], root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    if root.exists() and any(root.iterdir()):
        raise B68Error("publication", "preexisting", "public root")
    root.mkdir(parents=True, mode=0o700)
    manifests = []
    for artifact in artifacts:
        payload = canonical_json(artifact).encode("utf-8")
        digest = sha256_bytes(payload)
        artifact_id = f"p3-b68-{artifact['row_id']}-{digest[:16]}"
        manifest = {
            "schema": contract["public_future_batch"]["manifest_schema"], "version": "1.0.0",
            "artifact_id": artifact_id, "artifact_sha256": digest, "row_id": artifact["row_id"],
            "source_id": artifact["source_id"], "future_seconds": artifact["future_seconds"],
            "cue_count": len(artifact["cues"]), "raw_full_caption_persisted": False,
            "context_cues_persisted": False, "prediction_batch_result_hash": "f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82",
        }
        manifest["manifest_hash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
        _exclusive_bytes(root / f"{artifact_id}.json", payload)
        _exclusive_bytes(root / f"{artifact_id}.manifest.json", canonical_json(manifest).encode("utf-8"))
        manifests.append(manifest)
    os.chmod(root, 0o500)
    return manifests


def aggregate_scores(rows: list[dict[str, Any]]) -> dict[str, Any]:
    conditions = ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]
    aggregate = {}
    for condition in conditions:
        scores = [score for row in rows for score in row["scores"] if score["condition"] == condition]
        aggregate[condition] = {
            "row_count": len(scores),
            "top1_hits": sum(bool(score["selected_label_hit"]) for score in scores),
            "mean_actual_label_probability": round(sum(score["actual_label_probability"] for score in scores) / len(scores), 12),
            "mean_multiclass_brier": round(sum(score["multiclass_brier"] for score in scores) / len(scores), 12),
            "mean_log_loss": round(sum(score["log_loss"] for score in scores) / len(scores), 12),
        }
    aggregate["row_wins"] = {
        "BASELINE_LITERAL": sum(row["proxy_winner"] == "BASELINE_LITERAL" for row in rows),
        "SYSTEM_PRAGMATIC_STATE": sum(row["proxy_winner"] == "SYSTEM_PRAGMATIC_STATE" for row in rows),
        "TIE": sum(row["proxy_winner"] == "TIE" for row in rows),
    }
    return aggregate


def _finalize(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if result.get("schema") != "uruha_p3_b68_multiwindow_future_aggregate_result_v1" or result.get("status") not in {"aggregate_scored", "unlock_failed"}:
        errors.append("identity")
    if result.get("prediction_batch_result_hash") != "f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82":
        errors.append("prediction")
    for field in ("prediction_mutation_count", "model_human_or_llm_judge_call_count", "retry_count", "fallback_count", "training_write_count", "formal_m56_write_count", "production_memory_write_count"):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("status") == "aggregate_scored":
        if result.get("future_outcome_access_count") != 4 or result.get("outcome_score_count") != 8:
            errors.append("counts")
        if result.get("private_deleted_before_public_scoring") is not True or result.get("public_artifact_count") != 4:
            errors.append("separation")
        rows = result.get("rows")
        if not isinstance(rows, list) or [row.get("row_id") for row in rows] != ["r0600", "r1200", "r1800", "r2400"]:
            errors.append("rows")
        if not isinstance(result.get("aggregate"), dict):
            errors.append("aggregate")
    elif result.get("outcome_score_count") != 0 or not result.get("failure_stage"):
        errors.append("failure")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("hash")
    return {"valid": not errors, "errors": errors}


def execute() -> dict[str, Any]:
    validate_implementation_freeze()
    contract = load_contract()
    report = validate_contract(contract)
    if not report["valid"]:
        raise B68Error("contract", "contract", ";".join(report["errors"]))
    state_root = ROOT / contract["execution"]["state_root"]
    public_root = ROOT / contract["public_future_batch"]["root"]
    if state_root.exists() or (public_root.exists() and any(public_root.iterdir())):
        raise B68Error("preflight", "preflight", "B68 already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    intent = {"schema": "uruha_p3_b68_intent_v1", "prediction_batch_result_hash": "f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82", "all_rows_unlock_together": True, "contract_sha256": sha256_file(CONFIG_PATH)}
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], intent)
    predictions = load_json(ROOT / contract["bindings"]["b67_saved_predictions"]["path"])
    result = {
        "schema": "uruha_p3_b68_multiwindow_future_aggregate_result_v1", "version": "1.0.0",
        "prediction_batch_result_hash": "f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82",
        "prediction_mutation_count": 0, "model_human_or_llm_judge_call_count": 0, "retry_count": 0, "fallback_count": 0,
        "training_write_count": 0, "formal_m56_write_count": 0, "production_memory_write_count": 0,
        "future_outcome_access_count": 0, "outcome_score_count": 0, "claim_boundary": contract["claim_boundary"],
    }
    raw = artifacts = None
    started = time.perf_counter()
    try:
        b61_contract = b61.load_contract()
        yt_dlp = shutil.which("yt-dlp")
        version = b55_v2._tool_version(yt_dlp, b55_v2.load_contract()["transport"]["yt_dlp_version_command"])
        if version != b61_contract["native_downloader"]["required_version"]:
            raise B68Error("preflight", "version", "yt-dlp")
        with TemporaryDirectory(prefix="uruha-p3-b68-private-") as temporary:
            private_root = Path(temporary)
            completed = subprocess.run(b61.build_native_downloader_command(private_root, b61_contract), capture_output=True, timeout=180)
            result["native_downloader_process_invocation_count"] = 1
            result["downloader_returncode"] = completed.returncode
            if completed.returncode != 0:
                raise B68Error("download", b56.classify_private_stderr(completed.stderr or b""), "download")
            caption_path, raw = b61.read_single_private_caption(private_root, b61_contract)
            artifacts = extract_future_batch(raw, contract)
            result["private_full_caption_bytes_discarded_after_projection"] = len(raw)
            caption_path.unlink()
            raw = None
        result["private_deleted_before_public_scoring"] = True
        manifests = publish_batch(artifacts, public_root, contract)
        artifacts = None
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", future_reader.PUBLIC_ROOT_ENV: str(public_root)}
        child = subprocess.run([sys.executable, str(ROOT / "p3_b68_future_batch_reader.py"), "--read-batch", *[item["artifact_id"] for item in manifests]], capture_output=True, text=True, env=env, timeout=60)
        if child.returncode != 0:
            raise B68Error("reader", "reader", "future reader")
        batch = json.loads(child.stdout)
        rows = []
        b66_contract = b66.load_contract()
        for item in batch["rows"]:
            row_id = item["artifact"]["row_id"]
            target = b66.target_cues(item["artifact"], b66_contract)
            outcome_text = " ".join(cue["text"] for cue in target)
            actual_label, marker = b66.classify_observable_label(outcome_text, b66_contract)
            frozen = [row for row in predictions["predictions"] if row["row_id"] == row_id]
            scores = [b66.score_prediction(row, actual_label, outcome_text) for row in frozen]
            rows.append({
                "row_id": row_id, "actual_proxy_label": actual_label, "matched_proxy_marker": marker,
                "evidence_excerpt": outcome_text[:120], "target_cue_count": len(target),
                "target_seconds": [target[0]["start_seconds"], max(cue["end_seconds"] for cue in target)],
                "scores": scores, "proxy_winner": b66.choose_proxy_winner(scores),
            })
        result.update({"status": "aggregate_scored", "future_outcome_access_count": 4, "outcome_score_count": 8, "public_artifact_count": 4, "fresh_reader_count": 1, "rows": rows, "aggregate": aggregate_scores(rows), "proxy_is_not_human_ground_truth": True})
    except Exception as exc:
        raw = artifacts = None
        result.update({"status": "unlock_failed", "failure_stage": getattr(exc, "stage", "unexpected"), "failure_category": getattr(exc, "category", "unknown"), "failure_class": type(exc).__name__, "outcome_score_count": 0})
    result["total_elapsed_seconds"] = round(time.perf_counter() - started, 6)
    _finalize(result)
    checked = validate_result(result)
    if not checked["valid"]:
        raise B68Error("result", "result", ";".join(checked["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    if not args.execute_once:
        parser.error("B68 supports only one frozen execution")
    result = execute()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "aggregate_scored":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
