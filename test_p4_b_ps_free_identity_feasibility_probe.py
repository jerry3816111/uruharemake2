"""Fake-only checks for the one-use P4 B identity-visibility probe.

No test starts a surrogate, a sandbox, a model, a browser, or a subprocess.
These checks do not establish macOS sandbox visibility.
"""

from contextlib import ExitStack, nullcontext, redirect_stdout
import hashlib
import io
import json
import struct
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import p4_b_ps_free_identity_feasibility_probe as probe


class ProcargsParsingTests(unittest.TestCase):
    EXECUTABLE = "/opt/python3.11/bin/python3.11"
    ARGV = [EXECUTABLE, "/tmp/probe-v1.py", "--daemon"]

    @classmethod
    def procargs(cls, *, argc=None, argv=None, env=()):
        argv = cls.ARGV if argv is None else argv
        argc = len(argv) if argc is None else argc
        fields = [cls.EXECUTABLE, *argv, *env]
        return (struct.pack("=i", argc) +
                b"\0".join(field.encode("utf-8") for field in fields) + b"\0")

    def test_python_path_containing_one_is_not_env_pollution(self):
        raw = self.procargs(env=[
            f"OLLAMA_MODELS={probe.MODEL_SENTINEL}",
            "OLLAMA_NO_CLOUD=1",
        ])
        executable, argv, counts = probe._parse_procargs(raw, probe.EXPECTED_ENV)

        self.assertEqual(executable, self.EXECUTABLE)
        self.assertEqual(argv, self.ARGV)
        self.assertEqual(counts, {"OLLAMA_MODELS": 1, "OLLAMA_NO_CLOUD": 1})

    def test_full_assignment_in_argv_is_not_counted_as_environment(self):
        for assignment in (
            f"OLLAMA_MODELS={probe.MODEL_SENTINEL}",
            "OLLAMA_NO_CLOUD=1",
        ):
            with self.subTest(assignment=assignment):
                raw = self.procargs(
                    argv=[self.EXECUTABLE, "/tmp/probe-v1.py", assignment],
                    env=[assignment],
                )
                with self.assertRaisesRegex(probe.ProbeError, "env_oracle_in_argv"):
                    probe._parse_procargs(raw, probe.EXPECTED_ENV)

    def test_env_key_name_in_argv_is_rejected(self):
        raw = self.procargs(
            argv=[self.EXECUTABLE, "/tmp/probe-v1.py", "OLLAMA_NO_CLOUD"],
            env=["OLLAMA_NO_CLOUD=1"],
        )
        with self.assertRaisesRegex(probe.ProbeError, "env_oracle_in_argv"):
            probe._parse_procargs(raw, probe.EXPECTED_ENV)

    def test_each_key_needs_one_assignment_with_the_expected_value(self):
        cases = (
            (["PREFIX_OLLAMA_NO_CLOUD=1", "OLLAMA_NO_CLOUD=1"], 1),
            (["OLLAMA_NO_CLOUD=1", "OLLAMA_NO_CLOUD=1"], 0),
            (["OLLAMA_NO_CLOUD=1", "OLLAMA_NO_CLOUD=0"], 0),
            (["OLLAMA_NO_CLOUD=0"], 0),
        )
        for cloud_entries, wanted in cases:
            with self.subTest(cloud_entries=cloud_entries):
                raw = self.procargs(env=[
                    f"OLLAMA_MODELS={probe.MODEL_SENTINEL}", *cloud_entries,
                ])
                _, _, counts = probe._parse_procargs(raw, probe.EXPECTED_ENV)
                self.assertEqual(counts["OLLAMA_MODELS"], 1)
                self.assertEqual(counts["OLLAMA_NO_CLOUD"], wanted)

    def test_observer_requires_one_exact_value_for_each_env_key(self):
        expected = {"pid": 17, "port": 12345, "start": [100, 7],
                    "executable": self.EXECUTABLE, "argv": self.ARGV}
        with patch.object(probe, "_bsd_info", return_value=(17, 1, 100, 7)), \
                patch.object(probe, "_listener_owner", return_value=True):
            for counts, wanted in (
                ({"OLLAMA_MODELS": 1, "OLLAMA_NO_CLOUD": 1}, True),
                ({"OLLAMA_MODELS": 2, "OLLAMA_NO_CLOUD": 1}, False),
                ({"OLLAMA_MODELS": 1, "OLLAMA_NO_CLOUD": 0}, False),
            ):
                with self.subTest(counts=counts), patch.object(
                    probe, "_procargs", return_value=(self.EXECUTABLE, self.ARGV, counts),
                ):
                    self.assertEqual(probe._observe_one(expected, 999)[3], wanted)

    def test_malformed_argc_is_rejected(self):
        for argc in (0, 1, 9):
            with self.subTest(argc=argc):
                with self.assertRaisesRegex(probe.ProbeError, "procargs_invalid"):
                    probe._parse_procargs(self.procargs(argc=argc), probe.EXPECTED_ENV)
        truncated = (struct.pack("=i", 3) + self.EXECUTABLE.encode() + b"\0" +
                     self.EXECUTABLE.encode() + b"\0" + b"/tmp/probe-v1.py\0")
        with self.assertRaisesRegex(probe.ProbeError, "procargs_invalid"):
            probe._parse_procargs(truncated, probe.EXPECTED_ENV)


