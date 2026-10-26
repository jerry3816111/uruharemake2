"""Inert, injected-effects prototype for one non-B parity attempt.

Nothing in this module supplies a process launcher, HTTP client, or CLI.
Its receipt is deliberately ``fake_*``; it is not authority for a live run,
the B prompt bound, or Safari Send.  The seven-operation worker contains raw
request data, while the parent-facing summary and frames are allowlisted.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import secrets
import select
import signal
import stat
import struct
import threading
import time
from typing import Any

from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256, FROZEN_MANIFEST_SHA256, FROZEN_RUNNER_SHA256,
    GGUF_SHA256, MODEL, SYSTEM_SHA256, TEMPLATE_SHA256, VERSION,
)
from p4_b_non_b_usage_parity import fixed_transformed_request
from uruha_p4_b_child_local_identity import raw_generation


FRAME_LIMIT = 4096
REQUEST_LIMIT = 256 * 1024
RESPONSE_LIMIT = 2 * 1024 * 1024
JOURNAL_NAME = "journal.json"
RECEIPT_NAME = "receipt.json"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RUN = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
_NONCE = re.compile(r"[0-9a-f]{32}\Z")
_STAGES = (
    "before_metadata", "after_render", "before_tokenize_true",
    "before_tokenize_default", "before_completion", "after_completion",
)
_PATHS = (
    ("daemon", "GET", "/api/version"),
    ("daemon", "GET", "/api/tags"),
    ("daemon", "POST", "/api/show"),
    ("daemon", "POST", "/v1/chat/completions"),
    ("runner", "POST", "/tokenize"),
    ("runner", "POST", "/tokenize"),
    ("daemon", "POST", "/v1/chat/completions"),
)
_GRANT_FIELDS = frozenset({
    "run_id", "worker", "ordinal", "target_role", "port", "method",
    "path", "payload_sha256", "expires_at",
})
_WORKER_FIELDS = frozenset({"pid", "ppid", "start_sec", "start_usec"})
_DAEMON_FIELDS = frozenset({
    "pid", "ppid", "raw_generation", "pgid", "port", "argv_sha256",
    "binary_sha256", "manifest_sha256", "template_sha256",
    "system_sha256", "gguf_sha256",
})
_RUNNER_FIELDS = frozenset({
    "pid", "ppid", "raw_generation", "pgid", "port", "argv_sha256",
    "binary_sha256", "gguf_sha256",
})
_SOURCE_FIELDS = frozenset({
    "source_revision", "version", "renderer", "parser", "messages",
    "manifest_messages", "daemon_argv", "runner_argv", "gguf_pre",
    "gguf_model", "gguf_add_bos_token", "model_num_ctx",
    "daemon_default_num_ctx", "normal_request_options",
    "render_request_options",
})
_HTTP_FIELDS = frozenset({
    "requested_url", "effective_url", "proxy_used", "redirected",
    "status", "body",
})


class LiveOperatorError(RuntimeError):
    """Only a fixed, raw-free code is exposed from an injected effect."""


def _fail(code: str) -> None:
    raise LiveOperatorError(code) from None


def _canonical(value: Any, code: str) -> bytes:
    failed = False
    raw = b""
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except Exception:
        failed = True
    if failed:
        _fail(code)
    return raw


def _plain_copy(value: Any, code: str) -> Any:
    return json.loads(_canonical(value, code))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate")
        result[key] = value
    return result


def _reject_constant(_text: str) -> None:
    raise ValueError("constant")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("nonfinite")
    return value


def encode_frame(value: dict) -> bytes:
    """Encode one canonical, bounded parent/worker/helper control frame."""
    if type(value) is not dict:
        _fail("ipc_invalid")
    body = _canonical(value, "ipc_invalid")
    if not body or len(body) > FRAME_LIMIT:
        _fail("ipc_oversize")
    return struct.pack(">I", len(body)) + body


def decode_frame(frame: bytes, *, keys: frozenset[str] | set[str] | None = None) -> dict:
    """Reject noncanonical bytes, duplicate keys, and optional unknown fields."""
    if type(frame) is not bytes or len(frame) < 5:
        _fail("ipc_invalid")
    size = struct.unpack(">I", frame[:4])[0]
    if size == 0 or size > FRAME_LIMIT or len(frame) != size + 4:
        _fail("ipc_invalid")
    failed = False
    value = None
    try:
        value = json.loads(frame[4:].decode("utf-8"),
                           object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant,
                           parse_float=_finite_float)
    except Exception:
        failed = True
    if failed:
        _fail("ipc_invalid")
    if type(value) is not dict or _canonical(value, "ipc_invalid") != frame[4:]:
        _fail("ipc_invalid")
    if keys is not None and set(value) != set(keys):
        _fail("ipc_fields_invalid")
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _valid_sha(value: Any) -> bool:
    return type(value) is str and _SHA.fullmatch(value) is not None


def _port(value: Any) -> bool:
    return type(value) is int and 1 <= value <= 65535 and value != 11434


def _finite_number(value: Any) -> bool:
    if type(value) is int:
        return 0 <= value <= (1 << 63) - 1
    if type(value) is float:
        return math.isfinite(value) and value >= 0
    return False


def _worker(value: Any) -> bool:
    return (type(value) is dict and set(value) == _WORKER_FIELDS
            and type(value["pid"]) is int and value["pid"] > 0
            and type(value["ppid"]) is int and value["ppid"] > 0
            and type(value["start_sec"]) is int and value["start_sec"] >= 0
            and type(value["start_usec"]) is int
            and 0 <= value["start_usec"] < 1_000_000)


def _generation(value: Any, pid: int, ppid: int) -> bool:
    return (type(value) is list and len(value) == 4
            and all(type(item) is int and item >= 0 for item in value)
            and value[0] == pid and value[1] == ppid
            and value[3] < 1_000_000)


def _identity_process(value: Any, *, runner: bool) -> bool:
    keys = _RUNNER_FIELDS if runner else _DAEMON_FIELDS
    if type(value) is not dict or set(value) != keys:
        return False
    pid, ppid = value["pid"], value["ppid"]
    if (type(pid) is not int or pid <= 0 or type(ppid) is not int
            or ppid <= 0 or type(value["pgid"]) is not int
            or value["pgid"] <= 0 or not _port(value["port"])
            or not _generation(value["raw_generation"], pid, ppid)
            or not _valid_sha(value["argv_sha256"])
            or not _valid_sha(value["binary_sha256"])
            or not _valid_sha(value["gguf_sha256"])):
        return False
    if runner:
        return (value["binary_sha256"] == FROZEN_RUNNER_SHA256
                and value["gguf_sha256"] == GGUF_SHA256)
    return (value["binary_sha256"] == FROZEN_DAEMON_SHA256
            and value["manifest_sha256"] == FROZEN_MANIFEST_SHA256
            and value["template_sha256"] == TEMPLATE_SHA256
            and value["system_sha256"] == SYSTEM_SHA256
            and value["gguf_sha256"] == GGUF_SHA256)


def _grant_valid(value: Any, *, nonce_required: bool) -> bool:
    keys = _GRANT_FIELDS | ({"nonce"} if nonce_required else set())
    if type(value) is not dict or set(value) != keys:
        return False
    index = value["ordinal"]
    if (type(index) is not int or not 1 <= index <= 7
            or type(value["run_id"]) is not str
            or _RUN.fullmatch(value["run_id"]) is None
            or not _worker(value["worker"])
            or not _port(value["port"])
            or not _finite_number(value["expires_at"])):
        return False
    role, method, path = _PATHS[index - 1]
    if (value["target_role"] != role or value["method"] != method
            or value["path"] != path):
        return False
    if (value["payload_sha256"] is not None and
            not _valid_sha(value["payload_sha256"])):
        return False
    if method == "GET" and value["payload_sha256"] is not None:
        return False
    if method == "POST" and value["payload_sha256"] is None:
        return False
    return (not nonce_required or
            (type(value["nonce"]) is str and
             _NONCE.fullmatch(value["nonce"]) is not None))


class DurableJournal:
    """Single-use 0600 journal; ``granted`` means *durably minted* only.

    ``ack_callback_returned`` proves only local callback return, not worker
    delivery. A lost ACK or post-ACK durability failure cannot refund a grant
    or turn an uncertain ``on_wire`` into ``no``.
    """

    def __init__(self, run_dir: Path, state: dict):
        self.run_dir = run_dir
        self.path = run_dir / JOURNAL_NAME
        self._state = state
        self._lock = threading.Lock()
        self._poisoned = False
        self._ack_pending = False

    @classmethod
    def create(cls, run_dir: str | os.PathLike[str], run_id: str) -> DurableJournal:
        if type(run_id) is not str or _RUN.fullmatch(run_id) is None:
            _fail("journal_run_invalid")
        directory = Path(run_dir)
        if directory.exists() or directory.is_symlink():
            _fail("journal_existing_run")
        existed = False
        failed = False
        try:
            directory.mkdir(mode=0o700, parents=False, exist_ok=False)
            os.chmod(directory, 0o700)
        except FileExistsError:
            existed = True
        except Exception:
            failed = True
        if existed:
            _fail("journal_existing_run")
        if failed:
            _fail("journal_create_failed")
        state = {
            "schema": "fake_non_b_journal_v1", "run_id": run_id,
            "reserved": 0, "granted": 0, "worker_issued": 0,
            "ack_callback_returned": 0,
            "ack_failed_terminal": 0,
            "completion_attempt_spent": 0, "operations": [],
        }
        path = directory / JOURNAL_NAME
        fd = None
        failed = False
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.fchmod(fd, 0o600)
            raw = _canonical(state, "journal_create_failed")
            if os.write(fd, raw) != len(raw):
                raise OSError("short write")
            os.fsync(fd)
            os.close(fd)
            fd = None
            cls._sync_directory(directory)
        except Exception:
            failed = True
            if fd is not None:
                os.close(fd)
        if failed:
            _fail("journal_create_failed")
        return cls(directory, state)

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _commit(self, state: dict) -> None:
        # Failed replace/fsync poisons this one-use attempt.  It is never
        # retried or reopened, even if the old journal happens to remain.
        suffix = secrets.token_hex(16)
        temp = self.run_dir / f".journal-intent-{suffix}"
        fd = None
        failed = False
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.fchmod(fd, 0o600)
            raw = _canonical(state, "journal_commit_failed")
            if os.write(fd, raw) != len(raw):
                raise OSError("short write")
            os.fsync(fd)
            os.close(fd)
            fd = None
            os.replace(temp, self.path)
            self._sync_directory(self.run_dir)
        except Exception:
            failed = True
            self._poisoned = True
            if fd is not None:
                os.close(fd)
        if failed:
            _fail("journal_commit_failed")
        self._state = state

    def snapshot(self) -> dict:
        with self._lock:
            if self._poisoned:
                _fail("journal_unavailable")
            return _plain_copy(self._state, "journal_invalid")

    def reserve(self, grant_fields: dict, *, ack=None) -> dict:
        if not callable(ack):
            _fail("grant_ack_required")
        if not _grant_valid(grant_fields, nonce_required=False):
            _fail("grant_invalid")
        with self._lock:
            if self._poisoned:
                _fail("journal_unavailable")
            if self._ack_pending or self._state["ack_failed_terminal"]:
                _fail("grant_ack_terminal")
            ordinal = grant_fields["ordinal"]
            if (grant_fields["run_id"] != self._state["run_id"]
                    or ordinal != self._state["reserved"] + 1
                    or ordinal > 7 or self._state["completion_attempt_spent"]):
                _fail("grant_replay_or_order")
            if (ordinal > 1 and
                    grant_fields["worker"] != self._state["operations"][0]["worker"]):
                _fail("grant_worker_drift")
            grant = _plain_copy(grant_fields, "grant_invalid")
            grant["nonce"] = secrets.token_hex(16)
            # Both the ordinal and operation-7 completion spend are durable
            # before *any* ACK leaves this method.
            state = deepcopy(self._state)
            state["reserved"] += 1
            state["granted"] += 1
            if ordinal == 7:
                state["completion_attempt_spent"] = 1
            state["operations"].append({
                **grant, "reserved": 1, "granted": 1,
                "ack_callback_returned": 0, "worker_issued": 0,
                "on_wire": "unknown",
            })
            self._commit(state)
            self._ack_pending = True
        ack_failed = False
        try:
            ack(_plain_copy(grant, "grant_invalid"))
        except Exception:
            ack_failed = True
        if ack_failed:
            with self._lock:
                self._ack_pending = False
                state = deepcopy(self._state)
                state["ack_failed_terminal"] = 1
                self._commit(state)
            _fail("grant_ack_failed")
        # This records the injected callback's local return only.  The
        # final method return itself has no durable delivery witness.
        with self._lock:
            state = deepcopy(self._state)
            state["operations"][ordinal - 1]["ack_callback_returned"] = 1
            state["ack_callback_returned"] += 1
            self._commit(state)
            self._ack_pending = False
        return grant

    def mark_worker_issued(self, ordinal: int, nonce: str) -> None:
        with self._lock:
            if self._poisoned:
                _fail("journal_unavailable")
            if (type(ordinal) is not int or not 1 <= ordinal <= len(self._state["operations"])
                    or type(nonce) is not str):
                _fail("grant_invalid")
            state = deepcopy(self._state)
            op = state["operations"][ordinal - 1]
            if op["nonce"] != nonce or op["worker_issued"]:
                _fail("grant_replay_or_order")
            op["worker_issued"] = 1
            state["worker_issued"] += 1
            self._commit(state)

    def mark_on_wire(self, ordinal: int, nonce: str) -> None:
        with self._lock:
            if self._poisoned:
                _fail("journal_unavailable")
            if (type(ordinal) is not int or not 1 <= ordinal <= len(self._state["operations"])
                    or type(nonce) is not str):
                _fail("grant_invalid")
            state = deepcopy(self._state)
            op = state["operations"][ordinal - 1]
            if op["nonce"] != nonce or op["worker_issued"] != 1 or op["on_wire"] != "unknown":
                _fail("grant_replay_or_order")
            op["on_wire"] = "yes"
            self._commit(state)


def _argv_hash(argv: list[str]) -> str:
    return _sha(_canonical(argv, "source_invalid"))


def _option(argv: list[str], flag: str) -> str:
    values = []
    for index, token in enumerate(argv):
        if token == flag:
            if index + 1 >= len(argv):
                _fail("source_runner_argv_invalid")
            values.append(argv[index + 1])
        elif token.startswith(flag + "="):
            values.append(token[len(flag) + 1:])
    if len(values) != 1:
        _fail("source_runner_argv_invalid")
    return values[0]


def _positive_decimal(value: str) -> int:
    if (type(value) is not str or not value.isascii() or not value.isdecimal()
            or len(value) > 18):
        _fail("source_runner_argv_invalid")
    result = int(value)
    if result <= 0:
        _fail("source_runner_argv_invalid")
    return result


def _source_before_completion(source: dict, rendered_raw: bytes,
                              runner: dict, daemon: dict) -> dict:
    """Derive, rather than accept, branch/BOS/context/truncation predicates."""
    if type(source) is not dict or set(source) != _SOURCE_FIELDS:
        _fail("source_invalid")
    if (source["source_revision"] != "v0.34.4"
            or source["version"] != VERSION
            or source["renderer"] is not None
            or source["parser"] is not None
            or source["messages"] != []
            or source["manifest_messages"] != []
            or source["normal_request_options"] != {}
            or source["render_request_options"] != {}
            or source["gguf_pre"] != "qwen2"
            or source["gguf_model"] != "gpt2"
            or source["gguf_add_bos_token"] is not False):
        _fail("source_branch_or_bos_unproven")
    daemon_argv, runner_argv = source["daemon_argv"], source["runner_argv"]
    if (type(daemon_argv) is not list or not daemon_argv
            or type(runner_argv) is not list or not runner_argv
            or any(type(part) is not str or not part for part in daemon_argv + runner_argv)
            or _argv_hash(daemon_argv) != daemon["argv_sha256"]
            or _argv_hash(runner_argv) != runner["argv_sha256"]):
        _fail("source_argv_drift")
    branch_positions = [index for index, token in enumerate(runner_argv)
                        if token == "--no-jinja"]
    if (len(branch_positions) != 1
            or runner_argv[branch_positions[0]:branch_positions[0] + 3]
            != ["--no-jinja", "--chat-template", "chatml"]
            or any(token == "--jinja" or token.startswith("--jinja=")
                   or token.startswith("--no-jinja=")
                   or token.startswith("--chat-template=")
                   or (token == "--chat-template" and
                       index != branch_positions[0] + 1)
                   for index, token in enumerate(runner_argv))):
        _fail("source_branch_or_bos_unproven")
    # This checks the selected branch flags and their bound argv digest. It
    # does not establish a full launch-argv or binary conformance proof.
    context_total = _positive_decimal(_option(runner_argv, "-c"))
    parallel = _positive_decimal(_option(runner_argv, "-np"))
    if context_total % parallel:
        _fail("source_context_unproven")
    effective_num_ctx = context_total // parallel
    model_ctx = source["model_num_ctx"]
    default_ctx = source["daemon_default_num_ctx"]
    if (model_ctx is not None and
            (type(model_ctx) is not int or model_ctx <= 0)):
        _fail("source_context_unproven")
    if type(default_ctx) is not int or default_ctx <= 0:
        _fail("source_context_unproven")
    request_num_ctx = model_ctx if model_ctx is not None else default_ctx
    if request_num_ctx != effective_num_ctx:
        _fail("source_context_unproven")
    if len(rendered_raw) >= effective_num_ctx:
        _fail("source_wrapper_truncation_unproven")
    return {
        "source_revision": "v0.34.4", "version": VERSION,
        "branch": "go_rendered_chat", "bos_strip_applied": False,
        "context_total": context_total, "parallel": parallel,
        "effective_num_ctx": effective_num_ctx,
        "request_num_ctx": request_num_ctx,
        "rendered_utf8_below_num_ctx": True,
        "daemon_argv_sha256": daemon["argv_sha256"],
        "runner_argv_sha256": runner["argv_sha256"],
    }


def _validate_binding(binding: Any) -> tuple[dict, bytes]:
    if type(binding) is not dict or set(binding) != {
            "run_id", "daemon", "worker", "source", "t0", "work_stop_at"}:
        _fail("binding_invalid")
    raw = _canonical(binding, "binding_invalid")
    if len(raw) > FRAME_LIMIT:
        _fail("binding_invalid")
    copied = json.loads(raw)
    daemon, worker = copied["daemon"], copied["worker"]
    if (type(copied["run_id"]) is not str or _RUN.fullmatch(copied["run_id"]) is None
            or not _finite_number(copied["t0"])
            or not _finite_number(copied["work_stop_at"])
            or copied["work_stop_at"] != copied["t0"] + 80.0
            or not _identity_process(daemon, runner=False)
            or not _worker(worker)
            or worker["pid"] == daemon["pid"]
            or worker["ppid"] <= 0
            or type(copied["source"]) is not dict
            or set(copied["source"]) != _SOURCE_FIELDS):
        _fail("binding_invalid")
    return copied, raw


def _validate_observation(value: Any, binding: dict, *, runner_required: bool,
                          prior_runner_raw: bytes | None) -> tuple[dict | None, bytes | None]:
    if (type(value) is not dict or set(value) !=
            {"run_id", "identity_http_calls", "daemon", "runner"}
            or value["run_id"] != binding["run_id"]
            or type(value["identity_http_calls"]) is not int
            or value["identity_http_calls"] != 0
            or not _identity_process(value["daemon"], runner=False)
            or _canonical(value["daemon"], "identity_drift") !=
               _canonical(binding["daemon"], "identity_drift")):
        _fail("identity_drift")
    runner = value["runner"]
    if not runner_required:
        if runner is not None:
            _fail("identity_drift")
        return None, None
    if (not _identity_process(runner, runner=True)
            or runner["pid"] in (binding["daemon"]["pid"], binding["worker"]["pid"])
            or runner["ppid"] != binding["daemon"]["pid"]
            or runner["port"] == binding["daemon"]["port"]):
        _fail("identity_drift")
    raw = _canonical(runner, "identity_drift")
    if prior_runner_raw is not None and raw != prior_runner_raw:
        _fail("identity_drift")
    return runner, raw


def _tick(clock, previous: float | None, deadline: float | None) -> float:
    failed = False
    value = None
    try:
        value = clock()
    except Exception:
        failed = True
    if failed:
        _fail("clock_unavailable")
    if (not _finite_number(value) or
            (previous is not None and value < previous)):
        _fail("clock_invalid")
    result = float(value)
    if deadline is not None and result >= deadline:
        _fail("work_deadline_exceeded")
    return result


def _json_response(body: bytes) -> dict:
    failed = False
    value = None
    try:
        value = json.loads(body, object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant,
                           parse_float=_finite_float)
    except Exception:
        failed = True
    if failed or type(value) is not dict:
        _fail("response_invalid")
    pending = [(value, 0)]
    visited = 0
    while pending:
        item, depth = pending.pop()
        visited += 1
        if visited > 100_000 or depth > 64:
            _fail("response_invalid")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is float and not math.isfinite(item):
            _fail("response_invalid")
    return value


def _metadata(ordinal: int, response: dict, source: dict) -> None:
    if ordinal == 1:
        if response.get("version") != VERSION:
            _fail("metadata_drift")
    elif ordinal == 2:
        rows = response.get("models")
        if (type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict
                or rows[0].get("name") != MODEL
                or rows[0].get("digest") != FROZEN_MANIFEST_SHA256):
            _fail("metadata_drift")
    elif ordinal == 3:
        # Ollama v0.34.4 ShowResponse omits empty renderer/parser/messages;
        # manifest_messages is private bound manifest evidence, not a show
        # response field. Normalize only the omitted/empty forms here.
        renderer = response.get("renderer")
        parser = response.get("parser")
        messages = response.get("messages", [])
        if (type(response.get("template")) is not str
                or type(response.get("system")) is not str
                or renderer not in (None, "")
                or parser not in (None, "")
                or messages not in (None, [])
                or source["renderer"] is not None
                or source["parser"] is not None
                or source["messages"] != []
                or source["manifest_messages"] != []):
            _fail("metadata_drift")
        failed = False
        template_sha = system_sha = None
        try:
            template_sha = _sha(response["template"].encode("utf-8"))
            system_sha = _sha(response["system"].encode("utf-8"))
        except Exception:
            failed = True
        if failed or template_sha != TEMPLATE_SHA256 or system_sha != SYSTEM_SHA256:
            _fail("metadata_drift")


def _render(response: dict, request: dict) -> tuple[str, bytes]:
    try:
        rendered = response["_debug_info"]["rendered_template"]
        usage = response["usage"]
        choices = response["choices"]
        valid = (response.get("model") == MODEL and type(rendered) is str
                 and type(usage) is dict
                 and all(type(usage.get(key)) is int and usage[key] == 0
                         for key in ("prompt_tokens", "completion_tokens", "total_tokens"))
                 and type(choices) is list and len(choices) == 1
                 and type(choices[0]) is dict
                 and type(choices[0].get("message")) is dict
                 and choices[0]["message"].get("content") == "")
    except Exception:
        valid = False
        rendered = None
    if not valid:
        _fail("render_drift")
    system = request["messages"][0]["content"]
    user = request["messages"][1]["content"]
    expected = ("<|im_start|>system\n" + system + "<|im_end|>\n"
                + "<|im_start|>user\n" + user + "<|im_end|>\n"
                + "<|im_start|>assistant")
    if rendered != expected + "\n":
        _fail("render_drift")
    try:
        raw = rendered.encode("utf-8")
    except Exception:
        raw = None
    if raw is None:
        _fail("render_drift")
    return rendered, raw


def _token_ids(response: dict) -> list[int]:
    tokens = response.get("tokens")
    if (type(tokens) is not list or not tokens
            or any(type(token) is not int or token < 0 for token in tokens)):
        _fail("tokenizer_drift")
    return tokens


def _usage(response: dict) -> dict:
    fields = ("prompt_tokens", "completion_tokens", "total_tokens")
    usage = response.get("usage")
    choices = response.get("choices")
    if ("error" in response or response.get("model") != MODEL
            or type(choices) is not list or len(choices) != 1
            or type(choices[0]) is not dict
            or type(choices[0].get("message")) is not dict
            or type(choices[0]["message"].get("content")) is not str
            or type(usage) is not dict
            or any(type(usage.get(key)) is not int or usage[key] < 0 for key in fields)
            or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]):
        _fail("usage_drift")
    return {key: usage[key] for key in fields}


def worker_once(*, binding: dict, clock, observe_identity, authorize_call,
                http_call) -> dict:
    """Run seven injected calls; no raw prompt, tokens, or completion escapes.

    This worker alone is *not* a watchdog.  Only a separately reviewed
    process-supervised parent could bound a blocked injected callback.
    """
    if (not callable(clock) or not callable(observe_identity)
            or not callable(authorize_call) or not callable(http_call)):
        _fail("worker_configuration_invalid")
    bound, binding_raw = _validate_binding(binding)
    started = _tick(clock, None, None)
    deadline = float(bound["work_stop_at"])
    if started < bound["t0"]:
        _fail("clock_invalid")
    if started >= deadline:
        _fail("work_deadline_exceeded")
    fixture_failed = False
    request = None
    try:
        request = fixed_transformed_request()
    except Exception:
        fixture_failed = True
    if fixture_failed:
        _fail("fixed_request_drift")
    request_raw = _canonical(request, "fixed_request_drift")
    if (len(request_raw) != 1833 or _sha(request_raw) !=
            "7ea87c8e8985dfe7fb2b5dc9198cd9f26caaaa3fbf4c93559405a06230b4eb56"
            or set(request) != {"model", "messages", "temperature", "timeout",
                                    "max_tokens", "response_format"}):
        _fail("fixed_request_drift")
    normal = deepcopy(request)
    del normal["timeout"]
    debug = deepcopy(normal)
    debug["_debug_render_only"] = True
    prior = started
    http_count = 0
    identity_count = 0
    nonce_seen: set[str] = set()
    bound_runner_raw = None
    bound_runner = None

    def tick() -> float:
        nonlocal prior
        prior = _tick(clock, prior, deadline)
        return prior

    def unchanged() -> None:
        if _canonical(binding, "binding_mutated") != binding_raw:
            _fail("binding_mutated")

    def observe(stage: str, runner_required: bool) -> dict | None:
        nonlocal identity_count, bound_runner_raw, bound_runner
        if stage != _STAGES[identity_count]:
            _fail("identity_order_invalid")
        tick()
        failed = False
        value = None
        try:
            value = observe_identity(stage)
        except Exception:
            failed = True
        identity_count += 1
        tick()
        unchanged()
        if failed:
            _fail("identity_unavailable")
        runner, raw = _validate_observation(value, bound,
                                            runner_required=runner_required,
                                            prior_runner_raw=bound_runner_raw)
        if raw is not None and bound_runner_raw is None:
            bound_runner_raw, bound_runner = raw, runner
        return runner

    def send(ordinal: int, payload: dict | None) -> dict:
        nonlocal http_count
        if ordinal != http_count + 1 or ordinal > 7:
            _fail("http_order_invalid")
        role, method, path = _PATHS[ordinal - 1]
        port = (bound["daemon"]["port"] if role == "daemon"
                else bound_runner["port"] if bound_runner is not None else None)
        if not _port(port):
            _fail("identity_drift")
        tick()
        payload_raw = None if payload is None else _canonical(payload, "request_invalid")
        if payload_raw is not None and len(payload_raw) > REQUEST_LIMIT:
            _fail("request_too_large")
        spec = {
            "run_id": bound["run_id"], "worker": deepcopy(bound["worker"]),
            "ordinal": ordinal, "target_role": role, "port": port,
            "method": method, "path": path,
            "payload_sha256": None if payload_raw is None else _sha(payload_raw),
            "expires_at": deadline,
        }
        # The round-trip is the only worker-facing grant schema.  It cannot
        # carry the raw payload; grant bytes are canonical and <=4096.
        spec = decode_frame(encode_frame(spec), keys=_GRANT_FIELDS)
        failed = False
        grant = None
        try:
            grant = authorize_call(deepcopy(spec))
        except Exception:
            failed = True
        tick()
        unchanged()
        if failed:
            _fail("grant_unavailable")
        if not _grant_valid(grant, nonce_required=True):
            _fail("grant_invalid")
        if (any(grant[key] != spec[key] for key in _GRANT_FIELDS)
                or grant["nonce"] in nonce_seen):
            _fail("grant_mismatch")
        grant = decode_frame(encode_frame(grant), keys=_GRANT_FIELDS | {"nonce"})
        nonce_seen.add(grant["nonce"])
        url = f"http://127.0.0.1:{port}{path}"
        # Re-check the binding and grant immediately before the sole injected
        # transport callback.  The future live transport must repeat this
        # check atomically with its own send; this fake seam is not that proof.
        now = tick()
        if now >= grant["expires_at"]:
            _fail("grant_expired")
        remaining = min(deadline, float(grant["expires_at"])) - now
        if remaining <= 0:
            _fail("grant_expired")
        sent_payload = None if payload_raw is None else json.loads(payload_raw)
        callback_grant = deepcopy(grant)
        callback_grant_raw = _canonical(callback_grant, "grant_invalid")
        failed = False
        value = None
        try:
            value = http_call(method, url, sent_payload, remaining, callback_grant)
        except Exception:
            failed = True
        http_count += 1
        tick()
        unchanged()
        if payload_raw is not None and _canonical(sent_payload, "request_mutated") != payload_raw:
            _fail("request_mutated")
        if _canonical(callback_grant, "grant_mutated") != callback_grant_raw:
            _fail("grant_mutated")
        if failed:
            _fail("http_failed")
        if (type(value) is not dict or set(value) != _HTTP_FIELDS
                or value["requested_url"] != url
                or value["effective_url"] != url
                or value["proxy_used"] is not False
                or value["redirected"] is not False
                or type(value["status"]) is not int or value["status"] != 200
                or type(value["body"]) is not bytes):
            _fail("transport_drift")
        if len(value["body"]) > RESPONSE_LIMIT:
            _fail("response_too_large")
        return _json_response(value["body"])

    observe("before_metadata", False)
    for ordinal, payload in ((1, None), (2, None), (3, {"model": MODEL})):
        _metadata(ordinal, send(ordinal, payload), bound["source"])
    rendered, rendered_raw = _render(send(4, debug), request)
    observe("after_render", True)
    observe("before_tokenize_true", True)
    token_true = _token_ids(send(5, {"content": rendered, "add_special": False,
                                      "parse_special": True}))
    observe("before_tokenize_default", True)
    token_default = _token_ids(send(6, {"content": rendered, "add_special": False}))
    if token_true != token_default:
        _fail("tokenizer_drift")
    source_evidence = _source_before_completion(bound["source"], rendered_raw,
                                                bound_runner, bound["daemon"])
    if len(token_true) >= source_evidence["effective_num_ctx"]:
        _fail("source_context_unproven")
    observe("before_completion", True)
    completion = send(7, normal)
    observe("after_completion", True)
    usage = _usage(completion)
    # Source/model state and both observed process identities must still be
    # the same after the one spent completion attempt.
    _source_before_completion(bound["source"], rendered_raw,
                              bound_runner, bound["daemon"])
    tick()
    unchanged()
    delta = usage["prompt_tokens"] - len(token_true)
    summary = {
        "schema": "fake_non_b_worker_v1",
        "status": "fake_non_b_parity_pass" if delta == 0 else "fake_non_b_parity_mismatch",
        "request_sha256": _sha(request_raw),
        "request_utf8_bytes": len(request_raw),
        "rendered_prompt_sha256": _sha(rendered_raw),
        "rendered_prompt_utf8_bytes": len(rendered_raw),
        "identity_observation_sha256": _sha(bound_runner_raw),
        "source_evidence": source_evidence,
        "runner_token_count_parse_special_true": len(token_true),
        "runner_token_count_parse_special_default": len(token_default),
        "provider_usage": usage, "signed_delta": delta,
        "http_calls": http_count, "identity_checks": identity_count,
        "external_completion_attempts": 1,
        "internal_runner_generations": "unknown",
        "elapsed_seconds": prior - started,
        "b_upper_bound_proven": False, "b_send_authorized": False,
    }
    return decode_frame(encode_frame(summary), keys=set(summary))


def supervise_once(*, run_dir, model_root, clock, effects) -> dict:
    """Fail closed until process-witnessed helpers can be reviewed.

    A thread-backed fake would not model exact-PID signaling, reaping, or the
    T0+90 physical-stop receipt.  Exposing such a success path here would
    misstate the exact freeze.  This entry performs no callbacks or writes.
    """
    _fail("process_supervisor_not_implemented")


def _fake_os_witness(pid: int) -> dict:
    """Small *partial* OS witness for an ephemeral test child, never Ollama.

    The live freeze additionally requires argv, binary, listener, source and
    model witnesses; this function does not provide or imply those proofs.
    """
    first = raw_generation(pid)
    pgid = os.getpgid(pid)
    second = raw_generation(pid)
    if first != second or first[0] != pid or pgid <= 0:
        _fail("fake_witness_unavailable")
    return {"pid": pid, "ppid": first[1], "raw_generation": list(first),
            "pgid": pgid}


def _fake_witness_valid(value: Any, pid: int) -> bool:
    return (type(value) is dict
            and set(value) == {"pid", "ppid", "raw_generation", "pgid"}
            and value["pid"] == pid and type(value["pid"]) is int
            and type(value["ppid"]) is int and value["ppid"] > 0
            and _generation(value["raw_generation"], pid, value["ppid"])
            and type(value["pgid"]) is int and value["pgid"] > 0)


def _fake_exact_signal_transaction(initial: dict, observe, signum: int) -> str:
    """Check identity and signal in one *separate* short-lived process.

    The injected observer exists to exercise cleanup stalls/drift. Even if
    it lies, both bracketing OS observations must match the initial witness.
    This retains the documented final-check-to-os.kill PID-reuse residual.
    """
    pid = initial["pid"]
    try:
        if not _fake_witness_valid(initial, pid):
            return "identity_changed_no_signal"
        expected = _canonical(initial, "fake_witness_unavailable")
        first = _fake_os_witness(pid)
        injected_first = observe(pid)
        injected_final = observe(pid)
        final = _fake_os_witness(pid)
        if not all(_fake_witness_valid(item, pid)
                   and _canonical(item, "fake_witness_unavailable") == expected
                   for item in (first, injected_first, injected_final, final)):
            return "identity_changed_no_signal"
        os.kill(pid, signum)  # exact initial PID; never killpg
    except Exception:
        return "witness_or_signal_unavailable"
    return "signal_sent"


def _fake_child_alarm(_signum, _frame) -> None:
    # A synthetic callback or injected observer may never return. This is a
    # backstop for test-owned children, not evidence for the live stop gate.
    os._exit(124)


def _fake_child_lifetime(absolute_deadline: float) -> None:
    # Use the parent's monotonic deadline, not a new interval starting only
    # after fork/set-up. Otherwise slow child startup can outlive the
    # parent's bounded reap window and leave a test child behind.
    signal.signal(signal.SIGALRM, _fake_child_alarm)
    signal.setitimer(signal.ITIMER_REAL,
                     max(0.001, absolute_deadline - time.monotonic()))


def _fake_close(*fds: int) -> None:
    for fd in fds:
        if fd is None:
            continue
        try:
            os.close(fd)
        except OSError:
            pass


def _fake_read_bounded(fd: int, deadline: float, *, framed: bool,
                       keys: set[str] | None = None) -> Any:
    """Parent-side bounded read; framed messages require exact bytes and EOF.

    Each framed sender closes its write end after one frame. Waiting for EOF
    before accepting prevents a second/trailing frame from racing the next
    command. Single-byte cleanup replies use the non-EOF mode.
    """
    raw = bytearray()
    limit = FRAME_LIMIT + 5 if framed else 1
    while time.monotonic() < deadline and len(raw) < limit:
        readable, _, _ = select.select([fd], [], [],
                                       min(0.005, max(0, deadline - time.monotonic())))
        if not readable:
            continue
        try:
            part = os.read(fd, limit - len(raw))
        except BlockingIOError:
            continue
        if not part:
            if framed and len(raw) >= 4:
                size = struct.unpack(">I", raw[:4])[0]
                if 0 < size <= FRAME_LIMIT and len(raw) == size + 4:
                    try:
                        return decode_frame(bytes(raw), keys=keys or {"witness"})
                    except LiveOperatorError:
                        return None
            return None
        raw.extend(part)
        if not framed and raw:
            return bytes(raw)
        if len(raw) >= 4:
            size = struct.unpack(">I", raw[:4])[0]
            if size == 0 or size > FRAME_LIMIT:
                return None
            if len(raw) > size + 4:
                return None
    return None


def _fake_reap_nonblocking(pid: int, statuses: dict[int, int] | None = None) -> bool:
    try:
        seen_pid, wait_status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        # A missing waitable child is not an exit/reap witness. Callers keep
        # an explicit flag only after an exact waitpid result.
        return False
    if seen_pid != pid:
        return False
    if statuses is not None:
        statuses[pid] = wait_status
    return True


def _fake_journal_proof_valid(value: Any) -> bool:
    """Only hashes and the exact grant allowlist may cross this fake IPC."""
    return (type(value) is dict
            and set(value) == {"grant", "journal_sha256"}
            and _grant_valid(value["grant"], nonce_required=True)
            and _valid_sha(value["journal_sha256"]))


def _fake_zero_journal_proof_valid(value: Any, run_id: str) -> bool:
    return (type(value) is dict
            and set(value) == {"phase", "seq", "run_id", "journal_sha256",
                               "reserved", "granted", "completion_attempt_spent"}
            and value["phase"] == "zero" and type(value["seq"]) is int
            and value["seq"] == 1 and value["run_id"] == run_id
            and _valid_sha(value["journal_sha256"])
            and all(type(value[key]) is int and value[key] == 0
                    for key in ("reserved", "granted", "completion_attempt_spent")))


def _fake_staged_op1_proof_valid(value: Any) -> bool:
    return (type(value) is dict and set(value) == {"seq", "grant", "journal_sha256"}
            and type(value["seq"]) is int and value["seq"] == 2
            and _fake_journal_proof_valid(
                {"grant": value["grant"], "journal_sha256": value["journal_sha256"]}))


def _fake_wait_reap(pid: int, deadline: float,
                    statuses: dict[int, int] | None = None) -> bool:
    while time.monotonic() < deadline:
        if _fake_reap_nonblocking(pid, statuses):
            return True
        time.sleep(min(0.003, max(0, deadline - time.monotonic())))
    return _fake_reap_nonblocking(pid, statuses)


def _supervise_fake_callback_once(*, work, observe=None, initial_witness=None,
                                  signal_initial_witness=None,
                                  journal_proof: bool = False,
                                  staged_journal_run_id: str | None = None,
                                  preparation_seconds: float = 0.15,
                                  work_seconds: float = 0.10,
                                  term_grace_seconds: float = 0.04,
                                  cleanup_seconds: float = 0.25) -> dict:
    """Explicitly fake-only process watchdog slice, **not** a live receipt.

    `work` and the observer run only in ephemeral forked children. The
    parent waits for bounded initial witness ACKs before issuing GO,
    and never executes these callbacks or `raw_generation` itself. Missing
    witness means no callback and no ownership/signal claim. All returned
    fields are fixed-code, raw-free test evidence. There are no HTTP grants,
    durable journal/receipt, private port or shared-port proofs here, so
    `supervise_once` remains fail-closed.
    """
    if (not callable(work) or type(journal_proof) is not bool
            or (staged_journal_run_id is not None
                and (journal_proof or type(staged_journal_run_id) is not str
                     or _RUN.fullmatch(staged_journal_run_id) is None))
            or (observe is not None and not callable(observe))
            or (initial_witness is not None and not callable(initial_witness))
            or (signal_initial_witness is not None
                and not callable(signal_initial_witness))):
        _fail("fake_effects_invalid")
    limits = (preparation_seconds, work_seconds, term_grace_seconds,
              cleanup_seconds)
    if any(type(value) not in (int, float) or not math.isfinite(value)
           or not 0.01 <= value <= 5.0 for value in limits):
        _fail("fake_limits_invalid")
    observer = observe or _fake_os_witness
    initial_reader = initial_witness or _fake_os_witness
    signal_initial_reader = signal_initial_witness or _fake_os_witness
    prep_start = time.monotonic()
    hard_life = sum(limits) + preparation_seconds + 0.20
    hard_deadline = prep_start + hard_life
    wr, ww = os.pipe()       # worker initial witness
    cr, cw = os.pipe()       # parent -> worker GO
    dr, dw = os.pipe()       # worker fixed result
    zr, zw = os.pipe() if staged_journal_run_id is not None else (None, None)
    worker_pid = os.fork()
    if worker_pid == 0:
        _fake_close(wr, cw, dr, zr)
        try:
            os.setsid()
            _fake_child_lifetime(hard_deadline)
            actual = _fake_os_witness(os.getpid())
            witness = initial_reader(os.getpid())
            if witness != actual:
                os._exit(126)
            os.write(ww, encode_frame({"witness": witness}))
            _fake_close(ww)
            if os.read(cr, 1) != b"G":
                os._exit(0)
            if staged_journal_run_id is not None:
                stages = iter(work(actual))
                zero = next(stages)
                if not _fake_zero_journal_proof_valid(zero, staged_journal_run_id):
                    os._exit(125)
                os.write(zw, encode_frame(zero))
                _fake_close(zw)
                if os.read(cr, 1) != b"R":
                    os._exit(0)
                work_result = next(stages)
            else:
                work_result = work()
            if (journal_proof and not _fake_journal_proof_valid(work_result)):
                os._exit(125)
            if (staged_journal_run_id is not None
                    and not _fake_staged_op1_proof_valid(work_result)):
                os._exit(125)
            os.write(dw, (encode_frame(work_result)
                          if journal_proof or staged_journal_run_id is not None
                          else b"D"))
            os._exit(0)
        except BaseException:
            os._exit(125)
    _fake_close(ww, cr, dw, zw)
    signal_pid = None
    sr = sc = rr = None
    worker_reaped = False
    signal_reaped = False
    exit_statuses: dict[int, int] = {}
    term_code = "not_attempted"
    kill_code = "not_attempted"
    status = "fake_partial_initial_witness_unavailable"
    t0 = None
    result = None
    try:
        initial_msg = _fake_read_bounded(wr, prep_start + preparation_seconds,
                                         framed=True)
        initial = initial_msg.get("witness") if initial_msg else None
        if not _fake_witness_valid(initial, worker_pid):
            worker_reaped = _fake_wait_reap(worker_pid, hard_deadline + 0.35,
                                            exit_statuses)
            result = {"schema": "fake_process_watchdog_partial_v1",
                    "status": status, "go_issued": False,
                    "worker_reaped": worker_reaped,
                    "signal_reaped": True, "term": term_code,
                    "kill": kill_code, "full_gate_pass": False}
            return result

        # Prestart a separate cleanup transaction process while work is
        # still behind the GO barrier. Its own initial ACK is mandatory.
        sr, sw = os.pipe()
        sc_read, sc = os.pipe()
        rr, rw = os.pipe()
        signal_pid = os.fork()
        if signal_pid == 0:
            _fake_close(sr, sc, rr, wr, cw, dr, zr)
            try:
                os.setsid()
                _fake_child_lifetime(hard_deadline)
                actual_own = _fake_os_witness(os.getpid())
                own = signal_initial_reader(os.getpid())
                if own != actual_own:
                    os._exit(126)
                os.write(sw, encode_frame({"witness": own}))
                _fake_close(sw)
                while True:
                    command = os.read(sc_read, 1)
                    if command not in (b"T", b"K"):
                        os._exit(0)
                    signum = signal.SIGTERM if command == b"T" else signal.SIGKILL
                    code = _fake_exact_signal_transaction(initial, observer,
                                                          signum)
                    os.write(rw, {"signal_sent": b"S",
                                  "identity_changed_no_signal": b"D",
                                  "witness_or_signal_unavailable": b"U"}[code])
            except BaseException:
                os._exit(125)
        _fake_close(sw, sc_read, rw)
        signal_msg = _fake_read_bounded(sr, time.monotonic() + preparation_seconds,
                                        framed=True)
        signal_own = signal_msg.get("witness") if signal_msg else None
        if not _fake_witness_valid(signal_own, signal_pid):
            status = "fake_partial_signal_helper_witness_unavailable"
            worker_reaped = _fake_wait_reap(worker_pid, hard_deadline + 0.35,
                                            exit_statuses)
            signal_reaped = _fake_wait_reap(signal_pid, hard_deadline + 0.35,
                                            exit_statuses)
            result = {"schema": "fake_process_watchdog_partial_v1",
                    "status": status, "go_issued": False,
                    "worker_reaped": worker_reaped,
                    "signal_reaped": signal_reaped,
                    "term": term_code, "kill": kill_code,
                    "full_gate_pass": False}
            return result

        os.set_blocking(cw, False)
        t0 = time.monotonic()
        try:
            if os.write(cw, b"G") != 1:
                raise OSError("short GO")
        except OSError:
            # An ACKed child can still disappear before GO. No callback
            # start is claimed and no raw pipe exception escapes.
            _fake_close(cw)
            worker_reaped = _fake_wait_reap(worker_pid, hard_deadline + 0.35,
                                            exit_statuses)
            result = {"schema": "fake_process_watchdog_partial_v1",
                      "status": "fake_partial_go_unavailable",
                      "go_issued": False, "worker_reaped": worker_reaped,
                      "signal_reaped": False, "term": term_code,
                      "kill": kill_code, "full_gate_pass": False}
            return result
        zero_ack_received = False
        reserve_command_issued = False
        if staged_journal_run_id is not None:
            zero_msg = _fake_read_bounded(
                zr, t0 + work_seconds, framed=True,
                keys={"phase", "seq", "run_id", "journal_sha256", "reserved",
                      "granted", "completion_attempt_spent"})
            zero_ack_received = _fake_zero_journal_proof_valid(
                zero_msg, staged_journal_run_id)
            if zero_ack_received and time.monotonic() < t0 + work_seconds:
                try:
                    reserve_command_issued = os.write(cw, b"R") == 1
                except OSError:
                    reserve_command_issued = False
        work_done = _fake_read_bounded(
            dr, t0 + work_seconds,
            framed=journal_proof or staged_journal_run_id is not None,
            keys=({"seq", "grant", "journal_sha256"}
                  if staged_journal_run_id is not None else
                  {"grant", "journal_sha256"} if journal_proof else None))
        if (journal_proof and not _fake_journal_proof_valid(work_done)):
            work_done = None
        if (staged_journal_run_id is not None
                and not _fake_staged_op1_proof_valid(work_done)):
            work_done = None
        worker_reaped = _fake_reap_nonblocking(worker_pid, exit_statuses)
        work_reported = (type(work_done) is dict
                         if journal_proof or staged_journal_run_id is not None
                         else work_done == b"D")
        if work_reported and not worker_reaped:
            worker_reaped = _fake_wait_reap(worker_pid,
                                           time.monotonic() + 0.02,
                                           exit_statuses)
        if not worker_reaped:
            os.set_blocking(sc, False)
            try:
                os.write(sc, b"T")
            except OSError:
                term_code = "cleanup_command_unavailable"
            else:
                response = _fake_read_bounded(
                    rr, t0 + work_seconds + cleanup_seconds, framed=False)
                term_code = {b"S": "signal_sent", b"D": "identity_changed_no_signal",
                             b"U": "witness_or_signal_unavailable"}.get(
                                 response, "cleanup_observer_timeout")
            grace_end = t0 + work_seconds + term_grace_seconds
            worker_reaped = _fake_wait_reap(worker_pid, grace_end,
                                            exit_statuses)
            if not worker_reaped and term_code == "signal_sent":
                try:
                    os.write(sc, b"K")
                except OSError:
                    kill_code = "cleanup_command_unavailable"
                else:
                    response = _fake_read_bounded(rr, t0 + work_seconds +
                                                  cleanup_seconds, framed=False)
                    kill_code = {b"S": "signal_sent",
                                 b"D": "identity_changed_no_signal",
                                 b"U": "witness_or_signal_unavailable"}.get(
                                     response, "cleanup_observer_timeout")
            worker_reaped = worker_reaped or _fake_wait_reap(
                worker_pid, t0 + work_seconds + cleanup_seconds, exit_statuses)
        worker_status = exit_statuses.get(worker_pid)
        completed_normally = (worker_status is not None
                              and os.WIFEXITED(worker_status)
                              and os.WEXITSTATUS(worker_status) == 0)
        stopped_by_witnessed_signal = (
            worker_status is not None and os.WIFSIGNALED(worker_status)
            and ((term_code == "signal_sent"
                  and os.WTERMSIG(worker_status) == signal.SIGTERM)
                 or (kill_code == "signal_sent"
                     and os.WTERMSIG(worker_status) == signal.SIGKILL)))
        if (work_reported and worker_reaped and completed_normally
                and (staged_journal_run_id is None or reserve_command_issued)):
            status = "fake_partial_work_exited"
        elif worker_reaped and stopped_by_witnessed_signal:
            status = "fake_partial_witnessed_child_reaped"
        else:
            status = "fake_partial_physical_stop_unproven"
        result = {"schema": "fake_process_watchdog_partial_v1",
                "status": status, "go_issued": True,
                "worker_reaped": worker_reaped,
                "signal_reaped": False, "term": term_code,
                "kill": kill_code, "full_gate_pass": False}
        if staged_journal_run_id is not None:
            result["zero_ack_received"] = zero_ack_received
            result["reserve_command_issued"] = reserve_command_issued
        if (status == "fake_partial_work_exited"
                and (journal_proof or staged_journal_run_id is not None)):
            result["work_result"] = work_done
            result["worker_initial_witness"] = initial
        return result
    finally:
        _fake_close(wr, cw, dr, zr)
        if sc is not None:
            try:
                os.write(sc, b"Q")
            except (OSError, BrokenPipeError):
                pass
            _fake_close(sr, sc, rr)
        if signal_pid is not None and not signal_reaped:
            signal_reaped = _fake_wait_reap(signal_pid,
                             hard_deadline + 0.35, exit_statuses)
        if not worker_reaped:
            worker_reaped = _fake_wait_reap(worker_pid,
                             hard_deadline + 0.35, exit_statuses)
        if result is not None:
            result["worker_reaped"] = worker_reaped
            result["signal_reaped"] = signal_reaped or signal_pid is None


def _supervise_fake_journal_op1_once(*, run_dir, grant_without_worker: dict,
                                     crash_after_commit: bool = False,
                                     work_seconds: float = 0.4) -> dict:
    """Fake-only bounded zero-ACK -> op1 durability probe.

    One witnessed ephemeral child first creates/readbacks the zero journal.
    The parent issues the op1 command only after validating its bounded zero
    ACK. The same child then reserves op1 and emits a final proof after all
    commits return. This is still *not* a separate durability helper plus
    worker or a worker-delivered grant; ``supervise_once`` stays fail-closed.
    """
    if (type(grant_without_worker) is not dict
            or set(grant_without_worker) != _GRANT_FIELDS - {"worker"}
            or grant_without_worker.get("ordinal") != 1
            or not _grant_valid({**grant_without_worker,
                                 "worker": {"pid": 1, "ppid": 1,
                                            "start_sec": 0, "start_usec": 0}},
                                nonce_required=False)
            or type(crash_after_commit) is not bool):
        _fail("fake_journal_spec_invalid")
    spec = _plain_copy(grant_without_worker, "fake_journal_spec_invalid")
    directory = Path(run_dir)

    def durable_work(initial):
        generation = initial["raw_generation"]
        worker = {"pid": generation[0], "ppid": generation[1],
                  "start_sec": generation[2], "start_usec": generation[3]}
        journal = DurableJournal.create(directory, spec["run_id"])
        zero_state = journal.snapshot()
        with open(journal.path, "rb") as handle:
            zero_disk = handle.read(FRAME_LIMIT + 1)
        if (len(zero_disk) > FRAME_LIMIT
                or zero_disk != _canonical(zero_state,
                                           "fake_journal_readback_invalid")
                or zero_state["reserved"] != 0 or zero_state["granted"] != 0
                or zero_state["completion_attempt_spent"] != 0
                or zero_state["operations"] != []):
            _fail("fake_journal_readback_invalid")
        yield {"phase": "zero", "seq": 1, "run_id": spec["run_id"],
               "journal_sha256": _sha(zero_disk), "reserved": 0,
               "granted": 0, "completion_attempt_spent": 0}
        grant = journal.reserve({**spec, "worker": worker}, ack=lambda _grant: None)
        state = journal.snapshot()
        # The helper, never the parent watchdog, performs the post-commit
        # readback. A blocked read is subject to the same process deadline.
        with open(journal.path, "rb") as handle:
            disk = handle.read(FRAME_LIMIT + 1)
        if (len(disk) > FRAME_LIMIT
                or disk != _canonical(state, "fake_journal_readback_invalid")
                or state["reserved"] != 1 or state["granted"] != 1
                or state["ack_callback_returned"] != 1
                or state["worker_issued"] != 0
                or state["operations"][0]["on_wire"] != "unknown"):
            _fail("fake_journal_readback_invalid")
        if crash_after_commit:
            os._exit(121)  # injected lost proof after durable commit
        yield {"seq": 2, "grant": grant, "journal_sha256": _sha(disk)}

    watched = _supervise_fake_callback_once(
        work=durable_work,
        staged_journal_run_id=spec["run_id"],
        work_seconds=work_seconds)
    base = {"schema": "fake_process_journal_partial_v1",
            "status": "fake_partial_journal_unproven",
            "watchdog_status": watched["status"],
            "worker_reaped": watched["worker_reaped"],
            "signal_reaped": watched["signal_reaped"],
            "go_issued": watched["go_issued"],
            "term": watched["term"], "kill": watched["kill"],
            "zero_ack_received": watched.get("zero_ack_received", False),
            "reserve_command_issued": watched.get("reserve_command_issued", False),
            "full_gate_pass": False}
    if (watched["status"] != "fake_partial_work_exited"
            or not watched["signal_reaped"]
            or not watched.get("zero_ack_received")
            or not watched.get("reserve_command_issued")):
        return base
    proof = watched.get("work_result")
    initial = watched.get("worker_initial_witness")
    if (not _fake_staged_op1_proof_valid(proof)
            or not _fake_witness_valid(initial, initial.get("pid", -1)
                                       if type(initial) is dict else -1)):
        return base
    generation = initial["raw_generation"]
    expected_worker = {"pid": generation[0], "ppid": generation[1],
                       "start_sec": generation[2], "start_usec": generation[3]}
    grant = proof["grant"]
    if (not _grant_valid(grant, nonce_required=True)
            or _canonical({key: grant[key] for key in _GRANT_FIELDS - {"worker"}},
                          "fake_journal_proof_invalid") != _canonical(
                              spec, "fake_journal_proof_invalid")
            or grant["worker"] != expected_worker):
        return base
    return {**base, "status": "fake_partial_op1_durable_proof",
            "journal_sha256": proof["journal_sha256"],
            "grant_sha256": _sha(_canonical(grant, "fake_journal_proof_invalid")),
            "reserved": 1, "granted": 1, "worker_issued": 0,
            "on_wire": "unknown"}


# This is a separate fake-only process topology. Each edge has its own
# one-frame pipe, so EOF proves there was no second or trailing frame.
_SPLIT_SCHEMA = "fake_split_op1_v1"
_SPLIT_EDGES = (
    "d_initial", "w_initial", "d_go", "d_zero", "w_go", "w_request",
    "d_reserve", "d_proof", "w_delivery", "w_received",
)
_SPLIT_EXTRA = {
    "initial": frozenset({"role"}),
    "d_go": frozenset(),
    "zero": frozenset({"journal_sha256", "reserved", "granted",
                       "completion_attempt_spent"}),
    "w_go": frozenset(),
    "op1_request": frozenset({"fields"}),
    "reserve": frozenset({"fields", "worker_witness"}),
    "grant_proof": frozenset({"grant", "journal_sha256"}),
    "grant_delivery": frozenset({"grant", "journal_sha256"}),
    "received": frozenset({"grant_sha256"}),
    "signal_term": frozenset({"target_role", "target_witness"}),
    "signal_kill": frozenset({"target_role", "target_witness"}),
    "signal_result": frozenset({"target_role", "signal_name", "code"}),
    "receipt_preflight": frozenset(),
    "receipt_preflight_ack": frozenset(),
    "receipt_write": frozenset({"receipt"}),
    "receipt_proof": frozenset({"receipt_sha256", "receipt_bytes"}),
}
_SPLIT_BASE = frozenset({"schema", "run_id", "phase", "seq", "witness"})
_SPLIT_SIGNAL_CODES = frozenset({
    "signal_sent", "identity_changed_no_signal", "witness_or_signal_unavailable",
})
_SPLIT_RECEIPT_FIELDS = frozenset({
    "schema", "run_id", "snapshot_phase", "status", "failure_code",
    "zero_ack_received",
    "request_accepted", "grant_proven", "worker_received_proven",
    "reserved", "granted", "worker_issued", "on_wire", "journal_sha256",
    "grant_sha256", "d_reaped", "w_reaped", "s_d_reaped", "s_w_reaped",
    "d_term", "d_kill", "w_term", "w_kill", "d_stop", "w_stop",
    "physical_stop_unproven", "full_gate_pass", "b_upper_bound_proven",
    "b_send_authorized",
})
_SPLIT_FAILURE_CODES = frozenset({
    "initial_unavailable", "receipt_helper_initial_unavailable",
    "receipt_preflight_unavailable",
    "signal_helper_initial_unavailable", "zero_ack_unavailable",
    "worker_request_unavailable", "grant_proof_unavailable",
    "worker_received_ack_unavailable", "ipc_or_spawn_unavailable",
    "signal_helper_exit_unavailable", "cleanup_unavailable",
    "receipt_unavailable_review_required", "none",
})
_SPLIT_CLEANUP_CODES = frozenset({
    "not_attempted", "command_sent", "cleanup_command_unavailable",
    "cleanup_response_unavailable",
}) | _SPLIT_SIGNAL_CODES
_SPLIT_STOP_CODES = frozenset({
    "normal_exit", "witnessed_term", "witnessed_kill", "unproven",
})


def _split_zero_state(run_id: str) -> dict:
    # Match DurableJournal.create's canonical, empty state without touching
    # disk on the parent watchdog. D independently reads back actual bytes.
    return {
        "schema": "fake_non_b_journal_v1", "run_id": run_id,
        "reserved": 0, "granted": 0, "worker_issued": 0,
        "ack_callback_returned": 0, "ack_failed_terminal": 0,
        "completion_attempt_spent": 0, "operations": [],
    }


def _split_worker_from_witness(witness: dict) -> dict:
    generation = witness["raw_generation"]
    return {"pid": generation[0], "ppid": generation[1],
            "start_sec": generation[2], "start_usec": generation[3]}


def _split_worker_request(spec: dict, witness: dict) -> dict:
    """W alone builds its own pending request after both initial ACKs."""
    return {**spec, "worker": _split_worker_from_witness(witness)}


def _split_frame(run_id: str, phase: str, seq: int, witness: dict,
                 **extra) -> dict:
    return {"schema": _SPLIT_SCHEMA, "run_id": run_id, "phase": phase,
            "seq": seq, "witness": witness, **extra}


def _split_same(left: Any, right: Any) -> bool:
    try:
        return _canonical(left, "ipc_invalid") == _canonical(right, "ipc_invalid")
    except LiveOperatorError:
        return False


def _split_fields_valid(fields: Any, spec: dict, worker_witness: dict) -> bool:
    if not _grant_valid(fields, nonce_required=False):
        return False
    if not _fake_witness_valid(worker_witness, worker_witness.get("pid", -1)
                               if type(worker_witness) is dict else -1):
        return False
    expected = {**spec, "worker": _split_worker_from_witness(worker_witness)}
    return _split_same(fields, expected)


def _split_grant_valid(grant: Any, fields: dict) -> bool:
    return (_grant_valid(grant, nonce_required=True)
            and _split_same({key: grant[key] for key in _GRANT_FIELDS}, fields)
            and time.monotonic() < grant["expires_at"])


def _split_receipt_payload(result: dict, run_id: str) -> dict:
    """Project only fixed fake-result fields into the on-disk receipt."""
    reserved = result["durable_reserved"]
    return {
        "schema": "fake_split_receipt_v1", "run_id": run_id,
        "snapshot_phase": "after_dw_cleanup_before_r_final_reap",
        "status": result["status"], "failure_code": result["failure_code"],
        "zero_ack_received": result["zero_ack_received"],
        "request_accepted": result["request_accepted"],
        "grant_proven": result["grant_proven"],
        "worker_received_proven": result["worker_received_proven"],
        "reserved": reserved, "granted": reserved,
        "worker_issued": 0, "on_wire": "unknown",
        "journal_sha256": result.get("journal_sha256"),
        "grant_sha256": result.get("grant_sha256"),
        **{key: result[key] for key in (
            "d_reaped", "w_reaped", "s_d_reaped", "s_w_reaped",
            "d_term", "d_kill", "w_term", "w_kill", "d_stop", "w_stop")},
        "physical_stop_unproven": True, "full_gate_pass": False,
        "b_upper_bound_proven": False, "b_send_authorized": False,
    }


def _split_receipt_valid(value: Any, run_id: str) -> bool:
    if (type(value) is not dict or set(value) != _SPLIT_RECEIPT_FIELDS
            or value["schema"] != "fake_split_receipt_v1"
            or value["run_id"] != run_id
            or value["snapshot_phase"] != "after_dw_cleanup_before_r_final_reap"
            or value["status"] not in (
                "fake_partial_split_unproven", "fake_partial_op1_worker_received")
            or value["failure_code"] not in _SPLIT_FAILURE_CODES
            or value["reserved"] not in (0, 1, "unknown")
            or type(value["reserved"]) not in (int, str)
            or type(value["granted"]) is not type(value["reserved"])
            or value["granted"] != value["reserved"]
            or value["worker_issued"] != 0
            or type(value["worker_issued"]) is not int
            or value["on_wire"] != "unknown"
            or any(value[key] is not None and not _valid_sha(value[key])
                   for key in ("journal_sha256", "grant_sha256"))
            or any(type(value[key]) is not bool for key in (
                "zero_ack_received", "request_accepted", "grant_proven",
                "worker_received_proven", "d_reaped", "w_reaped",
                "s_d_reaped", "s_w_reaped"))
            or any(value[key] not in _SPLIT_CLEANUP_CODES for key in (
                "d_term", "d_kill", "w_term", "w_kill"))
            or any(value[key] not in _SPLIT_STOP_CODES
                   for key in ("d_stop", "w_stop"))
            or any(value[key] is not expected for key, expected in (
                ("physical_stop_unproven", True), ("full_gate_pass", False),
                ("b_upper_bound_proven", False),
                ("b_send_authorized", False)))):
        return False
    if (value["worker_received_proven"]
            and (not value["grant_proven"] or value["reserved"] != 1)):
        return False
    if (value["status"] == "fake_partial_op1_worker_received"
            and (value["failure_code"] != "none"
                 or not value["worker_received_proven"])):
        return False
    return True


def _split_frame_valid(value: Any, *, run_id: str, phase: str, seq: int,
                       witness: dict | None = None, pid: int | None = None,
                       role: str | None = None, spec: dict | None = None,
                       worker_witness: dict | None = None,
                       fields: dict | None = None, grant: dict | None = None,
                       journal_sha256: str | None = None,
                       target_role: str | None = None,
                       target_witness: dict | None = None,
                       signal_name: str | None = None,
                       receipt: dict | None = None) -> bool:
    """Exact schema and semantic allowlist before encode/after decode."""
    if (type(value) is not dict or phase not in _SPLIT_EXTRA
            or set(value) != _SPLIT_BASE | _SPLIT_EXTRA[phase]
            or value["schema"] != _SPLIT_SCHEMA or value["run_id"] != run_id
            or value["phase"] != phase or type(value["seq"]) is not int
            or value["seq"] != seq):
        return False
    try:
        if len(_canonical(value, "ipc_invalid")) + 4 > FRAME_LIMIT:
            return False
    except LiveOperatorError:
        return False
    got_witness = value["witness"]
    if (type(got_witness) is not dict
            or not _fake_witness_valid(got_witness, got_witness.get("pid", -1))):
        return False
    if witness is None:
        if (phase != "initial" or pid is None
                or not _fake_witness_valid(got_witness, pid)
                or got_witness["ppid"] != os.getpid()
                or got_witness["pgid"] != pid):
            return False
    elif not _split_same(got_witness, witness):
        return False
    if phase == "initial":
        return value["role"] == role and role in (
            "D", "W", "R", "S_D", "S_W", "S_R")
    if phase in ("signal_term", "signal_kill"):
        return (target_role in ("D", "W", "R")
                and value["target_role"] == target_role
                and target_witness is not None
                and _split_same(value["target_witness"], target_witness))
    if phase == "signal_result":
        return (target_role in ("D", "W", "R")
                and value["target_role"] == target_role
                and signal_name in ("term", "kill")
                and value["signal_name"] == signal_name
                and value["code"] in _SPLIT_SIGNAL_CODES)
    if phase == "receipt_write":
        return _split_receipt_valid(value["receipt"], run_id)
    if phase == "receipt_proof":
        if receipt is None or not _split_receipt_valid(receipt, run_id):
            return False
        raw = _canonical(receipt, "ipc_invalid")
        return (value["receipt_sha256"] == _sha(raw)
                and type(value["receipt_bytes"]) is int
                and value["receipt_bytes"] == len(raw))
    if phase == "zero":
        return (journal_sha256 is not None
                and value["journal_sha256"] == journal_sha256
                and all(type(value[key]) is int and value[key] == 0
                        for key in ("reserved", "granted",
                                    "completion_attempt_spent")))
    if phase in ("op1_request", "reserve"):
        if spec is None:
            return False
        bound_worker = (got_witness if phase == "op1_request"
                        else value["worker_witness"])
        return (worker_witness is None or _split_same(bound_worker, worker_witness)) \
            and _split_fields_valid(value["fields"], spec, bound_worker)
    if phase in ("grant_proof", "grant_delivery"):
        return (fields is not None and _split_grant_valid(value["grant"], fields)
                and _valid_sha(value["journal_sha256"])
                and (journal_sha256 is None
                     or value["journal_sha256"] == journal_sha256)
                and (grant is None or _split_same(value["grant"], grant)))
    if phase == "received":
        return (grant is not None and value["grant_sha256"] ==
                _sha(_canonical(grant, "ipc_invalid")))
    return True  # fixed, payload-free GO commands


def _split_close_except(pipes: dict[str, tuple[int, int]], keep: set[int]) -> None:
    for read_fd, write_fd in pipes.values():
        if read_fd not in keep:
            _fake_close(read_fd)
        if write_fd not in keep:
            _fake_close(write_fd)


def _split_send(fd: int, value: dict, deadline: float, **validation) -> bool:
    """One nonblocking bounded canonical frame; caller closes its one-shot FD."""
    try:
        if not _split_frame_valid(value, **validation):
            return False
        frame = encode_frame(value)
        if type(frame) is not bytes or not 5 <= len(frame) <= FRAME_LIMIT:
            return False
        # Validate the actual bytes after serialization but before writing.
        # A changed encoder must not put raw/unknown fields on the IPC pipe.
        encoded_value = decode_frame(
            frame, keys=set(_SPLIT_BASE | _SPLIT_EXTRA[validation["phase"]]))
        if (not _split_frame_valid(encoded_value, **validation)
                or not _split_same(encoded_value, value)):
            return False
        os.set_blocking(fd, False)
        offset = 0
        while offset < len(frame) and time.monotonic() < deadline:
            _, writable, _ = select.select([], [fd], [], min(
                0.005, max(0, deadline - time.monotonic())))
            if not writable:
                continue
            try:
                written = os.write(fd, frame[offset:])
            except BlockingIOError:
                continue
            if written <= 0:
                return False
            offset += written
        return offset == len(frame)
    except Exception:
        # Neither an injected encoder nor an OS callback may expose a raw
        # exception string through this fake control boundary.
        return False


def _split_receive(fd: int, deadline: float, *, phase: str, **validation) -> dict | None:
    keys = set(_SPLIT_BASE | _SPLIT_EXTRA[phase])
    value = _fake_read_bounded(fd, deadline, framed=True, keys=keys)
    if not _split_frame_valid(value, phase=phase, **validation):
        return None
    return value


def _split_disk_readback(journal: DurableJournal, state: dict) -> bytes:
    fd = os.open(journal.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(fd)
        disk = os.read(fd, FRAME_LIMIT + 1)
    finally:
        _fake_close(fd)
    if (not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or len(disk) > FRAME_LIMIT
            or disk != _canonical(state, "fake_journal_readback_invalid")):
        _fail("fake_journal_readback_invalid")
    return disk


def _split_d_child(pipes: dict[str, tuple[int, int]], *, run_dir: Path,
                   spec: dict, hard_deadline: float, work_deadline: float,
                   fault: str | None) -> int:
    owned = (pipes["d_initial"][1], pipes["d_go"][0],
             pipes["d_zero"][1], pipes["d_reserve"][0],
             pipes["d_proof"][1])
    _split_close_except(pipes, set(owned))
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        own = _fake_os_witness(os.getpid())
        run_id = spec["run_id"]
        initial = _split_frame(run_id, "initial", 0, own, role="D")
        if not _split_send(owned[0], initial, work_deadline, run_id=run_id,
                           phase="initial", seq=0, witness=own, role="D"):
            return 125
        _fake_close(owned[0])
        go = _split_receive(owned[1], work_deadline, phase="d_go",
                            run_id=run_id, seq=1, witness=own)
        _fake_close(owned[1])
        if go is None:
            return 125
        journal = DurableJournal.create(run_dir, run_id)
        zero_state = journal.snapshot()
        if not _split_same(zero_state, _split_zero_state(run_id)):
            return 125
        zero_disk = _split_disk_readback(journal, zero_state)
        zero_sha = _sha(zero_disk)
        zero = _split_frame(run_id, "zero", 1, own,
                            journal_sha256=zero_sha, reserved=0, granted=0,
                            completion_attempt_spent=0)
        if not _split_send(owned[2], zero, work_deadline, run_id=run_id,
                           phase="zero", seq=1, witness=own,
                           journal_sha256=zero_sha):
            return 125
        _fake_close(owned[2])
        if fault == "d_after_zero":
            return 121
        reserve = _split_receive(owned[3], work_deadline, phase="reserve",
                                  run_id=run_id, seq=2, witness=own, spec=spec)
        _fake_close(owned[3])
        if reserve is None:
            return 125
        fields = reserve["fields"]
        grant = journal.reserve(fields, ack=lambda _grant: None)
        state = journal.snapshot()
        disk = _split_disk_readback(journal, state)
        if (state["reserved"] != 1 or state["granted"] != 1
                or state["ack_callback_returned"] != 1
                or state["worker_issued"] != 0
                or state["operations"][0]["on_wire"] != "unknown"):
            return 125
        if fault == "d_after_commit":
            return 121
        proof = _split_frame(run_id, "grant_proof", 2, own,
                             grant=grant, journal_sha256=_sha(disk))
        return (0 if _split_send(owned[4], proof, work_deadline, run_id=run_id,
                                 phase="grant_proof", seq=2, witness=own,
                                 fields=fields) else 125)
    except BaseException:
        return 125
    finally:
        _fake_close(*owned)


def _split_w_child(pipes: dict[str, tuple[int, int]], *, spec: dict,
                   hard_deadline: float, work_deadline: float,
                   fault: str | None) -> int:
    owned = (pipes["w_initial"][1], pipes["w_go"][0],
             pipes["w_request"][1], pipes["w_delivery"][0],
             pipes["w_received"][1])
    _split_close_except(pipes, set(owned))
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        own = _fake_os_witness(os.getpid())
        run_id = spec["run_id"]
        initial = _split_frame(run_id, "initial", 0, own, role="W")
        if not _split_send(owned[0], initial, work_deadline, run_id=run_id,
                           phase="initial", seq=0, witness=own, role="W"):
            return 125
        _fake_close(owned[0])
        go = _split_receive(owned[1], work_deadline, phase="w_go",
                            run_id=run_id, seq=1, witness=own)
        _fake_close(owned[1])
        if go is None:
            return 125
        fields = _split_worker_request(spec, own)
        request = _split_frame(run_id, "op1_request", 1, own, fields=fields)
        if not _split_send(owned[2], request, work_deadline, run_id=run_id,
                           phase="op1_request", seq=1, witness=own, spec=spec):
            return 125
        _fake_close(owned[2])
        if fault == "w_after_request":
            return 121
        delivery = _split_receive(owned[3], work_deadline,
                                   phase="grant_delivery", run_id=run_id,
                                   seq=2, witness=own, fields=fields)
        _fake_close(owned[3])
        if delivery is None:
            return 125
        ack = _split_frame(run_id, "received", 2, own,
                           grant_sha256=_sha(_canonical(
                               delivery["grant"], "ipc_invalid")))
        return (0 if _split_send(owned[4], ack, work_deadline, run_id=run_id,
                                 phase="received", seq=2, witness=own,
                                 grant=delivery["grant"]) else 125)
    except BaseException:
        return 125
    finally:
        _fake_close(*owned)


def _split_write_receipt(run_dir: Path, receipt: dict, run_id: str) -> tuple[str, int]:
    """R-only one-use O_EXCL receipt; no parent filesystem callback."""
    if not _split_receipt_valid(receipt, run_id):
        _fail("receipt_invalid")
    directory = Path(run_dir)
    directory_mode = os.lstat(directory).st_mode
    if (not stat.S_ISDIR(directory_mode)
            or stat.S_IMODE(directory_mode) != 0o700):
        _fail("receipt_directory_invalid")
    raw = _canonical(receipt, "receipt_invalid")
    if len(raw) > FRAME_LIMIT:
        _fail("receipt_oversize")
    path = directory / RECEIPT_NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        if os.write(fd, raw) != len(raw):
            _fail("receipt_short_write")
        os.fsync(fd)
    finally:
        _fake_close(fd)
    DurableJournal._sync_directory(directory)
    read_fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(read_fd)
        readback = os.read(read_fd, FRAME_LIMIT + 1)
    finally:
        _fake_close(read_fd)
    if (not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or readback != raw):
        _fail("receipt_readback_invalid")
    return _sha(raw), len(raw)


def _split_receipt_preflight(run_dir: Path, run_id: str) -> bool:
    """R-only new-run, zero-journal and receipt-absence check before W GO."""
    directory = Path(run_dir)
    mode = os.lstat(directory).st_mode
    if (not stat.S_ISDIR(mode) or stat.S_IMODE(mode) != 0o700
            or set(os.listdir(directory)) != {JOURNAL_NAME}):
        return False
    fd = os.open(directory / JOURNAL_NAME,
                 os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(fd)
        raw = os.read(fd, FRAME_LIMIT + 1)
    finally:
        _fake_close(fd)
    return (stat.S_ISREG(metadata.st_mode)
            and stat.S_IMODE(metadata.st_mode) == 0o600
            and raw == _canonical(_split_zero_state(run_id), "ipc_invalid"))


def _split_receipt_child(receipt_pipes: dict[str, tuple[int, int]], *,
                         inherited_split_fds: set[int],
                         inherited_signal_pipes: dict[str, tuple[int, int]],
                         run_dir: Path, run_id: str, initial_reader,
                         prep_deadline: float, preflight_deadline: float,
                         work_deadline: float,
                         hard_deadline: float, fault: str | None) -> int:
    """Pre-witnessed R stays idle until P's final raw-free receipt command."""
    owned = (receipt_pipes["r_initial"][1],
             receipt_pipes["r_preflight"][0],
             receipt_pipes["r_preflight_ack"][1],
             receipt_pipes["r_write"][0], receipt_pipes["r_proof"][1])
    _fake_close(*inherited_split_fds)
    _split_close_except(inherited_signal_pipes, set())
    _split_close_except(receipt_pipes, set(owned))
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        actual = _fake_os_witness(os.getpid())
        own = initial_reader(os.getpid())
        if not _split_same(actual, own):
            return 126
        initial = _split_frame(run_id, "initial", 0, own, role="R")
        if not _split_send(owned[0], initial, prep_deadline, run_id=run_id,
                           phase="initial", seq=0, witness=own, role="R"):
            return 125
        _fake_close(owned[0])
        preflight = _split_receive(owned[1], preflight_deadline,
                                    phase="receipt_preflight", run_id=run_id,
                                    seq=1, witness=own)
        _fake_close(owned[1])
        if preflight is None:
            return 0
        if not _split_receipt_preflight(run_dir, run_id):
            return 125
        ack = _split_frame(run_id, "receipt_preflight_ack", 1, own)
        if not _split_send(owned[2], ack, preflight_deadline, run_id=run_id,
                           phase="receipt_preflight_ack", seq=1,
                           witness=own):
            return 125
        _fake_close(owned[2])
        command = _split_receive(owned[3], work_deadline,
                                  phase="receipt_write", run_id=run_id,
                                  seq=2, witness=own)
        _fake_close(owned[3])
        if command is None:
            return 0  # No final command or invalid/lost frame; never write.
        receipt = command["receipt"]
        sha, size = _split_write_receipt(run_dir, receipt, run_id)
        if fault == "r_after_commit":
            return 121
        proof = _split_frame(run_id, "receipt_proof", 2, own,
                             receipt_sha256=sha, receipt_bytes=size)
        if not _split_send(owned[4], proof, work_deadline, run_id=run_id,
                           phase="receipt_proof", seq=2, witness=own,
                           receipt=receipt):
            return 125
        _fake_close(owned[4])
        return 121 if fault == "r_after_proof" else 0
    except BaseException:
        return 125
    finally:
        _fake_close(*owned)


