from copy import deepcopy

import pytest

import p3_b52_metadata_only_source_freeze as v1
import p3_b52_metadata_only_source_freeze_v2 as v2


def test_v2_changes_only_transport_and_preserves_selection_contract():
    base = v1.load_contract()
    effective = v2.build_effective_contract()

    for key in (
        "research_task",
        "target",
        "candidate_window",
        "candidate_schema",
        "selection",
        "bindings",
        "execution_boundary",
    ):
        assert effective[key] == base[key]
    assert effective["retrieval_policy"]["flat_playlist"] is False
    assert effective["retrieval_policy"]["title_output"] is False
    assert effective["retrieval_policy"]["description_output"] is False


def test_allowlisted_transport_line_emits_only_candidate_schema():
    effective = v2.build_effective_contract()
    line = (
        "fresh-id\tUC5LyYg6cCA4yHEYvtUsir3g\t20260601\t3600"
        "\tpublic\twas_live"
    )
    row = v2._parse_allowlisted_line(line, effective)

    assert set(row) == set(effective["candidate_schema"]["allowed_keys"])
    assert row["published_at"] == "2026-06-01"
    assert row["duration_seconds"] == 3600


def test_transport_rejects_extra_or_missing_stdout_columns():
    effective = v2.build_effective_contract()
    with pytest.raises(v1.B52ContractError, match="column_count"):
        v2._parse_allowlisted_line("a\tb\tc", effective)
    with pytest.raises(v1.B52ContractError, match="column_count"):
        v2._parse_allowlisted_line("a\tb\tc\td\te\tf\tg", effective)


def test_v2_config_cannot_change_frozen_candidate_count():
    config = v2.load_v2_config()
    changed = deepcopy(config)
    changed["retrieval_override"]["maximum_playlist_entries_requested"] = 10

    with pytest.raises(v1.B52ContractError, match="maximum_playlist_entries_changed"):
        v2.build_effective_contract(changed)


def test_second_attempt_policy_is_exactly_one_and_fail_closed():
    config = v2.load_v2_config()
    assert config["second_attempt_policy"] == {
        "maximum_additional_live_retrieval_attempts": 1,
        "empty_or_failed_result": "retain_and_end_b52_without_a_source",
        "post_result_retuning": False,
    }


def test_v2_implementation_is_frozen_before_second_attempt():
    report = v2.validate_implementation_freeze()

    assert report == {
        "valid": True,
        "v1_failed_attempts_retained": 1,
        "v2_live_retrieval_count_at_freeze": 0,
        "target_segment_access_count_at_freeze": 0,
        "model_call_count_at_freeze": 0,
    }
