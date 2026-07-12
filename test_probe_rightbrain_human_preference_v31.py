import json
import tempfile
import unittest
from pathlib import Path

from probe_rightbrain_human_preference_v31 import (
    FORMAL_V10_ADAPTER,
    build_adapter_evidence,
    build_probe_report,
    main,
    preference_statistics,
)
from train_uruha_rightbrain_contract_v1 import _sha256


def _scored_row(index, margin):
    return {
        "id": f"row_{index}",
        "source_case_id": f"source_{index}",
        "source_family": f"family_{index}",
        "category": f"category_{index % 3}",
        "comparison_id": f"comparison_{index}",
        "chosen_candidate_id": f"chosen_{index}",
        "rejected_candidate_id": f"rejected_{index}",
        "chosen_average_log_prob": -1.0,
        "rejected_average_log_prob": -1.0 - margin,
        "raw_preference_margin": margin,
        "chosen_completion_token_count": 10 + index,
        "rejected_completion_token_count": 12 + index,
        "signed_completion_token_gap": -2,
        "status": (
            "v10_agrees_with_human"
            if margin > 0
            else "v10_misranks_human_choice"
            if margin < 0
            else "v10_exact_tie"
        ),
    }


def _dataset_report(pair_count):
    return {
        "authorize_preference_probe": True,
        "authorize_training": False,
        "authorize_runtime_promotion": False,
        "gates": {"source_valid": True},
        "pair_count": pair_count,
        "source_family_count": pair_count,
        "dataset_file_sha256": "a" * 64,
        "dataset_canonical_sha256": "b" * 64,
    }


def _adapter_evidence(passed=True):
    return {
        "source_adapter_refs": [FORMAL_V10_ADAPTER],
        "source_adapter_model_sha256": ["c" * 64],
        "local_adapter_ref": FORMAL_V10_ADAPTER,
        "local_adapter_model_sha256": "c" * 64,
        "gates": {"adapter_matches": passed},
    }


def _model_metadata(trainable_after_freeze=0):
    return {
        "trainable_parameter_count_before_freeze": 123,
        "trainable_parameter_count_after_freeze": trainable_after_freeze,
    }