def _split_signal_child(signal_pipes: dict[str, tuple[int, int]], *,
                        inherited_split_fds: set[int],
                        run_id: str, target_role: str, target_witness: dict,
                        initial_reader, observer, prep_deadline: float,
                        cleanup_deadline: float, hard_deadline: float) -> int:
    """Pre-witnessed, independent exact-PID transaction child for D or W."""
    prefix = f"s_{target_role.lower()}"
    owned = (signal_pipes[f"{prefix}_initial"][1],
             signal_pipes[f"{prefix}_term"][0],
             signal_pipes[f"{prefix}_term_result"][1],
             signal_pipes[f"{prefix}_kill"][0],
             signal_pipes[f"{prefix}_kill_result"][1])
    # S inherits the original ten pipes from P. Closing every unowned end is
    # necessary: one stray writer would suppress D/W's frame+EOF proof.
    _fake_close(*inherited_split_fds)
    _split_close_except(signal_pipes, set(owned))
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        actual = _fake_os_witness(os.getpid())
        own = initial_reader(os.getpid())
        if not _split_same(actual, own):
            return 126
        initial = _split_frame(run_id, "initial", 0, own,
                               role=f"S_{target_role}")
        if not _split_send(owned[0], initial, prep_deadline, run_id=run_id,
                           phase="initial", seq=0, witness=own,
                           role=f"S_{target_role}"):
            return 125
        _fake_close(owned[0])
        for name, seq, signum, command_fd, reply_fd in (
                ("term", 1, signal.SIGTERM, owned[1], owned[2]),
                ("kill", 2, signal.SIGKILL, owned[3], owned[4])):
            command = _split_receive(
                command_fd, cleanup_deadline, phase=f"signal_{name}",
                run_id=run_id, seq=seq, witness=own,
                target_role=target_role, target_witness=target_witness)
            _fake_close(command_fd)
            if command is None:
                return 0  # P did not request this transaction or pipe broke.
            code = _fake_exact_signal_transaction(target_witness, observer,
                                                  signum)
            reply = _split_frame(run_id, "signal_result", seq, own,
                                 target_role=target_role,
                                 signal_name=name, code=code)
            if not _split_send(reply_fd, reply, cleanup_deadline,
                               run_id=run_id, phase="signal_result", seq=seq,
                               witness=own, target_role=target_role,
                               signal_name=name):
                return 125
            _fake_close(reply_fd)
        return 0
    except BaseException:
        return 125
    finally:
        _fake_close(*owned)


