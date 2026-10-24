"""Zero-model typed provenance contracts; no frozen Safari wording is replayed."""

from copy import deepcopy
import datetime
from unittest import TestCase
from unittest.mock import patch

import uruha_explicit_episode_recall_focus_p4 as focus
import uruha_memory_runtime as umr
import uruha_typed_episode_recall_source_p4 as typed
from test_p4_explicit_episode_recall_focus import episode, memory_data
from uruha_memory_observatory import collect_memory_nodes


QUERY = "前に言った図書室の集合目印、覚えてる？"
SOURCE = "図書室の集合目印は銀色の掲示板だよ。"
OTHER = "映写室の集合目印は南の窓だよ。"


def make_typed_data(*, summary=True, source=True):
    rows = [
        episode(OTHER, 1, selected=True),
        episode("掃除する場所は西の廊下だよ。", 2, selected=True),
        episode("荷物の置き場は木の棚だよ。", 3, selected=True),
        episode("開始する時刻は十時だよ。", 4, selected=True),
        episode("本日の担当者は花子さんだよ。", 5, selected=True),
    ]
    summary_id = None
    if summary:
        rows[2]["text"] = "EpisodicSummary: 図書室の集合目印について会話した。"
        summary_id = rows[2]["trace_id"]
    if source:
        rows.append(episode(SOURCE, 6, selected=False))
    for row in rows:
        row["episode_record_kind"] = (
            "episodic_consolidation" if row["trace_id"] == summary_id else "turn_episode"
        )
        row["episode_record_kind_origin"] = "stored_metadata"
    return memory_data(*rows), (rows[-1]["trace_id"] if source else None), summary_id


def build(query, data):
    with patch.object(typed, "_ORIGINAL_FOCUS_BUILDER", focus.build_explicit_episode_recall_focus_contract_p4):
        return typed.build_typed_episode_recall_focus_contract_p4(query, data)


