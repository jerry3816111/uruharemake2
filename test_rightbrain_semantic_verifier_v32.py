import unittest

from rightbrain_semantic_verifier_v32 import (
    CONDITIONS,
    analyze_japanese,
    match_group,
    match_marker,
)
from uruha_brain_mac import RightBrain


class RightBrainSemanticVerifierV32Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rightbrain = RightBrain.__new__(RightBrain)

    def legacy_hit(self, reply, marker):
        return self.rightbrain._semantic_marker_hit(reply, marker)

    def test_conditions_are_frozen(self):
        self.assertEqual(
            CONDITIONS,
            (
                "legacy_control",
                "lemma_polarity",
                "lemma_polarity_reading",
            ),
        )

    def test_legacy_hits_are_preserved(self):
        trace = match_marker(
            "理由はまだ分かんない。",
            "分から",
            "lemma_polarity",
            self.legacy_hit,
        )
        self.assertTrue(trace.hit)
        self.assertEqual(trace.mode, "legacy")

    def test_dictionary_form_recovers_adjective_inflection(self):
        control = match_marker(
            "今日は軽く食べたい。",
            "軽い",
            "legacy_control",
            self.legacy_hit,
        )
        treatment = match_marker(
            "今日は軽く食べたい。",
            "軽い",
            "lemma_polarity",
            self.legacy_hit,
        )
        self.assertFalse(control.hit)
        self.assertTrue(treatment.hit)
        self.assertEqual(treatment.mode, "lemma")

    def test_dictionary_form_does_not_reverse_positive_polarity(self):
        trace = match_marker(
            "今日は全然軽くない。",
            "軽い",
            "lemma_polarity",
            self.legacy_hit,
        )
        self.assertFalse(trace.hit)

    def test_negative_marker_can_match_negative_inflection(self):
        trace = match_marker(
            "理由はまだ分かんない。",
            "分から",
            "lemma_polarity",
            lambda _reply, _marker: False,
        )
        self.assertTrue(trace.hit)
        self.assertEqual(trace.mode, "lemma")
        self.assertTrue(trace.marker_negative)
        self.assertTrue(trace.reply_negative)

    def test_pronunciation_condition_recovers_kana_kanji_surface(self):
        lemma_only = match_marker(
            "提出まで終わったな、お疲れ。",
            "おつかれ",
            "lemma_polarity",
            self.legacy_hit,
        )
        reading = match_marker(
            "提出まで終わったな、お疲れ。",
            "おつかれ",
            "lemma_polarity_reading",
            self.legacy_hit,
        )
        self.assertFalse(lemma_only.hit)
        self.assertTrue(reading.hit)
        self.assertEqual(reading.mode, "reading")

    def test_pronunciation_condition_exposes_homophone_risk(self):
        trace = match_marker(
            "この漢字は難しい。",
            "かんじ",
            "lemma_polarity_reading",
            self.legacy_hit,
        )
        self.assertTrue(trace.hit)
        self.assertEqual(trace.mode, "reading")

    def test_group_trace_preserves_marker_level_evidence(self):
        hit, traces = match_group(
            "今日は軽く食べたい。",
            ["重い", "軽い"],
            "lemma_polarity",
            self.legacy_hit,
        )
        self.assertTrue(hit)
        self.assertEqual(len(traces), 2)
        self.assertEqual([trace.hit for trace in traces], [False, True])

    def test_frontend_exposes_dictionary_form(self):
        tokens = analyze_japanese("軽く食べたい")
        self.assertTrue(
            any(token.surface == "軽く" and token.lemma == "軽い" for token in tokens)
        )

    def test_unknown_condition_fails_closed(self):
        with self.assertRaises(ValueError):
            match_marker("軽く食べる", "軽い", "unknown", self.legacy_hit)


if __name__ == "__main__":
    unittest.main()
