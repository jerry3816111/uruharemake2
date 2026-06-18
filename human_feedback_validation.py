"""Validation helpers for human feedback annotation records.

These helpers keep the Web UI, annotation report, and regression dataset on the
same definition of a usable human-feedback row.  Historical logs may contain
empty placeholder rows, so downstream tooling must explicitly ignore them.
"""


VALID_VERDICTS = {"pass", "mixed", "fail"}
FAIL_LIKE_VERDICTS = {"mixed", "fail"}
VALID_SEVERITIES = {"low", "medium", "high"}


def _non_empty_text(value):
    return bool(str(value or "").strip())


def _non_empty_turn_index(value):
    return value is not None and str(value).strip() != ""


def normalize_failure_types(failure_types):
    output = []
    seen = set()
    for value in failure_types or []:
        code = str(value or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        output.append(code)
    return output


def invalid_turn_source_reason(record):
    if not isinstance(record, dict):
        return "turn source is not an object"
    if not _non_empty_text(record.get("session_id")):
        return "missing session_id"
    if not _non_empty_turn_index(record.get("turn_index")):
        return "missing turn_index"
    if not _non_empty_text(record.get("user_text")):
        return "missing user_text"
    if not _non_empty_text(record.get("assistant_reply")):
        return "missing assistant_reply"
    return ""


def is_valid_turn_source(record):
    return invalid_turn_source_reason(record) == ""


def invalid_annotation_reason(record, valid_failure_types=None):
    source_reason = invalid_turn_source_reason(record)
    if source_reason:
        return source_reason

    verdict = str(record.get("verdict") or "").strip()
    if verdict not in VALID_VERDICTS:
        return "invalid verdict"

    severity = str(record.get("severity") or "").strip()
    if severity not in VALID_SEVERITIES:
        return "invalid severity"

    failure_types = normalize_failure_types(record.get("failure_types"))
    if verdict in FAIL_LIKE_VERDICTS and not failure_types:
        return "mixed/fail annotation requires failure_types"

    if valid_failure_types is not None:
        allowed = set(valid_failure_types)
        unknown = [code for code in failure_types if code not in allowed]
        if unknown:
            return "unknown failure_types: " + ",".join(unknown)

    return ""


def is_valid_annotation_record(record, valid_failure_types=None):
    return invalid_annotation_reason(record, valid_failure_types=valid_failure_types) == ""


def split_valid_annotations(records, valid_failure_types=None):
    valid = []
    invalid = []
    for record in records or []:
        reason = invalid_annotation_reason(record, valid_failure_types=valid_failure_types)
        if reason:
            invalid.append({"reason": reason, "record": record})
        else:
            valid.append(record)
    return valid, invalid


def invalid_reason_counts(invalid_records):
    counts = {}
    for item in invalid_records or []:
        reason = str((item or {}).get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return [
        {"reason": reason, "count": count}
        for reason, count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    ]