def _split_cleanup_children(*, result: dict, statuses: dict[int, int],
                            roles: tuple[str, ...] = ("D", "W"),
                            child_pids: dict[str, int | None],
                            child_witnesses: dict[str, dict],
                            signal_pids: dict[str, int],
                            signal_witnesses: dict[str, dict],
                            signal_pipes: dict[str, tuple[int, int]],
                            signal_parent_fds: set[int], run_id: str,
                            work_deadline: float, cleanup_deadline: float,
                            hard_deadline: float,
                            term_grace_seconds: float) -> None:
    """Bounded P-side exact witnessed cleanup; no parent OS observation."""

    def close_parent(fd: int) -> None:
        _fake_close(fd)
        signal_parent_fds.discard(fd)

    def command(role: str, name: str) -> bool:
        fd = signal_pipes[f"s_{role.lower()}_{name}"][1]
        try:
            frame = _split_frame(run_id, f"signal_{name}",
                                 1 if name == "term" else 2,
                                 signal_witnesses[role], target_role=role,
                                 target_witness=child_witnesses[role])
            return _split_send(
                fd, frame, cleanup_deadline, run_id=run_id,
                phase=f"signal_{name}", seq=1 if name == "term" else 2,
                witness=signal_witnesses[role], target_role=role,
                target_witness=child_witnesses[role])
        finally:
            close_parent(fd)

    def responses(pending: list[str], name: str,
                  deadline: float) -> dict[str, str]:
        """Read both one-shot replies together so one stalled S cannot hide the other."""
        codes = {role: "cleanup_response_unavailable" for role in pending}
        readers = {
            signal_pipes[f"s_{role.lower()}_{name}_result"][0]: role
            for role in pending
        }
        raw = {fd: bytearray() for fd in readers}
        try:
            for fd in readers:
                os.set_blocking(fd, False)
            while readers and time.monotonic() < deadline:
                try:
                    ready, _, _ = select.select(
                        list(readers), [], [],
                        min(0.003, max(0, deadline - time.monotonic())))
                except OSError:
                    break
                for fd in ready:
                    role = readers[fd]
                    try:
                        part = os.read(fd, FRAME_LIMIT + 5)
                    except BlockingIOError:
                        continue
                    except OSError:
                        part = None
                    if part:
                        raw[fd].extend(part)
                        if len(raw[fd]) <= FRAME_LIMIT + 4:
                            continue
                    elif part == b"" and len(raw[fd]) >= 4:
                        size = struct.unpack(">I", raw[fd][:4])[0]
                        if 0 < size <= FRAME_LIMIT and len(raw[fd]) == size + 4:
                            try:
                                value = decode_frame(
                                    bytes(raw[fd]),
                                    keys=set(_SPLIT_BASE | _SPLIT_EXTRA[
                                        "signal_result"]))
                                if _split_frame_valid(
                                        value, run_id=run_id,
                                        phase="signal_result",
                                        seq=1 if name == "term" else 2,
                                        witness=signal_witnesses[role],
                                        target_role=role, signal_name=name):
                                    codes[role] = value["code"]
                            except Exception:
                                pass
                    close_parent(fd)
                    del readers[fd]
        finally:
            for fd in readers:
                close_parent(fd)
        return codes

    owned = (all(role in child_witnesses and role in signal_witnesses
                 and role in signal_pids for role in roles))
    for role in roles:
        pid = child_pids[role]
        if pid is not None and pid not in statuses:
            _fake_reap_nonblocking(pid, statuses)
    if owned and any(child_pids[r] not in statuses for r in roles):
        # A completed or failed work phase starts cleanup *now*. The work
        # deadline is only an upper bound, never a reason to defer TERM.
        cleanup_started = time.monotonic()
        phase_deadline = min(cleanup_deadline,
                             cleanup_started + cleanup_deadline - work_deadline)
        pending = []
        for role in roles:
            pid = child_pids[role]
            if pid not in statuses and not _fake_reap_nonblocking(pid, statuses):
                result[f"{role.lower()}_term"] = (
                    "command_sent" if command(role, "term")
                    else "cleanup_command_unavailable")
                if result[f"{role.lower()}_term"] == "command_sent":
                    pending.append(role)
            else:
                close_parent(signal_pipes[f"s_{role.lower()}_term"][1])
        # Both commands are written before either reply is awaited: a blocked
        # D observer cannot prevent W's independently witnessed transaction.
        term_reply_deadline = min(phase_deadline,
                                  cleanup_started + max(0.04,
                                      (phase_deadline - cleanup_started) * 0.4))
        for role, code in responses(pending, "term", term_reply_deadline).items():
            result[f"{role.lower()}_term"] = code
        grace = min(phase_deadline, cleanup_started + term_grace_seconds)
        while time.monotonic() < grace:
            for role in roles:
                pid = child_pids[role]
                if pid not in statuses:
                    _fake_reap_nonblocking(pid, statuses)
            time.sleep(min(0.003, max(0, grace - time.monotonic())))
        pending = []
        for role in roles:
            pid = child_pids[role]
            if pid not in statuses and not _fake_reap_nonblocking(pid, statuses):
                result[f"{role.lower()}_kill"] = (
                    "command_sent" if command(role, "kill")
                    else "cleanup_command_unavailable")
                if result[f"{role.lower()}_kill"] == "command_sent":
                    pending.append(role)
            else:
                close_parent(signal_pipes[f"s_{role.lower()}_kill"][1])
        for role, code in responses(pending, "kill", phase_deadline).items():
            result[f"{role.lower()}_kill"] = code
    for role in roles:
        for name in ("term", "kill"):
            if f"s_{role.lower()}_{name}" in signal_pipes:
                close_parent(signal_pipes[f"s_{role.lower()}_{name}"][1])
    for role in roles:
        pid = child_pids[role]
        if pid is not None and pid not in statuses:
            _fake_wait_reap(pid, hard_deadline + 0.1, statuses)
        status = statuses.get(pid)
        result[f"{role.lower()}_reaped"] = status is not None
        if status is not None and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
            stop = "normal_exit"
        elif status is not None and os.WIFSIGNALED(status) and (
                (os.WTERMSIG(status) == signal.SIGTERM
                 and result[f"{role.lower()}_term"] == "signal_sent") or
                (os.WTERMSIG(status) == signal.SIGKILL
                 and result[f"{role.lower()}_kill"] == "signal_sent")):
            stop = ("witnessed_term" if os.WTERMSIG(status) == signal.SIGTERM
                    else "witnessed_kill")
        else:
            stop = "unproven"
        result[f"{role.lower()}_stop"] = stop
    for role in roles:
        pid = signal_pids.get(role)
        if pid is not None:
            helper_statuses: dict[int, int] = {}
            _fake_wait_reap(pid, hard_deadline + 0.1, helper_statuses)
            helper_status = helper_statuses.get(pid)
            result[f"s_{role.lower()}_reaped"] = helper_status is not None
            if f"s_{role.lower()}_normal_exit" in result:
                result[f"s_{role.lower()}_normal_exit"] = bool(
                    helper_status is not None
                    and os.WIFEXITED(helper_status)
                    and os.WEXITSTATUS(helper_status) == 0)
            if (helper_status is None or not os.WIFEXITED(helper_status)
                    or os.WEXITSTATUS(helper_status) != 0):
                if result["status"] == "fake_partial_op1_worker_received":
                    result["status"] = "fake_partial_split_unproven"
                    result["failure_code"] = "signal_helper_exit_unavailable"
                elif result["status"] == "fake_seven_process_pending_receipt":
                    result["status"] = "fake_seven_process_unproven"
                    result["failure_code"] = "signal_helper_exit_unavailable"
    # This remains a fake D/W-only slice: no real receipt, private ports,
    # shared-11434 proof, or frozen T0+90 evidence.
    result["physical_stop_unproven"] = True


