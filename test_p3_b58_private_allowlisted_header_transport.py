from copy import deepcopy

import pytest

import p3_b58_private_allowlisted_header_transport as b58


PRIVATE_URL = "https://rr1---sn-test.googlevideo.com/videoplayback?sig=PRIVATE-CANARY"


def test_contract_binds_b57_failure_and_preserves_future_and_account_locks():
    assert b58.validate_contract() == {"valid": True, "errors": []}
    contract = b58.load_contract()
    assert contract["authorization"]["overrides_b57_next_execution_authorized_false"] is True
    assert contract["authorization"]["resolver_process_invocation_count_max"] == 1
    assert contract["authorization"]["direct_ffmpeg_process_invocation_count_max"] == 1
    assert contract["authorization"]["retry_or_additional_correction_authorized"] is False
    assert contract["authorization"]["paid_api_login_cookie_or_account_access_authorized"] is False
    assert contract["source"]["context_start_seconds"] == 3000.0
    assert contract["source"]["context_end_seconds"] == 3180.0
    assert all(contract["denied_actions"].values())


def test_resolver_command_prints_only_url_and_headers_without_cookie_or_download():
    command = b58.build_resolver_command()
    print_indexes = [index for index, value in enumerate(command) if value == "--print"]
    assert [command[index + 1] for index in print_indexes] == [
        "%(url)s",
        "%(http_headers)j",
    ]
    assert command[command.index("-f") + 1] == "bestaudio/best"
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert "--no-write-info-json" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert "--no-write-comments" in command
    assert "--no-cache-dir" in command
    assert not any("cookie" in value.lower() for value in command)
    assert not any(value in {"-o", "--output"} for value in command)
    assert command[-1] == "https://www.youtube.com/watch?v=4y5GiQpgJgo"


def test_private_parser_selects_only_allowlisted_non_sensitive_headers():
    payload = (
        PRIVATE_URL
        + "\n"
        + '{"User-Agent":"private-agent","Accept":"*/*",'
        + '"Accept-Language":"ja,en;q=0.5","Sec-Fetch-Mode":"navigate",'
        + '"Range":"bytes=0-10"}\n'
    ).encode()
    media_url, headers = b58.parse_private_resolver_output(payload)
    assert media_url == PRIVATE_URL
    assert headers == {
        "User-Agent": "private-agent",
        "Accept": "*/*",
        "Accept-Language": "ja,en;q=0.5",
    }
    assert "Range" not in headers
    assert "Sec-Fetch-Mode" not in headers


@pytest.mark.parametrize("name", ["Cookie", "Authorization", "Proxy-Authorization", "Set-Cookie"])
def test_private_parser_rejects_sensitive_headers(name):
    payload = (
        PRIVATE_URL + "\n" + '{"User-Agent":"agent","' + name + '":"PRIVATE-CANARY"}\n'
    ).encode()
    with pytest.raises(b58.B58ExecutionError, match="sensitive header"):
        b58.parse_private_resolver_output(payload)


def test_private_parser_rejects_missing_user_agent_and_header_injection():
    missing = (PRIVATE_URL + '\n{"Accept":"*/*"}\n').encode()
    with pytest.raises(b58.B58ExecutionError, match="required header"):
        b58.parse_private_resolver_output(missing)
    injected = (PRIVATE_URL + '\n{"User-Agent":"agent\\r\\nCookie: bad"}\n').encode()
    with pytest.raises(b58.B58ExecutionError, match="unsafe header"):
        b58.parse_private_resolver_output(injected)


def test_private_parser_rejects_extra_lines_non_googlevideo_and_bad_json():
    for rejected in (
        b"",
        (PRIVATE_URL + '\n{"User-Agent":"agent"}\nextra\n').encode(),
        b"https://youtube.com/watch?v=x\n{\"User-Agent\":\"agent\"}\n",
        (PRIVATE_URL + "\nnot-json\n").encode(),
    ):
        with pytest.raises(b58.B58ExecutionError):
            b58.parse_private_resolver_output(rejected)


