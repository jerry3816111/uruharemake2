import json
import subprocess
import sys
import unittest
from pathlib import Path

import build_public_persona_data_inventory_v1 as inventory_v1


ROOT = Path(__file__).resolve().parent
LOCAL_REGISTRY = ROOT / "datasets/public_persona_local_asset_registry_v1.json"
REPORT = ROOT / "reports/public_persona_data_inventory_v1.json"


class PublicPersonaDataInventoryV1Test(unittest.TestCase):
    def test_generated_reports_are_current(self):
        result = subprocess.run(
            [sys.executable, "build_public_persona_data_inventory_v1.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_inventory_accounts_for_all_registered_research_groups(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        counts = report["available_data"]
        self.assertEqual(counts["development_observations"], 5)
        self.assertEqual(counts["target_calibration_source_reservations"], 3)
        self.assertEqual(counts["target_final_holdout_source_reservations"], 4)
        self.assertEqual(counts["matched_contrast_actors"], 3)
        self.assertEqual(counts["matched_contrast_source_reservations"], 9)

    def test_voice_identity_is_confirmed_without_claiming_source_provenance(self):
        registry = json.loads(LOCAL_REGISTRY.read_text(encoding="utf-8"))
        attestation = registry["owner_attestations"][0]
        voice = registry["assets"][0]
        self.assertEqual(attestation["identity_status"], "confirmed")
        self.assertEqual(voice["registered_fingerprint"]["raw_audio_count"], 874)
        self.assertEqual(voice["source_traceability"], "speaker_confirmed_original_url_unknown")
        self.assertFalse(voice["formal_persona_evaluation_authorized"])

    def test_generated_and_manual_text_are_not_target_evidence(self):
        registry = json.loads(LOCAL_REGISTRY.read_text(encoding="utf-8"))
        assets = {asset["asset_id"]: asset for asset in registry["assets"]}
        self.assertFalse(assets["uruha_v10_manual_patch_v1"]["target_behavior_evidence"])
        self.assertFalse(assets["uruha_local_rightbrain_generated_corpora"]["target_behavior_evidence"])

    def test_manifest_bindings_match_current_files(self):
        report = inventory_v1.build_inventory()
        for binding in report["artifact_bindings"].values():
            path = ROOT / binding["path"]
            self.assertEqual(inventory_v1.sha256(path), binding["sha256"])

    def test_formal_claim_remains_blocked(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        readiness = report["formal_readiness"]
        self.assertFalse(readiness["flags"]["formal_execution_ready"])
        self.assertFalse(readiness["flags"]["persona_fidelity_claim_available"])
        self.assertEqual(readiness["counts"]["formal_agent_response_count"], 0)


if __name__ == "__main__":
    unittest.main()
