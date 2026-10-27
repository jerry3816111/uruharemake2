# P4-B non-B early-A-death controlled negative result (2026-10-27)

Decision: **PASS only for the isolated cooperative `/bin/cat` negative;
real/live remains `REVIEW_REQUIRED` / NO-GO**. No product source was changed.
The frozen test-side interleaving is at
`research/p4_b_non_b_early_a_death_negative_freeze_2026-10-27.md`;
the prior read-only gap is at
`analysis/p4_b_non_b_early_a_death_orphan_window_review_2026-10-27.md`.

## Before, one controlled variable, and direct observation

Before this test, the accepted runner suite had 19 focused passes and no
case where A died between spawning a cat and P's first runner identity.
`known_runners` is populated only after that first P OS image snapshot; an
empty cleanup set cannot establish unknown-descendant absence. The new test
creates one controlled **A-death-before-P-identity** interleaving: a
parent-only wrapper kills A after a private witness and withholds the cat
PID from P's enumeration. The accepted `/bin/bash` → `/bin/cat` target and
product code remain unchanged.

On the first unchanged-source run, the wrapper independently observed one
exact `/bin/cat` with stable PID/start, PPID=A, stdio-only FD map and fd0
pipe-handle equal to A's private stdin. It confirmed A was the exact live,
unreaped P child, sent SIGKILL to A, then returned **no cat PID** to P.
The operator's own `observe_process` spy saw zero cat images. The test
rejected a run that never reached this barrier; it did not count simple
zero-child detection as a pass.

The operator returned `fake_runner_spawn_unavailable`, not a positive
receipt. Before any test-side emergency cat signal, the original cat
PID/start generation was gone (PPID changes alone did not count). All 11
direct P children were reaped, the caller's FD count returned to its prior
value, and fail-on-touch run/model path sentinels and forbidden clock were
not accessed. The test-side exact-generation emergency signal path was not
needed for this passing observation.

| Check | Result | Scope |
|---|---:|---|
| New frozen negative, first unchanged-source execution | 1/1 PASS, 0.78 s pytest | One controlled macOS interleaving |
| Adjacent `-k synthetic_runner` regression | 20/20 PASS, 2.03 s pytest | Includes prior positive/fault contracts; 404 deselected |
| Product source changes | 0 | Test-only evidence, no new stop mechanism |
| Model/HTTP/Safari/formal data | 0 / 0 / not run / not read | No real runner or product UI inference |

The runs used `.venv/product_checks/bin/python -m pytest -q -s -p
no:cacheprovider test_p4_b_non_b_parity_live_operator.py` with the focused
`-k early_a_death_before_operator_identity` and then `-k synthetic_runner`.
Compilation and `git diff --check` passed. A same-model read-only review
found no blocking signal-safety issue before the first run; it is not an
independent human or external acceptance.

## What this does and does not close

The result is evidence that the current P `finally` closes its private stdin
writer soon enough for this **cooperative cat** to exit even when its parent
A dies before P learns the cat PID. It is **not** evidence that cleanup knows
which unknown runner existed: `known_runners` remains empty in this path,
and the operator cannot issue an identity-bound stop or prove run-wide
containment. A real Ollama runner might keep other resources, ignore EOF,
change process group, or survive reparenting. The test's private witness is
not product authority. Do not promote this to installed model identity,
physical T0+90 stop, B Send, fresh generation, Web/Safari, or the human-
response research claim.

Next dependency: retain real/live `REVIEW_REQUIRED` until a separately
reviewed run-wide containment or equally strong installed-runner witness
closes the unknown-descendant window. Do not repeat fake tests indefinitely
to infer that proof; move to a separately scoped, independent product task
while real containment remains unresolved.
