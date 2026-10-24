from __future__ import annotations

import json
import copy
from pathlib import Path
import unittest

from longitudinal_human_model.rolling import available_events, materialize_cutoff, observable_memory_signals
from longitudinal_human_model.temporal import validate_temporal_dataset
from run_m8_rolling_scaling import run_experiment, validate_inputs


ROOT=Path(__file__).resolve().parent


class M8RollingRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset=json.loads((ROOT/"datasets/m8_rolling_semantic_synthetic_fixture_v1.json").read_text())
        cls.config=json.loads((ROOT/"configs/m8_rolling_scaling_preregistration.json").read_text())

    def test_all_cutoffs_pass_strict_temporal_validation(self):
        result=validate_inputs(self.dataset,self.config)
        self.assertTrue(result["valid"],result["errors"])
        self.assertEqual(0,result["future_leakage_violations"])
        self.assertEqual([8,12,16,20],result["history_counts"])
        for cutoff in self.config["rolling_cutoffs"]:
            self.assertTrue(validate_temporal_dataset(materialize_cutoff(self.dataset,cutoff))["valid"])

    def test_history_volume_is_a_real_information_intervention(self):
        self.assertEqual(0,len(available_events(self.dataset,"E4",0)))
        self.assertEqual(2,len(available_events(self.dataset,"E4",2)))
        self.assertEqual(20,len(available_events(self.dataset,"E4",None)))

    def test_memory_signals_do_not_read_current_outcome(self):
        history=available_events(self.dataset,"E1",2)
        names=self.dataset["event_feature_names"]
        extracted={row["event_id"]:row["event_features"] for row in self.dataset["events"]}
        current=next(row for row in self.dataset["events"] if row["event_id"]=="E1-01")
        signals=observable_memory_signals(current["event_features"],history,extracted,names)
        changed=dict(current); changed["actual_observed_behavior"]="direct_rejection"
        self.assertEqual(signals,observable_memory_signals(changed["event_features"],history,extracted,names))
        self.assertTrue(all(0<=value<=1 for value in signals.values()))

    def test_full_fake_provider_executes_exact_registered_call_graph(self):
        config=copy.deepcopy(self.config)
        config["predictor"]["epochs"]=10
        m5_dataset=json.loads((ROOT/config["m5_dataset"]["path"]).read_text())
        m5_result=json.loads((ROOT/config["m5_result"]["path"]).read_text())
        overlay=json.loads((ROOT/config["m6_overlay"]["path"]).read_text())
        labels=self.dataset["taxonomy"]["labels"]

        def provider(**kwargs):
            prompt=json.loads(kwargs["prompt"])
            if prompt["task"].startswith("Estimate only the observable"):
                text=json.dumps({"features":{name:.5 for name in self.dataset["event_feature_names"]}})
            elif prompt["task"].startswith("Condense"):
                text=json.dumps({"summary":"Frozen fictional history summary."})
            else:
                text=json.dumps({"probabilities":{label:1/len(labels) for label in labels},"brief_evidence":"fixture"})
            return {"text":text,"prompt_tokens":10,"completion_tokens":5,"latency_seconds":.01,"model_reported":"fixture-provider"}

        result=run_experiment(self.dataset,config,m5_dataset,m5_result,overlay,provider=provider)
        self.assertTrue(result["engineering_gate_pass"])
        self.assertEqual(108,result["resources"]["total_model_calls"])
        self.assertEqual(16,len([row for row in result["rows"] if row["condition"]=="OURS_HYBRID"]))
        self.assertEqual(8,len(result["history_scaling_metrics"]))
        self.assertEqual(5,len(result["seed_metrics"]))


if __name__=="__main__": unittest.main()
