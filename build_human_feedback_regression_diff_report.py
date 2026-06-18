import argparse
import json
import os
from datetime import datetime

from project_paths import (
    HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_MD_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR,
)


METRIC_SPECS = [
    ("route_match_rate", "Route 命中率", "higher"),
    ("focus_ok_rate", "Focus 命中率", "higher"),
    ("obligation_ok_rate", "Obligation 命中率", "higher"),
    ("memory_ok_rate_when_expected", "記憶命中率", "higher"),
    ("density_ok_rate", "資訊密度合格率", "higher"),
    ("generic_reply_rate", "通用空話率", "lower"),
    ("same_as_observed_bad_reply_rate", "重複舊壞答案率", "lower"),
    ("avg_expected_proxy_persist_rate", "壞 proxy 持續率", "lower"),
    ("overall_auto_pass_rate", "整體自動通過率", "higher"),
]


def _load_json(path):
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _rounded(value, digits=4):
    try:
        return round(float(value), digits)
    except Exception:
        return 0.0


def _latest_snapshot_json(snapshot_dir):
    if not os.path.exists(snapshot_dir):
        return None
    candidates = [
        os.path.join(snapshot_dir, name)
        for name in os.listdir(snapshot_dir)
        if name.endswith(".json") and not name.endswith(".meta.json")
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    return candidates[0]


def _metric_delta(before, after, direction):
    before_value = _safe_float(before)
    after_value = _safe_float(after)
    delta = after_value - before_value
    if abs(delta) < 1e-9:
        status = "no_change"
    elif direction == "higher":
        status = "improved" if delta > 0 else "regressed"
    else:
        status = "improved" if delta < 0 else "regressed"
    return {
        "before": _rounded(before_value),
        "after": _rounded(after_value),
        "delta": _rounded(delta),
        "status": status,
    }


def _failure_rows(before_rows, after_rows):
    before_map = {row.get("code"): row for row in (before_rows or [])}
    after_map = {row.get("code"): row for row in (after_rows or [])}
    codes = sorted(set(before_map) | set(after_map))
    rows = []
    for code in codes:
        before = before_map.get(code) or {}
        after = after_map.get(code) or {}
        before_resolved = _safe_float(before.get("resolved_rate"))
        after_resolved = _safe_float(after.get("resolved_rate"))
        delta = after_resolved - before_resolved
        if abs(delta) < 1e-9:
            status = "no_change"
        elif delta > 0:
            status = "improved"
        else:
            status = "regressed"
        rows.append(
            {
                "code": code,
                "label_zh": after.get("label_zh") or before.get("label_zh"),
                "before_resolved_rate": _rounded(before_resolved),
                "after_resolved_rate": _rounded(after_resolved),
                "delta_resolved_rate": _rounded(delta),
                "before_unresolved_count": int(before.get("unresolved_count") or 0),
                "after_unresolved_count": int(after.get("unresolved_count") or 0),
                "delta_unresolved_count": int(after.get("unresolved_count") or 0) - int(before.get("unresolved_count") or 0),
                "status": status,
            }
        )
    return rows


def _language_rows(before_summary, after_summary):
    before_map = (before_summary or {}).get("language_breakdown") or {}
    after_map = (after_summary or {}).get("language_breakdown") or {}
    languages = sorted(set(before_map) | set(after_map))
    rows = []
    for language in languages:
        before = before_map.get(language) or {}
        after = after_map.get(language) or {}
        rows.append(
            {
                "language": language,
                "before_overall_auto_pass_rate": _rounded(before.get("overall_auto_pass_rate")),
                "after_overall_auto_pass_rate": _rounded(after.get("overall_auto_pass_rate")),
                "delta_overall_auto_pass_rate": _rounded(
                    _safe_float(after.get("overall_auto_pass_rate")) - _safe_float(before.get("overall_auto_pass_rate"))
                ),
                "before_generic_reply_rate": _rounded(before.get("generic_reply_rate")),
                "after_generic_reply_rate": _rounded(after.get("generic_reply_rate")),
                "delta_generic_reply_rate": _rounded(
                    _safe_float(after.get("generic_reply_rate")) - _safe_float(before.get("generic_reply_rate"))
                ),
            }
        )
    return rows


def _case_score(row):
    if not row:
        return 0.0
    score = 0.0
    score += _safe_float(row.get("route_match")) * 1.0
    score += _safe_float(row.get("focus_ok")) * 1.0
    score += _safe_float(row.get("obligation_ok")) * 1.0
    if row.get("memory_expected"):
        score += _safe_float(row.get("memory_ok")) * 1.0
    score += (1.0 - _safe_float(row.get("generic_reply"))) * 1.0
    score += (1.0 - _safe_float(row.get("same_as_observed_bad_reply"))) * 1.0
    score += _safe_float(row.get("expected_proxy_persist_rate")) * -0.5
    score += _safe_float(row.get("overall_auto_pass")) * 2.0
    return round(score, 4)


def _case_changes(before_payload, after_payload):
    before_map = {row.get("id"): row for row in (before_payload.get("results") or []) if row.get("id")}
    after_map = {row.get("id"): row for row in (after_payload.get("results") or []) if row.get("id")}
    shared_ids = sorted(set(before_map) & set(after_map))

    improved = []
    regressed = []
    unchanged = []
    new_cases = sorted(set(after_map) - set(before_map))
    removed_cases = sorted(set(before_map) - set(after_map))

    for case_id in shared_ids:
        before = before_map[case_id]
        after = after_map[case_id]
        before_score = _case_score(before)
        after_score = _case_score(after)
        delta_score = round(after_score - before_score, 4)
        before_pass = int(bool(before.get("overall_auto_pass")))
        after_pass = int(bool(after.get("overall_auto_pass")))
        before_generic = _safe_float(before.get("generic_reply"))
        after_generic = _safe_float(after.get("generic_reply"))
        before_proxy = _safe_float(before.get("expected_proxy_persist_rate"))
        after_proxy = _safe_float(after.get("expected_proxy_persist_rate"))
        deltas = {
            "overall_auto_pass": after_pass - before_pass,
            "focus_ok": int(bool(after.get("focus_ok"))) - int(bool(before.get("focus_ok"))),
            "obligation_ok": int(bool(after.get("obligation_ok"))) - int(bool(before.get("obligation_ok"))),
            "memory_ok": int(bool(after.get("memory_ok"))) - int(bool(before.get("memory_ok"))),
            "generic_reply": round(after_generic - before_generic, 4),
            "expected_proxy_persist_rate": round(after_proxy - before_proxy, 4),
        }
        notes = []
        if deltas["overall_auto_pass"] > 0:
            notes.append("overall_auto_pass 修好")
        elif deltas["overall_auto_pass"] < 0:
            notes.append("overall_auto_pass 退化")
        if deltas["focus_ok"] > 0:
            notes.append("focus 修好")
        elif deltas["focus_ok"] < 0:
            notes.append("focus 退化")
        if deltas["obligation_ok"] > 0:
            notes.append("obligation 修好")
        elif deltas["obligation_ok"] < 0:
            notes.append("obligation 退化")
        if deltas["memory_ok"] > 0:
            notes.append("memory 修好")
        elif deltas["memory_ok"] < 0:
            notes.append("memory 退化")
        if deltas["generic_reply"] < 0:
            notes.append("空話減少")
        elif deltas["generic_reply"] > 0:
            notes.append("空話增加")
        if deltas["expected_proxy_persist_rate"] < 0:
            notes.append("壞 proxy 降低")
        elif deltas["expected_proxy_persist_rate"] > 0:
            notes.append("壞 proxy 增加")

        row = {
            "id": case_id,
            "language": after.get("language") or before.get("language"),
            "failure_types": after.get("failure_types") or before.get("failure_types") or [],
            "prompt": after.get("prompt") or before.get("prompt"),
            "before_observed_reply": before.get("observed_reply"),
            "before_replayed_reply": before.get("replayed_reply"),
            "after_replayed_reply": after.get("replayed_reply"),
            "before_score": before_score,
            "after_score": after_score,
            "delta_score": delta_score,
            "before_overall_auto_pass": before_pass,
            "after_overall_auto_pass": after_pass,
            "deltas": deltas,
            "notes": notes,
        }
        if delta_score > 0:
            improved.append(row)
        elif delta_score < 0:
            regressed.append(row)
        else:
            unchanged.append(row)

    improved.sort(key=lambda row: (row["delta_score"], row["after_overall_auto_pass"]), reverse=True)
    regressed.sort(key=lambda row: (row["delta_score"], row["after_overall_auto_pass"]))

    return {
        "summary": {
            "shared_case_count": len(shared_ids),
            "improved_case_count": len(improved),
            "regressed_case_count": len(regressed),
            "unchanged_case_count": len(unchanged),
            "new_case_count": len(new_cases),
            "removed_case_count": len(removed_cases),
        },
        "headline": {
            "top_improved_case_ids": [row["id"] for row in improved[:10]],
            "top_regressed_case_ids": [row["id"] for row in regressed[:10]],
            "new_case_ids": new_cases[:10],
            "removed_case_ids": removed_cases[:10],
        },
        "examples": {
            "improved": improved[:10],
            "regressed": regressed[:10],
        },
    }


def build_report(before_payload, after_payload, before_path, after_path):
    before_summary = before_payload.get("summary") or {}
    after_summary = after_payload.get("summary") or {}

    # 嘗試抓取 baseline meta 資訊 (若 before_path 是快照)
    baseline_label = "unknown"
    baseline_created_at = None
    if before_path and before_path.endswith(".json") and not before_path.endswith(".meta.json"):
        meta_path = before_path.replace(".json", ".meta.json")
        if os.path.exists(meta_path):
            meta = _load_json(meta_path)
            baseline_label = meta.get("label", "manual")
            baseline_created_at = meta.get("created_at")

    metrics = []
    for key, label_zh, direction in METRIC_SPECS:
        delta_row = _metric_delta(before_summary.get(key), after_summary.get(key), direction)
        delta_row.update({"key": key, "label_zh": label_zh, "direction": direction})
        metrics.append(delta_row)

    improved = [row for row in metrics if row["status"] == "improved"]
    regressed = [row for row in metrics if row["status"] == "regressed"]
    unchanged = [row for row in metrics if row["status"] == "no_change"]

    failure_rows = _failure_rows(
        before_payload.get("failure_type_summary"),
        after_payload.get("failure_type_summary"),
    )
    case_changes = _case_changes(before_payload, after_payload)

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "before_path": before_path,
        "after_path": after_path,
        "baseline_provenance": {
            "path": before_path,
            "label": baseline_label,
            "created_at": baseline_created_at,
        },
        "summary": {
            "before_total_cases": int(before_summary.get("total_cases") or 0),
            "after_total_cases": int(after_summary.get("total_cases") or 0),
            "delta_total_cases": int(after_summary.get("total_cases") or 0) - int(before_summary.get("total_cases") or 0),
            "metric_count": len(metrics),
            "improved_metric_count": len(improved),
            "regressed_metric_count": len(regressed),
            "unchanged_metric_count": len(unchanged),
            **case_changes["summary"],
        },
        "metric_deltas": metrics,
        "failure_type_deltas": failure_rows,
        "language_deltas": _language_rows(before_summary, after_summary),
        "headline": {
            "improved_metrics": [row["key"] for row in improved[:8]],
            "regressed_metrics": [row["key"] for row in regressed[:8]],
            **case_changes["headline"],
        },
        "case_change_examples": case_changes["examples"],
    }
    return report


