from __future__ import annotations

import json
import unittest

from longitudinal_human_model.summary_parser_v1_1 import SummaryAliasProvider


class M91SummaryAliasTests(unittest.TestCase):
    def test_equivalent_alias_is_normalized_and_raw_is_retained(self):
        raw=json.dumps({"behavior_prediction_summary":"observable history"})
        wrapped=SummaryAliasProvider(lambda **kwargs:{"text":raw})
        prompt=json.dumps({"task":"Condense the authorized observable history"})
        result=wrapped(model="fake",prompt=prompt,options={})
        self.assertEqual("observable history",json.loads(result["text"])["summary"])
        self.assertEqual(raw,wrapped.normalizations[0]["raw_response"])

    def test_non_summary_calls_and_existing_summary_are_untouched(self):
        raw=json.dumps({"behavior_prediction_summary":"x"}); wrapped=SummaryAliasProvider(lambda **kwargs:{"text":raw})
        self.assertEqual(raw,wrapped(model="fake",prompt=json.dumps({"task":"Predict"}),options={})["text"])
        good=json.dumps({"summary":"already valid"}); wrapped2=SummaryAliasProvider(lambda **kwargs:{"text":good})
        self.assertEqual(good,wrapped2(model="fake",prompt=json.dumps({"task":"Condense history"}),options={})["text"])
        self.assertEqual([],wrapped2.normalizations)


if __name__=="__main__": unittest.main()
