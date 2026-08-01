import json
import unittest
from pathlib import Path

import analyze_public_persona_payload_format_v10 as v10_analysis
import analyze_public_persona_realization_obligation_v11 as frozen_v11
import analyze_public_persona_realization_obligation_v11_result as result_analysis
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "reports/public_persona_realization_obligation_v11_raw.json"


class RealizationObligationV11ResultTest(unittest.TestCase):
    def test_raw_hash_is_frozen_by_amendment(self):
        amendment = json.loads(
            (ROOT / "configs/public_persona_realization_obligation_v11_analysis_amendment.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(frozen_v11.sha(RAW), amendment["raw_result_sha256"])

    def test_compatibility_shim_changes_no_score_fields(self):
        raw = json.loads(RAW.read_text(encoding="utf-8"))
        dataset = json.loads(frozen_v11.DATASET.read_text(encoding="utf-8"))
        case = {item["case_id"]: item for item in dataset["cases"]}[raw["rows"][0]["case_id"]]
        row = dict(raw["rows"][0])
        row["representation_metadata"] = {"representation_integrity_pass": True}
        row["canonical_payload_sha256"] = row["baseline_payload_sha256"]
        right_brain = RightBrain(load_model=False)
        expected = result_analysis.FROZEN_V10_SCORE_ROW(right_brain, row, case)
        observed = result_analysis.compatible_score_row(
            right_brain, raw["rows"][0], case
        )
        self.assertEqual(observed, expected)

    def test_analysis_restores_frozen_scorer(self):
        original = v10_analysis.score_row
        result_analysis.analyze(
            frozen_v11.load(RAW),
            frozen_v11.load(frozen_v11.DATASET),
            frozen_v11.load(frozen_v11.PREREGISTRATION),
        )
        self.assertIs(v10_analysis.score_row, original)

    def test_amendment_cannot_change_gates_or_authorize_runtime(self):
        amendment = json.loads(
            (ROOT / "configs/public_persona_realization_obligation_v11_analysis_amendment.json")
            .read_text(encoding="utf-8")
        )
        self.assertFalse(amendment["may_change_preregistered_gates"])
        self.assertFalse(amendment["may_strengthen_evidence_claim"])
        self.assertFalse(amendment["runtime_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