def build_markdown(report):
    summary = report.get("summary") or {}
    prov = report.get("baseline_provenance") or {}
    lines = [
        "# Human Feedback Regression Diff Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- baseline_label: `{prov.get('label', 'unknown')}`",
        f"- baseline_created_at: `{prov.get('created_at', 'unknown')}`",
        f"- before_path: `{report.get('before_path')}`",
        f"- after_path: `{report.get('after_path')}`",
        "",
        "## Summary",
        "",
        f"- before_total_cases: {summary.get('before_total_cases', 0)}",
        f"- after_total_cases: {summary.get('after_total_cases', 0)}",
        f"- delta_total_cases: {summary.get('delta_total_cases', 0)}",
        f"- improved_metric_count: {summary.get('improved_metric_count', 0)}",
        f"- regressed_metric_count: {summary.get('regressed_metric_count', 0)}",
        f"- unchanged_metric_count: {summary.get('unchanged_metric_count', 0)}",
        f"- shared_case_count: {summary.get('shared_case_count', 0)}",
        f"- improved_case_count: {summary.get('improved_case_count', 0)}",
        f"- regressed_case_count: {summary.get('regressed_case_count', 0)}",
        f"- unchanged_case_count: {summary.get('unchanged_case_count', 0)}",
        f"- new_case_count: {summary.get('new_case_count', 0)}",
        f"- removed_case_count: {summary.get('removed_case_count', 0)}",
        "",
        "## Metric Deltas",
        "",
    ]
    for row in report.get("metric_deltas") or []:
        lines.append(
            f"- {row.get('key')} ({row.get('label_zh')}): before={row.get('before')} after={row.get('after')} "
            f"delta={row.get('delta')} status={row.get('status')} direction={row.get('direction')}"
        )

    lines.extend(["", "## Failure Type Deltas", ""])
    for row in report.get("failure_type_deltas") or []:
        lines.append(
            f"- {row.get('code')} ({row.get('label_zh')}): resolved {row.get('before_resolved_rate')} -> {row.get('after_resolved_rate')} "
            f"(delta {row.get('delta_resolved_rate')}) unresolved {row.get('before_unresolved_count')} -> {row.get('after_unresolved_count')} "
            f"(delta {row.get('delta_unresolved_count')}) status={row.get('status')}"
        )
    if not (report.get("failure_type_deltas") or []):
        lines.append("- none")

    lines.extend(["", "## Language Deltas", ""])
    for row in report.get("language_deltas") or []:
        lines.append(
            f"- {row.get('language')}: overall_auto_pass {row.get('before_overall_auto_pass_rate')} -> {row.get('after_overall_auto_pass_rate')} "
            f"(delta {row.get('delta_overall_auto_pass_rate')}), generic_reply {row.get('before_generic_reply_rate')} -> {row.get('after_generic_reply_rate')} "
            f"(delta {row.get('delta_generic_reply_rate')})"
        )
    if not (report.get("language_deltas") or []):
        lines.append("- none")

    lines.extend(["", "## Changed Cases", ""])
    for label, rows in (
        ("Improved", (report.get("case_change_examples") or {}).get("improved") or []),
        ("Regressed", (report.get("case_change_examples") or {}).get("regressed") or []),
    ):
        lines.append(f"### {label}")
        if not rows:
            lines.append("- none")
            continue
        for row in rows:
            lines.append(
                f"- id={row.get('id')} lang={row.get('language')} failure={row.get('failure_types')} "
                f"score {row.get('before_score')} -> {row.get('after_score')} "
                f"(delta {row.get('delta_score')}) notes={row.get('notes')} "
                f"prompt={row.get('prompt')} reply_before={row.get('before_replayed_reply')} "
                f"reply_after={row.get('after_replayed_reply')}"
            )

    return "\n".join(lines) + "\n"


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two human feedback regression eval reports.")
    parser.add_argument("--before", default=None, help="Path to baseline eval json. Defaults to latest snapshot.")
    parser.add_argument("--after", default=HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH)
    parser.add_argument("--snapshot-dir", default=HUMAN_FEEDBACK_REGRESSION_EVAL_SNAPSHOTS_DIR)
    parser.add_argument("--out-json", default=HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_JSON_PATH)
    parser.add_argument("--out-md", default=HUMAN_FEEDBACK_REGRESSION_DIFF_REPORT_MD_PATH)
    return parser.parse_args()


def main():
    args = parse_args()
    before_path = args.before or _latest_snapshot_json(args.snapshot_dir)
    after_path = args.after

    if not before_path:
        raise SystemExit("missing baseline snapshot: use snapshot_human_feedback_regression_eval.py first or pass --before")
    if not os.path.exists(after_path):
        raise SystemExit(f"missing after report: {after_path}")

    before_payload = _load_json(before_path)
    after_payload = _load_json(after_path)
    report = build_report(before_payload, after_payload, before_path, after_path)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(args.out_json)
    print(args.out_md)
    print(json.dumps(report.get("summary") or {}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
