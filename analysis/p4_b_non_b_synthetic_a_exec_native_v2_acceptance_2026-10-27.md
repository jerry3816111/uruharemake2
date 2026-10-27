# P4-B non-B synthetic A native exec v2: fake-only acceptance

Scope: one prospective correction to the **synthetic A post-exec witness**
inside the existing P4-B non-B task card. This is not an installed Ollama,
runner, model, HTTP, physical-stop, product, Safari, or formal-research
acceptance. The failed Python v1 target and its red/failure evidence remain
at `31f7e5a`, `b58fe6e`, and `07880dc`; the v2 amendment and red contract
were committed before the source at `239e7fd` and `0ae1ddf`.

## Before, change, and observable result

The strengthened Python v1 WIP failed its FD witness in 17/30 direct
invocations; a delayed diagnostic saw framework-Python image/argv0 drift
in 30/30. Native cat/grep with immediate double snapshots each had only
4/10 clean stdio-only observations. Those are exposed engineering probes,
not a formal comparison. V1 public marker is now explicitly fail-closed
with zero forks; its failure is not reinterpreted as a pass.

V2 accepts only the exact `synthetic_a_exec_probe_v2` plain-dict marker.
Within the same 11 direct-child graph and 24-pipe/48-endpoint allocation,
A executes fixed `/bin/cat` with exact one-item argv and empty environment.
The CLOEXEC status-pipe zero-data EOF is a hint only. P actively obtains
two consecutive full OS image/argv/FD-number/type/**pipe-handle** snapshots
at least 10 ms apart, bracketed by raw PID generation/PPID/PGID and live
checks, inside a five-second absolute deadline. It records every attempt
in a bounded raw-free ledger; only transient extra VNODE FDs or exact
`ProbeError("procargs_unavailable")` may be observed again. Extra PIPE,
wrong image/argv, identity drift, other FD/observer errors, and timeout
fail closed. Only after the final witness does P close the private stdin
writer with zero bytes; A then exits normally and the other ten roles are
normally released/reaped. Six exact negative faults and invalid markers
remain covered. Failure exceptions retain fixed public error strings and
carry only bounded, raw-free attempt metadata for engineering inspection.

Final-source 30 isolated direct positive invocations: **30/30** reached
11/11 exact normal reaps, each with at least two complete observations;
attempt count 2–3, five total transient-VNODE observations, zero
procargs-unavailable observations, and minimum sampled parent FD margin
204 under this host's 256 soft FD limit. The 30 probes took 4.852 s total.
This is a local fake-only stability sample, not a statistical guarantee or
proof that an unobserved transient exec/FD never occurred.

## Verification and retained failure

- Prospective test-only contract first produced seven intended red tests,
  all on `process_supervisor_not_implemented`, plus four passing invalid
  marker rejections. A same-model read-only review tightened the six fault
  assertions to exact codes and added parent-side real OS image/argv
  observation; it was not an independent human review.
- Final focused command:
  `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s -p no:cacheprovider --tb=short test_p4_b_non_b_parity_live_operator.py -k synthetic_a_exec`
  returned **27 passed, 377 deselected** in 17.14 s (main-agent repeat).
  It includes V1 zero-fork refusal, V2 success/fault/invalid-marker cases,
  transient/persistent VNODE, first-snapshot extra PIPE, a forged
  `ProbeError` subclass, and a delayed second exact snapshot crossing the
  five-second deadline. Persistent VNODE and extra PIPE expose the
  failure-path attempt ledger without converting failure to success.
- The source implementer ran the affected operator file with the same
  `-q -s -p no:cacheprovider --tb=short` shape: **404/404 passed** in
  133.76 s. The earlier run that omitted `-s` yielded 260 pass/142 fail:
  pytest capture consumed extra FDs, and old fake-seven reservation tests
  failed at `fake_seven_fd_reservation_unavailable` under soft limit 256.
  One representative old V2 case passed 1/1 when rerun with `-s`; the
  corrected full-file run is the acceptance evidence. The failed invocation
  is retained as test-environment evidence, not hidden or called a source
  regression.
- Independent same-model read-only source review initially blocked on
  lost failure-path attempt records, a possible late second snapshot,
  and a `ProbeError` subclass loophole. All three were corrected before
  final tests: bounded metadata on fixed-code exceptions, a final
  `time.monotonic() >= deadline` rejection, and exact exception type.
  The reviewer then found no remaining fake-only blocker. This review is
  not a human or live-system acceptance.
- `git diff --check` is clean. No Ollama/model-byte/target HTTP or TCP/Safari/
  B Send/production-DB access was used for this slice; only local OS
  process probes and test children were exercised. The unrelated
  `output/graduate_application_report/` directory was untouched.

## Boundary and next gate

V2 proves a narrow, cooperative synthetic held-to-native-exec control path
on the tested macOS host. It does **not** prove executable bytes/SHA,
installed model identity, runner child discovery/non-parent reaping,
physical T0+90 stop, seven-operation budget, conversation quality, full
pipeline, runtime/production, or comparative advantage over an LLM. A
bounded sample cannot prove continuous FD absence between samples.

Next independent gate, only after this fake-only commit/review, is the
A-postexec **synthetic runner lifecycle**: exact child enumeration under A,
`S_runner` independent `NOTE_EXIT` registration/event fields, and the
non-parent `waitpid` boundary. Freeze its before evidence, one variable,
faults, FD/time budget, tests and resource ceiling before source. Do not
borrow this A exec PASS as runner or live authorization.