class TypedEpisodeRecallSourceTests(TestCase):
    def test_chroma_metadata_projection_keeps_original_ranking_and_scores(self):
        direct = episode(SOURCE, 1)
        stored = [
            (direct["memory_id"], direct["text"], {"source": "turn_episode"}),
            (
                "d5f6b2a1-833e-4c42-9485-e58d3d618794",
                "EpisodicSummary: 図書室の話題があった。",
                {"source": "episodic_consolidation"},
            ),
        ]

        class Collection:
            def query(self, **kwargs):
                return {
                    "ids": [[item[0] for item in stored]],
                    "documents": [[item[1] for item in stored]],
                    "metadatas": [[item[2] for item in stored]],
                    "distances": [[0.1, 0.2]],
                }

        candidates = umr.query_collection_candidates(Collection(), QUERY, "episode", limit=20)
        base_trace = {}
        time = datetime.datetime(2026, 10, 18, 12, 0, 0)
        base_selected = umr.build_working_memory(
            QUERY, candidates, reference_time=time, trace_sink=base_trace
        )
        original_trace_row = umr.memory_trace_row
        with (
            patch.object(typed, "_ORIGINAL_TRACE_ROW", original_trace_row),
            patch.object(umr, "memory_trace_row", typed.trace_row_with_episode_record_kind_p4),
        ):
            typed_trace = {}
            typed_selected = umr.build_working_memory(
                QUERY, candidates, reference_time=time, trace_sink=typed_trace
            )
        self.assertEqual(
            [row["trace_id"] for row in base_selected],
            [row["trace_id"] for row in typed_selected],
        )
        self.assertEqual(
            [(row["trace_id"], row["score"]) for row in base_trace["candidate_pool"]],
            [(row["trace_id"], row["score"]) for row in typed_trace["candidate_pool"]],
        )
        by_id = {row["memory_id"]: row for row in typed_trace["candidate_pool"]}
        self.assertEqual(by_id[direct["memory_id"]]["episode_record_kind"], "turn_episode")
        self.assertEqual(by_id[stored[1][0]]["episode_record_kind"], "episodic_consolidation")

    def test_stored_metadata_type_projects_into_trace_and_handoff(self):
        candidate = {
            "source": "episode",
            "collection_name": "episode",
            "memory_id": "7f7d4308-b25b-4abf-a5a1-31925d28bb9a",
            "text": "EpisodicSummary: 会話の要約。",
            "metadata": {"source": "episodic_consolidation", "private_extra": "not projected"},
        }
        with patch.object(typed, "_ORIGINAL_TRACE_ROW", umr.memory_trace_row):
            row = typed.trace_row_with_episode_record_kind_p4(candidate, rank=2, selected=True)
            handed = typed.trace_row_with_episode_record_kind_p4(row, channel="focus_handoff")
            missing = typed.trace_row_with_episode_record_kind_p4(
                {**candidate, "metadata": {}}, rank=2
            )
        self.assertEqual(row["episode_record_kind"], "episodic_consolidation")
        self.assertEqual(row["episode_record_kind_origin"], "stored_metadata")
        self.assertNotIn("private_extra", row)
        self.assertEqual(handed["episode_record_kind"], "episodic_consolidation")
        self.assertEqual(handed["episode_record_kind_origin"], "stored_metadata")
        self.assertEqual(missing["episode_record_kind"], "unavailable")

    def test_summary_is_audit_only_but_rank_six_direct_user_turn_is_answerable(self):
        data, target_id, summary_id = make_typed_data()
        before = deepcopy(data)
        old = focus.build_explicit_episode_recall_focus_contract_p4(QUERY, data)
        self.assertEqual(old["reason"], "episode_provenance_incomplete")
        contract = build(QUERY, data)
        self.assertEqual(contract["status"], "selected_unique_user_episode")
        self.assertEqual(contract["trace_id"], target_id)
        self.assertEqual(contract["candidate_rank"], 6)
        self.assertFalse(contract["ordinary_working_memory_selected"])
        self.assertIn("銀色の掲示板", contract["selected_core_jp"])
        audit = contract["typed_episode_audit"]
        self.assertEqual(audit["summary_candidate_count"], 1)
        self.assertEqual(audit["summary_trace_ids"], [summary_id])
        self.assertEqual(audit["summary_candidate_ranks"], [3])
        self.assertFalse(audit["summary_answer_authority"])
        self.assertEqual(data, before)

        with (
            patch.object(typed, "_ORIGINAL_FOCUS_BUILDER", focus.build_explicit_episode_recall_focus_contract_p4),
            patch.object(focus, "build_explicit_episode_recall_focus_contract_p4", typed.build_typed_episode_recall_focus_contract_p4),
            patch.object(focus, "_ORIGINAL_QUERY", return_value=data),
        ):
            returned = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), QUERY)
            plan = focus._plan_from_contract(returned[focus.LABEL])
            plan["semantic_route_m22"] = {"selected_type": "factual_or_memory"}
            dummy_right = type("Right", (), {
                "_structured_surface_required": lambda self: False,
                "_user_visible_language_rejection_reasons": lambda self, *a, **k: [],
            })()
            with patch.object(focus, "_ORIGINAL_VISIBLE_GUARD", return_value="前段の返答。"):
                visible = focus.visible_guard_with_explicit_episode_recall_focus_p4(
                    dummy_right, "前段の返答。", plan, user_input=QUERY, memory_data=returned
                )
        self.assertEqual(visible, contract["selected_core_jp"])
        self.assertEqual(plan["memory_recall_contract"]["trace_id"], target_id)
        self.assertEqual(plan["memory_recall_contract"]["visible_surface_status"], "matched")
        self.assertEqual(returned["memory_provenance"]["candidate_pool"], before["memory_provenance"]["candidate_pool"])
        self.assertEqual(returned["memory_provenance"]["selected_working_memory_trace_ids"], before["memory_provenance"]["selected_working_memory_trace_ids"])
        self.assertTrue(any(row["trace_id"] == summary_id for row in collect_memory_nodes({"memory_data": returned})))
        self.assertTrue(any(
            row.get("trace_id") == target_id and row.get("channel") == focus.HANDOFF_CHANNEL
            for row in returned["memory_provenance"]["passed_to_leftbrain"]
        ))

    def test_unknown_or_type_document_mismatch_never_silently_skips_an_episode(self):
        for mutation in ("missing", "unknown", "summary_as_turn", "turn_as_summary", "bad_direct"):
            with self.subTest(mutation=mutation):
                data, _, summary_id = make_typed_data()
                pool = data["memory_provenance"]["candidate_pool"]
                retrieved = data["memory_provenance"]["retrieved_candidates"]
                if mutation == "missing":
                    for row in (*pool, *retrieved):
                        if row["trace_id"] == summary_id:
                            row.pop("episode_record_kind")
                elif mutation == "unknown":
                    for row in (*pool, *retrieved):
                        if row["trace_id"] == summary_id:
                            row["episode_record_kind"] = "unknown"
                elif mutation == "summary_as_turn":
                    for row in (*pool, *retrieved):
                        if row["trace_id"] == summary_id:
                            row["episode_record_kind"] = "turn_episode"
                elif mutation == "turn_as_summary":
                    for row in (*pool, *retrieved):
                        if row["trace_id"] == summary_id:
                            row["text"] = "User: spoofed direct source"
                else:
                    for row in (*pool, *retrieved):
                        if row["rank"] == 6 or row["trace_id"] == pool[-1]["trace_id"]:
                            row["text"] = "broken direct turn"
                result = build(QUERY, data)
                self.assertFalse(result.get("source_selected"))
                self.assertNotIn("銀色の掲示板", result["selected_core_jp"])

    def test_duplicate_or_mismatched_retrieved_row_fails_closed(self):
        for mutation in ("duplicate", "text_mismatch", "kind_mismatch", "selected_mismatch"):
            with self.subTest(mutation=mutation):
                data, _, _ = make_typed_data()
                provenance = data["memory_provenance"]
                if mutation == "duplicate":
                    provenance["retrieved_candidates"].append(deepcopy(provenance["retrieved_candidates"][0]))
                elif mutation == "text_mismatch":
                    provenance["retrieved_candidates"][-1]["text"] = "別の保存文書。"
                elif mutation == "kind_mismatch":
                    provenance["retrieved_candidates"][-1]["episode_record_kind"] = "episodic_consolidation"
                else:
                    provenance["candidate_pool"][-1]["selected"] = True
                result = build(QUERY, data)
                self.assertEqual(result["reason"], "episode_record_type_provenance_mismatch" if mutation != "kind_mismatch" else "episode_record_type_unverified")
                self.assertFalse(result["source_selected"])

    def test_malformed_optional_passage_lists_fail_closed_without_throwing(self):
        for field in ("passed_to_leftbrain", "passed_to_leftbrain_trace_ids", "working_memory_items"):
            with self.subTest(field=field):
                data, _, _ = make_typed_data()
                target = data if field == "working_memory_items" else data["memory_provenance"]
                target[field] = 1
                result = build(QUERY, data)
                self.assertEqual(result["reason"], "episode_record_type_provenance_mismatch")
                self.assertFalse(result["source_selected"])

    def test_existing_conflict_sensitive_retraction_and_unknown_boundaries_remain(self):
        conflict, _, _ = make_typed_data(summary=False)
        opposing = episode("図書室の集合目印は緑の旗だよ。", 7, selected=False)
        opposing["episode_record_kind"] = "turn_episode"
        opposing["episode_record_kind_origin"] = "stored_metadata"
        conflict["memory_provenance"]["candidate_pool"].append(opposing)
        conflict["memory_provenance"]["retrieved_candidates"].append({
            **deepcopy(opposing), "channel": "retrieved_candidate", "ranking_status": "ranked"
        })
        conflict["memory_provenance"]["candidate_count"] += 1
        self.assertEqual(build(QUERY, conflict)["status"], "conflicting_or_nonunique")

        no_source, _, _ = make_typed_data(source=False)
        self.assertEqual(build(QUERY, no_source)["status"], "unavailable")
        sensitive = memory_data(episode("合言葉は1234だよ。", 1, selected=True))
        for row in (*sensitive["memory_provenance"]["candidate_pool"], *sensitive["memory_provenance"]["retrieved_candidates"]):
            row["episode_record_kind"] = "turn_episode"
            row["episode_record_kind_origin"] = "stored_metadata"
        secret = build("前に言った合言葉、覚えてる？", sensitive)
        self.assertEqual(secret["status"], "suppressed")
        self.assertNotIn("1234", secret["selected_core_jp"])

        retracted, _, _ = make_typed_data(summary=False)
        withdrawal = episode("図書室の集合目印はまだ決めてないよ。", 7, selected=False)
        withdrawal["episode_record_kind"] = "turn_episode"
        withdrawal["episode_record_kind_origin"] = "stored_metadata"
        retracted["memory_provenance"]["candidate_pool"].append(withdrawal)
        retracted["memory_provenance"]["retrieved_candidates"].append({
            **deepcopy(withdrawal), "channel": "retrieved_candidate", "ranking_status": "ranked"
        })
        retracted["memory_provenance"]["candidate_count"] += 1
        self.assertEqual(build(QUERY, retracted)["status"], "retracted_or_uncertain")
