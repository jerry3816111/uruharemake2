# M56 Blinded Same-Model Fair-Comparison Preflight Acceptance · 2026-09-01

## Decision

**Protocol-engineering gate: PASS. M56 execution: BLOCKED. Formal comparison result: NOT CREATED.**

This checkpoint freezes how B0–B5 and Ours will be compared before any real M55 outcome or M56 model
generation is available. It prevents a later score from changing the strongest control, visible input,
model settings, resource budget, success threshold, or answer-access sequence. It does not run the
comparison and does not show that Equation V1 works.

## Why this step was necessary

M55 is designed to produce a private cutoff-to-future dataset. If model conditions, the primary control,
token budgets, or scoring rules were selected after seeing those outcomes, a positive result could be a
protocol artifact rather than evidence for the state-transition mechanism. If generation can read the
future behavior key, the task is no longer prediction.

The preflight therefore locks the comparison while every real progress count is still zero and makes
execution fail closed until M55 genuinely authorizes M56.

## Frozen comparison

- B0: pre-cutoff historical behavior-frequency prior, with an explicit deterministic no-model exception;
- B1: current observable input X only;
- B2: X plus a static public-evidence persona summary;
- B3: X plus retrieved memory;
- B4: X plus a full-history summary, with summary cost included;
- B5: X plus structured full history — the fixed strongest primary control;
- Ours: the same observable data plus the frozen explicit state-transition mechanism — the candidate
  equation system.

The primary contrast is permanently **B5_STRUCTURED_HISTORY vs OURS_HYBRID**. A weaker baseline may not
replace B5 after results are known.

## Fairness, blinding, and decision gates

- B1–B5/Ours use the same `qwen3.5:9b` artifact, hardware fingerprint, decoding options, and declared
  per-sample token budgets; B0 is the only declared deterministic exception.
- Input budget is 8,192 tokens and output budget is 384 tokens per sample. B5 and Ours each have one
  semantic model-call cap per sample. All upstream Ours and B4-summary costs must be reported.
- Actual prompt tokens, latency, and peak memory are recorded. If B5/Ours actual prompt-token totals differ
  by more than 5%, the protocol requires an additional exact-token sensitivity comparison.
- The prediction packet contains only cutoff-before model input. The private outcome key is separate and
  cannot be read by generation. All condition predictions must be SHA-committed before a separate scorer
  may read outcomes.
- Condition order follows a sample-hash-rotated Latin cycle fixed by seed `560901`.
- Co-primary success requires both paired Brier and NLL delta 95% bootstrap upper bounds to be below zero;
  Ours top-1 accuracy may not trail B5 by more than five percentage points. All gates must pass. ECE is
  descriptive, not a substitute gate.
- A failed result is retained. Diagnosis belongs to M57, and any M58 repair changes one variable and uses
  new sealed data rather than rewriting this protocol.

## Acceptance evidence

### Contract and synthetic adversarial checks

- contract validation: PASS;
- 11 frozen dependency bindings: PASS;
- seven exact condition IDs and fixed B5/Ours primary contrast: PASS;
- contract hash: `aba95b4c0879cf9b8d70362606e6bf80055f9f34fa3475a8270a6007aa78abec`;
- live preflight report hash: `2e736852e5c1e95510db8badf254ea8d7e6f56873eedba40d8b9cf7cbde61456`;
- final focused suite including implementation-freeze verification: **17/17 passed**;
- M1/M2/M6/M54/V7/V9/M55/M56 selected compatibility suite before the freeze test: **115/115 passed**;
- final selected compatibility suite including the implementation-freeze verification: **116/116 passed**;
- Python compilation: PASS;
- `git diff --check`: PASS before documentation freeze;
- model calls: 0;
- target outcome access: 0;
- production-memory writes: 0.

The synthetic tests prove packet/key separation and reject inserted outcome fields, changed model input,
wrong condition order, stale hashes, missing M55 authority, different model artifacts, hardware or decoding,
token-budget drift, answer-visible generation, retry/fallback drift, sample-set drift, packet drift, and any
claim that a synthetic fixture executed the formal comparison.

The first focused run intentionally remains in the audit trail: **15 tests passed and one graphical wording
test failed** because the page rendered the two V7 counters as `[0, 0]` instead of the outsider-readable
`0/18 + 0/18`. Only that presentation was corrected; the final pre-freeze focused run was 16/16, and the
freeze-verification test brought the final focused suite to 17/17.

### Safari graphical acceptance

Safari reused the existing local test tab and remained at 28 tabs; no user tab was opened or closed and no
form was submitted. The page visibly showed:

1. all seven conditions and exactly what each condition may see;
2. `M55 temporal dataset → prediction packet → SHA commitment`, with the outcome key withheld;
3. the same-model/hardware rule, token budget and Brier/NLL decision gate;
4. current progress `V7 0/18 + 0/18`, `V9 0/30`, `real rows 0/30`, and `M56 禁止`;
5. blocker `complete_two_independent_v7_18_slot_ledgers` and an explicit statement that protocol readiness
   is not Equation V1 validity.

The full page fit the Safari viewport without horizontal overflow. Top and bottom views were inspected.

## Current authorization state

- M55 pilot complete: false;
- M55 authorizes M56: false;
- current M56 execution authorized: false;
- formal M56 result created: false;
- V7 private ledgers: 0/18 and 0/18;
- V9 independently reviewed events: 0/30;
- real temporal rows: 0/30;
- blocker: `complete_two_independent_v7_18_slot_ledgers`.

## Contribution to the candidate human-response equation

M54 defines the candidate equation, M55 defines how real cutoff-before input and later observable behavior
will be measured, and this M56 preflight defines the first fair falsification attempt. If Ours later beats
the strongest structured-history control under these unchanged gates, that would be bounded prospective
evidence that the explicit state-transition mechanism adds predictive value beyond giving the same model
structured history. If it fails, the current equation has not passed this test and the failure must remain.

Today there is no such result. This milestone removes post-outcome protocol freedom; it does not supply the
missing humans, Uruha rows, model predictions, statistical comparison, or causal validity evidence.

## Exact continuation

1. Two distinct consenting humans independently complete the unchanged V7 18-slot pilot.
2. Run the frozen reliability analyzer and retain the result; do not use Codex, LLM, synthetic labels, or
   the same person twice.
3. After a genuine reliability pass, both people independently complete V9 and boundary coding for all 30
   target slots.
4. A human explicitly adjudicates every pair, then the frozen M55 compiler produces exactly 30 valid real
   cutoff-to-future rows.
5. Revalidate all frozen hashes and authorization gates. Only then may a blinded M56 executor generate and
   SHA-commit B0–B5/Ours predictions before the separate scorer reads outcomes.

## Claim boundary

This is deterministic protocol, blinding, resource-control, validation, and graphical-UI evidence only. It
is not real-person prediction, an LLM comparison result, a validated human-response equation, evidence of
private mental states, human equivalence, full-pipeline readiness, or production authorization.
