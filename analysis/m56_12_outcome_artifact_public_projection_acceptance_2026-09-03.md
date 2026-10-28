# M56.12 Outcome-Derived Artifact Containment and Public Projection Acceptance

Date: 2026-09-03
Decision: **PASS for a cooperative allowlisted run-specific public projection; live formal scoring remains DENIED**

## Problem proved before the change

M56.10 intentionally embeds the complete score report in its private full-sync checkpoint. Existing live pages show
only global pre-formal zeros; none provides a sanctioned run-specific state view. An isolated forged 30-row run
showed that the naive workaround—serializing the checkpoint and canonical report—would expose:

- 57,024 bytes with default JSON serialization in the initial probe;
- 60 sample-id occurrences and 60 primary pair-record occurrences;
- 14 condition-metric blocks, three outcome-key-hash occurrences and two decisions.

The probe is retained in
`analysis/m56_12_prechange_naive_private_projection_probe_2026-09-03.json`. It proves that the artifact is sensitive
and that a safe run-specific projection was missing. It does **not** show that an existing production route leaked
data.

## Single changed variable

M56.12 changes only the public projection boundary for outcome-derived scoring artifacts. The frozen M56.10 scorer,
checkpoint, report, metrics and decision do not change. Four new sanctioned functions accept only `run_id`:

- `build_public_scoring_projection(run_id)`;
- `build_public_log_record(run_id)`;
- `build_public_telemetry_record(run_id)`;
- `render_public_dashboard(run_id)`.

They validate the complete private state internally, then return/render the same exact allowlisted projection. No
function accepts a checkpoint, report, metric, decision, result or readiness payload from the caller.

## What may cross the membrane

The public projection contains only a coarse phase, six artifact-existence booleans, whether a result commitment
exists, retry/fallback zero, an explicit redaction policy, a claim boundary and a hash of the already-public
projection. It does not contain the raw run id.

The seven frozen phases are:

1. pre-outcome not started;
2. mode committed, no join intent;
3. join incomplete with outcome access honestly unknown;
4. terminal ambiguous, no result;
5. private checkpoint committed;
6. private report committed;
7. formal result committed, while score and decision remain redacted.

All seven states passed. Impossible ordering, a changed private report, checkpoint/report mismatch, a modified
projection or a forbidden injected field fails closed.

## Attributable result

The controlled rehearsal used canonical JSON for both sides:

| Temporary forged completed run | Before: naive private serialization | After: validated public projection |
|---|---:|---:|
| UTF-8 bytes | 52,458 | **1,225** |
| sample-id occurrences | 60 | **0** |
| primary pair-record occurrences | 60 | **0** |
| condition-metric blocks | 14 | **0** |
| outcome-key-hash occurrences | 3 | **0** |
| decision occurrences | 2 | **0** |
| private-canary hits across projection/log/telemetry/HTML | not bounded | **0** |

The byte reduction is 97.66%; this is a redaction/shape result, not compression performance. Projection, log and
telemetry records were byte-identical. The saved rehearsal is validated before the graphical page renders:
`analysis/m56_12_outcome_artifact_public_projection_result_2026-09-03.json`.

Contract hash: `300b1a58039c9f00bfe49239f544f5a01106a0e015be2e7d6e87b5464be57b90`

Rehearsal hash: `9e403f819d24f02bb0121fa88bddd7aa064347002896e6de6f6b9ef12bb95404`

Live audit hash: `2548edc008d17f9fc04c98d7d6fbcb13e090a9df55f69fb04ec9b70ef9549ae8`

## Cost

Seven repetitions on one completed temporary forged run measured:

| Operation | Median wall time |
|---|---:|
| naive serialization, without validation | 0.000484 s |
| one validated state-only projection | **0.143658 s** |
| three independent dashboard/log/telemetry refreshes | **0.433071 s** |

The safe path is intentionally slower because each call rereads and verifies the complete private state. The
three-surface measurement performs three independent validations; it is not optimized or a production throughput
claim. No scorer model was called. Raw measurements are in
`analysis/m56_12_outcome_artifact_public_projection_fixture_cost_2026-09-03.json`.

## Tests

- focused M56.12 suite after freeze: **9/9 passed** in 12.52 seconds;
- direct M54-M56.12 compatibility: **258/258 passed** in 82.44 seconds;
- selected M1/M2/M6/V7/V9/M54-M56.12 compatibility: **323/323 passed** in 88.77 seconds;
- Python compilation, JSON parsing, contract/dependency/freeze hashes, rehearsal hash and audit hash: PASS;
- current formal model calls: **0**;
- current real target-outcome access: **0**;
- current formal score/result: **absent**.

## Safari graphical acceptance

Safari reused the existing M56.11 tab and navigated it to `http://127.0.0.1:7920/dashboard`. The count remained 33
tabs; none was opened or closed. The read-only page visibly showed:

- 52,458-byte naive canonical payload versus 1,225-byte safe projection;
- 60 sample ids, 60 pair records, 14 metric blocks and two decisions before, all zero after;
- one allowlist shared by dashboard/log/telemetry and zero private-canary hits;
- the private -> validate/allowlist -> public membrane;
- a completed result phase while score/decision stay private;
- zero real outcome reads and the same-host/future-consumer/scientific limits.

The page had no form or visible horizontal overflow:

- `analysis/m56_12_safari_public_projection_comparison_2026-09-03.png`
- `analysis/m56_12_safari_public_projection_boundary_2026-09-03.png`

The 7920 local server was stopped. The remaining read-only tab is safe to close.

## Failure analysis and honest boundary

No historical production leak was found or claimed. M56.12 prevents accidental exposure only when application
consumers use its sanctioned API. Same-host code can still read private files or call old functions directly. This
is not OS sandboxing, encryption, a malicious-host boundary, proof that every future consumer complies, or a
multi-process least-privilege architecture.

The authoritative scientific state remains V7 `0/18 + 0/18`, V9 and real temporal rows `0/30`, with no formal model
call, real outcome access, prediction/result or human evidence. M56.12 does not improve prediction, memory,
pragmatic understanding, Japanese output or persona. It cannot prove Equation V1, Uruha advantage, a solved human
response equation, full-pipeline value or production readiness.

## Long-term contribution and next milestone

M56.12 makes a future Equation V1 experiment safer to observe: scoring progress can be shown without publishing the
per-sample evidence used to judge the equation. This protects scientific blinding and negative-result integrity but
adds no evidence that the candidate equation is accurate.

The next safe single-variable milestone is **M56.13 Unidirectional Public Snapshot Boundary**. Its pass condition is
that a private exporter durably emits only a validated M56.12 projection into a separate public compartment, while
dashboard/log/telemetry consumers can run with private-root access disabled and still render the same state. This
would reduce accidental capability, but still would not claim malicious-host security. The next non-substitutable
scientific dependency remains two different humans completing the frozen V7 pilot.
