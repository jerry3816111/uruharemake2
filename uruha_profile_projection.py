"""Project persistent profile candidates into the existing session profile contract."""

from __future__ import annotations

import datetime as dt


def _time_key(candidate):
    value = (candidate.get("metadata") or {}).get("valid_from") or (candidate.get("metadata") or {}).get("timestamp") or ""
    try:
        return dt.datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def project_profile_candidates(candidates):
    profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}

    def add_recent(field, value):
        profile[field] = [value, *[item for item in profile[field] if item.casefold() != value.casefold()]][:8]

    for candidate in sorted(candidates or [], key=_time_key):
        metadata = candidate.get("metadata") or {}
        fact_type = str(metadata.get("fact_type") or "").casefold()
        value = str(metadata.get("value") or "").strip()
        if not value:
            continue
        if fact_type == "name":
            profile["name"] = value
        elif fact_type == "like":
            add_recent("likes", value)
        elif fact_type == "dislike":
            add_recent("dislikes", value)
        elif fact_type == "favorite":
            add_recent("favorites", value)
    return profile
