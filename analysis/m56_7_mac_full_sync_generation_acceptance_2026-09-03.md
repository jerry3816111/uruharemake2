# M56.7 Mac Full-Sync Generation Commit Acceptance

Date: 2026-09-03
Decision: **PASS for the bounded engineering variable; live formal generation remains DENIED**

## What changed

M56.5 synchronized each JSON file but did not synchronize the directory entry that names a newly created intent,
checkpoint, submission, ledger, commitment or release.  M56.6 prevented duplicate local writers but intentionally
left that write path unchanged.  After an abrupt power or kernel loss, a model transport could therefore have
finished while the corresponding checkpoint name was missing after restart, leaving an intent-only terminal state.

M56.7 changes only the stable-storage completion boundary on the bound Mac:

- it revalidates the permitted run and holds the unchanged M56.6 single-writer lock;
- it refuses to retroactively certify any pre-existing M56.5 generation state that lacks the M56.7 mode;
- a context-local dispatcher routes M56.5 JSON writes through the M56.7 writer only inside the new entry point;
- each payload completes before file `fsync` and macOS `F_FULLFSYNC`;
- the parent directory then completes `fsync` and `F_FULLFSYNC` before the write returns;
- the checkpoint barrier therefore completes before M56.5 may remove its matching intent;
- an immutable pre-transport mode and post-validation durable release bind the unchanged M56.5 hashes.

The new execution entry is exactly `execute_full_sync_formal_generation(run_id)`.  It has no writer, provider,
prediction, outcome, readiness, durability, retry or fallback injection.  Calls outside the M56.7 context retain the
frozen writer and cannot claim M56.7 evidence.

## Mechanism and recovery evidence

| Check | Result |
|---|---|
| real current filesystem file `fsync` | PASS |
| real current filesystem file `F_FULLFSYNC` | PASS |
| real current filesystem directory `fsync` | PASS |
| real current filesystem directory `F_FULLFSYNC` | PASS |
| payload → file sync → file full-sync → directory sync → directory full-sync → commit order | PASS |
| unsupported full-sync | rejected before M56.5 delegate and before transport |
| old M56.5 state without M56.7 mode | rejected before transport |
| checkpoint written before intent-clear fault | checkpoint + intent retained; restart reused it without recall |
| forged full path | 211 step checkpoints, 180 mock calls, 0 remaining intents |
| durable artifact commits on forged full path | 400 file-and-directory commits |
| unchanged M56.4 pre-score path | PASS; outcome access 0 |
| repeated completed invocation | validation only; no additional model call or write |

No actual power cut was performed.  The evidence proves syscall availability and application ordering, not every
storage controller's behavior during a real outage.

## Measured fixture cost

The same deterministic 30-row forged fixture was run three times per condition.  Both conditions performed exactly
180 mock calls; the only comparison variable was the write barrier.

| Condition | Median wall time | Allocated bytes | Files |
|---|---:|---:|---:|
| M56.6 file `fsync` only | 1.124688 s | 3,252,224 | 228 |
| M56.7 file + directory `fsync` / `F_FULLFSYNC` | 3.717044 s | 3,260,416 | 230 |
| Added by M56.7 | **2.592356 s** | **8,192** | **2** |

The 3.305x ratio applies only to the fast deterministic filesystem fixture.  It is not formal model latency or a
production throughput estimate; real local-model calls will dominate this synthetic runtime.

Raw fixture values are retained in
`analysis/m56_7_mac_full_sync_generation_fixture_cost_2026-09-03.json`.

## Retained development failures

- The first focused run was **12/14**, with two failures.  One test calculated an M56.5 path before installing its
  temporary private root and created exactly one fake mode at
  `analysis/local_m56_formal_execution_v1/legacy-state-no-m567-mode/`.  It contained no human data or model result;
  the exact test directory was removed and its absence was verified.  The fixture now resolves the path only inside
  the temporary-root context.
- The other failing test mocked the entire platform name to simulate missing `F_FULLFSYNC`.  That correctly caused
  the frozen upstream hardware snapshot to fail before reaching the intended barrier.  The test now faults only the
  full-sync capability function; the upstream hardware binding was not weakened.
- Safari initially had an unrelated `chatgpt.com` prompt asking to open the ChatGPT app.  `Cancel` was selected; no
  app was opened and no tab was closed.  The existing M56.6 test tab was then reused normally.

## Tests

- focused M56.7 suite: **15/15 passed** in 13.31 seconds;
- direct M54–M56.7 compatibility: **199/199 passed** in 35.83 seconds;
- selected M1/M2/V7/V9/M54–M56.7 compatibility: **264/264 passed** in 38.02 seconds;
- Python compilation, JSON parsing, frozen dependency hashes, implementation-freeze hashes and diff check: PASS;
- current formal model calls: **0**;
- current target-outcome access: **0**;
- current formal commitment, scoring release and result: **absent**.

Contract hash: `27376e8ff2321ecdcc39aa072a6b3f3d284a5242141d6eb41ad65e01a157fa0c`

Live audit hash: `33c0b9600152456e7ca6d2d7d5fef550139e5228de617b16eecbce2da62293c4`

No-call rehearsal hash: `521cf2a9e6023adf212ff170e1bf02703097119a220cebc61e95da6d4efa59bf`

## Safari graphical acceptance

Safari had 33 tabs before and after the check.  The existing M56.6 test tab was reused at
`http://127.0.0.1:7915/dashboard`; no tab was opened or closed.  The read-only page has no form and visibly explains:

- why synchronizing file contents alone does not commit a new filename;
- intent → one model transport → checkpoint → file and directory full-sync → intent removal;
- the three restart states: checkpoint, checkpoint plus intent, and intent only;
- the deterministic fixture overhead and unchanged experimental variable;
- V7 0/18 and 0/18, real rows 0/30, zero formal calls/results and the scientific evidence boundary.

The upper flow and lower restart/boundary sections were readable without horizontal overflow:

- `analysis/m56_7_safari_full_sync_flow_2026-09-03.jpeg`
- `analysis/m56_7_safari_restart_boundary_2026-09-03.jpeg`

The local port 7915 service was stopped after acceptance.  The remaining read-only Safari tab is safe to close and
does not hold private data, a lock or execution state.

## Honest boundary and long-term contribution

M56.7 closes a concrete gap between “Python returned from a file write” and “the Mac was asked to make both the file
and its name stable before continuing.”  This lowers the chance that an authorized, single-use longitudinal run is
lost specifically after a successful transport and before a recoverable checkpoint, without changing the candidate
human-response equation, any condition view or any score.

It does **not** reserve disk capacity, reproduce a real power failure, guarantee defective hardware, require the
M56.7 release inside the already frozen M56.4 scoring entry, add human labels, create real temporal rows, generate
fresh formal predictions, measure actual model performance, validate Equation V1, solve a human-response equation,
complete the full pipeline or establish production readiness.  The live state remains V7 0/18 and 0/18, V9 and real
temporal rows 0/30, with no formal call, commitment, scoring release or result.  Two different humans completing the
frozen V7 pilot remain the next non-substitutable scientific dependency.