class ExternalOracleClassificationTests(unittest.TestCase):
    def test_external_procargs_failure_is_invalid_surrogate(self):
        for reason in ("procargs_unavailable", "procargs_invalid"):
            with self.subTest(reason=reason), \
                    patch.object(probe, "_bsd_info", return_value=(17, 1, 100, 7)), \
                    patch.object(probe, "_procargs", side_effect=probe.ProbeError(reason)), \
                    patch.object(probe, "_run_fixed") as run_fixed:
                with self.assertRaises(probe.ProbeError) as error:
                    probe._expected_process(17, 12345, "daemon", 999)
                self.assertEqual(str(error.exception), "invalid_surrogate")
                run_fixed.assert_not_called()

    def test_early_oracle_failure_with_daemon_exit_one_needs_cleanup_review(self):
        class FakePath:
            def __init__(self, label, content=b""):
                self.label = label
                self.content = content

            def __str__(self):
                return self.label

            def is_file(self):
                return True

            def read_bytes(self):
                return self.content

        class FakeDaemon:
            pid = 17

            def __init__(self):
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO()
                self.returncode = None

            def poll(self):
                return self.returncode

            def wait(self, timeout=None):
                self.returncode = 1
                return 1

        daemon = FakeDaemon()
        ready = {"pid": 17, "port": 12345,
                 "runner_pid": 18, "runner_port": 12346}
        with ExitStack() as stack:
            stack.enter_context(patch.object(probe, "sys", SimpleNamespace(platform="darwin")))
            stack.enter_context(patch.object(probe, "PYTHON", FakePath("/fake/python")))
            stack.enter_context(patch.object(probe, "SCRIPT", FakePath("/fake/probe.py", b"source")))
            stack.enter_context(patch.object(probe, "PROFILE", FakePath("/fake/profile.sb", b"profile")))
            stack.enter_context(patch.object(
                probe, "PROFILE_SHA256", hashlib.sha256(b"profile").hexdigest(),
            ))
            popen = stack.enter_context(patch.object(probe.subprocess, "Popen", return_value=daemon))
            stack.enter_context(patch.object(
                probe, "_LineReader", return_value=SimpleNamespace(read=lambda _deadline: ready),
            ))
            oracle = stack.enter_context(patch.object(
                probe, "_expected_process", side_effect=probe.ProbeError("invalid_surrogate"),
            ))
            stack.enter_context(patch.object(probe.signal, "signal"))
            stack.enter_context(patch.object(probe.signal, "setitimer"))

            result = probe._execute()

        popen.assert_called_once()
        oracle.assert_called_once()
        self.assertEqual(oracle.call_args.args[:3], (17, 12345, "daemon"))
        self.assertEqual(result["status"], "cleanup_review_required")
        self.assertFalse(result["cleanup_verified"])
        self.assertEqual(result["daemon_exit_code"], 1)
        self.assertIsNone(result["runner_exit_code"])
        self.assertEqual(result["matrix"], {})


