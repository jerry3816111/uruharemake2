import json
import unittest

import torch

from train_uruha_rightbrain_contract_v1 import (
    init_adapter_report,
    load_rows,
    load_training_rows,
    resolve_model_dtype,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION


class RightBrainContractV1TrainingTest(unittest.TestCase):
    def test_auto_dtype_uses_bfloat16_on_mps(self):
        self.assertEqual(resolve_model_dtype("auto", use_cuda=False, use_mps=True), torch.bfloat16)
        self.assertEqual(resolve_model_dtype("auto", use_cuda=False, use_mps=False), torch.float32)

    def test_empty_init_adapter_reports_independent_lora(self):
        report = init_adapter_report("")

        self.assertEqual(report["init_adapter_ref"], "base_model_new_lora")
        self.assertIsNone(report["init_adapter_config_sha256"])

    def test_load_rows_requires_canonical_contract(self):
        import tempfile
        from pathlib import Path

        valid = {
            "messages": [
                {"role": "system", "content": "system"},
                {
                    "role": "user",
                    "content": json.dumps({"contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION}),
                },
                {"role": "assistant", "content": "返事。"},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.json"
            path.write_text(json.dumps([valid] * 500), encoding="utf-8")
            rows = load_rows(path)

        self.assertEqual(len(rows), 500)

    def test_load_training_rows_accepts_small_supplemental_dataset(self):
        import tempfile
        from pathlib import Path

        valid = {
            "messages": [
                {"role": "system", "content": "system"},
                {
                    "role": "user",
                    "content": json.dumps({"contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION}),
                },
                {"role": "assistant", "content": "返事。"},
            ]
        }
        supplemental = {
            "messages": [
                {"role": "system", "content": "system"},
                {
                    "role": "user",
                    "content": json.dumps({"contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION}),
                },
                {"role": "assistant", "content": "補強する。"},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            primary_path = Path(directory) / "primary.json"
            supplement_path = Path(directory) / "supplement.json"
            primary_path.write_text(json.dumps([valid] * 500), encoding="utf-8")
            supplement_path.write_text(json.dumps([supplemental] * 3), encoding="utf-8")

            rows, sources = load_training_rows(primary_path, [supplement_path])

        self.assertEqual(len(rows), 503)
        self.assertEqual(sources[0]["role"], "primary")
        self.assertEqual(sources[0]["rows"], 500)
        self.assertEqual(sources[1]["role"], "supplemental")
        self.assertEqual(sources[1]["rows"], 3)


if __name__ == "__main__":
    unittest.main()
