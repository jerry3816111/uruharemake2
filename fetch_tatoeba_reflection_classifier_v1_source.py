#!/usr/bin/env python3
"""Fetch the preregistered Tatoeba sentences without running either classifier."""

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
    / "reflection_classifier_v1_external_holdout_construction_preregistration.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "datasets"
    / "sources"
    / "tatoeba_reflection_classifier_v1_selected.json"
)
TZ = ZoneInfo("Asia/Tokyo")
USER_AGENT = "UruhaBrain-Research/1.0 (source snapshot; no model inference)"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_json(url: str, attempts: int = 3):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == attempts:
                raise
            time.sleep(attempt)


def fetch_snapshot(preregistration: dict):
    items = []
    endpoint = preregistration["external_source"]["stable_api"]
    for selected in preregistration["selected_cases"]:
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
        # Older Tatoeba sentences can legitimately have a null owner. Preserve that
        # official value instead of replacing the preregistered sentence.
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
        "schema": "uruha_tatoeba_reflection_classifier_source_snapshot_v1",
        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source": "Tatoeba official read-only API v1",
        "api_documentation": preregistration["external_source"][
            "api_documentation"
        ],
        "download_documentation": preregistration["external_source"][
            "download_documentation"
        ],
        "selection_preregistration": str(PREREG_PATH.relative_to(ROOT)),
        "classifier_or_model_inference_used": False,
        "item_count": len(items),
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite source snapshot: {args.output}")
    snapshot = fetch_snapshot(_load(PREREG_PATH))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
