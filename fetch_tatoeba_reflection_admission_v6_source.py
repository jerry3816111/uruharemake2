#!/usr/bin/env python3
"""Fetch the preregistered V6 near-miss source sentences without Qwen."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_nearmiss_construction_preregistration.json"
)
DEFAULT_OUTPUT = (
    ROOT / "datasets" / "sources" / "tatoeba_reflection_admission_v6_selected.json"
)
TZ = ZoneInfo("Asia/Tokyo")
USER_AGENT = "UruhaBrain-Research/1.0 (V6 admission source; no Qwen inference)"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_json(url, attempts=6):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == attempts:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else float(attempt * 2)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == attempts:
                raise
            delay = float(attempt * 2)
        time.sleep(delay)
    raise RuntimeError("unreachable")


def fetch_snapshot(preregistration, request_interval_seconds=0.5):
    items = []
    endpoint = preregistration["external_source"]["stable_api"]
    for index, selected in enumerate(preregistration["selected_cases"]):
        if index:
            time.sleep(request_interval_seconds)
        sentence_id = selected["sentence_id"]
        api_url = endpoint.format(id=sentence_id) + "?showtrans=none"
        payload = _fetch_json(api_url)
        data = payload.get("data") or {}
        if data.get("id") != sentence_id:
            raise ValueError(f"Tatoeba ID mismatch for {sentence_id}")
        if data.get("lang") != selected["language"]:
            raise ValueError(f"Tatoeba language mismatch for {sentence_id}")
        if data.get("is_unapproved"):
            raise ValueError(f"Tatoeba sentence is unapproved: {sentence_id}")
        if not data.get("text") or not data.get("license") or "owner" not in data:
            raise ValueError(f"Tatoeba provenance is incomplete: {sentence_id}")
        items.append(
            {
                "sentence_id": sentence_id,
                "language": data["lang"],
                "text": data["text"],
                "owner": data["owner"],
                "license": data["license"],
                "is_unapproved": data["is_unapproved"],
                "api_url": api_url,
                "sentence_url": f"https://tatoeba.org/en/sentences/show/{sentence_id}",
            }
        )
    return {
        "schema": "uruha_tatoeba_reflection_admission_source_snapshot_v6",
        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source": "Tatoeba official read-only API v1",
        "api_documentation": preregistration["external_source"]["api_documentation"],
        "selection_preregistration": str(PREREG_PATH.relative_to(ROOT)),
        "constructor_ai_assistance_used": preregistration["construction_provenance"][
            "constructor_ai_assistance_used"
        ],
        "evaluated_qwen_model_inference_used": False,
        "item_count": len(items),
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--request-interval-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite source snapshot: {args.output}")
    snapshot = fetch_snapshot(
        _load(PREREG_PATH),
        request_interval_seconds=args.request_interval_seconds,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
