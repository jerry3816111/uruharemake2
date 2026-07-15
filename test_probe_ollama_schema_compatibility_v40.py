#!/usr/bin/env python3

import unittest

from probe_ollama_schema_compatibility_v40 import _validate_expected_cat


class OllamaSchemaCompatibilityV40Tests(unittest.TestCase):
    def test_accepts_exact_cat_branch(self):
        self.assertTrue(_validate_expected_cat({"kind": "cat", "has_whiskers": True}))

    def test_rejects_unrequested_fields(self):
        self.assertFalse(
            _validate_expected_cat(
                {"kind": "cat", "has_whiskers": True, "name": "Whiskers"}
            )
        )

    def test_rejects_wrong_branch_shape(self):
        self.assertFalse(_validate_expected_cat({"kind": "cat", "bark_volume": 2}))


if __name__ == "__main__":
    unittest.main()
