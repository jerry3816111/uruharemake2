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
import secrets
import select
import signal
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
        try:
            os.close(fd)
        except OSError:
            pass


def _fake_read_bounded(fd: int, deadline: float, *, framed: bool) -> Any:
    """Parent-side nonblocking read; no effect callback runs on this path."""
    raw = bytearray()
    limit = FRAME_LIMIT + 4 if framed else 1
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
            return None
        raw.extend(part)
        if not framed and raw:
            return bytes(raw)
        if len(raw) >= 4:
            size = struct.unpack(">I", raw[:4])[0]
            if size == 0 or size > FRAME_LIMIT:
                return None
            if len(raw) == size + 4:
                try:
                    return decode_frame(bytes(raw), keys={"witness"})
                except LiveOperatorError:
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


def _fake_wait_reap(pid: int, deadline: float,
                    statuses: dict[int, int] | None = None) -> bool:
    while time.monotonic() < deadline:
        if _fake_reap_nonblocking(pid, statuses):
            return True
        time.sleep(min(0.003, max(0, deadline - time.monotonic())))
    return _fake_reap_nonblocking(pid, statuses)


def _supervise_fake_callback_once(*, work, observe=None, initial_witness=None,
                                  signal_initial_witness=None,
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
    if (not callable(work) or (observe is not None and not callable(observe))
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
    worker_pid = os.fork()
    if worker_pid == 0:
        _fake_close(wr, cw, dr)
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
            work()
            os.write(dw, b"D")
            os._exit(0)
        except BaseException:
            os._exit(125)
    _fake_close(ww, cr, dw)
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
            _fake_close(sr, sc, rr, wr, cw, dr)
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
        work_done = _fake_read_bounded(dr, t0 + work_seconds, framed=False)
        worker_reaped = _fake_reap_nonblocking(worker_pid, exit_statuses)
        if work_done == b"D" and not worker_reaped:
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
        if work_done == b"D" and worker_reaped and completed_normally:
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
        return result
    finally:
        _fake_close(wr, cw, dr)
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
