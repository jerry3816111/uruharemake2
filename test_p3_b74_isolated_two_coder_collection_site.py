import json
import os
from pathlib import Path
import threading
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import p3_b74_isolated_two_coder_collection_site as b74


def _entry(episode_id: str, index: int):
    rows = [
        ("ASK_CLARIFY", "SEEK_INFORMATION", "UNCERTAIN", "INDIRECT_CONTEXT_DEPENDENT"),
        ("SUPPORT_COMFORT", "AFFILIATE_OR_COMFORT", "WARM_SUPPORTIVE", "LITERAL_ALIGNED"),
        ("HUMOR_TEASE", "PLAY_OR_TEASE", "PLAYFUL", "OVERINTERPRETATION_RISK_CONTROL"),
    ]
    move, goal, stance, relation = rows[index % 3]
    return {
        "episode_id": episode_id,
        "response_moves": [move],
        "primary_interaction_goal": goal,
        "alternative_goals": [],
        "stance": stance,
        "literal_pragmatic_relation": relation,
        "evidence_anchor_count": 1,
        "private_motive_asserted": False,
        "completed_without_prediction_visibility": True,
        "coder_kind": "consenting_human",
    }


def test_contract_and_manifest_are_synthetic_only_with_zero_real_content():
    assert b74.validate_contract() == {"valid": True, "errors": []}
    manifest = b74.build_synthetic_manifest()
    assert b74.validate_manifest(manifest) == []
    assert len(manifest["packets"]) == 18
    assert manifest["scope"] == "synthetic_tooling_only"
    assert manifest["real_source_content_count"] == 0
    assert manifest["model_prediction_count"] == 0


def test_real_or_mutated_manifest_is_rejected():
    manifest = b74.build_synthetic_manifest()
    manifest["scope"] = "real_source"
    manifest["real_source_content_count"] = 18
    errors = b74.validate_manifest(manifest)
    assert "identity" in errors
    assert "forbidden_counts" in errors
    assert "manifest_hash" in errors


def test_two_private_ledgers_use_distinct_tokens_and_restrict_permissions(tmp_path: Path):
    state, urls = b74.create_site(tmp_path / "private", ("coder-a", "coder-b"), tokens=("a" * 32, "b" * 32))
    assert set(urls) == {"coder-a", "coder-b"}
    assert urls["coder-a"] != urls["coder-b"]
    paths = list(state.token_to_path.values())
    assert paths[0] != paths[1]
    assert oct(os.stat(tmp_path / "private").st_mode & 0o777) == "0o700"
    assert all(oct(os.stat(path).st_mode & 0o777) == "0o600" for path in paths)


def test_save_and_restart_preserve_entry_without_cross_coder_copy(tmp_path: Path):
    private = tmp_path / "private"
    state, _urls = b74.create_site(private, ("coder-a", "coder-b"), tokens=("a" * 32, "b" * 32))
    manifest = state.manifest
    first_id = manifest["packets"][0]["episode_id"]
    path_a = state.token_to_path["a" * 32]
    path_b = state.token_to_path["b" * 32]
    b74.save_entry(path_a, manifest, _entry(first_id, 0))
    _state2, _urls2 = b74.create_site(private, ("coder-a", "coder-b"), tokens=("c" * 32, "d" * 32))
    assert first_id in b74.load_json(path_a)["entries"]
    assert b74.load_json(path_b)["entries"] == {}


def test_rendered_page_contains_no_other_coder_identity_or_model_fields(tmp_path: Path):
    state, _urls = b74.create_site(tmp_path / "private", ("alpha-coder", "beta-coder"), tokens=("a" * 32, "b" * 32))
    ledger_a = b74.load_json(state.token_to_path["a" * 32])
    page = b74.render_page(state.manifest, ledger_a, "a" * 32)
    assert "beta-coder" not in page
    assert "alpha-coder" not in page
    assert "baseline" not in page.lower()
    assert "system_prediction" not in page
    assert "winner" not in page.lower()
    assert "synthetic fixture" in page


def test_invalid_form_fails_closed_without_writing(tmp_path: Path):
    state, _urls = b74.create_site(tmp_path / "private", ("coder-a", "coder-b"), tokens=("a" * 32, "b" * 32))
    path = state.token_to_path["a" * 32]
    invalid = _entry(state.manifest["packets"][0]["episode_id"], 0)
    invalid["response_moves"] = []
    try:
        b74.save_entry(path, state.manifest, invalid)
    except ValueError as exc:
        assert "response_moves" in str(exc)
    else:
        raise AssertionError("invalid entry accepted")
    assert b74.load_json(path)["entries"] == {}


def test_http_get_post_roundtrip_and_unknown_token_isolated(tmp_path: Path):
    state, _urls = b74.create_site(tmp_path / "private", ("coder-a", "coder-b"), tokens=("a" * 32, "b" * 32))
    server = b74.ThreadingHTTPServer(("127.0.0.1", 0), b74.make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        with urlopen(f"http://127.0.0.1:{port}/coder/{'a' * 32}") as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "進度：0/18" in page
        first_id = state.manifest["packets"][0]["episode_id"]
        payload = urlencode([
            ("episode_id", first_id),
            ("response_moves", "ASK_CLARIFY"),
            ("primary_interaction_goal", "SEEK_INFORMATION"),
            ("stance", "UNCERTAIN"),
            ("literal_pragmatic_relation", "INDIRECT_CONTEXT_DEPENDENT"),
            ("evidence_anchor_count", "1"),
        ]).encode()
        request = Request(f"http://127.0.0.1:{port}/coder/{'a' * 32}", data=payload, method="POST")
        with urlopen(request) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "進度：1/18" in page
        assert first_id in b74.load_json(state.token_to_path["a" * 32])["entries"]
        assert b74.load_json(state.token_to_path["b" * 32])["entries"] == {}
        try:
            urlopen(f"http://127.0.0.1:{port}/coder/{'z' * 32}")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("unknown token accepted")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_complete_synthetic_analysis_never_authorizes_human_reliability(tmp_path: Path):
    state, _urls = b74.create_site(tmp_path / "private", ("coder-a", "coder-b"), tokens=("a" * 32, "b" * 32))
    for index, packet in enumerate(state.manifest["packets"]):
        entry = _entry(packet["episode_id"], index)
        for path in state.token_to_path.values():
            b74.save_entry(path, state.manifest, entry)
    ledgers = [b74.load_json(path) for path in state.token_to_path.values()]
    result = b74.analyze_synthetic(state.manifest, *ledgers)
    assert result["calculation"]["gates"]["human_reliability_passed"] is True
    assert result["synthetic_fixture_authorizes_human_reliability"] is False
    assert result["real_source_prediction_authorized"] is False
