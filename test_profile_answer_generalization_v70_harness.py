import inspect, json, tempfile, unittest
from pathlib import Path
import chromadb
import analyze_profile_answer_generalization_v70 as analyzer
import run_profile_answer_generalization_v70 as runner
from uruha_profile_memory import compile_profile_memory_record, read_profile_candidates
from uruha_profile_projection import project_profile_candidates

ROOT=Path(__file__).resolve().parent
class ProfileAnswerV70HarnessTests(unittest.TestCase):
    def test_projector_preserves_buckets_and_latest_name(self):
        rows=[]
        for i,(kind,value) in enumerate([("name","Old"),("name","New"),("like","tea"),("dislike","coffee")]):
            r=compile_profile_memory_record(kind,value,timestamp=f"2026-01-0{i+1}T00:00:00+09:00",memory_id=str(i),typed_state=True); rows.append({"memory_id":r["memory_id"],"metadata":r["metadata"]})
        self.assertEqual(project_profile_candidates(rows),{"name":"New","likes":["tea"],"dislikes":["coffee"],"favorites":[]})
    def test_real_chroma_conditions_change_only_selected_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            c=chromadb.PersistentClient(path=d).get_or_create_collection("v70_probe")
            history=[{"memory_id":"old","fact_type":"like","value":"tea","timestamp":"2026-01-01T00:00:00+09:00"},{"memory_id":"new","fact_type":"dislike","value":"tea","timestamp":"2026-01-02T00:00:00+09:00"}]; runner._seed(c,history); candidates=read_profile_candidates(c)
            self.assertEqual(len(runner._selected(candidates,runner.CONDITIONS[1],history[-1]["timestamp"])),2)
            self.assertEqual(len(runner._selected(candidates,runner.CONDITIONS[2],history[-1]["timestamp"])),1)
    def test_runner_never_reads_expected(self):
        self.assertNotIn("expected",inspect.getsource(runner.run_case)); self.assertNotIn("DB_PATH",inspect.getsource(runner.run_case))
    def test_projector_contains_no_holdout_values(self):
        source=(ROOT/"uruha_profile_projection.py").read_text(encoding="utf-8")
        data=json.loads((ROOT/"datasets/profile_answer_generalization_v70.json").read_text(encoding="utf-8"))
        for case in data["cases"]:
            self.assertNotIn(case["id"],source)
            for row in case["profile_history"]: self.assertNotIn(row["value"],source)

    def _synthetic_inputs(self, treatment_reply):
        cases=[]; rows=[]
        for index in range(24):
            case_id=f"synthetic_{index:02d}"
            cases.append({"id":case_id,"scenario_family":"synthetic","expected":{"required_marker_groups":[["CURRENT"]],"forbidden_terms":["STALE"],"memory_relevant":index<16,"abstention_required":index>=20}})
            for condition in runner.CONDITIONS:
                reply=treatment_reply if condition==runner.CONDITIONS[2] else "CONTROL"
                rows.append({"case_id":case_id,"condition":condition,"reply":reply,"surface_gate_pass":True,"projection_seconds":0.001,"turn_seconds":1.0})
        raw={"row_count":72,"conditions":list(runner.CONDITIONS),"gold_in_raw":False,"locked_preflight":{"passed":True,"observed_test_count":15,"expected_test_count":15},"rightbrain_model_loading":False,"transport_error_count":0,"production_database_access_count":0,"physical_action_count":0,"rows":[{**row,"temporary_database":True} for row in rows]}
        prereg={"treatment_success_gates":{"relevant_case_pass_count_min":14,"overall_case_pass_count_min":21,"required_marker_group_recall_min":0.9,"stale_or_forbidden_term_case_count_max":0,"irrelevant_profile_intrusion_count_max":0,"abstention_pass_count_min":3,"newly_passed_vs_append_only_min":4,"regressions_vs_append_only_max":1,"newly_passed_vs_session_only_min":8,"surface_gate_regression_vs_session_only_max":1,"median_projection_seconds_max":0.005,"median_full_turn_seconds_max":8.0,"p95_full_turn_seconds_max":15.0,"transport_error_count_max":0,"production_database_access_count_max":0,"physical_action_count_max":0},"causal_boundary":"synthetic test"}
        return raw,{"cases":cases},prereg

    def test_analyzer_accepts_only_gate_passing_evidence(self):
        report=analyzer.analyze(*self._synthetic_inputs("CURRENT"))
        self.assertEqual(report["decision"],"authorize_answer_path_shadow")
        self.assertTrue(report["run_integrity"]["passed"])
        self.assertTrue(report["success_gates"]["passed"])

    def test_analyzer_freezes_stale_treatment(self):
        report=analyzer.analyze(*self._synthetic_inputs("STALE"))
        self.assertEqual(report["decision"],"freeze_and_keep_profile_out_of_answers")
        self.assertFalse(report["success_gates"]["passed"])
if __name__=="__main__": unittest.main()