class ObserverProtocolTests(unittest.TestCase):
    DESCRIPTOR = {"daemon": {"pid": 17}, "runner": {"pid": 18}}
    FIELDS = (
        "daemon_start", "runner_start", "daemon_argv", "runner_argv",
        "daemon_env", "runner_env", "runner_parent", "daemon_listener",
        "runner_listener",
    )

    def test_runner_environment_is_a_required_observation(self):
        descriptor = {
            "daemon": {"pid": 17},
            "runner": {"pid": 18},
        }
        with patch.object(probe, "_observe_one", side_effect=[
            (True, True, True, True),
            (True, True, True, False),
        ]), patch.object(probe, "_bsd_info", return_value=(18, 17, 101, 8)):
            matrix = probe._observe(descriptor, 999)
        self.assertIn("runner_env", matrix)
        self.assertFalse(matrix["runner_env"])

    def test_phase_handshake_reobserves_in_same_observer(self):
        before = dict.fromkeys(self.FIELDS, True)
        after = {**before, "runner_start": False, "runner_listener": False}
        input_bytes = (json.dumps(self.DESCRIPTOR) + "\n" +
                       json.dumps({"phase": "after_runner_exit"}) + "\n").encode()
        output = io.BytesIO()
        fake_sys = SimpleNamespace(
            stdin=SimpleNamespace(buffer=io.BytesIO(input_bytes)),
            stdout=SimpleNamespace(buffer=output),
        )
        with patch.object(probe, "sys", fake_sys), \
                patch.object(probe, "_observe", side_effect=[before, after]) as observe, \
                patch.object(probe.os, "getpid", return_value=77):
            self.assertEqual(probe._observer_mode(), 0)

        self.assertEqual([call.args[0] for call in observe.call_args_list],
                         [self.DESCRIPTOR, self.DESCRIPTOR])
        messages = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([message["phase"] for message in messages], ["before", "after"])
        self.assertEqual([message["observer_pid"] for message in messages], [77, 77])
        self.assertTrue(all(messages[0]["matrix"].values()))
        self.assertFalse(messages[1]["matrix"]["runner_listener"])

    def test_wrong_phase_cannot_trigger_second_observation(self):
        input_bytes = (json.dumps(self.DESCRIPTOR) + "\n" +
                       json.dumps({"phase": "not_after_runner_exit"}) + "\n").encode()
        fake_sys = SimpleNamespace(
            stdin=SimpleNamespace(buffer=io.BytesIO(input_bytes)),
            stdout=SimpleNamespace(buffer=io.BytesIO()),
        )
        with patch.object(probe, "sys", fake_sys), \
                patch.object(probe, "_observe", return_value=dict.fromkeys(self.FIELDS, True)) as observe:
            self.assertEqual(probe._observer_mode(), 2)
        observe.assert_called_once()

    def _run_fake_supervisor(self, after, *, ack_exit_code=-15,
                             observer_reported_pid=77):
        before = dict.fromkeys(self.FIELDS, True)

        class FakePath:
            def __init__(self, label, content=b""):
                self.label = label
                self.content = content

            def __str__(self):
                return self.label

            def is_file(self):
                return True

            def read_bytes(self):
                return self.content

        class FakeProcess:
            def __init__(self, pid):
                self.pid = pid
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO()
                self.running = True
                self.returncode = None

            def poll(self):
                return None if self.running else 0

            def terminate(self):
                self.running = False
                self.returncode = -15

            def wait(self, timeout=None):
                self.running = False
                if self.returncode is None:
                    self.returncode = 0
                return 0

        daemon = FakeProcess(17)
        observer = FakeProcess(77)
        daemon_ready = {"pid": 17, "port": 12345,
                        "runner_pid": 18, "runner_port": 12346}
        messages = iter([
            daemon_ready,
            {"phase": "before", "observer_pid": observer_reported_pid, "matrix": before},
            {"phase": "runner_reaped", "pid": 18, "exit_code": ack_exit_code},
            {"phase": "after", "observer_pid": observer_reported_pid, "matrix": after},
        ])
        writes = []
        source = FakePath("/fake/probe.py", b"source")
        profile = FakePath("/fake/profile.sb", b"profile")
        expected_processes = [
            {"pid": 17, "port": 12345, "start": [100, 7], "ppid": 1,
             "executable": "/fake/python", "argv": ["/fake/python", "/fake/probe.py", "--daemon"]},
            {"pid": 18, "port": 12346, "start": [101, 8], "ppid": 17,
             "executable": "/fake/python", "argv": ["/fake/python", "/fake/probe.py", "--runner"]},
        ]
        with ExitStack() as stack:
            stack.enter_context(patch.object(probe, "sys", SimpleNamespace(platform="darwin")))
            stack.enter_context(patch.object(probe, "PYTHON", FakePath("/fake/python")))
            stack.enter_context(patch.object(probe, "SCRIPT", source))
            stack.enter_context(patch.object(probe, "PROFILE", profile))
            stack.enter_context(patch.object(
                probe, "PROFILE_SHA256", hashlib.sha256(b"profile").hexdigest(),
            ))
            popen = stack.enter_context(patch.object(
                probe.subprocess, "Popen", side_effect=[daemon, observer],
            ))
            stack.enter_context(patch.object(
                probe, "_LineReader", side_effect=lambda _stream: SimpleNamespace(
                    read=lambda _deadline: next(messages),
                ),
            ))
            stack.enter_context(patch.object(
                probe, "_write_line", side_effect=lambda stream, value: writes.append((stream, value)),
            ))
            stack.enter_context(patch.object(
                probe, "_expected_process", side_effect=expected_processes,
            ))
            stack.enter_context(patch.object(probe, "_outside_env_valid", return_value=True))
            exact_signal = stack.enter_context(patch.object(probe, "_exact_signal", return_value=True))
            stack.enter_context(patch.object(probe, "_wait_gone", return_value=True))
            stack.enter_context(patch.object(probe.signal, "signal"))
            stack.enter_context(patch.object(probe.signal, "setitimer"))

            result = probe._execute()

        self.assertEqual(popen.call_count, 2)
        daemon_call = popen.call_args_list[0]
        self.assertEqual(daemon_call.args[0],
                         ["/fake/python", "/fake/probe.py", "--daemon"])
        self.assertEqual(
            {key: daemon_call.kwargs["env"][key] for key in probe.EXPECTED_ENV},
            probe.EXPECTED_ENV,
        )
        self.assertTrue(all(
            key not in arg for arg in daemon_call.args[0] for key in probe.EXPECTED_ENV
        ))
        exact_signal.assert_not_called()
        descriptor = {"daemon": expected_processes[0], "runner": expected_processes[1]}
        expected_writes = [(observer.stdin, descriptor)]
        if observer_reported_pid == observer.pid:
            expected_writes.append(
                (daemon.stdin, {"phase": "stop_runner", "pid": 18, "start": [101, 8]}),
            )
            if ack_exit_code == -probe.signal.SIGTERM:
                expected_writes.append((observer.stdin, {"phase": "after_runner_exit"}))
        self.assertEqual(writes, expected_writes)
        self.assertTrue(result["cleanup_verified"])
        return result

    def test_supervisor_rejects_stale_all_positive_after_runner_exit(self):
        result = self._run_fake_supervisor(dict.fromkeys(self.FIELDS, True))
        self.assertEqual(result["status"], "no_go_stale_observer")
        self.assertFalse(result["negative_rejected"])

    def test_runner_only_negative_cannot_hide_lost_daemon(self):
        after = dict.fromkeys(self.FIELDS, True)
        for field in ("runner_start", "runner_argv", "runner_env",
                      "runner_parent", "runner_listener"):
            after[field] = False
        after["daemon_listener"] = False
        result = self._run_fake_supervisor(after)
        self.assertEqual(result["status"], "no_go_stale_observer")
        self.assertFalse(result["negative_rejected"])

    def test_parent_rejects_runner_reap_ack_with_wrong_exit_code(self):
        after = dict.fromkeys(self.FIELDS, True)
        for field in ("runner_start", "runner_argv", "runner_env",
                      "runner_parent", "runner_listener"):
            after[field] = False
        result = self._run_fake_supervisor(after, ack_exit_code=0)
        self.assertEqual(result["status"], "runner_reap_unconfirmed")
        self.assertNotEqual(result["status"], "feasible_observability")
        self.assertFalse(result["negative_rejected"])

    def test_reported_observer_pid_must_match_supervised_pid_before_runner_stop(self):
        result = self._run_fake_supervisor(
            dict.fromkeys(self.FIELDS, True), observer_reported_pid=78,
        )
        self.assertEqual(result["status"], "observer_before_invalid")
        self.assertFalse(result["negative_rejected"])
        self.assertIsNone(result["runner_exit_code"])
        self.assertEqual(result["matrix"], {})


