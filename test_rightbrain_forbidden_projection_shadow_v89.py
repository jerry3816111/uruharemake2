import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_rightbrain_forbidden_projection_live_evidence import (
    _contains_raw_bearing_key,
    build_report,
    extract_observation,
    load_jsonl,
)
from test_rightbrain_model_candidate_gate import MEMORY, build_rightbrain, reply_anxiety_logic
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_forbidden_projection_shadow_v89_preregistration.json"
LOCK = ROOT / "configs/rightbrain_forbidden_projection_shadow_v89_harness_lock.json"


def conflict_logic():
    return {
        "jp_summary": "前に話した食べ物について答える。",
        "core_message_jp": "ポテトなら普通にあり。少しもらう。",
        "memory_use_expected": True,
        "memory_speakability": "explicit_ok",
        "memory_anchor": {"kind": "context", "jp_anchor": "ポテトの話", "terms": ["ポテト"]},
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["ポテトなら普通にあり", "少しもらう"],
            "grounding_terms": ["ポテト"],
            "forbidden_repetition": {"recent_openings": ["ポテトなら"]},
        },
        "must_avoid": ["ポテトなら", "危険な指示"],
        "model_surface_candidate_trace": {
            "accepted": [],
            "initial_rejected": [
                {
                    "candidate_index": 0,
                    "raw_candidate": "ポテトなら普通にあり。少しもらう。",
                    "candidate": "ポテトなら普通にあり。少しもらう。",
                    "rejection_reasons": ["must_avoid_violation"],
                }
            ],
            "repairs": [],
        },
    }


def live_record(session_id="session-a", turn_index=1, recovered=1, **shadow_updates):
    reply = "今の返事。"
    shadow = {
        "schema": "uruha_rightbrain_forbidden_projection_shadow_v89",
        "mode": "observe_only",
        "enabled": True,
        "status": "active",
        "changes_user_visible_reply": False,
        "extra_model_call_count": 0,
        "production_projection_enabled": False,
        "projection_scope_matches": True,
        "candidate_count": 1,
        "projected_marker_count": 1,
        "recovered_candidate_count": recovered,
        "new_rejection_count": 0,
        "visible_reply_sha256": hashlib.sha256(reply.encode("utf-8")).hexdigest(),
        "candidate_comparisons": [
            {
                "source": "rejected:initial",
                "candidate_sha256": "a" * 64,
                "control_accepted": False,
                "shadow_accepted": True,
                "control_rejection_reasons": ["must_avoid_violation"],
                "shadow_rejection_reasons": [],
                "removed_rejection_reasons": ["must_avoid_violation"],
                "added_rejection_reasons": [],
                "recovered": bool(recovered),
            }
        ],
        "elapsed_milliseconds": 0.2,
    }
    shadow.update(shadow_updates)
    return {
        "session_id": session_id,
        "turn_index": turn_index,
        "assistant_reply": reply,
        "logic": {"model_surface_forbidden_projection_shadow": shadow},
    }


