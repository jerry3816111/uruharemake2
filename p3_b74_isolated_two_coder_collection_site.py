"""B74 localhost-only isolated two-coder collection site (synthetic readiness only)."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

import p3_b73_prospective_response_target_protocol as b73


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b74_isolated_two_coder_collection_site_v1.json"
PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"not_object:{path}")
    return value


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b74_isolated_two_coder_collection_site_contract_v1":
        errors.append("schema")
    if contract.get("status") != "frozen_before_site_execution_or_real_episode_content":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str(binding.get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    site = contract.get("site") or {}
    if site.get("listen_host") != "127.0.0.1" or any(site.get(field) is not expected for field, expected in {
        "two_distinct_private_session_tokens": True,
        "other_coder_identity_or_entries_visible": False,
        "condition_prediction_score_or_winner_visible": False,
        "ledger_root_must_be_explicit_and_outside_tracked_release": True,
        "atomic_ledger_writes": True,
        "restart_preserves_existing_entries": True,
        "analyzer_not_exposed_as_coder_http_route": True,
    }.items()):
        errors.append("site")
    scope = contract.get("b74_execution_scope") or {}
    if scope != {
        "manifest_scope": "synthetic_tooling_only",
        "episode_count_exact": 18,
        "real_source_packet_allowed": False,
        "human_reliability_claim_allowed": False,
        "new_source_content_access_count": 0,
        "model_call_count": 0,
        "production_memory_write_count": 0,
    }:
        errors.append("scope")
    return {"valid": not errors, "errors": errors}


def _synthetic_packet(index: int) -> dict[str, Any]:
    utterances = ["もういい。", "別に。", "好きにすれば。"]
    contexts = ["synthetic supportive context", "synthetic task context", "synthetic playful context"]
    responses = ["そういうことなら、もう少し聞かせて。", "一回確認してからにしよ。", "はいはい、そういう言い方ね。"]
    response = responses[index % 3]
    return {
        "schema": "uruha_p3_b73_response_episode_packet_v1",
        "episode_id": f"synthetic_{index:04d}",
        "provenance": {
            "source_id": "b74-synthetic-only",
            "source_url": "https://example.invalid/b74-synthetic-only",
            "publisher": "synthetic-fixture",
            "observed_at": "2026-09-20T00:00:00Z",
        },
        "stimulus": {
            "surface_form_id": f"surface_{index % 3}",
            "context_variant_id": f"context_{index:04d}",
            "utterance_text": utterances[index % 3],
            "pre_context_text": contexts[index % 3],
            "boundary_status": "usable_stimulus_response_pair",
            "pub_coverage_bucket": ["IMPLICATURE", "PRESUPPOSITION", "REFERENCE"][index % 3],
            "relationship_evidence": [],
            "memory_evidence": [],
            "modality": {"text_available": True, "acoustic_summary_status": "unavailable", "acoustic_features": None},
        },
        "outcome": {
            "response_text": response,
            "response_text_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
            "response_start_ms": index * 10000 + 1000,
            "response_end_ms": index * 10000 + 2500,
        },
        "blinding": {
            "prediction_frozen_before_outcome_access": True,
            "condition_identity_visible_to_coder": False,
            "model_prediction_visible_to_coder": False,
        },
    }


def build_synthetic_manifest() -> dict[str, Any]:
    packets = [_synthetic_packet(index) for index in range(18)]
    manifest = {
        "schema": "uruha_p3_b74_collection_manifest_v1",
        "version": "1.0.0",
        "scope": "synthetic_tooling_only",
        "status": "synthetic_packets_not_human_evidence",
        "packets": packets,
        "real_source_content_count": 0,
        "model_prediction_count": 0,
    }
    manifest["manifest_hash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors = []
    if manifest.get("schema") != "uruha_p3_b74_collection_manifest_v1" or manifest.get("scope") != "synthetic_tooling_only" or manifest.get("status") != "synthetic_packets_not_human_evidence":
        errors.append("identity")
    packets = manifest.get("packets")
    if not isinstance(packets, list) or len(packets) != 18:
        errors.append("packet_count")
        packets = packets if isinstance(packets, list) else []
    ids = []
    for index, packet in enumerate(packets):
        packet_errors = b73.validate_episode_packet(packet)
        errors.extend(f"packet:{index}:{error}" for error in packet_errors)
        ids.append(packet.get("episode_id"))
    if len(ids) != len(set(ids)):
        errors.append("duplicate_episode_id")
    if manifest.get("real_source_content_count") != 0 or manifest.get("model_prediction_count") != 0:
        errors.append("forbidden_counts")
    candidate = deepcopy(manifest)
    expected_hash = candidate.pop("manifest_hash", None)
    if expected_hash != sha256_bytes(canonical_json(candidate).encode("utf-8")):
        errors.append("manifest_hash")
    return errors


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _ledger_path(private_root: Path, pseudonym: str) -> Path:
    digest = hashlib.sha256(pseudonym.encode("utf-8")).hexdigest()[:20]
    root = private_root.resolve()
    path = (root / f"coder-{digest}.json").resolve()
    if path.parent != root:
        raise ValueError("ledger_path_escape")
    return path


def load_or_initialize_ledger(private_root: Path, pseudonym: str, manifest: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if not PSEUDONYM_RE.fullmatch(pseudonym):
        raise ValueError("invalid_pseudonym")
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("invalid_manifest:" + ";".join(errors))
    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private_root, 0o700)
    path = _ledger_path(private_root, pseudonym)
    if path.exists():
        ledger = load_json(path)
        if ledger.get("coder_pseudonym") != pseudonym or ledger.get("manifest_hash") != manifest["manifest_hash"] or ledger.get("evidence_scope") != "synthetic_tooling_only":
            raise ValueError("existing_ledger_identity")
        return path, ledger
    ledger = {
        "schema": "uruha_p3_b73_private_human_annotation_ledger_v1",
        "coder_pseudonym": pseudonym,
        "coder_kind": "consenting_human",
        "evidence_scope": "synthetic_tooling_only",
        "manifest_hash": manifest["manifest_hash"],
        "entries": {},
    }
    _atomic_write(path, ledger)
    return path, ledger


def save_entry(path: Path, manifest: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    ledger = load_json(path)
    episode_ids = [packet["episode_id"] for packet in manifest["packets"]]
    if entry.get("episode_id") not in episode_ids:
        raise ValueError("unknown_episode")
    errors = b73.validate_annotation_entry(entry)
    if errors:
        raise ValueError("invalid_entry:" + ";".join(errors))
    updated = deepcopy(ledger)
    updated["entries"][entry["episode_id"]] = entry
    errors = b73.validate_ledger(updated, episode_ids, require_complete=False)
    if errors:
        raise ValueError("invalid_ledger:" + ";".join(errors))
    _atomic_write(path, updated)
    return updated


def _select_options(values: list[str], *, name: str, multiple: bool = False) -> str:
    suffix = " multiple" if multiple else ""
    return f'<select name="{html.escape(name)}"{suffix}>' + "".join(f'<option value="{html.escape(value)}">{html.escape(value)}</option>' for value in values) + "</select>"


def render_page(manifest: dict[str, Any], ledger: dict[str, Any], token: str) -> str:
    packets = manifest["packets"]
    done = len(ledger["entries"])
    remaining = [packet for packet in packets if packet["episode_id"] not in ledger["entries"]]
    if not remaining:
        body = "<h1>合成工具測試完成</h1><p>18/18 已保存。這不是正式真人可靠度證據。</p>"
    else:
        view = b73.build_coder_view(remaining[0])
        stimulus, outcome = view["stimulus"], view["outcome"]
        move_boxes = "".join(f'<label><input type="checkbox" name="response_moves" value="{html.escape(move)}">{html.escape(move)}</label><br>' for move in b73.load_contract()["codebook"]["response_moves"])
        body = f"""
