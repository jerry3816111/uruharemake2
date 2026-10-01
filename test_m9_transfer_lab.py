from __future__ import annotations
import unittest
from uruha_transfer_lab import render_transfer_lab,transfer_cutoff_choices

class TransferLabTests(unittest.TestCase):
    def test_negative_transfer_and_engineering_pass_are_visible(self):
        html=render_transfer_lab("E1"); self.assertEqual(4,len(transfer_cutoff_choices())); self.assertIn("1 / 7 HYPOTHESES",html); self.assertIn("0 CORE BRANCHES",html); self.assertIn("43.75%",html); self.assertIn("75%",html)
    def test_case_switch_and_core_hashes_render(self):
        html=render_transfer_lab("E3"); self.assertIn("M-E3-01",html); self.assertIn("person branches 0",html); self.assertIn("下一步 M10",html)

if __name__=="__main__": unittest.main()