class RightBrainHumanPreferenceV31Test(unittest.TestCase):
    def test_exact_statistics_preserve_small_sample_uncertainty(self):
        stats = preference_statistics(
            [_scored_row(index, 0.1 + index / 100) for index in range(4)]
        )

        self.assertEqual(stats["v10_agrees_with_human_count"], 4)
        self.assertEqual(stats["v10_misranked_count"], 0)
        self.assertEqual(stats["agreement_greater_than_chance_exact_pvalue"], 0.0625)
        self.assertLess(stats["agreement_rate_exact_ci"][0], 0.6)
        self.assertEqual(stats["agreement_rate_exact_ci"][1], 1.0)

    def test_exact_statistics_exclude_model_ties_from_sign_test(self):
        stats = preference_statistics(
            [
                _scored_row(0, 0.3),
                _scored_row(1, -0.2),
                _scored_row(2, 0.0),
            ]
        )

        self.assertEqual(stats["decisive_model_pair_count"], 2)
        self.assertEqual(stats["v10_exact_tie_count"], 1)
        self.assertEqual(stats["v10_human_agreement_rate_decisive_pairs"], 0.5)
        self.assertEqual(stats["agreement_greater_than_chance_exact_pvalue"], 0.75)

    def test_two_independent_misrankings_authorize_only_controlled_ablation(self):
        rows = [
            _scored_row(0, -0.2),
            _scored_row(1, 0.3),
            _scored_row(2, -0.1),
            _scored_row(3, 0.2),
        ]
        report = build_probe_report(
            _dataset_report(len(rows)),
            _adapter_evidence(),
            rows,
            model_metadata=_model_metadata(),
        )

        self.assertEqual(report["decision"]["status"], "controlled_ablation_candidate")
        self.assertTrue(
            report["decision"]["authorize_controlled_training_ablation"]
        )
        self.assertFalse(report["decision"]["authorize_training"])
        self.assertFalse(report["decision"]["authorize_runtime_promotion"])
        self.assertFalse(report["training_performed"])
        self.assertEqual(report["optimizer_updates"], 0)

    def test_one_misranking_is_diagnostic_not_training_trigger(self):
        rows = [
            _scored_row(0, -0.2),
            _scored_row(1, 0.3),
            _scored_row(2, 0.1),
            _scored_row(3, 0.2),
        ]
        report = build_probe_report(
            _dataset_report(len(rows)),
            _adapter_evidence(),
            rows,
            model_metadata=_model_metadata(),
        )

        self.assertEqual(report["decision"]["status"], "isolated_preference_conflict")
        self.assertFalse(
            report["decision"]["authorize_controlled_training_ablation"]
        )

    def test_all_human_choices_preferred_are_saturated_not_training_trigger(self):
        rows = [_scored_row(index, 0.1 + index / 100) for index in range(4)]
        report = build_probe_report(
            _dataset_report(len(rows)),
            _adapter_evidence(),
            rows,
            model_metadata=_model_metadata(),
        )

        self.assertEqual(
            report["decision"]["status"],
            "development_pairs_saturated",
        )
        self.assertFalse(report["decision"]["headroom_detected"])
        self.assertFalse(
            report["decision"]["authorize_controlled_training_ablation"]
        )

    def test_invalid_adapter_evidence_blocks_every_action(self):
        rows = [_scored_row(index, -0.1) for index in range(4)]
        report = build_probe_report(
            _dataset_report(len(rows)),
            _adapter_evidence(False),
            rows,
            model_metadata=_model_metadata(),
        )

        self.assertEqual(report["decision"]["status"], "invalid_evidence")
        self.assertFalse(
            report["decision"]["authorize_controlled_training_ablation"]
        )
        self.assertFalse(report["decision"]["authorize_runtime_promotion"])

    def test_v30_report_that_claims_training_authority_is_rejected(self):
        rows = [_scored_row(index, -0.1) for index in range(4)]
        dataset_report = _dataset_report(len(rows))
        dataset_report["authorize_training"] = True
        report = build_probe_report(
            dataset_report,
            _adapter_evidence(),
            rows,
            model_metadata=_model_metadata(),
        )

        self.assertEqual(report["decision"]["status"], "invalid_evidence")
        self.assertFalse(report["gates"]["v30_report_authorizes_only_probe"])

    def test_nonfrozen_model_blocks_every_action(self):
        rows = [_scored_row(index, -0.1) for index in range(4)]
        report = build_probe_report(
            _dataset_report(len(rows)),
            _adapter_evidence(),
            rows,
            model_metadata=_model_metadata(trainable_after_freeze=1),
        )

        self.assertEqual(report["decision"]["status"], "invalid_evidence")
        self.assertFalse(report["gates"]["model_is_fully_frozen"])
        self.assertFalse(
            report["decision"]["authorize_controlled_training_ablation"]
        )

    def test_nonfinite_margin_is_rejected(self):
        row = _scored_row(0, 0.1)
        row["raw_preference_margin"] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            preference_statistics([row])

    def test_adapter_evidence_binds_local_model_bytes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = Path(tmpdir) / FORMAL_V10_ADAPTER
            adapter.mkdir()
            (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
            model_path = adapter / "adapter_model.safetensors"
            model_path.write_bytes(b"formal-v10")
            sha = _sha256(model_path)
            rows = [
                {
                    "on_policy_adapter_ref": FORMAL_V10_ADAPTER,
                    "on_policy_adapter_sha256": sha,
                }
            ]

            evidence = build_adapter_evidence(rows, adapter)
            self.assertTrue(all(evidence["gates"].values()))
            rows[0]["on_policy_adapter_sha256"] = "0" * 64
            tampered = build_adapter_evidence(rows, adapter)
            self.assertFalse(
                tampered["gates"]["local_adapter_sha_matches_human_candidates"]
            )

    def test_missing_v30_evidence_removes_stale_outputs_and_waits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_json = root / "probe.json"
            output_md = root / "probe.md"
            output_json.write_text(json.dumps({"stale": True}), encoding="utf-8")
            output_md.write_text("stale", encoding="utf-8")
            missing = root / "missing"

            exit_code = main(
                [
                    "--dataset",
                    str(missing / "dataset.json"),
                    "--dataset-report",
                    str(missing / "report.json"),
                    "--package",
                    str(missing / "package.json"),
                    "--key",
                    str(missing / "key.jsonl"),
                    "--ratings",
                    str(missing / "ratings.json"),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ]
            )

            self.assertEqual(exit_code, 2)
            self.assertFalse(output_json.exists())
            self.assertFalse(output_md.exists())


if __name__ == "__main__":
    unittest.main()