<h1>UruhaBrain 回應標註工具（合成驗證）</h1>
<p class="warning">目前內容全是 synthetic fixture，只驗證網站，不計入真人研究。</p>
<p>進度：{done}/18</p>
<section><h2>前文與刺激</h2><p>{html.escape(stimulus['pre_context_text'])}</p><blockquote>{html.escape(stimulus['utterance_text'])}</blockquote></section>
<section><h2>實際回應</h2><blockquote>{html.escape(outcome['response_text'])}</blockquote></section>
<form method="post" action="/coder/{html.escape(token)}">
<input type="hidden" name="episode_id" value="{html.escape(view['episode_id'])}">
<fieldset><legend>可觀察 response moves（可複選）</legend>{move_boxes}</fieldset>
<label>主要互動目標 {_select_options(b73.load_contract()['codebook']['interaction_goals'], name='primary_interaction_goal')}</label><br>
<label>替代目標（最多兩個） {_select_options(b73.load_contract()['codebook']['interaction_goals'], name='alternative_goals', multiple=True)}</label><br>
<label>立場 {_select_options(b73.load_contract()['codebook']['stances'], name='stance')}</label><br>
<label>字面／語用關係 {_select_options(b73.load_contract()['codebook']['literal_pragmatic_relations'], name='literal_pragmatic_relation')}</label><br>
<label>證據錨點數 <input type="number" min="1" name="evidence_anchor_count" value="1"></label><br>
<button type="submit">保存並到下一題</button>
</form>"""
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>UruhaBrain B74 coder</title><style>body{{font:16px system-ui;max-width:860px;margin:32px auto;padding:0 16px;background:#0b1020;color:#e8ecff}}section,fieldset{{background:#151d34;border:1px solid #39466d;border-radius:12px;padding:16px;margin:14px 0}}blockquote{{font-size:1.2rem;border-left:4px solid #8aa1ff;padding-left:14px}}label{{line-height:1.9}}select,input,button{{font:inherit;margin:6px;padding:6px}}button{{background:#8aa1ff;border:0;border-radius:8px;padding:10px 16px}}.warning{{color:#ffd27d}}</style></head><body>{body}</body></html>"""


