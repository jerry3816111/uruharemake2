# M56.6 Single-writer Formal Generation Gate Acceptance

Date: 2026-09-03
Decision: **PASS for the bounded engineering variable; live formal generation remains DENIED**

## What changed

M56.5 could safely continue one interrupted process, but it did not own an authorized run exclusively. Two local
processes could validate the same `run_id`; the exclusive invocation-intent write prevented a clean double call, but
the losing process could still write a terminal failure while the first process was healthy. M56.6 changes only that
concurrency boundary:

- it validates the standard permitted run before creating any lock artifact;
- it resolves one fixed lock file inside the run's private telemetry compartment;
- it rejects symlinks, non-regular files, wrong ownership, multiple hard links and group/world access;
- it obtains a non-blocking operating-system advisory exclusive lock and rechecks descriptor/path identity;
- only the owner delegates to unchanged `execute_resumable_formal_generation(run_id)`;
- a simultaneous contender is rejected before delegate entry and cannot write an M56.5 terminal failure;
- normal return, Python exception or process death releases lock ownership; the persistent empty/stale lock file is
  not treated as authority.

The public execution surface is exactly `execute_single_writer_formal_generation(run_id)`. There is no lock,
provider, prediction, outcome, readiness, retry or fallback injection.

## Contention and failure evidence

| Check | Result |
|---|---|
| two threads cross the pre-lock barrier for one run id | one M56.5 delegate entry; one fail-closed rejection |
| additional transport by contender | 0 |
| terminal generation-failure artifact by contender | absent |
| lock held for whole delegate | second acquisition rejected while delegate is active |
| delegate raises | original exception preserved; lock immediately reacquirable |
| holder exits with `os._exit(19)` | operating system releases ownership; existing lock file reacquirable |
| different run ids | independent locks; both can be held concurrently |
| stale lock-file content | does not grant or retain authority |
| symlink / hard link / wrong owner / group-readable lock | fail closed |
| unchanged forged M56.5 full path | exactly 180 mock calls; complete release; outcome access 0; no failure artifact |

This is a cooperative one-host lock. It is not a distributed lock and does not protect against an administrator or
attacker who can rewrite code, directories, or file ownership.

## Retained development failures

- The first focused invocation used Homebrew Python 3.12, which had no `pytest` module. No project test was collected
  or executed. The run was repeated with the repository's existing Python 3.12 pytest executable; the environment
  failure is not counted as a code result.
- The first Safari downward scroll reused an accessibility element id from an older tree and was rejected by the
  Computer Use service. The page was not changed. A fresh accessibility tree was fetched before the successful
  scroll and visual check.

## Tests

- focused M56.6 suite: **15/15 passed** in 1.64 seconds;
- direct M54–M56.6 compatibility: **184/184 passed** in 23.88 seconds;
- selected M1/M2/V7/V9/M54–M56.6 compatibility: **249/249 passed** in 25.74 seconds;
- Python compilation, JSON parsing, frozen dependency hashes, implementation-freeze hashes and diff check: PASS;
- current formal model calls: **0**;
- current target-outcome access: **0**;
- current formal commitment, scoring release and result: **absent**.

Contract hash: `5a3e1ea8a0923bd4ddc77816391c7c9e77ba46eae1b982ac2100dcacc8f7dd59`

Live audit hash: `cb0115a0355e99bb7f6764dbaeeec75b379da3fd8f06d3ffb12183a832512a80`

No-call contention rehearsal hash: `50c0191b4c64add022a1256f10c9c3b01b16edfac1ef18bd8d76ea71f900e512`

## Safari graphical acceptance

The existing M56.5 local Safari test tab was reused at `http://127.0.0.1:7914/dashboard`; no tab was opened or closed
and the tab count remained 32. The read-only page has no form and visually shows:

- the pre-M56.6 defect: process A is healthy while duplicate process B can poison the same run;
- the new run-id single-writer lock and unchanged M56.5 delegate;
- one owner versus a contender rejected with 0 extra calls and 0 terminal-failure writes;
- normal exception release, operating-system release after process death, and the non-authoritative stale lock file;
- the synthetic two-contender result and the scientific evidence boundary.

Both the upper flow and lower contention/boundary sections were readable without horizontal overflow:

- `analysis/m56_6_safari_single_writer_flow_2026-09-03.jpeg`
- `analysis/m56_6_safari_contention_boundary_2026-09-03.jpeg`

The local port 7914 service was stopped after acceptance. The remaining read-only Safari tab is safe to close and
does not hold private data, a lock, or execution state.

## Honest boundary and long-term contribution

M56.6 removes a concrete way that one accidental duplicate launch could waste a single-use, human-authorized formal
run or invalidate healthy M56.5 checkpoints. It strengthens the future longitudinal comparison's operational
reliability without changing the scientific variable, model behavior, resource accounting, or scorer.

It does **not** add human labels, real temporal rows, fresh model predictions, actual resource measurements, an M56
score, Uruha predictive evidence, Equation V1 validity, a solved human-response equation, full-pipeline readiness or
production readiness. The live state remains V7 0/18 and 0/18, V9 0/30 and real temporal rows 0/30. The next
non-substitutable scientific dependency remains two different humans completing the frozen V7 reliability pilot.