class DaemonPhaseTests(unittest.TestCase):
    def test_runner_exit_between_poll_and_terminate_is_not_acknowledged(self):
        runner = SimpleNamespace(pid=18, stdout=io.BytesIO(), returncode=None)
        runner.poll = Mock(side_effect=lambda: runner.returncode)
        runner.terminate = Mock()
        runner.wait = Mock(side_effect=lambda timeout=None: runner.returncode)
        command = {"phase": "stop_runner", "pid": 18, "start": [101, 8]}
        fake_sys = SimpleNamespace(
            stdin=SimpleNamespace(buffer=io.BytesIO((json.dumps(command) + "\n").encode())),
            stdout=SimpleNamespace(buffer=io.BytesIO()),
        )
        server = SimpleNamespace(getsockname=lambda: ("127.0.0.1", 12345))
        writes = []

        def runner_exits_during_generation_check(_pid):
            runner.returncode = 0
            return (18, 17, 101, 8)

        with patch.object(probe, "sys", fake_sys), \
                patch.object(probe, "_listener", return_value=nullcontext(server)), \
                patch.object(probe.subprocess, "Popen", return_value=runner), \
                patch.object(probe, "_LineReader", return_value=SimpleNamespace(
                    read=lambda _deadline: {"pid": 18, "port": 12346},
                )), \
                patch.object(probe, "_bsd_info", side_effect=runner_exits_during_generation_check), \
                patch.object(probe, "_write_line",
                             side_effect=lambda stream, value: writes.append(value)), \
                patch.object(probe.os, "getpid", return_value=17), \
                patch.object(probe.signal, "signal"):
            with self.assertRaisesRegex(probe.ProbeError, "^runner_exit_unexpected$"):
                probe._daemon_mode()

        runner.terminate.assert_called_once()
        self.assertFalse(any(value.get("phase") == "runner_reaped" for value in writes))


