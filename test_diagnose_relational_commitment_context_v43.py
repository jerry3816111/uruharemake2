#!/usr/bin/env python3

import unittest

from diagnose_relational_commitment_context_v43 import (
    output_shape,
    recover_unique_label,
)


class DiagnoseRelationalCommitmentContextV43Tests(unittest.TestCase):
    def test_unique_label_recovery_does_not_resolve_multiple_labels(self):
        self.assertEqual(recover_unique_label('"requested"'), "requested")
        self.assertEqual(recover_unique_label("requested"), "requested")
        self.assertEqual(
            recover_unique_label('{"commitment":{"requested":true}}'),
            "requested",
        )
        self.assertIsNone(
            recover_unique_label(
                '{"commitment":{"requested":true,"negated":false}}'
            )
        )

    def test_output_shape_keeps_strict_and_malformed_contracts_separate(self):
        self.assertEqual(output_shape('{"commitment":"requested"}', True), "strict_object")
        self.assertEqual(output_shape('"requested"', False), "json_string_enum")
        self.assertEqual(output_shape("requested", False), "plain_enum_token")
        self.assertEqual(
            output_shape('{"commitment":{"requested":true}}', False),
            "nested_commitment_object",
        )


if __name__ == "__main__":
    unittest.main()