def _supervise_fake_split_op1_once(*, run_dir, grant_without_worker: dict,
                                   work_seconds: float = 0.4,
                                   preparation_seconds: float = 0.2,
                                   fault: str | None = None,
                                   cleanup_observe=None,
                                   signal_initial_witness=None,
                                   receipt_initial_witness=None,
                                   term_grace_seconds: float = 0.05,
                                   cleanup_seconds: float = 0.25) -> dict:
    """Fake-only P+D+W zero→request→durable op1→received-ACK probe.

    W performs no HTTP. `worker_received_proven=False` means no valid received
    ACK proof, not proof W never received a grant. The separate fake receipt
    is not port or live cleanup proof;
    `supervise_once` deliberately stays fail-closed. Parent does only bounded
    canonical IPC and nonblocking waitpid, never journal disk operations.
    """
    if (type(grant_without_worker) is not dict
            or set(grant_without_worker) != _GRANT_FIELDS - {"worker"}
            or not _grant_valid({**grant_without_worker,
                                 "worker": {"pid": 1, "ppid": 1,
                                            "start_sec": 0, "start_usec": 0}},
                                nonce_required=False)
            or grant_without_worker["ordinal"] != 1
            or fault not in (None, "d_after_zero", "d_after_commit",
                             "w_after_request", "r_after_commit",
                             "r_after_proof")
            or (cleanup_observe is not None and not callable(cleanup_observe))
            or (signal_initial_witness is not None
                and not callable(signal_initial_witness))
            or (receipt_initial_witness is not None
                and not callable(receipt_initial_witness))
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   or not 0.05 <= value <= 5.0
                   for value in (work_seconds, preparation_seconds,
                                 term_grace_seconds, cleanup_seconds))):
        _fail("fake_split_spec_invalid")
    spec = _plain_copy(grant_without_worker, "fake_split_spec_invalid")
    run_id = spec["run_id"]
    result = {"schema": "fake_split_op1_partial_v1",
              "status": "fake_partial_split_unproven", "failure_code": "initial_unavailable",
              "zero_ack_received": False, "request_accepted": False,
              "grant_proven": False, "worker_received_proven": False,
              "durable_reserved": "unknown", "on_wire": "unknown",
              "d_reaped": False, "w_reaped": False,
              "r_reaped": False, "s_d_reaped": False,
              "s_w_reaped": False, "s_r_reaped": False,
              "d_term": "not_attempted", "d_kill": "not_attempted",
              "w_term": "not_attempted", "w_kill": "not_attempted",
              "r_term": "not_attempted", "r_kill": "not_attempted",
              "d_stop": "unproven", "w_stop": "unproven",
              "r_stop": "unproven", "receipt_durable_proven": False,
              "receipt_preflight_accepted": False,
              "receipt_failure_code": "receipt_unavailable_review_required",
              "physical_stop_unproven": True, "full_gate_pass": False}
    started = time.monotonic()
    prep_deadline = started + preparation_seconds
    work_deadline = prep_deadline + work_seconds
    cleanup_deadline = work_deadline + cleanup_seconds
    hard_deadline = cleanup_deadline + 0.10
    # Even when D/W consume their full bounded self-alarm/reap window, R
    # retains a separate fake-only receipt window. This is not T0+90 proof.
    receipt_work_deadline = hard_deadline + 0.30
    receipt_cleanup_deadline = receipt_work_deadline + 0.15
    receipt_hard_deadline = receipt_cleanup_deadline + 0.10
    pipes: dict[str, tuple[int, int]] = {}
    receipt_pipes: dict[str, tuple[int, int]] = {}
    d_pid = w_pid = r_pid = None
    parent_fds: set[int] = set()
    parent_layout_ready = False
    statuses: dict[int, int] = {}
    child_witnesses: dict[str, dict] = {}
    signal_pipes: dict[str, tuple[int, int]] = {}
    signal_pids: dict[str, int] = {}
    signal_witnesses: dict[str, dict] = {}
    signal_parent_fds: set[int] = set()
    signal_layout_ready = False
    receipt_parent_fds: set[int] = set()
    receipt_layout_ready = False
    r_witness = None
    try:
        for name in _SPLIT_EDGES:
            pipes[name] = os.pipe()
        for role in ("D", "W", "R"):
            prefix = f"s_{role.lower()}"
            for edge in ("initial", "term", "term_result", "kill",
                         "kill_result"):
                signal_pipes[f"{prefix}_{edge}"] = os.pipe()
        for name in ("r_initial", "r_preflight", "r_preflight_ack",
                     "r_write", "r_proof"):
            receipt_pipes[name] = os.pipe()
        d_pid = os.fork()
        if d_pid == 0:
            try:
                _split_close_except(signal_pipes, set())
                _split_close_except(receipt_pipes, set())
                child_code = _split_d_child(
                    pipes, run_dir=Path(run_dir), spec=spec,
                    hard_deadline=hard_deadline,
                    work_deadline=work_deadline, fault=fault)
            except BaseException:
                child_code = 125
            os._exit(child_code)
        w_pid = os.fork()
        if w_pid == 0:
            try:
                _split_close_except(signal_pipes, set())
                _split_close_except(receipt_pipes, set())
                child_code = _split_w_child(
                    pipes, spec=spec, hard_deadline=hard_deadline,
                    work_deadline=work_deadline, fault=fault)
            except BaseException:
                child_code = 125
            os._exit(child_code)
        parent_fds = {
            pipes[name][0] for name in ("d_initial", "w_initial", "d_zero",
                                      "w_request", "d_proof", "w_received")
        } | {
            pipes[name][1] for name in ("d_go", "w_go", "d_reserve",
                                      "w_delivery")
        }
        _split_close_except(pipes, parent_fds)
        parent_layout_ready = True

        def receive(name: str, phase: str, deadline: float, **kwargs):
            fd = pipes[name][0]
            try:
                return _split_receive(fd, deadline, phase=phase,
                                      run_id=run_id, **kwargs)
            finally:
                _fake_close(fd)
                parent_fds.discard(fd)

        def send(name: str, phase: str, seq: int, witness: dict,
                 **extra) -> bool:
            fd = pipes[name][1]
            try:
                frame = _split_frame(run_id, phase, seq, witness, **extra)
                validation = {"run_id": run_id, "phase": phase, "seq": seq,
                              "witness": witness}
                if phase == "reserve":
                    validation["spec"] = spec
                    validation["worker_witness"] = w_witness
                if phase == "grant_delivery":
                    validation["fields"] = request["fields"]
                return _split_send(fd, frame, work_deadline, **validation)
            finally:
                _fake_close(fd)
                parent_fds.discard(fd)

        d_initial_frame = receive("d_initial", "initial", prep_deadline,
                                  seq=0, pid=d_pid, role="D")
        w_initial_frame = receive("w_initial", "initial", prep_deadline,
                                  seq=0, pid=w_pid, role="W")
        if d_initial_frame is None or w_initial_frame is None:
            return result
        d_witness = d_initial_frame["witness"]
        w_witness = w_initial_frame["witness"]
        child_witnesses = {"D": d_witness, "W": w_witness}
        # R is process-reserved before D's first work GO. It does not create
        # the directory: exclusive ownership stays with DurableJournal.create.
        r_pid = os.fork()
        if r_pid == 0:
            try:
                child_code = _split_receipt_child(
                    receipt_pipes, inherited_split_fds=parent_fds,
                    inherited_signal_pipes=signal_pipes,
                    run_dir=Path(run_dir), run_id=run_id,
                    initial_reader=receipt_initial_witness or _fake_os_witness,
                    prep_deadline=prep_deadline,
                    preflight_deadline=work_deadline,
                    work_deadline=receipt_work_deadline,
                    hard_deadline=receipt_hard_deadline, fault=fault)
            except BaseException:
                child_code = 125
            os._exit(child_code)
        receipt_parent_fds = {
            receipt_pipes["r_initial"][0],
            receipt_pipes["r_preflight"][1],
            receipt_pipes["r_preflight_ack"][0],
            receipt_pipes["r_write"][1], receipt_pipes["r_proof"][0],
        }
        _split_close_except(receipt_pipes, receipt_parent_fds)
        receipt_layout_ready = True
        fd = receipt_pipes["r_initial"][0]
        try:
            initial = _split_receive(fd, prep_deadline, phase="initial",
                                      run_id=run_id, seq=0, pid=r_pid,
                                      role="R")
        finally:
            _fake_close(fd)
            receipt_parent_fds.discard(fd)
        if initial is None:
            result["failure_code"] = "receipt_helper_initial_unavailable"
            return result
        r_witness = initial["witness"]
        child_witnesses["R"] = r_witness
        for role, target in (("D", d_witness), ("W", w_witness),
                             ("R", r_witness)):
            pid = os.fork()
            if pid == 0:
                try:
                    child_code = _split_signal_child(
                        signal_pipes,
                        inherited_split_fds=parent_fds | receipt_parent_fds,
                        run_id=run_id,
                        target_role=role, target_witness=target,
                        initial_reader=signal_initial_witness or _fake_os_witness,
                        observer=cleanup_observe or _fake_os_witness,
                        prep_deadline=prep_deadline,
                        cleanup_deadline=(receipt_cleanup_deadline if role == "R"
                                          else cleanup_deadline),
                        hard_deadline=(receipt_hard_deadline if role == "R"
                                       else hard_deadline))
                except BaseException:
                    child_code = 125
                os._exit(child_code)
            signal_pids[role] = pid
        signal_parent_fds = {
            signal_pipes[f"s_{role.lower()}_{edge}"][0]
            for role in ("D", "W", "R")
            for edge in ("initial", "term_result", "kill_result")
        } | {
            signal_pipes[f"s_{role.lower()}_{edge}"][1]
            for role in ("D", "W", "R") for edge in ("term", "kill")
        }
        _split_close_except(signal_pipes, signal_parent_fds)
        signal_layout_ready = True
        for role in ("D", "W", "R"):
            fd = signal_pipes[f"s_{role.lower()}_initial"][0]
            try:
                initial = _split_receive(
                    fd, prep_deadline, phase="initial", run_id=run_id,
                    seq=0, pid=signal_pids[role], role=f"S_{role}")
            finally:
                _fake_close(fd)
                signal_parent_fds.discard(fd)
            if initial is None:
                result["failure_code"] = "signal_helper_initial_unavailable"
                return result
            signal_witnesses[role] = initial["witness"]
        result["failure_code"] = "zero_ack_unavailable"
        if not send("d_go", "d_go", 1, d_witness):
            return result
        zero_sha = _sha(_canonical(_split_zero_state(run_id), "ipc_invalid"))
        zero = receive("d_zero", "zero", work_deadline, seq=1,
                       witness=d_witness, journal_sha256=zero_sha)
        if zero is None:
            return result
        result["zero_ack_received"] = True
        result["durable_reserved"] = 0
        result["failure_code"] = "receipt_preflight_unavailable"
        preflight_fd = receipt_pipes["r_preflight"][1]
        try:
            preflight = _split_frame(run_id, "receipt_preflight", 1, r_witness)
            sent = _split_send(preflight_fd, preflight, work_deadline,
                               run_id=run_id, phase="receipt_preflight",
                               seq=1, witness=r_witness)
        finally:
            _fake_close(preflight_fd)
            receipt_parent_fds.discard(preflight_fd)
        if not sent:
            return result
        ack_fd = receipt_pipes["r_preflight_ack"][0]
        try:
            preflight_ack = _split_receive(
                ack_fd, work_deadline, phase="receipt_preflight_ack",
                run_id=run_id, seq=1, witness=r_witness)
        finally:
            _fake_close(ack_fd)
            receipt_parent_fds.discard(ack_fd)
        if preflight_ack is None:
            return result
        result["receipt_preflight_accepted"] = True
        result["failure_code"] = "worker_request_unavailable"
        if not send("w_go", "w_go", 1, w_witness):
            return result
        request = receive("w_request", "op1_request", work_deadline,
                          seq=1, witness=w_witness, spec=spec,
                          worker_witness=w_witness)
        if request is None:
            return result
        result["request_accepted"] = True
        result["failure_code"] = "grant_proof_unavailable"
        # A partial/lost parent command may still have reached D. Once this
        # edge is attempted, only D's durable proof can narrow reservation.
        result["durable_reserved"] = "unknown"
        if not send("d_reserve", "reserve", 2, d_witness,
                    fields=request["fields"], worker_witness=w_witness):
            return result
        proof = receive("d_proof", "grant_proof", work_deadline,
                        seq=2, witness=d_witness, fields=request["fields"])
        if proof is None:
            result["durable_reserved"] = "unknown"
            return result
        # A full frame+EOF is not enough if D failed after emitting it.
        if not _fake_wait_reap(d_pid, work_deadline, statuses):
            result["durable_reserved"] = "unknown"
            return result
        result["d_reaped"] = True
        d_status = statuses[d_pid]
        if not (os.WIFEXITED(d_status) and os.WEXITSTATUS(d_status) == 0):
            result["durable_reserved"] = "unknown"
            return result
        result["grant_proven"] = True
        result["durable_reserved"] = 1
        result["journal_sha256"] = proof["journal_sha256"]
        result["grant_sha256"] = _sha(_canonical(proof["grant"], "ipc_invalid"))
        result["failure_code"] = "worker_received_ack_unavailable"
        if not send("w_delivery", "grant_delivery", 2, w_witness,
                    grant=proof["grant"], journal_sha256=proof["journal_sha256"]):
            return result
        received = receive("w_received", "received", work_deadline,
                           seq=2, witness=w_witness, grant=proof["grant"])
        if received is None:
            return result
        if not _fake_wait_reap(w_pid, work_deadline, statuses):
            return result
        result["w_reaped"] = True
        w_status = statuses[w_pid]
        if not (os.WIFEXITED(w_status) and os.WEXITSTATUS(w_status) == 0):
            return result
        result["worker_received_proven"] = True
        result["failure_code"] = "none"
        result["status"] = "fake_partial_op1_worker_received"
        return result
    except Exception:
        result["failure_code"] = "ipc_or_spawn_unavailable"
        return result
    finally:
        _fake_close(*parent_fds)
        if not parent_layout_ready:  # a pipe/fork failed before FD layout
            for read_fd, write_fd in pipes.values():
                _fake_close(read_fd, write_fd)
        cleanup_failed = False
        try:
            _split_cleanup_children(
                result=result, statuses=statuses,
                child_pids={"D": d_pid, "W": w_pid},
                child_witnesses=child_witnesses, signal_pids=signal_pids,
                signal_witnesses=signal_witnesses, signal_pipes=signal_pipes,
                signal_parent_fds=signal_parent_fds, run_id=run_id,
                work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
                hard_deadline=hard_deadline,
                term_grace_seconds=term_grace_seconds)
        except Exception:
            # A failed cleanup cannot leak a raw OS exception or preserve a
            # positive status. Test-child alarms are containment, not proof.
            cleanup_failed = True
            result["status"] = "fake_partial_split_unproven"
            result["failure_code"] = "cleanup_unavailable"
            result["physical_stop_unproven"] = True
            result["d_stop"] = result["w_stop"] = "unproven"
        if cleanup_failed:
            for role, pid in (("D", d_pid), ("W", w_pid),
                              ("S_D", signal_pids.get("D")),
                              ("S_W", signal_pids.get("W"))):
                if pid is None or pid <= 0:
                    continue
                try:
                    if role in ("D", "W"):
                        reaped = pid in statuses or _fake_wait_reap(
                            pid, hard_deadline + 0.1, statuses)
                    else:
                        reaped = result[f"{role.lower()}_reaped"] or _fake_wait_reap(
                            pid, hard_deadline + 0.1)
                    result[f"{role.lower()}_reaped"] = bool(reaped)
                except Exception:
                    result[f"{role.lower()}_reaped"] = False
        # R was pre-witnessed before D GO and held idle through D/W cleanup.
        # Only its child performs the O_EXCL write, fsync and readback.
        try:
            if (result["receipt_preflight_accepted"]
                    and r_pid is not None and r_witness is not None
                    and "R" in signal_witnesses):
                receipt = _split_receipt_payload(result, run_id)
                frame = _split_frame(run_id, "receipt_write", 2, r_witness,
                                     receipt=receipt)
                command_fd = receipt_pipes["r_write"][1]
                try:
                    sent = _split_send(
                        command_fd, frame, receipt_work_deadline,
                        run_id=run_id, phase="receipt_write", seq=2,
                        witness=r_witness)
                finally:
                    _fake_close(command_fd)
                    receipt_parent_fds.discard(command_fd)
                if sent:
                    proof_fd = receipt_pipes["r_proof"][0]
                    try:
                        proof = _split_receive(
                            proof_fd, receipt_work_deadline,
                            phase="receipt_proof", run_id=run_id, seq=2,
                            witness=r_witness, receipt=receipt)
                    finally:
                        _fake_close(proof_fd)
                        receipt_parent_fds.discard(proof_fd)
                    if proof is not None and _fake_wait_reap(
                            r_pid, receipt_work_deadline, statuses):
                        r_status = statuses[r_pid]
                        if (os.WIFEXITED(r_status)
                                and os.WEXITSTATUS(r_status) == 0):
                            result["receipt_durable_proven"] = True
                            result["receipt_sha256"] = proof["receipt_sha256"]
                            result["receipt_failure_code"] = "none"
        except Exception:
            result["receipt_durable_proven"] = False
            result.pop("receipt_sha256", None)
            result["receipt_failure_code"] = "receipt_unavailable_review_required"
        finally:
            _fake_close(*receipt_parent_fds)
            if not receipt_layout_ready:
                for read_fd, write_fd in receipt_pipes.values():
                    _fake_close(read_fd, write_fd)
        try:
            _split_cleanup_children(
                result=result, statuses=statuses, roles=("R",),
                child_pids={"R": r_pid},
                child_witnesses=child_witnesses, signal_pids=signal_pids,
                signal_witnesses=signal_witnesses, signal_pipes=signal_pipes,
                signal_parent_fds=signal_parent_fds, run_id=run_id,
                work_deadline=receipt_work_deadline,
                cleanup_deadline=receipt_cleanup_deadline,
                hard_deadline=receipt_hard_deadline,
                term_grace_seconds=term_grace_seconds)
        except Exception:
            result["receipt_durable_proven"] = False
            result.pop("receipt_sha256", None)
            result["receipt_failure_code"] = "receipt_unavailable_review_required"
            result["r_stop"] = "unproven"
            result["physical_stop_unproven"] = True
            for role, pid in (("R", r_pid), ("S_R", signal_pids.get("R"))):
                if pid is None or pid <= 0:
                    continue
                try:
                    reaped = (pid in statuses if role == "R" else
                              result["s_r_reaped"])
                    if not reaped:
                        reaped = _fake_wait_reap(
                            pid, receipt_hard_deadline + 0.1,
                            statuses if role == "R" else None)
                    result[f"{role.lower()}_reaped"] = bool(reaped)
                except Exception:
                    result[f"{role.lower()}_reaped"] = False
        finally:
            _fake_close(*signal_parent_fds)
            if not signal_layout_ready:
                for read_fd, write_fd in signal_pipes.values():
                    _fake_close(read_fd, write_fd)
        if (not result["receipt_durable_proven"]
                and result["status"] == "fake_partial_op1_worker_received"):
            # W receipt proof remains separately true; the overall one-use
            # result cannot retain a positive status without durable receipt.
            result["status"] = "fake_partial_split_unproven"
            result["failure_code"] = "receipt_unavailable_review_required"


