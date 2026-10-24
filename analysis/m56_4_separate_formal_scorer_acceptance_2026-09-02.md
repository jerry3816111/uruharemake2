# M56.4 Separate Formal Scorer and Result Commitment Acceptance · 2026-09-02

## Decision

**Separate-scorer engineering gate: PASS. Current formal scoring: DENIED. Formal result: ABSENT.**

M56.3 ended at a post-commit release: a future prediction matrix could be outcome-blind, resource-audited,
complete, immutable, and ready for a different capability to read the withheld answers. It still lacked a
frozen formal scorer. M56.4 adds that scorer without changing M54–M56.3 frozen files or opening the current
outcome compartment.

V7 remains `0/18 + 0/18`; V9 and real temporal rows remain `0/30`. The only valid live outcome is therefore
denial with zero scorer outcome access, zero scorer model calls, and no score report or result commitment.

## What actually changed

### Fairness is checked before answers are opened

`execute_formal_scoring(run_id)` is the only public formal-scoring entry point. It accepts no predictions,
outcomes, thresholds, metrics, token-sensitivity override, result, readiness, provider, or model. Before it
opens `scoring/`, it revalidates:

- the M56.2 activation request, consumed receipt and single-run lease;
- the M56.3 210-task schedule, complete submission, prediction commitment and scoring release;
- the exact Equation artifacts, model/hardware snapshot and all outcome-blind content bindings;
- the formal call ledger against every non-B0 prediction and every non-empty B4-summary resource row;
- zero retry, zero fallback, zero generation outcome access and the actual B5/Ours prompt-token difference.

If the B5/Ours difference exceeds the frozen 5% threshold, M56.4 stops before outcome access. There is no
caller boolean that can declare the sensitivity test passed. A separately named prospective sensitivity
freeze would be required before any answer is opened.

### The private scorer cannot regenerate or reinterpret predictions

Only after the pre-score audit passes does the scorer atomically commit one logical outcome-join receipt and
open the standard `private_outcome_key.json` plus `split_report.json`. It checks their activation hashes,
packet hash, sample order, candidate-label order, confidence, cutoff-before-observation-before-source time,
zero future leakage, and denial of generation access.

It then deterministically reports all seven frozen conditions and keeps the frozen primary comparison:

`B5_STRUCTURED_HISTORY` versus `OURS_HYBRID`

The co-primary Brier and NLL paired bootstrap, sign-flip tests, top-1 noninferiority, exact McNemar test,
condition metrics, and descriptive ECE use the already frozen M56 values. No post-result baseline, metric or
threshold selection exists. Scoring performs zero model calls.

### Positive and negative results are both immutable

The private score report contains aggregate condition metrics, preregistered paired deltas, opaque sample IDs,
resource totals, hashes, and one bounded `formal_gate_pass` or `formal_gate_fail_retained` decision. It excludes
raw source content, raw model responses, reasoning traces and private mental-state assertions. A second SHA-256
commitment binds the report and decision.

If the process stops after the report write but before the result commitment, an identical invocation may
validate the same deterministic report and finish the commitment. It cannot replace predictions, outcomes,
rules or the decision. A mutated existing report is rejected.

## Fail-closed evidence

The focused suite verifies:

- the public formal API exposes only `run_id`;
- the current live state and a missing run directory produce no outcome access or result artifacts;
- a test-only 30-row real-shaped packet exercises 210 committed predictions, 180 no-retry mock call rows,
  seven-condition metrics, frozen B5/Ours comparison and result commitment in an isolated temporary directory;
- the new primary-comparison output exactly matches the pre-existing frozen scorer mechanics;
- token imbalance blocks before `load_outcome_inputs` can be called;
- a non-empty B4 history contributes its separate summary call before prediction calls and raises the audited
  mock call count from 180 to 181 without being lost or merged into prediction cost;
- changed schedule/submission/commitment/release/call-ledger data, private outcome key, split report, label,
  timestamp or immutable result fails closed;
- repeat finalization accepts only byte-equivalent canonical content;
- forbidden raw/source/reasoning fields and excess production, deployment or broad-equation authority are absent;
- the separate no-call rehearsal has zero humans, calls, outcome access and formal authority.

The forged data, predictions, call resources and temporary score are test fixtures only. They do not become a
tracked or live formal result and provide no human or model-performance evidence.

## Tests

- focused M56.4 suite: **17/17 passed**;
- direct M54–M56.4 compatibility suite: **154/154 passed**;
- selected M1/M2/V7/V9/M54–M56.4 compatibility suite: **219/219 passed**;
- Python compilation, JSON validation and diff check: PASS;
- contract and seven frozen dependency bindings: PASS;
- implementation freeze: PASS;
- formal scorer model calls: **0**;
- formal scorer target-outcome access: **0**;
- formal score report: **absent**;
- formal result commitment: **absent**;
- scorer contract hash:
  `3c374130102335515114e3a560f3103e06dbc392f46740d6617c7a49b3bebd6a`;
- live audit hash:
  `67c23e06c53718dc4f86e0664d8c25bd26a095738e8e47f89e584211e4243d3d`;
- no-call rehearsal hash:
  `2eeba5c58cf2baa9c13b5c84251f0d196d232b10b08dfd7acb841888104a586f`.

## Safari graphical acceptance

Safari reused the existing M56.3 tab and navigated it to `http://127.0.0.1:7912/dashboard`. Safari had **30
tabs** before and after this acceptance; no tab was created or closed and no form was submitted.

The page visibly showed:

1. `DENIED NOW`, V7 `0/18 + 0/18`, prediction release 0, answer reads 0 and formal result 0;
2. six mandatory stages from prediction commitment through result commitment;
3. the B5/Ours 5% resource gate before the private outcome boundary;
4. all seven conditions, fixed B5 versus Ours comparison and retained negative results;
5. V9 `0/30`, real rows `0/30`, scorer accesses/calls/result all zero;
6. the exact evidence boundary in ordinary language.

No visible horizontal overflow was observed at desktop width. Evidence:

- `analysis/m56_4_safari_prescore_boundary_2026-09-02.jpeg`
- `analysis/m56_4_safari_scoring_boundary_2026-09-02.jpeg`

The local server was stopped after capture. The reused Safari tab is read-only and can be safely closed; it
holds no formal private data or state.

## Exact remaining boundary

M56.4 proves only that a future already-authorized, already-committed formal prediction matrix has a concrete,
fail-closed, resource-gated scoring and scoped-result commitment path. It has not scored real predictions or
accessed real outcomes. If an actual run exceeds the 5% token threshold, a separately frozen prospective
exact-token sensitivity execution remains required before scoring can continue.

As with M56.2/M56.3, SHA hashes are application-level drift controls, not digital signatures against an attacker
who can rewrite all code and local files. Test-only fully consistent forged files can exercise mechanics but
cannot be substituted for the standard human activation chain.

The next non-substitutable dependency remains two different humans completing V7. Until V7→V9→M55 produces 30
valid real cutoff-to-future rows, this work cannot establish real-person predictive validity, Equation V1
validity, Ours superiority, private mental truth, a solved human-brain equation, full-pipeline readiness or
production readiness.
