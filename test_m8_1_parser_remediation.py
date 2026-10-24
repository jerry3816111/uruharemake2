from __future__ import annotations

import json
import unittest

from longitudinal_human_model.rolling_parser_v1_1 import extract_event_features_bounded


class M81ParserRemediationTests(unittest.TestCase):
    def test_only_finite_numeric_boundaries_are_clamped_and_recorded(self):
        names=["a","b","c"]
        def provider(**kwargs):
            return {"text":json.dumps({"a":-0.2,"b":.4,"c":1.3}),"prompt_tokens":1,"completion_tokens":1,"latency_seconds":0,"model_reported":"fake"}
        result=extract_event_features_bounded("same frozen prompt",names,model="fake",provider=provider,options={})
        self.assertEqual({"a":0.0,"b":.4,"c":1.0},result["features"])
        self.assertEqual(2,len(result["numeric_boundary_normalizations"]))

    def test_nonfinite_and_key_mismatch_remain_fatal(self):
        def nonfinite(**kwargs): return {"text":json.dumps({"a":float("nan")})}
        with self.assertRaisesRegex(Exception,"finite"):
            extract_event_features_bounded("x",["a"],model="fake",provider=nonfinite,options={})
        def wrong(**kwargs): return {"text":json.dumps({"wrong":.2})}
        with self.assertRaisesRegex(Exception,"exact feature map"):
            extract_event_features_bounded("x",["a"],model="fake",provider=wrong,options={})


if __name__=="__main__": unittest.main()