# The following is a second, deliberately fake-only topology.  The old op1
# protocol and public fail-closed entry above remain unchanged.
_SEVEN_SCHEMA = "fake_seven_process_ipc_v1"
_SEVEN_BASE = frozenset({"schema", "run_id", "phase", "seq", "witness"})
_SEVEN_EXTRA = {
    "initial": frozenset({"role"}),
    "d_go": frozenset({"worker_witness"}), "w_go": frozenset(),
    "zero": frozenset({"journal_sha256"}),
    "request": frozenset({"fields"}),
    "reserve": frozenset({"fields"}),
    "grant_proof": frozenset({"grant", "journal_sha256", "reserved",
                              "completion_attempt_spent"}),
    "grant_delivery": frozenset({"grant", "journal_sha256"}),
    "issue_entry": frozenset({"grant_sha256"}),
    "mark_issue": frozenset({"nonce"}),
    "issue_proof": frozenset({"journal_sha256", "worker_issued"}),
    "issue_ack": frozenset({"journal_sha256"}),
    "result_entry": frozenset({"grant_sha256", "response_sha256",
                               "response_bytes"}),
    "mark_wire": frozenset({"nonce"}),
    "wire_proof": frozenset({"journal_sha256", "on_wire_yes"}),
    "result_ack": frozenset({"journal_sha256"}),
    "d_finish": frozenset(), "w_finish": frozenset(),
    "d_final": frozenset({"journal_sha256", "reserved", "worker_issued",
                           "on_wire_yes", "completion_attempt_spent"}),
    "w_summary": frozenset({"summary"}),
    "r_preflight": frozenset(), "r_preflight_ack": frozenset(),
    "r_write": frozenset({"receipt"}),
    "r_proof": frozenset({"receipt_sha256", "receipt_bytes"}),
}
_SEVEN_ORDINAL_EDGES = (
    "w_request", "d_reserve", "d_grant", "w_grant", "w_issue",
    "d_issue", "d_issue_proof", "w_issue_ack", "w_result",
    "d_wire", "d_wire_proof", "w_result_ack",
)
_SEVEN_BASE_EDGES = (
    "d_initial", "w_initial", "d_go", "d_zero", "w_go",
    "d_finish", "d_final", "w_finish", "w_summary",
)
_SEVEN_RECEIPT_EDGES = (
    "r_initial", "r_preflight", "r_preflight_ack", "r_write", "r_proof",
)
_SEVEN_RECEIPT_FIELDS = frozenset({
    "schema", "run_id", "snapshot_phase", "status", "failure_code",
    "zero_ack_received", "receipt_preflight_accepted", "reserved",
    "granted", "worker_issued", "on_wire_yes",
    "completion_attempt_spent", "http_calls", "identity_checks",
    "journal_sha256", "summary_sha256", "d_reaped", "w_reaped",
    "d_stop", "w_stop", "physical_stop_unproven", "full_gate_pass",
    "b_upper_bound_proven", "b_send_authorized",
})
_SEVEN_SUMMARY_FIELDS = frozenset({
    "schema", "status", "request_sha256", "request_utf8_bytes",
    "rendered_prompt_sha256", "rendered_prompt_utf8_bytes",
    "identity_observation_sha256", "source_evidence",
    "runner_token_count_parse_special_true",
    "runner_token_count_parse_special_default", "provider_usage",
    "signed_delta", "http_calls", "identity_checks",
    "external_completion_attempts", "internal_runner_generations",
    "elapsed_seconds", "b_upper_bound_proven", "b_send_authorized",
})
_SEVEN_SOURCE_EVIDENCE_FIELDS = frozenset({
    "source_revision", "version", "branch", "bos_strip_applied",
    "context_total", "parallel", "effective_num_ctx", "request_num_ctx",
    "rendered_utf8_below_num_ctx", "daemon_argv_sha256",
    "runner_argv_sha256",
})
_SEVEN_FAILURE_CODES = frozenset({
    "none", "initial_unavailable", "receipt_helper_initial_unavailable",
    "signal_helper_initial_unavailable", "zero_ack_unavailable",
    "receipt_preflight_unavailable", "worker_go_unavailable",
    "worker_request_unavailable", "worker_request_invalid",
    "grant_proof_unavailable", "grant_delivery_unavailable",
    "issue_entry_unavailable", "issue_proof_unavailable",
    "issue_ack_unavailable", "fake_result_unavailable",
    "wire_proof_unavailable", "result_ack_unavailable",
    "d_final_unavailable", "w_summary_unavailable",
    "normal_exit_unavailable", "cleanup_unavailable",
    "signal_helper_exit_unavailable",
    "receipt_unavailable_review_required", "ipc_or_spawn_unavailable",
    "fake_seven_fd_reservation_unavailable",
})


