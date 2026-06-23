import json
import unittest

import torch

from train_uruha_rightbrain_contract_v1 import load_rows, resolve_model_dtype
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION


class RightBrainContractV1TrainingTest(unittest.TestCase):
    def test_auto_dtype_uses_bfloat16_on_mps(self):
        self.assertEqual(resolve_model_dtype("auto", use_cuda=False, use_mps=True), torch.bfloat16)
        self.assertEqual(resolve_model_dtype("auto", use_cuda=False, use_mps=False), torch.float32)

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


if __name__ == "__main__":
    unittest.main()
