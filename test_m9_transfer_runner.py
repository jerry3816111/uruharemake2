from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from run_m9_second_person_transfer import run_experiment, validate_inputs


ROOT=Path(__file__).resolve().parent


class M9TransferRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/"configs/m9_second_person_transfer_preregistration.json").read_text()); cls.mira=json.loads((ROOT/cls.config["second_person_dataset"]["path"]).read_text()); cls.ren=json.loads((ROOT/cls.config["source_person_dataset"]["path"]).read_text()); cls.source=json.loads((ROOT/cls.config["source_person_result"]["path"]).read_text())

    def test_second_person_passes_unchanged_schema_and_cutoff_contract(self):
        result=validate_inputs(self.mira,self.ren,self.source,self.config)
        self.assertTrue(result["valid"],result["errors"]); self.assertEqual([8,12,16,20],result["history_counts"]); self.assertEqual(0,result["future_leakage_violations"])

    def test_full_fake_provider_runs_three_transfer_conditions_and_baselines(self):
        config=copy.deepcopy(self.config); config["predictor"]["epochs"]=10
        m5d=json.loads((ROOT/config["m5_dataset"]["path"]).read_text()); m5r=json.loads((ROOT/config["m5_result"]["path"]).read_text()); overlay=json.loads((ROOT/config["m6_overlay"]["path"]).read_text()); labels=self.mira["taxonomy"]["labels"]
        def provider(**kwargs):
            prompt=json.loads(kwargs["prompt"])
            if prompt["task"].startswith("Estimate only the observable"): text=json.dumps({name:.5 for name in self.mira["event_feature_names"]})
            elif prompt["task"].startswith("Condense"): text=json.dumps({"summary":"Second fictional person history."})
            else: text=json.dumps({"probabilities":{label:1/len(labels) for label in labels},"brief_evidence":"fixture"})
            return {"text":text,"prompt_tokens":10,"completion_tokens":5,"latency_seconds":.01,"model_reported":"fake"}
        result=run_experiment(self.mira,self.ren,self.source,config,m5d,m5r,overlay,provider=provider)
        self.assertTrue(result["engineering_gate_pass"]); self.assertEqual(108,result["resources"]["total_model_calls"]); self.assertEqual(48,len([r for r in result["rows"] if r.get("transfer_condition")]))
        self.assertEqual(0,sum(result["person_specific_core_mentions"].values()))


if __name__=="__main__": unittest.main()
