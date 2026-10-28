from p4_r_multiturn_interference_probe import _recent_lexical_value, _timestamp


def test_recent_lexical_baseline_uses_only_frozen_window_and_latest_surface_mention():
    turns = [
        {"turn": 1, "user": "今は開発用茶が好き。"},
        {"turn": 2, "user": "普通の話。"},
        {"turn": 3, "user": "友達は妨害用茶が好き。"},
        {"turn": 4, "user": "さらに普通の話。"},
    ]
    value, source_turn = _recent_lexical_value(
        turns,
        window=3,
        lexicon=["開発用茶", "妨害用茶"],
    )
    assert value == "妨害用茶"
    assert source_turn == 3


def test_recent_lexical_baseline_returns_no_answer_when_window_has_no_surface_token():
    value, source_turn = _recent_lexical_value(
        [{"turn": 1, "user": "何も飲み物を言ってない。"}],
        window=5,
        lexicon=["開発用茶"],
    )
    assert value is None
    assert source_turn is None


def test_frozen_reference_times_are_ordered_and_already_elapsed():
    assert _timestamp(1) == "2026-09-22T06:01:00+08:00"
    assert _timestamp(12) == "2026-09-22T06:12:00+08:00"
