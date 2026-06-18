import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path to allow importing uruha_web_ui
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def _gr_update(**kwargs):
    return ("update", kwargs)


def _gr_skip():
    return ("skip", {})


# Mock Gradio before importing uruha_web_ui to avoid heavy initialization
fake_gradio = types.ModuleType("gradio")
fake_gradio.update = _gr_update
fake_gradio.skip = _gr_skip
sys.modules["gradio"] = fake_gradio
import gradio as gr

# Mock other heavy imports if necessary, but since they are lazy-loaded it might be okay.
fake_colorama = types.ModuleType("colorama")
fake_colorama.Fore = types.SimpleNamespace(CYAN="", YELLOW="")
fake_colorama.init = lambda autoreset=True: None
sys.modules["colorama"] = fake_colorama
sys.modules["uruha_brain_mac"] = MagicMock()
sys.modules["uruha_senses"] = MagicMock()

import uruha_web_ui
from project_paths import HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH

class RegressionPanelContractHarness(unittest.TestCase):
    """
    Formal Contract Harness for Regression Panel Logic.
    Verifies the alignment of picker, freshness, and diff panel across various scenarios.
    """

    def setUp(self):
        # Reset common mocks
        self.mock_exists = patch('os.path.exists').start()
        self.mock_load_json = patch('uruha_web_ui._load_json').start()
        self.mock_load_text = patch('uruha_web_ui._load_text').start()
        self.mock_getmtime = patch('os.path.getmtime').start()
        self.mock_subprocess = patch('subprocess.run').start()
        
        # Default mock behaviors
        self.mock_exists.return_value = True
        self.mock_load_json.return_value = {}
        self.mock_load_text.return_value = "## Regression Diff Report (Mocked)"
        self.mock_getmtime.return_value = 1000.0

    def tearDown(self):
        patch.stopall()

    def test_manual_diff_success(self):
        """Scenario: Manual diff succeeds with valid meta path."""
        meta_path = "/mock/path/snapshot.meta.json"
        self.mock_load_json.side_effect = lambda p: {
            "snapshot_json": "/mock/path/snapshot.json",
            "label": "test_label"
        } if p == meta_path else {}
        
        # Run manual diff
        msg, diff_md, diff_json, fresh_md = uruha_web_ui.run_regression_diff_manually(meta_path)
        
        self.assertIn("✅", msg)
        self.mock_subprocess.assert_called()
        self.assertIn("Regression Diff", diff_md)
        self.assertIsInstance(diff_json, dict)
        self.assertIn("Regression Data Provenance", fresh_md)

    def test_manual_diff_invalid_meta_path(self):
        """Scenario: Manual diff fails when meta path does not exist."""
        meta_path = "/non/existent/meta.json"
        self.mock_exists.side_effect = lambda p: p != meta_path
        
        msg, diff_md, diff_json, fresh_md = uruha_web_ui.run_regression_diff_manually(meta_path)
        
        self.assertIn("❌", msg)
        self.assertIn("遺失", msg)
        self.assertIn("unavailable", diff_md)
        self.assertIn("選中的基準元數據已遺失", diff_md)
        self.assertEqual(diff_json, {})
        self.assertIn("INVALID", fresh_md)

    def test_manual_diff_current_eval_missing(self):
        """Scenario: Manual diff fails when current eval report is missing."""
        self.mock_exists.side_effect = lambda p: p != HUMAN_FEEDBACK_REGRESSION_EVAL_REPORT_JSON_PATH
        
        msg, diff_md, diff_json, fresh_md = uruha_web_ui.run_regression_diff_manually("some_meta.json")
        
        self.assertIn("❌", msg)
        self.assertIn("current eval missing", msg)
        self.assertIn("unavailable", diff_md)
        self.assertIn("找不到目前的評測報表", diff_md)
        self.assertEqual(diff_json, {})
        self.assertIn("Current Eval", fresh_md)
        self.assertIn("missing", fresh_md)
        self.assertIn("Unavailable", fresh_md)

    def test_manual_diff_invalid_snapshot_json(self):
        """Scenario: Manual diff fails when snapshot JSON file is missing."""
        meta_path = "valid.meta.json"
        snap_json = "missing.json"
        self.mock_load_json.side_effect = lambda p: {
            "snapshot_json": snap_json,
            "label": "test"
        } if p == meta_path else {}
        
        # exists returns True for meta_path and Eval Report, but False for snap_json
        def exists_side_effect(p):
            if p == snap_json: return False
            return True
        self.mock_exists.side_effect = exists_side_effect
        
        msg, diff_md, diff_json, fresh_md = uruha_web_ui.run_regression_diff_manually(meta_path)
        
        self.assertIn("❌", msg)
        self.assertIn("快照 JSON 遺失", msg)
        self.assertIn("unavailable", diff_md)
        self.assertIn("選中的基準數據檔已遺失", diff_md)
        self.assertEqual(diff_json, {})
        self.assertIn("Regression Data Provenance", fresh_md)
        self.assertIn("Unavailable", fresh_md)

    def test_manual_diff_no_baseline(self):
        """Scenario: Manual diff fails when no baseline is selected and none found in latest."""
        with patch('uruha_web_ui._load_latest_snapshot_metadata', return_value={}):
            msg, diff_md, diff_json, fresh_md = uruha_web_ui.run_regression_diff_manually("")
            
            self.assertIn("❌", msg)
            self.assertIn("無 baseline snapshot", msg)
            self.assertEqual(diff_json, {})
            self.assertIn("Latest Baseline", fresh_md)
            self.assertIn("missing", fresh_md)
            self.assertIn("Unavailable", fresh_md)

    def test_architecture_check_success(self):
        """Scenario: Architecture check runs and successfully triggers auto-diff."""
        current_picker = "some_meta.json"
        self.mock_load_json.return_value = {"snapshot_json": "snap.json"}
        
        results = uruha_web_ui._run_architecture_checks(current_picker)
        
        diff_md = results[12]
        fresh_md = results[16]
        
        self.assertIn("Regression Diff", diff_md)
        self.assertIn("Regression Data Provenance", fresh_md)
        self.mock_subprocess.assert_called()

    def test_architecture_check_invalid_snapshot_json(self):
        """Scenario: Architecture check auto-diff fails due to missing snapshot json."""
        current_picker = "some_meta.json"
        snap_json = "missing.json"
        self.mock_load_json.return_value = {"snapshot_json": snap_json}
        
        # Mock exists to fail for snap_json
        self.mock_exists.side_effect = lambda p: p != snap_json
        
        results = uruha_web_ui._run_architecture_checks(current_picker)
        
        diff_md = results[12]
        self.assertIn("unavailable", diff_md)
        self.assertIn("選中的基準數據檔已遺失", diff_md)
        self.assertEqual(results[13], {}) # diff_json
        self.assertIn("Unavailable", results[16]) # freshness
        self.assertEqual(results[17][1]["value"], current_picker) # picker preserved

    def test_batch_accept_run_replay_false(self):
        """Scenario: Batch accept with run_replay=False MUST NOT overwrite diff panel."""
        with patch('uruha_web_ui._annotation_draft_rows', return_value=[{"draft_id": "D1", "source_record": {}}]):
            with patch('uruha_web_ui._load_existing_annotation_keys', return_value=set()):
                results = uruha_web_ui.batch_accept_annotation_drafts(
                    "ALL", "ALL", "ALL", 5, 20, "meta.json", run_replay=False
                )
                
                eval_md = results[9]
                diff_md = results[11]
                
                self.assertEqual(eval_md, gr.update(), "Eval panel should be gr.update() when run_replay=False")
                self.assertEqual(diff_md, gr.update(), "Diff panel should be gr.update() when run_replay=False")
                self.assertEqual(results[12], gr.update(), "Diff JSON should be untouched when run_replay=False")
                self.assertIn("Regression Data Provenance", results[13])

    def test_batch_accept_run_replay_true_success(self):
        """Scenario: Batch accept with run_replay=True should update diff panel."""
        with patch('uruha_web_ui._annotation_draft_rows', return_value=[{"draft_id": "D1", "source_record": {}}]):
            with patch('uruha_web_ui._load_existing_annotation_keys', return_value=set()):
                self.mock_load_json.return_value = {"snapshot_json": "snap.json"}
                
                results = uruha_web_ui.batch_accept_annotation_drafts(
                    "ALL", "ALL", "ALL", 5, 20, "meta.json", run_replay=True
                )
                
                eval_md = results[9]
                diff_md = results[11]
                self.assertNotEqual(eval_md, gr.update(), "Eval panel should be updated when run_replay=True")
                self.assertNotEqual(diff_md, gr.update(), "Diff panel should be updated when run_replay=True")

    def test_batch_accept_invalid_meta_path(self):
        """Scenario: Batch accept with run_replay=True fails diff due to invalid meta path."""
        with patch('uruha_web_ui._annotation_draft_rows', return_value=[{"draft_id": "D1", "source_record": {"session_id":"S1", "turn_index":1}}]):
            with patch('uruha_web_ui._load_existing_annotation_keys', return_value=set()):
                meta_path = "non_existent.meta.json"
                self.mock_exists.side_effect = lambda p: p != meta_path
                
                results = uruha_web_ui.batch_accept_annotation_drafts(
                    "ALL", "ALL", "ALL", 5, 20, meta_path, run_replay=True
                )
                
                diff_md = results[11]
                self.assertIn("unavailable", diff_md)
                self.assertIn("選中的基準元數據已遺失", diff_md)
                self.assertEqual(results[12], {})
                self.assertIn("Selected Baseline (INVALID)", results[13])
                self.assertIn("Unavailable", results[13])
                self.assertEqual(results[14][1]["value"], meta_path)

    def test_batch_accept_all_skipped(self):
        """Scenario: Batch accept where all rows are already accepted (skipped)."""
        with patch('uruha_web_ui._annotation_draft_rows', return_value=[{"draft_id": "D1", "source_record": {"session_id":"S1", "turn_index":1}}]):
            with patch('uruha_web_ui._load_existing_annotation_keys', return_value={("S1", "1")}):
                results = uruha_web_ui.batch_accept_annotation_drafts(
                    "ALL", "ALL", "ALL", 5, 20, "meta.json", run_replay=True
                )
                
                diff_md = results[11]
                self.assertIn("unavailable", diff_md)
                self.assertIn("重複草稿已被略過", diff_md)
                self.assertEqual(results[12], {})

    def test_batch_accept_no_rows(self):
        """Scenario: Batch accept with no rows matching filter."""
        with patch('uruha_web_ui._annotation_draft_rows', return_value=[]):
            results = uruha_web_ui.batch_accept_annotation_drafts(
                "ALL", "ALL", "ALL", 5, 20, "meta.json", run_replay=True
            )
            
            eval_md = results[9]
            self.assertIn("skipped (no data)", eval_md)
            self.assertIn("unavailable", results[11])
            self.assertEqual(results[12], {})

    def test_baseline_picker_invalid_state_preservation(self):
        """
        Scenario: Even if the selected meta path is invalid/missing, 
        the UI picker value MUST be preserved to maintain surface integrity.
        """
        invalid_path = "/path/to/missing.meta.json"
        self.mock_exists.side_effect = lambda p: p != invalid_path
        
        # Test via manual diff refresh
        _, _, _, _ = uruha_web_ui.run_regression_diff_manually(invalid_path)
        
        # We need to capture the bundle assembly or check the return values.
        # run_regression_diff_manually calls _assemble_regression_panel_bundle internally.
        # Since we can't easily peek into _assemble_regression_panel_bundle's return from run_regression_diff_manually 
        # (it only returns 4 values, but bundle has more), let's call the helper directly if possible, 
        # or test a function that returns the picker update.
        
        # batch_accept_annotation_drafts returns the picker update at index 14
        with patch('uruha_web_ui._annotation_draft_rows', return_value=[]):
            results = uruha_web_ui.batch_accept_annotation_drafts(
                "ALL", "ALL", "ALL", 5, 20, invalid_path, run_replay=True
            )
            picker_update = results[14]
            self.assertEqual(picker_update[1]["value"], invalid_path, "Picker value must be preserved even if invalid")

if __name__ == '__main__':
    unittest.main()