def _seven_frame(run_id: str, phase: str, seq: int, witness: dict,
                 **extra) -> dict:
    return {"schema": _SEVEN_SCHEMA, "run_id": run_id, "phase": phase,
            "seq": seq, "witness": witness, **extra}


def _seven_summary_valid(value: Any) -> bool:
    if (type(value) is not dict or set(value) != _SEVEN_SUMMARY_FIELDS
            or value["schema"] != "fake_non_b_worker_v1"
            or value["status"] not in (
                "fake_non_b_parity_pass", "fake_non_b_parity_mismatch")
            or value["http_calls"] != 7 or value["identity_checks"] != 6
            or value["external_completion_attempts"] != 1
            or value["internal_runner_generations"] != "unknown"
            or value["b_upper_bound_proven"] is not False
            or value["b_send_authorized"] is not False
            or any(not _valid_sha(value[key]) for key in (
                "request_sha256", "rendered_prompt_sha256",
                "identity_observation_sha256"))):
        return False
    source = value["source_evidence"]
    if (type(source) is not dict or set(source) != _SEVEN_SOURCE_EVIDENCE_FIELDS
            or source["source_revision"] != "v0.34.4"
            or source["version"] != VERSION
            or source["branch"] != "go_rendered_chat"
            or source["bos_strip_applied"] is not False
            or source["rendered_utf8_below_num_ctx"] is not True
            or any(not _valid_sha(source[key]) for key in (
                "daemon_argv_sha256", "runner_argv_sha256"))
            or any(type(source[key]) is not int or source[key] <= 0
                   for key in ("context_total", "parallel",
                               "effective_num_ctx", "request_num_ctx"))
            or source["effective_num_ctx"] != source["request_num_ctx"]):
        return False
    usage = value["provider_usage"]
    if (type(usage) is not dict
            or set(usage) != {"prompt_tokens", "completion_tokens", "total_tokens"}
            or any(type(usage[key]) is not int or usage[key] < 0
                   for key in usage)
            or usage["total_tokens"] != (
                usage["prompt_tokens"] + usage["completion_tokens"])):
        return False
    if (any(type(value[key]) is not int or value[key] <= 0
            for key in ("request_utf8_bytes", "rendered_prompt_utf8_bytes",
                        "runner_token_count_parse_special_true",
                        "runner_token_count_parse_special_default"))
            or value["request_utf8_bytes"] != 1833
            or value["runner_token_count_parse_special_true"]
               != value["runner_token_count_parse_special_default"]
            or type(value["signed_delta"]) is not int
            or value["signed_delta"] != (
                usage["prompt_tokens"]
                - value["runner_token_count_parse_special_true"])
            or (value["status"] == "fake_non_b_parity_pass")
               != (value["signed_delta"] == 0)
            or not _finite_number(value["elapsed_seconds"])):
        return False
    return True


def _seven_receipt_valid(value: Any, run_id: str) -> bool:
    if (type(value) is not dict or set(value) != _SEVEN_RECEIPT_FIELDS
            or value["schema"] != "fake_seven_process_receipt_v1"
            or value["run_id"] != run_id
            or value["snapshot_phase"] != "after_dw_cleanup_before_r_final_reap"
            or value["status"] not in (
                "fake_seven_process_pending_receipt", "fake_seven_process_unproven")
            or value["failure_code"] not in _SEVEN_FAILURE_CODES
            or any(type(value[key]) is not bool for key in (
                "zero_ack_received", "receipt_preflight_accepted",
                "d_reaped", "w_reaped"))
            or any(value[key] is not expected for key, expected in (
                ("physical_stop_unproven", True), ("full_gate_pass", False),
                ("b_upper_bound_proven", False),
                ("b_send_authorized", False)))
            or any(value[key] not in _SPLIT_STOP_CODES
                   for key in ("d_stop", "w_stop"))
            or any(value[key] is not None and not _valid_sha(value[key])
                   for key in ("journal_sha256", "summary_sha256"))):
        return False
    for key in ("reserved", "granted", "worker_issued", "on_wire_yes",
                "completion_attempt_spent", "http_calls", "identity_checks"):
        item = value[key]
        if item != "unknown" and (type(item) is not int or not 0 <= item <= 7):
            return False
    if value["status"] == "fake_seven_process_pending_receipt":
        return (value["failure_code"] == "none"
                and all(value[key] == 7 for key in (
                    "reserved", "granted", "worker_issued", "on_wire_yes",
                    "http_calls")) and value["identity_checks"] == 6
                and value["completion_attempt_spent"] == 1
                and _valid_sha(value["journal_sha256"])
                and _valid_sha(value["summary_sha256"])
                and value["d_reaped"] and value["w_reaped"]
                and value["d_stop"] == value["w_stop"] == "normal_exit")
    return True


def _seven_frame_valid(value: Any, *, run_id: str, phase: str, seq: int,
                       witness: dict | None = None, pid: int | None = None,
                       expected: dict | None = None) -> bool:
    if (type(value) is not dict or phase not in _SEVEN_EXTRA
            or set(value) != _SEVEN_BASE | _SEVEN_EXTRA[phase]
            or value["schema"] != _SEVEN_SCHEMA or value["run_id"] != run_id
            or value["phase"] != phase or type(value["seq"]) is not int
            or value["seq"] != seq):
        return False
    got = value["witness"]
    if (type(got) is not dict
            or not _fake_witness_valid(got, got.get("pid", -1))):
        return False
    if witness is None:
        if (phase != "initial" or pid is None
                or not _fake_witness_valid(got, pid)
                or got["ppid"] != os.getpid() or got["pgid"] != pid):
            return False
    elif not _split_same(got, witness):
        return False
    if expected is not None:
        if any(key not in value or not _split_same(value[key], item)
               for key, item in expected.items()):
            return False
    if phase == "initial":
        return value["role"] in ("D", "W", "R")
    if "fields" in value and not _grant_valid(value["fields"], nonce_required=False):
        return False
    if "worker_witness" in value:
        worker_witness = value["worker_witness"]
        if (type(worker_witness) is not dict
                or not _fake_witness_valid(worker_witness,
                                           worker_witness.get("pid", -1))):
            return False
    if "grant" in value and not _grant_valid(value["grant"], nonce_required=True):
        return False
    if "nonce" in value and (type(value["nonce"]) is not str
                             or _NONCE.fullmatch(value["nonce"]) is None):
        return False
    for key in ("journal_sha256", "grant_sha256", "response_sha256",
                "receipt_sha256"):
        if key in value and not _valid_sha(value[key]):
            return False
    for key in ("reserved", "worker_issued", "on_wire_yes",
                "completion_attempt_spent", "response_bytes", "receipt_bytes"):
        if key in value and (type(value[key]) is not int or value[key] < 0
                             or value[key] > (RESPONSE_LIMIT if key == "response_bytes"
                                               else FRAME_LIMIT if key == "receipt_bytes"
                                               else 7)):
            return False
    if "summary" in value and not _seven_summary_valid(value["summary"]):
        return False
    if "receipt" in value and not _seven_receipt_valid(value["receipt"], run_id):
        return False
    return True


def _seven_send(fd: int, value: dict, deadline: float, **validation) -> bool:
    try:
        if not _seven_frame_valid(value, **validation):
            return False
        frame = encode_frame(value)
        if not _seven_frame_valid(decode_frame(
                frame, keys=set(value)), **validation):
            return False
        os.set_blocking(fd, False)
        offset = 0
        while offset < len(frame) and time.monotonic() < deadline:
            _, ready, _ = select.select([], [fd], [], min(
                0.005, max(0, deadline - time.monotonic())))
            if not ready:
                continue
            try:
                size = os.write(fd, frame[offset:])
            except BlockingIOError:
                continue
            if size <= 0:
                return False
            offset += size
        return offset == len(frame)
    except Exception:
        return False


def _seven_receive(fd: int, deadline: float, **validation) -> dict | None:
    phase = validation["phase"]
    value = _fake_read_bounded(
        fd, deadline, framed=True,
        keys=set(_SEVEN_BASE | _SEVEN_EXTRA[phase]))
    return value if _seven_frame_valid(value, **validation) else None