class RightBrainForbiddenProjectionShadowV89Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_defaults_enable_only_observe_shadow(self):
        rightbrain = RightBrain(load_model=False)
        self.assertTrue(rightbrain.forbidden_projection_shadow_enabled)
        self.assertFalse(rightbrain.forbidden_conflict_projection_enabled)

    def test_conflict_shadow_recovers_candidate_without_raw_text(self):
        rightbrain = RightBrain(load_model=False)
        logic = conflict_logic()
        shadow = rightbrain._record_forbidden_projection_shadow(logic, "ポテトどう？", 40)
        self.assertEqual(shadow["status"], "active")
        self.assertEqual(shadow["projected_marker_count"], 1)
        self.assertEqual(shadow["recovered_candidate_count"], 1)
        self.assertEqual(shadow["new_rejection_count"], 0)
        self.assertFalse(shadow["changes_user_visible_reply"])
        self.assertEqual(shadow["extra_model_call_count"], 0)
        self.assertFalse(_contains_raw_bearing_key(shadow))
        serialized = json.dumps(shadow, ensure_ascii=False)
        self.assertNotIn("ポテトなら", serialized)
        self.assertNotIn("危険な指示", serialized)

    def test_shadow_restores_runtime_flag_and_state(self):
        rightbrain = RightBrain(load_model=False)
        rightbrain.history = [{"role": "assistant", "content": "前の返事。"}]
        before = {
            "history": copy.deepcopy(rightbrain.history),
            "reply_variant_counts": copy.deepcopy(rightbrain.reply_variant_counts),
            "intent_variant_counts": copy.deepcopy(rightbrain.intent_variant_counts),
            "normalized_reply_counts": copy.deepcopy(rightbrain.normalized_reply_counts),
            "intent_normalized_counts": copy.deepcopy(rightbrain.intent_normalized_counts),
            "projection": rightbrain.forbidden_conflict_projection_enabled,
        }
        rightbrain._record_forbidden_projection_shadow(conflict_logic(), "ポテトどう？", 40)
        after = {
            "history": rightbrain.history,
            "reply_variant_counts": rightbrain.reply_variant_counts,
            "intent_variant_counts": rightbrain.intent_variant_counts,
            "normalized_reply_counts": rightbrain.normalized_reply_counts,
            "intent_normalized_counts": rightbrain.intent_normalized_counts,
            "projection": rightbrain.forbidden_conflict_projection_enabled,
        }
        self.assertEqual(before, after)

    def test_nonconflict_and_disabled_paths_are_explicit(self):
        rightbrain = RightBrain(load_model=False)
        logic = conflict_logic()
        logic["must_avoid"] = ["そうなんだ", "危険な指示"]
        logic["human_speech_plan"]["forbidden_repetition"]["recent_openings"] = ["そうなんだ"]
        shadow = rightbrain._record_forbidden_projection_shadow(logic, "ポテトどう？", 40)
        self.assertEqual(shadow["status"], "no_conflict")
        rightbrain.forbidden_projection_shadow_enabled = False
        disabled = rightbrain._record_forbidden_projection_shadow(logic, "ポテトどう？", 40)
        self.assertEqual(disabled["status"], "disabled")

    def test_speak_visible_output_is_identical_with_shadow_on_or_off(self):
        model_reply = "既読のままでも理由はまだ分からない。自分のせいにせず少し待て。"
        logic_on = reply_anxiety_logic()
        logic_on["must_avoid"] = ["既読のまま"]
        logic_on["human_speech_plan"]["forbidden_repetition"] = {
            "recent_openings": ["既読のまま"]
        }
        logic_off = copy.deepcopy(logic_on)
        rightbrain_on = build_rightbrain([model_reply + "<|im_end|>"])
        rightbrain_off = build_rightbrain([model_reply + "<|im_end|>"])
        rightbrain_off.forbidden_projection_shadow_enabled = False
        reply_on = rightbrain_on.speak(
            "他已讀但沒回，是不是我講錯話？",
            logic_on,
            MEMORY,
            {"mood": 0, "trust": 50},
        )
        reply_off = rightbrain_off.speak(
            "他已讀但沒回，是不是我講錯話？",
            logic_off,
            MEMORY,
            {"mood": 0, "trust": 50},
        )
        self.assertEqual(reply_on, reply_off)
        shadow = logic_on["model_surface_forbidden_projection_shadow"]
        self.assertEqual(
            shadow["visible_reply_sha256"],
            hashlib.sha256(reply_on.encode("utf-8")).hexdigest(),
        )
        self.assertFalse(shadow["changes_user_visible_reply"])

    def test_live_builder_requires_real_volume_and_safety(self):
        records = [
            live_record(f"session-{index % 5}", turn_index=(index // 5) + 1)
            for index in range(20)
        ]
        report = build_report(
            records,
            source_meta={"invalid_line_count": 0},
            min_active_conflict_turns=20,
            min_active_sessions=5,
            min_recovered_turns=5,
        )
        self.assertEqual(report["status"], "ready_for_limited_activation_review")
        self.assertTrue(report["limited_activation_review_ready"])
        self.assertEqual(report["summary"]["recovered_turn_count"], 20)
        self.assertTrue(all(report["safety_gate"].values()))
        self.assertFalse(report["production_default_enable_authorized"])
        self.assertFalse(report["persona_fidelity_claim_authorized"])

    def test_any_live_safety_violation_blocks_review(self):
        record = live_record(
            visible_reply_sha256="bad-hash",
            new_rejection_count=1,
            extra_model_call_count=1,
            production_projection_enabled=True,
            elapsed_milliseconds=30.0,
        )
        report = build_report(
            [record],
            source_meta={"invalid_line_count": 0},
            min_active_conflict_turns=1,
            min_active_sessions=1,
            min_recovered_turns=1,
        )
        self.assertEqual(report["status"], "blocked_by_shadow_safety_failure")
        self.assertFalse(report["limited_activation_review_ready"])
        self.assertGreater(report["summary"]["visible_output_violation_count"], 0)
        self.assertFalse(report["safety_gate"]["shadow_overhead_within_budget"])
        self.assertFalse(report["safety_gate"]["production_projection_never_enabled"])

    def test_duplicate_live_turn_uses_latest_shadow_record(self):
        records = [
            live_record("session-a", turn_index=1, recovered=0),
            live_record("session-a", turn_index=1, recovered=1),
        ]
        report = build_report(
            records,
            source_meta={"invalid_line_count": 0},
            min_active_conflict_turns=1,
            min_active_sessions=1,
            min_recovered_turns=1,
        )
        self.assertEqual(report["summary"]["raw_shadow_trace_count"], 2)
        self.assertEqual(report["summary"]["shadow_trace_count"], 1)
        self.assertEqual(report["summary"]["duplicate_shadow_trace_count"], 1)
        self.assertEqual(report["summary"]["recovered_turn_count"], 1)
        self.assertTrue(report["limited_activation_review_ready"])

    def test_legacy_rows_do_not_count_as_live_shadow(self):
        self.assertIsNone(extract_observation({"logic": {}, "assistant_reply": "返事"}))
        report = build_report([], source_meta={"invalid_line_count": 0})
        self.assertEqual(report["status"], "waiting_for_live_shadow_data")
        self.assertEqual(report["summary"]["shadow_trace_count"], 0)

    def test_live_source_snapshot_is_hash_bound(self):
        raw = json.dumps(live_record(), ensure_ascii=False) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "web.jsonl"
            path.write_text(raw, encoding="utf-8")
            records, source_meta = load_jsonl(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(source_meta["sha256"], hashlib.sha256(raw.encode("utf-8")).hexdigest())
        self.assertEqual(source_meta["size_bytes"], len(raw.encode("utf-8")))
        self.assertEqual(source_meta["invalid_line_count"], 0)

    def test_preregistration_preserves_authorization_boundary(self):
        self.assertEqual(
            self.prereg["authorizations"]["on_readiness_pass"],
            "authorize_separate_limited_activation_review_only",
        )
        self.assertFalse(self.prereg["authorizations"]["projection_runtime_enable"])
        self.assertFalse(self.prereg["authorizations"]["production_default_enable"])
        self.assertFalse(self.prereg["authorizations"]["persona_fidelity_claim"])
        self.assertEqual(
            self.prereg["live_readiness_thresholds"]["maximum_shadow_elapsed_milliseconds"],
            25.0,
        )

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
