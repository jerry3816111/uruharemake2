# M56 Blinded Execution Capsule and Separate Scorer Acceptance · 2026-09-01

## Decision

**Execution/scoring engineering gate: PASS. Formal M56 execution: BLOCKED. Formal result: NOT CREATED.**

The frozen M56 preflight described a fair experiment, but its prediction packet still held the complete
safe history for every condition. This unit makes the rules executable: each condition receives a
capability-separated view, every prediction row must be complete and immutable before outcomes can be
opened, and a separate scorer validates the commitment before joining the private answer key.

This is not the M56 experiment. It ran no formal model calls and read no Uruha target outcome.

## What changed

### 1. Seven real information boundaries

- **B0** receives candidate labels and pre-cutoff behavior counts only. Its Laplace-smoothed frequency
  prior is recomputed and verified; it cannot be replaced by arbitrary probabilities.
- **B1** receives only the current pre-cutoff event, labels, and minimal identity. No history or persona
  summary is present.
- **B2** adds only the frozen public persona summary, still with no dynamic history.
- **B3** adds a deterministic top-four pre-cutoff retrieval.
- **B4** prediction receives only an independently completed summary artifact. Raw history remains in a
  separate summary task, and each distinct nonempty history snapshot incurs one separately audited model
  call. Empty history uses a deterministic zero-call artifact.
- **B5** receives structured complete pre-cutoff source information and no equation state.
- **Ours** receives the byte-identical source-information object and hash used by B5, plus the frozen
  Equation V1 binding and mandatory pre-outcome fit, state-snapshot, and transition-trace hashes.

A model request is materialized one task at a time. It contains only that task's authorized view; the
caller is not given the full seven-condition capsule.

### 2. Complete prediction commitment

The submission must follow packet sample order and each sample's prospectively rotated condition order.
Every sample-condition pair appears exactly once. Each row binds the view hash, uses every frozen label
exactly once, sums to one within `1e-6`, selects the frozen label-order argmax, cites only authorized
history IDs, reports zero retry/fallback, and matches the frozen model artifact, hardware, options, and
resource telemetry.

Only a fully valid submission receives a SHA-256 commitment receipt. Any later row, evidence, probability,
resource, packet, capsule, or receipt change makes scoring fail closed.

### 3. Separate outcome scorer

The scorer revalidates the contract, packet, manifest, capsule, submission, receipt, split report, and
private outcome-key hash before joining by sample ID. The outcome key must preserve exact row order and
schema, use known labels, keep the primary observed behavior among acceptable labels, report valid human
confidence, forbid generation access, and retain zero future leakage.

All seven conditions receive Top-1/Top-3, macro/weighted F1, Brier, NLL, ECE, MRR, and NDCG. The fixed
primary comparison remains **B5 versus Ours**. Brier and NLL use 20,000 paired bootstrap draws. Sign-flip
is exact through 20 pairs and uses the prospectively frozen deterministic 20,000-draw Monte Carlo method
at the formal 30-row size; it is descriptive, not a replacement for the frozen joint confidence-interval
gate. Acceptable alternative labels affect rank metrics only; the primary observed label remains the
one-hot proper-score target.

### 4. Resource accounting

- B0: zero calls;
- B1–B5: one prediction call per sample;
- Ours: one semantic model call per sample, not double-counted as a second prediction call;
- B4: every nonempty summary-build call, token, latency, and peak-memory cost counted separately;
- every condition: actual prompt/completion tokens, latency, and peak memory aggregated;
- B5/Ours prompt-token difference above 5% triggers exact-token sensitivity and prevents a formal pass
  until that sensitivity result passes.

## Acceptance evidence

### Focused and adversarial tests

- final execution-capsule suite including freeze verification: **28/28 passed**;
- direct M55/M56 compatibility suite before freeze: **55/55 passed**;
- selected M1/M2/M54/V7/V9/M55/M56 compatibility suite including freeze: **161/161 passed**;
- Python compilation: PASS;
- `git diff --check`: PASS before documentation handoff;
- contract validation: PASS, 9 dependency bindings, 7 exact conditions;
- contract hash: `b30a9ff4a99c68bc28b3c67ad8d68bff13c911d410b7578553c0c7d1e470d84a`;
- live report hash: `407489389e2b12fe69cc1a260f92adde807552416c3d3588b5dc2cdd53d1e1b9`;
- formal model calls: 0;
- target outcome access: 0;
- production-memory writes: 0.

The adversarial suite rejects unauthorized history in B1/B2, more than four B3 memories, raw history in
B4 prediction, unequal B5/Ours sources, equation artifacts in B5, missing Ours provenance, inserted
outcomes, stale hashes, task/row reordering, missing/duplicate rows, invalid probability mass, wrong
argmax, arbitrary B0 output, unauthorized evidence IDs, changed model/hardware/options, retry/fallback,
unreported calls, altered post-commitment submissions, malformed outcome rows, generation-visible keys,
wrong split hashes, and stale B4 summary artifacts.

The two-row synthetic scorer exercise validates mechanics and hand-checked proper scoring. It deliberately
remains `synthetic_engineering_only_no_formal_claim`, regardless of its numerical scores. A separate
21-pair unit confirms the prospectively fixed transition from exact to deterministic Monte Carlo
sign-flip. Neither fixture is evidence of model quality.

### Safari graphical acceptance

Safari reused the existing local M56 test tab at `127.0.0.1:7908/dashboard`. It stayed at **28 tabs**;
no tab was created or closed and no form was submitted. Top and bottom views visibly showed:

1. all seven information views, including B1/B2 no-history, B4 separately costed summary, and B5/Ours
   same-source distinction;
2. `safe packet → generation compartment → SHA-256 commitment → separate scoring compartment`;
3. four fail-closed attack examples;
4. current `V7 0/18 + 0/18`, real rows `0/30`, formal execution forbidden;
5. explicit statements that there is no formal M56 win and no proof of a human equation.

The full-width seven-card row and four-stage flow rendered without horizontal overflow at the current
Safari viewport.

## Current authorization and exact next step

- V7 independent ledgers: 0/18 and 0/18;
- V9 independently reviewed Uruha events: 0/30;
- valid real temporal rows: 0/30;
- M55 pilot complete: false;
- formal M56 execution authorized: false;
- formal M56 result: absent;
- blocker: `complete_two_independent_v7_18_slot_ledgers`.

Two distinct consenting humans must first complete the unchanged V7 pilot and pass its frozen reliability
gate. Only then can the existing V9, boundary, adjudication, and temporal compiler tools create 30 real
cutoff-to-future rows. At that point all frozen hashes must be revalidated, the missing real pre-outcome
Equation V1 fit/state/transition executor must materialize valid Ours artifacts, and the capsule can run
the seven-condition matrix before the separate scorer opens outcomes.

## Contribution and limitation

This unit removes an important alternative explanation from a future result: a condition can no longer
win merely because it saw information reserved for another condition, omitted summary costs, changed
after seeing outcomes, or used a different model environment. It therefore makes the first prospective
test of the candidate reaction equation more credible and reproducible.

It does **not** show that Equation V1 predicts Uruha, that explicit state transition beats structured
history, that the system knows private mental states, that LLMs are generally inferior, that a human-brain
equation has been found, or that the product is ready for full-pipeline or production use.
