import tempfile
import unittest

import chromadb

import uruha_memory_runtime as umr


class PersistentMemoryCandidateIntegrationTest(unittest.TestCase):
    def test_all_persistent_memory_sources_return_real_chroma_candidates(self):
        sources = ("episode", "wisdom", "procedural", "knowledge")
        with tempfile.TemporaryDirectory(prefix="uruha_persistent_candidates_") as tempdir:
            client = chromadb.PersistentClient(path=tempdir)
            all_candidates = []
            for source in sources:
                collection = client.get_or_create_collection(f"test_{source}_memory")
                collection.add(
                    ids=[f"{source}-1"],
                    documents=["The user avoids coffee at night because it disrupts sleep."],
                    metadatas=[{"source": source, "owner": "user"}],
                )
                candidates = umr.query_collection_candidates(
                    collection,
                    "What should the user drink tonight?",
                    source,
                    limit=1,
                )
                self.assertEqual(len(candidates), 1, source)
                self.assertEqual(candidates[0]["memory_id"], f"{source}-1")
                self.assertEqual(candidates[0]["collection_name"], source)
                self.assertEqual(candidates[0]["metadata"]["owner"], "user")
                self.assertIsNotNone(candidates[0]["distance"])
                all_candidates.extend(candidates)

            working_memory = umr.build_working_memory(
                "What should the user drink tonight?",
                all_candidates,
                working_memory_limit=4,
                scoring_profile="v2",
            )
            self.assertEqual(len(working_memory), 4)
            self.assertEqual({item["source"] for item in working_memory}, set(sources))


if __name__ == "__main__":
    unittest.main()
