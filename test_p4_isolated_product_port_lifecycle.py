"""No-model contracts for the direct-act product controller's opt-in port."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap


def _isolated(script: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    return json.loads(completed.stdout.splitlines()[-1])


def test_all_cli_actions_forward_only_the_selected_port_and_restore_default():
    result = _isolated("""
        import json
        from pathlib import Path
        import p4_direct_reply_act_m29_priority_detached_control as wrapper

        base = wrapper.prior.base_controller
        original_port = base.PORT
        original_env = wrapper.launchd._isolated_env
        original_preflight = wrapper.product_launcher.preflight_preference_fallback
        observed = []
        layout = {
            "runtime_root": Path("/tmp/port-contract"),
            "memory_db": Path("/tmp/port-contract/memory_db"),
            "session_db": Path("/tmp/port-contract/session_db"),
            "web_logs": Path("/tmp/port-contract/web_logs"),
            "jsonl_log": Path("/tmp/port-contract/web_logs/conversation.jsonl"),
            "text_log": Path("/tmp/port-contract/web_logs/conversation.txt"),
        }
        def no_launch_main(argv):
            env = wrapper.launchd._isolated_env(layout, port=base.PORT)
            observed.append([
                list(argv), base.PORT, env["URUHA_WEB_PORT"],
                env.get("URUHA_WEB_TURN_ADMISSION_JOURNAL_PATH"),
            ])
            return 17
        base.main = no_launch_main
        for action in ("prepare", "start", "status", "verify-ready", "stop"):
            argv = [action, "--product-port", "7914"]
            if action in ("status", "verify-ready", "stop"):
                argv += ["--runtime-root", "/tmp/unused"]
            assert wrapper.main(argv) == 17
            assert base.PORT == original_port == 7894
            assert wrapper.launchd._isolated_env is original_env
            assert wrapper.product_launcher.preflight_preference_fallback is original_preflight
        assert wrapper.main(["status", "--runtime-root", "/tmp/unused"]) == 17
        assert observed[-1][1:] == [7894, "7894", None]
        assert wrapper.main([
            "--turn-admission-journal", "start", "--mode", "product",
            "--product-port", "7916",
        ]) == 17
        assert observed[-1][1:] == [
            7916, "7916", "/tmp/port-contract/turn_admission_journal.jsonl",
        ]
        assert len(observed) == 7
        assert all(row[1:] == [7914, "7914", None] for row in observed[:5])
        assert all("--product-port" not in row[0] for row in observed)
        assert all("--turn-admission-journal" not in row[0] for row in observed)
        print(json.dumps({"actions": len(observed), "default": original_port}))
    """)
    assert result == {"actions": 7, "default": 7894}


def test_invalid_port_and_exception_leave_all_globals_unchanged():
    result = _isolated("""
        import json
        import p4_direct_reply_act_m29_priority_detached_control as wrapper

        base = wrapper.prior.base_controller
        original_port = base.PORT
        original_env = wrapper.launchd._isolated_env
        original_preflight = wrapper.product_launcher.preflight_preference_fallback
        called = []
        def synthetic_failure(argv):
            called.append(base.PORT)
            raise LookupError("synthetic_no_launch")
        base.main = synthetic_failure
        for bad in ("0", "1023", "65536"):
            try:
                wrapper.main(["prepare", "--product-port", bad])
            except SystemExit as exc:
                assert exc.code == 2
            else:
                raise AssertionError("invalid port admitted")
            assert base.PORT == original_port
            assert wrapper.launchd._isolated_env is original_env
            assert wrapper.product_launcher.preflight_preference_fallback is original_preflight
        assert called == []
        try:
            wrapper.main(["start", "--mode", "product", "--product-port", "7914"])
        except LookupError as exc:
            assert str(exc) == "synthetic_no_launch"
        else:
            raise AssertionError("missing synthetic failure")
        assert called == [7914]
        assert base.PORT == original_port
        assert wrapper.launchd._isolated_env is original_env
        assert wrapper.product_launcher.preflight_preference_fallback is original_preflight
        print(json.dumps({"invalid_rejected": 3, "restored": True}))
    """)
    assert result == {"invalid_rejected": 3, "restored": True}


def test_real_prepared_receipt_rejects_mismatched_start_before_preflight():
    result = _isolated("""
        import contextlib
        import io
        import json
        import sys
        import tempfile
        from pathlib import Path
        import p4_direct_reply_act_m29_priority_detached_control as wrapper

        base = wrapper.prior.base_controller
        with tempfile.TemporaryDirectory(prefix="uruha-product-") as scratch:
            root = Path(scratch)
            wrapper.base_launcher._write_manifest(root)
            original_prepare = wrapper.base_launcher.prepare_runtime_root
            wrapper.base_launcher.prepare_runtime_root = lambda *args, **kwargs: (root, True)
            try:
                captured = io.StringIO()
                with contextlib.redirect_stdout(captured):
                    assert wrapper.main(["prepare", "--product-port", "7914"]) == 0
                prepared = json.loads(captured.getvalue())
                receipt = json.loads((root / base.PREPARED).read_text())
                assert prepared["runtime_root"] == str(root)
                assert receipt["port"] == 7914
                assert base.PORT == 7894
            finally:
                wrapper.base_launcher.prepare_runtime_root = original_prepare
            # The real base CLI must reject the wrong selected port before any
            # model preflight, process launch, or one-use prepared claim.
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = wrapper.main([
                    "start", "--mode", "product", "--prepared-runtime-root", str(root),
                    "--python", sys.executable, "--product-port", "7915",
                ])
            failure = json.loads(captured.getvalue())
            assert code == 2
            assert failure == {"ok": False, "error": "prepared_receipt_mismatch"}
            assert not (root / base.PREPARED_CLAIM).exists()
            assert base.PORT == 7894
        print(json.dumps({"receipt_port": 7914, "wrong_port_rejected": True}))
    """)
    assert result == {"receipt_port": 7914, "wrong_port_rejected": True}


def test_real_base_cli_uses_opt_in_port_for_status_ready_and_stop():
    result = _isolated("""
        import contextlib
        import io
        import json
        import p4_direct_reply_act_m29_priority_detached_control as wrapper

        base = wrapper.prior.base_controller
        seen = []
        for action in ("status", "verify-ready", "stop"):
            def observe(root, *, _action=action):
                seen.append([_action, root, base.PORT])
                return {"ok": True, "port": base.PORT}
            setattr(base, action.replace("-", "_"), observe)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                assert wrapper.main([
                    action, "--runtime-root", "/tmp/no-launch", "--product-port", "7914"
                ]) == 0
            assert json.loads(out.getvalue())["port"] == 7914
            assert base.PORT == 7894
        assert seen == [
            ["status", "/tmp/no-launch", 7914],
            ["verify-ready", "/tmp/no-launch", 7914],
            ["stop", "/tmp/no-launch", 7914],
        ]
        print(json.dumps({"actions": len(seen), "selected_port": 7914}))
    """)
    assert result == {"actions": 3, "selected_port": 7914}


def test_wrong_port_rejects_existing_run_before_ready_or_stop_side_effects():
    result = _isolated("""
        import contextlib
        import io
        import json
        import os
        import tempfile
        from pathlib import Path
        import p4_direct_reply_act_m29_priority_detached_control as wrapper

        base = wrapper.prior.base_controller
        with tempfile.TemporaryDirectory(prefix="uruha-product-") as scratch:
            root = Path(scratch)
            wrapper.base_launcher._write_manifest(root)
            run_id = "0123456789abcdef"
            base._private_json(root / base.CURRENT, {
                "schema": base.SCHEMA, "uid": os.getuid(), "run_id": run_id,
            })
            base._private_json(root / base._name(run_id, "json"), {
                "schema": base.SCHEMA, "run_id": run_id, "uid": os.getuid(),
                "runtime_root": str(root), "mode": "product", "port": 7914,
                "pid": 4242, "start_identity": {"pid": 4242, "uid": os.getuid(), "pgid": 4242},
            })
            def forbidden(*args, **kwargs):
                raise AssertionError("wrong-port command reached a side effect")
            base.os.killpg = forbidden
            base._port_listeners = forbidden
            base.http.client.HTTPConnection = forbidden
            for action in ("status", "verify-ready", "stop"):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = wrapper.main([
                        action, "--runtime-root", str(root), "--product-port", "7915"
                    ])
                assert code == 2
                assert json.loads(output.getvalue()) == {
                    "ok": False, "error": "run_metadata_mismatch",
                }
                assert base.PORT == 7894
        print(json.dumps({"wrong_port_rejected": 3, "side_effects": 0}))
    """)
    assert result == {"wrong_port_rejected": 3, "side_effects": 0}