class CliTests(unittest.TestCase):
    def test_default_cli_does_not_execute(self):
        output = io.StringIO()
        with patch.object(probe, "_execute", side_effect=AssertionError("executed")), \
                redirect_stdout(output):
            self.assertEqual(probe.main([]), 2)
        self.assertEqual(json.loads(output.getvalue()),
                         {"ok": False, "reason": "explicit_execute_required"})


class WatchdogTests(unittest.TestCase):
    def test_supervisor_rejects_internally_inconsistent_feasible_result(self):
        valid_shape = {
            "schema": "p4_b_ps_free_identity_feasibility_v1",
            "status": "feasible_observability",
            "matrix": dict.fromkeys(probe._MATRIX_KEYS, True),
            "negative_rejected": True,
            "cleanup_verified": True,
            "daemon_exit_code": 0,
            "runner_exit_code": -probe.signal.SIGTERM,
            "observer_exit_code": 0,
            "active_wall_s": 1.0,
            "total_wall_s": 1.2,
            "source_sha256": hashlib.sha256(probe.SCRIPT.read_bytes()).hexdigest(),
            "model_calls": 0,
            "b_sends": 0,
            "web_sends": 0,
        }
        self.assertEqual(set(valid_shape), probe._RESULT_KEYS)
        for broken_field in (
            "negative_rejected", "matrix", "runner_exit_code",
            "daemon_exit_code", "observer_exit_code",
        ):
            with self.subTest(broken_field=broken_field):
                forged = {**valid_shape, "matrix": dict(valid_shape["matrix"])}
                if broken_field == "matrix":
                    forged["matrix"]["daemon_listener"] = False
                elif broken_field == "negative_rejected":
                    forged[broken_field] = False
                elif broken_field == "daemon_exit_code":
                    forged[broken_field] = 1
                elif broken_field == "observer_exit_code":
                    forged[broken_field] = 2
                else:
                    forged[broken_field] = 0
                worker = SimpleNamespace(pid=47, stdout=io.BytesIO(), returncode=None)
                reader = SimpleNamespace(read=Mock(side_effect=[
                    {"phase": "cleanup_started", "active_wall_s": 1.0},
                    forged,
                ]))
                with patch.object(probe.subprocess, "Popen", return_value=worker), \
                        patch.object(probe, "_LineReader", return_value=reader), \
                        patch.object(probe, "_stop_owned_group", return_value=True) as stop:
                    result = probe._execute_supervised()
                stop.assert_called_once()
                self.assertEqual(result["status"], "worker_result_invalid")
                self.assertFalse(result["negative_rejected"])
                self.assertNotEqual(result["status"], "feasible_observability")

    def test_worker_cleanup_failure_cannot_return_feasible(self):
        worker = SimpleNamespace(pid=47, stdout=io.BytesIO(), returncode=None)
        incomplete_cleanup_result = {
            "schema": "p4_b_ps_free_identity_feasibility_v1",
            "status": "no_go_missing_identity_field",
            "matrix": {},
            "negative_rejected": False,
            "cleanup_verified": False,
            "daemon_exit_code": 0,
            "runner_exit_code": None,
            "observer_exit_code": 0,
            "active_wall_s": 1.0,
            "total_wall_s": 1.2,
            "source_sha256": hashlib.sha256(probe.SCRIPT.read_bytes()).hexdigest(),
            "model_calls": 0,
            "b_sends": 0,
            "web_sends": 0,
        }
        self.assertEqual(set(incomplete_cleanup_result), probe._RESULT_KEYS)
        reader = SimpleNamespace(read=Mock(side_effect=[
            {"phase": "cleanup_started", "active_wall_s": 1.0},
            incomplete_cleanup_result,
        ]))
        with patch.object(probe.subprocess, "Popen", return_value=worker), \
                patch.object(probe, "_LineReader", return_value=reader), \
                patch.object(probe, "_stop_owned_group", return_value=True) as stop:
            result = probe._execute_supervised()

        stop.assert_called_once()
        self.assertIs(stop.call_args.args[0], worker)
        self.assertEqual(result["status"], "worker_cleanup_review_required")
        self.assertNotEqual(result["status"], "feasible_observability")
        self.assertTrue(result["cleanup_verified"])
        self.assertFalse(result["negative_rejected"])

    def test_timeout_and_missing_cleanup_phase_stop_only_owned_worker(self):
        cases = (
            (probe.ProbeError("deadline_exceeded"), "deadline_exceeded"),
            ({"phase": "before", "active_wall_s": 1.0}, "worker_phase_invalid"),
        )
        for first_read, wanted_status in cases:
            with self.subTest(wanted_status=wanted_status):
                worker = SimpleNamespace(pid=47, stdout=io.BytesIO())
                read = (Mock(side_effect=first_read) if isinstance(first_read, Exception)
                        else Mock(return_value=first_read))
                with patch.object(probe.subprocess, "Popen", return_value=worker) as popen, \
                        patch.object(probe, "_LineReader", return_value=SimpleNamespace(read=read)), \
                        patch.object(probe, "_stop_owned_group", return_value=True) as stop:
                    result = probe._execute_supervised()

                self.assertEqual(result["status"], wanted_status)
                self.assertTrue(result["cleanup_verified"])
                self.assertEqual(result["matrix"], {})
                self.assertEqual(popen.call_args.args[0],
                                 [str(probe.PYTHON), str(probe.SCRIPT), "--worker"])
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                stop.assert_called_once()
                self.assertIs(stop.call_args.args[0], worker)

    def test_wrong_process_group_is_never_signaled(self):
        worker = SimpleNamespace(pid=47)
        with patch.object(probe.os, "getpgid", return_value=999), \
                patch.object(probe.os, "killpg") as killpg:
            self.assertFalse(probe._stop_owned_group(worker, time.monotonic() + 1))
        killpg.assert_not_called()

    def test_group_stop_signals_only_direct_child_group(self):
        worker = SimpleNamespace(pid=47, wait=Mock(return_value=0))
        with patch.object(probe.os, "getpgid", return_value=47), \
                patch.object(probe.os, "killpg") as killpg, \
                patch.object(probe, "_owned_group_gone",
                             side_effect=[False, True, True, True]):
            self.assertTrue(probe._stop_owned_group(worker, time.monotonic() + 1))
        killpg.assert_called_once_with(47, probe.signal.SIGTERM)
        worker.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