def _seven_edge(name: str, ordinal: int) -> str:
    return f"{name}_{ordinal}"


def _seven_child_send(pipes: dict[str, tuple[int, int]], name: str,
                      run_id: str, phase: str, seq: int, own: dict,
                      deadline: float, **extra) -> bool:
    fd = pipes[name][1]
    try:
        value = _seven_frame(run_id, phase, seq, own, **extra)
        return _seven_send(fd, value, deadline, run_id=run_id, phase=phase,
                           seq=seq, witness=own)
    finally:
        _fake_close(fd)


def _seven_child_receive(pipes: dict[str, tuple[int, int]], name: str,
                         run_id: str, phase: str, seq: int, own: dict,
                         deadline: float, expected: dict | None = None) -> dict | None:
    fd = pipes[name][0]
    try:
        return _seven_receive(fd, deadline, run_id=run_id, phase=phase,
                              seq=seq, witness=own, expected=expected)
    finally:
        _fake_close(fd)


def _seven_d_child(pipes: dict[str, tuple[int, int]], *, run_dir: Path,
                   run_id: str, hard_deadline: float,
                   work_deadline: float, fault: str | None) -> int:
    writes = {"d_initial", "d_zero", "d_final"} | {
        _seven_edge(edge, n) for n in range(1, 8)
        for edge in ("d_grant", "d_issue_proof", "d_wire_proof")}
    reads = {"d_go", "d_finish"} | {
        _seven_edge(edge, n) for n in range(1, 8)
        for edge in ("d_reserve", "d_issue", "d_wire")}
    owned = {pipes[name][1] for name in writes} | {
        pipes[name][0] for name in reads}
    _split_close_except(pipes, owned)
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        own = _fake_os_witness(os.getpid())
        if not _seven_child_send(pipes, "d_initial", run_id, "initial", 0,
                                 own, work_deadline, role="D"):
            return 125
        go = _seven_child_receive(pipes, "d_go", run_id, "d_go", 0,
                                  own, work_deadline)
        if go is None:
            return 125
        worker_witness = go["worker_witness"]
        journal = DurableJournal.create(run_dir, run_id)
        zero = journal.snapshot()
        if not _split_same(zero, _split_zero_state(run_id)):
            return 125
        zero_sha = _sha(_split_disk_readback(journal, zero))
        if not _seven_child_send(pipes, "d_zero", run_id, "zero", 0,
                                 own, work_deadline, journal_sha256=zero_sha):
            return 125
        for ordinal in range(1, 8):
            state = journal.snapshot()
            if (state["reserved"] != ordinal - 1
                    or (ordinal > 1 and state["operations"][-1]["on_wire"] != "yes")):
                return 125
            reserve = _seven_child_receive(
                pipes, _seven_edge("d_reserve", ordinal), run_id, "reserve",
                ordinal, own, work_deadline)
            if reserve is None:
                return 125
            fields = reserve["fields"]
            if (fields["run_id"] != run_id or fields["ordinal"] != ordinal
                    or not _split_same(fields["worker"],
                                       _split_worker_from_witness(worker_witness))):
                return 125
            grant = journal.reserve(fields, ack=lambda _grant: None)
            state = journal.snapshot()
            disk_sha = _sha(_split_disk_readback(journal, state))
            if (state["reserved"] != ordinal or state["granted"] != ordinal
                    or state["worker_issued"] != ordinal - 1
                    or state["operations"][-1]["on_wire"] != "unknown"
                    or state["completion_attempt_spent"] != int(ordinal == 7)):
                return 125
            if fault == f"d_after_reserve_{ordinal}":
                return 121
            if not _seven_child_send(
                    pipes, _seven_edge("d_grant", ordinal), run_id,
                    "grant_proof", ordinal, own, work_deadline,
                    grant=grant, journal_sha256=disk_sha,
                    reserved=ordinal,
                    completion_attempt_spent=int(ordinal == 7)):
                return 125
            issue = _seven_child_receive(
                pipes, _seven_edge("d_issue", ordinal), run_id,
                "mark_issue", ordinal, own, work_deadline,
                expected={"nonce": grant["nonce"]})
            if issue is None:
                return 125
            journal.mark_worker_issued(ordinal, grant["nonce"])
            state = journal.snapshot()
            disk_sha = _sha(_split_disk_readback(journal, state))
            if state["worker_issued"] != ordinal:
                return 125
            if fault == f"d_after_issue_{ordinal}":
                return 121
            if not _seven_child_send(
                    pipes, _seven_edge("d_issue_proof", ordinal), run_id,
                    "issue_proof", ordinal, own, work_deadline,
                    journal_sha256=disk_sha, worker_issued=ordinal):
                return 125
            wire = _seven_child_receive(
                pipes, _seven_edge("d_wire", ordinal), run_id,
                "mark_wire", ordinal, own, work_deadline,
                expected={"nonce": grant["nonce"]})
            if wire is None:
                return 125
            journal.mark_on_wire(ordinal, grant["nonce"])
            state = journal.snapshot()
            disk_sha = _sha(_split_disk_readback(journal, state))
            if (sum(op["on_wire"] == "yes" for op in state["operations"])
                    != ordinal):
                return 125
            if fault == f"d_after_wire_{ordinal}":
                return 121
            if not _seven_child_send(
                    pipes, _seven_edge("d_wire_proof", ordinal), run_id,
                    "wire_proof", ordinal, own, work_deadline,
                    journal_sha256=disk_sha, on_wire_yes=ordinal):
                return 125
        if _seven_child_receive(pipes, "d_finish", run_id, "d_finish", 8,
                                own, work_deadline) is None:
            return 125
        state = journal.snapshot()
        disk_sha = _sha(_split_disk_readback(journal, state))
        if (state["reserved"] != 7 or state["granted"] != 7
                or state["worker_issued"] != 7
                or state["completion_attempt_spent"] != 1
                or any(op["on_wire"] != "yes" for op in state["operations"])):
            return 125
        return (0 if _seven_child_send(
            pipes, "d_final", run_id, "d_final", 8, own, work_deadline,
            journal_sha256=disk_sha, reserved=7, worker_issued=7,
            on_wire_yes=7, completion_attempt_spent=1) else 125)
    except BaseException:
        return 125
    # Its sole caller immediately os._exit()s. Remaining owned descriptors
    # close at process exit; re-closing consumed numeric FDs could close a
    # different callback FD that reused the number.


def _seven_w_child(pipes: dict[str, tuple[int, int]], *, binding_template: dict,
                   observe_identity, fake_http, run_id: str,
                   hard_deadline: float, work_deadline: float,
                   fault: str | None) -> int:
    writes = {"w_initial", "w_summary"} | {
        _seven_edge(edge, n) for n in range(1, 8)
        for edge in ("w_request", "w_issue", "w_result")}
    reads = {"w_go", "w_finish"} | {
        _seven_edge(edge, n) for n in range(1, 8)
        for edge in ("w_grant", "w_issue_ack", "w_result_ack")}
    owned = {pipes[name][1] for name in writes} | {
        pipes[name][0] for name in reads}
    _split_close_except(pipes, owned)
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        own = _fake_os_witness(os.getpid())
        if not _seven_child_send(pipes, "w_initial", run_id, "initial", 0,
                                 own, work_deadline, role="W"):
            return 125
        if _seven_child_receive(pipes, "w_go", run_id, "w_go", 0,
                                own, work_deadline) is None:
            return 125
        binding = deepcopy(binding_template)
        binding["worker"] = _split_worker_from_witness(own)
        # worker_once's existing binding contract fixes work_stop_at=t0+80.
        # For this shortened synthetic attempt, anchor that nominal T0 to
        # the parent's *absolute* work stop instead of granting W a fresh
        # 80 real seconds. This is not a real T0 timing claim.
        binding["t0"] = work_deadline - 80.0
        binding["work_stop_at"] = work_deadline
        pending: dict[int, tuple[dict, dict]] = {}
        used: set[str] = set()
        callback_count = 0

        def authorize_call(spec: dict) -> dict:
            ordinal = spec["ordinal"]
            if (ordinal != len(pending) + 1 or not _grant_valid(
                    spec, nonce_required=False)
                    or spec["run_id"] != run_id
                    or not _split_same(spec["worker"], binding["worker"])):
                _fail("fake_seven_request_invalid")
            if not _seven_child_send(
                    pipes, _seven_edge("w_request", ordinal), run_id,
                    "request", ordinal, own, work_deadline, fields=spec):
                _fail("fake_seven_request_unavailable")
            delivery = _seven_child_receive(
                pipes, _seven_edge("w_grant", ordinal), run_id,
                "grant_delivery", ordinal, own, work_deadline)
            if (delivery is None or not _split_grant_valid(
                    delivery["grant"], spec)):
                _fail("fake_seven_grant_unavailable")
            grant = delivery["grant"]
            if grant["nonce"] in used:
                _fail("fake_seven_nonce_replay")
            pending[ordinal] = (deepcopy(spec), deepcopy(grant))
            return grant

        def http_call(method, url, payload, remaining, grant):
            nonlocal callback_count
            ordinal = callback_count + 1
            pair = pending.get(ordinal)
            if pair is None:
                _fail("fake_seven_no_pending")
            spec, original = pair
            payload_raw = None if payload is None else _canonical(
                payload, "request_invalid")
            expected_url = (f"http://127.0.0.1:{spec['port']}"
                            f"{spec['path']}")
            # This is the W-local, one-use *fake* transport entrance.  No
            # parent or D receives a body, completion or rendered prompt.
            if (not _split_same(grant, original)
                    or not _split_grant_valid(grant, spec)
                    or url != expected_url or method != spec["method"]
                    or (None if payload_raw is None else _sha(payload_raw))
                       != spec["payload_sha256"]
                    or not _split_same(grant["worker"], binding["worker"])
                    or grant["nonce"] in used
                    or not _finite_number(remaining) or remaining <= 0
                    or time.monotonic() >= grant["expires_at"]):
                _fail("fake_seven_transport_gate_invalid")
            used.add(grant["nonce"])
            grant_sha = _sha(_canonical(grant, "grant_invalid"))
            if not _seven_child_send(
                    pipes, _seven_edge("w_issue", ordinal), run_id,
                    "issue_entry", ordinal, own, work_deadline,
                    grant_sha256=grant_sha):
                _fail("fake_seven_issue_unavailable")
            issue_ack = _seven_child_receive(
                pipes, _seven_edge("w_issue_ack", ordinal), run_id,
                "issue_ack", ordinal, own, work_deadline)
            if issue_ack is None:
                _fail("fake_seven_issue_ack_unavailable")
            if fault == f"w_after_issue_{ordinal}":
                return None  # worker_once rejects it; no fake send occurred.
            value = fake_http(method, url, payload, remaining, deepcopy(grant))
            callback_count += 1
            if (type(value) is not dict or set(value) != _HTTP_FIELDS
                    or value["requested_url"] != expected_url
                    or value["effective_url"] != expected_url
                    or value["proxy_used"] is not False
                    or value["redirected"] is not False
                    or type(value["status"]) is not int
                    or value["status"] != 200 or type(value["body"]) is not bytes
                    or len(value["body"]) > RESPONSE_LIMIT):
                _fail("fake_seven_transport_failed")
            if not _seven_child_send(
                    pipes, _seven_edge("w_result", ordinal), run_id,
                    "result_entry", ordinal, own, work_deadline,
                    grant_sha256=grant_sha,
                    response_sha256=_sha(value["body"]),
                    response_bytes=len(value["body"])):
                _fail("fake_seven_result_unavailable")
            if _seven_child_receive(
                    pipes, _seven_edge("w_result_ack", ordinal), run_id,
                    "result_ack", ordinal, own, work_deadline) is None:
                _fail("fake_seven_result_ack_unavailable")
            return value

        summary = worker_once(
            binding=binding, clock=time.monotonic,
            observe_identity=observe_identity,
            authorize_call=authorize_call, http_call=http_call)
        if (not _seven_summary_valid(summary) or callback_count != 7
                or len(used) != 7):
            return 125
        if _seven_child_receive(pipes, "w_finish", run_id, "w_finish", 8,
                                own, work_deadline) is None:
            return 125
        return (0 if _seven_child_send(
            pipes, "w_summary", run_id, "w_summary", 8, own,
            work_deadline, summary=summary) else 125)
    except BaseException:
        return 125
    # The fork wrapper immediately os._exit()s; do not double-close used
    # one-shot numeric FDs after injected callback code may have reused them.


def _seven_write_receipt(run_dir: Path, receipt: dict,
                         run_id: str) -> tuple[str, int]:
    """R-only 0600 O_EXCL fake receipt, never a live wire/stop receipt."""
    if not _seven_receipt_valid(receipt, run_id):
        _fail("fake_seven_receipt_invalid")
    directory = Path(run_dir)
    metadata = os.lstat(directory)
    if (not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700):
        _fail("fake_seven_receipt_directory_invalid")
    raw = _canonical(receipt, "fake_seven_receipt_invalid")
    if len(raw) > FRAME_LIMIT:
        _fail("fake_seven_receipt_oversize")
    path = directory / RECEIPT_NAME
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(fd, 0o600)
        if os.write(fd, raw) != len(raw):
            _fail("fake_seven_receipt_short_write")
        os.fsync(fd)
    finally:
        _fake_close(fd)
    DurableJournal._sync_directory(directory)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(fd)
        readback = os.read(fd, FRAME_LIMIT + 1)
    finally:
        _fake_close(fd)
    if (not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or readback != raw):
        _fail("fake_seven_receipt_readback_invalid")
    return _sha(raw), len(raw)


def _seven_r_child(pipes: dict[str, tuple[int, int]], *,
                   inherited_core_fds: set[int],
                   inherited_signal_pipes: dict[str, tuple[int, int]],
                   run_dir: Path, run_id: str,
                   hard_deadline: float, prep_deadline: float,
                   preflight_deadline: float, receipt_deadline: float,
                   initial_reader=None) -> int:
    owned = {pipes[name][1] for name in (
        "r_initial", "r_preflight_ack", "r_proof")} | {
        pipes[name][0] for name in ("r_preflight", "r_write")}
    _fake_close(*inherited_core_fds)
    _split_close_except(inherited_signal_pipes, set())
    _split_close_except(pipes, owned)
    try:
        os.setsid()
        _fake_child_lifetime(hard_deadline)
        actual = _fake_os_witness(os.getpid())
        own = (initial_reader or _fake_os_witness)(os.getpid())
        if not _split_same(actual, own):
            return 126
        if not _seven_child_send(pipes, "r_initial", run_id, "initial", 0,
                                 own, prep_deadline, role="R"):
            return 125
        if _seven_child_receive(pipes, "r_preflight", run_id,
                                "r_preflight", 1, own,
                                preflight_deadline) is None:
            return 0
        if not _split_receipt_preflight(run_dir, run_id):
            return 125
        if not _seven_child_send(pipes, "r_preflight_ack", run_id,
                                 "r_preflight_ack", 1, own,
                                 preflight_deadline):
            return 125
        command = _seven_child_receive(pipes, "r_write", run_id, "r_write",
                                       2, own, receipt_deadline)
        if command is None:
            return 0
        receipt = command["receipt"]
        sha, length = _seven_write_receipt(run_dir, receipt, run_id)
        return (0 if _seven_child_send(pipes, "r_proof", run_id, "r_proof",
                                       2, own, receipt_deadline,
                                       receipt_sha256=sha,
                                       receipt_bytes=length) else 125)
    except BaseException:
        return 125
    # The fork wrapper immediately os._exit()s and owns any unused ends.


def _seven_receipt_payload(result: dict, run_id: str) -> dict:
    status = ("fake_seven_process_pending_receipt"
              if result["status"] == "fake_seven_process_pending_receipt"
              else "fake_seven_process_unproven")
    return {
        "schema": "fake_seven_process_receipt_v1", "run_id": run_id,
        "snapshot_phase": "after_dw_cleanup_before_r_final_reap",
        "status": status, "failure_code": result["failure_code"],
        "zero_ack_received": result["zero_ack_received"],
        "receipt_preflight_accepted": result["receipt_preflight_accepted"],
        **{key: result[key] for key in (
            "reserved", "granted", "worker_issued", "on_wire_yes",
            "completion_attempt_spent", "http_calls", "identity_checks",
            "d_reaped", "w_reaped", "d_stop", "w_stop")},
        "journal_sha256": result.get("journal_sha256"),
        "summary_sha256": result.get("summary_sha256"),
        "physical_stop_unproven": True, "full_gate_pass": False,
        "b_upper_bound_proven": False, "b_send_authorized": False,
    }


def _seven_pipe_layout() -> tuple[dict[str, tuple[int, int]],
                                  dict[str, tuple[int, int]],
                                  dict[str, tuple[int, int]]]:
    """Reserve every fake IPC edge before any D/W/R/S child is work-GOed."""
    core: dict[str, tuple[int, int]] = {}
    receipt: dict[str, tuple[int, int]] = {}
    signals: dict[str, tuple[int, int]] = {}
    try:
        for name in _SEVEN_BASE_EDGES:
            core[name] = os.pipe()
        for ordinal in range(1, 8):
            for edge in _SEVEN_ORDINAL_EDGES:
                core[_seven_edge(edge, ordinal)] = os.pipe()
        for name in _SEVEN_RECEIPT_EDGES:
            receipt[name] = os.pipe()
        for role in ("D", "W", "R"):
            prefix = f"s_{role.lower()}"
            for edge in ("initial", "term", "term_result", "kill",
                         "kill_result"):
                signals[f"{prefix}_{edge}"] = os.pipe()
        all_fds = [fd for mapping in (core, receipt, signals)
                   for pair in mapping.values() for fd in pair]
        soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
        if (len(all_fds) != 226 or len(set(all_fds)) != len(all_fds)
                or max(all_fds) >= soft_limit):
            _fail("fake_seven_fd_reservation_unavailable")
        return core, receipt, signals
    except BaseException:
        for mapping in (core, receipt, signals):
            for pair in mapping.values():
                _fake_close(*pair)
        raise