class SiteState:
    def __init__(self, manifest: dict[str, Any], token_to_path: dict[str, Path]):
        self.manifest = manifest
        self.token_to_path = token_to_path
        self.lock = threading.Lock()


def _entry_from_form(payload: dict[str, list[str]]) -> dict[str, Any]:
    try:
        anchors = int((payload.get("evidence_anchor_count") or [""])[0])
    except ValueError as exc:
        raise ValueError("evidence_anchor_count") from exc
    return {
        "episode_id": (payload.get("episode_id") or [""])[0],
        "response_moves": payload.get("response_moves") or [],
        "primary_interaction_goal": (payload.get("primary_interaction_goal") or [""])[0],
        "alternative_goals": payload.get("alternative_goals") or [],
        "stance": (payload.get("stance") or [""])[0],
        "literal_pragmatic_relation": (payload.get("literal_pragmatic_relation") or [""])[0],
        "evidence_anchor_count": anchors,
        "private_motive_asserted": False,
        "completed_without_prediction_visibility": True,
        "coder_kind": "consenting_human",
    }


def make_handler(state: SiteState):
    class Handler(BaseHTTPRequestHandler):
        def _token(self) -> str | None:
            parts = urlparse(self.path).path.strip("/").split("/")
            return parts[1] if len(parts) == 2 and parts[0] == "coder" else None

        def _headers(self, status: int, content_type: str = "text/html; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.end_headers()

        def do_GET(self):
            token = self._token()
            path = state.token_to_path.get(token or "")
            if path is None:
                self._headers(404)
                self.wfile.write(b"not found")
                return
            page = render_page(state.manifest, load_json(path), token)
            self._headers(200)
            self.wfile.write(page.encode("utf-8"))

        def do_POST(self):
            token = self._token()
            path = state.token_to_path.get(token or "")
            if path is None:
                self._headers(404)
                self.wfile.write(b"not found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 65536:
                    raise ValueError("content_length")
                payload = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=False)
                entry = _entry_from_form(payload)
                with state.lock:
                    save_entry(path, state.manifest, entry)
            except (UnicodeDecodeError, ValueError) as exc:
                self._headers(400, "text/plain; charset=utf-8")
                self.wfile.write(f"invalid submission: {exc}".encode("utf-8"))
                return
            self.send_response(303)
            self.send_header("Location", f"/coder/{token}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def log_message(self, _format, *_args):
            return

    return Handler


def create_site(private_root: Path, pseudonyms: tuple[str, str], *, tokens: tuple[str, str] | None = None) -> tuple[SiteState, dict[str, str]]:
    if pseudonyms[0] == pseudonyms[1]:
        raise ValueError("pseudonyms_not_distinct")
    manifest = build_synthetic_manifest()
    paths = [load_or_initialize_ledger(private_root, pseudonym, manifest)[0] for pseudonym in pseudonyms]
    tokens = tokens or (secrets.token_urlsafe(32), secrets.token_urlsafe(32))
    if tokens[0] == tokens[1] or any(len(token) < 24 for token in tokens):
        raise ValueError("invalid_tokens")
    token_to_path = dict(zip(tokens, paths, strict=True))
    state = SiteState(manifest, token_to_path)
    urls = {pseudonym: f"/coder/{token}" for pseudonym, token in zip(pseudonyms, tokens, strict=True)}
    return state, urls


def analyze_synthetic(manifest: dict[str, Any], ledger_a: dict[str, Any], ledger_b: dict[str, Any]) -> dict[str, Any]:
    episode_ids = [packet["episode_id"] for packet in manifest["packets"]]
    report = b73.build_reliability_report(ledger_a, ledger_b, episode_ids)
    return {
        "schema": "uruha_p3_b74_synthetic_site_analysis_v1",
        "status": "synthetic_site_calculation_complete",
        "calculation": report,
        "synthetic_fixture_authorizes_human_reliability": False,
        "real_source_prediction_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-synthetic", action="store_true")
    parser.add_argument("--private-root")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--coder-a", default="coder-a")
    parser.add_argument("--coder-b", default="coder-b")
    args = parser.parse_args()
    if not args.serve_synthetic or not args.private_root:
        parser.error("--serve-synthetic and --private-root are required")
    validation = validate_contract()
    if not validation["valid"]:
        raise SystemExit("invalid contract: " + ";".join(validation["errors"]))
    state, urls = create_site(Path(args.private_root), (args.coder_a, args.coder_b))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(state))
    actual_port = server.server_address[1]
    print(json.dumps({"status": "synthetic_site_ready", "port": actual_port, "urls": {name: f"http://127.0.0.1:{actual_port}{path}" for name, path in urls.items()}, "human_reliability_authorized": False}, ensure_ascii=False), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
