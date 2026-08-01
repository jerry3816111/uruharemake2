"""Select and verify only preregistered non-holdout public-persona sources."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TARGET_MANIFEST = ROOT / "datasets/public_persona_reference_source_manifest_v2.json"
CONTRAST_MANIFEST = ROOT / "datasets/public_persona_contrast_source_manifest_v4.json"
USER_AGENT = "UruhaBrain-Public-Metadata-Audit/1.0"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_sources(target_manifest, contrast_manifest):
    target = [
        dict(source, source_group="target_calibration")
        for source in target_manifest["sources"]
        if source.get("dataset_role") == "calibration"
        and source.get("source_type") == "official_public_stream_archive"
        and source.get("sealed") is False
    ]
    contrast = [
        dict(source, source_group="matched_contrast")
        for source in contrast_manifest["sources"]
        if source.get("dataset_role") == "contrast_calibration"
        and source.get("source_type") == "official_public_stream_archive"
    ]
    selected = sorted(target + contrast, key=lambda source: source["source_id"])
    if len(target) != 3 or len(contrast) != 9 or len(selected) != 12:
        raise ValueError("V8 source accounting drift")
    if any(source.get("sealed") is True or source.get("dataset_role") == "final_holdout" for source in selected):
        raise ValueError("V8 selection attempted to include a final holdout")
    if len({source["source_id"] for source in selected}) != len(selected):
        raise ValueError("V8 duplicate source id")
    return selected


def _request(url, timeout_seconds):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
        status = int(response.status)
    return status, body, round(time.monotonic() - started, 6)


def parse_watch_metadata(html):
    channel_matches = re.findall(r'"channelId":"([A-Za-z0-9_-]+)"', html)
    date_match = re.search(
        r'<meta\s+itemprop="datePublished"\s+content="(\d{4}-\d{2}-\d{2})', html
    ) or re.search(r'"publishDate":"(\d{4}-\d{2}-\d{2})', html)
    return {
        "channel_id": channel_matches[0] if channel_matches else None,
        "published_date": date_match.group(1) if date_match else None,
    }


def verify_source(source, timeout_seconds=15):
    video_id = source["video_id"]
    watch_url = f"https://www.youtube.com/watch?v={urllib.parse.quote(video_id)}"
    oembed_url = (
        "https://www.youtube.com/oembed?"
        + urllib.parse.urlencode({"url": watch_url, "format": "json"})
    )
    errors = []
    oembed_status = None
    watch_status = None
    oembed_elapsed = None
    watch_elapsed = None
    author_url = None
    observed = {"channel_id": None, "published_date": None}
    try:
        oembed_status, oembed_body, oembed_elapsed = _request(oembed_url, timeout_seconds)
        oembed = json.loads(oembed_body)
        author_url = str(oembed.get("author_url") or "") or None
    except Exception as exc:
        errors.append(f"oembed:{type(exc).__name__}")
    try:
        watch_status, watch_body, watch_elapsed = _request(watch_url, timeout_seconds)
        observed = parse_watch_metadata(watch_body)
    except Exception as exc:
        errors.append(f"watch:{type(exc).__name__}")
    return {
        "source_id": source["source_id"],
        "source_group": source["source_group"],
        "actor_id": source["actor_id"],
        "video_id": video_id,
        "expected_channel_id": source["publisher_channel_id"],
        "observed_channel_id": observed["channel_id"],
        "channel_match": observed["channel_id"] == source["publisher_channel_id"],
        "expected_published_date": source["published_at"],
        "observed_published_date": observed["published_date"],
        "published_date_match": observed["published_date"] == source["published_at"],
        "oembed_resolved": oembed_status == 200 and author_url is not None,
        "watch_metadata_resolved": watch_status == 200
        and observed["channel_id"] is not None
        and observed["published_date"] is not None,
        "oembed_author_url": author_url,
        "oembed_elapsed_seconds": oembed_elapsed,
        "watch_elapsed_seconds": watch_elapsed,
        "errors": errors,
        "stored_title": False,
        "stored_description": False,
        "stored_transcript": False,
        "behavior_content_reviewed": False,
    }


def summarize(rows):
    return {
        "source_count": len(rows),
        "target_calibration_count": sum(row["source_group"] == "target_calibration" for row in rows),
        "matched_contrast_count": sum(row["source_group"] == "matched_contrast" for row in rows),
        "oembed_resolution_count": sum(row["oembed_resolved"] for row in rows),
        "watch_metadata_resolution_count": sum(row["watch_metadata_resolved"] for row in rows),
        "publisher_channel_match_count": sum(row["channel_match"] for row in rows),
        "publication_date_match_count": sum(row["published_date_match"] for row in rows),
        "request_error_count": sum(len(row["errors"]) for row in rows),
        "final_holdout_source_request_count": 0,
        "behavior_content_review_count": sum(row["behavior_content_reviewed"] for row in rows),
        "stored_title_count": sum(row["stored_title"] for row in rows),
        "stored_description_count": sum(row["stored_description"] for row in rows),
        "stored_transcript_count": sum(row["stored_transcript"] for row in rows),
        "request_count": len(rows) * 2,
        "model_call_count": 0,
        "production_memory_write_count": 0,
    }
