# M56.8 Durable-Release-Gated Formal Scoring Acceptance

Date: 2026-09-03
Decision: **PASS for the bounded authorization-chain variable; live formal scoring remains DENIED**

## Problem proved before the change

The frozen M56.4 full isolated-file test writes only M56.2/M56.3 artifacts, calls
`execute_formal_scoring(run_id)`, opens the test outcome and creates a result.  It contains no M56.7 mode or
durable-generation release.  M56.7 itself explicitly retained this gap.

This is valid historical M56.4 engineering evidence, but it means the old scorer cannot by itself certify that its
predictions passed the newer Mac file-and-directory full-sync boundary.

## What changed

M56.8 adds one new sanctioned entry point:

`execute_durable_release_gated_formal_scoring(run_id)`

It accepts only `run_id`.  Before private outcome access it:

1. revalidates the unchanged M56.4 210-row/resource pre-score state;
2. requires the exact standard-path M56.7 mode, including lease and filesystem-device binding;
3. requires the exact M56.7 durable release binding the same submission, prediction commitment, M56.3 scoring
   release and generation call count;
4. refuses to add M56.8 authority if an M56.4 access receipt, score report or result already exists without the gate;
5. commits an immutable M56.8 gate with file and parent-directory `fsync` plus macOS `F_FULLFSYNC`;
6. only after that durable commit delegates to the unchanged frozen M56.4 scorer.

The M56.4 scorer, metrics, thresholds, B5/Ours contrast, outcome key, prediction contents, model settings and human
gates were not changed.

## Fail-closed and full-path evidence

| Check | Result |
|---|---|
| historical M56.4 result without M56.7 reproduced | PASS; proves the original gap |
| missing M56.7 mode/release | rejected before outcome load |
| mutated M56.7 mode | rejected before outcome load |
| mutated M56.7 release | rejected before outcome load |
| existing M56.4 result without earlier M56.8 gate | rejected; no retroactive certification |
| changed existing M56.8 gate | rejected before outcome load |
| full actual M56.7 forged-generation entry | 180 mock generation calls, zero scorer calls |
| gate durability before outcome loader | observed `artifact_commit_complete` before loader invocation |
| M56.4 seven-condition score/report | valid and unchanged after M56.8 gate |
| identical restart | same gate hash and result commitment; no new generation call |

The full-path fixture is real state-machine execution in a temporary private root, but its data and model responses
are forged deterministic test material.  It is not a formal result.

## Fixture cost and score-semantic invariance

The same deterministic forged 30-row score fixture was run three times per condition.  M56.4 and M56.8 produced
identical seven-condition metrics, identical primary B5/Ours comparison and identical decision in all three repeats.

| Condition | Median wall time | Scorer model calls |
|---|---:|---:|
| frozen M56.4 direct scoring | 0.597449 s | 0 |
| M56.8 release validation + durable gate + unchanged M56.4 | 0.747182 s | 0 |
| added by M56.8 | **0.149733 s** | **0** |

Raw values are retained in
`analysis/m56_8_durable_release_gated_scoring_fixture_cost_2026-09-03.json`.  This is local deterministic fixture
cost, not formal model latency or production throughput.

## Tests

- focused M56.8 suite: **10/10 passed** in 8.50 seconds;
- direct M54-M56.8 compatibility: **209/209 passed** in 44.58 seconds;
- selected M1/M2/V7/V9/M54-M56.8 compatibility: **274/274 passed** in 46.81 seconds;
- Python compilation, JSON parsing, frozen dependency hashes, implementation-freeze hashes and diff check: PASS;
- current formal model calls: **0**;
- current target-outcome access: **0**;
- current formal score/result: **absent**.

Contract hash: `ee60d7c4179d347418d24467f7a3b0656cafab14f127cde4b8853f8280cd3316`

Live audit hash: `1e3bfca929d7cb83032ac9c9e76c33dc7302d359d3378732c34b7b8916368fa2`

No-call rehearsal hash: `5ddd084cdb4168493bda707cf7b7b91bd672bad7e40677f51d72822894827b1e`

## Safari graphical acceptance

Safari reused the existing M56.7 local test tab at `http://127.0.0.1:7916/dashboard`.  It had 33 tabs before and
after acceptance; no tab was opened or closed.  The read-only page has no form and visibly explains:

- the five-step M56.4 pre-score -> M56.7 mode -> durable release -> M56.8 gate -> private score chain;
- the actual before/after difference;
- why a result cannot receive authorization after the answer was already opened;
- V7 `0/18 + 0/18`, real rows `0/30`, zero formal calls/results;
- the same-host cooperative, non-cryptographic boundary.

The upper flow and lower retroactive/boundary sections were readable without horizontal overflow:

- `analysis/m56_8_safari_authorization_chain_2026-09-03.jpeg`
- `analysis/m56_8_safari_retroactive_boundary_2026-09-03.jpeg`

The local port 7916 service was stopped after acceptance.  The remaining read-only Safari tab is safe to close and
does not hold a lock, private outcome or execution state.

## Honest boundary and long-term contribution

M56.8 closes the application-level evidence-chain gap between crash-safe formal generation and formal scoring.  A
future sanctioned score can now prove, before answer access, which exact durable generation release authorized it;
a historical result cannot be relabeled after the fact.  This improves reproducibility and protects the eventual
candidate human-response-equation comparison from an untraceable execution path.

It does **not** cryptographically prevent a same-host caller from invoking historical M56.4 or reading files when it
already has permission.  Such a result lacks M56.8 authority but the read itself is not physically blocked.  It also
does not add human labels, real temporal rows, fresh formal predictions, actual model performance, Equation V1
validity, a solved human-response equation, full-pipeline evidence or production readiness.

The live state remains V7 `0/18 + 0/18`, V9 and real rows `0/30`, with no formal call, outcome access, commitment or
result.  Two different humans completing the frozen V7 pilot remain the next non-substitutable scientific
dependency.