def test_direct_ffmpeg_command_forwards_private_headers_and_exact_interval(tmp_path):
    output = tmp_path / "bounded.wav"
    command = b58.build_direct_ffmpeg_command(
        PRIVATE_URL,
        {
            "User-Agent": "private-agent",
            "Referer": "https://www.youtube.com/",
            "Origin": "https://www.youtube.com",
            "Accept": "*/*",
        },
        output,
    )
    assert command[command.index("-user_agent") + 1] == "private-agent"
    assert command[command.index("-referer") + 1] == "https://www.youtube.com/"
    header_block = command[command.index("-headers") + 1]
    assert header_block == "Origin: https://www.youtube.com\r\nAccept: */*\r\n"
    assert command[command.index("-ss") + 1] == "3000.000000"
    assert command[command.index("-i") + 1] == PRIVATE_URL
    assert command[command.index("-t") + 1] == "180.000000"
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-c:a") + 1] == "pcm_s16le"
    assert command[-1] == str(output)


def test_failure_receipt_contains_no_url_header_or_raw_diagnostics():
    result = b58._base_result(b58.load_contract())
    result.update(
        {
            "status": "header_transport_failed",
            "resolver_process_invocation_count": 1,
            "resolver_returncode": 0,
            "resolver_stdout_bytes_discarded": 180,
            "resolver_url_count": 1,
            "resolver_url_host_category": "googlevideo_cdn",
            "private_allowlisted_header_count": 2,
            "direct_ffmpeg_process_invocation_count": 1,
            "direct_ffmpeg_returncode": 1,
            "direct_ffmpeg_stderr_bytes_discarded": 35,
            "private_request_material_cleared_before_public_reader": True,
            "private_runtime_deleted_before_public_reader": True,
            "failure_stage": "direct_ffmpeg",
            "failure_category": "tls_or_network",
            "failure_class": "B58ExecutionError",
        }
    )
    b58._finalize_result(result)
    assert b58.validate_result(result) == {"valid": True, "errors": []}
    serialized = b58.canonical_json(result)
    assert "PRIVATE-CANARY" not in serialized
    assert "googlevideo.com" not in serialized
    assert "videoplayback" not in serialized
    assert "private-agent" not in serialized
    assert "User-Agent" not in serialized


def test_result_validator_rejects_private_material_future_and_paid_access():
    result = b58._base_result(b58.load_contract())
    result.update(
        {
            "status": "header_transport_failed",
            "failure_stage": "resolver",
            "failure_category": "unknown",
            "failure_class": "B58ExecutionError",
            "private_runtime_deleted_before_public_reader": True,
            "private_headers": {"User-Agent": "PRIVATE-CANARY"},
            "hidden_future_media_request_count": 1,
            "paid_api_or_account_access_count": 1,
        }
    )
    b58._finalize_result(result)
    report = b58.validate_result(result)
    assert "forbidden_key:private_headers" in report["errors"]
    assert "hidden_future_media_request_count" in report["errors"]
    assert "paid_api_or_account_access_count" in report["errors"]


def test_contract_drift_to_future_retry_cookie_or_header_persistence_fails():
    contract = b58.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["context_start_seconds"] = 3181.0
    assert "source_boundary" in b58.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["resolver"]["network_retry_count"] = 1
    assert "resolver_retries" in b58.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["resolver"]["cookies_or_browser_session_allowed"] = True
    assert "resolver_denial:cookies_or_browser_session_allowed" in b58.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["private_request_boundary"]["header_value_persistence_allowed"] = True
    assert "private_denial:header_value_persistence_allowed" in b58.validate_contract(drifted)["errors"]


def test_preexisting_state_or_public_output_fails_before_resolver(monkeypatch, tmp_path):
    monkeypatch.setattr(b58, "ROOT", tmp_path)
    contract = b58.load_contract()
    state_root = tmp_path / contract["runtime_state"]["state_root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b58.B58ExecutionError, match="already consumed"):
        b58._fresh_runtime_roots(contract)
    state_root.rmdir()
    public_root = tmp_path / contract["runtime_state"]["public_root"]
    public_root.mkdir(parents=True)
    (public_root / "occupied").write_bytes(b"x")
    with pytest.raises(b58.B58ExecutionError, match="nonempty"):
        b58._fresh_runtime_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b58.validate_implementation_freeze() == {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": 0,
        "direct_ffmpeg_process_invocation_count_at_freeze": 0,
        "hidden_future_media_request_count_at_freeze": 0,
    }
