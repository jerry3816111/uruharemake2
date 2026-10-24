import json
import unittest
from unittest import mock

import uruha_brain_mac as brain_module
import uruha_compute_ledger as ledger_module


class _FakeEmbeddingFunction:
    def name(self):
        return "fake-local-embedding"


class _FakeCollection:
    def __init__(self, name):
        self.name = name
        self._embedding_function = _FakeEmbeddingFunction()
        self.fail_query = False

    def query(
        self,
        query_embeddings=None,
        query_texts=None,
        n_results=10,
        where=None,
        where_document=None,
        include=None,
    ):
        if self.fail_query:
            raise RuntimeError("private vector failure")
        return {
            "ids": [[]],
            "documents": [["private retrieved document"]] if query_texts else [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    def add(self, ids, embeddings=None, metadatas=None, documents=None, images=None, uris=None):
        return None

    def update(self, ids, embeddings=None, metadatas=None, documents=None, images=None, uris=None):
        return None

    def upsert(self, ids, embeddings=None, metadatas=None, documents=None, images=None, uris=None):
        return None

    def get(self, ids=None, where=None, limit=None, offset=None, where_document=None, include=None):
        return {"ids": [], "documents": [], "metadatas": []}

    def peek(self, limit=10):
        return {"ids": [], "documents": [], "metadatas": []}

    def delete(self, ids=None, where=None, where_document=None):
        return None


class _FakePersistentClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, name):
        self.collections.setdefault(name, _FakeCollection(name))
        return self.collections[name]


class P3CompleteProductComputeAccountingTest(unittest.TestCase):
    def test_native_ollama_records_real_tokens_without_raw_text(self):
        ledger = ledger_module.ComputeLedger()
        with ledger.item_scope("case-1", "system"):
            with ledger.stage("semantic_authorizer"):
                ledger.record_native_ollama_chat(
                    {
                        "model": "qwen2.5:7b",
                        "messages": [
                            {"role": "user", "content": "private native prompt"}
                        ],
                        "options": {"temperature": 0, "num_predict": 32},
                        "think": False,
                    },
                    {
                        "message": {"content": "private native reply"},
                        "prompt_eval_count": 13,
                        "eval_count": 5,
                        "total_duration": 123,
                        "done_reason": "stop",
                    },
                    0.25,
                )

        snapshot = ledger.snapshot()
        encoded = json.dumps(snapshot, ensure_ascii=False)
        self.assertEqual(snapshot["schema"], "uruha_compute_ledger_v2")
        self.assertNotIn("private native prompt", encoded)
        self.assertNotIn("private native reply", encoded)
        call = snapshot["calls"][0]
        self.assertEqual(call["backend"], "ollama_native_chat")
        self.assertEqual(call["resource_kind"], "generative_inference")
        self.assertEqual(call["response"]["prompt_tokens"], 13)
        self.assertEqual(call["response"]["completion_tokens"], 5)
        self.assertEqual(call["response"]["total_tokens"], 18)
        self.assertTrue(snapshot["summary"]["generative_token_accounting_complete"])

    def test_native_failure_records_type_not_message(self):
        ledger = ledger_module.ComputeLedger()
        error = RuntimeError("private provider failure")
        ledger.record_native_ollama_chat(
            {
                "model": "qwen2.5:7b",
                "messages": [{"role": "user", "content": "private failed prompt"}],
            },
            None,
            0.1,
            error=error,
        )
        encoded = json.dumps(ledger.snapshot(), ensure_ascii=False)
        self.assertNotIn("private provider failure", encoded)
        self.assertNotIn("private failed prompt", encoded)
        self.assertEqual(ledger.snapshot()["calls"][0]["error_type"], "RuntimeError")
        self.assertFalse(
            ledger.snapshot()["summary"]["generative_token_accounting_complete"]
        )

    def test_left_brain_native_ollama_path_is_instrumented(self):
        ledger = ledger_module.ComputeLedger()
        response_payload = {
            "message": {"content": '{"same_meaning": true}'},
            "prompt_eval_count": 21,
            "eval_count": 7,
            "done_reason": "stop",
        }
        fake_response = mock.MagicMock()
        fake_response.__enter__.return_value.read.return_value = json.dumps(
            response_payload
        ).encode("utf-8")
        left_brain = brain_module.LeftBrain(None, compute_ledger=ledger)

        with ledger.item_scope("turn-native", "system"):
            with mock.patch.object(
                brain_module.urllib.request,
                "urlopen",
                return_value=fake_response,
            ):
                parsed = left_brain._native_semantic_authorizer_m31(
                    "private semantic verification prompt"
                )

        self.assertTrue(parsed["same_meaning"])
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot["call_count"], 1)
        call = snapshot["calls"][0]
        self.assertEqual(call["backend"], "ollama_native_chat")
        self.assertEqual(call["item_id"], "turn-native")
        self.assertEqual(call["response"]["total_tokens"], 28)
        self.assertNotIn(
            "private semantic verification prompt",
            json.dumps(snapshot, ensure_ascii=False),
        )

    def test_chroma_query_and_add_are_raw_free_and_embedding_aware(self):
        ledger = ledger_module.ComputeLedger()
        raw = _FakeCollection("episodic_memory")
        collection = ledger_module.instrument_chroma_collection(raw, ledger)
        with ledger.item_scope("turn-1", "system"):
            result = collection.query(
                query_texts=["private memory query"],
                n_results=3,
            )
            collection.add(
                ids=["private-id"],
                documents=["private memory document"],
                metadatas=[{"source": "private metadata"}],
            )
            collection.add(
                ids=["caller-vector"],
                embeddings=[[0.1, 0.2]],
                documents=["private preembedded document"],
            )

        self.assertEqual(result["documents"][0][0], "private retrieved document")
        snapshot = ledger.snapshot()
        encoded = json.dumps(snapshot, ensure_ascii=False)
        for raw_text in (
            "private memory query",
            "private memory document",
            "private metadata",
            "private preembedded document",
            "private retrieved document",
            "private-id",
            "caller-vector",
        ):
            self.assertNotIn(raw_text, encoded)
        self.assertEqual(snapshot["summary"]["vector_store_operation_count"], 3)
        self.assertEqual(snapshot["summary"]["embedding_expected_operation_count"], 2)
        self.assertEqual(snapshot["summary"]["by_operation"], {"query": 1, "add": 2})
        self.assertEqual(snapshot["summary"]["scoped_call_count"], 3)
        self.assertEqual(snapshot["summary"]["unscoped_call_count"], 0)
        query_call, embedded_add, vector_add = snapshot["calls"]
        self.assertTrue(query_call["request"]["embedding_expected"])
        self.assertTrue(embedded_add["request"]["embedding_expected"])
        self.assertFalse(vector_add["request"]["embedding_expected"])
        self.assertTrue(vector_add["request"]["caller_vectors_supplied"])
        self.assertEqual(vector_add["request"]["embeddings"]["dimensions"], [2])
        self.assertEqual(query_call["item_id"], "turn-1")
        self.assertEqual(query_call["condition_id"], "system")

    def test_chroma_failure_is_recorded_and_reraised_without_message(self):
        ledger = ledger_module.ComputeLedger()
        raw = _FakeCollection("knowledge_base")
        raw.fail_query = True
        collection = ledger_module.instrument_chroma_collection(raw, ledger)
        with self.assertRaises(RuntimeError):
            collection.query(query_texts=["private failing query"])
        encoded = json.dumps(ledger.snapshot(), ensure_ascii=False)
        self.assertNotIn("private failing query", encoded)
        self.assertNotIn("private vector failure", encoded)
        self.assertEqual(ledger.snapshot()["calls"][0]["error_type"], "RuntimeError")

    def test_memory_manager_installs_collection_accounting_only_with_ledger(self):
        fake_client = _FakePersistentClient()
        ledger = ledger_module.ComputeLedger()
        with mock.patch.object(
            brain_module.chromadb,
            "PersistentClient",
            return_value=fake_client,
        ):
            memory = brain_module.MemoryManager(compute_ledger=ledger)
            with ledger.item_scope("turn-1", "system"):
                memory.query_all_layers("private current input")
                memory.save_episode(
                    "private current input",
                    "private visible reply",
                    {"mood": "neutral"},
                    {"intent": "chat", "scene": "casual"},
                )

        snapshot = ledger.snapshot()
        turn_calls = [
            call for call in snapshot["calls"] if call["item_id"] == "turn-1"
        ]
        self.assertGreaterEqual(len(turn_calls), 9)
        self.assertTrue(
            all(call["resource_kind"] == "vector_store_operation" for call in turn_calls)
        )
        self.assertTrue(
            any(
                call["request"]["operation"] == "add"
                and call["request"]["collection_name"] == "episodic_memory"
                for call in turn_calls
            )
        )
        encoded = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("private current input", encoded)
        self.assertNotIn("private visible reply", encoded)

        without_ledger = _FakeCollection("plain")
        self.assertIs(
            ledger_module.instrument_chroma_collection(without_ledger, None),
            without_ledger,
        )

    def test_invalid_collection_ledger_is_rejected(self):
        with self.assertRaises(TypeError):
            ledger_module.instrument_chroma_collection(
                _FakeCollection("bad"),
                object(),
            )


if __name__ == "__main__":
    unittest.main()
