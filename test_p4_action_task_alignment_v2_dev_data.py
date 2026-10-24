"""Pre-model integrity checks for exposed B2 development data only.

These checks do not score semantic correctness or make these cases a holdout.
They ensure gold citations survive the same M45.1 clause preparation that both
prospective arms must receive; a quote spanning clauses cannot be copied as a
single exact citation into a source-bound frame.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path

from p4_action_transaction_scoring import prepare_source_case


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "datasets/p4_action_task_alignment_v2_dev_sources.json"
GOLD = ROOT / "datasets/p4_action_task_alignment_v2_dev_gold.json"
OLD_SOURCES = ROOT / "datasets/p4_action_transaction_v1_sources.json"
ROLES = {"request", "current", "target", "availability", "forbidden", "actor", "stop"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_dev_pair_counts_and_no_exact_old_source_reuse():
    cases = _load(SOURCES)["cases"]
    gold = _load(GOLD)["gold_by_case_id"]
    assert len(cases) == len(gold) == 12
    assert len({case["case_id"] for case in cases}) == 12
    assert {case["case_id"] for case in cases} == set(gold)
    counts = Counter((case["language"], case["variant"]) for case in cases)
    assert counts == Counter({(language, variant): 2
                              for language in ("zh-TW", "en", "ja")
                              for variant in ("valid", "invalid")})
    pairs = defaultdict(list)
    for case in cases:
        pairs[case["pair_id"]].append(case)
    assert len(pairs) == 6
    assert all({row["variant"] for row in rows} == {"valid", "invalid"}
               and len({row["language"] for row in rows}) == 1
               for rows in pairs.values())
    old_texts = {case["sources"][0]["text"] for case in _load(OLD_SOURCES)["cases"]}
    assert all(case["sources"][0]["text"] not in old_texts for case in cases)


def test_every_gold_span_is_exact_in_original_and_one_prepared_clause():
    for case in _load(SOURCES)["cases"]:
        original = case["sources"][0]
        prepared = prepare_source_case(case)
        clauses = prepared["sources"]
        assert clauses and all(row["kind"] == "current_user" for row in clauses)
        row = _load(GOLD)["gold_by_case_id"][case["case_id"]]
        assert set(row["evidence_spans"]) == ROLES
        assert all(row["evidence_spans"][role] for role in ROLES)
        spans = [span for role in ROLES for span in row["evidence_spans"][role]]
        if row["blocking_reason"] is not None:
            spans.extend(row["blocking_reason"]["blocking_spans"])
        for span in spans:
            assert span["source_id"] == original["id"]
            quote = span["quote"]
            assert quote and quote == quote.strip() and quote in original["text"]
            assert any(quote in clause["text"] for clause in clauses), (
                case["case_id"], span)


def test_gold_action_and_abstain_branches_are_exclusive():
    gold = _load(GOLD)["gold_by_case_id"]
    assert Counter(row["decision"] for row in gold.values()) == {
        "action": 6, "abstain": 6,
    }
    for row in gold.values():
        if row["decision"] == "action":
            assert row["acceptable_action_envelope"] is not None
            assert row["blocking_reason"] is None
            assert row["expected_reason_code"] == "none"
        else:
            assert row["acceptable_action_envelope"] is None
            reason = row["blocking_reason"]
            assert reason is not None and reason["blocking_spans"]
            assert reason["primary_code"] == row["expected_reason_code"]
            assert reason["primary_code"] in row["acceptable_reason_codes"]
