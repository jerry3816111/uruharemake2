# P4-B non-B early-A-death negative: prospective, test-only freeze

Status: **isolated diagnostic only; real/live NO-GO**. This does not amend
the accepted synthetic runner source, its normal receipt, the real supervisor
freeze, or B Send authorization. The read-only before analysis is
`analysis/p4_b_non_b_early_a_death_orphan_window_review_2026-10-27.md`:
`known_runners` is empty until P has an OS cat identity, so `all(empty)` in
cleanup is not a proof that an unknown descendant stopped. No actual leak was
observed there. This test's first run against unchanged source is the runtime
before observation; preserve a failure instead of adjusting the contract to
make it green.

## One variable and controlled interleaving

Only the test-side scheduling of A's death changes. Use the accepted exact
`synthetic_runner_lifecycle_probe_v1` null-fault target and 11-role/25-pipe
topology. In the parent P alone, wrap its first-child enumeration. When the
OS shows exactly one postexec `/bin/cat` under the exact live A generation,
the test independently records the cat's PID/start generation, executable,
argv and private fd0 pipe-handle match. While A is still P's direct unreaped
child, recheck its generation and send SIGKILL to **that A PID only**. The
wrapper returns an empty child list to P on this and later P enumerations;
child O/S_runner calls retain the original enumeration function. The test's
private cat witness is never given to the operator, and P must not observe a
cat image through its normal identity path. If an enumeration is transient
before the exact cat image/FD witness is available, return empty and retry
under the existing deadline. If the exact barrier is not reached, fail the
test; do not accept a zero-child shortcut.

Expected result: operator fails closed with `fake_runner_spawn_unavailable`,
not a fake-positive receipt; after its `finally` closes the private stdin
writer, the originally witnessed cat PID/start generation is independently
absent, all 11 direct P children have been reaped, P FD count is restored,
fail-on-touch caller-path sentinels are not accessed, and elapsed time is
under 25 seconds. Merely checking that a directory was not created would
not prove absence of reads. The
cat check must use stable `(pid,start_sec,start_usec)` or exact kernel ESRCH,
not PPID drift or an arbitrary probe exception. Product cleanup of an
unknown runner is **not** inferred from a passed cooperative-cat case.

If the cat survives, the acceptance assertion fails. The test-side `finally`
must also handle any other test exception after the cat was captured: it may
clean that precise PID only after a fresh matching generation check. If
identity cannot be reverified, no blind or group signal is sent and the
result requires manual review. Test-side emergency cleanup and direct-
child hygiene are never counted as product stop proof. No source correction
is preauthorized: first record the unchanged-source result; if red, review
the smallest exact failure before a separate source decision.

Allowed files: `test_p4_b_non_b_parity_live_operator.py`, this freeze,
`analysis/p4_b_non_b_early_a_death_negative_result_2026-10-27.md`, and the
top of `CURRENT_TASK.md`. Product source may change only after a red runtime
result and a separately documented narrow correction. First run the one
focused negative, then adjacent runner-focused tests and only affected
operator regression if source changes. No Ollama, HTTP, formal DB, Safari,
model bytes, original dirty checkout, or unrelated `output/` changes.

Even a PASS covers only this controlled cooperative `/bin/cat` path. The
unknown-descendant window for a real runner, run-wide containment, installed
identity, true model/port use, T0+90 physical stop, and B Send remain
`REVIEW_REQUIRED` until their own prospective design and evidence.
