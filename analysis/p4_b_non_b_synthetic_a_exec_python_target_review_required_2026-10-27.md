# P4-B non-B A exec: Python target REVIEW_REQUIRED

This is a retained **failure**, not fake-only acceptance. The frozen
synthetic A target in
`research/p4_b_non_b_synthetic_a_exec_gate_freeze_2026-10-27.md`
(`31f7e5a`) resolves the isolated framework Python executable and expects
exactly that path/argv after A's one `os.execve`. The test-only red contract
is `b58fe6e`; its pre-source result was 7 intended failures and 4 invalid
marker passes. The attempted operator source remains **uncommitted WIP**
in the safe worktree and must not be mistaken for an admitted live path.

## Counterexample and evidence scope

- An initial implementation made the new focused tests 11/11 green and
  the affected operator file 388/388 (122.04 s), but its two post-exec FD
  lists compared only FD number/type and checked pipe handles later once.
  Read-only patch review identified this as below the frozen two-exact-map
  witness. Neither green result authorizes acceptance.
- With two raw-generation-bracketed FD/type/pipe-handle snapshots, the
  focused new gate was unstable: one observed run was 1 positive failure
  `fake_a_exec_fd_witness_unavailable` plus 10 passes, while an immediate
  rerun was 11/11. In 30 direct marker invocations, 17 failed at the FD
  witness. OS inspection showed transient extra type-1 VNODE FDs during
  framework Python startup.
- A diagnostic 50 ms delay *outside the source*, used only to inspect the
  stable state, yielded 30/30 `fake_a_exec_image_mismatch`. The stable OS
  executable and argv[0] changed from the frozen canonical
  `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12` to
  `/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python`;
  other argv positions remained the same. This time-dependent OS image/argv
  observation is consistent with a further launcher transition, although
  this probe does not establish its exact mechanism. EOF plus one momentary
  image observation cannot honestly prove the frozen single-image target.
  A sleep or ignored FD
  would hide, not fix, this counterexample.
- The current strengthened source was **not** given a final full operator
  pass. `git diff --check` was clean; only the operator WIP and the
  unrelated pre-existing `output/graduate_application_report/` were dirty
  before this report. 0 Ollama, model bytes, HTTP, Safari and B Send were
  used. There is no valid new FD-resource maximum or product gain to claim.

The focused counterexample can be rechecked without model/network calls:
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s -p no:cacheprovider --tb=short test_p4_b_non_b_parity_live_operator.py -k synthetic_a_exec`.
One observed strengthened-source run had 1 positive FD-witness failure and
10 passes (6.31 s); an immediate rerun had 11 passes (6.06 s). This command
is a diagnostic on exposed development tests, not a frozen holdout rerun.

An additional isolated native-target feasibility check rules out the easy
assumption that only framework Python is affected: immediately after
CLOEXEC EOF, `/bin/cat` and `/usr/bin/grep -q -x R` each yielded two exact
stdio-only FD snapshots in only **4/10** bounded trials; the other trials
could observe startup VNODE FDs. Those are exploratory probes, not an
amendment or product result. A prospective native-target correction must
also freeze a bounded stable-observation policy that records every interim
OS snapshot and rejects unexpected inherited **control pipe** handles; it
may not merely sleep for a chosen interval or ignore the observed failures.

## Decision boundary

The frozen Python target is **NO-GO**. Keep the tests/failure and WIP; do
not alter the frozen file retroactively or mark an EOF/image flag as PASS.
A separately reviewed prospective amendment may choose a stable, fixed
native no-network executable, with exact argv/release behavior and the
same two final OS FD-handle snapshots inside a bounded observation phase.
Such a target needs its own isolated
feasibility evidence, red-contract update **before** source adaptation,
then focused/full regression and patch review. Runner discovery, true
Ollama binary/model identity, T0+90 physical stop, Web graph and Safari
remain outside this failure and are not authorized.
