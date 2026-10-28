from copy import deepcopy

import pytest

import p3_b52_metadata_only_source_freeze as v1
import p3_b52_metadata_only_source_freeze_v3 as v3


def atom_fixture():
    return b"""<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'
          xmlns:yt='http://www.youtube.com/xml/schemas/2015'
          xmlns:media='http://search.yahoo.com/mrss/'>
      <entry>
        <yt:videoId>fresh-b</yt:videoId>
        <yt:channelId>UC5LyYg6cCA4yHEYvtUsir3g</yt:channelId>
        <published>2026-06-02T10:00:00+00:00</published>
        <title>FORBIDDEN TITLE</title>
        <media:group><media:description>FORBIDDEN DESCRIPTION</media:description></media:group>
      </entry>
      <entry>
        <yt:videoId>fresh-a</yt:videoId>
        <yt:channelId>UC5LyYg6cCA4yHEYvtUsir3g</yt:channelId>
        <published>2026-05-01T10:00:00+00:00</published>
        <title>ANOTHER FORBIDDEN TITLE</title>
      </entry>
    </feed>"""


def exclusions(*ids):
    return {"excluded_video_ids": list(ids)}


def postcheck_row(video_id, published_at, *, duration=3600, live_status="was_live"):
    return {
        "source_id": f"youtube_{video_id}",
        "platform": "youtube",
        "video_id": video_id,
        "publisher_channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "published_at": published_at,
        "duration_seconds": duration,
        "availability": "public",
        "live_status": live_status,
    }


def test_contract_preserves_v1_semantics_and_closes_execution_boundary():
    report = v3.validate_contract()
    assert report["valid"] is True
    assert report["errors"] == []
    assert all(report["unchanged_v1_checks"].values())


def test_atom_parser_ignores_title_description_and_emits_exact_schema():
    rows = v3.parse_atom_metadata(atom_fixture())
    allowed = set(v3.load_config()["preselection"]["allowed_keys"])

    assert len(rows) == 2
    assert all(set(row) == allowed for row in rows)
    assert "FORBIDDEN" not in str(rows)


def test_atom_selection_is_order_independent_and_excludes_known_ids():
    rows = v3.parse_atom_metadata(atom_fixture())
    first = v3.select_atom_source(rows, exclusions=exclusions("fresh-b"))
    second = v3.select_atom_source(
        list(reversed(rows)), exclusions=exclusions("fresh-b")
    )

    assert first["selected_video_id"] == "fresh-a"
    assert first["preselection_receipt_hash"] == second["preselection_receipt_hash"]
    assert first["selected_id_locked_before_postcheck"] is True


def test_preselection_rejects_any_content_field():
    rows = v3.parse_atom_metadata(atom_fixture())
    rows[0]["title"] = "must fail"
    with pytest.raises(v1.B52ContractError, match="forbidden"):
        v3.select_atom_source(rows, exclusions=exclusions())


def test_postcheck_pass_reserves_exact_preselected_id():
    selected = v3.select_atom_source(
        v3.parse_atom_metadata(atom_fixture()), exclusions=exclusions()
    )
    metadata = postcheck_row(
        selected["selected_video_id"], selected["selected_published_at"]
    )
    result = v3.finalize_no_replacement(selected, metadata)

    assert result["status"] == "source_reserved_postcheck_passed"
    assert result["postcheck_accepted"] is True
    assert result["automatic_replacement_performed"] is False
    assert result["model_call_count"] == 0


def test_postcheck_failure_keeps_same_id_and_never_selects_runner_up():
    rows = v3.parse_atom_metadata(atom_fixture())
    selected = v3.select_atom_source(rows, exclusions=exclusions())
    other = next(row for row in rows if row["video_id"] != selected["selected_video_id"])
    metadata = postcheck_row(
        other["video_id"], other["published_at"], duration=60, live_status="not_live"
    )
    result = v3.finalize_no_replacement(selected, metadata)

    assert result["status"] == "selected_source_ineligible_no_replacement"
    assert result["selected_video_id"] == selected["selected_video_id"]
    assert result["automatic_replacement_performed"] is False
    assert "selected_video_id_changed" in result["postcheck_reasons"]


def test_reviewed_sequence_cannot_be_mutated_to_auto_replacement():
    config = v3.load_config()
    changed = deepcopy(config)
    changed["postselection_check"]["automatic_replacement"] = True
    report = v3.validate_contract(changed)

    assert report["valid"] is False
    assert "automatic_replacement_must_be_false" in report["errors"]


def test_v3_implementation_is_frozen_before_network_access():
    report = v3.validate_implementation_freeze()
    assert report == {
        "valid": True,
        "reviewed_option": "C_official_atom_preselection_then_no_replacement_postcheck",
        "atom_retrieval_count_at_freeze": 0,
        "selected_id_postcheck_count_at_freeze": 0,
        "target_segment_access_count_at_freeze": 0,
    }
