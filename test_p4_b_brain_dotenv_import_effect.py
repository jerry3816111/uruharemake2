"""Zero-import contract for Brain's B-only dotenv decision.

The heavy Brain module cannot be imported in this test-only environment. We
execute its exact source function AST with a fake dotenv loader, not a copy of
the decision rule. This is source-contract evidence, not Web/runtime evidence.
"""

import ast
import os
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().with_name("uruha_brain_mac.py")


def _source_decision():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_load_runtime_dotenv"]
    assert len(functions) == 1
    calls = [index for index, node in enumerate(tree.body)
             if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
             and isinstance(node.value.func, ast.Name)
             and node.value.func.id == "_load_runtime_dotenv"]
    assert len(calls) == 1
    assert tree.body.index(functions[0]) < calls[0]
    config_reads = [index for index, node in enumerate(tree.body)
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name)
                            and target.id == "M31_SEMANTIC_VERIFIER_MODEL"
                            for target in node.targets)]
    assert len(config_reads) == 1
    assert calls[0] < config_reads[0]
    assert not any(isinstance(node, ast.Expr)
                   and isinstance(node.value, ast.Call)
                   and isinstance(node.value.func, ast.Name)
                   and node.value.func.id == "load_dotenv"
                   for node in tree.body)
    return functions[0]


def _exercise(environ):
    attempted = []

    def fake_load_dotenv():
        attempted.append(True)
        os.environ["URUHA_M31_SEMANTIC_VERIFIER_MODEL"] = "ambient-unbound-model"

    namespace = {"os": os, "load_dotenv": fake_load_dotenv}
    node = _source_decision()
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, str(SOURCE), "exec"), namespace)
    with patch.dict(os.environ, environ, clear=True):
        result = namespace["_load_runtime_dotenv"]()
        injected = os.environ.get("URUHA_M31_SEMANTIC_VERIFIER_MODEL")
    return result, attempted, injected


def test_b_intent_suppresses_unbound_dotenv_import_effect():
    for env in (
        {"URUHA_P4_B_PRIVATE_CHILD": "1"},
        {"URUHA_P4_B_PRIVATE_CHILD": "malformed"},
        {"uruha_p4_b_private_child": "1"},
        {"UrUhA_P4_b_unexpected": ""},
    ):
        result, attempted, injected = _exercise(env)
        assert result is False
        assert attempted == []
        assert injected is None


def test_non_b_import_keeps_existing_dotenv_behavior():
    result, attempted, injected = _exercise({"URUHA_WEB_COMPUTE_LEDGER": "1"})
    assert result is True
    assert attempted == [True]
    assert injected == "ambient-unbound-model"
