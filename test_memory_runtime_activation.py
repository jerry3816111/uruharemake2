import os
import unittest
from unittest.mock import patch

import uruha_brain_mac as ubm


class MemoryRuntimeActivationTest(unittest.TestCase):
    def test_validated_v2_is_the_default_runtime_profile(self):
        if "URUHA_WORKING_MEMORY_SCORING_PROFILE" not in os.environ:
            self.assertEqual(ubm.WORKING_MEMORY_SCORING_PROFILE, "v2")
        self.assertIn(
            ubm.WORKING_MEMORY_SCORING_PROFILE,
            ubm.umr.MEMORY_SCORING_PROFILES,
        )

    def test_memory_manager_passes_the_selected_profile_to_runtime(self):
        manager = object.__new__(ubm.MemoryManager)
        manager._profile_candidates = lambda: []
        manager._short_term_candidates = lambda: []
        manager._recent_turn_candidates = lambda: []
        manager._query_collection_candidates = lambda *args, **kwargs: []
        manager.episode_col = object()
        manager.wisdom_col = object()
        manager.procedural_col = object()
        manager.kb_col = object()

        with patch.object(ubm.umr, "build_working_memory", return_value=[]) as build:
            manager._build_working_memory("question")

        self.assertEqual(
            build.call_args.kwargs["scoring_profile"],
            ubm.WORKING_MEMORY_SCORING_PROFILE,
        )


if __name__ == "__main__":
    unittest.main()