def _supervise_fake_seven_once(*, run_dir, binding_template: dict,
                               observe_identity, fake_http,
                               work_seconds: float = 2.0,
                               preparation_seconds: float = 0.5,
                               cleanup_seconds: float = 0.5,
                               term_grace_seconds: float = 0.05,
                               fault: str | None = None,
                               cleanup_observe=None,
                               signal_initial_witness=None,
                               receipt_initial_witness=None) -> dict:
    """Synthetic P+D/W/R seven-operation proof; never a live provider path.

    All seven W responses are injected locally. P handles bounded canonical
    frames and waitpid only; D exclusively owns the journal, R the receipt.
    The public ``supervise_once`` remains fail-closed.
    """
    if (type(binding_template) is not dict
            or not callable(observe_identity) or not callable(fake_http)
            or (cleanup_observe is not None and not callable(cleanup_observe))
            or (signal_initial_witness is not None
                and not callable(signal_initial_witness))
            or (receipt_initial_witness is not None
                and not callable(receipt_initial_witness))
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   or not 0.05 <= value <= 5.0 for value in (
                       work_seconds, preparation_seconds, cleanup_seconds,
                       term_grace_seconds))
            or (fault is not None and re.fullmatch(
                r"(?:d_after_(?:reserve|issue|wire)|w_after_issue)_[1-7]",
                fault) is None)):
        _fail("fake_seven_configuration_invalid")
    bound, _ = _validate_binding(binding_template)
    run_id = bound["run_id"]
    result = {
        "schema": "fake_seven_process_result_v1",
        "status": "fake_seven_process_unproven",
        "failure_code": "initial_unavailable",
        "zero_ack_received": False,
        "receipt_preflight_accepted": False,
        "receipt_durable_proven": False,
        "reserved": "unknown", "granted": "unknown",
        "worker_issued": "unknown", "on_wire_yes": "unknown",
        "completion_attempt_spent": "unknown",
        "http_calls": "unknown", "identity_checks": "unknown",
        "fd_endpoints_reserved": 0,
        "d_reaped": False, "w_reaped": False, "r_reaped": False,
        "s_d_reaped": False, "s_w_reaped": False, "s_r_reaped": False,
        "s_d_normal_exit": False, "s_w_normal_exit": False,
        "s_r_normal_exit": False,
        "d_term": "not_attempted", "d_kill": "not_attempted",
        "w_term": "not_attempted", "w_kill": "not_attempted",
        "r_term": "not_attempted", "r_kill": "not_attempted",
        "d_stop": "unproven", "w_stop": "unproven", "r_stop": "unproven",
        "physical_stop_unproven": True, "full_gate_pass": False,
        "b_upper_bound_proven": False, "b_send_authorized": False,
    }
    started = time.monotonic()
    prep_deadline = started + preparation_seconds
    work_deadline = prep_deadline + work_seconds
    cleanup_deadline = work_deadline + cleanup_seconds
    hard_deadline = cleanup_deadline + 0.10
    receipt_deadline = hard_deadline + 0.45
    receipt_cleanup_deadline = receipt_deadline + 0.15
    receipt_hard_deadline = receipt_cleanup_deadline + 0.10
    core: dict[str, tuple[int, int]] = {}
    receipt_pipes: dict[str, tuple[int, int]] = {}
    signal_pipes: dict[str, tuple[int, int]] = {}
    core_parent_fds: set[int] = set()
    receipt_parent_fds: set[int] = set()
    signal_parent_fds: set[int] = set()
    core_layout_ready = False
    receipt_layout_ready = False
    signal_layout_ready = False
    child_pids: dict[str, int | None] = {"D": None, "W": None, "R": None}
    child_witnesses: dict[str, dict] = {}
    signal_pids: dict[str, int] = {}
    signal_witnesses: dict[str, dict] = {}
    statuses: dict[int, int] = {}

    def require(value, code: str) -> None:
        if not value:
            _fail(code)

    def parent_receive(mapping, owned: set[int], name: str,
                       phase: str, seq: int, witness: dict | None,
                       deadline: float, *, pid: int | None = None,
                       expected: dict | None = None):
        fd = mapping[name][0]
        try:
            return _seven_receive(fd, deadline, run_id=run_id,
                                  phase=phase, seq=seq, witness=witness,
                                  pid=pid, expected=expected)
        finally:
            _fake_close(fd)
            owned.discard(fd)

    def parent_send(mapping, owned: set[int], name: str, phase: str,
                    seq: int, witness: dict, deadline: float,
                    **extra) -> bool:
        fd = mapping[name][1]
        try:
            frame = _seven_frame(run_id, phase, seq, witness, **extra)
            return _seven_send(fd, frame, deadline, run_id=run_id,
                               phase=phase, seq=seq, witness=witness)
        finally:
            _fake_close(fd)
            owned.discard(fd)

    try:
        core, receipt_pipes, signal_pipes = _seven_pipe_layout()
        result["fd_endpoints_reserved"] = 226
        d_pid = os.fork()
        if d_pid == 0:
            try:
                _split_close_except(receipt_pipes, set())
                _split_close_except(signal_pipes, set())
                child_code = _seven_d_child(
                    core, run_dir=Path(run_dir), run_id=run_id,
                    hard_deadline=hard_deadline,
                    work_deadline=work_deadline, fault=fault)
            except BaseException:
                child_code = 125
            os._exit(child_code)
        child_pids["D"] = d_pid
        w_pid = os.fork()
        if w_pid == 0:
            try:
                _split_close_except(receipt_pipes, set())
                _split_close_except(signal_pipes, set())
                child_code = _seven_w_child(
                    core, binding_template=bound,
                    observe_identity=observe_identity, fake_http=fake_http,
                    run_id=run_id, hard_deadline=hard_deadline,
                    work_deadline=work_deadline, fault=fault)
            except BaseException:
                child_code = 125
            os._exit(child_code)
        child_pids["W"] = w_pid
        core_reads = {"d_initial", "w_initial", "d_zero", "d_final",
                      "w_summary"} | {
            _seven_edge(edge, n) for n in range(1, 8)
            for edge in ("w_request", "d_grant", "w_issue",
                         "d_issue_proof", "w_result", "d_wire_proof")}
        core_parent_fds = {core[name][0] for name in core_reads} | {
            core[name][1] for name in core if name not in core_reads}
        _split_close_except(core, core_parent_fds)
        core_layout_ready = True

        d_initial = parent_receive(core, core_parent_fds, "d_initial",
                                   "initial", 0, None, prep_deadline,
                                   pid=d_pid, expected={"role": "D"})
        w_initial = parent_receive(core, core_parent_fds, "w_initial",
                                   "initial", 0, None, prep_deadline,
                                   pid=w_pid, expected={"role": "W"})
        require(d_initial is not None and w_initial is not None,
                "initial_unavailable")
        d_witness = d_initial["witness"]
        w_witness = w_initial["witness"]
        child_witnesses.update({"D": d_witness, "W": w_witness})

        # R and all three exact-PID signal helpers are initially witnessed
        # before either D or W receives work GO.
        r_pid = os.fork()
        if r_pid == 0:
            try:
                child_code = _seven_r_child(
                    receipt_pipes, inherited_core_fds=core_parent_fds,
                    inherited_signal_pipes=signal_pipes,
                    run_dir=Path(run_dir), run_id=run_id,
                    hard_deadline=receipt_hard_deadline,
                    prep_deadline=prep_deadline,
                    preflight_deadline=work_deadline,
                    receipt_deadline=receipt_deadline,
                    initial_reader=receipt_initial_witness)
            except BaseException:
                child_code = 125
            os._exit(child_code)
        child_pids["R"] = r_pid
        receipt_reads = {"r_initial", "r_preflight_ack", "r_proof"}
        receipt_parent_fds = {receipt_pipes[name][0] for name in receipt_reads} | {
            receipt_pipes[name][1] for name in receipt_pipes
            if name not in receipt_reads}
        _split_close_except(receipt_pipes, receipt_parent_fds)
        receipt_layout_ready = True
        r_initial = parent_receive(receipt_pipes, receipt_parent_fds,
                                   "r_initial", "initial", 0, None,
                                   prep_deadline, pid=r_pid,
                                   expected={"role": "R"})
        require(r_initial is not None, "receipt_helper_initial_unavailable")
        r_witness = r_initial["witness"]
        child_witnesses["R"] = r_witness
        for role, target in (("D", d_witness), ("W", w_witness),
                             ("R", r_witness)):
            pid = os.fork()
            if pid == 0:
                try:
                    child_code = _split_signal_child(
                        signal_pipes,
                        inherited_split_fds=core_parent_fds
                        | receipt_parent_fds,
                        run_id=run_id, target_role=role,
                        target_witness=target,
                        initial_reader=signal_initial_witness
                        or _fake_os_witness,
                        observer=cleanup_observe or _fake_os_witness,
                        prep_deadline=prep_deadline,
                        cleanup_deadline=(receipt_cleanup_deadline
                                          if role == "R" else cleanup_deadline),
                        hard_deadline=(receipt_hard_deadline
                                       if role == "R" else hard_deadline))
                except BaseException:
                    child_code = 125
                os._exit(child_code)
            signal_pids[role] = pid
        signal_parent_fds = {
            signal_pipes[f"s_{role.lower()}_{edge}"][0]
            for role in ("D", "W", "R")
            for edge in ("initial", "term_result", "kill_result")
        } | {
            signal_pipes[f"s_{role.lower()}_{edge}"][1]
            for role in ("D", "W", "R")
            for edge in ("term", "kill")
        }
        _split_close_except(signal_pipes, signal_parent_fds)
        signal_layout_ready = True
        for role in ("D", "W", "R"):
            fd = signal_pipes[f"s_{role.lower()}_initial"][0]
            try:
                initial = _split_receive(
                    fd, prep_deadline, phase="initial", run_id=run_id,
                    seq=0, pid=signal_pids[role], role=f"S_{role}")
            finally:
                _fake_close(fd)
                signal_parent_fds.discard(fd)
            require(initial is not None, "signal_helper_initial_unavailable")
            signal_witnesses[role] = initial["witness"]

        require(parent_send(core, core_parent_fds, "d_go", "d_go", 0,
                            d_witness, work_deadline,
                            worker_witness=w_witness), "zero_ack_unavailable")
        zero_sha = _sha(_canonical(_split_zero_state(run_id), "ipc_invalid"))
        zero = parent_receive(core, core_parent_fds, "d_zero", "zero", 0,
                              d_witness, work_deadline,
                              expected={"journal_sha256": zero_sha})
        require(zero is not None, "zero_ack_unavailable")
        result.update({"zero_ack_received": True, "reserved": 0,
                       "granted": 0, "worker_issued": 0,
                       "on_wire_yes": 0, "completion_attempt_spent": 0,
                       "journal_sha256": zero_sha})
        require(parent_send(receipt_pipes, receipt_parent_fds,
                            "r_preflight", "r_preflight", 1,
                            r_witness, work_deadline),
                "receipt_preflight_unavailable")
        preflight = parent_receive(receipt_pipes, receipt_parent_fds,
                                   "r_preflight_ack", "r_preflight_ack",
                                   1, r_witness, work_deadline)
        require(preflight is not None, "receipt_preflight_unavailable")
        result["receipt_preflight_accepted"] = True
        require(parent_send(core, core_parent_fds, "w_go", "w_go", 0,
                            w_witness, work_deadline),
                "worker_go_unavailable")

        for ordinal in range(1, 8):
            request = parent_receive(core, core_parent_fds,
                                     _seven_edge("w_request", ordinal),
                                     "request", ordinal, w_witness,
                                     work_deadline)
            require(request is not None, "worker_request_unavailable")
            fields = request["fields"]
            require(fields["ordinal"] == ordinal
                    and fields["run_id"] == run_id
                    and _split_same(fields["worker"],
                                    _split_worker_from_witness(w_witness)),
                    "worker_request_invalid")
            # D itself also rejects moving on while the previous operation's
            # on_wire state is unknown. P cannot mint a grant independently.
            result["reserved"] = result["granted"] = "unknown"
            if ordinal == 7:
                result["completion_attempt_spent"] = "unknown"
            require(parent_send(core, core_parent_fds,
                                _seven_edge("d_reserve", ordinal),
                                "reserve", ordinal, d_witness,
                                work_deadline, fields=fields),
                    "grant_proof_unavailable")
            proof = parent_receive(core, core_parent_fds,
                                   _seven_edge("d_grant", ordinal),
                                   "grant_proof", ordinal, d_witness,
                                   work_deadline,
                                   expected={
                                       "reserved": ordinal,
                                       "completion_attempt_spent":
                                       int(ordinal == 7)})
            require(proof is not None and _split_grant_valid(
                        proof["grant"], fields),
                    "grant_proof_unavailable")
            grant = proof["grant"]
            grant_sha = _sha(_canonical(grant, "grant_invalid"))
            result.update({"reserved": ordinal, "granted": ordinal,
                           "completion_attempt_spent": int(ordinal == 7),
                           "journal_sha256": proof["journal_sha256"]})
            require(parent_send(core, core_parent_fds,
                                _seven_edge("w_grant", ordinal),
                                "grant_delivery", ordinal, w_witness,
                                work_deadline, grant=grant,
                                journal_sha256=proof["journal_sha256"]),
                    "grant_delivery_unavailable")
            issue = parent_receive(core, core_parent_fds,
                                   _seven_edge("w_issue", ordinal),
                                   "issue_entry", ordinal, w_witness,
                                   work_deadline,
                                   expected={"grant_sha256": grant_sha})
            require(issue is not None, "issue_entry_unavailable")
            result["worker_issued"] = "unknown"
            require(parent_send(core, core_parent_fds,
                                _seven_edge("d_issue", ordinal),
                                "mark_issue", ordinal, d_witness,
                                work_deadline, nonce=grant["nonce"]),
                    "issue_proof_unavailable")
            issue_proof = parent_receive(core, core_parent_fds,
                                         _seven_edge("d_issue_proof", ordinal),
                                         "issue_proof", ordinal, d_witness,
                                         work_deadline,
                                         expected={"worker_issued": ordinal})
            require(issue_proof is not None, "issue_proof_unavailable")
            result.update({"worker_issued": ordinal,
                           "journal_sha256": issue_proof["journal_sha256"]})
            require(parent_send(core, core_parent_fds,
                                _seven_edge("w_issue_ack", ordinal),
                                "issue_ack", ordinal, w_witness,
                                work_deadline,
                                journal_sha256=issue_proof["journal_sha256"]),
                    "issue_ack_unavailable")
            fake_result = parent_receive(
                core, core_parent_fds, _seven_edge("w_result", ordinal),
                "result_entry", ordinal, w_witness, work_deadline,
                expected={"grant_sha256": grant_sha})
            require(fake_result is not None, "fake_result_unavailable")
            result["on_wire_yes"] = "unknown"
            require(parent_send(core, core_parent_fds,
                                _seven_edge("d_wire", ordinal),
                                "mark_wire", ordinal, d_witness,
                                work_deadline, nonce=grant["nonce"]),
                    "wire_proof_unavailable")
            wire_proof = parent_receive(core, core_parent_fds,
                                        _seven_edge("d_wire_proof", ordinal),
                                        "wire_proof", ordinal, d_witness,
                                        work_deadline,
                                        expected={"on_wire_yes": ordinal})
            require(wire_proof is not None, "wire_proof_unavailable")
            result.update({"on_wire_yes": ordinal,
                           "journal_sha256": wire_proof["journal_sha256"]})
            require(parent_send(core, core_parent_fds,
                                _seven_edge("w_result_ack", ordinal),
                                "result_ack", ordinal, w_witness,
                                work_deadline,
                                journal_sha256=wire_proof["journal_sha256"]),
                    "result_ack_unavailable")

        require(parent_send(core, core_parent_fds, "d_finish", "d_finish",
                            8, d_witness, work_deadline),
                "d_final_unavailable")
        require(parent_send(core, core_parent_fds, "w_finish", "w_finish",
                            8, w_witness, work_deadline),
                "w_summary_unavailable")
        final = parent_receive(core, core_parent_fds, "d_final", "d_final",
                               8, d_witness, work_deadline,
                               expected={
                                   "journal_sha256": result["journal_sha256"],
                                   "reserved": 7, "worker_issued": 7,
                                   "on_wire_yes": 7,
                                   "completion_attempt_spent": 1})
        require(final is not None, "d_final_unavailable")
        summary_frame = parent_receive(core, core_parent_fds, "w_summary",
                                       "w_summary", 8, w_witness,
                                       work_deadline)
        require(summary_frame is not None, "w_summary_unavailable")
        summary = summary_frame["summary"]
        require(_fake_wait_reap(d_pid, work_deadline, statuses)
                and _fake_wait_reap(w_pid, work_deadline, statuses)
                and all(os.WIFEXITED(statuses[pid])
                        and os.WEXITSTATUS(statuses[pid]) == 0
                        for pid in (d_pid, w_pid)), "normal_exit_unavailable")
        result.update({"d_reaped": True, "w_reaped": True,
                       "d_stop": "normal_exit", "w_stop": "normal_exit",
                       "http_calls": summary["http_calls"],
                       "identity_checks": summary["identity_checks"],
                       "worker_status": summary["status"],
                       "signed_delta": summary["signed_delta"],
                       "summary_sha256": _sha(_canonical(
                           summary, "fake_seven_summary_invalid")),
                       "status": "fake_seven_process_pending_receipt",
                       "failure_code": "none"})
    except LiveOperatorError as exc:
        # An injected helper may raise this same exception type with raw
        # contents. Never let its message become a public result/receipt.
        code = str(exc)
        result["failure_code"] = (code if code in _SEVEN_FAILURE_CODES
                                  else "ipc_or_spawn_unavailable")
    except Exception:
        result["failure_code"] = "ipc_or_spawn_unavailable"
    finally:
        _fake_close(*core_parent_fds)
        if not core_layout_ready:
            # Before parent ownership is established all allocated ends are
            # still owned here; afterward only core_parent_fds is authoritative.
            for pair in core.values():
                _fake_close(*pair)
        try:
            _split_cleanup_children(
                result=result, statuses=statuses, roles=("D", "W"),
                child_pids={key: child_pids[key] for key in ("D", "W")},
                child_witnesses=child_witnesses,
                signal_pids=signal_pids,
                signal_witnesses=signal_witnesses,
                signal_pipes=signal_pipes,
                signal_parent_fds=signal_parent_fds,
                run_id=run_id, work_deadline=work_deadline,
                cleanup_deadline=cleanup_deadline,
                hard_deadline=hard_deadline,
                term_grace_seconds=term_grace_seconds)
        except Exception:
            result["status"] = "fake_seven_process_unproven"
            result["failure_code"] = "cleanup_unavailable"
            result["d_stop"] = result["w_stop"] = "unproven"
        if (result["status"] == "fake_seven_process_pending_receipt"
                and not all(result[key] for key in (
                    "d_reaped", "w_reaped", "s_d_normal_exit",
                    "s_w_normal_exit"))):
            result["status"] = "fake_seven_process_unproven"
            result["failure_code"] = "cleanup_unavailable"
        if result["status"] == "fake_seven_process_pending_receipt":
            if result["d_stop"] != "normal_exit" or result["w_stop"] != "normal_exit":
                result["status"] = "fake_seven_process_unproven"
                result["failure_code"] = "cleanup_unavailable"
        try:
            if (result["receipt_preflight_accepted"]
                    and child_pids["R"] is not None
                    and "R" in child_witnesses
                    and "R" in signal_witnesses):
                r_witness = child_witnesses["R"]
                receipt = _seven_receipt_payload(result, run_id)
                if not _seven_receipt_valid(receipt, run_id):
                    _fail("fake_seven_receipt_invalid")
                sent = parent_send(receipt_pipes, receipt_parent_fds,
                                   "r_write", "r_write", 2, r_witness,
                                   receipt_deadline, receipt=receipt)
                if sent:
                    proof = parent_receive(
                        receipt_pipes, receipt_parent_fds, "r_proof",
                        "r_proof", 2, r_witness, receipt_deadline,
                        expected={
                            "receipt_sha256": _sha(_canonical(
                                receipt, "fake_seven_receipt_invalid")),
                            "receipt_bytes": len(_canonical(
                                receipt, "fake_seven_receipt_invalid"))})
                    if (proof is not None and _fake_wait_reap(
                            child_pids["R"], receipt_deadline, statuses)):
                        status = statuses[child_pids["R"]]
                        if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
                            result["receipt_durable_proven"] = True
                            result["receipt_sha256"] = proof["receipt_sha256"]
        except Exception:
            result["receipt_durable_proven"] = False
            result.pop("receipt_sha256", None)
        finally:
            _fake_close(*receipt_parent_fds)
            if not receipt_layout_ready:
                for pair in receipt_pipes.values():
                    _fake_close(*pair)
        try:
            _split_cleanup_children(
                result=result, statuses=statuses, roles=("R",),
                child_pids={"R": child_pids["R"]},
                child_witnesses=child_witnesses,
                signal_pids=signal_pids,
                signal_witnesses=signal_witnesses,
                signal_pipes=signal_pipes,
                signal_parent_fds=signal_parent_fds,
                run_id=run_id, work_deadline=receipt_deadline,
                cleanup_deadline=receipt_cleanup_deadline,
                hard_deadline=receipt_hard_deadline,
                term_grace_seconds=term_grace_seconds)
        except Exception:
            result["receipt_durable_proven"] = False
            result["r_stop"] = "unproven"
        finally:
            _fake_close(*signal_parent_fds)
            if not signal_layout_ready:
                for pair in signal_pipes.values():
                    _fake_close(*pair)
        if result["status"] == "fake_seven_process_pending_receipt":
            if (result["receipt_durable_proven"]
                    and result["r_stop"] == "normal_exit"
                    and result["s_r_normal_exit"]):
                result["status"] = (
                    "fake_seven_process_pass"
                    if result["worker_status"] == "fake_non_b_parity_pass"
                    else "fake_seven_process_mismatch")
            else:
                result["status"] = "fake_seven_process_unproven"
                result["failure_code"] = "receipt_unavailable_review_required"
    return result
