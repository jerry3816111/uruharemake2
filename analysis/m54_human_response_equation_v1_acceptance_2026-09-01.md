# M54 Human Response Equation V1 Contract Acceptance · 2026-09-01

## Decision

**M54 contract gate: PASS.** UruhaBrain now has one machine-checkable, versioned candidate equation
contract and a read-only runtime adapter. This establishes that the next real-person experiment has a
defined set of variables, outputs, interventions, updates, provenance rules, and claim boundaries.
It does **not** establish that the equation predicts a real person or describes a biological brain.

## What changed

- froze the candidate prediction and update equations;
- defined nine inputs: current observable input, observable history, structured memory, transient state,
  relationship state, goal/need state, observable context, person parameter, and uncertainty/calibration;
- separated primary observable-behavior distribution, secondary desired-response policy distribution,
  and downstream Japanese utterance;
- required every variable to declare evidence, epistemic status, measurement, uncertainty, persistence,
  interventions, runtime paths, and forbidden claims;
- added a deterministic single-variable intervention interface and connected graph payload;
- added an opt-in M54 runtime/Web overlay that records hashes and availability only. It adds no model
  call, reply decision, long-term-memory write, or new psychological inference.

## Deterministic and compatibility evidence

- contract JSON validation: PASS;
- focused M54 tests: **10/10 passed**;
- selected M1–M53 compatibility set plus M54: **329/329 passed** in 46.43 seconds;
- warnings: three pre-existing Python dependency deprecation warnings;
- contract and snapshot hashes are deterministic;
- tests verify fail-closed unknown variables, no factual promotion of inference, one-target-only
  intervention, connected graph, unique trace materialization, and unchanged visible reply.

The 329-test run is a selected compatibility suite reconstructed from the last M53 scoped run. It is
not represented as every historical test in the repository.

## Isolated Safari runtime evidence

Environment:

- local Safari, `127.0.0.1:7895`, isolated temporary memory/session paths;
- session `20260901_050820_8ba6d32e`;
- one real text turn, no formal database and no external deployment.

Observed turn:

```text
User: 方法はいらない。ただ聞いてほしい。
Uruha: うん。今は方法出さないから、そのまま話して。そのくらいでいいだろ。
```

Evidence observed in the page and local trace:

- the visible reply was natural Japanese and selected `listen_presence`;
- M47 correctly prevented practical-help generation, and M45/M51 were not invoked;
- the M54 card changed from initialization coverage **1/9** to current-turn coverage **7/9**;
- `S[t]` and `C[t]` stayed `unavailable_not_inferred` instead of being fabricated;
- the secondary policy distribution was normalized and led with `listen_presence = 0.6832`;
- the primary real-person behavior distribution stayed `unavailable_not_fabricated`;
- node `human_response_equation_v1_m54` appeared exactly once before the utterance path;
- the M54 overlay reported reply/decision unchanged, zero added model calls, and no long-term-memory
  write;
- the underlying turn completed within the recorded local runtime budget (1.4361 seconds); this is one
  warm fast-path observation, not a latency distribution;
- the test conversation and memory database were under `/tmp/uruha-m54-safari.LK6PnO`; Git status
  showed no test-generated modification to the formal annotation data.

## What passed and what did not

Passed:

1. Equation V1 is explicit enough to be falsified rather than retrofitted after seeing future data.
2. Runtime sources can be measured without changing the existing conversational decision.
3. Missing variables remain visible as missing.
4. A teacher can see the proposed variables and the actual node lineage in the real Web runtime.

Not yet passed:

1. No timestamped real-person longitudinal pilot has been coded.
2. No primary observable-behavior probability distribution has been produced before language output.
3. No unseen-future B0–B5/Ours comparison exists for Equation V1.
4. No independent coder reliability, oracle substitution, causal ablation, second-person transfer, or
   second-model replication exists for this equation.
5. This is not evidence of private mental-state truth, general human understanding, LLM superiority,
   subjective consciousness, biological equivalence, or production readiness.

## Next dependency

Start **M55 Timestamped Real-Person Longitudinal Pilot**. M55 must create a provenance-bounded codebook
and pilot in which inputs stop at a declared cutoff and labels come only from later observable behavior.
Equation V1 must not be tuned on the sealed future rows. If a variable cannot be coded reliably, M55
must report or remove it before M56 rather than filling it with model intuition.

## Goal-service note

The project handoff and roadmap now carry the M54–M75 objective as the highest-priority execution
target. The desktop Goal API could not replace the text of an existing unfinished paused Goal and only
supports complete/blocked status updates; the old Goal was therefore not falsely marked complete.
This interface limitation does not change the repository execution target, but the app-level Goal text
still requires a user-side replace/resume action if autonomous Goal scheduling must display the new text.
